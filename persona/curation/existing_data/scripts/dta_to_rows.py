#!/usr/bin/env python3
"""Convert the official CGSS2017 .dta into the crosswalk input format (rows.jsonl).

This is the production entry for the CGSS pipeline: read the official Stata file with
pyreadstat **without** value formats (`apply_value_formats=False`), so coded fields come
out as raw numeric codes (1/2/…, NaN for missing) — the crosswalk in `crosswalks/cgss.py`
matches those codes. Keep only the columns the cgss crosswalk consumes.

Usage:
  python dta_to_rows.py --dta ../raw/cgss2017/CGSS2017.dta \
      --out ../outputs/cgss2017_pilot/rows_real.jsonl
Then run the observed-only pipeline:
  python run_pipeline.py --source ../outputs/cgss2017_pilot/rows_real.jsonl \
      --dataset crosswalks/cgss.py --schema ../../../schema/dimensions.json \
      --out ../outputs/cgss2017_pilot/extraction_real.jsonl.gz --observed-only
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyreadstat

# columns consumed by crosswalks/cgss.py (raw numeric codes)
KEEP_2017 = [
    "id", "a2", "a31", "a4", "a7a", "a69",
    "a51", "a511", "a512", "a513", "a514", "a515", "a516", "a517",
    "a518", "a519", "a520", "a521",
    "a6", "a15", "v458", "a43e",
    # family / life events
    "a12a", "a121", "a128", "d4", "d24", "d61a", "d62a", "d131", "a21",
    "d3a1", "d3a2", "d3a3", "d3a4", "d3a5", "d3a6", "d3a7", "d3a8", "d3a9", "d3a10",
    "d3c1", "d3c2", "d3c3", "d3c4", "d3c5", "d3c6", "d3c7", "d3c8", "d3c9", "d3c10",
    "d3e1", "d3e2", "d3e3", "d3e4", "d3e5", "d3e6", "d3e7", "d3e8", "d3e9", "d3e10",
    "d5a1", "d5a2", "d5a3", "d5a4", "d5a5",
    "d5b1", "d5b2", "d5b3", "d5b4", "d5b5",
    # employment / career
    "a53", "a54", "a59a", "a59c", "a59e", "a59f", "a59j", "a59l",
    # media / internet
    "a283", "a284", "a29", "a30c", "a30e", "a30g", "a30h",
    "a301", "a302", "a304", "a308", "a309", "a3012",
    # attitudes
    "a17", "a16", "a421", "a422", "a423", "a424", "a425",
    "c32", "c34", "c58",
    "c491", "c492", "c493", "c494", "c495", "c496", "c497", "c498", "c499", "c4910", "c4911",
    "c621", "c622", "c623", "c624", "c625",
    "d161", "d162", "d163", "d164", "d202",
    "d381", "d382", "d383", "d384", "d385", "d386",
]

KEEP_2021 = [
    "id", "A2", "A3_1", "A4", "A7a", "A69", "A5", "A6", "A15", "E34", "P4c", "A43e",
    # family
    "A1",
    "A011601", "A011602", "A011603", "A011604", "A011605", "A011606", "A011607", "A011608",
    "A011609", "A011610", "A011611", "A011612", "A011613", "A011614",
    "A12_1", "A12_8",
    # employment
    "A53", "A54", "A59a", "A59c", "A59e", "A59f", "A59j", "A59L",
    # media / habits
    "A28_3", "A29", "A30b", "A30_4", "A30_8", "A30_12", "D23_b", "D23_a",
    # attitudes
    "A17", "A16", "A42_1", "A42_2", "A42_3", "A42_4", "A42_5",
]

VARIANTS = {"2017": KEEP_2017, "2021": KEEP_2021}


def _clean(v):
    """NaN/bytes -> None; integer-valued floats (1.0) -> int (1) so crosswalk
    string-key matching never sees '1.0'."""
    if v is None:
        return None
    try:
        if v != v:  # NaN
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, bytes):
        v = v.decode("utf-8", errors="replace")
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return v


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dta", required=True, help="path to CGSS2017.dta / CGSS2021.dta")
    ap.add_argument("--out", required=True, help="output rows.jsonl path")
    ap.add_argument("--variant", choices=sorted(VARIANTS), default="2017",
                    help="CGSS wave; selects the column list (default 2017)")
    args = ap.parse_args()

    keep = VARIANTS[args.variant]
    df, meta = pyreadstat.read_dta(args.dta, apply_value_formats=False)
    missing = [c for c in keep if c not in df.columns]
    if missing:
        raise SystemExit(f"columns missing from .dta: {missing}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    prefix = f"cgss{args.variant}-"
    with open(out, "w", encoding="utf-8") as fh:
        for _, row in df[keep].iterrows():
            rec = {"user_id": f"{prefix}{int(row['id'])}"}
            for col in keep[1:]:
                rec[col] = _clean(row[col])
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"✓ wrote {n:,} rows -> {out}  [{args.variant}]")


if __name__ == "__main__":
    main()
