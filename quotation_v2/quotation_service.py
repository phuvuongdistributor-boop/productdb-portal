from __future__ import annotations

import json
import os
import secrets
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(os.getenv("PRODUCTDB_QUOTATIONS_PATH", str(Path(__file__).with_name("data"))))
STATUSES = ["DRAFT", "SENT", "FOLLOW_UP", "WON", "LOST", "CANCELLED"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_quotation_id() -> str:
    return f"BG-{datetime.now():%Y%m%d}-{secrets.token_hex(2).upper()}"


def _path(quotation_id: str) -> Path:
    safe_id = "".join(char for char in quotation_id if char.isalnum() or char in "-_")
    return DATA_DIR / f"{safe_id}.json"


def save_quotation(record: dict) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    quotation_id = str(record.get("QuotationID") or new_quotation_id())
    existing = load_quotation(quotation_id)
    saved = {
        **record,
        "QuotationID": quotation_id,
        "CreatedAt": existing.get("CreatedAt", record.get("CreatedAt", _now())),
        "UpdatedAt": _now(),
    }
    target = _path(quotation_id)
    temporary = target.with_name(f"{target.stem}-{secrets.token_hex(3)}.tmp")
    temporary.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)
    return saved


def load_quotation(quotation_id: str) -> dict:
    target = _path(quotation_id)
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def list_quotations() -> list[dict]:
    if not DATA_DIR.exists():
        return []
    records = []
    for path in DATA_DIR.glob("BG-*.json"):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(records, key=lambda item: item.get("UpdatedAt", ""), reverse=True)


def duplicate_quotation(quotation_id: str) -> dict:
    source = load_quotation(quotation_id)
    if not source:
        raise FileNotFoundError(quotation_id)
    duplicate = {
        **source,
        "QuotationID": new_quotation_id(),
        "Status": "DRAFT",
        "CreatedAt": _now(),
        "UpdatedAt": _now(),
    }
    return save_quotation(duplicate)


def update_status(quotation_id: str, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"Invalid quotation status: {status}")
    record = load_quotation(quotation_id)
    if not record:
        raise FileNotFoundError(quotation_id)
    record["Status"] = status
    return save_quotation(record)
