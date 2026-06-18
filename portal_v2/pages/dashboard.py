from __future__ import annotations

import streamlit as st

from auth import require_auth
from data_loader import count_products_with_images, drive_health, load_products_or_stop
from ui import apply_theme


st.set_page_config(page_title="Dashboard | ProductDB V2", layout="wide")
apply_theme()
require_auth(["admin"])
st.title("Dashboard")
products = load_products_or_stop()
health = drive_health()

with st.expander("Trạng thái kết nối Drive", expanded=True):
    sheet_status = "OK" if health.get("sheet_ok") is True else "Lỗi" if health.get("sheet_ok") is False else "Chưa kiểm tra"
    bundle_status = "OK" if health.get("bundle_ok") is True else "Lỗi" if health.get("bundle_ok") is False else "Chưa cấu hình/không dùng"
    st.write(f"Google Sheet LIVE: **{sheet_status}** - {health.get('sheet_message', '')}")
    st.write(f"Bundle ảnh Drive: **{bundle_status}** - {health.get('bundle_message', '')}")

columns = st.columns(5)
columns[0].metric("Total Rows", f"{len(products):,}")
columns[1].metric("Unique Code", f"{products['Code'].astype(str).nunique():,}")
columns[2].metric("Products With Images", f"{count_products_with_images(products):,}")
columns[3].metric("Products With Price", f"{products['SalePrice'].astype(str).str.strip().ne('').sum():,}")
columns[4].metric("Source Groups", f"{products['Source_Group'].astype(str).nunique():,}")

st.subheader("Rows by Source Group")
chart = products.groupby("Source_Group", dropna=False).size().sort_values(ascending=False)
st.bar_chart(chart)
st.dataframe(chart.rename("Rows"), width="stretch")
