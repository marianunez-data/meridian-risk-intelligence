"""Train-fitted cleaning for the PD model.

Every rule here was decided in notebook 02 (data audit). Rules that need a
number learned from data (caps, medians, rare-category lists) are fitted on the
training set only, then applied unchanged to validation, test and live data.
Deterministic business rules (joint-application income) live in the warehouse.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# Continuous inputs that get winsorised at train percentiles.
CONTINUOUS = [
    "loan_amount", "installment_amount", "annual_income", "debt_to_income", "fico_score",
    "revolving_balance", "revolving_utilization", "total_current_balance", "total_credit_limit",
    "total_revolving_limit", "bankcard_utilization", "bankcard_open_to_buy", "avg_current_balance",
    "credit_history_months", "loan_to_income", "payment_to_income", "revolving_balance_to_income",
    "months_since_oldest_revolving", "months_since_recent_account",
]
# Counts are bounded below by 0; only the top tail is capped.
COUNTS = [
    "delinquencies_2y", "inquiries_6m", "open_accounts", "total_accounts", "public_records",
    "public_bankruptcies", "tax_liens", "mortgage_accounts", "accounts_opened_24m",
    "accounts_opened_12m", "active_revolving_accounts", "accounts_ever_120dpd", "collections_12m",
]
SHARES = ["pct_bankcards_over_75_util", "pct_accounts_never_delinquent"]
# Missing means "the event never happened": keep NaN, add a flag.
INFORMATIVE_MISSING = {
    "months_since_last_delinquency": "has_delinquency_history",
    "months_since_last_public_record": "has_public_record",
    "months_since_recent_inquiry": "has_recent_inquiry",
}
# Small random gaps: impute with the train median.
RANDOM_MISSING = [
    "debt_to_income", "inquiries_6m", "delinquencies_2y", "open_accounts", "total_accounts",
    "public_records", "tax_liens", "collections_12m", "revolving_balance", "revolving_utilization", "bankcard_utilization", "bankcard_open_to_buy",
    "pct_bankcards_over_75_util", "pct_accounts_never_delinquent", "avg_current_balance",
    "months_since_oldest_revolving", "months_since_recent_account", "total_current_balance",
    "total_credit_limit", "total_revolving_limit", "mortgage_accounts", "accounts_opened_24m",
    "accounts_opened_12m", "active_revolving_accounts", "accounts_ever_120dpd",
    "public_bankruptcies", "loan_to_income", "payment_to_income", "revolving_balance_to_income",
]
CATEGORICAL = ["loan_purpose", "home_ownership", "income_verification", "state_code"]
RARE_SHARE = 0.005

FEATURES_NUMERIC = (
    ["term_months", "employment_years"] + CONTINUOUS + COUNTS + SHARES + list(INFORMATIVE_MISSING)
    + list(INFORMATIVE_MISSING.values()) + ["employment_not_stated", "is_joint_application"]
)
FEATURES_CATEGORICAL = CATEGORICAL


class PDCleaner(BaseEstimator, TransformerMixin):
    """Winsorise, flag informative missingness, impute random gaps, group rare categories."""

    def __init__(self, lower_q: float = 0.001, upper_q: float = 0.999, rare_share: float = RARE_SHARE):
        self.lower_q = lower_q
        self.upper_q = upper_q
        self.rare_share = rare_share

    def fit(self, X: pd.DataFrame, y=None):
        X = self._recode(X)
        self.lower_ = X[CONTINUOUS].quantile(self.lower_q).to_dict()
        self.upper_ = X[CONTINUOUS + COUNTS].quantile(self.upper_q).to_dict()
        clipped = self._clip(X.copy())
        self.medians_ = clipped[RANDOM_MISSING].median().to_dict()
        self.categories_ = {}
        for col in CATEGORICAL:
            share = X[col].astype(str).value_counts(normalize=True)
            self.categories_[col] = sorted(share[share >= self.rare_share].index)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = self._recode(X.copy())
        for col, flag in INFORMATIVE_MISSING.items():
            X[flag] = X[col].notna().astype(np.int8)
        X["employment_not_stated"] = X["employment_years"].isna().astype(np.int8)
        X["is_joint_application"] = X["is_joint_application"].astype(np.int8)
        X = self._clip(X)
        for col, med in self.medians_.items():
            X[col] = X[col].fillna(med)
        for col in SHARES:
            X[col] = X[col].clip(0, 1)
        for col, keep in self.categories_.items():
            s = X[col].astype(str)
            X[col] = pd.Categorical(s.where(s.isin(keep), "OTHER"), categories=keep + ["OTHER"])
        return X

    @staticmethod
    def _recode(X: pd.DataFrame) -> pd.DataFrame:
        ho = X["home_ownership"].astype(str)
        X["home_ownership"] = ho.where(ho.isin(["MORTGAGE", "RENT", "OWN"]), "OTHER")
        return X

    def _clip(self, X: pd.DataFrame) -> pd.DataFrame:
        for col in CONTINUOUS:
            X[col] = X[col].clip(self.lower_[col], self.upper_[col])
        for col in COUNTS:
            X[col] = X[col].clip(0, self.upper_[col])
        return X
