"""Download every raw dataset into data/raw/. Idempotent: skips files that exist.

Usage:
    python scripts/download_data.py            # everything
    python scripts/download_data.py --only fred sec
"""
from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from meridian import config  # noqa: E402

CHUNK = 1 << 20


def _stream(url: str, dest: Path, headers: dict | None = None) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip  {dest.relative_to(config.PROJECT_ROOT)} (exists)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=120, headers=headers) as r:
        r.raise_for_status()
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(CHUNK):
                fh.write(chunk)
    tmp.rename(dest)
    print(f"  done  {dest.relative_to(config.PROJECT_ROOT)} ({dest.stat().st_size / 1e6:,.0f} MB)")


def lending_club() -> None:
    _stream(config.LENDING_CLUB_URL, config.RAW_DIR / "lendingclub" / "accepted_2007_to_2018Q4.csv")


def paysim() -> None:
    _stream(config.PAYSIM_URL, config.RAW_DIR / "paysim" / "paysim.csv")


def fred() -> None:
    for series in config.FRED_SERIES:
        _stream(config.FRED_URL.format(series=series), config.RAW_DIR / "fred" / f"{series}.csv")


def sec() -> None:
    headers = {"User-Agent": config.SEC_USER_AGENT}
    for quarter in config.SEC_QUARTERS:
        out_dir = config.RAW_DIR / "sec" / quarter
        if (out_dir / "num.txt").exists():
            print(f"  skip  sec/{quarter} (exists)")
            continue
        r = requests.get(config.SEC_FSDS_URL.format(quarter=quarter), headers=headers, timeout=300)
        r.raise_for_status()
        out_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            zf.extractall(out_dir, members=[m for m in zf.namelist() if m in {"sub.txt", "num.txt"}])
        print(f"  done  sec/{quarter}")


SOURCES = {"lendingclub": lending_club, "paysim": paysim, "fred": fred, "sec": sec}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", choices=SOURCES, default=list(SOURCES))
    args = parser.parse_args()
    for name in args.only:
        print(f"[{name}]")
        SOURCES[name]()
