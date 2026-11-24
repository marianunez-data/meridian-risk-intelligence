"""Weight of Evidence (WoE) binning and Information Value (IV).

The standard encoding for bank application scorecards:

* Each variable is cut into a small number of bins.
* For numeric variables the bad rate must move in one direction across bins
  (monotonic), so the scorecard never rewards a borrower for getting riskier.
* Missing values get their own bin, so "not reported" can carry its own risk.
* Each bin is replaced by WoE = ln(share of goods in bin / share of bads in bin).
  Positive WoE means safer than average, negative means riskier.
* IV = sum over bins of (share of goods - share of bads) * WoE measures how
  much a variable separates goods from bads.

Rules of thumb for IV: < 0.02 useless, 0.02-0.1 weak, 0.1-0.3 medium,
0.3-0.5 strong, > 0.5 suspicious (check for leakage).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

EPS = 0.5  # Laplace smoothing so empty cells never produce log(0)


@dataclass
class VariableBinning:
    name: str
    kind: str                                   # "numeric" or "categorical"
    edges: list[float] = field(default_factory=list)       # numeric: inner cut points
    groups: list[list[str]] = field(default_factory=list)  # categorical: levels per bin
    woe: list[float] = field(default_factory=list)          # one per bin, same order as table
    woe_missing: float = 0.0
    iv: float = 0.0
    direction: int = 0                          # +1 bad rate rises with value, -1 falls
    table: list[dict] = field(default_factory=list)

    def labels(self) -> list[str]:
        if self.kind == "numeric":
            e = [-np.inf] + self.edges + [np.inf]
            return [f"[{_fmt(a)}, {_fmt(b)})" for a, b in zip(e[:-1], e[1:])]
        return [", ".join(g) for g in self.groups]


def _fmt(v: float) -> str:
    if np.isinf(v):
        return "-inf" if v < 0 else "+inf"
    return f"{v:,.4g}"


def _stats(bad: np.ndarray, n: np.ndarray, tot_bad: float, tot_good: float):
    good = n - bad
    dist_bad = (bad + EPS) / (tot_bad + EPS * len(n))
    dist_good = (good + EPS) / (tot_good + EPS * len(n))
    woe = np.log(dist_good / dist_bad)
    iv = (dist_good - dist_bad) * woe
    return woe, iv


class WoEBinner:
    """Fit monotonic WoE bins for many variables at once."""

    def __init__(self, max_bins: int = 8, initial_bins: int = 20, min_bin_share: float = 0.05,
                 min_cat_share: float = 0.02):
        self.max_bins = max_bins
        self.initial_bins = initial_bins
        self.min_bin_share = min_bin_share
        self.min_cat_share = min_cat_share
        self.binnings_: dict[str, VariableBinning] = {}

    # ------------------------------------------------------------------ fit
    def fit(self, X: pd.DataFrame, y: pd.Series, numeric: list[str], categorical: list[str]) -> WoEBinner:
        y = pd.Series(np.asarray(y, dtype=float), index=X.index)
        self.tot_bad_, self.tot_good_ = y.sum(), (1 - y).sum()
        for col in numeric:
            self.binnings_[col] = self._fit_numeric(X[col].astype(float), y, col)
        for col in categorical:
            self.binnings_[col] = self._fit_categorical(X[col].astype(str), y, col)
        return self

    def _fit_numeric(self, x: pd.Series, y: pd.Series, name: str) -> VariableBinning:
        present = x.notna()
        xv, yv = x[present].to_numpy(), y[present].to_numpy()
        qs = np.unique(np.quantile(xv, np.linspace(0, 1, self.initial_bins + 1)[1:-1]))
        edges = list(qs)
        direction = int(np.sign(pd.Series(xv).corr(pd.Series(yv), method="spearman")) or 1)

        def agg(edges):
            idx = np.searchsorted(np.asarray(edges), xv, side="right")
            n = np.bincount(idx, minlength=len(edges) + 1).astype(float)
            b = np.bincount(idx, weights=yv, minlength=len(edges) + 1)
            return n, b

        # Drop empty bins created by repeated quantiles.
        n, b = agg(edges)
        while len(edges) and (n == 0).any():
            i = int(np.argmax(n == 0))
            edges.pop(min(i, len(edges) - 1))
            n, b = agg(edges)

        # 1) Enforce monotonic bad rate by merging the first violating pair.
        changed = True
        while changed and edges:
            changed = False
            rate = b / n
            diffs = np.diff(rate) * direction
            bad_idx = np.where(diffs < 0)[0]
            if len(bad_idx):
                edges.pop(int(bad_idx[0]))
                n, b = agg(edges)
                changed = True
        # 2) Enforce a minimum bin size and a maximum number of bins by merging
        #    the smallest bin into the neighbour with the closest bad rate.
        while edges and ((n / n.sum()).min() < self.min_bin_share or len(n) > self.max_bins):
            i = int(np.argmin(n))
            rate = b / n
            if i == 0:
                j = 0
            elif i == len(n) - 1:
                j = i - 1
            else:
                j = i - 1 if abs(rate[i] - rate[i - 1]) <= abs(rate[i] - rate[i + 1]) else i
            edges.pop(j)
            n, b = agg(edges)

        woe, iv = _stats(b, n, self.tot_bad_, self.tot_good_)
        table = [{"bin": lbl, "loans": int(nn), "bads": int(bb), "bad_rate": bb / nn, "woe": w, "iv": v}
                 for lbl, nn, bb, w, v in zip(VariableBinning(name, "numeric", edges).labels(), n, b, woe, iv)]
        woe_missing, iv_missing = 0.0, 0.0
        if (~present).sum() > 0:
            nm, bm = float((~present).sum()), float(y[~present].sum())
            wm, im = _stats(np.array([bm]), np.array([nm]), self.tot_bad_, self.tot_good_)
            woe_missing, iv_missing = float(wm[0]), float(im[0])
            table.append({"bin": "Missing", "loans": int(nm), "bads": int(bm), "bad_rate": bm / nm,
                          "woe": woe_missing, "iv": iv_missing})
        return VariableBinning(name, "numeric", [float(e) for e in edges], [], [float(w) for w in woe],
                               woe_missing, float(iv.sum() + iv_missing), direction, table)

    def _fit_categorical(self, x: pd.Series, y: pd.Series, name: str) -> VariableBinning:
        g = pd.DataFrame({"x": x, "y": y}).groupby("x")["y"].agg(["size", "sum"]).rename(columns={"size": "n", "sum": "b"})
        g["rate"] = g.b / g.n
        g = g.sort_values("rate")
        # Merge small levels into the neighbour with the closest bad rate.
        groups = [[str(i)] for i in g.index]
        n, b = g.n.to_numpy(float).tolist(), g.b.to_numpy(float).tolist()
        while len(n) > 1 and (min(n) / sum(n) < self.min_cat_share or len(n) > self.max_bins):
            i = int(np.argmin(n))
            rates = [bb / nn for bb, nn in zip(b, n)]
            if i == 0:
                j = 1
            elif i == len(n) - 1:
                j = i - 1
            else:
                j = i - 1 if abs(rates[i] - rates[i - 1]) <= abs(rates[i] - rates[i + 1]) else i + 1
            lo, hi = sorted((i, j))
            groups[lo] = groups[lo] + groups[hi]
            n[lo] += n[hi]
            b[lo] += b[hi]
            del groups[hi], n[hi], b[hi]
        n_arr, b_arr = np.array(n), np.array(b)
        woe, iv = _stats(b_arr, n_arr, self.tot_bad_, self.tot_good_)
        table = [{"bin": ", ".join(gr), "loans": int(nn), "bads": int(bb), "bad_rate": bb / nn, "woe": w, "iv": v}
                 for gr, nn, bb, w, v in zip(groups, n_arr, b_arr, woe, iv)]
        return VariableBinning(name, "categorical", [], groups, [float(w) for w in woe], 0.0, float(iv.sum()), 0, table)

    # ------------------------------------------------------------ transform
    def transform(self, X: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
        out = {}
        for col in columns or list(self.binnings_):
            vb = self.binnings_[col]
            if vb.kind == "numeric":
                x = X[col].astype(float).to_numpy()
                idx = np.searchsorted(np.asarray(vb.edges), x, side="right")
                w = np.asarray(vb.woe)[np.clip(idx, 0, len(vb.woe) - 1)]
                w = np.where(np.isnan(x), vb.woe_missing, w)
            else:
                lookup = {lvl: woe for grp, woe in zip(vb.groups, vb.woe) for lvl in grp}
                w = X[col].astype(str).map(lookup).fillna(0.0).to_numpy()  # unseen level = average risk
            out[col] = w.astype(np.float32)
        return pd.DataFrame(out, index=X.index)

    def bin_index(self, X: pd.DataFrame, col: str) -> np.ndarray:
        """Bin number per row (missing = last), used for stability checks."""
        vb = self.binnings_[col]
        if vb.kind == "numeric":
            x = X[col].astype(float).to_numpy()
            idx = np.searchsorted(np.asarray(vb.edges), x, side="right")
            return np.where(np.isnan(x), len(vb.woe), idx)
        lookup = {lvl: i for i, grp in enumerate(vb.groups) for lvl in grp}
        return X[col].astype(str).map(lookup).fillna(len(vb.groups)).to_numpy(int)

    def iv_table(self) -> pd.DataFrame:
        rows = [{"variable": k, "kind": v.kind, "bins": len(v.woe) + (1 if any(t["bin"] == "Missing" for t in v.table) else 0),
                 "iv": v.iv} for k, v in self.binnings_.items()]
        df = pd.DataFrame(rows).sort_values("iv", ascending=False).reset_index(drop=True)
        df["strength"] = pd.cut(df.iv, [-1, 0.02, 0.1, 0.3, 0.5, 99],
                                labels=["Useless", "Weak", "Medium", "Strong", "Suspicious"])
        return df

    # ---------------------------------------------------------------- io
    def save(self, path: Path) -> None:
        payload = {k: asdict(v) for k, v in self.binnings_.items()}
        Path(path).write_text(json.dumps(payload, indent=1, default=float))

    @classmethod
    def load(cls, path: Path) -> WoEBinner:
        obj = cls()
        obj.binnings_ = {k: VariableBinning(**v) for k, v in json.loads(Path(path).read_text()).items()}
        return obj


def psi(expected: np.ndarray, actual: np.ndarray) -> float:
    """Population Stability Index between two discrete distributions (bin shares)."""
    e = np.clip(np.asarray(expected, float), 1e-6, None)
    a = np.clip(np.asarray(actual, float), 1e-6, None)
    e, a = e / e.sum(), a / a.sum()
    return float(np.sum((a - e) * np.log(a / e)))
