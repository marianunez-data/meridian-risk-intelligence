"""Governed catalog: the only tables the AI analyst may query, with business descriptions.

The descriptions are written for the language model as much as for people:
they state the grain, units and the meaning of rates, which is what prevents
most text-to-SQL errors.
"""
from __future__ import annotations

import duckdb

TABLES: dict[str, str] = {
    "portfolio_cube": (
        "Loan book aggregated by issue_month x grade x term_months x loan_purpose x state_code x dataset_split. "
        "Sum columns before dividing. funded_amount in USD. Weighted rate = sum(rate_x_funded)/sum(funded_amount). "
        "24-month bad rate = sum(bad_24m)/sum(loans_with_24m_outcome). Default-to-date rate = sum(defaults_to_date)/sum(loans). "
        "realised_loss in USD (exposure at default minus net recoveries). dataset_split is train, validation, test_oot or monitoring."
    ),
    "mart_portfolio_monthly": (
        "One row per origination month: loans_originated, funded_amount (USD), weighted_interest_rate, avg_fico_score, "
        "share_prime_ab, share_subprime_efg, bad_rate_24m (null when outcomes are immature), realised_credit_loss, "
        "interest_income, and macro context (unemployment_rate, fed_funds_rate)."
    ),
    "mart_vintage_curves": (
        "Cumulative default rate by vintage_quarter, term_months and months_on_book. "
        "Rates are shares (0.12 = 12%). Combine vintages with sum(cumulative_defaults)/sum(loans)."
    ),
    "mart_macro_monthly": "Monthly US macro series: unemployment_rate, fed_funds_rate, baa_credit_spread, card_chargeoff_rate (all in percent).",
    "live_book_el": (
        "Live loans at March 2019 aggregated by grade, term_months, loan_status, issue_quarter: loans, outstanding (USD), "
        "expected_loss and expected_loss_downturn (USD). EL rate = sum(expected_loss)/sum(outstanding)."
    ),
    "report_stress_test_results": "Expected loss of the live book under Baseline, Adverse and Severely adverse scenarios (column scenario).",
    "report_pd_model_comparison": "Out-of-time 2016 metrics (auc, gini, ks, brier) for the scorecard, the challenger and the Lending Club grade.",
    "report_pd_budget_simulation": "Profit by loan-selection strategy at 25%, 50% and 75% capital budgets on 2016 loans (budget is a share).",
    "mart_fraud_by_type": "Payments by transaction_type: transactions, fraud_transactions, fraud_amount (USD), fraud_rate, rule_alerts, rule_detection_rate.",
    "report_fraud_roi_test_period": "Fraud model comparison on the test period: alerts, frauds_caught, fraud_value_caught and missed (USD), saving_vs_rule_engine.",
    "supplier_scores": (
        "One row per US public company (FY2018 10-K): company_name, sector_name, revenue (USD), altman_z_double_prime, "
        "altman_zone (Safe, Grey, Distress), red_flags (0-4), risk_tier (Tier 1 Low to Tier 4 Critical)."
    ),
    "procurement_spend": (
        "Synthetic spend ledger of client Atlas Industrial Group: company_name, category, annual_spend (USD), single_source, "
        "risk_tier, altman_zone."
    ),
    "monitoring_psi": "Score Population Stability Index by origination quarter with status (Green, Amber, Red).",
    "monitoring_performance": "Gini and calibration (observed_bad_rate vs predicted_pd) by mature origination quarter.",
    "dim_risk_grade": "Lending Club sub_grade, grade and risk_rank (1 = A1 safest, 35 = G5 riskiest).",
    "dim_geography": "US state_code, state_name, census_region, census_division.",
}


def schema_text(con: duckdb.DuckDBPyConnection) -> str:
    """Compact schema listing for the system prompt."""
    lines = []
    for table, desc in TABLES.items():
        cols = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ? ORDER BY ordinal_position",
            [table]).fetchall()
        col_txt = ", ".join(f"{c} {t.lower()}" for c, t in cols)
        lines.append(f"- {table}({col_txt})\n  {desc}")
    return "\n".join(lines)
