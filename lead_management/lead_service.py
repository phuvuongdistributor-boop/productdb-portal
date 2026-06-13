from __future__ import annotations

from pathlib import Path
import os

import pandas as pd


LEADS_PATH = Path(os.getenv("PRODUCTDB_LEADS_PATH", str(Path(__file__).with_name("leads.xlsx"))))
LEAD_COLUMNS = ["CreatedAt", "Name", "Phone", "Channel", "Interest", "Status", "Notes"]


def load_leads() -> pd.DataFrame:
    if not LEADS_PATH.exists():
        return pd.DataFrame(columns=LEAD_COLUMNS)
    return pd.read_excel(LEADS_PATH).fillna("")


def save_lead(lead: dict[str, object]) -> None:
    LEADS_PATH.parent.mkdir(parents=True, exist_ok=True)
    leads = load_leads()
    leads.loc[len(leads)] = [lead.get(column, "") for column in LEAD_COLUMNS]
    leads.to_excel(LEADS_PATH, index=False)
