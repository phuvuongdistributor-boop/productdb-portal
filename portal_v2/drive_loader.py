from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import quote

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DRIVE_CONFIG_PATH = PROJECT_ROOT / "config" / "drive_config.json"
SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
GOOGLE_READONLY_SCOPES = [SHEETS_READONLY_SCOPE, DRIVE_READONLY_SCOPE]


def load_drive_config() -> dict:
    with DRIVE_CONFIG_PATH.open(encoding="utf-8") as config_file:
        return json.load(config_file)


def _credentials():
    try:
        from google.oauth2 import service_account
    except ImportError as error:
        raise RuntimeError(
            "Drive mode requires dependencies from portal_v2/requirements.txt."
        ) from error
    inline_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    if inline_json:
        info = json.loads(inline_json)
        return service_account.Credentials.from_service_account_info(
            info, scopes=GOOGLE_READONLY_SCOPES
        )
    if credentials_path:
        return service_account.Credentials.from_service_account_file(
            credentials_path, scopes=GOOGLE_READONLY_SCOPES
        )
    raise RuntimeError(
        "Drive mode requires GOOGLE_SERVICE_ACCOUNT_JSON or "
        "GOOGLE_APPLICATION_CREDENTIALS. Share the LIVE Google Sheet with "
        "the service-account email before deployment."
    )


def load_products_from_drive() -> pd.DataFrame:
    try:
        from google.auth.transport.requests import AuthorizedSession
    except ImportError as error:
        raise RuntimeError(
            "Drive mode requires dependencies from portal_v2/requirements.txt."
        ) from error
    config = load_drive_config()["master_live"]
    spreadsheet_id = config["spreadsheet_id"]
    sheet_name = config["sheet_name"]
    value_range = quote(f"{sheet_name}!A:AN", safe="")
    endpoint = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
        f"/values/{value_range}?valueRenderOption=UNFORMATTED_VALUE"
    )
    session = AuthorizedSession(_credentials())
    response = None
    for attempt in range(3):
        response = session.get(endpoint, timeout=60)
        if response.status_code not in {429, 500, 502, 503, 504}:
            break
        if attempt < 2:
            time.sleep(2**attempt)
    if response is None:
        raise RuntimeError("Google Sheets request was not attempted.")
    response.raise_for_status()
    values = response.json().get("values", [])
    if not values:
        raise RuntimeError("The LIVE master spreadsheet returned no data.")
    headers, *rows = values
    normalized_rows = [row + [""] * (len(headers) - len(row)) for row in rows]
    return pd.DataFrame(normalized_rows, columns=headers).fillna("")
