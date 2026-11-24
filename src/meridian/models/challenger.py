"""Gradient-boosted PD challenger with calibration and SHAP explanations."""
from __future__ import annotations

from dataclasses import dataclass, field

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression

from meridian.features.cleaning import FEATURES_CATEGORICAL, FEATURES_NUMERIC

CHALLENGER_FEATURES = [c for c in FEATURES_NUMERIC if c != "is_joint_application"] + FEATURES_CATEGORICAL


def prepare(df: pd.DataFrame, categories: dict | None = None) -> pd.DataFrame:
    """Select features and fix categorical levels so train and scoring data agree."""
    X = df[CHALLENGER_FEATURES].copy()
    for c in FEATURES_CATEGORICAL:
        levels = categories[c] if categories else None
        X[c] = pd.Categorical(X[c].astype(str), categories=levels)
    return X


@dataclass
class PDChallenger:
    params: dict
    monotone: dict = field(default_factory=dict)
    model_: lgb.LGBMClassifier | None = None
    calibrator_: LogisticRegression | None = None
    categories_: dict = field(default_factory=dict)

    def fit(self, train: pd.DataFrame, y_train, valid: pd.DataFrame, y_valid, early_stopping: int = 100):
        Xt = prepare(train)
        self.categories_ = {c: list(Xt[c].cat.categories) for c in FEATURES_CATEGORICAL}
        Xv = prepare(valid, self.categories_)
        constraints = [self.monotone.get(c, 0) for c in CHALLENGER_FEATURES]
        self.model_ = lgb.LGBMClassifier(**self.params, monotone_constraints=constraints, verbose=-1)
        self.model_.fit(Xt, np.asarray(y_train, int), eval_X=Xv, eval_y=np.asarray(y_valid, int), eval_metric="auc",
                        callbacks=[lgb.early_stopping(early_stopping, verbose=False)])
        return self

    def raw_pd(self, df: pd.DataFrame) -> np.ndarray:
        return self.model_.predict_proba(prepare(df, self.categories_))[:, 1]

    def calibrate(self, df: pd.DataFrame, y) -> PDChallenger:
        """Platt scaling on the most recent mature year: logit(PD) re-fitted linearly."""
        z = logit(np.clip(self.raw_pd(df), 1e-6, 1 - 1e-6)).reshape(-1, 1)
        self.calibrator_ = LogisticRegression(C=1e6).fit(z, np.asarray(y, int))
        return self

    def predict_pd(self, df: pd.DataFrame) -> np.ndarray:
        p = self.raw_pd(df)
        if self.calibrator_ is None:
            return p
        z = logit(np.clip(p, 1e-6, 1 - 1e-6)).reshape(-1, 1)
        return self.calibrator_.predict_proba(z)[:, 1]

    def shap_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Exact TreeSHAP contributions in log-odds; last column is the base value."""
        contrib = self.model_.booster_.predict(prepare(df, self.categories_), pred_contrib=True)
        return pd.DataFrame(contrib, columns=CHALLENGER_FEATURES + ["base_value"], index=df.index)

    def reason_codes(self, df: pd.DataFrame, top: int = 3) -> list[list[str]]:
        sv = self.shap_values(df).drop(columns="base_value")
        return [row.sort_values(ascending=False).head(top).index.tolist() for _, row in sv.iterrows()]


def to_log_odds(p) -> np.ndarray:
    return logit(np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6))


def from_log_odds(z) -> np.ndarray:
    return expit(z)
