import numpy as np
import pandas as pd

from meridian.economics import LoanEconomics, budget_selection
from meridian.stress import SatelliteModel, share_in_horizon


def test_good_loans_earn_and_bad_loans_lose():
    eco = LoanEconomics()
    good, bad = eco.profit([10000, 10000], [0.12, 0.12], [36, 36], [False, True])
    assert good > 0 > bad


def test_expected_profit_falls_with_pd():
    eco = LoanEconomics()
    p = eco.expected_profit([10000] * 3, [0.15] * 3, [36] * 3, [0.01, 0.10, 0.40])
    assert p[0] > p[1] > p[2]


def test_budget_selection_respects_budget():
    rng = np.random.default_rng(0)
    funded = rng.uniform(1000, 30000, 1000)
    res = budget_selection(rng.random(1000), funded, rng.normal(0, 1, 1000), rng.random(1000) < 0.1, 0.5)
    assert 0.5 * funded.sum() <= res["capital_deployed"] <= 0.5 * funded.sum() + funded.max()


def test_multiplier_is_one_at_baseline_and_rises_with_unemployment():
    sat = SatelliteModel(slope=0.17, baseline_unemployment=3.9)
    assert np.isclose(sat.multiplier(3.9), 1.0)
    assert sat.multiplier(10.0) > sat.multiplier(7.0) > 1.0


def test_share_in_horizon_bounds():
    curves = pd.DataFrame({"term_months": [36] * 37 + [60] * 61,
                           "months_on_book": list(range(37)) + list(range(61)),
                           "share": list(np.linspace(0, 1, 37)) + list(np.linspace(0, 1, 61))})
    h = share_in_horizon(np.array([36, 60, 36]), np.array([0, 10, 5]), ["Current", "Current", "Late (31-120 days)"], curves)
    assert ((h >= 0) & (h <= 1)).all()
    assert h[2] == 1.0
