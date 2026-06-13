from __future__ import annotations

import streamlit as st

from data_loader import resolve_image_source


def render_image(url: object, caption: str = "") -> None:
    value = resolve_image_source(url)
    if value:
        st.image(value, caption=caption, width="stretch")
    else:
        st.info("Sản phẩm chưa có hình ảnh.")
