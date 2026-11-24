"""Loan economics: turn predictions and outcomes into dollars.

Deliberately simple and fully transparent, so a finance stakeholder can audit
every assumption. Each assumption is a field with a documented default and is
exposed as a slider in the dashboard's ROI calculator.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass
class LoanEconomics:
    cost_of_funds: float = 0.025          # annual cost of funds (2016 bank funding plus spread)
    servicing_cost: float = 0.010         # annual servicing cost, share of average balance
    avg_balance_factor: float = 0.55      # average outstanding balance of an amortising loan / principal
    lgd: float = 0.90                     # loss given default (notebook 08: observed mean 0.90)
    ead_ratio: float = 0.72               # balance outstanding at default / principal (observed mean 0.72)
    months_paid_before_default: float = 18.0  # median months to charge-off, observed 18

    def profit(self, funded, rate, term_months, defaulted) -> np.ndarray:
        """Lifetime profit per loan in USD under the stated assumptions."""
        funded = np.asarray(funded, float)
        rate = np.asarray(rate, float)
        years = np.asarray(term_months, float) / 12
        bad = np.asarray(defaulted, bool)
        margin = rate - self.cost_of_funds - self.servicing_cost
        good_profit = funded * margin * self.avg_balance_factor * years
        paid_years = self.months_paid_before_default / 12
        bad_profit = funded * margin * paid_years * 0.85 - funded * self.ead_ratio * self.lgd
        return np.where(bad, bad_profit, good_profit)

    def expected_profit(self, funded, rate, term_months, pd_hat) -> np.ndarray:
        p = np.asarray(pd_hat, float)
        return (1 - p) * self.profit(funded, rate, term_months, False) + p * self.profit(funded, rate, term_months, True)

    def as_frame(self) -> pd.DataFrame:
        return pd.Series(asdict(self), name="value").to_frame()


def cutoff_curve(score, funded, profit, n_points: int = 101) -> pd.DataFrame:
    """Profit if Meridian approves only loans above each score cutoff (higher score = safer)."""
    order = np.argsort(-np.asarray(score))
    s, f, p = np.asarray(score)[order], np.asarray(funded)[order], np.asarray(profit)[order]
    cum_profit, cum_funded = np.cumsum(p), np.cumsum(f)
    idx = np.unique(np.linspace(0, len(s) - 1, n_points).astype(int))
    return pd.DataFrame({"approval_rate": (idx + 1) / len(s), "score_cutoff": s[idx],
                         "funded": cum_funded[idx], "profit": cum_profit[idx],
                         "profit_per_1bn": cum_profit[idx] / cum_funded[idx] * 1e9})


def budget_selection(rank_key, funded, realised_profit, defaulted, budget_share: float) -> dict:
    """Fund loans in order of rank_key (highest first) until budget_share of total volume is used."""
    rank_key, funded = np.asarray(rank_key, float), np.asarray(funded, float)
    order = np.argsort(-rank_key, kind="stable")
    k = int(np.searchsorted(np.cumsum(funded[order]), budget_share * funded.sum())) + 1
    sel = order[:k]
    profit = float(np.asarray(realised_profit)[sel].sum())
    deployed = float(funded[sel].sum())
    return {"loans_funded": k, "capital_deployed": deployed, "profit": profit,
            "profit_per_1bn": profit / deployed * 1e9, "default_rate": float(np.asarray(defaulted, float)[sel].mean())}
