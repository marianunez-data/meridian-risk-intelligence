import numpy as np
import pandas as pd

from meridian.features.woe import WoEBinner, psi


def _data(n=20000, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    y = (rng.random(n) < 1 / (1 + np.exp(-(-2.5 + 1.2 * x)))).astype(int)
    x[rng.random(n) < 0.05] = np.nan
    cat = np.where(x > 0.5, "risky", np.where(x < -0.5, "safe", "mid"))
    return pd.DataFrame({"x": x, "cat": cat}), pd.Series(y)


def test_numeric_bins_are_monotonic_and_have_missing_bin():
    X, y = _data()
    b = WoEBinner().fit(X, y, ["x"], ["cat"]).binnings_["x"]
    rates = [t["bad_rate"] for t in b.table if t["bin"] != "Missing"]
    assert all(np.diff(rates) >= 0), "bad rate must rise with x"
    assert any(t["bin"] == "Missing" for t in b.table)
    assert b.iv > 0.1


def test_woe_sign_convention_positive_is_safer():
    X, y = _data()
    binner = WoEBinner().fit(X, y, ["x"], ["cat"])
    w = binner.transform(pd.DataFrame({"x": [-3.0, 3.0], "cat": ["safe", "risky"]}))
    assert w.loc[0, "x"] > 0 > w.loc[1, "x"]
    assert w.loc[0, "cat"] > w.loc[1, "cat"]


def test_unseen_category_gets_neutral_woe():
    X, y = _data()
    binner = WoEBinner().fit(X, y, ["x"], ["cat"])
    assert binner.transform(pd.DataFrame({"x": [0.0], "cat": ["new"]}), ["cat"]).iloc[0, 0] == 0.0


def test_psi_zero_for_identical_and_positive_for_shift():
    assert abs(psi([10, 20, 30], [10, 20, 30])) < 1e-12
    assert psi([10, 20, 30], [30, 20, 10]) > 0.25
