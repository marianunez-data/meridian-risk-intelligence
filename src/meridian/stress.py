"""Macro stress testing: satellite model and scenario application.

Lending Club's history (2007-2018) contains no full recession for its book and
its vintages deteriorated while unemployment fell, so its own data cannot
identify macro sensitivity. The satellite model is therefore estimated on an
industry proxy with complete credit cycles (FRED CORCCACBS, credit card
charge-off rate, all US commercial banks, 1985 onwards) and transferred to Meridian's
PDs as a multiplier.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass
class Scenario:
    name: str
    unemployment_rate: float
    use_downturn_lgd: bool
    description: str


SCENARIOS = [
    Scenario("Baseline", 3.9, False, "Unemployment stays at its March 2019 level"),
    Scenario("Adverse", 7.0, True, "Moderate recession, unemployment rises about 3 points"),
    Scenario("Severely adverse", 10.0, True, "2008-09 style recession, unemployment peaks at 10%"),
]


@dataclass
class SatelliteModel:
    """Year-over-year change in log charge-off rate explained by the change in unemployment.

        ln(CO_t) - ln(CO_t-4) = a + b * (U_t - U_t-4)

    Fitted on changes rather than levels because the charge-off level drifts for
    reasons unrelated to the cycle (product mix, regulation). The slope b is the
    elasticity transferred to Meridian's PDs: multiplier = exp(b * delta U).
    """
    intercept: float = 0.0
    slope: float = 0.0
    r_squared: float = 0.0
    n_quarters: int = 0
    baseline_unemployment: float = 3.9

    @classmethod
    def fit(cls, macro: pd.DataFrame, baseline_unemployment: float = 3.9) -> SatelliteModel:
        q = macro.set_index("month")[["card_chargeoff_rate", "unemployment_rate"]].resample("QS").mean()
        df = pd.DataFrame({"dy": np.log(q.card_chargeoff_rate).diff(4), "du": q.unemployment_rate.diff(4)}).dropna()
        res = sm.OLS(df.dy, sm.add_constant(df.du)).fit()
        return cls(float(res.params["const"]), float(res.params["du"]), float(res.rsquared), len(df),
                   baseline_unemployment)

    def multiplier(self, unemployment_rate) -> np.ndarray:
        """Default-rate multiplier relative to the baseline unemployment level."""
        return np.exp(self.slope * (np.asarray(unemployment_rate, float) - self.baseline_unemployment))


def stressed_expected_loss(book: pd.DataFrame, model: SatelliteModel, scenario: Scenario) -> pd.Series:
    """Per-loan expected loss under a scenario.

    Book needs pd_remaining, lgd, lgd_downturn, outstanding_principal and, optionally,
    share_in_horizon: the part of each loan's remaining default risk that falls
    inside the scenario horizon. Only that part is stressed; defaults expected
    after the recession keep their baseline probability.
    """
    h = book["share_in_horizon"] if "share_in_horizon" in book else 1.0
    m = model.multiplier(scenario.unemployment_rate)
    pd_s = np.clip(book.pd_remaining * (h * m + (1 - h)), 0, 1)
    lgd = book.lgd_downturn if scenario.use_downturn_lgd else book.lgd
    return pd_s * lgd * book.outstanding_principal


def share_in_horizon(term_months, months_on_book, loan_status, curves: pd.DataFrame, horizon: int = 24) -> np.ndarray:
    """Share of each loan's remaining default risk expected inside the scenario horizon.

    curves: columns term_months, months_on_book, share (cumulative share of lifetime
    defaults already happened by that age, from mature vintages).
    Loans already late are treated as fully inside the horizon.
    """
    out = np.empty(len(term_months))
    for term in (36, 60):
        c = curves[curves.term_months == term]
        m = np.asarray(term_months) == term
        now = np.interp(np.asarray(months_on_book)[m], c.months_on_book, c.share)
        later = np.interp(np.asarray(months_on_book)[m] + horizon, c.months_on_book, c.share)
        with np.errstate(divide="ignore", invalid="ignore"):
            out[m] = np.where(now < 1, (later - now) / np.maximum(1 - now, 1e-9), 1.0)
    late = pd.Series(loan_status).astype(str).str.startswith("Late").to_numpy()
    out[late] = 1.0
    return out
