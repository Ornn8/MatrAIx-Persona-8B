#!/usr/bin/env python3
"""Materialize an extraction output as a Playground persona pool.

Generic version of materialize_cgss_pool.py (which is kept as-is for the
CGSS2017 LLM-rich pool). Reads a validated extraction jsonl.gz (full 1290-dim
records) and writes `<outdir>/persona_0001.yaml ..` plus `manifest.json`
following the existing pool contracts:

* dimensions: flat {field_id: value} of non-null values (schema-enum values)
* source: cohort marker (e.g. "cgss", "wvs_cn") — keeps China cohorts isolated
* display_name: synthetic_display_name (East-Asia name pool, stable hash)
* provenance.origin_persona_id keeps the original dataset row id

Usage:
  python materialize_pool.py \
      --input ../outputs/wvs_cn_pilot/extraction_real.jsonl.gz \
      --outdir ../../../../persona/datasets/wvs-cn \
      --source wvs_cn \
      --notes "WVS wave-7 China cohort: 3036 respondents, 9 observed dims, no LLM enrichment."
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

from matraix.persona_display_name import synthetic_display_name

CARD_DIMS = ["age_bracket", "region", "domain", "intent", "life_stage", "source"]
PERSONA_VERSION = "1.0"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--source", required=True, help="cohort marker, e.g. cgss / wvs_cn")
    ap.add_argument("--notes", default="")
    ap.add_argument("--origin-tag", default="", help="display tag for provenance.origin_persona_id")
    args = ap.parse_args()

    records = [json.loads(l) for l in gzip.open(args.input, "rt", encoding="utf-8")]
    records.sort(key=lambda r: r["user_id"])

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    personas = []
    for i, rec in enumerate(records, 1):
        pid = f"{i:04d}"
        dims = {f["field_id"]: f["value"] for f in rec["fields"] if f["value"] is not None}
        display = synthetic_display_name(pid, dims)
        path = f"persona_{pid}.yaml"
        yaml_lines = [
            f"persona_id: '{pid}'",
            f"version: '{PERSONA_VERSION}'",
            f"source: {args.source}",
            f"display_name: {display}",
            "dimensions:",
        ]
        for k in sorted(dims):
            yaml_lines.append(f"  {k}: {dims[k]}")
        yaml_lines += [
            "provenance:",
            f"  parent_pool: {args.origin_tag or args.source}",
            f"  origin_persona_id: {rec['user_id']}",
        ]
        (outdir / path).write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

        card = {"persona_id": pid, "path": path, "source": args.source, "display_name": display}
        for cd in CARD_DIMS:
            if cd in dims:
                card[cd] = dims[cd]
        personas.append(card)

    manifest = {
        "schema_version": PERSONA_VERSION,
        "personas": personas,
        "source_counts": {args.source: len(personas)},
        "smoke_persona_id": personas[0]["persona_id"] if personas else None,
        "notes": args.notes,
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"✓ wrote {len(personas)} personas + manifest -> {outdir}")


if __name__ == "__main__":
    sys.exit(main())
