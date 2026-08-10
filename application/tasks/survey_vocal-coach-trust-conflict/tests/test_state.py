from __future__ import annotations

import json
import os
import sys
from pathlib import Path


OUTPUT_DIR = Path(os.environ.get("HARBOR_OUTPUT_DIR") or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")
RESULT_PATH = OUTPUT_DIR / "survey_result.json"
EXPECTED_IDS = {
    "q0_research_role", "q1_decision_context", "q2_baseline_trust",
    "q3_evidence_ab", "q4_high_confidence_behavior", "q5_low_confidence_ab",
    "q6_low_confidence_behavior", "q7_user_disagreement_ab",
    "q8_user_disagreement_behavior", "q9_teacher_conflict_ab",
    "q10_teacher_override_effect", "q11_professional_control",
    "q12_known_error_repair_ab", "q13_post_error_behavior",
    "q14_accuracy_claim_ab", "q15_adoption_boundary",
    "q16_professional_acceptance", "q17_final_trust", "q18_decisive_boundary",
}
EVENT_KEYS = {"timestamp", "actor", "action", "context", "outcome"}


def verifier_dir() -> Path:
    path = Path(os.environ.get("HARBOR_VERIFIER_DIR") or "/logs/verifier")
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
    answer_ids = [str(answer.get("questionId") or "") for answer in answers if isinstance(answer, dict)]
    if len(answer_ids) != 19 or set(answer_ids) != EXPECTED_IDS:
        return fail("survey must contain one answer for each of the 19 expected questions")
    if not isinstance(trajectory, list) or not trajectory:
        return fail("survey_result.trajectory must be a non-empty list")
    for index, event in enumerate(trajectory):
        if not isinstance(event, dict) or not EVENT_KEYS <= set(event):
            return fail(f"trajectory[{index}] is missing required fields")
        if not isinstance(event.get("context"), dict) or not isinstance(event.get("outcome"), dict):
            return fail(f"trajectory[{index}] context and outcome must be objects")
    fields = [
        {
            "key": f"question.{answer['questionId']}.response",
            "label": "Selected response",
            "group": f"question.{answer['questionId']}",
            "role": "primary",
            "kind": "numerical" if isinstance(answer.get("value"), (int, float)) and not isinstance(answer.get("value"), bool) else "categorical",
            "value": answer.get("value"),
        }
        for answer in answers
    ]
    contexts = [
        {
            "key": f"question.{answer['questionId']}",
            "label": str(answer.get("prompt") or answer["questionId"]),
            "contextType": "question_response",
            "facets": [
                {
                    "key": "response",
                    "label": "Selected response",
                    "role": "primary",
                    "kind": "numerical" if isinstance(answer.get("value"), (int, float)) and not isinstance(answer.get("value"), bool) else "categorical",
                    "value": answer.get("value"),
                }
            ] + ([{
                "key": "reason", "label": "Reason", "role": "explanation",
                "kind": "textual", "value": str(answer.get("rationale")),
            }] if str(answer.get("rationale") or "").strip() else []),
        }
        for answer in answers
    ]
    structured = {
        "schemaVersion": "1.0",
        "artifactType": "matraix.trial_evaluation",
        "taskType": "survey",
        "presenceCheck": {"passed": True, "requiredArtifacts": ["survey_result.json"], "missingArtifacts": []},
        "sourceArtifacts": {"surveyResult": "/app/output/survey_result.json"},
        "contexts": contexts,
        "fields": fields,
    }
    (verifier_dir() / "structured_output.json").write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

