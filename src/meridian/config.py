"""Single source of truth for paths, dates and business constants.

Every notebook, script and the Streamlit app imports from here, so a change
(for example a new snapshot date) propagates everywhere at once.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("MERIDIAN_DATA", PROJECT_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
BRONZE_DIR = DATA_DIR / "bronze"
WAREHOUSE_PATH = DATA_DIR / "warehouse" / "meridian.duckdb"
SQL_DIR = PROJECT_ROOT / "sql"
APP_DB_PATH = PROJECT_ROOT / "app" / "data" / "meridian_app.duckdb"
DOCS_DIR = PROJECT_ROOT / "docs"
DBT_DIR = PROJECT_ROOT / "warehouse"

# --------------------------------------------------------------------------- #
# Data sources (all public)
# --------------------------------------------------------------------------- #
HF_BASE = "https://huggingface.co/datasets"
LENDING_CLUB_URL = f"{HF_BASE}/codesignal/lending-club-loan-accepted/resolve/main/accepted_2007_to_2018Q4.csv"
PAYSIM_URL = f"{HF_BASE}/theman10/paysim/resolve/main/paysim.csv"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
SEC_FSDS_URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/{quarter}.zip"
# SEC asks automated clients to identify themselves.
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "MeridianRiskPortfolio research contact@example.com")

FRED_SERIES = {
    "UNRATE": "Unemployment rate (%)",
    "FEDFUNDS": "Effective federal funds rate (%)",
    "GDPC1": "Real GDP (bn 2017 USD, quarterly)",
    "CPIAUCSL": "CPI all urban consumers (index)",
    "DRCCLACBS": "Credit card delinquency rate, all banks (%, quarterly)",
    "CORCCACBS": "Credit card charge-off rate, all commercial banks (%, quarterly)",
    "BAA10Y": "Moody's Baa corporate spread over 10Y Treasury (pp)",
}
SEC_QUARTERS = ["2019q1", "2019q2"]  # FY2018 10-K filings land in H1 2019

# --------------------------------------------------------------------------- #
# Credit risk design decisions
# --------------------------------------------------------------------------- #
SNAPSHOT_DATE = date(2019, 3, 1)          # last payment month observed in the data
PERFORMANCE_WINDOW_MONTHS = 24            # "bad" = default within 24 months of issue
CHARGE_OFF_LAG_MONTHS = 5                 # Lending Club charges off at ~150 days past due
SPLITS = {                                # out-of-time split by issue year
    "train": (2007, 2014),
    "validation": (2015, 2015),
    "test_oot": (2016, 2016),
    "monitoring": (2017, 2018),           # outcomes immature, used for drift only
}

# Post-origination fields: known only AFTER the loan is funded. Using any of
# them as a model feature is target leakage.
LEAKAGE_COLUMNS = [
    "total_pymnt", "total_pymnt_inv", "total_rec_prncp", "total_rec_int",
    "total_rec_late_fee", "recoveries", "collection_recovery_fee",
    "last_pymnt_d", "last_pymnt_amnt", "next_pymnt_d", "last_credit_pull_d",
    "last_fico_range_high", "last_fico_range_low", "out_prncp", "out_prncp_inv",
    "hardship_flag", "debt_settlement_flag", "settlement_status", "pymnt_plan",
    "funded_amnt_inv",
]
