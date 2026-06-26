from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from zipfile import ZipFile
import re

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MASTER_DB_PATH = PROJECT_ROOT / "master_v2" / "MASTER_DB.xlsx"
DATA_STATUS_PATH = PROJECT_ROOT / "config" / "portal_data_status.json"
BUNDLED_DATA_PATH = PROJECT_ROOT / "deployment" / "productdb_data_bundle.zip"
BUNDLED_DATA_MARKER = PROJECT_ROOT / ".productdb_data_bundle"
LAST_DATA_SOURCE = "Local MASTER_DB.xlsx"
IMAGE_BUNDLE_RETRY_DONE = False
LAST_BUNDLE_PATH: Path | None = None


def _data_source_mode() -> str:
    return os.getenv("PRODUCTDB_DATA_SOURCE", "drive").strip().lower()


DRIVE_HEALTH = {
    "mode": _data_source_mode(),
    "sheet_ok": None,
    "sheet_message": "Google Sheet has not been checked.",
    "bundle_ok": None,
    "bundle_message": "Image bundle has not been checked.",
}


def drive_health() -> dict:
    return dict(DRIVE_HEALTH)


def _allow_local_fallback() -> bool:
    return os.getenv("PRODUCTDB_ALLOW_LOCAL_FALLBACK", "").strip().lower() in {"1", "true", "yes"}


def _expected_master_rows() -> int | None:
    config_path = PROJECT_ROOT / "config" / "drive_config.json"
    if not config_path.is_file():
        return None
    try:
        with config_path.open(encoding="utf-8") as config_file:
            value = json.load(config_file).get("master_live", {}).get("rows")
        return int(value) if value else None
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _read_local_fallback_master() -> pd.DataFrame:
    products = _read_master(str(MASTER_DB_PATH), MASTER_DB_PATH.stat().st_mtime_ns)
    expected_rows = _expected_master_rows()
    if expected_rows is not None and len(products) != expected_rows:
        raise RuntimeError(
            f"Local fallback MASTER_DB has {len(products):,} rows, "
            f"but Drive config expects {expected_rows:,}. Refusing stale fallback."
        )
    return products


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
    global LAST_BUNDLE_PATH
    file_id = str(bundle_config.get("file_id", "")).strip()
    if not file_id or _data_source_mode() != "drive":
        DRIVE_HEALTH["bundle_ok"] = None
        DRIVE_HEALTH["bundle_message"] = "Drive image bundle download is not configured."
        return None
    runtime_bundle = Path(os.getenv("PRODUCTDB_BUNDLE_PATH", "/tmp/productdb_data_bundle.zip"))
    marker = PROJECT_ROOT / ".productdb_drive_bundle"
    marker.unlink(missing_ok=True)
    try:
        try:
            from .drive_loader import _credentials
        except ImportError:
            from drive_loader import _credentials
        from google.auth.transport.requests import AuthorizedSession
    except Exception as error:
        DRIVE_HEALTH["bundle_ok"] = False
        DRIVE_HEALTH["bundle_message"] = f"Missing dependency/credential for Drive image bundle: {error}"
        return None
    try:
        endpoint = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"
        response = AuthorizedSession(_credentials()).get(endpoint, timeout=120)
        if not response.ok:
            detail = response.text[:1000]
            raise RuntimeError(f"HTTP {response.status_code}: {detail}")
        runtime_bundle.write_bytes(response.content)
        LAST_BUNDLE_PATH = runtime_bundle
        marker.write_text(file_id, encoding="utf-8")
        DRIVE_HEALTH["bundle_ok"] = True
        DRIVE_HEALTH["bundle_message"] = f"Downloaded image bundle from Drive: {file_id}"
        print(f"ProductDB bundle: downloaded Drive bundle {file_id} to {runtime_bundle}", flush=True)
        return runtime_bundle
    except Exception as error:
        DRIVE_HEALTH["bundle_ok"] = False
        DRIVE_HEALTH["bundle_message"] = f"Could not download image bundle from Drive: {error}"
        print(f"ProductDB bundle: Drive download failed: {error}", flush=True)
    try:
        public_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        request = Request(public_url, headers={"User-Agent": "ProductDB-V2/1.0"})
        with urlopen(request, timeout=120) as response:
            payload = response.read()
        if len(payload) < 1024 or payload[:64].lower().startswith(b"<!doctype html"):
            raise RuntimeError("Drive public download did not return a zip payload.")
        runtime_bundle.write_bytes(payload)
        LAST_BUNDLE_PATH = runtime_bundle
        marker.write_text(file_id, encoding="utf-8")
        DRIVE_HEALTH["bundle_ok"] = True
        DRIVE_HEALTH["bundle_message"] = f"Downloaded image bundle from Drive public URL: {file_id}"
        print(f"ProductDB bundle: downloaded public Drive bundle {file_id} to {runtime_bundle}", flush=True)
        return runtime_bundle
    except Exception as public_error:
        DRIVE_HEALTH["bundle_ok"] = False
        DRIVE_HEALTH["bundle_message"] = f"Could not download image bundle from Drive: {public_error}"
        print(f"ProductDB bundle: public Drive download failed: {public_error}", flush=True)
        return None


def _install_bundled_data() -> None:
    global LAST_BUNDLE_PATH
    drive_bundle_path = _download_drive_bundle(_load_drive_bundle_config())
    if drive_bundle_path is not None:
        bundle_path = drive_bundle_path
    elif BUNDLED_DATA_PATH.is_file():
        bundle_path = BUNDLED_DATA_PATH
        if _data_source_mode() == "drive":
            DRIVE_HEALTH["bundle_ok"] = False
            previous_message = DRIVE_HEALTH.get("bundle_message") or "Drive image bundle was not downloaded."
            DRIVE_HEALTH["bundle_message"] = f"{previous_message} Falling back to local deploy bundle."
            print("ProductDB bundle: falling back to local deploy bundle in drive mode", flush=True)
        else:
            DRIVE_HEALTH["bundle_ok"] = True
            DRIVE_HEALTH["bundle_message"] = "Using the local image/data bundle included in this deploy."
            print("ProductDB bundle: using local deploy bundle", flush=True)
    else:
        bundle_path = None
    if bundle_path is None or not bundle_path.is_file():
        return
    LAST_BUNDLE_PATH = bundle_path
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


def _extract_bundle_member(relative_path: Path) -> Path | None:
    parts = relative_path.parts
    if not parts or parts[0] not in {"master_v2", "GHE_NHAP", "assets"} or ".." in parts:
        return None
    member_name = relative_path.as_posix()
    bundle_path = LAST_BUNDLE_PATH
    if bundle_path is None or not bundle_path.is_file():
        bundle_path = _download_drive_bundle(_load_drive_bundle_config())
    if (bundle_path is None or not bundle_path.is_file()) and BUNDLED_DATA_PATH.is_file():
        bundle_path = BUNDLED_DATA_PATH
    if bundle_path is None or not bundle_path.is_file():
        return None
    try:
        with ZipFile(bundle_path) as archive:
            if member_name not in archive.namelist():
                if _data_source_mode() == "drive":
                    refreshed = _download_drive_bundle(_load_drive_bundle_config())
                    if refreshed is not None and refreshed.is_file() and refreshed != bundle_path:
                        bundle_path = refreshed
                    else:
                        return None
                    with ZipFile(bundle_path) as refreshed_archive:
                        if member_name not in refreshed_archive.namelist():
                            return None
                        refreshed_archive.extract(member_name, PROJECT_ROOT)
                    extracted = PROJECT_ROOT / relative_path
                    return extracted if extracted.is_file() else None
                return None
            archive.extract(member_name, PROJECT_ROOT)
    except Exception:
        return None
    extracted = PROJECT_ROOT / relative_path
    return extracted if extracted.is_file() else None


_install_bundled_data()


@st.cache_data(show_spinner=False)
def _read_master(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    workbook = pd.ExcelFile(path)
    sheet_name = "MASTER_DB" if "MASTER_DB" in workbook.sheet_names else workbook.sheet_names[0]
    frame = pd.read_excel(workbook, sheet_name=sheet_name)
    return frame.fillna("")


def load_products() -> pd.DataFrame:
    global LAST_DATA_SOURCE
    if _data_source_mode() == "drive":
        try:
            from .drive_loader import load_products_from_drive
        except ImportError:
            from drive_loader import load_products_from_drive
        try:
            products = load_products_from_drive()
            LAST_DATA_SOURCE = "Google Sheets MASTER_DB"
            DRIVE_HEALTH["sheet_ok"] = True
            DRIVE_HEALTH["sheet_message"] = f"Read Google Sheet LIVE: {len(products):,} rows."
            return products
        except Exception as error:
            DRIVE_HEALTH["sheet_ok"] = False
            DRIVE_HEALTH["sheet_message"] = f"Could not read Google Sheet LIVE: {error}"
            if not _allow_local_fallback():
                raise RuntimeError(DRIVE_HEALTH["sheet_message"]) from error
            if not MASTER_DB_PATH.exists():
                raise
            LAST_DATA_SOURCE = "Local MASTER_DB.xlsx (Drive fallback)"
            return _read_local_fallback_master()
    if not MASTER_DB_PATH.exists():
        raise FileNotFoundError(
            f"Missing {MASTER_DB_PATH}. Run: python portal_v2/build_master_db.py"
        )
    return _read_master(str(MASTER_DB_PATH), MASTER_DB_PATH.stat().st_mtime_ns)


def load_products_or_stop() -> pd.DataFrame:
    try:
        return load_products()
    except (FileNotFoundError, RuntimeError) as error:
        st.error(str(error))
        st.stop()


def load_data_status() -> dict:
    if _data_source_mode() == "drive":
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
    global IMAGE_BUNDLE_RETRY_DONE
    source = str(value or "").strip()
    if not source:
        return None
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return source
    local_path = Path(source)
    candidates = [local_path, PROJECT_ROOT / local_path, PROJECT_ROOT.parent / local_path]
    found = next((path for path in candidates if path.is_file()), None)
    if found is not None:
        return found
    if not IMAGE_BUNDLE_RETRY_DONE:
        IMAGE_BUNDLE_RETRY_DONE = True
        _install_bundled_data()
        found = next((path for path in candidates if path.is_file()), None)
        if found is not None:
            return found
    if not local_path.is_absolute():
        found = _extract_bundle_member(local_path)
        if found is not None:
            return found
    return None


def _safe_segment(value: object) -> str:
    text = str(value or "").strip()
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")


def _split_image_values(value: object) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"[\n;|]+", text) if part.strip()]


def resolve_product_images(product: object) -> list[str | Path]:
    try:
        image_value = product.get("Image_URL", "")
        code = _safe_segment(product.get("Code", ""))
        source_group = _safe_segment(product.get("Source_Group", "")).lower()
    except AttributeError:
        image_value = ""
        code = ""
        source_group = ""

    images: list[str | Path] = []
    seen: set[str] = set()

    def add_image(candidate: str | Path | None) -> None:
        if not candidate:
            return
        key = str(candidate)
        if key in seen:
            return
        seen.add(key)
        images.append(candidate)

    for value in _split_image_values(image_value):
        add_image(resolve_image_source(value))

    image_roots = [
        PROJECT_ROOT / "assets" / "product_images_multi" / source_group / code,
    ]
    for root in image_roots:
        if not code or not source_group or not root.is_dir():
            continue
        for path in sorted(root.iterdir()):
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                add_image(path)
    return images


def count_products_with_images(products: pd.DataFrame) -> int:
    return sum(resolve_image_source(value) is not None for value in products["Image_URL"])


def unresolved_image_rows(products: pd.DataFrame) -> pd.DataFrame:
    if "Image_URL" not in products:
        return products.iloc[0:0].copy()
    image_values = products["Image_URL"].astype(str).str.strip()
    unresolved_mask = image_values.ne("") & products["Image_URL"].map(lambda value: resolve_image_source(value) is None)
    return products[unresolved_mask].copy()
