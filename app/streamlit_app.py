"""Meridian Capital, Counterparty Risk Intelligence Platform: Streamlit entry point.

Run locally:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Meridian Capital | Risk Intelligence", page_icon=":material/insights:",
                   layout="wide", initial_sidebar_state="expanded")

from lib import ui  # noqa: E402

ui.setup_page()

st.logo(str(Path(__file__).resolve().parent / "assets" / "logo.svg"), size="large")

pages = {
    "Executive": [
        st.Page("views/overview.py", title="Executive overview", icon=":material/dashboard:", default=True),
        st.Page("views/roi_calculator.py", title="ROI calculator", icon=":material/calculate:"),
    ],
    "Credit risk": [
        st.Page("views/credit_decision.py", title="Credit decision", icon=":material/person_search:"),
        st.Page("views/portfolio.py", title="Portfolio and vintages", icon=":material/stacked_line_chart:"),
        st.Page("views/stress_test.py", title="Stress testing", icon=":material/thunderstorm:"),
    ],
    "Payments and procurement": [
        st.Page("views/fraud.py", title="Fraud monitor", icon=":material/shield:"),
        st.Page("views/supplier_risk.py", title="Supplier risk", icon=":material/local_shipping:"),
    ],
    "Governance and AI": [
        st.Page("views/monitoring.py", title="Model monitoring", icon=":material/monitor_heart:"),
        st.Page("views/ai_analyst.py", title="AI Risk Analyst", icon=":material/forum:"),
        st.Page("views/methodology.py", title="Methodology and data", icon=":material/menu_book:"),
    ],
}
st.navigation(pages, position="sidebar").run()
