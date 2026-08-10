from __future__ import annotations

import json
import os
import sys
from pathlib import Path

OUTPUT_DIR = Path(os.environ.get("HARBOR_OUTPUT_DIR") or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")
RESULT_PATH = OUTPUT_DIR / "survey_result.json"
EVENT_KEYS = {"timestamp", "actor", "action", "context", "outcome"}
QUESTION_TYPES = {
    "q0_research_role": "single_choice",
    "q1_current_frequency": "single_choice",
    "q2_primary_first_week_goal": "single_choice",
    "q3_stage_profile_setup": "single_choice",
    "q4_stage_priority_result": "single_choice",
    "q5_stage_evidence_confidence": "single_choice",
    "q6_teacher_conflict_decision": "single_choice",
    "q7_stage_exercise_start": "single_choice",
    "q8_practice_frequency": "single_choice",
    "q9_reminder_preference": "single_choice",
    "q10_stage_midweek_decision": "single_choice",
    "q11_safety_stop_decision": "single_choice",
    "q12_improvement_threshold": "single_choice",
    "q13_stage_day7_clear_improvement": "single_choice",
    "q14_stage_day7_weak_improvement": "single_choice",
    "q15_postweek_practice_intent": "single_choice",
    "q16_subscription_decision_68": "single_choice",
    "q17_subscription_blocker": "single_choice",
    "q18_full_curriculum_expectation": "single_choice",
    "q19_decisive_optimization": "single_choice",
}


def verifier_dir() -> Path:
    explicit = os.environ.get("HARBOR_VERIFIER_DIR")
    path = Path(explicit) if explicit else Path("/logs/verifier")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError("HARBOR_VERIFIER_DIR is required outside a Harbor container") from exc
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
    if not isinstance(payload, dict):
        return fail("survey_result.json must contain an object")
    answers = payload.get("answers")
    trajectory = payload.get("trajectory")
    if not isinstance(answers, list):
        return fail("survey_result.answers must be a list")
    if not isinstance(trajectory, list) or not trajectory:
        return fail("survey_result.trajectory must be a non-empty list")

    seen: set[str] = set()
    contexts: list[dict[str, object]] = []
    fields: list[dict[str, object]] = []
    for index, answer in enumerate(answers):
        if not isinstance(answer, dict):
            return fail(f"answers[{index}] must be an object")
        question_id = str(answer.get("questionId") or "").strip()
        if question_id not in QUESTION_TYPES:
            return fail(f"answers[{index}] has unknown questionId: {question_id}")
        if question_id in seen:
            return fail(f"duplicate answer for {question_id}")
        seen.add(question_id)
        value = answer.get("value")
        if not isinstance(value, str) or not value.strip():
            return fail(f"{question_id}.value must be a non-empty choice id")
        facets: list[dict[str, object]] = [{
            "key": "response", "label": "Selected response", "role": "primary",
            "kind": "categorical", "value": value,
        }]
        fields.append({
            "key": f"question.{question_id}.response", "label": "Selected response",
            "group": f"question.{question_id}", "role": "primary",
            "kind": "categorical", "value": value,
        })
        rationale = str(answer.get("rationale") or "").strip()
        if rationale:
            facets.append({
                "key": "reason", "label": "Reason", "role": "explanation",
                "kind": "textual", "value": rationale,
            })
            fields.append({
                "key": f"question.{question_id}.reason", "label": "Reason",
                "group": f"question.{question_id}", "role": "explanation",
                "kind": "textual", "value": rationale,
            })
        contexts.append({
            "key": f"question.{question_id}",
            "label": str(answer.get("prompt") or question_id),
            "contextType": "question_response",
            "questionType": QUESTION_TYPES[question_id],
            "facets": facets,
        })

    missing = set(QUESTION_TYPES) - seen
    if missing:
        return fail("missing required answers: " + ", ".join(sorted(missing)))
    if len(answers) != len(QUESTION_TYPES):
        return fail(f"expected {len(QUESTION_TYPES)} answers, got {len(answers)}")

    for index, event in enumerate(trajectory):
        if not isinstance(event, dict):
            return fail(f"trajectory[{index}] must be an object")
        absent = EVENT_KEYS - set(event)
        if absent:
            return fail(f"trajectory[{index}] missing keys: {', '.join(sorted(absent))}")
        if not isinstance(event.get("context"), dict) or not isinstance(event.get("outcome"), dict):
            return fail(f"trajectory[{index}] context and outcome must be objects")

    summary_facets = [
        {"key": "answer_count", "label": "Answer count", "role": "score", "kind": "numerical", "value": len(answers)},
        {"key": "trajectory_event_count", "label": "Trajectory event count", "role": "score", "kind": "numerical", "value": len(trajectory)},
    ]
    contexts.append({
        "key": "survey.summary", "label": "Survey summary",
        "contextType": "trial_summary", "facets": summary_facets,
    })
    fields.extend([
        {"key": "survey.summary.answer_count", "label": "Answer count", "group": "survey.summary", "role": "score", "kind": "numerical", "value": len(answers)},
        {"key": "survey.summary.trajectory_event_count", "label": "Trajectory event count", "group": "survey.summary", "role": "score", "kind": "numerical", "value": len(trajectory)},
    ])
    structured = {
        "schemaVersion": "1.0",
        "artifactType": "matraix.trial_evaluation",
        "taskType": "survey",
        "presenceCheck": {"passed": True, "requiredArtifacts": ["survey_result.json"], "missingArtifacts": []},
        "sourceArtifacts": {"surveyResult": "/app/output/survey_result.json"},
        "contexts": contexts,
        "fields": fields,
    }
    (verifier_dir() / "structured_output.json").write_text(
        json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
