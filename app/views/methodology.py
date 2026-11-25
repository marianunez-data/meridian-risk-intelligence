import streamlit as st
from lib import ui
from lib.data import DOCS, q

try:
    REPO = st.secrets["GITHUB_REPO_URL"]
except Exception:  # noqa: BLE001
    REPO = "https://github.com/"

ui.header("Documentation", "Methodology and data",
          "How the platform was built, from raw files to decisions. Every step is reproducible from the repository "
          "with three commands.")

st.header("Architecture")
st.markdown("""
| Layer | Technology | What happens |
|---|---|---|
| Raw | CSV, TSV (3.2 GB) | Public downloads: Lending Club, FRED, SEC, PaySim |
| Bronze | DuckDB to Parquet | Typed and compressed, content unchanged (0.55 GB) |
| Silver | dbt staging and intermediate | Cleaning and the single definition of default, loss and split |
| Gold | dbt marts, 43 data tests | Star schema and purpose-built marts |
| Models | scikit-learn, statsmodels, LightGBM, SHAP | Scorecard, challenger, LGD and EAD, stress, fraud, supplier tiers |
| Serving | Streamlit, DuckDB (27 MB app warehouse) | This dashboard and the AI Risk Analyst |
""")

st.header("Notebooks")
nb = [("00", "Business context", "Problem, KPIs, ROI framework"), ("01", "Data ingestion and SQL", "Warehouse, reconciliation, 8 SQL analyses"),
      ("02", "Data audit", "Quality scorecard, leakage audit"), ("03", "Data cleaning", "Train-fitted pipeline"),
      ("04", "Exploratory analysis", "Risk drivers, stability"), ("05", "Feature engineering and WoE", "Binning, IV, PSI screening"),
      ("06", "PD scorecard", "Logistic regression, points, profit strategy"), ("07", "Challenger and SHAP", "LightGBM, Optuna, monotonic, SHAP"),
      ("08", "LGD, EAD, Expected Loss", "Fractional logit, downturn LGD, backtest"), ("09", "Stress testing and ROI", "Satellite model, scenarios"),
      ("10", "Fraud detection", "Velocity SQL, Isolation Forest, cost threshold"), ("11", "Supplier risk", "Altman Z'', tiers, spend at risk"),
      ("12", "Validation and monitoring", "PSI, CSI, model card"), ("13", "AI Risk Analyst", "Text-to-SQL agent, guardrails, evaluation")]
st.dataframe([{"#": n, "Notebook": t, "Covers": c} for n, t, c in nb], hide_index=True, width="stretch")
st.markdown(f"Source code and executed notebooks: [{REPO}]({REPO})")

st.header("Data quality")
st.dataframe(q("select * from report_data_audit_scorecard"), hide_index=True, width="stretch")

st.header("Definitions")
st.markdown((DOCS / "methodology.md").read_text().split("\n", 2)[2])
ui.footer()
