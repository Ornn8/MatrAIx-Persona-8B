from __future__ import annotations

import json
import os
import sys
from pathlib import Path

OUTPUT_DIR = Path(
    os.environ.get("HARBOR_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
RESULT_PATH = OUTPUT_DIR / "survey_result.json"
EXPECTED_IDS = [
    "q0_research_role",
    "q1_likely_payer",
    "q2_price_perception_68",
    "q3_meaningful_comparison",
    "q4_post_trial_action",
    "q5_primary_cancellation_reason",
    "q6_payment_format_choice",
    "q7_package_choice",
    "q8_tradeoff_choice",
    "q9_vw_too_cheap",
    "q10_vw_bargain",
    "q11_vw_expensive",
    "q12_vw_too_expensive",
    "q13_conversion_proof",
    "q14_decision_explanation",
]
PRICE_IDS = {
    f"cny_{value}": value
    for value in (9, 19, 29, 39, 49, 68, 88, 108, 138, 168, 198, 268)
}
EVENT_KEYS = {"timestamp", "actor", "action", "context", "outcome"}


def _verifier_dir() -> Path:
    explicit = os.environ.get("HARBOR_VERIFIER_DIR")
    if explicit:
        path = Path(explicit)
        path.mkdir(parents=True, exist_ok=True)
        return path
    path = Path("/logs/verifier")
    path.mkdir(parents=True, exist_ok=True)
    return path


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def main() -> int:
    if not RESULT_PATH.is_file():
        return fail("missing /app/output/survey_result.json")
    try:
        payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"survey_result.json is not valid JSON: {exc}")

    answers = payload.get("answers")
    trajectory = payload.get("trajectory")
    if not isinstance(answers, list):
        return fail("survey_result.answers must be a list")
    if not isinstance(trajectory, list) or not trajectory:
        return fail("survey_result.trajectory must be a non-empty list")

    by_id: dict[str, dict] = {}
    for index, answer in enumerate(answers):
        if not isinstance(answer, dict):
            return fail(f"answers[{index}] must be an object")
        question_id = str(answer.get("questionId") or "").strip()
        if not question_id or "value" not in answer:
            return fail(f"answers[{index}] requires questionId and value")
        if question_id in by_id:
            return fail(f"duplicate answer for {question_id}")
        by_id[question_id] = answer
    if list(by_id) != EXPECTED_IDS:
        missing = [qid for qid in EXPECTED_IDS if qid not in by_id]
        extra = [qid for qid in by_id if qid not in EXPECTED_IDS]
        return fail(f"expected 15 ordered answers; missing={missing}, extra={extra}")

    thresholds = []
    for qid in EXPECTED_IDS[9:13]:
        option_id = str(by_id[qid].get("value") or "")
        if option_id not in PRICE_IDS:
            return fail(f"{qid} must use a listed cny_N option id")
        thresholds.append(PRICE_IDS[option_id])
    if not all(left < right for left, right in zip(thresholds, thresholds[1:])):
        return fail(f"Van Westendorp thresholds must be strictly ordered: {thresholds}")

    for index, event in enumerate(trajectory):
        if not isinstance(event, dict):
            return fail(f"trajectory[{index}] must be an object")
        missing = EVENT_KEYS - set(event)
        if missing:
            return fail(f"trajectory[{index}] missing keys: {sorted(missing)}")
        if not isinstance(event.get("context"), dict):
            return fail(f"trajectory[{index}].context must be an object")
        if not isinstance(event.get("outcome"), dict):
            return fail(f"trajectory[{index}].outcome must be an object")

    fields = []
    contexts = []
    for qid in EXPECTED_IDS:
        answer = by_id[qid]
        value = answer["value"]
        kind = "textual" if qid == "q14_decision_explanation" else "categorical"
        facets = [
            {
                "key": "response",
                "label": "Selected response",
                "role": "primary",
                "kind": kind,
                "value": value,
            }
        ]
        rationale = str(answer.get("rationale") or "").strip()
        if rationale:
            facets.append(
                {
                    "key": "reason",
                    "label": "Reason",
                    "role": "explanation",
                    "kind": "textual",
                    "value": rationale,
                }
            )
        contexts.append(
            {
                "key": f"question.{qid}",
                "label": str(answer.get("prompt") or qid),
                "contextType": "question_response",
                "facets": facets,
            }
        )
        for facet in facets:
            fields.append(
                {
                    "key": f"question.{qid}.{facet['key']}",
                    "label": facet["label"],
                    "group": f"question.{qid}",
                    "role": facet["role"],
                    "kind": facet["kind"],
                    "value": facet["value"],
                }
            )
    summary = {
        "key": "answer_count",
        "label": "Answer count",
        "role": "score",
        "kind": "numerical",
        "value": 15,
    }
    contexts.append(
        {
            "key": "survey.summary",
            "label": "Survey summary",
            "contextType": "trial_summary",
            "facets": [summary],
        }
    )
    fields.append(
        {
            **summary,
            "key": "survey.summary.answer_count",
            "group": "survey.summary",
        }
    )
    structured = {
        "schemaVersion": "1.0",
        "artifactType": "matraix.trial_evaluation",
        "taskType": "survey",
        "presenceCheck": {
            "passed": True,
            "requiredArtifacts": ["survey_result.json"],
            "missingArtifacts": [],
        },
        "sourceArtifacts": {"surveyResult": "/app/output/survey_result.json"},
        "contexts": contexts,
        "fields": fields,
    }
    (_verifier_dir() / "structured_output.json").write_text(
        json.dumps(structured, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
