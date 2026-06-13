
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime
from pathlib import Path

import streamlit as st


DEFAULT_USERS_PATH = Path(__file__).resolve().parents[1] / "config" / "auth_users.json"
USERS_PATH = Path(os.getenv("PRODUCTDB_USERS_PATH", str(DEFAULT_USERS_PATH)))
ITERATIONS = 310_000
ROLES = ["admin", "sale"]


def _load_users() -> dict:
    bootstrap_password = os.getenv("PRODUCTDB_ADMIN_PASSWORD", "").strip()
    bootstrap_username = os.getenv("PRODUCTDB_ADMIN_USERNAME", "admin").strip().lower()
    bootstrap_fingerprint = (
        hashlib.sha256(bootstrap_password.encode("utf-8")).hexdigest()
        if bootstrap_password else ""
    )
    if not USERS_PATH.exists():
        if bootstrap_password:
            salt, password_hash = hash_password(bootstrap_password)
            data = {
                "users": [{
                    "username": bootstrap_username,
                    "display_name": os.getenv("PRODUCTDB_ADMIN_NAME", "Quản trị viên").strip(),
                    "role": "admin", "active": True,
                    "salt": salt, "password_hash": password_hash,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }],
                "bootstrap_password_fingerprint": bootstrap_fingerprint,
            }
            _save_users(data)
            return data
        return {"users": []}
    data = json.loads(USERS_PATH.read_text(encoding="utf-8"))
    if bootstrap_password and data.get("bootstrap_password_fingerprint") != bootstrap_fingerprint:
        users = data.setdefault("users", [])
        admin = next((user for user in users if user.get("username") == bootstrap_username), None)
        if admin is None:
            admin = {"username": bootstrap_username, "created_at": datetime.now().isoformat(timespec="seconds")}
            users.append(admin)
        salt, password_hash = hash_password(bootstrap_password)
        admin.update({
            "display_name": os.getenv("PRODUCTDB_ADMIN_NAME", "Quản trị viên").strip(),
            "role": "admin",
            "active": True,
            "salt": salt,
            "password_hash": password_hash,
        })
        data["bootstrap_password_fingerprint"] = bootstrap_fingerprint
        _save_users(data)
    return data


def _save_users(data: dict) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = USERS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(USERS_PATH)


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

