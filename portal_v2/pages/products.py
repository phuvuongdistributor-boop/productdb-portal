from __future__ import annotations

import streamlit as st

from auth import require_auth
from cart import cart_count
from data_loader import load_products
from public_links import catalog_url
from ui import apply_theme, source_label


st.set_page_config(page_title="Sản phẩm | ProductDB V2", page_icon="P", layout="wide")
apply_theme()
require_auth()
st.title("Sản phẩm theo nguồn dữ liệu")
st.caption("Chọn tab nguồn để tra cứu nhanh SKU, hình ảnh, giá và thông tin phân loại.")
quotation_link, catalog_link = st.columns(2)
quotation_link.page_link("pages/quotation.py", label=f"Mở báo giá ({cart_count()})")
catalog_link.link_button("Mở catalog khách hàng", catalog_url(), width="stretch")
with st.expander("Link gửi khách hàng"):
    st.text_input("Catalog không hiển thị giá", value=catalog_url(), disabled=True)

products = load_products()
source_counts = products["Source_Group"].astype(str).value_counts()
sources = source_counts.index.tolist()
tab_labels = [f"Tất cả ({len(products):,})"] + [f"{source_label(source)} ({source_counts[source]:,})" for source in sources]
tabs = st.tabs(tab_labels)


def render_source_tab(frame, key: str) -> None:
    search_col, category_col, subcategory_col = st.columns([2.4, 1.4, 1.4])
    query = search_col.text_input(
        "Tìm trong nguồn", key=f"product-query-{key}",
        placeholder="Mã, tên hoặc mô tả sản phẩm...",
    )
    categories = sorted(value for value in frame["Category"].astype(str).unique() if value.strip())
    selected_categories = category_col.multiselect("Danh mục", categories, key=f"product-category-{key}")
    subcategories = sorted(value for value in frame["SubCategory"].astype(str).unique() if value.strip())
    selected_subcategories = subcategory_col.multiselect("Danh mục con", subcategories, key=f"product-subcategory-{key}")
    filtered = frame
    if query.strip():
        needle = query.strip()
        mask = False
        for column in ["Code", "ProductName", "Description"]:
            mask = mask | filtered[column].astype(str).str.contains(needle, case=False, na=False, regex=False)
        filtered = filtered[mask]
    if selected_categories:
        filtered = filtered[filtered["Category"].astype(str).isin(selected_categories)]
    if selected_subcategories:
        filtered = filtered[filtered["SubCategory"].astype(str).isin(selected_subcategories)]

    st.caption(f"Hiển thị {len(filtered):,} SKU")
    display = filtered[[
        "Image_URL", "Code", "ProductName", "SalePrice", "Category",
        "SubCategory", "Material", "Source_Group",
    ]].copy()
    display["Source_Group"] = display["Source_Group"].map(source_label)
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        height=620,
        column_config={
            "Image_URL": st.column_config.ImageColumn("Ảnh", width="small"),
            "Code": st.column_config.TextColumn("Mã", width="small"),
            "ProductName": st.column_config.TextColumn("Tên sản phẩm", width="large"),
            "SalePrice": st.column_config.NumberColumn("Giá bán", format="localized", width="small"),
            "Category": "Danh mục",
            "SubCategory": "Danh mục con",
            "Material": "Vật liệu",
            "Source_Group": "Nguồn dữ liệu",
        },
    )


with tabs[0]:
    render_source_tab(products, "all")
for tab, source in zip(tabs[1:], sources):
    with tab:
        render_source_tab(products[products["Source_Group"].astype(str) == source], source)
