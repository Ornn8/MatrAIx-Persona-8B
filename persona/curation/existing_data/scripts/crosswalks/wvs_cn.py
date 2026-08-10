#!/usr/bin/env python3
"""Crosswalk: WVS wave-7 China sample (2018, n=3,036) → the exact/"observed" layer of the 1290 schema.

World Values Survey wave 7 China (2018, ~3,036 respondents) is a public cross-national
dataset (downloaded from the WVS7 v6.0 CSV export; see `wvs7_to_rows.py`). It provides
attitudes/values CGSS lacks (generalised trust, religious denomination, gender-equality
indexes) — used here as a second, independent Chinese real-data source.

Source & input convention: numeric codes from `wvs7_to_rows.py` (WVS missing codes
-1..-5 -> null).

Verified variable map (against WVS7 codebook + China-sample value distributions):
* Q260 sex (1=Male 2=Female) — codebook-verified, high confidence
* Q261 year of birth / Q262 age — codebook-verified, high confidence
* Q57P most-people-can-be-trusted (1=Most people can be trusted 2=Need to be very careful)
  — codebook-verified; China sample 34% trust, consistent with WVS China findings
* H_URBRURAL (1=urban 2=rural) — high confidence
* Q97 religious denomination (0=none; 1/2 = specific denominations whose China-specific
  labels need the China questionnaire — only 0→None mapped, rest left null)
* Q47P subjective health (1=Very good … 5=Very poor, international codebook) — MEDIUM
  confidence: the China-sample direction is flagged (distribution skews 3-4, unusual)
* I_WOMJOB / I_WOMPOL / I_WOMEDU (Inglehart-Welzel gender-equality indexes, 0..1;
  high = egalitarian) → att_traditional_gender_roles (reversed), medium-high
* I_RELIGPRAC (religiosity index 0..1, high = more religious) → religiosity, medium

Deliberately NOT mapped (no faithful schema home / direction unverified):
* Q46P happiness — direction vs codebook contradicted by sample distribution and schema
  has no happiness dim (recorded as schema-extension proposal)
* Q49 life satisfaction, I_TRUSTPOLICE/COURTS/ARMY (institutional trust), SACSECVAL,
  I_AUTHORITY / I_NATIONALISM / I_HOMOLIB / I_ABORTLIB / I_DIVORLIB — no schema dim

Run ``python crosswalks/wvs_cn.py --selftest``.
"""


def _s(row, key):
    v = row.get(key)
    if v is None:
        return None
    try:
        if v != v:
            return None
    except (TypeError, ValueError):
        pass
    return str(v).strip()


def _gender(row):
    return {"1": "Man", "2": "Woman"}.get(_s(row, "Q260"))


def _age_bracket(row):
    v = row.get("Q262")
    if v is None:
        return None
    try:
        age = int(float(v))
    except (TypeError, ValueError):
        return None
    for lo, hi, lab in (
        (0, 4, "Under 5"), (5, 12, "5-12"), (13, 17, "13-17"), (18, 24, "18-24"),
        (25, 34, "25-34"), (35, 44, "35-44"), (45, 54, "45-54"), (55, 64, "55-64"),
        (65, 74, "65-74"), (75, 84, "75-84"),
    ):
        if lo <= age <= hi:
            return lab
    return "85+" if age >= 85 else None


def _region(row):
    return "East Asia"


def _trust_level(row):
    return {"1": "Trusting", "2": "Skeptical"}.get(_s(row, "Q57P"))


def _urbanicity(row):
    return {"1": "Dense urban", "2": "Rural"}.get(_s(row, "H_URBRURAL"))


def _religion(row):
    # 0 = no religious denomination; specific denominations need China questionnaire
    if _s(row, "Q97") == "0":
        return "None"
    return None


def _religiosity(row):
    # Q97=0 (no denomination) -> Secular; else use religiosity index when present
    if _s(row, "Q97") == "0":
        return "Secular"
    v = row.get("I_RELIGPRAC")
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x >= 0.66:
        return "Observant"
    if x >= 0.34:
        return "Spiritual"
    return "Secular"


def _health(row):
    """Q47 subjective health. The China-sample direction is reversed vs the
    international codebook (1=Very good … 5=Very poor): 61% pick 4, which only
    makes sense as 'good' — so we reverse (6-v). FLAGGED: confirm with the
    China questionnaire before production."""
    v = _s(row, "Q47P")
    if v not in {"1", "2", "3", "4", "5"}:
        return None
    return {"5": "Excellent", "4": "Good", "3": "Fair", "2": "Poor", "1": "Poor"}[v]


def _gender_roles(row):
    """Inglehart-Welzel gender-equality indexes (0..1, high = egalitarian) →
    att_traditional_gender_roles (reversed)."""
    vals = []
    for k in ("I_WOMJOB", "I_WOMPOL", "I_WOMEDU"):
        v = row.get(k)
        if v is not None:
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                pass
    if not vals:
        return None
    egal = sum(vals) / len(vals)
    if egal >= 0.8:
        return "Opposed"
    if egal >= 0.6:
        return "Skeptical"
    if egal >= 0.4:
        return "Neutral"
    if egal >= 0.2:
        return "Positive"
    return "Enthusiast"


CROSSWALK = {
    "gender_identity": {"compute": _gender, "prov": "observed"},
    "age_bracket": {"compute": _age_bracket, "prov": "observed"},
    "region": {"compute": _region, "prov": "observed"},
    "trust_level": {"compute": _trust_level, "prov": "observed"},
    "urbanicity": {"compute": _urbanicity, "prov": "observed"},
    "demo_religion_affiliation": {"compute": _religion, "prov": "observed"},
    "religiosity": {"compute": _religiosity, "prov": "observed"},
    "health_general_health": {"compute": _health, "prov": "observed"},
    "att_traditional_gender_roles": {"compute": _gender_roles, "prov": "observed"},
}


def _selftest():
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from crosswalk_engine import apply_crosswalk

    allowed = {
        "gender_identity": {"Man", "Woman", "Non-binary", "Self-described", "Prefer not to say"},
        "age_bracket": {"18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-84", "85+"},
        "region": {"East Asia"},
        "trust_level": {"Trusting", "Verifying", "Skeptical", "Hostile"},
        "urbanicity": {"Dense urban", "Suburban", "Small town", "Rural", "Nomadic / remote"},
        "demo_religion_affiliation": {
            "Christian", "Muslim", "Hindu", "Buddhist", "Jewish", "Sikh",
            "Folk / traditional", "Spiritual but unaffiliated", "Atheist / agnostic", "None",
        },
        "religiosity": {"Secular", "Spiritual", "Observant", "Devout", "Prefer not to say"},
        "health_general_health": {"Excellent", "Good", "Fair", "Poor"},
        "att_traditional_gender_roles": {"Enthusiast", "Positive", "Neutral", "Skeptical", "Opposed"},
    }

    row = {
        "user_id": "wvs-cn-00000",
        "Q260": 1, "Q261": 1980, "Q262": 38, "Q57P": 1, "Q97": 0,
        "Q47P": 2, "H_URBRURAL": 1,
        "I_WOMJOB": 0.75, "I_WOMPOL": 0.66, "I_WOMEDU": 0.8,
    }
    obs, prov, unmapped = apply_crosswalk(row, CROSSWALK, allowed)
    assert obs["gender_identity"] == "Man"
    assert obs["age_bracket"] == "35-44", obs  # 38
    assert obs["region"] == "East Asia"
    assert obs["trust_level"] == "Trusting"
    assert obs["urbanicity"] == "Dense urban"
    assert obs["demo_religion_affiliation"] == "None"
    assert obs["religiosity"] == "Secular"
    assert obs["health_general_health"] == "Poor", obs  # reversed: China 2-> international 4 = Poor
    assert obs["att_traditional_gender_roles"] == "Skeptical", obs  # egal ~0.74
    assert all(p == "observed" for p in prov.values())

    # faithful: no-denomination-but-index -> not secular-guessed; missing -> unobserved
    row2 = {"Q260": 2, "Q262": 50, "Q57P": 2, "Q97": 1, "I_RELIGPRAC": 0.8}
    obs2, _, _ = apply_crosswalk(row2, CROSSWALK, allowed)
    assert obs2["trust_level"] == "Skeptical"
    assert "demo_religion_affiliation" not in obs2  # Q97=1 needs China labels
    assert obs2["religiosity"] == "Observant", obs2

    print(f"wvs_cn crosswalk self-test: {len(CROSSWALK)} dims, mapping + faithfulness verified ✅")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="WVS wave-7 China crosswalk for crosswalk_engine.")
    ap.add_argument("--selftest", action="store_true", help="verify the crosswalk against the engine")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        ap.print_help()
