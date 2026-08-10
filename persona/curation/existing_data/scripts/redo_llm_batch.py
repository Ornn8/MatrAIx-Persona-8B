#!/usr/bin/env python3
"""Redo low-grounded records in the LLM-rich CGSS subset (e.g. rows that hit API
402 mid-run). Re-runs the full Layer-2 pipeline for records with grounded < threshold
and writes a merged output file.

Usage:
  python redo_llm_batch.py --shards ../outputs/cgss2017_llm/shard_*.jsonl.gz \
      --rows ../outputs/cgss2017_pilot/rows_real.jsonl \
      --dataset crosswalks/cgss.py --out ../outputs/cgss2017_llm/merged.jsonl.gz \
      --threshold 60 --parallel 6
"""
from __future__ import annotations

import argparse
import gzip
import glob
import importlib.util
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crosswalk_engine import apply_crosswalk  # noqa: E402
from postprocess_engine import load_schema, normalize  # noqa: E402
from llm_infer_engine import infer  # noqa: E402

SCHEMA = r"..\..\..\schema\dimensions.json"


def _load_module(path):
    spec = importlib.util.spec_from_file_location("dataset_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--shards", required=True, help="glob of shard_*.jsonl.gz")
    ap.add_argument("--rows", required=True, help="rows_real.jsonl (source rows)")
    ap.add_argument("--dataset", required=True, help="crosswalk module path")
    ap.add_argument("--out", required=True, help="merged output .jsonl.gz")
    ap.add_argument("--threshold", type=int, default=60)
    ap.add_argument("--parallel", type=int, default=6)
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.normpath(os.path.join(base, SCHEMA))
    mod = _load_module(os.path.normpath(os.path.join(base, args.dataset)))
    order, allowed = load_schema(schema_path)

    shard_files = sorted(glob.glob(args.shards))
    recs: dict[str, dict] = {}
    for f in shard_files:
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                recs[rec["user_id"]] = rec
    print(f"loaded {len(recs)} records from {len(shard_files)} shards")

    rows = {r["user_id"]: r for r in (json.loads(l) for l in open(args.rows, encoding="utf-8"))}
    todo = [
        (uid, rec) for uid, rec in recs.items()
        if sum(1 for f in rec["fields"] if f["value"] is not None) < args.threshold
    ]
    print(f"redo todo: {len(todo)} (grounded < {args.threshold})")
    if not todo:
        print("nothing to redo")

    def process(uid: str) -> dict:
        row = rows[uid]
        observed, _, _ = apply_crosswalk(row, mod.CROSSWALK, allowed)
        profile_text = mod.render(row)
        raw = infer(profile_text, order, workers=1)
        fields = normalize(raw, order, allowed, profile_text=profile_text, observed=observed)
        return {"user_id": uid, "fields": fields, "observed": observed}

    t0 = time.time()
    lock = threading.Lock()
    n_done = 0

    def flush_record(rec):
        nonlocal n_done
        with lock:
            recs[rec["user_id"]] = rec
            n_done += 1
            g = sum(1 for f in rec["fields"] if f["value"] is not None)
            print(f"[{n_done}/{len(todo)}] {rec['user_id']} grounded={g} "
                  f"{(time.time()-t0)/60:.1f}m", flush=True)

    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futures = {ex.submit(process, uid): uid for uid, _ in todo}
        for f in as_completed(futures):
            flush_record(f.result())

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        for rec in sorted(recs.values(), key=lambda r: r["user_id"]):
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"merged {len(recs)} records -> {out} in {(time.time()-t0)/60:.1f}m")


if __name__ == "__main__":
    main()
