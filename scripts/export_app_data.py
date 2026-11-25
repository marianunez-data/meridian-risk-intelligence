"""Build the compact, deployable app database: app/data/meridian_app.duckdb.

The full warehouse is about 2 GB, too large for free hosting (Streamlit
Community Cloud gives each app about 1 GB of memory). The app only needs gold
aggregates, model outputs and a small scoring sample, so this script exports
exactly that (typically under 40 MB) into one DuckDB file that ships with the
repository. The AI Risk Analyst queries the same file, so it can only ever see
governed, aggregated data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from meridian import config  # noqa: E402

APP_DB = config.PROJECT_ROOT / "app" / "data" / "meridian_app.duckdb"
APP_PARQUET = config.DATA_DIR / "app"
REPORTS = config.PROJECT_ROOT / "reports"
MODELS = config.PROJECT_ROOT / "models"


def main() -> None:
    APP_DB.parent.mkdir(parents=True, exist_ok=True)
    if APP_DB.exists():
        APP_DB.unlink()
    out = duckdb.connect(str(APP_DB))
    out.execute(f"ATTACH '{config.WAREHOUSE_PATH}' AS wh (READ_ONLY)")

    # Gold marts, copied as-is (already aggregated).
    for t in ["dim_month", "dim_risk_grade", "dim_geography", "mart_portfolio_monthly", "mart_vintage_curves",
              "mart_macro_monthly", "mart_fraud_by_type", "mart_fraud_hourly"]:
        out.execute(f"CREATE TABLE {t} AS SELECT * FROM wh.gold.{t}")

    # Portfolio cube: loan-level fact aggregated to month x grade x term x purpose x state.
    out.execute("""
        CREATE TABLE portfolio_cube AS
        SELECT issue_month, grade, term_months, loan_purpose, state_code, dataset_split,
               count(*)                                              AS loans,
               sum(funded_amount)                                    AS funded_amount,
               sum(funded_amount * interest_rate)                    AS rate_x_funded,
               sum(is_defaulted::int)                                AS defaults_to_date,
               count(is_bad_24m)                                     AS loans_with_24m_outcome,
               sum(coalesce(is_bad_24m::int, 0))                     AS bad_24m,
               sum(coalesce(exposure_at_default - net_recoveries, 0)) AS realised_loss,
               sum(interest_received)                                AS interest_received
        FROM wh.gold.fct_loans
        GROUP BY ALL
    """)

    # Parquet outputs written by the notebooks.
    for name in ["live_book_el", "fraud_monitor", "supplier_scores", "procurement_spend",
                 "monitoring_psi", "monitoring_csi", "monitoring_performance"]:
        path = APP_PARQUET / f"{name}.parquet"
        if name == "live_book_el":
            out.execute(f"""
                CREATE TABLE live_book_el AS
                SELECT grade, term_months, loan_status, date_trunc('quarter', issue_month) AS issue_quarter,
                       count(*) AS loans, sum(outstanding_principal) AS outstanding,
                       sum(pd_remaining * outstanding_principal) AS pd_x_outstanding,
                       sum(expected_loss) AS expected_loss, sum(expected_loss_downturn) AS expected_loss_downturn,
                       avg(lgd) AS lgd, avg(lgd_downturn) AS lgd_downturn
                FROM '{path}' GROUP BY ALL""")
        else:
            out.execute(f"CREATE TABLE {name} AS SELECT * FROM '{path}'")

    # Reports written by the notebooks.
    index_names = {"stress_test_results": "scenario", "el_backtest_2016": "grade",
                   "challenger_shap_importance": "feature", "fraud_roi_test_period": "model", "fraud_model_metrics": "model"}
    for name in ["pd_model_comparison", "pd_budget_simulation", "stress_test_results", "fraud_roi_test_period",
                 "fraud_model_metrics", "el_backtest_2016", "challenger_shap_importance", "data_audit_scorecard"]:
        df = pd.read_csv(REPORTS / f"{name}.csv")
        df = df.rename(columns={"Unnamed: 0": index_names.get(name, "name")})
        out.register("report_df", df)
        out.execute(f"CREATE TABLE report_{name} AS SELECT * FROM report_df")
        out.unregister("report_df")

    # Scoring sample: 5,000 2016 applicants with application-time features only.
    sample = pd.read_parquet(config.DATA_DIR / "features" / "pd_test_oot.parquet").sample(5000, random_state=11)
    out.register("sample_df", sample)
    out.execute("CREATE TABLE applicant_sample AS SELECT * FROM sample_df")

    # Stress parameters and loss parameters as small tables.
    sat = joblib.load(MODELS / "stress_satellite.joblib")
    out.execute("CREATE TABLE stress_satellite AS SELECT ? AS slope, ? AS intercept, ? AS r_squared, ? AS baseline_unemployment",
                [sat.slope, sat.intercept, sat.r_squared, sat.baseline_unemployment])

    # Loan-level 2016 table for the interactive ROI calculator (predictions computed once here).
    from meridian.models.challenger import PDChallenger  # noqa: F401  (needed to unpickle)
    challenger = joblib.load(MODELS / "pd_challenger.joblib")
    scorecard = joblib.load(MODELS / "pd_scorecard.joblib")
    loss = joblib.load(MODELS / "loss_parameters.joblib")
    feats = {s: pd.read_parquet(config.DATA_DIR / "features" / f"pd_{s}.parquet") for s in ["validation", "test_oot"]}
    outcomes = out.execute("""select loan_id, is_defaulted, funded_amount from wh.gold.fct_loans
                              where dataset_split in ('validation', 'test_oot')""").df()
    va = feats["validation"].merge(outcomes, on="loan_id")
    te = feats["test_oot"].merge(outcomes, on="loan_id")
    ratio_ch = va.is_defaulted.mean() / challenger.predict_pd(va).mean()
    ratio_sc = va.is_defaulted.mean() / scorecard.predict_pd(va).mean()
    grade_pd = va.groupby(va.benchmark_sub_grade.astype(str)).is_defaulted.mean()
    roi = pd.DataFrame({
        "funded": te.funded_amount.astype("float32"),
        "rate": te.benchmark_interest_rate.astype("float32"),
        "term": te.term_months.astype("int16"),
        "grade": te.benchmark_grade.astype(str),
        "defaulted": te.is_defaulted.astype(bool),
        "pd_challenger": np.clip(challenger.predict_pd(te) * ratio_ch, 0, 1).astype("float32"),
        "pd_scorecard": np.clip(scorecard.predict_pd(te) * ratio_sc, 0, 1).astype("float32"),
        "pd_grade": te.benchmark_sub_grade.astype(str).map(grade_pd).astype("float32"),
    })
    out.register("roi_df", roi)
    out.execute("CREATE TABLE roi_loans_2016 AS SELECT * FROM roi_df")
    out.unregister("roi_df")
    out.execute("CREATE TABLE loss_parameters AS SELECT * FROM (VALUES "
                + ", ".join(f"({t}, {loss['lgd_long_run_by_term'][t]}, {loss['lgd_downturn_by_term'][t]}, "
                            f"{loss['ead_ratio_by_term'][t]}, {loss['lifetime_pd_ratio_by_term'][t]})" for t in (36, 60))
                + ") t(term_months, lgd_long_run, lgd_downturn, ead_ratio, lifetime_pd_ratio)")

    # Fraud test-period scores for the interactive threshold control.
    fraud = joblib.load(MODELS / "fraud_model.joblib")
    tx = out.execute((config.SQL_DIR / "analysis" / "q10_fraud_features.sql").read_text()
                     .replace("silver.stg_paysim__transactions", "wh.silver.stg_paysim__transactions")).df()
    tx = tx[tx.day_index >= 19].copy()
    tx["is_transfer"] = (tx.transaction_type == "transfer").astype(int)
    tx["amount_to_origin_balance"] = tx.amount_to_origin_balance.clip(upper=10)
    fs = pd.DataFrame({
        "hour_index": tx.hour_index.astype("int16"), "amount": tx.amount.astype("float32"),
        "is_fraud": tx.is_fraud.astype(bool), "rule_flag": tx.rule_flag.astype(bool),
        "score_restricted": fraud["restricted"].predict_proba(tx[fraud["features_restricted"]])[:, 1].astype("float32"),
        "score_full": fraud["full"].predict_proba(tx[fraud["features_full"]])[:, 1].astype("float32"),
        "score_iforest": (-fraud["isolation_forest"].score_samples(tx[fraud["features_full"]])).astype("float32"),
    })
    out.register("fs_df", fs)
    out.execute("CREATE TABLE fraud_scores_test AS SELECT * FROM fs_df")
    out.unregister("fs_df")
    th = fraud["thresholds"]
    out.execute("CREATE TABLE fraud_thresholds AS SELECT * FROM (VALUES "
                + ", ".join(f"('{k}', {v})" for k, v in th.items()) + ") t(model, threshold)")

    # Exact loan-level stress curve: expected loss by grade for unemployment 3.5% to 14%.
    from meridian.stress import share_in_horizon
    live = pd.read_parquet(APP_PARQUET / "live_book_el.parquet")
    curves = out.execute("""
        select term_months, months_on_book, sum(cumulative_defaults) / sum(loans) as cdr
        from wh.gold.mart_vintage_curves
        where (term_months = 36 and vintage_year between 2013 and 2015)
           or (term_months = 60 and vintage_year between 2012 and 2013)
        group by all order by all""").df()
    curves["share"] = curves.cdr / curves.groupby("term_months").cdr.transform("max")
    h = share_in_horizon(live.term_months.values, live.months_on_book.values, live.loan_status.values, curves)
    rows = []
    for u in np.round(np.arange(3.5, 14.01, 0.1), 1):
        mult = float(np.exp(sat.slope * (u - sat.baseline_unemployment)))
        pd_s = np.clip(live.pd_remaining.values * (h * mult + (1 - h)), 0, 1)
        for grade, idx in live.groupby("grade").indices.items():
            rows.append({"unemployment": u, "grade": grade,
                         "el_long_run": float((pd_s[idx] * live.lgd.values[idx] * live.outstanding_principal.values[idx]).sum()),
                         "el_downturn": float((pd_s[idx] * live.lgd_downturn.values[idx] * live.outstanding_principal.values[idx]).sum())})
    out.register("curve_df", pd.DataFrame(rows))
    out.execute("CREATE TABLE stress_curve AS SELECT * FROM curve_df")
    out.unregister("curve_df")

    out.execute("DETACH wh")
    sizes = out.execute("""
        SELECT table_name, estimated_size AS rows FROM duckdb_tables() ORDER BY table_name""").df()
    out.close()
    print(sizes.to_string(index=False))
    print(f"\nWrote {APP_DB.relative_to(config.PROJECT_ROOT)} ({APP_DB.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
