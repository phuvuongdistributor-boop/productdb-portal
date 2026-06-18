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


def _load_drive_bundle_config() -> dict:
    config_path = PROJECT_ROOT / "config" / "drive_config.json"
    if not config_path.is_file():
        return {}
    try:
        with config_path.open(encoding="utf-8") as config_file:
            return json.load(config_file).get("data_bundle", {})
    except (OSError, json.JSONDecodeError):
        return {}


def _download_drive_bundle(bundle_config: dict) -> Path | None:
    file_id = str(bundle_config.get("file_id", "")).strip()
    if not file_id or os.getenv("PRODUCTDB_DATA_SOURCE", "local").strip().lower() != "drive":
        return None
    marker = PROJECT_ROOT / ".productdb_drive_bundle"
    if marker.is_file() and marker.read_text(encoding="utf-8").strip() == file_id:
        return None
    try:
        try:
            from .drive_loader import _credentials
        except ImportError:
            from drive_loader import _credentials
        from google.auth.transport.requests import AuthorizedSession
    except Exception:
        return None
    try:
        endpoint = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        response = AuthorizedSession(_credentials()).get(endpoint, timeout=120)
        response.raise_for_status()
        runtime_bundle = Path(os.getenv("PRODUCTDB_BUNDLE_PATH", "/tmp/productdb_data_bundle.zip"))
        runtime_bundle.write_bytes(response.content)
        marker.write_text(file_id, encoding="utf-8")
        return runtime_bundle
    except Exception:
        return None


def _install_bundled_data() -> None:
    drive_bundle_path = _download_drive_bundle(_load_drive_bundle_config())
    bundle_path = drive_bundle_path or BUNDLED_DATA_PATH
    if not bundle_path.is_file():
        return
    signature = f"{bundle_path.stat().st_size}:{bundle_path.stat().st_mtime_ns}"
    if BUNDLED_DATA_MARKER.is_file() and BUNDLED_DATA_MARKER.read_text(encoding="utf-8") == signature:
        return
    allowed_roots = {"master_v2", "GHE_NHAP", "assets"}
    with ZipFile(bundle_path) as archive:
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
