from __future__ import annotations

from io import BytesIO
from pathlib import Path

import requests
import streamlit as st
from PIL import Image, ImageOps

from data_loader import resolve_image_source
from quotation_v2.watermark import apply_phone_watermark


def _should_apply_phone_watermark(source: str) -> bool:
    normalized = source.replace("\\", "/").lower()
    return "/placeholders/" not in normalized and not normalized.startswith(
        "assets/product_images_cleaned/placeholders/"
    )


@st.cache_data(show_spinner=False, ttl=3600)
def _watermarked_bytes(source: str, modified_ns: int = 0) -> bytes | None:
    del modified_ns
    resolved = resolve_image_source(source)
    if not resolved:
        return None
    try:
        if isinstance(resolved, Path):
            raw = resolved.read_bytes()
        else:
            response = requests.get(
                resolved,
                timeout=15,
                headers={"User-Agent": "ProductDB-V2/1.0"},
            )
            response.raise_for_status()
            raw = response.content
        image = Image.open(BytesIO(raw)).convert("RGB")
        image = ImageOps.contain(image, (1400, 1400), Image.Resampling.LANCZOS)
        if _should_apply_phone_watermark(source):
            image = apply_phone_watermark(image, opacity=42)
        output = BytesIO()
        image.save(output, format="JPEG", quality=88, optimize=True)
        return output.getvalue()
    except (OSError, ValueError, requests.RequestException):
        return None


def catalog_image(source: object) -> bytes | None:
    value = str(source or "").strip()
    if not value:
        return None
    resolved = resolve_image_source(value)
    modified_ns = resolved.stat().st_mtime_ns if isinstance(resolved, Path) else 0
    return _watermarked_bytes(value, modified_ns)
