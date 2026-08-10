#!/usr/bin/env python3
"""Generate a small CGSS2017-style pilot sample for the cgss crosswalk.

Simulates what `dta_to_rows.py` produces: **raw numeric codes** (apply_value_formats=False),
matching the `crosswalks/cgss.py` contract. 200 rows, distribution loosely shaped after a
mainland-China adult sample. This is a synthetic demo fixture — for real data run
`dta_to_rows.py` on the official CGSS2017.dta.

Output: ../../outputs/cgss2017_pilot/rows_sample.jsonl (gitignored)
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # persona/curation/existing_data
OUT_DIR = ROOT / "outputs" / "cgss2017_pilot"
N = 200
FIELD_YEAR = 2017

SEX = [1, 2]
ETHNICITY = ([1] * 190) + [4, 5, 6, 7, 8, 9, 10, 11, 12, 56]
EDUCATION = (
    [1] * 4 + [3] * 15 + [4] * 40 + [5] * 8 + [6] * 25 + [7] * 8 + [8] * 4
    + [10] * 25 + [12] * 40 + [11] * 8 + [13] * 15 + [14] * 8
)
MARITAL = [1] * 45 + [3] * 105 + [4] * 8 + [2] * 5 + [5] * 3 + [6] * 15 + [7] * 19
RELIGION_ROWS = (
    [{"a51": 1}] * 150
    + [{"a511": 1}] * 30
    + [{"a512": 1}] * 6
    + [{"a513": 1}] * 5
    + [{"a514": 1}] * 3
    + [{"a515": 1}] * 2
    + [{"a516": 1}] * 4
)
RELIG_FREQ = [1, 2, 3, 4, 5, 6, 7, 8, 9]
HEALTH = [1] * 4 + [2] * 20 + [3] * 60 + [4] * 90 + [5] * 26
TRUST = [1] * 12 + [2] * 60 + [3] * 10 + [4] * 100 + [5] * 14
SES = [1] * 2 + [2] * 30 + [3] * 80 + [4] * 70 + [5] * 18
FREQ5 = [1, 2, 3, 4, 5]  # leisure / media freq
EMP = ([1] * 40 + [2] * 5 + [3] * 5 + [4] * 150)
NOTWORK_REASON = [1] * 8 + [7] * 20 + [8] * 10 + [4] * 6 + [9] * 4
JOB_TYPE = [1] * 10 + [2] * 25 + [3] * 120 + [4] * 10 + [5] * 8 + [8] * 12 + [9] * 5
ATT5 = [1, 2, 3, 4, 5]
ATT7 = [1, 2, 3, 4, 5, 6, 7]


def main() -> None:
    rng = random.Random(2017)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(1, N + 1):
        age = rng.choices([22, 28, 35, 42, 50, 60, 70, 80], weights=[15, 15, 15, 15, 15, 12, 8, 5])[0] + rng.randint(-2, 2)
        age = max(18, min(88, age))
        religion = dict(rng.choice(RELIGION_ROWS))
        for col in ("a51", "a511", "a512", "a513", "a514", "a515", "a516", "a517", "a521"):
            religion.setdefault(col, 0)
        kids = 1 if age >= 25 and rng.random() < 0.7 else 0
        rows.append(
            {
                "user_id": f"cgss2017-{i:04d}",
                "a2": rng.choice(SEX),
                "a31": FIELD_YEAR - age,
                "a4": rng.choice(ETHNICITY),
                "a7a": rng.choice(EDUCATION),
                "a69": rng.choice(MARITAL),
                **religion,
                "a6": rng.choice(RELIG_FREQ),
                "a15": rng.choice(HEALTH),
                "v458": rng.choice(TRUST),
                "a43e": rng.choice(SES),
                "a301": rng.choice(FREQ5), "a302": rng.choice(FREQ5),
                "a304": rng.choice(FREQ5), "a308": rng.choice(FREQ5),
                "a309": rng.choice(FREQ5), "a3012": rng.choice(FREQ5),
                "a29": rng.choice([4, 5, 5, 5, 6, 1, 3]),
                "a30c": rng.choice([0, 0, 10, 30, 45, 90, 180, 360]),
                "a30e": rng.choice([1, 1, 1, 2]),
                "a30g": rng.choice([1, 1, 2]), "a30h": rng.choice([1, 1, 2]),
                "a283": rng.choice(FREQ5),
                "a12a": 1, "a121": rng.choice([0, 1]), "a128": rng.choice([0, 0, 1]),
                "a17": rng.choice(ATT5), "a16": rng.choice(ATT5),
                "a421": rng.choice(ATT5), "a422": rng.choice(ATT5),
                "a423": rng.choice(ATT5), "a424": rng.choice(ATT5), "a425": rng.choice(ATT5),
                "a53": rng.choice(EMP), "a54": rng.choice(NOTWORK_REASON),
                "a59a": rng.choice(JOB_TYPE), "a59c": rng.choice([0, 0, 3, 8, 15, 22, 30]),
                "a59e": rng.choice([1, 1, 2]), "a59f": rng.choice([1, 2, 3, 4]),
                "a59j": rng.choice([1, 2, 2, 2, 3, 4, 5]), "a59l": rng.choice([5, 30, 120, 1500, 9000]),
                "c32": rng.choice(ATT7), "c34": rng.choice(ATT5), "c58": rng.choice(ATT5),
                **{f"c49{j}": rng.choice(ATT5) for j in range(1, 12)},
                **{f"c62{j}": rng.choice(ATT5) for j in range(1, 6)},
                "d24": rng.choice([1, 1, 2]), "d131": rng.choice([1, 1, 2, 3, 5, 6, 7]),
                **{f"d16{j}": rng.choice(ATT5) for j in range(1, 5)},
                "d202": rng.choice(ATT7),
                **{f"d38{j}": rng.choice(ATT5) for j in range(1, 7)},
                "d61a": rng.choice([1, 1, 2]), "d62a": rng.choice([1, 1, 1, 2]),
                "d3a1": rng.choice([1, 1, 2, 10]), "d3a2": kids if kids else None,
                "d3c1": rng.choice([30, 42, 55, 68]), "d3c2": rng.choice([5, 12, 18, 25]) if kids else None,
                "d3e1": 1, "d3e2": rng.choice([1, 2]) if kids else None,
                "d4": rng.choice([1, 1, 2, 3]), "d5a1": rng.choice([1, 2, 3, 11]) if rng.random() < 0.3 else None,
                "d5b1": rng.choice([16, 22, 28]) if kids else None,
            }
        )
    out = OUT_DIR / "rows_sample.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} sample rows -> {out}")


if __name__ == "__main__":
    main()
