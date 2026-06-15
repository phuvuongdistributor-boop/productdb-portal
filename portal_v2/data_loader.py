from __future__ import annotations

import os
import json
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MASTER_DB_PATH = PROJECT_ROOT / "master_v2" / "MASTER_DB.xlsx"
DATA_STATUS_PATH = PROJECT_ROOT / "config" / "portal_data_status.json"
BUNDLED_DATA_PATH = PROJECT_ROOT / "deployment" / "productdb_data_bundle.zip"
BUNDLED_DATA_MARKER = PROJECT_ROOT / ".productdb_data_bundle"
LAST_DATA_SOURCE = "Local MASTER_DB.xlsx"


def _install_bundled_data() -> None:
    if not BUNDLED_DATA_PATH.is_file():
        return
    signature = f"{BUNDLED_DATA_PATH.stat().st_size}:{BUNDLED_DATA_PATH.stat().st_mtime_ns}"
    if BUNDLED_DATA_MARKER.is_file() and BUNDLED_DATA_MARKER.read_text(encoding="utf-8") == signature:
        return
    allowed_roots = {"master_v2", "GHE_NHAP", "assets"}
    with ZipFile(BUNDLED_DATA_PATH) as archive:
        for member in archive.infolist():
            parts = Path(member.filename).parts
            if not parts or parts[0] not in allowed_roots or ".." in parts:
                continue
            archive.extract(member, PROJECT_ROOT)
    BUNDLED_DATA_MARKER.write_text(signature, encoding="utf-8")


_install_bundled_data()


@st.cache_data(show_spinner=False)
def _read_master(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    frame = pd.read_excel(path, sheet_name="MASTER_DB")
    return frame.fillna("")


def load_products() -> pd.DataFrame:
    global LAST_DATA_SOURCE
    if os.getenv("PRODUCTDB_DATA_SOURCE", "local").strip().lower() == "drive":
        try:
            from .drive_loader import load_products_from_drive
        except ImportError:
            from drive_loader import load_products_from_drive
        try:
            products = load_products_from_drive()
            LAST_DATA_SOURCE = "Google Sheets MASTER_DB"
            return products
        except Exception:
            if not MASTER_DB_PATH.exists():
                raise
            LAST_DATA_SOURCE = "Local MASTER_DB.xlsx (Drive fallback)"
            return _read_master(str(MASTER_DB_PATH), MASTER_DB_PATH.stat().st_mtime_ns)
    if not MASTER_DB_PATH.exists():
        raise FileNotFoundError(
            f"Missing {MASTER_DB_PATH}. Run: python portal_v2/build_master_db.py"
        )
    return _read_master(str(MASTER_DB_PATH), MASTER_DB_PATH.stat().st_mtime_ns)


def load_data_status() -> dict:
    if os.getenv("PRODUCTDB_DATA_SOURCE", "local").strip().lower() == "drive":
        return {"source": LAST_DATA_SOURCE}
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
