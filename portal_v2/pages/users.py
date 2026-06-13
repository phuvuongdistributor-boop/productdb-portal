from __future__ import annotations

import pandas as pd
import streamlit as st

from auth import ROLES, list_users, require_auth, upsert_user
from ui import apply_theme


st.set_page_config(page_title="Tài khoản | ProductDB V2", layout="wide")
apply_theme()
require_auth(["admin"])
st.title("Quản lý tài khoản")

users = list_users()
st.dataframe(
    pd.DataFrame([
        {
            "Tên đăng nhập": user.get("username", ""),
            "Tên hiển thị": user.get("display_name", ""),
            "Vai trò": user.get("role", ""),
            "Hoạt động": user.get("active", False),
            "Ngày tạo": user.get("created_at", ""),
        }
        for user in users
    ]),
    width="stretch", hide_index=True,
)

st.subheader("Thêm hoặc cập nhật tài khoản")
with st.form("user-form"):
    username = st.text_input("Tên đăng nhập", placeholder="Ví dụ: sale.lan")
    display_name = st.text_input("Tên hiển thị", placeholder="Ví dụ: Nguyễn Lan")
    role = st.selectbox("Vai trò", ROLES)
    password = st.text_input("Mật khẩu mới", type="password", help="Để trống khi chỉ cập nhật tài khoản đã có.")
    active = st.checkbox("Đang hoạt động", value=True)
    save = st.form_submit_button("Lưu tài khoản", type="primary")

if save:
    try:
        upsert_user(username, display_name, role, password, active)
        st.success("Đã lưu tài khoản.")
        st.rerun()
    except ValueError as error:
        st.error(str(error))
