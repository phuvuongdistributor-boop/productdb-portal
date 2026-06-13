from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "public_portal.json"


def public_base_url() -> str:
    environment_url = os.getenv("PRODUCTDB_PUBLIC_URL", "").strip()
    if environment_url:
        return environment_url.rstrip("/")
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip()
    if render_url:
        return render_url.rstrip("/")
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        configured_url = str(config.get("public_base_url", "")).strip()
        if configured_url:
            return configured_url.rstrip("/")
    return "http://192.168.1.11:8501"


def catalog_url(code: object = "") -> str:
    base = f"{public_base_url()}/catalog"
    value = str(code or "").strip()
    return f"{base}?code={quote(value)}" if value else base
