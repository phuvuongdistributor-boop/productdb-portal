from __future__ import annotations

import streamlit as st

from ui import source_label


FILTER_COLUMNS = ["Source_Group", "Category", "SubCategory", "Material"]


def apply_filters(products):
    filtered = products
    columns = st.columns(4)
    for container, column in zip(columns, FILTER_COLUMNS):
        options = sorted(value for value in products[column].astype(str).unique() if value.strip())
        selected = container.multiselect(
            column.replace("_", " "),
            options,
            format_func=source_label if column == "Source_Group" else str,
        )
        if selected:
            filtered = filtered[filtered[column].astype(str).isin(selected)]
    return filtered
