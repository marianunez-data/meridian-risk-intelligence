"""Logistic-regression scorecard on WoE inputs, scaled to points.

Score scaling (industry convention):
    score = offset + factor * ln(odds of being good)
    factor = PDO / ln(2)            -> every PDO points doubles the odds
    offset = base_score - factor * ln(base_odds)

Because the model is linear in WoE, each bin of each variable maps to a fixed
number of points, which is what a credit officer reads.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.special import expit, logit

from meridian.features.woe import WoEBinner


@dataclass
class Scorecard:
    binner: WoEBinner
    variables: list[str]
    pdo: float = 20.0
    base_score: float = 600.0
    base_odds: float = 50.0
    coef_: dict = field(default_factory=dict)
    intercept_: float = 0.0
    calibration_shift_: float = 0.0
    fit_summary_: pd.DataFrame | None = None

    # ------------------------------------------------------------------ fit
    def fit(self, X: pd.DataFrame, y) -> Scorecard:
        W = sm.add_constant(self.binner.transform(X, self.variables).astype(float))
        res = sm.Logit(np.asarray(y, float), W).fit(disp=0, maxiter=200)
        self.intercept_ = float(res.params["const"])
        self.coef_ = {v: float(res.params[v]) for v in self.variables}
        self.fit_summary_ = pd.DataFrame({"coefficient": res.params, "std_error": res.bse,
                                          "z": res.tvalues, "p_value": res.pvalues}).drop(index="const")
        return self

    def recalibrate(self, X: pd.DataFrame, y) -> Scorecard:
        """Shift the intercept so the mean PD matches a more recent population.

        Ranking (and therefore points) is unchanged; only the score-to-PD map moves.
        """
        target = float(np.mean(np.asarray(y, float)))
        lo, hi = -3.0, 3.0
        for _ in range(60):
            mid = (lo + hi) / 2
            self.calibration_shift_ = mid
            if self.predict_pd(X).mean() < target:
                lo = mid
            else:
                hi = mid
        return self

    # -------------------------------------------------------------- predict
    def log_odds_bad(self, X: pd.DataFrame) -> np.ndarray:
        W = self.binner.transform(X, self.variables).to_numpy(float)
        return self.intercept_ + W @ np.array([self.coef_[v] for v in self.variables])

    def predict_pd(self, X: pd.DataFrame) -> np.ndarray:
        return expit(self.log_odds_bad(X) + self.calibration_shift_)

    @property
    def factor(self) -> float:
        return self.pdo / np.log(2)

    @property
    def offset(self) -> float:
        return self.base_score - self.factor * np.log(self.base_odds)

    def score(self, X: pd.DataFrame) -> np.ndarray:
        return self.offset - self.factor * self.log_odds_bad(X)

    def pd_from_score(self, score) -> np.ndarray:
        log_odds_bad = (self.offset - np.asarray(score, float)) / self.factor
        return expit(log_odds_bad + self.calibration_shift_)

    # --------------------------------------------------------------- points
    def points_table(self) -> pd.DataFrame:
        n = len(self.variables)
        rows = []
        for v in self.variables:
            vb = self.binner.binnings_[v]
            for t in vb.table:
                pts = -self.factor * (self.coef_[v] * t["woe"] + self.intercept_ / n) + self.offset / n
                rows.append({"variable": v, "bin": t["bin"], "woe": t["woe"], "points": round(pts),
                             "train_bad_rate": t["bad_rate"], "train_loans": t["loans"]})
        return pd.DataFrame(rows)

    def points_lost(self, X: pd.DataFrame) -> pd.DataFrame:
        """Points each variable cost the applicant versus that variable's best bin (>= 0)."""
        W = self.binner.transform(X, self.variables)
        best = {v: max(self.binner.binnings_[v].woe + [self.binner.binnings_[v].woe_missing]) for v in self.variables}
        return pd.DataFrame({v: -self.factor * self.coef_[v] * (best[v] - W[v]) for v in self.variables},
                            index=X.index)

    def reason_codes(self, X: pd.DataFrame, top: int = 3) -> list[list[str]]:
        """Top variables that lowered the score most: the adverse-action reasons."""
        lost = self.points_lost(X)
        return [row.sort_values(ascending=False).head(top).index.tolist() for _, row in lost.iterrows()]


def odds_to_logit(p: float) -> float:
    return float(logit(p))
