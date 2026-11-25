import numpy as np
import pandas as pd

from meridian.features.cleaning import CONTINUOUS, COUNTS, RANDOM_MISSING, SHARES, PDCleaner


def _frame(n=2000, seed=0, shift=0.0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.lognormal(3 + shift, 1, n) for c in CONTINUOUS + COUNTS + SHARES})
    for c in SHARES:
        df[c] = rng.random(n)
    df["employment_years"] = np.where(rng.random(n) < 0.05, np.nan, rng.integers(0, 11, n))
    df["months_since_last_delinquency"] = np.where(rng.random(n) < 0.5, np.nan, rng.integers(0, 100, n))
    df["months_since_last_public_record"] = np.nan
    df["months_since_recent_inquiry"] = rng.integers(0, 24, n).astype(float)
    df["is_joint_application"] = False
    df["home_ownership"] = rng.choice(["MORTGAGE", "RENT", "OWN", "ANY"], n, p=[0.5, 0.4, 0.099, 0.001])
    df["loan_purpose"] = rng.choice(["debt_consolidation", "credit_card", "wedding"], n, p=[0.7, 0.299, 0.001])
    df["income_verification"] = rng.choice(["Verified", "Not Verified"], n)
    df["state_code"] = rng.choice(["CA", "TX", "NY"], n)
    for c in RANDOM_MISSING:
        df.loc[df.sample(frac=0.01, random_state=seed).index, c] = np.nan
    return df


def test_caps_are_learned_on_train_only():
    train, test = _frame(seed=1), _frame(seed=2, shift=2.0)
    cleaner = PDCleaner().fit(train)
    out = cleaner.transform(test)
    for c in CONTINUOUS:
        assert out[c].max() <= cleaner.upper_[c] + 1e-9
        assert out[c].min() >= cleaner.lower_[c] - 1e-9


def test_informative_missing_flags_and_random_imputation():
    df = _frame()
    out = PDCleaner().fit(df).transform(df)
    assert (out["has_delinquency_history"] == df["months_since_last_delinquency"].notna().astype(int)).all()
    assert out["months_since_last_delinquency"].isna().any(), "informative missingness must be kept"
    assert out[RANDOM_MISSING].isna().sum().sum() == 0


def test_rare_and_unseen_categories_collapse_to_other():
    train = _frame()
    cleaner = PDCleaner().fit(train)
    test = train.head(5).copy()
    test["loan_purpose"] = "never_seen_before"
    out = cleaner.transform(test)
    assert set(out["loan_purpose"].astype(str)) == {"OTHER"}
    assert "ANY" not in set(cleaner.transform(train)["home_ownership"].astype(str))
