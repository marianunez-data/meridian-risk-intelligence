"""Load modelling datasets from the warehouse with memory-friendly dtypes."""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from meridian.db import connect

ID_COLS = ["loan_id", "issue_month", "dataset_split"]
TARGET = "target_bad_24m"
BENCHMARK_COLS = ["benchmark_grade", "benchmark_sub_grade", "benchmark_interest_rate"]


def _shrink(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.select_dtypes("float64").columns:
        df[col] = df[col].astype(np.float32)
    for col in df.select_dtypes("int64").columns:
        if col != "loan_id":
            df[col] = pd.to_numeric(df[col], downcast="integer")
    for col in df.select_dtypes("object").columns:
        if col not in ID_COLS:
            df[col] = df[col].astype("category")
    return df


def load_pd_split(split: str, con: duckdb.DuckDBPyConnection | None = None,
                  labelled_only: bool = True) -> pd.DataFrame:
    """Load one split of gold.mart_pd_features.

    Train is restricted to the full-bureau era (2012+), as decided in the
    data audit. Monitoring rows have no mature label unless labelled_only.
    """
    con = con or connect()
    where = [f"dataset_split = '{split}'"]
    if split == "train":
        where.append("is_full_bureau_era")
    if labelled_only:
        where.append("target_bad_24m is not null")
    df = con.execute(f"select * exclude (is_full_bureau_era) from gold.mart_pd_features where {' and '.join(where)}").df()
    if labelled_only or split != "monitoring":
        df[TARGET] = df[TARGET].astype("Int8")
    return _shrink(df)
