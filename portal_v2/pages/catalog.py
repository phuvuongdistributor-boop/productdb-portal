from __future__ import annotations

import html

import streamlit as st

from components.catalog_image import catalog_image
from data_loader import load_products_or_stop
from ui import apply_theme, paginate_frame, source_label


def image_placeholder(product) -> str:
    status = str(product.get("Image_Status", "")).strip().upper()
    if status == "WATERMARK_REVIEW":
        return "Anh dang cap nhat"
    return "Chua co hinh anh"


st.set_page_config(page_title="Catalog san pham", page_icon="P", layout="wide")
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
      <h1>Catalog noi that</h1>
      <p>Tra cuu san pham va lien he tu van kich thuoc, vat lieu, mau sac theo yeu cau.</p>
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
        st.error("Khong tim thay san pham.")
    else:
        image_col, detail_col = st.columns([1, 1.25], gap="large")
        with image_col:
            image = catalog_image(product.get("Image_URL", ""))
            if image:
                st.image(image, width="stretch")
            else:
                st.markdown(
                    f'<div class="catalog-image-placeholder">{html.escape(image_placeholder(product))}</div>',
                    unsafe_allow_html=True,
                )
        with detail_col:
            st.caption(html.escape(str(product.get("Code", ""))))
            st.title(str(product.get("ProductName", "San pham")))
            for label, field in [
                ("Mo ta", "Description"),
                ("Kich thuoc", "Size"),
                ("Vat lieu", "Material"),
                ("Danh muc", "Category"),
                ("Nhom san pham", "SubCategory"),
            ]:
                value = str(product.get(field, "")).strip()
                if value:
                    st.markdown(f"**{label}:** {html.escape(value)}")
            st.info("Lien he de nhan gia va phuong an phu hop nhu cau cua ban.")
            st.markdown("### Hotline: 0929.878.666")
            st.link_button("Xem toan bo catalog", "catalog", width="stretch")
    st.stop()

query_col, source_col, category_col = st.columns([2.2, 1.4, 1.4])
query = query_col.text_input("Tim san pham", placeholder="Nhap ma, ten hoac mo ta...")
sources = sorted(value for value in products["Source_Group"].astype(str).unique() if value.strip())
selected_source = source_col.selectbox(
    "Nguon san pham",
    [""] + sources,
    format_func=lambda value: source_label(value) if value else "Tat ca",
)
categories = sorted(value for value in products["Category"].astype(str).unique() if value.strip())
selected_category = category_col.selectbox("Danh muc", [""] + categories, format_func=lambda value: value or "Tat ca")

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

st.caption(f"Tim thay {len(filtered):,} san pham")
page_frame = paginate_frame(filtered, "catalog")
for start in range(0, len(page_frame), 4):
    columns = st.columns(4)
    for container, (_, product) in zip(columns, page_frame.iloc[start:start + 4].iterrows()):
        with container:
            with st.container(border=True):
                image = catalog_image(product.get("Image_URL", ""))
                if image:
                    st.image(image, width="stretch")
                else:
                    st.markdown(
                        f'<div class="catalog-image-placeholder">{html.escape(image_placeholder(product))}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f'<div class="customer-code">{html.escape(str(product.get("Code", "")))}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="catalog-product-name">{html.escape(str(product.get("ProductName", "")))}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(source_label(product.get("Source_Group", "")))
                st.link_button("Xem chi tiet", f"catalog?code={product.get('Code', '')}", width="stretch")

st.markdown(
    """
    <div style="text-align:center;background:#fff8e7;border:1px solid #f0d58c;border-radius:16px;padding:18px;margin-top:25px">
      San pham co the thay doi kich thuoc, vat lieu va mau sac theo yeu cau.<br>
      <strong style="color:#b42318;font-size:1.2rem">Hotline: 0929.878.666</strong>
    </div>
    """,
    unsafe_allow_html=True,
)
