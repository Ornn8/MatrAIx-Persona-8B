#!/usr/bin/env python3
"""Run the LLM inference layer (Layer-2) for a stratified sample of CGSS rows.

Produces full 1290-dim records (observed + LLM-inferred, evidence-grounded) as
the rich-persona subset of the CGSS pipeline. Stratified by age_bracket x gender,
processed with **person-level parallelism** (each person's 9 chunks run serially,
multiple people in parallel) — balances throughput vs DeepSeek rate limits.
Resumable: skips user_ids already written to shard files.

Usage:
  python run_llm_batch.py --variant 2017 --n 200 --batch-size 10 --parallel 6 \
      --outdir ../outputs/cgss2017_llm
"""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crosswalk_engine import apply_crosswalk  # noqa: E402
from postprocess_engine import load_schema, normalize  # noqa: E402
from llm_infer_engine import infer  # noqa: E402

ROWS = {
    "2017": r"..\outputs\cgss2017_pilot\rows_real.jsonl",
    "2021": r"..\outputs\cgss2021_pilot\rows_real.jsonl",
}
CROSSWALK = {
    "2017": os.path.join(os.path.dirname(os.path.abspath(__file__)), "crosswalks", "cgss.py"),
    "2021": os.path.join(os.path.dirname(os.path.abspath(__file__)), "crosswalks", "cgss2021.py"),
}
SCHEMA = r"..\..\..\schema\dimensions.json"


def _load_module(path):
    spec = importlib.util.spec_from_file_location("dataset_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _strata(row):
    """(age_bracket, gender) bucket for stratified sampling."""
    try:
        year = int(float(str(row.get("a31") or row.get("A3_1") or 0)))
        age = (2017 if "a31" in row else 2021) - year
    except (TypeError, ValueError):
        age = None
    if age is None or not (18 <= age <= 100):
        age_b = "unknown"
    elif age < 25:
        age_b = "18-24"
    elif age < 35:
        age_b = "25-34"
    elif age < 45:
        age_b = "35-44"
    elif age < 55:
        age_b = "45-54"
    elif age < 65:
        age_b = "55-64"
    else:
        age_b = "65+"
    g = {1: "M", 2: "F"}.get(row.get("a2") or row.get("A2"))
    return (age_b, g or "U")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--variant", choices=sorted(ROWS), default="2017")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--parallel", type=int, default=6, help="people processed concurrently")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    rows_path = os.path.normpath(os.path.join(base, ROWS[args.variant]))
    schema_path = os.path.normpath(os.path.join(base, SCHEMA))
    mod = _load_module(os.path.normpath(os.path.join(base, CROSSWALK[args.variant])))

    all_rows = [json.loads(l) for l in open(rows_path, encoding="utf-8")]
    order, allowed = load_schema(schema_path)

    # stratified sample
    buckets: dict[tuple, list] = {}
    for row in all_rows:
        buckets.setdefault(_strata(row), []).append(row)
    rng = random.Random(args.seed)
    sample: list[dict] = []
    pool = {k: list(v) for k, v in buckets.items()}
    while len(sample) < args.n and pool:
        for k in list(pool):
            if not pool[k]:
                del pool[k]
                continue
            idx = rng.randrange(len(pool[k]))
            sample.append(pool[k].pop(idx))
            if len(sample) >= args.n:
                break
    if len(sample) < args.n:
        rest = [r for r in all_rows if r not in sample]
        sample += rng.sample(rest, args.n - len(sample))

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    done = set()
    for f in outdir.glob("shard_*.jsonl.gz"):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                done.add(json.loads(line)["user_id"])

    todo = [r for r in sample if r["user_id"] not in done]
    print(f"sample={len(sample)} done={len(done)} todo={len(todo)} "
          f"parallel={args.parallel} ({len(all_rows):,} source rows; {len(buckets)} strata)",
          flush=True)

    def process_one(row: dict) -> dict:
        observed, _, _ = apply_crosswalk(row, mod.CROSSWALK, allowed)
        profile_text = mod.render(row)
        raw = infer(profile_text, order, workers=1)  # chunk-serial per person
        fields = normalize(raw, order, allowed, profile_text=profile_text, observed=observed)
        return {"user_id": row["user_id"], "fields": fields, "observed": observed}

    t0 = time.time()
    lock = threading.Lock()
    shard_idx = len(list(outdir.glob("shard_*.jsonl.gz")))
    batch: list[dict] = []
    n_done = 0
    total = len(todo)

    def flush():
        nonlocal batch, shard_idx
        if not batch:
            return
        out = outdir / f"shard_{shard_idx:03d}.jsonl.gz"
        with gzip.open(out, "wt", encoding="utf-8") as fh:
            for rec in batch:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        shard_idx += 1
        batch = []

    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futures = {ex.submit(process_one, r): r for r in todo}
        for f in as_completed(futures):
            rec = f.result()
            with lock:
                batch.append(rec)
                n_done += 1
                grounded = sum(1 for ff in rec["fields"] if ff["value"] is not None)
                print(f"[{n_done}/{total}] {rec['user_id']} grounded={grounded} "
                      f"{(time.time()-t0)/60:.1f}m", flush=True)
                if len(batch) >= args.batch_size:
                    flush()
        flush()
    print(f"DONE {n_done} in {(time.time()-t0)/60:.1f}m -> {outdir}", flush=True)


if __name__ == "__main__":
    main()
