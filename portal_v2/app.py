from __future__ import annotations

import streamlit as st

from auth import require_auth
from data_loader import count_products_with_images, load_data_status, load_products
from public_links import catalog_url
from ui import apply_theme


st.set_page_config(page_title="ProductDB V2", page_icon="P", layout="wide")
apply_theme()
user = require_auth()

st.markdown(
    """
    <style>
    .stApp { background: #f5f7fb; }
    .hero { padding: 2.2rem; border-radius: 22px; color: white;
      background: linear-gradient(125deg, #102a43, #146c94 58%, #19a7ce); margin-bottom: 1.2rem; }
    .hero h1 { margin: 0; font-size: 2.6rem; }
    .hero p { margin: .5rem 0 0; opacity: .9; font-size: 1.08rem; }
    [data-testid="stMetric"] { background: white; border: 1px solid #e5eaf0; padding: 1rem; border-radius: 16px; }
    .notice { text-align: center; padding: 1.2rem; margin-top: 1.5rem; border-radius: 16px;
      background: #fff8e7; border: 1px solid #f0d58c; color: #5f4610; font-weight: 600; }
    .notice strong { display:block; color:#b42318; font-size:1.25rem; margin-top:.45rem; letter-spacing:.04em; }
    .image-placeholder { min-height: 220px; display:grid; place-items:center; background:#eef2f6; border-radius:12px; color:#667085; }
    .product-card-body { background:white; padding:.8rem 1rem; border-radius:0 0 14px 14px; }
    .product-card-body h3 { min-height:3.4rem; font-size:1.05rem; margin:.35rem 0; }
    .product-code { color:#667085; font-size:.82rem; font-weight:700; }
    .product-price { color:#c62828; font-size:1.22rem; font-weight:800; }
    .product-hotline { color:#146c94; font-weight:700; margin-top:.35rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.link_button("Catalog công khai cho khách hàng", catalog_url(), width="stretch")

st.markdown(
    """
    <section class="hero">
      <h1>ProductDB V2</h1>
      <p>Cơ sở dữ liệu sản phẩm tập trung cho bán hàng, báo giá và tư vấn.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

try:
    products = load_products()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

data_status = load_data_status()
st.caption(
    f"Nguồn: {data_status.get('source', 'MASTER_DB.xlsx')} | "
    f"Cập nhật: {data_status.get('synced_at', 'chưa xác định')}"
)

metrics = st.columns(5)
metrics[0].metric("Tổng SKU", f"{len(products):,}")
metrics[1].metric("Mã sản phẩm", f"{products['Code'].astype(str).nunique():,}")
metrics[2].metric("Có hình ảnh", f"{count_products_with_images(products):,}")
metrics[3].metric("Có giá bán", f"{products['SalePrice'].astype(str).str.strip().ne('').sum():,}")
metrics[4].metric("Nhóm nguồn", f"{products['Source_Group'].astype(str).nunique():,}")

st.subheader("Khám phá dữ liệu")
links = st.columns(6 if user["role"] == "admin" else 4)
position = 0
if user["role"] == "admin":
    links[position].page_link("pages/dashboard.py", label="Dashboard")
    position += 1
links[position].page_link("pages/products.py", label="Sản phẩm")
links[position + 1].page_link("pages/search.py", label="Tìm kiếm")
links[position + 2].page_link("pages/quotation.py", label="Tạo báo giá")
links[position + 3].page_link("pages/quotations.py", label="Quản lý báo giá")
if user["role"] == "admin":
    links[position + 4].page_link("pages/users.py", label="Tài khoản")

st.markdown(
    """
    <div class="notice">
      Sản phẩm có thể thay đổi kích thước, vật liệu và màu sắc theo yêu cầu.
      <strong>Hotline: 0929.878.666</strong>
    </div>
    """,
    unsafe_allow_html=True,
)
