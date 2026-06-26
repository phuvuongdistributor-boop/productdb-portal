from __future__ import annotations

import streamlit as st

from data_loader import resolve_image_source, resolve_product_images


def image_missing_message(product=None) -> str:
    status = ""
    if hasattr(product, "get"):
        status = str(product.get("Image_Status", "")).strip().upper()
    if status == "WATERMARK_REVIEW":
        return "Anh dang cap nhat."
    return "San pham chua co hinh anh."


def render_image(url: object, caption: str = "") -> None:
    value = resolve_image_source(url)
    if value:
        st.image(value, caption=caption, width="stretch")
    else:
        st.info(image_missing_message())


def render_product_gallery(product) -> None:
    images = resolve_product_images(product)
    code = str(product.get("Code", "")) if hasattr(product, "get") else ""
    if not images:
        st.info(image_missing_message(product))
        return
    st.image(images[0], caption=code, width="stretch")
    if len(images) <= 1:
        return
    st.caption(f"{len(images)} hinh anh")
    for start in range(1, len(images), 3):
        columns = st.columns(3)
        for column, image in zip(columns, images[start:start + 3]):
            with column:
                st.image(image, width="stretch")
