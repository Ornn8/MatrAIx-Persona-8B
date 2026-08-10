#!/usr/bin/env python3
"""Materialize the CGSS2017 LLM-rich subset as a Playground persona pool.

Reads the 200-person merged extraction (full 1290-dim records) and writes
`persona/datasets/cgss2017-llm/` as `persona_0001.yaml .. persona_0200.yaml`
plus `manifest.json`, following the existing pool contracts
(persona_1m_pool.py materialize_cohort / persona_pool_service.py save_pool_as_dataset):

* dimensions: flat {field_id: value} of non-null values (already schema-enum values)
* source: "cgss" (custom value; local-pool get_catalog derives filters from it)
* display_name: synthetic_display_name (East-Asia name pool, stable hash)
* provenance.origin_persona_id keeps the original cgss2017-xxxx id

Usage:
  python materialize_cgss_pool.py \
      --input ../outputs/cgss2017_llm/merged.jsonl.gz \
      --outdir ../../../../persona/datasets/cgss2017-llm
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from pathlib import Path

from matraix.persona_display_name import synthetic_display_name

CARD_DIMS = ["age_bracket", "region", "domain", "intent", "life_stage", "source"]
PERSONA_VERSION = "1.0"
SOURCE = "cgss"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    records = [json.loads(l) for l in gzip.open(args.input, "rt", encoding="utf-8")]
    records.sort(key=lambda r: r["user_id"])

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    personas = []
    source_counts: dict[str, int] = {}
    for i, rec in enumerate(records, 1):
        pid = f"{i:04d}"
        dims = {f["field_id"]: f["value"] for f in rec["fields"] if f["value"] is not None}
        display = synthetic_display_name(pid, dims)
        path = f"persona_{pid}.yaml"
        yaml_lines = [
            f"persona_id: '{pid}'",
            f"version: '{PERSONA_VERSION}'",
            f"source: {SOURCE}",
            f"display_name: {display}",
            "dimensions:",
        ]
        for k in sorted(dims):
            yaml_lines.append(f"  {k}: {dims[k]}")
        yaml_lines += [
            "provenance:",
            f"  parent_pool: persona/curation/existing_data/outputs/cgss2017_llm",
            f"  origin_persona_id: {rec['user_id']}",
        ]
        (outdir / path).write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

        source_counts[SOURCE] = source_counts.get(SOURCE, 0) + 1
        card = {"persona_id": pid, "path": path, "source": SOURCE, "display_name": display}
        for cd in CARD_DIMS:
            if cd in dims:
                card[cd] = dims[cd]
        personas.append(card)

    manifest = {
        "schema_version": PERSONA_VERSION,
        "personas": personas,
        "source_counts": source_counts,
        "smoke_persona_id": personas[0]["persona_id"] if personas else None,
        "notes": (
            "CGSS2017 LLM-rich subset: 200 stratified respondents, 44 observed dims + "
            "LLM-inferred (avg 105.4 grounded/1290). China-only cohort; keep isolated "
            "from non-China pools. Source: CNSDA CGSS2017 + DeepSeek inference layer."
        ),
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"✓ wrote {len(personas)} personas + manifest -> {outdir}")


if __name__ == "__main__":
    main()
