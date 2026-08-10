#!/usr/bin/env python3
"""End-to-end smoke check for the China persona pipeline deliverables.

Verifies (all read-only):
1. Each persona pool dir loads via the existing manifest loader (load_manifest).
2. A sample of personas from each pool renders through the full persona system
   template in both en and zh (Jinja macros incl. render_consumer_profile).
3. Consumer-profile block appears ONLY for the LLM-rich cgss pool and only when
   explicitly passed (China market-research opt-in / data isolation).
4. All dimension values in the pools are within the schema allowed values.

Usage:
  python smoke_china_pipeline.py
Exit code 0 = all checks passed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from matraix.persona_dimension_catalog import build_template_context_extras  # noqa: E402
from matraix.persona_job import load_manifest  # noqa: E402

POOLS = {
    "cgss2017-llm": (REPO / "persona" / "datasets" / "cgss2017-llm", True),
    "wvs-cn": (REPO / "persona" / "datasets" / "wvs-cn", False),
}
SCHEMA = yaml.safe_load((REPO / "persona" / "schema" / "dimensions.json").read_text(encoding="utf-8"))
ALLOWED = {d["id"]: set(d.get("values") or []) for d in SCHEMA["dimensions"]}
TEMPLATE_DIR = REPO / "environment" / "agents" / "matraix" / "agents" / "persona" / "templates"

FAILED: list[str] = []


def check(ok: bool, msg: str) -> None:
    tag = "OK " if ok else "FAIL"
    print(f"[{tag}] {msg}")
    if not ok:
        FAILED.append(msg)


def main() -> int:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape(["html", "xml"])
    )
    tpl = env.get_template("persona_system.md.j2")

    for pool_name, (pool_dir, has_consumer) in POOLS.items():
        # 1) manifest loader
        entries = load_manifest(pool_dir, repo_root=REPO)
        check(len(entries) > 0, f"{pool_name}: load_manifest -> {len(entries)} entries")
        if not entries:
            continue
        sources = {e.get("source") for e in entries}
        check(len(sources) == 1, f"{pool_name}: single source marker ({sources})")

        # 2) sample render en + zh
        samples = [e for e in entries if e["persona_id"] in {"0001", "0002", "0100"}]
        rendered_any = False
        for e in samples:
            ypath = pool_dir / e["path"]
            if not ypath.is_file():
                continue
            persona = yaml.safe_load(ypath.read_text(encoding="utf-8"))
            dims = persona.get("dimensions", {}) or {}
            cp = persona.get("consumer_profile")
            for lang in ("en", "zh"):
                ctx = build_template_context_extras(
                    dims, language=lang, consumer_profile=cp if has_consumer else None
                )
                ctx["dimensions"] = dims
                ctx["display_name"] = persona.get("display_name")
                out = tpl.render(**ctx)
                rendered_any = rendered_any or bool(out.strip())
                check("You are" in out or "你是" in out, f"{pool_name} {e['persona_id']}: {lang} identity line")
                if has_consumer:
                    expect_zh = "消费画像" in out if lang == "zh" else "Consumer profile" in out
                    check(expect_zh, f"{pool_name} {e['persona_id']}: {lang} consumer block present")
                else:
                    check("消费画像" not in out and "Consumer profile" not in out,
                          f"{pool_name} {e['persona_id']}: {lang} no consumer block (isolation)")
        check(rendered_any, f"{pool_name}: at least one persona rendered")

        # 4) schema value validity on all personas (sample up to 300)
        bad: list[str] = []
        for i, e in enumerate(entries[:300]):
            ypath = pool_dir / e["path"]
            if not ypath.is_file():
                continue
            persona = yaml.safe_load(ypath.read_text(encoding="utf-8"))
            for k, v in (persona.get("dimensions", {}) or {}).items():
                if k in ALLOWED and ALLOWED[k] and v not in ALLOWED[k]:
                    bad.append(f"{e['persona_id']}:{k}={v!r}")
        check(not bad, f"{pool_name}: schema values valid (first bad: {bad[:3]})")

    # 3) isolation: consumer block absent when not passed (cgss pool)
    cg_dir, _ = POOLS["cgss2017-llm"]
    persona = yaml.safe_load((cg_dir / "persona_0001.yaml").read_text(encoding="utf-8"))
    ctx = build_template_context_extras(persona["dimensions"], language="zh")
    ctx["dimensions"] = persona["dimensions"]
    ctx["display_name"] = persona.get("display_name")
    out = tpl.render(**ctx)
    check("消费画像" not in out, "isolation: consumer block absent when not passed")

    print()
    if FAILED:
        print(f"{len(FAILED)} checks FAILED:")
        for f in FAILED:
            print("  -", f)
        return 1
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
