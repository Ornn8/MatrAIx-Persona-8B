#!/usr/bin/env python3
"""Generate persona/schema/labels_zh.json — Chinese labels + value translations for
the 1290-dim schema, using the DeepSeek endpoint configured in
application/playground/.env.local (same as llm_infer_engine).

Output shape:
{
  "age_bracket": {"label": "年龄段", "values": {"Under 5": "5岁以下", ...}},
  ...
}

Rules for the model: translate labels and generic values; keep proper nouns /
brands / language names / code identifiers verbatim (e.g. "Python", "GitHub",
"Mandarin"). Values that are numeric ranges ("35-44") translate to Chinese style
("35-44岁" kept as-is where safe).

Usage:
  python translate_schema_labels.py --out ../../../schema/labels_zh.json \
      --chunk 120 --parallel 8
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_infer_engine import deepseek_config, _call_deepseek  # noqa: E402

SCHEMA = r"..\..\..\schema\dimensions.json"


def build_prompt(chunk: list[dict]) -> str:
    items = []
    for d in chunk:
        items.append({"id": d["id"], "label": d.get("label", d["id"]), "values": d.get("values") or []})
    lines = [
        "你是翻译专家。把 persona schema 的英文维度标签和取值翻译成简体中文。",
        "规则:",
        "- 只返回 JSON,格式:{\"<id>\": {\"label\": \"中文标签\", \"values\": {\"<英文值>\": \"<中文值>\"}}}",
        "- 专有名词、品牌、语言名、编程语言、公司名保持原文(Python、GitHub、Mandarin 等)。",
        "- 数值范围照常翻译(\"35-44\" → \"35-44岁\",\"8+ hrs\" → \"8小时以上\")。",
        "- values 里每个值都要翻译;含义相同的值用中文习惯表达。",
        "- 不确定的标签给出最常用译法,不要留空。",
        "",
        "待翻译:",
        json.dumps(items, ensure_ascii=False),
    ]
    return "\n".join(lines)


def _parse(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        obj = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--chunk", type=int, default=60)
    ap.add_argument("--parallel", type=int, default=8)
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    dims = json.load(open(os.path.normpath(os.path.join(base, SCHEMA)), encoding="utf-8"))["dimensions"]

    # resume: keep already-translated dims from an existing output file
    out = Path(args.out)
    result: dict[str, dict] = {}
    if out.is_file():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
            result = {k: v for k, v in existing.items() if isinstance(v, dict) and v.get("label")}
        except (OSError, ValueError):
            result = {}
    todo_dims = [d for d in dims if d["id"] not in result]
    print(f"existing {len(result)} dims; todo {len(todo_dims)}", flush=True)
    if todo_dims:
        chunks = [todo_dims[i : i + args.chunk] for i in range(0, len(todo_dims), args.chunk)]
        print(f"{len(todo_dims)} dims in {len(chunks)} chunks", flush=True)

    key, base_url = deepseek_config()
    lock = __import__("threading").Lock()

    def work(chunk: list[dict]) -> dict:
        text = _call_deepseek(key, base_url, "deepseek-chat", build_prompt(chunk), max_tokens=8192)
        return _parse(text)

    if todo_dims:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futs = [ex.submit(work, c) for c in chunks]
            done = 0
            for f in as_completed(futs):
                got = f.result()
                with lock:
                    for did, entry in got.items():
                        if isinstance(entry, dict) and isinstance(entry.get("label"), str):
                            result[did] = entry
                    done += 1
                    print(f"[{done}/{len(chunks)}] accumulated {len(result)} dims", flush=True)

    missing = [d["id"] for d in dims if d["id"] not in result]
    if missing:
        print(f"WARNING missing {len(missing)} dims: {missing[:10]}", flush=True)

    # drop values entries not in schema (defensive), keep label
    by_id = {d["id"]: d for d in dims}
    clean: dict[str, dict] = {}
    for did, entry in result.items():
        d = by_id.get(did)
        if not d:
            continue
        vals = {}
        for v in d.get("values") or []:
            t = (entry.get("values") or {}).get(v)
            vals[v] = t if isinstance(t, str) and t else v
        clean[did] = {"label": entry["label"], "values": vals}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(clean, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ wrote {len(clean)} dims -> {out}")


if __name__ == "__main__":
    main()
