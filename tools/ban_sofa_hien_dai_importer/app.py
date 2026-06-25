from __future__ import annotations

import io
import os
import re
import shutil
import time
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from PIL import Image

try:
    import rarfile
except Exception:  # pragma: no cover
    rarfile = None

try:
    import imagehash
except Exception:  # pragma: no cover
    imagehash = None


SOURCE_NAME = "BÀN SOFA HIỆN ĐẠI"
UPLOAD_DIR = Path("uploads/ban_sofa_hien_dai")
OUTPUT_XLSX = "MASTER_IMPORT_BAN_SOFA_HIEN_DAI.xlsx"
OUTPUT_REPORT = "IMPORT_REPORT.txt"
SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_ARCHIVES = {".zip", ".rar"}

MASTER_COLUMNS = [
    "Code",
    "ProductName",
    "Size",
    "Category",
    "Variant",
    "BasePrice",
    "SaleFactor",
    "SalePrice",
    "Status",
    "Search_URL",
    "Search_Keyword",
    "Material",
    "SubCategory",
    "Description",
    "CatalogPrice",
    "Price_Mode",
    "Hotline",
    "Template_ID",
    "TheOne_URL",
    "Image_Status",
    "Image_URL",
    "Image_Source",
    "Harvest_Status",
]


@dataclass
class ImageRecord:
    original_filename: str
    saved_filename: str
    local_path: str
    extension: str
    source_type: str
    image_type: str = "unknown"
    confidence: float = 0.0
    review_note: str = ""
    perceptual_hash: str = ""
    raw_ocr_text: str = ""


@dataclass
class TableRow:
    source_image: str
    row_index: int
    Code: str = ""
    ProductName: str = ""
    BasePrice: str = ""
    Size: str = ""
    Material: str = ""
    Description: str = ""
    raw_text: str = ""
    confidence: float = 0.0
    review_note: str = ""


def safe_name(filename: str) -> str:
    base = Path(filename).name.replace("\\", "_").replace("/", "_").strip()
    return base or f"image_{int(time.time())}.jpg"


def unique_path(directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    filename = safe_name(filename)
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    idx = 2
    while True:
        candidate = directory / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def save_image_bytes(data: bytes, filename: str, source_type: str) -> ImageRecord | None:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_IMAGES:
        return None
    dest = unique_path(UPLOAD_DIR, filename)
    dest.write_bytes(data)
    rel = dest.as_posix()
    rec = ImageRecord(
        original_filename=filename,
        saved_filename=dest.name,
        local_path=rel,
        extension=ext,
        source_type=source_type,
    )
    rec.perceptual_hash = compute_image_hash(dest)
    rec.image_type, rec.confidence, rec.review_note = classify_image(dest)
    return rec


def compute_image_hash(path: Path) -> str:
    if imagehash is None:
        return ""
    try:
        with Image.open(path) as img:
            return str(imagehash.phash(img.convert("RGB")))
    except Exception:
        return ""


def classify_image(path: Path) -> tuple[str, float, str]:
    """Lightweight image-type heuristic. Vision/OCR provider can improve this later."""
    try:
        with Image.open(path) as img:
            width, height = img.size
            aspect = width / max(height, 1)
            area = width * height
        name = path.name.lower()
        if any(k in name for k in ["bang", "bảng", "gia", "giá", "price", "bao-gia", "baogia"]):
            return "price_table_image", 0.75, "classified by filename hint"
        if aspect > 1.8 and area > 700_000:
            return "composite_image", 0.55, "wide image, possible composite/catalog"
        if aspect < 0.45 or aspect > 3.0:
            return "unknown", 0.35, "unusual aspect ratio"
        return "single_product_image", 0.45, "default image heuristic; needs OCR/vision confirmation"
    except Exception as exc:
        return "unknown", 0.0, f"image open error: {exc}"


def handle_loose_file(uploaded_file: Any) -> list[ImageRecord]:
    data = uploaded_file.getvalue()
    rec = save_image_bytes(data, uploaded_file.name, "loose_image")
    return [rec] if rec else []


def handle_zip(uploaded_file: Any) -> tuple[list[ImageRecord], list[str]]:
    records: list[ImageRecord] = []
    errors: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(uploaded_file.getvalue())) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                ext = Path(info.filename).suffix.lower()
                if ext not in SUPPORTED_IMAGES:
                    continue
                try:
                    rec = save_image_bytes(zf.read(info), Path(info.filename).name, "zip")
                    if rec:
                        records.append(rec)
                except Exception as exc:
                    errors.append(f"ZIP item error {info.filename}: {exc}")
    except Exception as exc:
        errors.append(f"ZIP extract error {uploaded_file.name}: {exc}")
    return records, errors


def handle_rar(uploaded_file: Any) -> tuple[list[ImageRecord], list[str]]:
    records: list[ImageRecord] = []
    errors: list[str] = []
    if rarfile is None:
        return records, ["RAR_EXTRACTOR_MISSING: install rarfile plus unrar/unar/bsdtar/7z, or upload ZIP"]
    try:
        with rarfile.RarFile(io.BytesIO(uploaded_file.getvalue())) as rf:
            for info in rf.infolist():
                if info.isdir():
                    continue
                ext = Path(info.filename).suffix.lower()
                if ext not in SUPPORTED_IMAGES:
                    continue
                try:
                    with rf.open(info) as f:
                        rec = save_image_bytes(f.read(), Path(info.filename).name, "rar")
                    if rec:
                        records.append(rec)
                except Exception as exc:
                    errors.append(f"RAR item error {info.filename}: {exc}")
    except Exception as exc:
        errors.append(
            f"RAR_EXTRACTOR_MISSING_OR_FAILED: {uploaded_file.name}: {exc}. "
            "Vui lòng nén lại thành ZIP hoặc cài unrar/7z."
        )
    return records, errors


def ocr_image(record: ImageRecord) -> ImageRecord:
    """Provider placeholder. Configure OPENAI_API_KEY in runtime for real vision OCR."""
    if not os.getenv("OPENAI_API_KEY"):
        record.review_note = (record.review_note + "; OCR not configured").strip("; ")
        return record
    # TODO: connect OpenAI Vision provider here. Do not hardcode API keys.
    record.review_note = (record.review_note + "; OCR provider TODO").strip("; ")
    return record


def extract_digits_price(text: str) -> str:
    if not text:
        return ""
    # Prefer Vietnamese-style million price strings.
    patterns = re.findall(r"(?:\d{1,3}(?:[\.,]\d{3}){1,3}|\d+\s*(?:tr|triệu))", text, flags=re.I)
    if not patterns:
        return ""
    raw = patterns[0].lower().replace(" ", "")
    if "tr" in raw or "triệu" in raw:
        nums = re.findall(r"\d+", raw)
        return str(int(nums[0]) * 1_000_000) if nums else ""
    return re.sub(r"\D", "", raw)


def normalize_size(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"(\d{2,4})\s*[xX\*×]\s*(\d{2,4})(?:\s*[xX\*×]\s*(\d{2,4}))?\s*(mm|cm|m)?", text)
    if not m:
        return ""
    parts = [m.group(1), m.group(2)]
    if m.group(3):
        parts.append(m.group(3))
    unit = m.group(4) or "mm"
    return "x".join(parts) + f" {unit}"


def parse_table_rows(records: list[ImageRecord]) -> list[TableRow]:
    rows: list[TableRow] = []
    for rec in records:
        if rec.image_type != "price_table_image":
            continue
        lines = [line.strip() for line in rec.raw_ocr_text.splitlines() if line.strip()]
        for i, line in enumerate(lines, start=1):
            row = TableRow(
                source_image=rec.local_path,
                row_index=i,
                ProductName=line,
                BasePrice=extract_digits_price(line),
                Size=normalize_size(line),
                raw_text=line,
                confidence=0.25,
                review_note="raw OCR line; needs table parser/vision extraction",
            )
            rows.append(row)
    return rows


def empty_master_row(code: str, image_url: str, status: str = "ACTIVE") -> dict[str, str]:
    row = {col: "" for col in MASTER_COLUMNS}
    row.update(
        {
            "Code": code,
            "Status": status,
            "Price_Mode": "FIXED",
            "Hotline": "0929878666",
            "Template_ID": "SOFA_MODERN",
            "Image_Status": "LOCAL",
            "Image_URL": image_url,
            "Image_Source": SOURCE_NAME,
            "Harvest_Status": "READY",
        }
    )
    return row


def build_outputs(records: list[ImageRecord], table_rows: list[TableRow]) -> dict[str, pd.DataFrame]:
    main_rows: list[dict[str, str]] = []
    unmatched_rows: list[dict[str, str]] = []
    duplicate_rows: list[dict[str, str]] = []

    # This skeleton keeps table-derived rows separate until real matching is implemented.
    code_seq = 1
    for rec in records:
        if rec.image_type == "single_product_image":
            code = f"BSH{code_seq:04d}"
            code_seq += 1
            row = empty_master_row(code, rec.local_path, status="REVIEW")
            row["Description"] = "UNMATCHED_SINGLE_PRODUCT - cần gán tên/giá từ bảng báo giá"
            unmatched_rows.append(row)
        elif rec.image_type == "composite_image":
            row = empty_master_row(f"REF{code_seq:04d}", rec.local_path, status="REVIEW")
            code_seq += 1
            row["Description"] = "COMPOSITE_REFERENCE - ảnh tập hợp, không import trực tiếp"
            duplicate_rows.append(row)

    sheets = {
        "MAIN_IMPORT": pd.DataFrame(main_rows, columns=MASTER_COLUMNS),
        "UNMATCHED_SINGLE_PRODUCT": pd.DataFrame(unmatched_rows, columns=MASTER_COLUMNS),
        "REVIEW_DUPLICATE": pd.DataFrame(duplicate_rows, columns=MASTER_COLUMNS),
        "IMAGE_MANIFEST": pd.DataFrame([asdict(r) for r in records]),
        "TABLE_ROWS": pd.DataFrame([asdict(r) for r in table_rows]),
    }
    return sheets


def make_excel(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df = df.fillna("")
            df.to_excel(writer, sheet_name=name[:31], index=False)
    output.seek(0)
    return output.getvalue()


def make_report(records: list[ImageRecord], table_rows: list[TableRow], errors: list[str], sheets: dict[str, pd.DataFrame]) -> str:
    counts = pd.Series([r.image_type for r in records]).value_counts().to_dict() if records else {}
    lines = [
        "IMPORT_REPORT - BÀN SOFA HIỆN ĐẠI",
        "=" * 40,
        f"Total images: {len(records)}",
        f"Image type counts: {counts}",
        f"Table rows extracted: {len(table_rows)}",
        f"MAIN_IMPORT records: {len(sheets['MAIN_IMPORT'])}",
        f"UNMATCHED_SINGLE_PRODUCT records: {len(sheets['UNMATCHED_SINGLE_PRODUCT'])}",
        f"REVIEW_DUPLICATE/reference records: {len(sheets['REVIEW_DUPLICATE'])}",
        "",
        "Errors / warnings:",
    ]
    lines.extend(errors or ["None"])
    lines.append("")
    lines.append("Manual review images:")
    for rec in records:
        if rec.image_type in {"unknown", "single_product_image", "composite_image"} or "OCR not configured" in rec.review_note:
            lines.append(f"- {rec.local_path} | {rec.image_type} | {rec.review_note}")
    return "\n".join(lines)


def main() -> None:
    st.set_page_config(page_title="IMPORT MASTER_PRODUCTDB", layout="wide")
    st.title("IMPORT MASTER_PRODUCTDB")
    st.caption(f"Nguồn dữ liệu: {SOURCE_NAME}")

    uploaded_files = st.file_uploader(
        "📁 Kéo thả thư mục ảnh hoặc chọn nhiều ảnh",
        type=["jpg", "jpeg", "png", "webp", "zip", "rar"],
        accept_multiple_files=True,
    )
    master_db = st.file_uploader("MASTER_PRODUCTDB.xlsx để check trùng (tùy chọn)", type=["xlsx"])

    if not uploaded_files:
        st.info("Upload ảnh, ZIP hoặc RAR để bắt đầu.")
        return

    if st.button("Bắt đầu xử lý"):
        start = time.time()
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        records: list[ImageRecord] = []
        errors: list[str] = []
        progress = st.progress(0)
        log = st.empty()

        for idx, uploaded in enumerate(uploaded_files, start=1):
            ext = Path(uploaded.name).suffix.lower()
            log.write(f"Đang xử lý: {uploaded.name}")
            if ext in SUPPORTED_IMAGES:
                records.extend(handle_loose_file(uploaded))
            elif ext == ".zip":
                recs, errs = handle_zip(uploaded)
                records.extend(recs)
                errors.extend(errs)
            elif ext == ".rar":
                recs, errs = handle_rar(uploaded)
                records.extend(recs)
                errors.extend(errs)
            else:
                errors.append(f"Unsupported file: {uploaded.name}")
            progress.progress(idx / len(uploaded_files))

        for rec in records:
            ocr_image(rec)

        table_rows = parse_table_rows(records)
        sheets = build_outputs(records, table_rows)
        xlsx_bytes = make_excel(sheets)
        report = make_report(records, table_rows, errors, sheets)

        st.success("✅ OCR/import skeleton hoàn thành")
        st.write(
            {
                "total_images": len(records),
                "main_import": len(sheets["MAIN_IMPORT"]),
                "unmatched_single_product": len(sheets["UNMATCHED_SINGLE_PRODUCT"]),
                "processing_seconds": round(time.time() - start, 2),
                "master_db_uploaded": bool(master_db),
            }
        )
        st.download_button("⬇️ Tải MASTER_IMPORT_BAN_SOFA_HIEN_DAI.xlsx", xlsx_bytes, OUTPUT_XLSX)
        st.download_button("⬇️ Tải IMPORT_REPORT.txt", report, OUTPUT_REPORT)

        with st.expander("Xem IMAGE_MANIFEST"):
            st.dataframe(sheets["IMAGE_MANIFEST"])
        with st.expander("Xem UNMATCHED_SINGLE_PRODUCT"):
            st.dataframe(sheets["UNMATCHED_SINGLE_PRODUCT"])


if __name__ == "__main__":
    main()
