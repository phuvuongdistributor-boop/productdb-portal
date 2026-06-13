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
    if not USERS_PATH.exists():
        bootstrap_password = os.getenv("PRODUCTDB_ADMIN_PASSWORD", "").strip()
        if bootstrap_password:
            salt, password_hash = hash_password(bootstrap_password)
            data = {
                "users": [{
                    "username": os.getenv("PRODUCTDB_ADMIN_USERNAME", "admin").strip().lower(),
                    "display_name": os.getenv("PRODUCTDB_ADMIN_NAME", "Quản trị viên").strip(),
                    "role": "admin", "active": True,
                    "salt": salt, "password_hash": password_hash,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }]
            }
            _save_users(data)
            return data
        return {"users": []}
    return json.loads(USERS_PATH.read_text(encoding="utf-8"))


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
    user = get_user(username)
    if not user or not user.get("active", False):
        return None
    if not verify_password(password, user.get("salt", ""), user.get("password_hash", "")):
        return None
    return {key: user.get(key) for key in ["username", "dispo^��kh��춻�q�^t(current_status) if current_status in STATUSES else 0,
            key=f"status-{quotation_id}",
        )
        if new_status != current_status:
            update_status(quotation_id, new_status)
            st.rerun()
        open_col, duplicate_col = actions.columns(2)
        if open_col.button("Mở / sửa", key=f"open-{quotation_id}", width="stretch"):
            open_record(record)
            st.switch_page("pages/quotation.py")
        if duplicate_col.button("Nhân bản", key=f"duplicate-{quotation_id}", width="stretch"):
            duplicate = duplicate_quotation(quotation_id)
            open_record(duplicate)
            st.switch_page("pages/quotation.py")
