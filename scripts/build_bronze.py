"""Raw -> Bronze: convert every raw file to typed, compressed Parquet.

Bronze keeps the data exactly as delivered (no filtering, no renaming), only
in a columnar format that is ~5x smaller and ~20x faster to query. All
business logic lives downstream in dbt (silver = staging, gold = marts).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from meridian import config  # noqa: E402

RAW, BRONZE = config.RAW_DIR, config.BRONZE_DIR


def copy(con: duckdb.DuckDBPyConnection, select_sql: str, name: str) -> None:
    t0 = time.time()
    out = BRONZE / f"{name}.parquet"
    con.execute(f"COPY ({select_sql}) TO '{out}' (FORMAT parquet, COMPRESSION zstd)")
    rows = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
    print(f"  {name:<28} {rows:>12,} rows  {out.stat().st_size / 1e6:>8,.1f} MB  {time.time() - t0:5.1f}s")


def main(only: list[str] | None = None) -> None:
    BRONZE.mkdir(parents=True, exist_ok=True)
    config.WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)  # dbt needs the folder to exist
    (config.DATA_DIR / "features").mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order = false")
    want = lambda name: only is None or name in only  # noqa: E731

    # Lending Club: full-file type inference so sparse late columns are typed correctly.
    if want("lendingclub"):
        copy(con, f"SELECT * FROM read_csv('{RAW}/lendingclub/accepted_2007_to_2018Q4.csv', "
                  "header=true, sample_size=-1)", "lending_club_loans")
    if want("paysim"):
        copy(con, f"SELECT * FROM read_csv('{RAW}/paysim/paysim.csv', header=true)", "paysim_transactions")

    fred_union = " UNION ALL ".join(
        f"SELECT '{s}' AS series_id, CAST(observation_date AS DATE) AS observation_date, "
        f"TRY_CAST({s} AS DOUBLE) AS value FROM read_csv('{RAW}/fred/{s}.csv', header=true, all_varchar=true)"
        for s in config.FRED_SERIES
    )
    if want("fred"):
        copy(con, fred_union, "fred_series")

    for part in ("sub", "num") if want("sec") else ():
        files = [str(RAW / "sec" / q / f"{part}.txt") for q in config.SEC_QUARTERS]
        copy(con, f"SELECT *, regexp_extract(filename, '(\\d{{4}}q\\d)', 1) AS source_quarter "
                  f"FROM read_csv({files}, delim='\\t', header=true, quote='', all_varchar=true, filename=true)",
             f"sec_{part}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", choices=["lendingclub", "paysim", "fred", "sec"])
    main(parser.parse_args().only)
