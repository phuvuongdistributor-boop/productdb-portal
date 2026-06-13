from __future__ import annotations

import os
import json
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MASTER_DB_PATH = PROJECT_ROOT / "master_v2" / "MASTER_DB.xlsx"
DATA_STATUS_PATH = PROJECT_ROOT / "config" / "portal_data_status.json"


@st.cache_data(show_spinner=False)
def _read_master(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    frame = pd.read_excel(path, sheet_name="MASTER_DB")
    return frame.fillna("")


def load_products() -> pd.DataFrame:
    if os.getenv("PRODUCTDB_DATA_SOURCE", "local").strip().lower() == "drive":
        try:
            from .drive_loader import load_products_from_drive
        except ImportError:
            from drive_loader import load_products_from_drive
        return load_products_from_drive()
    if not MASTER_DB_PATH.exists():
        raise FileNotFoundError(
            f"Missing {MASTER_DB_PATH}. Run: python portal_v2/build_master_db.py"
        )
    return _read_master(str(MASTER_DB_PATH), MASTER_DB_PATH.stat().st_mtime_ns)


def load_data_status() -> dict:
    if not DATA_STATUS_PATH.exists():
        return {"source": "Local MASTER_DB.xlsx"}
    with DATA_STATUS_PATH.open(encoding="utf-8") as status_file:
        return json.load(status_file)


def find_product(code: str) -> pd.Series | None:
    products = load_products()
    matches = products[products["Code"].astype(str).str.casefold() == str(code).casefold()]
    return None if matches.empty else matches.iloc[0]


def resolve_image_source(value: object) -> str | Path | None:
    source = str(value or "").strip()
    if not source:
        return None
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return source
    local_path = Path(source)
    candidates = [local_path, PROJECT_ROOT / local_path, PROJECT_ROOT.parent / local_path]
    return next((path for path in candidates if path.is_file()), None)


def count_products_with_images(products: pd.DataFrame) -> int:
    return sum(resolve_image_source(value) is not None for value in products["Image_URL"])
