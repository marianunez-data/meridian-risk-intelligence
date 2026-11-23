"""Thin DuckDB helpers shared by notebooks, scripts and the app."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from meridian.config import SQL_DIR, WAREHOUSE_PATH


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Open the warehouse. Read-only by default so analysis can never mutate it."""
    return duckdb.connect(str(WAREHOUSE_PATH), read_only=read_only)


def load_sql(name: str) -> str:
    """Load a versioned query from sql/analysis/<name>.sql."""
    path = Path(SQL_DIR) / "analysis" / f"{name}.sql"
    return path.read_text(encoding="utf-8")


def run_sql(con: duckdb.DuckDBPyConnection, name_or_query: str, **params) -> pd.DataFrame:
    """Run a named query file or a raw SQL string and return a DataFrame."""
    query = load_sql(name_or_query) if name_or_query.isidentifier() else name_or_query
    return con.execute(query, params or None).df()
