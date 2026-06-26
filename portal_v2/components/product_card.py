from __future__ import annotations

import html

import streamlit as st

from data_loader import resolve_image_source
from cart import add_product


def format_price(value: object) -> str:
    try:
        return f"{float(value):,.0f} d".replace(",", ".")
    except (TypeError, ValueError):
        return "Lien he"


def image_placeholder(product) -> str:
    status = str(product.get("Image_Status", "")).strip().upper()
    if status == "WATERMARK_REVIEW":
        return "Anh dang cap nhat"
    return "Chua co hinh anh"


def render_product_card(product) -> None:
    image = resolve_image_source(product.get("Image_URL", ""))
    if image:
        st.image(image, width="stretch")
    else:
        st.markdown(
            f'<div class="image-placeholder">{html.escape(image_placeholder(product))}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f"""
        <div class="product-card-body">
          <div class="product-code">{html.escape(str(product.get('Code', '')))}</div>
          <h3>{html.escape(str(product.get('ProductName', '')))}</h3>
          <div class="product-price">{format_price(product.get('SalePrice'))}</div>
          <div class="product-hotline">Hotline: 0929.878.666</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns(2)
    if left.button("Chi tiet", key=f"detail-{product.name}", width="stretch"):
        st.session_state["selected_code"] = str(product.get("Code", ""))
        st.session_state["selected_row_id"] = str(product.name)
        st.switch_page("pages/product_detail.py")
    if right.button("Them bao gia", key=f"cart-{product.name}", width="stretch"):
        add_product(product)
        st.session_state["cart_notice"] = f"Da them {product.get('Code', '')} vao bao gia"
        st.rerun()
