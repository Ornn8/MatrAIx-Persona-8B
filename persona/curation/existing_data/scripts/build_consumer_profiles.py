#!/usr/bin/env python3
"""Build a lightweight consumer-profile block for China persona pools.

For each persona YAML under a pool dir (e.g. persona/datasets/cgss2017-llm),
prompt DeepSeek to infer ~10 consumer-behavior fields (willingness to pay,
price sensitivity, payment-model preference, promotion receptivity, ...) from
the persona's existing dimensions. Every value carries an `evidence` pointer to
the source dimension/value it is grounded in (faithfulness contract, same as
llm_infer_engine). Output is written back to the persona YAML as a
`consumer_profile:` block (idempotent: skips personas that already have one).

Usage:
    python build_consumer_profiles.py [--pool persona/datasets/cgss2017-llm]
        [--limit N] [--parallel 8] [--force]
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm_infer_engine import _call_deepseek, deepseek_config  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
DEFAULT_POOL = REPO / "persona" / "datasets" / "cgss2017-llm"

# --- field definition -------------------------------------------------------
# id -> (en_label, zh_label, allowed values)
CONSUMER_FIELDS: dict[str, tuple[str, str, list[str]]] = {
    "willingness_to_pay": ("Willingness to pay", "付费意愿", ["low", "moderate", "high"]),
    "price_anchor": ("Price anchor (RMB)", "价格锚点（人民币）", ["under_50", "50-200", "200-500", "500-2000", "2000+"]),
    "price_sensitivity": ("Price sensitivity", "价格敏感度", ["low", "moderate", "high"]),
    "payment_model_pref": ("Payment model preference", "付费模式偏好", ["one_time", "subscription", "freemium", "ad_supported"]),
    "promo_receptivity": ("Promotion receptivity", "推广接受度", ["open", "selective", "resistant"]),
    "trusted_channels": ("Trusted channels (multi)", "信任的渠道（多选）", ["word_of_mouth", "platform_reviews", "official_channels", "influencer", "offline"]),
    "spending_style": ("Spending style", "消费风格", ["frugal", "balanced", "generous"]),
    "decision_factors": ("Decision factors (ranked 3-5)", "决策因素（按权重排序 3-5 项）", ["price", "quality", "brand", "word_of_mouth", "convenience"]),
    "brand_loyalty": ("Brand loyalty", "品牌忠诚度", ["low", "moderate", "high"]),
    "payment_motivations": ("Payment motivations (multi)", "付费理由（多选）", ["core_need", "time_saving", "membership_perks", "creator_support", "none"]),
}

# Dimensions from the persona that plausibly inform consumer behavior.
CONSUMER_SIGNAL_DIMS = [
    "socioeconomic_band", "age_bracket", "gender_identity", "highest_education",
    "demo_employment_status", "region", "life_stage", "demo_marital_status",
    "demo_children_count", "lstyle_household_size", "urbanicity",
    "health_general_health", "trust_level",
    "att_brand_loyalty", "att_advertising", "att_subscription_services",
    "lstyle_payment_pref", "lstyle_subscription_count", "peeve_paywalls",
    "trait_loyalty", "val_loyalty", "pref_save_vs_spend", "mft_loyalty_betrayal",
    "economic_motivation", "cog_curiosity", "big5_self_efficacy",
]

SCHEMA = "（字段_值均为英文枚举，与 schema 惯例一致）"


def build_prompt(display_name: str, dims: dict[str, str]) -> str:
    signal = "\n".join(f"- {k}: {v}" for k, v in sorted(dims.items()))
    fields = "\n".join(
        f"- {fid}（{zh}）: [{', '.join(vals)}]"
        for fid, (_en, zh, vals) in CONSUMER_FIELDS.items()
    )
    return (
        "你是消费行为研究助手。基于一份中国用户(persona)的画像维度,推断其消费行为画像。\n"
        "只返回 JSON,不要 markdown,格式:\n"
        '{"fields": [{"field_id": "<id>", "value": "<allowed value 或 null>",\n'
        '"evidence": "<支撑该值的画像维度,格式 维度名: 值>",\n'
        '"assignment_type": "direct|summary_inference|unsupported"}]}\n'
        "规则:\n"
        "- 每个 field_id 恰好一个对象;value 必须精确是 allowed values 之一(多选字段为数组),无法支撑则 null。\n"
        "- 非 null 值必须带 evidence:引用下方 PERSONA DIMENSIONS 中的维度(格式:维度名: 值);\n"
        "  多选字段的 evidence 可引用多个维度。\n"
        "- 绝不编造画像中不存在的事实;价格锚点只选区间,不编精确数字。\n"
        "- assignment_type:有直接维度支撑=direct;由相关维度合理推断=summary_inference;无法推断=unsupported 且 value=null。\n"
        f"\n{SCHEMA}\n"
        "\nFIELDS:\n" + fields + "\n\nPERSONA DIMENSIONS:\n" + signal
    )


def parse_response(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    data = json.loads(text)
    return data.get("fields", data if isinstance(data, list) else [])


def heuristic_fallback(signals: dict[str, str]) -> dict:
    """Deterministic zero-cost fallback for personas whose LLM output failed to
    parse. Values come only from the persona's own signal dims (never invented).
    """
    ses = signals.get("socioeconomic_band")
    save = signals.get("pref_save_vs_spend")
    sub = signals.get("att_subscription_services")
    adv = signals.get("att_advertising")
    brand = signals.get("att_brand_loyalty")
    age = signals.get("age_bracket")
    urban = signals.get("urbanicity")

    ses_to_wtp = {"High income": "high", "Upper-middle": "high", "Middle": "moderate",
                  "Lower-middle": "low", "Low income": "low"}
    ses_to_anchor = {"High income": "200-500", "Upper-middle": "200-500", "Middle": "50-200",
                     "Lower-middle": "under_50", "Low income": "under_50"}
    ses_to_sens = {"High income": "low", "Upper-middle": "moderate", "Middle": "moderate",
                   "Lower-middle": "high", "Low income": "high"}
    save_to_style = {"Hard saver": "frugal", "Saver-leaning": "frugal", "Balanced": "balanced",
                     "Spender-leaning": "generous", "Free spender": "generous"}

    def ev(*parts: str) -> str:
        return "; ".join(p for p in parts if p)

    def three(att: str | None, pos: str, neg: str) -> str | None:
        if att in ("Enthusiast", "Positive"):
            return pos
        if att in ("Skeptical", "Opposed"):
            return neg
        if att == "Neutral":
            return "moderate"
        return None

    age_num = None
    if age and age.rstrip("+").isdigit():
        age_num = int(age.rstrip("+"))

    block = {
        "willingness_to_pay": {
            "value": ses_to_wtp.get(ses) if ses else None,
            "evidence": ev(f"socioeconomic_band: {ses}") if ses else None,
            "assignment_type": "heuristic_fallback",
        },
        "price_anchor": {
            "value": ses_to_anchor.get(ses) if ses else None,
            "evidence": ev(f"socioeconomic_band: {ses}") if ses else None,
            "assignment_type": "heuristic_fallback",
        },
        "price_sensitivity": {
            "value": ses_to_sens.get(ses) if ses else None,
            "evidence": ev(f"socioeconomic_band: {ses}", f"pref_save_vs_spend: {save}") if (ses or save) else None,
            "assignment_type": "heuristic_fallback",
        },
        "payment_model_pref": {
            "value": (three(sub, "subscription", "one_time") if sub else None),
            "evidence": ev(f"att_subscription_services: {sub}") if sub else None,
            "assignment_type": "heuristic_fallback",
        },
        "promo_receptivity": {
            "value": three(adv, "open", "resistant"),
            "evidence": ev(f"att_advertising: {adv}") if adv else None,
            "assignment_type": "heuristic_fallback",
        },
        "trusted_channels": {
            "value": ["word_of_mouth", "platform_reviews"],
            "evidence": "heuristic default",
            "assignment_type": "heuristic_fallback",
        },
        "spending_style": {
            "value": save_to_style.get(save) if save else None,
            "evidence": ev(f"pref_save_vs_spend: {save}") if save else None,
            "assignment_type": "heuristic_fallback",
        },
        "decision_factors": {
            "value": ["price", "quality", "convenience"],
            "evidence": "heuristic default",
            "assignment_type": "heuristic_fallback",
        },
        "brand_loyalty": {
            "value": three(brand, "high", "low"),
            "evidence": ev(f"att_brand_loyalty: {brand}") if brand else None,
            "assignment_type": "heuristic_fallback",
        },
        "payment_motivations": {
            "value": ["core_need"],
            "evidence": "heuristic default",
            "assignment_type": "heuristic_fallback",
        },
    }
    # Add influencer channel only for younger dense-urban personas.
    if urban in ("Dense urban", "Suburban") and age_num is not None and 18 <= age_num <= 44:
        block["trusted_channels"]["value"].append("influencer")
    if age_num is not None and 45 <= age_num:
        block["trusted_channels"]["value"].append("offline")
    return block


def infer_consumer_profile(display_name: str, dims: dict[str, str], retries: int = 1) -> list[dict]:
    key, base = deepseek_config()
    prompt = build_prompt(display_name, dims)
    last: Exception | None = None
    for attempt in range(retries + 1):
        raw = _call_deepseek(key, base, "deepseek-chat", prompt, max_tokens=4096)
        try:
            return parse_response(raw)
        except Exception as exc:  # LLM occasionally emits truncated/malformed JSON
            last = exc
    assert last is not None
    raise last


def persona_signals(persona: dict[str, Any]) -> dict[str, str]:
    dims = persona.get("dimensions", {}) or {}
    out: dict[str, str] = {}
    for k in CONSUMER_SIGNAL_DIMS:
        if k in dims and dims[k] not in (None, ""):
            out[k] = str(dims[k])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default=str(DEFAULT_POOL))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--parallel", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--heuristic-only", action="store_true", help="skip LLM; fill consumer_profile with deterministic fallback only")
    args = ap.parse_args()

    pool = Path(args.pool)
    yamls = sorted(pool.glob("persona_*.yaml"))
    if args.limit:
        yamls = yamls[: args.limit]

    lock = threading.Lock()
    done = 0
    errors: list[str] = []

    def process(path: Path) -> tuple[str, str]:
        persona = yaml.safe_load(path.read_text(encoding="utf-8"))
        if "consumer_profile" in persona and not args.force:
            return path.name, "skip(has consumer_profile)"
        name = persona.get("display_name") or persona.get("persona_id") or path.stem
        signals = persona_signals(persona)
        if not signals:
            return path.name, "skip(no signal dims)"
        fields = None
        if not args.heuristic_only:
            try:
                fields = infer_consumer_profile(name, signals)
            except Exception:
                fields = None
        if fields:
            by_id = {f.get("field_id"): f for f in fields if f.get("field_id") in CONSUMER_FIELDS}
            block = {}
            for fid in CONSUMER_FIELDS:
                f = by_id.get(fid)
                if not f:
                    continue
                block[fid] = {
                    "value": f.get("value"),
                    "evidence": f.get("evidence"),
                    "assignment_type": f.get("assignment_type", "summary_inference"),
                }
            filled = sum(1 for v in block.values() if v.get("value") not in (None, "", []))
            if filled == 0:
                fields = None
        if not fields:
            # Zero-cost deterministic fallback (no extra LLM spend).
            block = heuristic_fallback(signals)
        persona["consumer_profile"] = block
        with lock:
            path.write_text(
                yaml.safe_dump(persona, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        n = sum(1 for v in block.values() if v.get("value") not in (None, "", []))
        return path.name, f"ok({n}/{len(CONSUMER_FIELDS)} fields)"

    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(process, p): p for p in yamls}
        for fut in as_completed(futs):
            try:
                name, msg = fut.result()
                with lock:
                    done += 1
                    print(f"[{done}/{len(yamls)}] {name}: {msg}", flush=True)
            except Exception as exc:  # noqa: BLE001
                with lock:
                    errors.append(f"{futs[fut].name}: {exc}")
                    print(f"[ERR] {futs[fut].name}: {exc}", flush=True)

    print(f"\ndone {done}/{len(yamls)}, errors {len(errors)}")
    for e in errors[:10]:
        print("  ", e)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
