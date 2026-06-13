from __future__ import annotations

import streamlit as st


CART_KEY = "quotation_cart"


def get_cart() -> dict[str, dict]:
    cart = st.session_state.setdefault(CART_KEY, {})
    for item in cart.values():
        item.setdefault("BasePrice", item.get("SalePrice", 0))
        item.setdefault("UnitPrice", item.get("SalePrice", 0))
        item.setdefault("ItemNote", "")
        item.setdefault("Image_URL", "")
    return cart


def add_product(product, quantity: int = 1) -> None:
    cart = get_cart()
    key = str(product.name)
    if key in cart:
        cart[key]["Quantity"] += quantity
        return
    cart[key] = {
        "Row_ID": key,
        "Code": str(product.get("Code", "")),
        "ProductName": str(product.get("ProductName", "")),
        "Size": str(product.get("Size", "")),
        "Material": str(product.get("Material", "")),
        "SalePrice": product.get("SalePrice", 0),
        "BasePrice": product.get("SalePrice", 0),
        "UnitPrice": product.get("SalePrice", 0),
        "Hotline": str(product.get("Hotline", "")),
        "Source_URL": str(product.get("Source_URL", "")),
        "Image_URL": str(product.get("Image_URL", "")),
        "Quantity": quantity,
        "Discount": 0.0,
        "ItemNote": "",
    }


def remove_product(key: str) -> None:
    get_cart().pop(str(key), None)


def clear_cart() -> None:
    st.session_state[CART_KEY] = {}


def cart_count() -> int:
    return sum(int(item.get("Quantity", 0)) for item in get_cart().values())
