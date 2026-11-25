"""Cached access to the deployable app warehouse and the trained models."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import duckdb  # noqa: E402
import joblib  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

APP_DB = ROOT / "app" / "data" / "meridian_app.duckdb"
MODELS = ROOT / "models"
DOCS = ROOT / "docs"


def _version(*paths: Path) -> tuple:
    """Modification time and size of each file. Part of every cache key, so a redeploy that ships a new
    warehouse or model file is picked up immediately instead of serving numbers cached from the old one."""
    return tuple((p.stat().st_mtime_ns, p.stat().st_size) for p in paths)


@st.cache_resource(show_spinner=False)
def _connection(version: tuple) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(APP_DB), read_only=True)


def connection() -> duckdb.DuckDBPyConnection:
    return _connection(_version(APP_DB))


@st.cache_data(show_spinner=False, ttl=None)
def _q(sql: str, params: tuple | None, version: tuple) -> pd.DataFrame:
    cur = _connection(version).cursor()
    return cur.execute(sql, list(params) if params else None).df()


def q(sql: str, params: tuple | None = None) -> pd.DataFrame:
    return _q(sql, params, _version(APP_DB))


def models() -> dict:
    return _models(_version(MODELS / "pd_challenger.joblib", MODELS / "pd_scorecard.joblib", MODELS / "scorecard_points.csv"))


@st.cache_resource(show_spinner=False)
def _models(version: tuple) -> dict:
    from meridian.models.challenger import PDChallenger  # noqa: F401  (unpickling)
    from meridian.models.scorecard import Scorecard  # noqa: F401
    return {
        "challenger": joblib.load(MODELS / "pd_challenger.joblib"),
        "scorecard": joblib.load(MODELS / "pd_scorecard.joblib"),
        "points": pd.read_csv(MODELS / "scorecard_points.csv"),
    }


def headline() -> dict:
    """Numbers used on several pages, computed once per warehouse version."""
    return _headline(_version(APP_DB))


@st.cache_data(show_spinner=False)
def _headline(version: tuple) -> dict:
    cube = q("select sum(funded_amount) funded, sum(loans) loans from portfolio_cube").iloc[0]
    live = q("select sum(outstanding) outstanding, sum(expected_loss) el, sum(expected_loss_downturn) el_dt from live_book_el").iloc[0]
    stress = q("select scenario, expected_loss from report_stress_test_results").set_index("scenario").expected_loss
    cmp_ = q("select dataset, gini, ks from report_pd_model_comparison").set_index("dataset")
    fraud = q("select model, fraud_value_caught, fraud_value_missed from report_fraud_roi_test_period").set_index("model")
    spend = q("""select sum(annual_spend) total,
                        sum(annual_spend) filter (where risk_tier in ('Tier 3 High', 'Tier 4 Critical')) at_risk
                 from procurement_spend""").iloc[0]
    budget = q("select strategy, profit, default_rate from report_pd_budget_simulation where budget = 0.5").set_index("strategy")
    stopped = lambda m: fraud.loc[m, "fraud_value_caught"] / (fraud.loc[m, "fraud_value_caught"] + fraud.loc[m, "fraud_value_missed"])  # noqa: E731
    gini = lambda key: float(cmp_.loc[[i for i in cmp_.index if i.startswith(key)][0], "gini"])  # noqa: E731
    return {
        "funded": cube.funded, "loans": cube.loans,
        "outstanding": live.outstanding, "el": live.el, "el_rate": live.el / live.outstanding,
        "stress_buffer": stress["Severely adverse"] - stress["Baseline"],
        "gini_challenger": gini("Meridian challenger"), "gini_scorecard": gini("Meridian scorecard"),
        "gini_lc": gini("Lending Club"),
        "fraud_stopped_model": stopped("LightGBM, restricted (no balances)"), "fraud_stopped_rules": stopped("Rule engine (today)"),
        "spend_total": spend.total, "spend_at_risk": spend.at_risk,
        "profit_challenger": budget.loc["Expected profit, Meridian challenger", "profit"],
        "profit_grade": budget.loc["Expected profit, Lending Club grade PD", "profit"],
        "profit_random": budget.loc["Random selection (no model)", "profit"],
        "dr_challenger": budget.loc["Expected profit, Meridian challenger", "default_rate"],
        "dr_grade": budget.loc["Expected profit, Lending Club grade PD", "default_rate"],
    }
