from __future__ import annotations

from datetime import datetime
import json
import pandas as pd
import streamlit as st

from auth import list_users, require_auth
from cart import add_product, cart_count, clear_cart, get_cart, remove_product
from data_loader import load_products
from quotation_v2.exporters import export_excel, export_pdf, export_png
from quotation_v2.quotation_service import STATUSES, save_quotation
from ui import apply_theme


def money(value: object) -> str:
    try:
        return f"{float(value):,.0f} đ".replace(",", ".")
    except (TypeError, ValueError):
        return "0 đ"


def quotation_frame(cart: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for item in cart.values():
        price = float(item.get("UnitPrice", item.get("SalePrice")) or 0)
        quantity = int(item.get("Quantity") or 1)
        discount = float(item.get("Discount") or 0)
        total = price * quantity * (1 - discount / 100)
        rows.append({**item, "LineTotal": total})
    return pd.DataFrame(rows)


def save_lead(customer: dict[str, str], interest: str) -> None:
    from lead_management.lead_service import save_lead as persist_lead

    persist_lead(
        {
            "CreatedAt": datetime.now().isoformat(timespec="seconds"),
            "Name": customer["Name"],
            "Phone": customer["Phone"],
            "Channel": customer["Channel"],
            "Interest": interest,
            "Status": "NEW",
            "Notes": customer["Notes"],
        }
    )


st.set_page_config(page_title="Báo giá | ProductDB V2", layout="wide")
apply_theme()
user = require_auth()
st.title("Tạo báo giá")
active_quotation_id = st.session_state.get("active_quotation_id", "")
if active_quotation_id:
    st.caption(f"Đang chỉnh sửa: {active_quotation_id}")
manager_col, new_col = st.columns([1, 1])
manager_col.page_link("pages/quotations.py", label="Quản lý báo giá")
if new_col.button("Tạo báo giá mới"):
    clear_cart()
    for key in [
        "quotation_customer", "active_quotation_id", "quotation_salesperson", "quotation_status",
        "customer_name", "customer_phone", "customer_channel", "customer_notes",
        "salesperson_input", "status_input",
        "quotation_owner_username", "owner_username_input",
    ]:
        st.session_state.pop(key, None)
    st.rerun()
products = load_products()
cart = get_cart()
for item in cart.values():
    if not item.get("Image_URL"):
        try:
            row_id = int(item.get("Row_ID", -1))
            if row_id in products.index:
                item["Image_URL"] = str(products.loc[row_id].get("Image_URL", ""))
        except (TypeError, ValueError):
            pass

with st.expander("Thêm sản phẩm nhanh", expanded=not bool(cart)):
    labels = products.apply(lambda row: f"{row['Code']} | {row['ProductName']}", axis=1)
    selected_label = st.selectbox("Sản phẩm", [""] + labels.tolist())
    if st.button("Thêm sản phẩm đã chọn", disabled=not selected_label):
        selected_index = labels[labels == selected_label].index[0]
        add_product(products.loc[selected_index])
        st.rerun()

st.caption(f"Giỏ báo giá hiện có {cart_count()} sản phẩm")
if not cart:
    st.info("Chưa có sản phẩm. Hãy thêm từ trang tìm kiếm hoặc chọn nhanh ở trên.")
    st.page_link("pages/search.py", label="Đi tới tìm kiếm sản phẩm")
    st.stop()

st.subheader("Sản phẩm và giá sale")
remove_keys = []
with st.form("quotation-lines"):
    for key, item in list(cart.items()):
        item.setdefault("BasePrice", item.get("SalePrice", 0))
        item.setdefault("UnitPrice", item.get("SalePrice", 0))
        item.setdefault("ItemNote", "")
        cols = st.columns([1.1, 2.5, 1.35, 1.35, .8, .9, .6])
        cols[0].markdown(f"**{item['Code']}**")
        cols[1].write(item["ProductName"])
        cols[2].caption(f"Giá dữ liệu: {money(item['BasePrice'])}")
        item["UnitPrice"] = cols[3].number_input(
            "Đơn giá sale", min_value=0.0, value=float(item["UnitPrice"]),
            step=10000.0, key=f"price-{key}"
        )
        item["Quantity"] = cols[4].number_input(
            "SL", min_value=1, value=int(item["Quantity"]), key=f"qty-{key}"
        )
        item["Discount"] = cols[5].number_input(
            "CK %", min_value=0.0, max_value=100.0,
            value=float(item["Discount"]), step=1.0, key=f"discount-{key}"
        )
        if cols[6].checkbox("Xóa", key=f"remove-{key}"):
            remove_keys.append(key)
        item["ItemNote"] = st.text_input(
            "Ghi chú sản phẩm",
            value=str(item.get("ItemNote", "")),
            placeholder="Ví dụ: đổi màu, thay kích thước, giao tầng 2...",
            key=f"note-{key}",
        )
        st.divider()
    update_lines = st.form_submit_button("Cập nhật giá & ghi chú", type="primary")

if update_lines:
    for key in remove_keys:
        remove_product(key)
    st.rerun()

quotation = quotation_frame(cart)
base_total = (quotation["BasePrice"].astype(float) * quotation["Quantity"]).sum()
subtotal = (quotation["UnitPrice"].astype(float) * quotation["Quantity"]).sum()
grand_total = quotation["LineTotal"].sum()
summary_left, summary_right = st.columns([2.7, 1.3])
summary_right.metric("Tổng theo giá dữ liệu", money(base_total))
summary_right.metric("Tạm tính", money(subtotal))
summary_right.metric("Tổng sau chiết khấu", money(grand_total))

st.subheader("Thông tin khách hàng")
existing_customer = st.session_state.get("quotation_customer", {})
saved_salesperson = st.session_state.get("quotation_salesperson", user["display_name"])
saved_owner_username = st.session_state.get("quotation_owner_username", user["username"])
saved_status = st.session_state.get("quotation_status", "DRAFT")
st.session_state.setdefault("customer_name", existing_customer.get("Name", ""))
st.session_state.setdefault("customer_phone", existing_customer.get("Phone", ""))
st.session_state.setdefault("customer_channel", existing_customer.get("Channel", "Direct"))
st.session_state.setdefault("customer_notes", existing_customer.get("Notes", ""))
st.session_state.setdefault("salesperson_input", saved_salesperson)
st.session_state.setdefault("owner_username_input", saved_owner_username)
st.session_state.setdefault("status_input", saved_status)
with st.form("customer-form"):
    name = st.text_input("Tên khách hàng / công ty", key="customer_name")
    phone = st.text_input("Số điện thoại", key="customer_phone")
    channels = ["Direct", "Facebook", "Zalo", "Google/SEO", "Khác"]
    if st.session_state["customer_channel"] not in channels:
        st.session_state["customer_channel"] = "Direct"
    channel = st.selectbox("Kênh", channels, key="customer_channel")
    if user["role"] == "admin":
        assignable_users = [account for account in list_users() if account.get("active")]
        owner_options = [account["username"] for account in assignable_users]
        owner_labels = {account["username"]: account["display_name"] for account in assignable_users}
        if st.session_state["owner_username_input"] not in owner_options:
            st.session_state["owner_username_input"] = user["username"]
        owner_username = st.selectbox(
            "Sale phụ trách", owner_options,
            format_func=lambda username: f"{owner_labels[username]} ({username})",
            key="owner_username_input",
        )
        salesperson = owner_labels[owner_username]
    else:
        owner_username = user["username"]
        salesperson = user["display_name"]
        st.text_input("Sale phụ trách", value=salesperson, disabled=True)
    if st.session_state["status_input"] not in STATUSES:
        st.session_state["status_input"] = "DRAFT"
    status = st.selectbox(
        "Trạng thái báo giá", STATUSES, key="status_input",
    )
    notes = st.text_area(
        "Ghi chú đơn hàng",
        key="customer_notes",
        placeholder="Yêu cầu giao hàng, xuất hóa đơn, màu sắc, thời hạn báo giá...",
    )
    prepare = st.form_submit_button("Lưu & chuẩn bị báo giá", type="primary")

if prepare:
    if not name.strip() or not phone.strip():
        st.error("Vui lòng nhập tên khách hàng và số điện thoại.")
    else:
        customer = {"Name": name.strip(), "Phone": phone.strip(), "Channel": channel, "Notes": notes.strip()}
        st.session_state["quotation_customer"] = customer
        st.session_state["quotation_salesperson"] = salesperson.strip()
        st.session_state["quotation_owner_username"] = owner_username
        st.session_state["quotation_status"] = status
        items = json.loads(quotation_frame(cart).to_json(orient="records", force_ascii=False))
        saved_record = save_quotation(
            {
                "QuotationID": active_quotation_id,
                "Customer": customer,
                "Salesperson": salesperson.strip(),
                "OwnerUsername": owner_username,
                "Status": status,
                "Items": items,
                "BaseTotal": float(base_total),
                "Subtotal": float(subtotal),
                "GrandTotal": float(grand_total),
            }
        )
        st.session_state["active_quotation_id"] = saved_record["QuotationID"]
        if not active_quotation_id:
            save_lead(customer, ", ".join(quotation["Code"].astype(str).tolist()))
        st.success(f"Đã lưu báo giá {saved_record['QuotationID']} và chuẩn bị file gửi khách.")

customer = st.session_state.get("quotation_customer")
if customer:
    current_quotation = quotation_frame(cart)
    safe_name = customer['Name'].replace(' ', '_')
    filename = f"Bao_gia_{safe_name}_{datetime.now():%Y%m%d}"
    st.subheader("Xuất báo giá gửi khách")
    excel_col, pdf_col, png_col = st.columns(3)
    excel_col.download_button(
        "Tải Excel có ảnh", data=export_excel(customer, current_quotation),
        file_name=f"{filename}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary", width="stretch",
    )
    pdf_col.download_button(
        "Tải PDF", data=export_pdf(customer, current_quotation),
        file_name=f"{filename}.pdf", mime="application/pdf", width="stretch",
    )
    png_col.download_button(
        "Tải PNG", data=export_png(customer, current_quotation),
        file_name=f"{filename}.png", mime="image/png", width="stretch",
    )

if st.button("Xóa toàn bộ giỏ báo giá"):
    clear_cart()
    for key in [
        "quotation_customer", "active_quotation_id", "quotation_salesperson", "quotation_status",
        "customer_name", "customer_phone", "customer_channel", "customer_notes",
        "salesperson_input", "status_input",
        "quotation_owner_username", "owner_username_input",
    ]:
        st.session_state.pop(key, None)
    st.rerun()
