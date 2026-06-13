from __future__ import annotations

import streamlit as st

from auth import require_auth
from components.image_viewer import render_image
from components.product_card import format_price
from data_loader import find_product, load_products
from public_links import catalog_url
from cart import add_product, cart_count
from ui import apply_theme


st.set_page_config(page_title="Chi tiết sản phẩm | ProductDB V2", layout="wide")
apply_theme()
require_auth()
code = st.query_params.get("code") or st.session_state.get("selected_code", "")
if not code:
    st.warning("Hãy chọn một sản phẩm từ trang tìm kiếm.")
    st.stop()

row_id = st.session_state.get("selected_row_id")
products = load_products()
product = products.loc[int(row_id)] if row_id is not None and int(row_id) in products.index else find_product(str(code))
if product is None:
    st.error(f"Không tìm thấy sản phẩm: {code}")
    st.stop()

st.title(str(product.get("ProductName", "Sản phẩm")))
left, right = st.columns([1, 1.25], gap="large")
with left:
    render_image(product.get("Image_URL"), str(product.get("Code", "")))
with right:
    st.caption(str(product.get("Code", "")))
    st.markdown(f"## {format_price(product.get('SalePrice'))}")
    fields = ["Description", "Size", "Material", "CatalogPrice", "SalePrice", "Hotline"]
    for field in fields:
        value = product.get(field, "")
        if field in {"CatalogPrice", "SalePrice"}:
            value = format_price(value)
        st.markdown(f"**{field}:** {value or 'Đang cập nhật'}")
    source_url = str(product.get("Source_URL", "")).strip()
    if source_url:
        st.link_button("Xem nguồn sản phẩm", source_url)
    quantity = st.number_input("Số lượng", min_value=1, value=1, step=1)
    action_left, action_right = st.columns(2)
    if action_left.button("Thêm vào báo giá", type="primary", width="stretch"):
        add_product(product, int(quantity))
        st.success("Đã thêm sản phẩm vào báo giá.")
    action_right.page_link("pages/quotation.py", label=f"Mở báo giá ({cart_count()})", width="stretch")
    st.divider()
    st.markdown("**Link gửi khách (ẩn giá):**")
    customer_url = catalog_url(product.get("Code", ""))
    st.text_input("Link sản phẩm cho khách", value=customer_url, disabled=True, label_visibility="collapsed")
    st.link_button("Mở trang khách hàng", customer_url, width="stretch")

st.markdown(
    """
    <div style="text-align:center;padding:20px;border-radius:16px;background:#fff8e7;border:1px solid #f0d58c;margin-top:24px;font-weight:600">
      Sản phẩm có thể thay đổi kích thước, vật liệu và màu sắc theo yêu cầu.
      <div style="color:#b42318;font-size:1.25rem;margin-top:8px">Hotline: 0929.878.666</div>
    </div>
    """,
    unsafe_allow_html=True,
)
