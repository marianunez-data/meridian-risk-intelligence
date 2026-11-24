"""Discrimination and calibration metrics used across every risk model."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score, roc_curve


def ks_statistic(y_true, score) -> float:
    """Kolmogorov-Smirnov: maximum gap between the cumulative bad and good distributions."""
    fpr, tpr, _ = roc_curve(y_true, score)
    return float(np.max(tpr - fpr))


def summary(y_true, pd_hat, name: str = "") -> dict:
    y = np.asarray(y_true, float)
    p = np.asarray(pd_hat, float)
    auc = roc_auc_score(y, p)
    return {
        "dataset": name,
        "loans": len(y),
        "observed_bad_rate": y.mean(),
        "predicted_bad_rate": p.mean(),
        "auc": auc,
        "gini": 2 * auc - 1,
        "ks": ks_statistic(y, p),
        "brier": brier_score_loss(y, p),
        "pr_auc": average_precision_score(y, p),
    }


def gains_table(y_true, pd_hat, n_bins: int = 10) -> pd.DataFrame:
    """Decile table sorted from riskiest to safest, the standard credit 'lift' view."""
    df = pd.DataFrame({"y": np.asarray(y_true, float), "p": np.asarray(pd_hat, float)})
    df["decile"] = pd.qcut(df.p.rank(method="first", ascending=False), n_bins, labels=range(1, n_bins + 1))
    g = df.groupby("decile", observed=True).agg(loans=("y", "size"), bads=("y", "sum"),
                                                 predicted_pd=("p", "mean"), min_pd=("p", "min"), max_pd=("p", "max"))
    g["bad_rate"] = g.bads / g.loans
    g["cum_share_of_bads"] = g.bads.cumsum() / g.bads.sum()
    g["cum_share_of_loans"] = g.loans.cumsum() / g.loans.sum()
    g["lift"] = g.bad_rate / (g.bads.sum() / g.loans.sum())
    return g


def calibration_table(y_true, pd_hat, n_bins: int = 10) -> pd.DataFrame:
    df = pd.DataFrame({"y": np.asarray(y_true, float), "p": np.asarray(pd_hat, float)})
    df["bin"] = pd.qcut(df.p.rank(method="first"), n_bins, labels=False)
    return df.groupby("bin").agg(predicted=("p", "mean"), observed=("y", "mean"), loans=("y", "size"))
