#!/usr/bin/env python3
"""Convert the WVS wave-7 China sample CSV into the crosswalk input format.

Reads `raw/wvs/wvs7_china.csv` (filtered to B_COUNTRY_ALPHA=='CHN', 3,036 rows),
keeps only the columns `crosswalks/wvs_cn.py` consumes, maps WVS missing codes
(-1 don't know / -2 no answer / -3 not applicable / -4 not asked / -5 missing)
to None.

Usage:
  python wvs7_to_rows.py --csv ../raw/wvs/wvs7_china.csv \
      --out ../outputs/wvs_cn_pilot/rows_real.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

KEEP = [
    "Q260",  # sex 1=Male 2=Female
    "Q261",  # year of birth
    "Q262",  # age
    "Q57P",  # most people can be trusted (1=trust 2=careful)
    "Q97",   # religious denomination (0=none)
    "Q47P",  # state of health 1=Very good..5=Very poor (direction flagged)
    "H_URBRURAL",  # 1=urban 2=rural
    "I_WOMJOB", "I_WOMPOL", "I_WOMEDU",  # gender-equality indexes 0..1
    "I_RELIGPRAC",  # religiosity index 0..1 (direction flagged)
]
MISSING = {-1, -2, -3, -4, -5}


def _clean(v):
    if v is None:
        return None
    try:
        if v != v:  # NaN
            return None
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f in MISSING:
        return None
    if f.is_integer():
        return int(f)
    return f


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.csv, low_memory=False)
    missing = [c for c in KEEP if c not in df.columns]
    if missing:
        raise SystemExit(f"columns missing from csv: {missing}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "w", encoding="utf-8") as fh:
        for i, row in df[KEEP].iterrows():
            rec = {"user_id": f"wvs-cn-{int(i):05d}"}
            for col in KEEP:
                rec[col] = _clean(row[col])
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"✓ wrote {n:,} rows -> {out}")


if __name__ == "__main__":
    main()
