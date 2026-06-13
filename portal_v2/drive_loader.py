from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DRIVE_CONFIG_PATH = PROJECT_ROOT / "config" / "drive_config.json"
SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


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
            info, scopes=[SHEETS_READONLY_SCOPE]
        )
    if credentials_path:
        return service_account.Credentials.from_service_account_file(
            credentials_path, scopes=[SHEETS_READONLY_SCOPE]
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
    endpoint = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
        f"/values/{sheet_name}!A:W?valueRenderOption=UNFORMATTED_VALUE"
    )
    response = AuthorizedSession(_credentials()).get(endpoint, timeout=60)
    response.raise_for_status()
    values = response.json().get("values", [])
    if not values:
        raise RuntimeError("The LIVE master spreadsheet returned no data.")
    headers, *rows = values
    normalized_rows = [row + [""] * (len(headers) - len(row)) for row in rows]
    return pd.DataFrame(normalized_rows, columns=headers).fillna("")
