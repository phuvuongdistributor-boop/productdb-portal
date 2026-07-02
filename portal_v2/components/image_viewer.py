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


def render_product_gallery(product, max_thumbnails: int = 4) -> None:
    images = resolve_product_images(product)
    code = str(product.get("Code", "")) if hasattr(product, "get") else ""
    if not images:
        st.info(image_missing_message(product))
        return
    selected_key = f"gallery_selected_image_{code}"
    selected = st.session_state.get(selected_key, images[0])
    if selected not in images:
        selected = images[0]
    st.caption(f"Gallery v3 - {len(images)} hinh anh")
    if len(images) > 1:
        visible_images = images[:max(1, max_thumbnails)]
        columns = st.columns(min(len(visible_images), max_thumbnails))
        for index, (column, image) in enumerate(zip(columns, visible_images), start=1):
            with column:
                st.image(image, width="stretch")
                if st.button(f"Anh {index}", key=f"gallery-{code}-{index}", width="stretch"):
                    st.session_state[selected_key] = image
                    st.rerun()
    st.image(selected, caption=code, width="stretch")
