#!/usr/bin/env python3
"""Crosswalk: raw CGSS2017 (Chinese General Social Survey 2017, `CGSS2017.dta`) → the exact/"observed" layer of the 1290 schema.

CGSS is a nationally representative mainland-China household survey (CGSS2017: 12,582
respondents, 786 variables; data & official codebook via CNSDA, https://www.cnsda.org/).
Like GSS, it is fully coded, so this observed layer alone is the rule-based extraction —
feed it to `run_pipeline.py --observed-only` (no LLM).

Source & input convention
-------------------------
Read the official `.dta` with `pyreadstat.read_dta(path, apply_value_formats=False)` (see
`dta_to_rows.py`) so coded fields come out as **raw numeric codes** (e.g. a2 -> 1/2).
This crosswalk matches those numeric codes; decoded Chinese labels ("男"/"女") are also
accepted for backwards compatibility. All question numbers below were verified against
the actual CGSS2017 `.dta` column labels and value labels.

Verified variable map (checked against CGSS2017 data)
-----------------------------------------------------
* a2 sex (1男 2女); a31 birth year (numeric, NOT a3a); a4 ethnicity (1汉…); a7a education (14)
* a69 marital (1未婚 2同居 3初婚 4再婚 5分居 6离婚 7丧偶)
* a51-a521 religion multi-select (0/1; a51=no religion, a511=佛教 … a521=其他)
* a6 religious attendance (1从来没有 … 9一周几次); a15 self-rated health (1很不健康…5很健康)
* v458 social trust (1非常不同意…5非常同意); a43e subjective SES (1上层…5下层)
* a301/a302/a304/a308/a309/a3012 leisure frequency (1每天…5从不); a29 main info source
* a30c daily news-reading minutes (missing codes 998/999 range-checked); a30g/a30h WeChat/Alipay mobile payment; a283 radio media freq
* a17 depressed mood freq (1总是…5从不); a421-a425 gender-role attitudes (a425 reversed)
* a53 work last week (1未工作 2带薪休 3停薪休 4工作); a54 not-working reason (8=料理家务); a59a job type (8=自由职业者)
* a59c career years (0 = no non-farm work history -> null); a59e full/part-time; a59f management; a59j org type; a59l employees (99998/99999 missing)
* c32 self-efficacy (7pt); c34 household balance; c491-c4911 internet-dependence (11 items)
* c58 remote-work attitude; c621-c625 online privacy (5 items)
* d24 first marriage; d131 cooking freq; d161-d164 govt-responsibility; d202 family-first
* d381-d386 LOT-R optimism (d382/d384/d385 reversed); d61a/d62a parents alive
* d3a1-10 household roster (relation codes 1=配偶 2-6=子女 7=女婿/儿媳 8=孙辈 9=孙辈配偶 10=父母…); d3c1-10 ages (missing 0/999); d3e1-10 co-residence; d4 kids co-reside; d5a1-5/d5b1-5 non-resident children

Faithfulness choices (map value ``None`` = present-but-deliberately-unmapped → null):
* non-Han ethnicity → null (no faithful schema bucket); a7a=13 研究生及以上 → null (too coarse)
* a18 hukou → null (≠ urbanicity); a8a income → not used (a43e self-rated SES is the faithful source)
* a10 party membership → null (not political_lean); schema-only additions stay out (see NOTES)
* Deliberately NOT mapped (semantics would be fabricated): a284 TV frequency → lstyle_streaming_hours
  (frequency ≠ hours/week); a30c news minutes → lstyle_screen_time (news ≠ total screen time);
  a301/a302 leisure frequency → topic_tv_series/topic_film (frequency ≠ interest).
* Multi-item scales are aggregated only over answered items; 97/98/99/8 (不知道/拒绝/无法选择) are
  treated as missing and skipped — never imputed.

NOTES on scope: this crosswalk maps ONLY dimensions that already exist in the 1290-dim schema.
CGSS2017 carries strong signal with no schema home (happiness, life satisfaction, generalized
social trust, institutional trust, perceived fairness, hukou status, living arrangement,
occupation class, personal income band, internet dependence, online-shopping attitude, …) —
those are recorded as a schema-extension proposal, not added here.

Run ``python crosswalks/cgss.py --selftest``.
"""


def _s(row, key):
    """Lowercased source string, or None for missing/NaN — no pandas dependency."""
    v = row.get(key)
    if v is None:
        return None
    try:
        if v != v:  # NaN
            return None
    except (TypeError, ValueError):
        pass
    return str(v).strip().lower()


def _num(row, key, reject8=True):
    """Numeric value, or None. Rejects missing codes 97/98/99 and (by default) 8.

    ``reject8=False`` for variables where 8 is a real business value
    (a54=8 料理家务, a59a=8 自由职业者, d3a=8 孙子/外孙子) instead of
    "无法选择". Note CGSS also uses 998/999/9998/9999-style missing codes on
    continuous fields (a30c, a59l, d3c) — callers must range-check those.
    """
    v = row.get(key)
    if v is None:
        return None
    try:
        if v != v:  # NaN
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
    """1-5 score -> Enthusiast/Positive/Neutral/Skeptical/Opposed (attitude dims)."""
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
    """a31 = 4-digit birth year (CGSS2017 field year = 2017); age = 2017 - a31."""
    raw = row.get("a31")
    if raw is None:
        return None
    try:
        if raw != raw:
            return None
        year = int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return None
    if not (1900 <= year <= 2017):
        return None
    age = 2017 - year
    for lo, hi, lab in (
        (0, 4, "Under 5"), (5, 12, "5-12"), (13, 17, "13-17"), (18, 24, "18-24"),
        (25, 34, "25-34"), (35, 44, "35-44"), (45, 54, "45-54"), (55, 64, "55-64"),
        (65, 74, "65-74"), (75, 84, "75-84"),
    ):
        if lo <= age <= hi:
            return lab
    return "85+" if age >= 85 else None


def _region(row):
    return "East Asia"  # CGSS sampling frame = mainland China


def _ethnicity(row):
    """a4: only Han (1/汉) maps faithfully to East Asian."""
    v = _s(row, "a4")
    if v in ("1", "汉"):
        return "East Asian"
    return None


def _religion(row):
    if _s(row, "a51") in ("是", "1"):
        return "None"
    mapping = {
        "a511": "Buddhist", "a512": "Folk / traditional", "a513": "Folk / traditional",
        "a514": "Muslim", "a515": "Christian", "a516": "Christian", "a517": "Christian",
        "a518": "Christian", "a519": "Jewish", "a520": "Hindu", "a521": None,
    }
    for col, target in mapping.items():
        if _s(row, col) in ("是", "1"):
            return target
    return None


def _religiosity(row):
    if _s(row, "a51") in ("是", "1"):
        return "Secular"
    freq = _num(row, "a6")
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
    return {
        1: "High income", 2: "Upper-middle", 3: "Middle", 4: "Lower-middle", 5: "Low income",
    }.get(_num(row, "a43e"))


def _household_size(row):
    n = sum(1 for i in range(1, 11) if _num(row, f"d3a{i}") is not None)
    if n == 0:
        return None
    if n == 1:
        return "Lives alone"
    if n == 2:
        return "2 people"
    if n <= 4:
        return "3-4 people"
    return "5+ people"


def _child_ages(row):
    """Ages of all children (resident roster + non-resident roster).

    CGSS encodes missing ages as 0 / 999 / 9998 / 9999 rather than NaN, so
    ages outside [1, 110] are treated as missing.
    """
    ages = []
    for i in range(1, 11):
        rel = _num(row, f"d3a{i}", reject8=False)
        if rel is not None and 2 <= rel <= 6:
            a = _num(row, f"d3c{i}")
            if a is not None and 1 <= a <= 110:
                ages.append(a)
    for i in range(1, 6):
        a = _num(row, f"d5b{i}")
        if a is not None and 1 <= a <= 110:
            ages.append(a)
    return ages


def _children_count(row):
    d4 = _num(row, "d4")
    if d4 == 3:
        return "None"
    kids = 0
    for i in range(1, 11):
        rel = _num(row, f"d3a{i}", reject8=False)
        if rel is not None and 2 <= rel <= 6:
            kids += 1
    for i in range(1, 6):
        if _num(row, f"d5a{i}") is not None:
            kids += 1
    if kids == 0:
        return None
    ages = _child_ages(row)
    if ages and all(a >= 18 for a in ages):
        return "Adult children"
    if kids == 1:
        return "1 child"
    if kids == 2:
        return "2 children"
    return "3+ children"


def _has_grandchild(row):
    return any(_num(row, f"d3a{i}", reject8=False) in (8, 9) for i in range(1, 11))


def _parental_status(row):
    if _has_grandchild(row):
        return "Grandparent"
    d4 = _num(row, "d4")
    if d4 == 3:
        return "Not a parent"
    ages = _child_ages(row)
    if not ages:
        return None
    return "Parent of minors" if any(a < 18 for a in ages) else "Parent of adults"


def _parenting_journey(row):
    if _num(row, "d4") == 3:
        return "No children"
    if _has_grandchild(row):
        return "Raising grandchildren"
    ages = _child_ages(row)
    if not ages:
        return None
    youngest = min(ages)
    if youngest <= 12:
        return "Young children"
    if youngest <= 17:
        return "Teenagers"
    co_resident = any(
        2 <= (_num(row, f"d3a{i}") or 0) <= 6 and _num(row, f"d3e{i}") == 1
        for i in range(1, 11)
    )
    return "Empty nester" if not co_resident else "Grown children"


def _housing_status(row):
    """a121=现住房产权(自己) 1; a128=现住房产权(租借) 1; a12a=是否拥有(含共同)房产.
    Judge the CURRENT dwelling first; a12a only supplements. Mortgage vs own
    outright cannot be distinguished in CGSS2017 -> conservative 'Own outright'.
    """
    rent = _num(row, "a128")
    if rent == 1:
        return "Renting"
    own = _num(row, "a121")
    a12a = _num(row, "a12a")
    if own == 1 or a12a == 1:
        return "Own outright"
    return None


def _loss_experience(row):
    f = _num(row, "d61a")
    m = _num(row, "d62a")
    if f == 2 and m == 2:
        return "Multiple bereavements"
    if f == 2 or m == 2:
        return "Lost a parent"
    if f == 1 and m == 1:
        return "No major loss"
    return None


def _rel_history(row):
    d24 = _num(row, "d24")
    if d24 == 1:
        return "Married once"
    if d24 == 2:
        return "Remarried"
    return None


def _geo_mobility(row):
    a21 = _num(row, "a21")
    if a21 == 1:
        return "Never left hometown"
    if a21 == 2:
        return "Moved within region"
    if a21 == 3:
        return "Moved nationally"
    return None


# ---------------------------------------------------------------- employment

def _employment_status(row):
    a53 = _num(row, "a53")
    if a53 in (2, 4):  # working (incl. paid leave)
        a59a = _num(row, "a59a", reject8=False)  # 8=自由职业者
        if a59a in (1, 2, 6, 7):
            return "Self-employed"
        if a59a in (5, 8):
            return "Gig / freelance"
        if a59a in (3, 4):
            return "Part-time" if _num(row, "a59e") == 2 else "Full-time"
        return None  # working but job-type unknown -> unobserved
    if a53 == 3:
        return "Unemployed"
    if a53 == 1:
        a54 = _num(row, "a54", reject8=False)  # 8=料理家务
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
    """a59c = years since first non-farm job. 0 means 'no non-farm work
    history' (farmers/students/unemployed) -> null, not '0-2 years'."""
    y = _num(row, "a59c")
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
    j = _num(row, "a59j")
    if j in (1, 3, 6):
        return "Public sector"
    if j == 4:
        return "NGO"
    if j == 5:
        return "Solo / freelance"
    if j == 2:
        l = _num(row, "a59l")
        if l is None or l >= 99990:  # 99998/99999 = 无单位/不知道
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
    f = _num(row, "a59f")  # 1 only-manages 2 manages+managed 3 managed 4 neither
    if f in (1, 2):
        return "Manager"
    if f == 3:
        return "Mid"
    if f == 4:
        return "Entry"
    return None


def _entrepreneurship(row):
    if _num(row, "a59a") in (1, 2):
        return "Founded once"
    return None


# ---------------------------------------------------------------- media / internet

def _tech_savviness(row):
    a30e = _num(row, "a30e")  # 1=上网过 2=没上过
    if a30e == 2:
        return "Avoidant"
    if a30e == 1:
        f = _num(row, "a3012")  # leisure internet freq
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


def _payment_pref(row):
    if _num(row, "a30g") == 1 or _num(row, "a30h") == 1:
        return "Mobile wallet"
    return None  # not using mobile payment does not imply cash preference


def _news_freq(row):
    """a30c = minutes/day reading news via internet/WeChat/Weibo. CGSS missing
    codes on this continuous field are 998/999 (not NaN), so range-check."""
    m = _num(row, "a30c")
    if m is None or not (0 <= m <= 1440):
        return None
    if m >= 60:
        return "Constant"
    if m >= 30:
        return "Daily"
    if m >= 1:
        return "Daily"  # the question is minutes *per day*: any >0 is daily
    return "Avoids news"


_FREQ5 = {"1": "Daily", "2": "Weekly", "3": "Monthly", "4": "Rarely", "5": "Never"}


def _media_diet(row):
    v = _num(row, "a29")
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
    v = _num(row, "a308")
    if v is None:
        return None
    if v == 1:
        return "All day"
    if v == 2:
        return "Daily"
    if v == 3:
        return "Sometimes"
    return "Rarely"


# ---------------------------------------------------------------- attitudes

def _gender_roles(row):
    scores = []
    for i, rev in ((1, False), (2, False), (3, False), (4, False), (5, True)):
        v = _num(row, f"a42{i}")
        if v is None:
            continue
        scores.append(6 - v if rev else v)
    return _band5(_mean(scores))


def _remote_work(row):
    v = _num(row, "c58")
    if v in (1, 2):
        return "Enthusiast"
    if v == 3:
        return "Neutral"
    if v in (4, 5):
        return "Opposed"
    return None


def _data_privacy(row):
    return _band5(_mean([_num(row, f"c62{i}") for i in range(1, 6)]))


def _gov_regulation(row):
    # d16x: 1=都是政府的责任 … 5=都是个人/家庭的责任 -> reverse to "govt-responsibility" score
    return _band5(_mean([6 - v for v in (_num(row, f"d16{i}") for i in range(1, 5)) if v is not None]))


def _doomscrolling(row):
    s = _mean([6 - v for v in (_num(row, f"c49{i}") for i in range(1, 12)) if v is not None])
    if s is None:
        return None
    if s >= 4:
        return "Daily"
    if s >= 3:
        return "Weekly"
    if s >= 2.3:
        return "Monthly"
    if s >= 1.5:
        return "Rarely"
    return "Never"


def _optimism(row):
    """LOT-R: d381/d383/d386 are positively-keyed (agree = optimistic),
    d382/d384/d385 negatively-keyed (agree = pessimistic). 1=非常同意…5=非常不同意.
    Positive items score 6-v, negative items score v; higher = more optimistic."""
    rev = {2, 4, 5}
    s = _mean([6 - v if i not in rev else v
               for i in range(1, 7)
               for v in [_num(row, f"d38{i}")] if v is not None])
    if s is None:
        return None
    if s >= 4.4:
        return "Signature"
    if s >= 3.6:
        return "Strong"
    if s >= 2.8:
        return "Moderate"
    if s >= 2.0:
        return "Slight"
    return "Absent"


def _self_efficacy(row):
    v = _num(row, "c32")  # 1=完全符合(高效能)
    if v is None:
        return None
    if v <= 2:
        return "Very high"
    if v == 3:
        return "High"
    if v == 4:
        return "Average"
    if v == 5:
        return "Low"
    return "Very low"


def _depression(row):
    v = _num(row, "a17")  # 1=总是(抑郁高)
    if v is None:
        return None
    return {1: "Very high", 2: "High", 3: "Average", 4: "Low", 5: "Very low"}.get(int(v))


def _val_family(row):
    v = _num(row, "d202")  # 7pt: 1=非常同意(家庭优先)
    if v is None:
        return None
    if v <= 2:
        return "Core value"
    if v <= 4:
        return "Important"
    if v <= 5:
        return "Moderate"
    if v == 6:
        return "Minor"
    return "Irrelevant"


def _economic_motivation(row):
    v = _num(row, "c34")  # 1=非常困难 5=非常容易
    if v is None:
        return None
    if v <= 2:
        return "Cost-sensitive"
    if v == 3:
        return "Indifferent"
    return "Value-driven"


def _energy_level(row):
    v = _num(row, "a16")  # 1=总是受限(能量低)
    if v is None:
        return None
    return {1: "None", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"}.get(int(v))


CROSSWALK = {
    "age_bracket": {"compute": _age_bracket, "prov": "observed"},
    "region": {"compute": _region, "prov": "observed"},
    "gender_identity": {
        "src": "a2",
        "map": {"1": "Man", "男": "Man", "2": "Woman", "女": "Woman"},
        "prov": "observed",
    },
    "demo_ethnicity_broad": {"compute": _ethnicity, "prov": "observed"},
    "highest_education": {
        "src": "a7a",
        "map": {
            "1": "No formal", "没有受过任何教育": "No formal",
            "2": "No formal", "私塾、扫盲班": "No formal",
            "3": "Primary", "小学": "Primary",
            "4": "Secondary", "初中": "Secondary",
            "5": "Vocational / cert", "职业高中": "Vocational / cert",
            "6": "Secondary", "普通高中": "Secondary",
            "7": "Vocational / cert", "中专": "Vocational / cert",
            "8": "Vocational / cert", "技校": "Vocational / cert",
            "9": "Associate's", "大学专科（成人高等教育）": "Associate's",
            "10": "Associate's", "大学专科（正规高等教育）": "Associate's",
            "11": "Bachelor's", "大学本科（成人高等教育）": "Bachelor's",
            "12": "Bachelor's", "大学本科（正规高等教育）": "Bachelor's",
            "13": None, "研究生及以上": None,
            "14": None, "其他": None,
        },
        "prov": "observed",
    },
    "demo_marital_status": {
        "src": "a69",
        "map": {
            "1": "Single", "未婚": "Single",
            "2": "Domestic partnership", "同居": "Domestic partnership",
            "3": "Married", "初婚有配偶": "Married",
            "4": "Married", "再婚有配偶": "Married",
            "5": "Separated", "分居未离婚": "Separated",
            "6": "Divorced", "离婚": "Divorced",
            "7": "Widowed", "丧偶": "Widowed",
        },
        "prov": "observed",
    },
    "demo_religion_affiliation": {"compute": _religion, "prov": "observed"},
    "religiosity": {"compute": _religiosity, "prov": "observed"},
    "health_general_health": {
        "src": "a15",
        "map": {
            "1": "Poor", "很不健康": "Poor",
            "2": "Poor", "比较不健康": "Poor",
            "3": "Fair", "一般": "Fair",
            "4": "Good", "比较健康": "Good",
            "5": "Excellent", "很健康": "Excellent",
        },
        "prov": "observed",
    },
    "trust_level": {
        "src": "v458",
        "map": {
            "1": "Skeptical", "非常不同意": "Skeptical",
            "2": "Skeptical", "比较不同意": "Skeptical",
            "3": "Verifying", "说不上同意不同意": "Verifying",
            "4": "Trusting", "比较同意": "Trusting",
            "5": "Trusting", "非常同意": "Trusting",
        },
        "prov": "observed",
    },
    "socioeconomic_band": {"compute": _socioeconomic_band, "prov": "observed"},

    # ---- family / life events ----
    "lstyle_household_size": {"compute": _household_size, "prov": "observed"},
    "demo_children_count": {"compute": _children_count, "prov": "observed"},
    "demo_parental_status": {"compute": _parental_status, "prov": "observed"},
    "lifex_parenting_journey": {"compute": _parenting_journey, "prov": "observed"},
    "demo_housing_status": {"compute": _housing_status, "prov": "observed"},
    "lifex_loss_experience": {"compute": _loss_experience, "prov": "observed"},
    "lifex_relationship_history": {"compute": _rel_history, "prov": "observed"},
    "lifex_geographic_mobility": {"compute": _geo_mobility, "prov": "observed"},
    "lstyle_cooking_freq": {
        "src": "d131",
        "map": {"1": "Daily", "2": "Weekly", "3": "Weekly", "4": "Monthly",
                "5": "Rarely", "6": "Rarely", "7": "Never"},
        "prov": "observed",
    },

    # ---- employment / career ----
    "demo_employment_status": {"compute": _employment_status, "prov": "observed"},
    "years_experience": {"compute": _years_experience, "prov": "observed"},
    "company_size": {"compute": _company_size, "prov": "observed"},
    "seniority": {"compute": _seniority, "prov": "observed"},
    "lifex_entrepreneurship_history": {"compute": _entrepreneurship, "prov": "observed"},

    # ---- media / internet ----
    "tech_savviness": {"compute": _tech_savviness, "prov": "observed"},
    "lstyle_payment_pref": {"compute": _payment_pref, "prov": "observed"},
    "lstyle_news_freq": {"compute": _news_freq, "prov": "observed"},
    "lstyle_reading_freq": {"src": "a304", "map": _FREQ5, "prov": "observed"},
    "lstyle_music_listening": {"compute": _music_listening, "prov": "observed"},
    "lstyle_podcast_listening": {
        "src": "a283",
        "map": {"1": "Never", "2": "Rarely", "3": "Monthly", "4": "Weekly", "5": "Daily"},
        "prov": "observed",
    },
    "media_diet": {"compute": _media_diet, "prov": "observed"},
    "lstyle_exercise_freq": {"src": "a309", "map": _FREQ5, "prov": "observed"},

    # ---- attitudes ----
    "att_traditional_gender_roles": {"compute": _gender_roles, "prov": "observed"},
    "att_remote_work": {"compute": _remote_work, "prov": "observed"},
    "att_data_privacy": {"compute": _data_privacy, "prov": "observed"},
    "att_government_regulation": {"compute": _gov_regulation, "prov": "observed"},
    "habit_doomscrolling": {"compute": _doomscrolling, "prov": "observed"},
    "trait_hope_optimism": {"compute": _optimism, "prov": "observed"},
    "big5_self_efficacy": {"compute": _self_efficacy, "prov": "observed"},
    "bfi2_facet_depression": {"compute": _depression, "prov": "observed"},
    "val_family": {"compute": _val_family, "prov": "observed"},
    "economic_motivation": {"compute": _economic_motivation, "prov": "observed"},
    "health_energy_level": {"compute": _energy_level, "prov": "observed"},
}


def render(row, labels_path=None):
    """Layer-2: faithful Chinese profile_text rendered from the coded row.

    Each answered item becomes one sentence '题目: 答项' (numeric codes decoded
    via the wave's labels file), so an LLM can quote verbatim evidence from it.
    """
    import json as _json
    import os as _os
    import re as _re

    path = labels_path or _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)), "labels2017.json"
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
        "lifex_parenting_journey": {"No children", "Young children", "Teenagers", "Grown children", "Empty nester", "Raising grandchildren"},
        "demo_housing_status": {"Own outright", "Mortgage", "Renting", "Living with family", "Shared housing", "Temporary / transitional"},
        "lifex_loss_experience": {"No major loss", "Lost a grandparent", "Lost a parent", "Lost a partner / child", "Multiple bereavements"},
        "lifex_relationship_history": {"Limited", "A few relationships", "Long-term partnership", "Married once", "Remarried", "Widowed"},
        "lifex_geographic_mobility": {"Never left hometown", "Moved within region", "Moved nationally", "Moved internationally", "Serial relocator"},
        "lstyle_cooking_freq": {"Daily", "Weekly", "Monthly", "Rarely", "Never"},
        "demo_employment_status": {"Full-time", "Part-time", "Self-employed", "Gig / freelance", "Student", "Unemployed", "Retired", "Homemaker"},
        "years_experience": {"0-2", "3-5", "6-10", "11-20", "20+"},
        "company_size": {"Solo / freelance", "Startup (<50)", "SMB (50-500)", "Mid (500-5k)", "Enterprise (5k+)", "Public sector", "Academia", "NGO"},
        "seniority": {"Student / intern", "Entry", "Mid", "Senior", "Lead / Principal", "Manager", "Director", "VP", "C-suite", "Founder", "Retired"},
        "lifex_entrepreneurship_history": {"Never considered", "Considered it", "Side hustle", "Founded once", "Serial founder", "Exited a company"},
        "tech_savviness": {"Digital native", "Comfortable", "Cautious adopter", "Reluctant", "Avoidant"},
        "lstyle_payment_pref": {"Credit card", "Debit card", "Mobile wallet", "Cash", "BNPL", "Crypto"},
        "lstyle_news_freq": {"Constant", "Daily", "Weekly", "Rarely", "Avoids news"},
        "lstyle_reading_freq": {"Daily", "Weekly", "Monthly", "Rarely", "Never"},
        "lstyle_music_listening": {"All day", "Daily", "Sometimes", "Rarely"},
        "lstyle_podcast_listening": {"Daily", "Weekly", "Monthly", "Rarely", "Never"},
        "media_diet": {"Academic journals", "News", "Social-media-heavy", "Long-form", "Video-first", "Minimal"},
        "lstyle_exercise_freq": {"Daily", "Weekly", "Monthly", "Rarely", "Never"},
        "att_traditional_gender_roles": {"Enthusiast", "Positive", "Neutral", "Skeptical", "Opposed"},
        "att_remote_work": {"Enthusiast", "Positive", "Neutral", "Skeptical", "Opposed"},
        "att_data_privacy": {"Enthusiast", "Positive", "Neutral", "Skeptical", "Opposed"},
        "att_government_regulation": {"Enthusiast", "Positive", "Neutral", "Skeptical", "Opposed"},
        "habit_doomscrolling": {"Daily", "Weekly", "Monthly", "Rarely", "Never"},
        "trait_hope_optimism": {"Signature", "Strong", "Moderate", "Slight", "Absent"},
        "big5_self_efficacy": {"Very high", "High", "Average", "Low", "Very low"},
        "bfi2_facet_depression": {"Very high", "High", "Average", "Low", "Very low"},
        "val_family": {"Core value", "Important", "Moderate", "Minor", "Irrelevant"},
        "economic_motivation": {"Cost-sensitive", "Value-driven", "Premium-seeking", "Indifferent"},
        "health_energy_level": {"Very high", "High", "Moderate", "Low", "None"},
    }

    # (a) fully-answered respondent (numeric codes, as dta_to_rows produces)
    row = {
        "user_id": "u1",
        "a2": 2, "a31": 1975, "a4": 1, "a7a": 12, "a69": 3,
        "a51": 0, "a511": 1, "a6": 6, "a15": 4, "v458": 4, "a43e": 3,
        "a301": 2, "a302": 3, "a304": 1, "a308": 2, "a309": 3, "a3012": 1,
        "a29": 5, "a30c": 45, "a30e": 1, "a30g": 1, "a30h": 1, "a283": 2, "a284": 3,
        "a12a": 1, "a121": 1, "a128": 0,
        "a17": 4, "a16": 4, "a421": 4, "a422": 3, "a423": 4, "a424": 2, "a425": 2,
        "a53": 4, "a54": 8, "a59a": 3, "a59c": 15, "a59e": 1, "a59f": 3,
        "a59j": 2, "a59l": 120,
        "c32": 2, "c34": 4, "c58": 1,
        "c491": 2, "c492": 3, "c493": 2, "c494": 3, "c495": 2, "c496": 3,
        "c497": 2, "c498": 3, "c499": 2, "c4910": 3, "c4911": 2,
        "c621": 4, "c622": 4, "c623": 3, "c624": 4, "c625": 4,
        "d24": 1, "d131": 2, "d161": 2, "d162": 2, "d163": 2, "d164": 2,
        "d202": 2, "d381": 1, "d382": 5, "d383": 1, "d384": 5, "d385": 5, "d386": 1,
        "d61a": 1, "d62a": 2,
        "d3a1": 1, "d3a2": 2, "d3a3": 2, "d3e1": 1, "d3e2": 1, "d3e3": 1,
        "d3c1": 42, "d3c2": 15, "d3c3": 12, "d4": 1, "d5a1": 3,
    }
    obs, prov, unmapped = apply_crosswalk(row, CROSSWALK, allowed)
    assert obs["age_bracket"] == "35-44", obs
    assert obs["gender_identity"] == "Woman"
    assert obs["demo_ethnicity_broad"] == "East Asian"
    assert obs["highest_education"] == "Bachelor's"
    assert obs["demo_marital_status"] == "Married"
    assert obs["demo_religion_affiliation"] == "Buddhist"
    assert obs["religiosity"] == "Observant"
    assert obs["health_general_health"] == "Good"
    assert obs["trust_level"] == "Trusting"
    assert obs["socioeconomic_band"] == "Middle"
    # family
    assert obs["lstyle_household_size"] == "3-4 people", obs  # d3a1-3 = 3 members
    assert obs["demo_children_count"] == "3+ children", obs  # d3a2+d3a3 + d5a1
    assert obs["demo_parental_status"] == "Parent of minors", obs  # kids 15,12
    assert obs["lifex_parenting_journey"] == "Young children", obs  # youngest 12
    assert obs["demo_housing_status"] == "Own outright"
    assert obs["lifex_loss_experience"] == "Lost a parent"
    assert obs["lifex_relationship_history"] == "Married once"
    assert "lifex_geographic_mobility" not in obs  # a21 missing -> unobserved
    assert obs["lstyle_cooking_freq"] == "Weekly"
    # employment
    assert obs["demo_employment_status"] == "Full-time", obs
    assert obs["years_experience"] == "11-20", obs  # 15y
    assert obs["company_size"] == "SMB (50-500)", obs  # 120 employees
    assert obs["seniority"] == "Mid", obs  # managed
    assert "lifex_entrepreneurship_history" not in obs  # employee
    # media
    assert obs["tech_savviness"] == "Digital native", obs
    assert obs["lstyle_payment_pref"] == "Mobile wallet"
    assert obs["lstyle_news_freq"] == "Daily", obs  # 45 min/day -> daily
    assert obs["lstyle_reading_freq"] == "Daily"
    assert obs["lstyle_music_listening"] == "Daily"
    assert obs["lstyle_podcast_listening"] == "Rarely", obs  # a283=2
    assert obs["media_diet"] == "Social-media-heavy", obs  # a29=5
    assert obs["lstyle_exercise_freq"] == "Monthly"
    # attitudes
    assert obs["att_remote_work"] == "Enthusiast", obs  # c58=1
    assert obs["att_data_privacy"] == "Positive", obs  # ~3.8
    assert obs["att_government_regulation"] == "Positive", obs  # mean(6-2,..)=4.0
    assert obs["habit_doomscrolling"] == "Weekly", obs  # mean(6-2,6-3,...)=3.5
    assert obs["trait_hope_optimism"] == "Signature", obs  # LOT-R: pos(6-1)=5, neg(5)=5 -> mean 5.0
    assert obs["big5_self_efficacy"] == "Very high", obs  # c32=2
    assert obs["bfi2_facet_depression"] == "Low", obs  # a17=4
    assert obs["val_family"] == "Core value", obs  # d202=2
    assert obs["economic_motivation"] == "Value-driven", obs  # c34=4
    assert obs["health_energy_level"] == "High", obs  # a16=4 -> High

    # (b) numeric-code input: no-religion / single / rural-worker edge cases
    row2 = {
        "user_id": "u2", "a2": 1, "a31": 1990, "a4": 1, "a7a": 4, "a69": 1,
        "a51": 1, "a15": 3, "v458": 2, "a43e": 5, "d4": 3, "d61a": 1, "d62a": 1,
        "a53": 1, "a54": 1, "a3012": 5, "a30e": 2, "a30c": 0,
    }
    obs2, _p2, _u2 = apply_crosswalk(row2, CROSSWALK, allowed)
    assert obs2["age_bracket"] == "25-34"
    assert obs2["demo_religion_affiliation"] == "None" and obs2["religiosity"] == "Secular"
    assert obs2["demo_employment_status"] == "Student", obs2
    assert obs2["tech_savviness"] == "Avoidant"
    assert obs2["lstyle_news_freq"] == "Avoids news", obs2  # 0 min
    assert obs2["demo_children_count"] == "None"
    assert obs2["demo_parental_status"] == "Not a parent"
    assert obs2["lifex_parenting_journey"] == "No children"
    assert obs2["lifex_loss_experience"] == "No major loss"

    # (c) faithfulness: non-Han / too-coarse / withheld codes stay null
    coarse = {"a2": 1, "a31": 1982, "a4": 4, "a7a": 13, "a69": 5, "a51": 0, "a521": 1,
              "a15": 98, "v458": 99, "a43e": 98, "a30g": 2, "a30h": 2, "a59j": 7, "a59a": 9}
    obs3, _p3, _u3 = apply_crosswalk(coarse, CROSSWALK, allowed)
    assert "demo_ethnicity_broad" not in obs3
    assert "highest_education" not in obs3
    assert "demo_religion_affiliation" not in obs3
    assert "health_general_health" not in obs3 and "trust_level" not in obs3
    assert "socioeconomic_band" not in obs3
    assert "lstyle_payment_pref" not in obs3
    assert "demo_employment_status" not in obs3

    # garbage birth year -> null
    obs4, _, _ = apply_crosswalk({"a2": 1, "a31": 9999, "a4": 1}, CROSSWALK, allowed)
    assert "age_bracket" not in obs4

    # (d) 8-as-business-value paths (a54=8 料理家务, a59a=8 自由职业者, d3a=8 孙辈)
    obs8, _, _ = apply_crosswalk({"a2": 1, "a31": 1970, "a4": 1, "a53": 1, "a54": 8}, CROSSWALK, allowed)
    assert obs8["demo_employment_status"] == "Homemaker", obs8
    obs9, _, _ = apply_crosswalk({"a2": 1, "a31": 1985, "a4": 1, "a53": 4, "a59a": 8}, CROSSWALK, allowed)
    assert obs9["demo_employment_status"] == "Gig / freelance", obs9
    obs10, _, _ = apply_crosswalk({"a2": 1, "a31": 1950, "a4": 1, "d4": 2, "d3a1": 8, "d3c1": 5}, CROSSWALK, allowed)
    assert obs10["demo_parental_status"] == "Grandparent", obs10
    assert obs10["lifex_parenting_journey"] == "Raising grandchildren", obs10

    print(f"cgss crosswalk self-test: {len(CROSSWALK)} dims, mapping + faithfulness verified ✅")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Raw CGSS2017 crosswalk for crosswalk_engine.")
    ap.add_argument("--selftest", action="store_true", help="verify the crosswalk against the engine")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        ap.print_help()
