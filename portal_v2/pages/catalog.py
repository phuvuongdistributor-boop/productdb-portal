from __future__ import annotations

import html

import streamlit as st

from components.catalog_image import catalog_image
from data_loader import load_products_or_stop
from ui import apply_theme, source_label


st.set_page_config(page_title="Catalog sản phẩm", page_icon="P", layout="wide")
apply_theme()
st.markdown(
    """
    <style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }
    .block-container { max-width: 1240px; padding-top: 1.5rem; }
    .catalog-hero { background:linear-gradient(120deg,#102a43,#176b87); color:white;
      padding:24px 30px; border-radius:18px; margin-bottom:18px; }
    .catalog-hero h1 { color:white; margin:0; }
    [data-testid="stVerticalBlockBorderWrapper"] { background:white; border-radius:15px; }
    [data-testid="stImage"] img { border-radius:10px; display:block; }
    .catalog-image-placeholder { height:180px; display:grid; place-items:center;
      background:#eef3f7; border-radius:10px; color:#667085; margin-bottom:.5rem; }
    .catalog-product-name { font-size:1rem; font-weight:700; line-height:1.4;
      min-height:2.8rem; margin:.45rem 0; color:#102a43; }
    .customer-code { color:#176b87; font-weight:700; font-size:.85rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="catalog-hero">
      <h1>Catalog nội thất</h1>
      <p>Tra cứu sản phẩm và liên hệ tư vấn kích thước, vật liệu, màu sắc theo yêu cầu.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

code = str(st.query_params.get("code", "")).strip()
products = load_products_or_stop()
if code:
    matches = products[products["Code"].astype(str).str.casefold() == code.casefold()]
    product = None if matches.empty else matches.iloc[0]
    if product is None:
        st.error("Không tìm thấy sản phẩm.")
    else:
        image_col, detail_col = st.columns([1, 1.25], gap="large")
        with image_col:
            image = catalog_image(product.get("Image_URL", ""))
            if image:
                st.image(image, width="stretch")
        with detail_col:
            st.caption(html.escape(str(product.get("Code", ""))))
            st.title(str(product.get("ProductName", "Sản phẩm")))
            for label, field in [
                ("Mô tả", "Description"), ("Kích thước", "Size"),
                ("Vật liệu", "Material"), ("Danh mục", "Category"),
                ("Nhóm sản phẩm", "SubCategory"),
            ]:
                value = str(product.get(field, "")).strip()
                if value:
                    st.markdown(f"**{label}:** {html.escape(value)}")
            st.info("Liên hệ để nhận giá và phương án phù hợp nhu cầu của bạn.")
            st.markdown("### Hotline: 0929.878.666")
            st.link_button("Xem toàn bộ catalog", "catalog", width="stretch")
    st.stop()

query_col, source_col, category_col = st.columns([2.2, 1.4, 1.4])
query = query_col.text_input("Tìm sản phẩm", placeholder="Nhập mã, tên hoặc mô tả...")
sources = sorted(value for value in products["Source_Group"].astype(str).unique() if value.strip())
selected_source = source_col.selectbox("Nguồn sản phẩm", [""] + sources, format_func=lambda value: source_label(value) if value else "Tất cả")
categories = sorted(value for value in products["Category"].astype(str).unique() if value.strip())
selected_category = category_col.selectbox("Danh mục", [""] + categories, format_func=lambda value: value or "Tất cả")

filtered = products
if query.strip():
    needle = query.strip()
    mask = False
    for column in ["Code", "ProductName", "Description"]:
        mask = mask | filtered[column].astype(str).str.contains(needle, case=False, na=False, regex=False)
    filtered = filtered[mask]
if selected_source:
    filtered = filtered[filtered["Source_Group"].astype(str) == selected_source]
if selected_category:
    filtered = filtered[filtered["Category"].astype(str) == selected_category]

st.caption(f"Tìm thấy {len(filtered):,} sản phẩm")
limit = st.selectbox("Số sản phẩm hiển thị", [24, 48, 96], index=0)
for start in range(0, min(len(filtered), limit), 4):
    columns = st.columns(4)
    for container, (_, product) in zip(columns, filtered.iloc[start:start + 4].iterrows()):
        with container:
            with st.container(border=True):
                image = catalog_image(product.get("Image_URL", ""))
                if image:
                    st.image(image, width="stretch")
                else:
                    st.markdown(
                        '<div class="catalog-image-placeholder">Chưa có hình ảnh</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown(f'<div class="customer-code">{html.escape(str(product.get("Code", "")))}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="catalog-product-name">{html.escape(str(product.get("ProductName", "")))}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(source_label(product.get("Source_Group", "")))
                st.link_button("Xem chi tiết", f"catalog?code={product.get('Code', '')}", width="stretch")

st.markdown(
    """
    <div style="text-align:center;background:#fff8e7;border:1px solid #f0d58c;border-radius:16px;padding:18px;margin-top:25px">
      Sản phẩm có thể thay đổi kích thước, vật liệu và màu sắc theo yêu cầu.<br>
      <strong style="color:#b42318;font-size:1.2rem">Hotline: 0929.878.666</strong>
    </div>
    """,
    unsafe_allow_html=True,
)
