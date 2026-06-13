from __future__ import annotations

import streamlit as st


SOURCE_LABELS = {
    "BAN_HOP": "Bàn họp",
    "BAN_MAY_TINH": "Bàn máy tính",
    "BAN_VAN_PHONG": "Bàn văn phòng",
    "GHE_VAN_PHONG": "Ghế văn phòng",
    "GIA_KE_SAT": "Giá kệ sắt",
    "HOC_SAT": "Hộc sắt",
    "HOC_TU_PHU_GO": "Hộc, tủ phụ gỗ",
    "NOI_THAT_CONG_TRINH": "Nội thất công trình",
    "NOI_THAT_GIA_DINH": "Nội thất gia đình",
    "NOI_THAT_GIA_DUNG": "Nội thất gia dụng",
    "NOI_THAT_TRUONG_HOC": "Nội thất trường học",
    "NOI_THAT_Y_TE": "Nội thất y tế",
    "SOFA": "Sofa",
    "TU_VAN_PHONG": "Tủ văn phòng",
    "VACH_VAN_PHONG": "Vách văn phòng",
}


def source_label(value: object) -> str:
    text = str(value or "").strip()
    return SOURCE_LABELS.get(text, text.replace("_", " ").title())


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
          --portal-navy: #12304a;
          --portal-blue: #176b87;
          --portal-red: #b42318;
          --portal-bg: #f4f7fa;
          --portal-border: #dce4eb;
        }
        html, body, [class*="css"], .stApp {
          font-family: "Segoe UI", Arial, sans-serif;
        }
        .stApp { background: var(--portal-bg); color: #172b3a; }
        [data-testid="stHeader"] { background: rgba(244, 247, 250, .92); }
        [data-testid="stSidebar"] {
          background: linear-gradient(180deg, #102a43 0%, #174b69 100%);
          border-right: 1px solid #0d2437;
        }
        [data-testid="stSidebar"] * { color: #f8fafc; }
        [data-testid="stSidebarNav"] a {
          border-radius: 10px; margin: 3px 8px; padding: 9px 12px;
        }
        [data-testid="stSidebarNav"] a:hover,
        [data-testid="stSidebarNav"] a[aria-current="page"] {
          background: rgba(255,255,255,.16);
        }
        h1, h2, h3 { color: var(--portal-navy); letter-spacing: -.02em; }
        [data-testid="stMetric"], [data-testid="stVerticalBlockBorderWrapper"] {
          background: #fff; border-color: var(--portal-border); border-radius: 15px;
        }
        .stTabs [data-baseweb="tab-list"] {
          gap: 7px; padding: 8px; border-radius: 14px;
          background: #e7eef4; overflow-x: auto;
        }
        .stTabs [data-baseweb="tab"] {
          height: 42px; padding: 0 16px; border-radius: 10px;
          background: #fff; color: #29485f; border: 1px solid #d6e0e8;
          white-space: nowrap;
        }
        .stTabs [aria-selected="true"] {
          background: var(--portal-blue) !important; color: #fff !important;
          border-color: var(--portal-blue) !important;
        }
        .stTabs [data-baseweb="tab-highlight"] { display: none; }
        .stButton > button, .stDownloadButton > button, [data-testid="stPageLink"] a {
          border-radius: 10px; font-weight: 650;
        }
        [data-testid="stDataFrame"] { background: #fff; border-radius: 14px; overflow: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )
