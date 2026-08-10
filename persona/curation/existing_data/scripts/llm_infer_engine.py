#!/usr/bin/env python3
"""Shared LLM inference layer (Layer-2) for survey datasets like CGSS.

Given a faithful Chinese `profile_text` rendered from a survey row, prompt a
DeepSeek model (credentials read from `application/playground/.env.local`) to fill
the schema dims the coded crosswalk cannot observe — each non-null value grounded
in a verbatim quote from `profile_text`, same contract as the human_extraction
pipeline (HOW_TO_ADD_A_DATASET.md §8: no invented facts, unsupported -> null).

Subset: only dims plausibly inferable from a household survey (Personality,
Values & Motivation, Behavior, Linguistic, Health, Life Events, topic_* interests)
— ~422 of 1290 dims, chunked per category (≤ 50/chunk).
"""
from __future__ import annotations

import json
import re
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import urllib.request

REPO = Path(__file__).resolve().parents[4]  # MatrAIx repo root
ENV_LOCAL = REPO / "application" / "playground" / ".env.local"
DIMS_JSON = REPO / "persona" / "schema" / "dimensions.json"
DEFAULT_MODEL = "deepseek-chat"


def deepseek_config() -> tuple[str, str]:
    """Return (api_key, base_url) from application/playground/.env.local."""
    key = base = None
    if ENV_LOCAL.is_file():
        for line in ENV_LOCAL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                key = line.split("=", 1)[1]
            elif line.startswith("DEEPSEEK_API_BASE="):
                base = line.split("=", 1)[1]
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not found in application/playground/.env.local")
    return key, (base or "https://api.deepseek.com")


def _call_deepseek(key: str, base: str, model: str, prompt: str, max_tokens: int = 4096) -> str:
    body = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": prompt}],
         "max_tokens": max_tokens, "temperature": 0}
    ).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]


def build_prompt(profile_text: str, chunk_dims: list[dict]) -> str:
    lines = [
        "你是从一份真实问卷调查记录中提取用户(persona)特征的助手。",
        "只返回 JSON,不要 markdown 或解释,格式:",
        '{"fields": [{"field_id": "<id>", "value": "<allowed value 或 null>",',
        '"confidence": 0.0, "evidence": "<从 PROFILE 逐字摘抄的引用>",',
        '"description": "<1-2 句中文,描述该受访者在此属性上的情况,不要解释选择理由>",',
        '"assignment_type": "direct|summary_inference|unsupported"}]}',
        "规则:",
        "- 下面列出的每个 field_id 恰好输出一个对象。",
        "- value 必须精确是 allowed values 之一,或 null(问卷不支持该推断时)。",
        "- 非 null 值必须带 evidence:从 PROFILE 原文逐字摘抄的短引用。",
        "- assignment_type:问卷直接问到=direct;由答项合理推断=summary_inference;无法推断=unsupported 且 value=null。",
        "- 绝不编造 PROFILE 中不存在的事实;不确定就 null。",
        "",
        "DIMENSIONS (field_id — label — allowed values):",
    ]
    for d in chunk_dims:
        allowed = " | ".join(d.get("values") or []) or "(free)"
        lines.append(f"- {d['id']} — {d.get('label', d['id'])} — [{allowed}]")
    lines += ["", "PROFILE:", profile_text]
    return "\n".join(lines)


def _inferable(d: dict) -> bool:
    cat = d.get("category", "")
    if cat.startswith("Personality"):
        return True
    if cat in ("Values & Motivation", "Behavior: Preferences", "Behavior: Habits"):
        return True
    if cat.startswith("Linguistic"):
        return True
    if cat.startswith("Health"):
        return True
    if cat == "Demographic: Life Events":
        return True
    if d.get("id", "").startswith("topic_"):
        return True
    return False


def _parse_fields(text: str) -> list[dict]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return []
    try:
        obj = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    return obj.get("fields") if isinstance(obj, dict) and isinstance(obj.get("fields"), list) else []


def infer(
    profile_text: str,
    order: list[str],
    dims_json: str | Path | None = None,
    model: str = DEFAULT_MODEL,
    per_chunk: int = 50,
    workers: int = 4,
) -> list[dict]:
    """Return raw_fields for the inferable subset of `order` (Layer-2)."""
    dims = json.load(open(dims_json or DIMS_JSON, encoding="utf-8"))["dimensions"]
    by_id = {d["id"]: d for d in dims}
    subset = [by_id[i] for i in order if i in by_id and _inferable(by_id[i])]

    by_cat: "OrderedDict[str, list[dict]]" = OrderedDict()
    for d in subset:
        by_cat.setdefault(d["category"], []).append(d)
    chunks = []
    for cat_dims in by_cat.values():
        for i in range(0, len(cat_dims), per_chunk):
            chunks.append(cat_dims[i : i + per_chunk])

    key, base = deepseek_config()
    fields: list[dict] = []
    lock = threading.Lock()

    def work(chunk: list[dict]) -> list[dict]:
        prompt = build_prompt(profile_text, chunk)
        text = _call_deepseek(key, base, model, prompt)
        parsed = _parse_fields(text)
        # keep only dims this chunk asked for (defensive)
        asked = {d["id"] for d in chunk}
        return [f for f in parsed if f.get("field_id") in asked]

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(work, c) for c in chunks]
        for f in as_completed(futures):
            try:
                got = f.result()
                with lock:
                    fields.extend(got)
            except Exception as exc:  # keep going; chunk-level failure
                print(f"chunk failed: {exc}")
    return fields
