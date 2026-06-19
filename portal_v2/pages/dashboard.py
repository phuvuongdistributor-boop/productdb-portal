from __future__ import annotations

import os

import streamlit as st

from auth import require_auth
from data_loader import count_products_with_images, drive_health, load_products_or_stop, unresolved_image_rows
from ui import apply_theme


st.set_page_config(page_title="Dashboard | ProductDB V2", layout="wide")
apply_theme()
require_auth(["admin"])
st.title("Dashboard")
st.caption(
    "App build: ghe-nhap-4k-bundle-v1 | "
    f"Render commit: {os.getenv('RENDER_GIT_COMMIT', 'unknown')[:7]}"
)
products = load_products_or_stop()
health = drive_health()
image_count = count_products_with_images(products)
unresolved_images = unresolved_image_rows(products)

with st.expander("Trạng thái kết nối Drive", expanded=True):
    sheet_status = "OK" if health.get("sheet_ok") is True else "Lỗi" if health.get("sheet_ok") is False else "Chưa kiểm tra"
    bundle_status = "OK" if health.get("bundle_ok") is True else "Lỗi" if health.get("bundle_ok") is False else "Chưa cấu hình/không dùng"
    st.write(f"Google Sheet LIVE: **{sheet_status}** - {health.get('sheet_message', '')}")
    st.write(f"Bundle ảnh Drive: **{bundle_status}** - {health.get('bundle_message', '')}")

columns = st.columns(5)
columns[0].metric("Total Rows", f"{len(products):,}")
columns[1].metric("Unique Code", f"{products['Code'].astype(str).nunique():,}")
columns[2].metric("Products With Images", f"{image_count:,}")
columns[3].metric("Products With Price", f"{products['SalePrice'].astype(str).str.strip().ne('').sum():,}")
columns[4].metric("Source Groups", f"{products['Source_Group'].astype(str).nunique():,}")

if not unresolved_images.empty:
    st.warning(
        f"{len(unresolved_images):,} product rows reference image paths that are not available in this deployment."
    )
    with st.expander("Unresolved image paths by source group", expanded=False):
        unresolved_counts = unresolved_images.groupby("Source_Group", dropna=False).size().sort_values(ascending=False)
        st.dataframe(unresolved_counts.rename("Rows"), width="stretch")
        sample_columns = ["Code", "ProductName", "Source_Group", "Image_Status", "Image_URL"]
        st.dataframe(unresolved_images.reindex(columns=sample_columns).head(50), width="stretch", hide_index=True)

st.subheader("Rows by Source Group")
chart = products.groupby("Source_Group", dropna=False).size().sort_values(ascending=False)
st.bar_chart(chart)
st.dataframe(chart.rename("Rows"), width="stretch")
