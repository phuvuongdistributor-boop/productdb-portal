from __future__ import annotations

import pandas as pd
import streamlit as st

from auth import require_auth
from cart import CART_KEY
from quotation_v2.quotation_service import (
    STATUSES,
    duplicate_quotation,
    list_quotations,
    update_status,
)
from ui import apply_theme


def money(value: object) -> str:
    try:
        return f"{float(value):,.0f} đ".replace(",", ".")
    except (TypeError, ValueError):
        return "0 đ"


def open_record(record: dict) -> None:
    customer = record.get("Customer", {})
    st.session_state[CART_KEY] = {
        str(item.get("Row_ID", index)): item
        for index, item in enumerate(record.get("Items", []))
    }
    st.session_state["quotation_customer"] = customer
    st.session_state["active_quotation_id"] = record.get("QuotationID", "")
    st.session_state["quotation_salesperson"] = record.get("Salesperson", "")
    st.session_state["quotation_owner_username"] = record.get("OwnerUsername", "")
    st.session_state["quotation_status"] = record.get("Status", "DRAFT")
    st.session_state["customer_name"] = customer.get("Name", "")
    st.session_state["customer_phone"] = customer.get("Phone", "")
    st.session_state["customer_channel"] = customer.get("Channel", "Direct")
    st.session_state["customer_notes"] = customer.get("Notes", "")
    st.session_state["salesperson_input"] = record.get("Salesperson", "")
    st.session_state["owner_username_input"] = record.get("OwnerUsername", "")
    st.session_state["status_input"] = record.get("Status", "DRAFT")


st.set_page_config(page_title="Quản lý báo giá | ProductDB V2", layout="wide")
apply_theme()
user = require_auth()
st.title("Quản lý báo giá")
records = list_quotations()
if user["role"] == "sale":
    records = [record for record in records if record.get("OwnerUsername") == user["username"]]

if not records:
    st.info("Chưa có báo giá đã lưu.")
    st.page_link("pages/quotation.py", label="Tạo báo giá đầu tiên")
    st.stop()

status_filter, salesperson_filter, search_filter = st.columns([1, 1.2, 2])
selected_status = status_filter.multiselect("Trạng thái", STATUSES)
salespeople = sorted({str(record.get("Salesperson", "")).strip() for record in records if record.get("Salesperson")})
selected_salespeople = salesperson_filter.multiselect("Sale phụ trách", salespeople)
query = search_filter.text_input("Tìm mã, khách hàng hoặc số điện thoại")

filtered = records
if selected_status:
    filtered = [record for record in filtered if record.get("Status") in selected_status]
if selected_salespeople:
    filtered = [record for record in filtered if record.get("Salesperson") in selected_salespeople]
if query.strip():
    needle = query.casefold().strip()
    filtered = [
        record for record in filtered
        if needle in " ".join([
            str(record.get("QuotationID", "")),
            str(record.get("Customer", {}).get("Name", "")),
            str(record.get("Customer", {}).get("Phone", "")),
        ]).casefold()
    ]

summary = pd.DataFrame([
    {
        "Mã báo giá": record.get("QuotationID", ""),
        "Khách hàng": record.get("Customer", {}).get("Name", ""),
        "Điện thoại": record.get("Customer", {}).get("Phone", ""),
        "Sale": record.get("Salesperson", ""),
        "Trạng thái": record.get("Status", ""),
        "Tổng tiền": record.get("GrandTotal", 0),
        "Cập nhật": record.get("UpdatedAt", ""),
    }
    for record in filtered
])
st.caption(f"{len(filtered)} / {len(records)} báo giá")
if not summary.empty:
    st.dataframe(summary, width="stretch", hide_index=True)

st.subheader("Thao tác")
for record in filtered:
    quotation_id = record.get("QuotationID", "")
    customer = record.get("Customer", {})
    with st.container(border=True):
        info, status_column, actions = st.columns([3.4, 1.4, 2.2])
        info.markdown(f"**{quotation_id}** · {customer.get('Name', '')} · {customer.get('Phone', '')}")
        info.caption(
            f"Sale: {record.get('Salesperson') or 'Chưa gán'} | "
            f"{len(record.get('Items', []))} dòng | {money(record.get('GrandTotal', 0))}"
        )
        current_status = record.get("Status", "DRAFT")
        new_status = status_column.selectbox(
            "Trạng thái", STATUSES,
            index=STATUSES.index(current_status) if current_status in STATUSES else 0,
            key=f"status-{quotation_id}",
        )
        if new_status != current_status:
            update_status(quotation_id, new_status)
            st.rerun()
        open_col, duplicate_col = actions.columns(2)
        if open_col.button("Mở / sửa", key=f"open-{quotation_id}", width="stretch"):
            open_record(record)
            st.switch_page("pages/quotation.py")
        if duplicate_col.button("Nhân bản", key=f"duplicate-{quotation_id}", width="stretch"):
            duplicate = duplicate_quotation(quotation_id)
            open_record(duplicate)
            st.switch_page("pages/quotation.py")
