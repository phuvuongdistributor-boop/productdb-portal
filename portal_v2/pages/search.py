from __future__ import annotations

import streamlit as st

from auth import require_auth
from components.filters import apply_filters
from components.product_card import render_product_card
from data_loader import load_products_or_stop
from cart import cart_count
from ui import apply_theme


st.set_page_config(page_title="Tìm kiếm | ProductDB V2", layout="wide")
apply_theme()
require_auth()
st.title("Tìm kiếm sản phẩm")
notice = st.session_state.pop("cart_notice", "")
if notice:
    st.toast(notice)
head_left, head_right = st.columns([4, 1])
with head_right:
    st.page_link("pages/quotation.py", label=f"Báo giá ({cart_count()})")
products = load_products_or_stop()
query = st.text_input("Tìm theo Code, ProductName hoặc Description", placeholder="Nhập mã hoặc tên sản phẩm...")
filtered = apply_filters(products)

if query.strip():
    needle = query.strip()
    mask = False
    for column in ["Code", "ProductName", "Description"]:
        mask = mask | filtered[column].astype(str).str.contains(needle, case=False, na=False, regex=False)
    filtered = filtered[mask]

st.caption(f"Tìm thấy {len(filtered):,} SKU")
limit = st.selectbox("Số sản phẩm hiển thị", [24, 48, 96], index=0)
for start in range(0, min(len(filtered), limit), 4):
    columns = st.columns(4)
    for container, (_, product) in zip(columns, filtered.iloc[start:start + 4].iterrows()):
        with container:
            render_product_card(product)
