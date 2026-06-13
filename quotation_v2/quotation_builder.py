from __future__ import annotations

from portal_v2.data_loader import load_products


def build_quotation(codes: list[str]):
    products = load_products()
    normalized = {str(code).casefold() for code in codes}
    return products[products["Code"].astype(str).str.casefold().isin(normalized)].copy()
