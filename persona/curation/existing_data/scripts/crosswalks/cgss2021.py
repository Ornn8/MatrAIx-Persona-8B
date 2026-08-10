#!/usr/bin/env python3
"""Crosswalk: raw CGSS2021 (Chinese General Social Survey 2021, `CGSS2021.dta`) → the exact/"observed" layer of the 1290 schema.

CGSS2021: 8,148 respondents, 700 variables (CNSDA project 65635422, gated). Compared to
CGSS2017 the questionnaire was restructured: question numbers changed to title-case
(A2/A3_1/A4/…), religion is a single-select A5 (was a51-a521 multi-select), and the
D-module attitude batteries (LOT-R optimism, filial duty, govt responsibility, cooking,
parental death) were dropped — so fewer dims are mappable here.

Source & input convention: `pyreadstat.read_dta(path, apply_value_formats=False)` via
`dta_to_rows.py --variant 2021` (raw numeric codes). All names verified against the
actual CGSS2021.dta column labels.

Verified variable map (checked against CGSS2021 data)
-----------------------------------------------------
* A2 sex; A3_1 birth year; A4 ethnicity (1汉 …); A7a education (14); A69 marital (1-7)
* A5 religion single-select (1=不信仰 11佛教 12道教 13民间 14回教 15天主 16基督 17东正 18其他基督 19犹太 20印度 21其他)
* A6 religious attendance (1-9); A15 self-rated health; A43e subjective SES
* E34 (fallback P4c) generalised trust (1-2 trust, 3-4 distrust)
* A1 household size (excluding self); A011601-14 household roster (1=配偶 2=子女 3=父母 … 9=孙辈)
* A12_1 own dwelling; A12_8 rented dwelling
* A30_1 TV / A30_2 film / A30_4 reading / A30_8 music / A30_9 exercise / A30_12 internet (leisure freq 1-5)
* A28_3 radio / A28_5 internet (media freq 1-5); A29 main info source; A30b used internet in 6mo
* A53 work last week (1-4); A54 not-working reason (8=料理家务); A59a job type (8=自由职业者)
* A59c career years; A59e full/part-time; A59f management; A59j org type; A59L employees (99996+ missing)
* A42_1-5 gender-role attitudes (A42_5 reversed); A17 depressed mood; A16 health-limited energy
* D23_a alcohol frequency; D23_b exercise frequency

Faithfulness choices (same rules as CGSS2017):
* non-Han ethnicity → null; a7a=13 研究生及以上 → null; hukou/income/party → null
* Children: roster relation 2 (子女) counts as a child; 9 (孙辈) → Grandparent. No child
  ages are collected in 2021 -> demo_parental_status/lifex_parenting_journey are NOT mapped
  (cannot separate minors/adults faithfully).
* A5=1 不信仰宗教 → None affiliation + Secular; else attendance A6 → Devout/Observant/Spiritual.
* D23_a alcohol: 1=从不→Never, 2=每月1次或更少→Rarely, 3=每月几次→Socially,
  4=每星期几次→Regularly, 5=每天→Heavily.

Run ``python crosswalks/cgss2021.py --selftest``.
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
    return str(v).strip().lower()


def _num(row, key, reject8=True):
    v = row.get(key)
    if v is None:
        return None
    try:
        if v != v:
            return None
        f = float(str(v).strip())
    except (TypeError, ValueError):
        return None
    if f in (97, 98, 99):
        return None
    if reject8 and f == 8:
        return None
    return f


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _band5(score):
    if score is None:
        return None
    if score >= 4.2:
        return "Enthusiast"
    if score >= 3.4:
        return "Positive"
    if score >= 2.6:
        return "Neutral"
    if score >= 1.8:
        return "Skeptical"
    return "Opposed"


# ---------------------------------------------------------------- demographics

def _age_bracket(row):
    raw = row.get("A3_1")
    if raw is None:
        return None
    try:
        if raw != raw:
            return None
        year = int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return None
    if not (1900 <= year <= 2021):
        return None
    age = 2021 - year
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


def _ethnicity(row):
    v = _s(row, "A4")
    if v in ("1", "汉"):
        return "East Asian"
    return None


def _religion(row):
    # A5 single-select: 1=不信仰宗教, 11=佛教 … 21=其他
    return {
        "1": "None", "11": "Buddhist", "12": "Folk / traditional",
        "13": "Folk / traditional", "14": "Muslim", "15": "Christian",
        "16": "Christian", "17": "Christian", "18": "Christian",
        "19": "Jewish", "20": "Hindu", "21": None,
    }.get(_s(row, "A5"))


def _religiosity(row):
    if _s(row, "A5") in ("1",):
        return "Secular"
    freq = _num(row, "A6")
    if freq is None:
        return None
    if freq >= 7:
        return "Devout"
    if freq >= 5:
        return "Observant"
    if freq >= 1:
        return "Spiritual"
    return None


def _socioeconomic_band(row):
    return {1: "High income", 2: "Upper-middle", 3: "Middle", 4: "Lower-middle", 5: "Low income"}.get(
        _num(row, "A43e")
    )


def _household_size(row):
    n = _num(row, "A1")
    if n is None:
        return None
    n = int(n) + 1  # + self
    if n == 1:
        return "Lives alone"
    if n == 2:
        return "2 people"
    if n <= 4:
        return "3-4 people"
    return "5+ people"


def _children_count(row):
    kids = sum(
        1 for i in range(1, 15)
        if _num(row, f"A01160{i}", reject8=False) == 2  # 2=子女
    )
    if kids == 0:
        return None
    if kids == 1:
        return "1 child"
    if kids == 2:
        return "2 children"
    return "3+ children"


def _has_grandchild(row):
    return any(_num(row, f"A01160{i}", reject8=False) == 9 for i in range(1, 15))


def _parental_status(row):
    if _has_grandchild(row):
        return "Grandparent"
    kids = sum(1 for i in range(1, 15) if _num(row, f"A01160{i}", reject8=False) == 2)
    if kids == 0:
        return None  # no child ages in 2021 -> cannot distinguish minors/adults
    return "Parent of adults" if not _has_grandchild(row) else "Grandparent"


def _housing_status(row):
    if _num(row, "A12_8") == 1:  # rented dwelling
        return "Renting"
    if _num(row, "A12_1") == 1:  # self-owned dwelling
        return "Own outright"
    return None


# ---------------------------------------------------------------- employment

def _employment_status(row):
    a53 = _num(row, "A53")
    if a53 in (2, 4):
        a59a = _num(row, "A59a", reject8=False)
        if a59a in (1, 2, 6, 7):
            return "Self-employed"
        if a59a in (5, 8):
            return "Gig / freelance"
        if a59a in (3, 4):
            return "Part-time" if _num(row, "A59e") == 2 else "Full-time"
        return None
    if a53 == 3:
        return "Unemployed"
    if a53 == 1:
        a54 = _num(row, "A54", reject8=False)
        if a54 == 7:
            return "Retired"
        if a54 == 8:
            return "Homemaker"
        if a54 == 1:
            return "Student"
        if a54 is not None:
            return "Unemployed"
    return None


def _years_experience(row):
    y = _num(row, "A59c")
    if y is None or y <= 0:
        return None
    if y <= 2:
        return "0-2"
    if y <= 5:
        return "3-5"
    if y <= 10:
        return "6-10"
    if y <= 20:
        return "11-20"
    return "20+"


def _company_size(row):
    j = _num(row, "A59j")
    if j in (1, 3, 6):
        return "Public sector"
    if j == 4:
        return "NGO"
    if j == 5:
        return "Solo / freelance"
    if j == 2:
        l = _num(row, "A59L")
        if l is None or l >= 99990:  # 99996 超过五位数 / 99998/99999 缺失
            return None
        if l < 50:
            return "Startup (<50)"
        if l < 500:
            return "SMB (50-500)"
        if l < 5000:
            return "Mid (500-5k)"
        return "Enterprise (5k+)"
    return None


def _seniority(row):
    f = _num(row, "A59f")
    if f in (1, 2):
        return "Manager"
    if f == 3:
        return "Mid"
    if f == 4:
        return "Entry"
    return None


# ---------------------------------------------------------------- media / habits

def _tech_savviness(row):
    a30b = _num(row, "A30b")  # 1=上网过 2=没上过
    if a30b == 2:
        return "Avoidant"
    if a30b == 1:
        f = _num(row, "A30_12")
        if f == 1:
            return "Digital native"
        if f == 2:
            return "Comfortable"
        if f == 3:
            return "Cautious adopter"
        if f == 4:
            return "Reluctant"
        if f == 5:
            return "Avoidant"
        return "Comfortable"
    return None


_FREQ5 = {"1": "Daily", "2": "Weekly", "3": "Monthly", "4": "Rarely", "5": "Never"}


def _media_diet(row):
    v = _num(row, "A29")
    if v in (1, 2):
        return "Long-form"
    if v == 3:
        return "News"
    if v == 4:
        return "Video-first"
    if v in (5, 6):
        return "Social-media-heavy"
    return None


def _music_listening(row):
    v = _num(row, "A30_8")
    if v is None:
        return None
    if v == 1:
        return "All day"
    if v == 2:
        return "Daily"
    if v == 3:
        return "Sometimes"
    return "Rarely"


def _trust_level(row):
    v = _num(row, "E34", reject8=False)
    if v is None:
        v = _num(row, "P4c", reject8=False)  # fallback module
    if v in (1, 2):
        return "Trusting"
    if v in (3, 4):
        return "Skeptical"
    return None


def _alcohol_use(row):
    return {1: "Never", 2: "Rarely", 3: "Socially", 4: "Regularly", 5: "Heavily"}.get(
        _num(row, "D23_a")
    )


def _exercise_freq(row):
    return {1: "Never", 2: "Rarely", 3: "Monthly", 4: "Weekly", 5: "Daily"}.get(
        _num(row, "D23_b")
    )


# ---------------------------------------------------------------- attitudes

def _gender_roles(row):
    scores = []
    for i, rev in ((1, False), (2, False), (3, False), (4, False), (5, True)):
        v = _num(row, f"A42_{i}")
        if v is None:
            continue
        scores.append(6 - v if rev else v)
    return _band5(_mean(scores))


def _depression(row):
    v = _num(row, "A17")
    if v is None:
        return None
    return {1: "Very high", 2: "High", 3: "Average", 4: "Low", 5: "Very low"}.get(int(v))


def _energy_level(row):
    v = _num(row, "A16")
    if v is None:
        return None
    return {1: "None", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"}.get(int(v))


CROSSWALK = {
    "age_bracket": {"compute": _age_bracket, "prov": "observed"},
    "region": {"compute": _region, "prov": "observed"},
    "gender_identity": {"src": "A2", "map": {"1": "Man", "2": "Woman"}, "prov": "observed"},
    "demo_ethnicity_broad": {"compute": _ethnicity, "prov": "observed"},
    "highest_education": {
        "src": "A7a",
        "map": {
            "1": "No formal", "2": "No formal", "3": "Primary", "4": "Secondary",
            "5": "Vocational / cert", "6": "Secondary", "7": "Vocational / cert",
            "8": "Vocational / cert", "9": "Associate's", "10": "Associate's",
            "11": "Bachelor's", "12": "Bachelor's", "13": None, "14": None,
        },
        "prov": "observed",
    },
    "demo_marital_status": {
        "src": "A69",
        "map": {
            "1": "Single", "2": "Domestic partnership", "3": "Married", "4": "Married",
            "5": "Separated", "6": "Divorced", "7": "Widowed",
        },
        "prov": "observed",
    },
    "demo_religion_affiliation": {"compute": _religion, "prov": "observed"},
    "religiosity": {"compute": _religiosity, "prov": "observed"},
    "health_general_health": {
        "src": "A15",
        "map": {"1": "Poor", "2": "Poor", "3": "Fair", "4": "Good", "5": "Excellent"},
        "prov": "observed",
    },
    "trust_level": {"compute": _trust_level, "prov": "observed"},
    "socioeconomic_band": {"compute": _socioeconomic_band, "prov": "observed"},

    # ---- family ----
    "lstyle_household_size": {"compute": _household_size, "prov": "observed"},
    "demo_children_count": {"compute": _children_count, "prov": "observed"},
    "demo_parental_status": {"compute": _parental_status, "prov": "observed"},
    "demo_housing_status": {"compute": _housing_status, "prov": "observed"},

    # ---- employment ----
    "demo_employment_status": {"compute": _employment_status, "prov": "observed"},
    "years_experience": {"compute": _years_experience, "prov": "observed"},
    "company_size": {"compute": _company_size, "prov": "observed"},
    "seniority": {"compute": _seniority, "prov": "observed"},

    # ---- media / habits ----
    "tech_savviness": {"compute": _tech_savviness, "prov": "observed"},
    "lstyle_reading_freq": {"src": "A30_4", "map": _FREQ5, "prov": "observed"},
    "lstyle_music_listening": {"compute": _music_listening, "prov": "observed"},
    "lstyle_podcast_listening": {
        "src": "A28_3",
        "map": {"1": "Never", "2": "Rarely", "3": "Monthly", "4": "Weekly", "5": "Daily"},
        "prov": "observed",
    },
    "media_diet": {"compute": _media_diet, "prov": "observed"},
    "lstyle_exercise_freq": {"compute": _exercise_freq, "prov": "observed"},
    "lstyle_alcohol_use": {"compute": _alcohol_use, "prov": "observed"},

    # ---- attitudes ----
    "att_traditional_gender_roles": {"compute": _gender_roles, "prov": "observed"},
    "bfi2_facet_depression": {"compute": _depression, "prov": "observed"},
    "health_energy_level": {"compute": _energy_level, "prov": "observed"},
}


def render(row, labels_path=None):
    """Layer-2: faithful Chinese profile_text rendered from the coded 2021 row."""
    import json as _json
    import os as _os
    import re as _re

    path = labels_path or _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)), "labels2021.json"
    )
    labels = _json.load(open(path, encoding="utf-8"))
    parts = []
    for key, info in labels.items():
        v = row.get(key)
        if v is None:
            continue
        lab = _re.sub(r"^\[.*?\]\s*", "", info.get("label", key)).strip()
        zh = info.get("values", {}).get(str(v).strip())
        if zh is None:
            zh = str(v)
        parts.append(f"{lab}: {zh}")
    return "。".join(parts) + "。"


def llm_infer(profile_text, order):
    """Layer-2: fill schema dims the coded crosswalk cannot observe (DeepSeek)."""
    import os as _os
    import sys as _sys

    _d = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # scripts/
    if _d not in _sys.path:
        _sys.path.insert(0, _d)
    from llm_infer_engine import infer

    return infer(profile_text, order)


def _selftest():
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from crosswalk_engine import apply_crosswalk

    allowed = {
        "age_bracket": {"Under 5", "5-12", "13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-84", "85+"},
        "region": {"East Asia"},
        "gender_identity": {"Man", "Woman", "Non-binary", "Self-described", "Prefer not to say"},
        "demo_ethnicity_broad": {"East Asian", "South Asian", "Southeast Asian"},
        "highest_education": {"No formal", "Primary", "Secondary", "Vocational / cert", "Some college", "Associate's", "Bachelor's", "Master's", "Doctorate", "Postdoc"},
        "demo_marital_status": {"Single", "In a relationship", "Engaged", "Married", "Domestic partnership", "Separated", "Divorced", "Widowed"},
        "demo_religion_affiliation": {"Christian", "Muslim", "Hindu", "Buddhist", "Jewish", "Sikh", "Folk / traditional", "Spiritual but unaffiliated", "Atheist / agnostic", "None"},
        "religiosity": {"Secular", "Spiritual", "Observant", "Devout", "Prefer not to say"},
        "health_general_health": {"Excellent", "Good", "Fair", "Poor"},
        "trust_level": {"Trusting", "Verifying", "Skeptical", "Hostile"},
        "socioeconomic_band": {"Low income", "Lower-middle", "Middle", "Upper-middle", "High income"},
        "lstyle_household_size": {"Lives alone", "2 people", "3-4 people", "5+ people", "Communal"},
        "demo_children_count": {"None", "Expecting", "1 child", "2 children", "3+ children", "Adult children"},
        "demo_parental_status": {"Not a parent", "New parent", "Parent of minors", "Parent of adults", "Grandparent", "Step / foster parent"},
        "demo_housing_status": {"Own outright", "Mortgage", "Renting", "Living with family", "Shared housing", "Temporary / transitional"},
        "demo_employment_status": {"Full-time", "Part-time", "Self-employed", "Gig / freelance", "Student", "Unemployed", "Retired", "Homemaker"},
        "years_experience": {"0-2", "3-5", "6-10", "11-20", "20+"},
        "company_size": {"Solo / freelance", "Startup (<50)", "SMB (50-500)", "Mid (500-5k)", "Enterprise (5k+)", "Public sector", "Academia", "NGO"},
        "seniority": {"Student / intern", "Entry", "Mid", "Senior", "Lead / Principal", "Manager", "Director", "VP", "C-suite", "Founder", "Retired"},
        "tech_savviness": {"Digital native", "Comfortable", "Cautious adopter", "Reluctant", "Avoidant"},
        "lstyle_reading_freq": {"Daily", "Weekly", "Monthly", "Rarely", "Never"},
        "lstyle_music_listening": {"All day", "Daily", "Sometimes", "Rarely"},
        "lstyle_podcast_listening": {"Daily", "Weekly", "Monthly", "Rarely", "Never"},
        "media_diet": {"Academic journals", "News", "Social-media-heavy", "Long-form", "Video-first", "Minimal"},
        "lstyle_exercise_freq": {"Daily", "Weekly", "Monthly", "Rarely", "Never"},
        "lstyle_alcohol_use": {"Never", "Rarely", "Socially", "Regularly", "Heavily"},
        "att_traditional_gender_roles": {"Enthusiast", "Positive", "Neutral", "Skeptical", "Opposed"},
        "bfi2_facet_depression": {"Very high", "High", "Average", "Low", "Very low"},
        "health_energy_level": {"Very high", "High", "Moderate", "Low", "None"},
    }

    row = {
        "user_id": "u1",
        "A2": 2, "A3_1": 1980, "A4": 1, "A7a": 12, "A69": 3,
        "A5": 11, "A6": 6, "A15": 4, "A43e": 3, "E34": 1,
        "A1": 3, "A011601": 1, "A011602": 2, "A011603": 2, "A011604": 9,
        "A12_1": 1, "A12_8": 0,
        "A53": 4, "A59a": 3, "A59c": 15, "A59e": 1, "A59f": 3, "A59j": 2, "A59L": 120,
        "A30_4": 1, "A30_8": 2, "A28_3": 2, "A29": 5, "A30b": 1, "A30_12": 1,
        "D23_b": 4, "D23_a": 4, "A42_1": 4, "A42_2": 3, "A42_3": 4, "A42_4": 2, "A42_5": 2,
        "A17": 4, "A16": 4,
    }
    obs, prov, unmapped = apply_crosswalk(row, CROSSWALK, allowed)
    assert obs["age_bracket"] == "35-44", obs  # 2021-1980=41
    assert obs["gender_identity"] == "Woman"
    assert obs["demo_religion_affiliation"] == "Buddhist"
    assert obs["religiosity"] == "Observant"
    assert obs["trust_level"] == "Trusting"
    assert obs["lstyle_household_size"] == "3-4 people", obs  # A1=3 -> 4 people
    assert obs["demo_children_count"] == "2 children", obs  # two 子女
    assert obs["demo_parental_status"] == "Grandparent", obs  # 孙辈 present
    assert obs["demo_housing_status"] == "Own outright"
    assert obs["demo_employment_status"] == "Full-time", obs
    assert obs["years_experience"] == "11-20", obs
    assert obs["company_size"] == "SMB (50-500)", obs  # 120
    assert obs["tech_savviness"] == "Digital native", obs
    assert obs["lstyle_exercise_freq"] == "Weekly", obs  # D23_b=4
    assert obs["lstyle_alcohol_use"] == "Regularly", obs  # D23_a=4
    assert obs["bfi2_facet_depression"] == "Low", obs  # A17=4
    assert obs["health_energy_level"] == "High", obs  # A16=4
    assert all(p == "observed" for p in prov.values())

    # faithfulness edges
    coarse = {"A2": 1, "A3_1": 1990, "A4": 4, "A7a": 13, "A69": 6, "A5": 21, "A15": 98,
              "E34": 3, "A43e": 98, "A59j": 7, "A30b": 2, "A011601": 3}
    obs2, _, _ = apply_crosswalk(coarse, CROSSWALK, allowed)
    assert "demo_ethnicity_broad" not in obs2
    assert "highest_education" not in obs2
    assert "demo_religion_affiliation" not in obs2  # 21=其他 -> null
    assert "health_general_health" not in obs2
    assert obs2["trust_level"] == "Skeptical", obs2  # E34=3
    assert "demo_children_count" not in obs2  # no 子女, no 孙辈
    assert obs2["tech_savviness"] == "Avoidant", obs2

    # 8-as-business-value paths
    obs3, _, _ = apply_crosswalk({"A2": 1, "A3_1": 1970, "A53": 1, "A54": 8}, CROSSWALK, allowed)
    assert obs3["demo_employment_status"] == "Homemaker", obs3
    obs4, _, _ = apply_crosswalk({"A2": 1, "A3_1": 1985, "A53": 4, "A59a": 8}, CROSSWALK, allowed)
    assert obs4["demo_employment_status"] == "Gig / freelance", obs4

    print(f"cgss2021 crosswalk self-test: {len(CROSSWALK)} dims, mapping + faithfulness verified ✅")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Raw CGSS2021 crosswalk for crosswalk_engine.")
    ap.add_argument("--selftest", action="store_true", help="verify the crosswalk against the engine")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        ap.print_help()
