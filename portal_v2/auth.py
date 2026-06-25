from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USERS_PATH = PROJECT_ROOT / "config" / "auth_users.json"
USERS_PATH = Path(os.getenv("PRODUCTDB_USERS_PATH", str(DEFAULT_USERS_PATH)))
DRIVE_CONFIG_PATH = PROJECT_ROOT / "config" / "drive_config.json"
AUTH_USERS_FILE_NAME = os.getenv("PRODUCTDB_USERS_DRIVE_NAME", "productdb_auth_users.json")
AUTH_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
ITERATIONS = 310_000
ROLES = ["admin", "sale"]


def _local_load_users() -> dict:
    if not USERS_PATH.exists():
        return {"users": []}
    return json.loads(USERS_PATH.read_text(encoding="utf-8"))


def _load_users() -> dict:
    data = _load_users_backend()
    data, changed = _ensure_bootstrap_admin(data)
    if changed:
        _save_users(data)
    return data


def _load_users_backend() -> dict:
    local_data = _local_load_users()
    if not _drive_users_enabled():
        return local_data
    try:
        remote_data = _load_users_from_drive()
        if remote_data is None:
            _save_users_to_drive(local_data)
            return local_data
        merged, changed = _merge_user_sets(remote_data, local_data)
        if changed:
            _save_users_to_drive(merged)
        _save_users_local(merged)
        return merged
    except Exception:
        return local_data


def _ensure_bootstrap_admin(data: dict) -> tuple[dict, bool]:
    bootstrap_password = os.getenv("PRODUCTDB_ADMIN_PASSWORD", "").strip()
    bootstrap_username = os.getenv("PRODUCTDB_ADMIN_USERNAME", "admin").strip().lower()
    bootstrap_fingerprint = (
        hashlib.sha256(bootstrap_password.encode("utf-8")).hexdigest()
        if bootstrap_password else ""
    )
    changed = False
    if bootstrap_password and data.get("bootstrap_password_fingerprint") != bootstrap_fingerprint:
        users = data.setdefault("users", [])
        admin = next((user for user in users if user.get("username") == bootstrap_username), None)
        if admin is None:
            admin = {"username": bootstrap_username, "created_at": datetime.now().isoformat(timespec="seconds")}
            users.append(admin)
        salt, password_hash = hash_password(bootstrap_password)
        admin.update(
            {
                "display_name": os.getenv("PRODUCTDB_ADMIN_NAME", "Quản trị viên").strip(),
                "role": "admin",
                "active": True,
                "salt": salt,
                "password_hash": password_hash,
            }
        )
        data["bootstrap_password_fingerprint"] = bootstrap_fingerprint
        changed = True
    return data, changed


def _save_users(data: dict) -> None:
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save_users_local(data)
    if _drive_users_enabled():
        try:
            _save_users_to_drive(data)
        except Exception:
            pass


def _save_users_local(data: dict) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = USERS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(USERS_PATH)


def _merge_user_sets(primary: dict, fallback: dict) -> tuple[dict, bool]:
    users = primary.setdefault("users", [])
    by_username = {str(user.get("username", "")).casefold(): user for user in users}
    changed = False
    for fallback_user in fallback.get("users", []):
        username = str(fallback_user.get("username", "")).casefold()
        if username and username not in by_username:
            users.append(fallback_user)
            by_username[username] = fallback_user
            changed = True
    return primary, changed


def _drive_users_enabled() -> bool:
    if os.getenv("PRODUCTDB_USERS_STORE", "drive").strip().lower() == "local":
        return False
    return bool(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )


def _load_drive_config() -> dict:
    if not DRIVE_CONFIG_PATH.exists():
        return {}
    return json.loads(DRIVE_CONFIG_PATH.read_text(encoding="utf-8"))


def _drive_credentials():
    from google.oauth2 import service_account

    inline_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if inline_json:
        return service_account.Credentials.from_service_account_info(
            json.loads(inline_json), scopes=AUTH_DRIVE_SCOPES
        )
    if credentials_path:
        return service_account.Credentials.from_service_account_file(credentials_path, scopes=AUTH_DRIVE_SCOPES)
    raise RuntimeError("Missing Google service account credentials.")


def _drive_session():
    from google.auth.transport.requests import AuthorizedSession

    return AuthorizedSession(_drive_credentials())


def _folder_id_from_url(url: str) -> str:
    marker = "/folders/"
    if marker in url:
        return url.split(marker, 1)[1].split("?", 1)[0].strip("/")
    return ""


def _auth_drive_file_id(session=None) -> str:
    configured = os.getenv("PRODUCTDB_USERS_DRIVE_FILE_ID", "").strip()
    config = _load_drive_config().get("auth_users", {})
    if configured:
        return configured
    if config.get("file_id"):
        return str(config["file_id"])
    session = session or _drive_session()
    folder_id = _folder_id_from_url(_load_drive_config().get("project_folder_url", ""))
    query_parts = [
        f"name = '{AUTH_USERS_FILE_NAME}'",
        "trashed = false",
        "mimeType = 'application/json'",
    ]
    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")
    query = quote(" and ".join(query_parts), safe="")
    endpoint = f"https://www.googleapis.com/drive/v3/files?q={query}&fields=files(id,name)&pageSize=1"
    response = session.get(endpoint, timeout=30)
    response.raise_for_status()
    files = response.json().get("files", [])
    return files[0]["id"] if files else ""


def _load_users_from_drive() -> dict | None:
    session = _drive_session()
    file_id = _auth_drive_file_id(session)
    if not file_id:
        return None
    response = session.get(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", timeout=30)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json() or {"users": []}


def _save_users_to_drive(data: dict) -> None:
    session = _drive_session()
    file_id = _auth_drive_file_id(session)
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    if file_id:
        response = session.patch(
            f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media",
            data=payload,
            headers={"Content-Type": "application/json; charset=UTF-8"},
            timeout=30,
        )
        response.raise_for_status()
        return
    folder_id = _folder_id_from_url(_load_drive_config().get("project_folder_url", ""))
    metadata = {"name": AUTH_USERS_FILE_NAME, "mimeType": "application/json"}
    if folder_id:
        metadata["parents"] = [folder_id]
    boundary = "productdb-users-boundary"
    body = (
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata, ensure_ascii=False)}\r\n"
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
    ).encode("utf-8") + payload + f"\r\n--{boundary}--".encode("utf-8")
    response = session.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id",
        data=body,
        headers={"Content-Type": f"multipart/related; boundary={boundary}"},
        timeout=30,
    )
    response.raise_for_status()


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, password_hash: str) -> bool:
    _, candidate = hash_password(password, salt_hex)
    return hmac.compare_digest(candidate, password_hash)


def list_users() -> list[dict]:
    return _load_users().get("users", [])


def get_user(username: str) -> dict | None:
    normalized = username.strip().casefold()
    return next((user for user in list_users() if user.get("username", "").casefold() == normalized), None)


def upsert_user(username: str, display_name: str, role: str, password: str = "", active: bool = True) -> dict:
    if role not in ROLES:
        raise ValueError("Vai trò không hợp lệ")
    username = username.strip().lower()
    if not username or not display_name.strip():
        raise ValueError("Tên đăng nhập và tên hiển thị không được trống")
    data = _load_users()
    users = data.setdefault("users", [])
    existing = next((user for user in users if user.get("username") == username), None)
    if existing is None and not password:
        raise ValueError("Tài khoản mới phải có mật khẩu")
    if existing is None:
        existing = {"username": username, "created_at": datetime.now().isoformat(timespec="seconds")}
        users.append(existing)
    existing.update({"display_name": display_name.strip(), "role": role, "active": bool(active)})
    if password:
        salt, password_hash = hash_password(password)
        existing.update({"salt": salt, "password_hash": password_hash})
    _save_users(data)
    return existing


def authenticate(username: str, password: str) -> dict | None:
    bootstrap_username = os.getenv("PRODUCTDB_ADMIN_USERNAME", "admin").strip().casefold()
    bootstrap_password = os.getenv("PRODUCTDB_ADMIN_PASSWORD", "").strip()
    if (
        bootstrap_password
        and username.strip().casefold() == bootstrap_username
        and hmac.compare_digest(password, bootstrap_password)
    ):
        return {
            "username": bootstrap_username,
            "display_name": os.getenv("PRODUCTDB_ADMIN_NAME", "Quản trị viên").strip(),
            "role": "admin",
        }
    user = get_user(username)
    if not user or not user.get("active", False):
        return None
    if not verify_password(password, user.get("salt", ""), user.get("password_hash", "")):
        return None
    return {key: user.get(key) for key in ["username", "display_name", "role"]}


def current_user() -> dict | None:
    return st.session_state.get("auth_user")


def logout() -> None:
    for key in list(st.session_state):
        del st.session_state[key]


def login_screen() -> None:
    st.markdown("## Đăng nhập ProductDB V2")
    st.caption("Dành cho nhân viên sale và quản trị viên.")
    bootstrap_password_configured = bool(os.getenv("PRODUCTDB_ADMIN_PASSWORD", "").strip())
    if not bootstrap_password_configured:
        st.warning("Chưa nhận biến PRODUCTDB_ADMIN_PASSWORD.")
    with st.form("login-form"):
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        submitted = st.form_submit_button("Đăng nhập", type="primary", width="stretch")
    if submitted:
        locked_until = float(st.session_state.get("login_locked_until", 0))
        if time.time() < locked_until:
            st.error("Đăng nhập tạm khóa trong 60 giây do thử sai nhiều lần.")
            return
        user = authenticate(username, password)
        if user:
            st.session_state.pop("login_failures", None)
            st.session_state.pop("login_locked_until", None)
            st.session_state["auth_user"] = user
            st.rerun()
        failures = int(st.session_state.get("login_failures", 0)) + 1
        st.session_state["login_failures"] = failures
        if failures >= 5:
            st.session_state["login_locked_until"] = time.time() + 60
            st.session_state["login_failures"] = 0
        st.error("Tên đăng nhập hoặc mật khẩu không đúng.")


def require_auth(roles: list[str] | None = None) -> dict:
    user = current_user()
    if not user:
        login_screen()
        st.stop()
    if roles and user.get("role") not in roles:
        st.error("Bạn không có quyền truy cập trang này.")
        st.stop()
    with st.sidebar:
        st.markdown(f"**{user['display_name']}**")
        st.caption(f"Vai trò: {user['role']}")
        if st.button("Đăng xuất", width="stretch"):
            logout()
            st.switch_page("app.py")
    return user
