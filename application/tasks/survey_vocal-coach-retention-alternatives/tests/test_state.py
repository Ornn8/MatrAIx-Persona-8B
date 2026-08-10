from __future__ import annotations

import json
import os
import sys
from pathlib import Path

OUTPUT_DIR = Path(os.environ.get("HARBOR_OUTPUT_DIR") or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")
RESULT_PATH = OUTPUT_DIR / "survey_result.json"
EVENT_KEYS = {"timestamp", "actor", "action", "context", "outcome"}


def verifier_dir() -> Path:
    explicit = os.environ.get("HARBOR_VERIFIER_DIR")
    path = Path(explicit) if explicit else Path("/logs/verifier")
    path.mkdir(parents=True, exist_ok=True)
    return path


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def question_types(trajectory: list[object]) -> dict[str, str]:
    result: dict[str, str] = {}
    for event in trajectory:
        if not isinstance(event, dict) or event.get("action") != "ask_question":
            continue
        context = event.get("context")
        if isinstance(context, dict):
            question_id = str(context.get("questionId") or "").strip()
            question_type = str(context.get("questionType") or "").strip().lower()
            if question_id and question_type:
                result[question_id] = question_type
    return result


def field_kind(question_type: str, value: object) -> str:
    if question_type == "likert":
        return "numerical"
    if question_type in {"single_choice", "multi_choice"}:
        return "categorical"
    if question_type == "free_text":
        return "textual"
    return "numerical" if isinstance(value, (int, float)) and not isinstance(value, bool) else "textual"


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
    if not isinstance(answers, list) or not answers:
        return fail("survey_result.answers must be a non-empty list")
    if not isinstance(trajectory, list) or not trajectory:
        return fail("survey_result.trajectory must be a non-empty list")

    types = question_types(trajectory)
    contexts: list[dict[str, object]] = []
    fields: list[dict[str, object]] = []
    for index, answer in enumerate(answers):
        if not isinstance(answer, dict):
            return fail(f"answers[{index}] must be an object")
        question_id = str(answer.get("questionId") or "").strip()
        if not question_id or "value" not in answer:
            return fail(f"answers[{index}] requires questionId and value")
        value = answer["value"]
        qtype = types.get(question_id, "")
        kind = field_kind(qtype, value)
        key = f"question.{question_id}"
        facets: list[dict[str, object]] = [{"key": "response", "label": "Selected response", "role": "primary", "kind": kind, "value": value}]
        fields.append({"key": f"{key}.response", "label": "Selected response", "group": key, "role": "primary", "kind": kind, "value": value})
        rationale = str(answer.get("rationale") or "").strip()
        if rationale:
            facets.append({"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": rationale})
            fields.append({"key": f"{key}.reason", "label": "Reason", "group": key, "role": "explanation", "kind": "textual", "value": rationale})
        contexts.append({"key": key, "label": str(answer.get("prompt") or question_id), "contextType": "question_response", "questionType": qtype, "facets": facets})

    for index, event in enumerate(trajectory):
        if not isinstance(event, dict):
            return fail(f"trajectory[{index}] must be an object")
        missing = EVENT_KEYS - set(event)
        if missing:
            return fail(f"trajectory[{index}] missing keys: {', '.join(sorted(missing))}")
        if not isinstance(event.get("context"), dict) or not isinstance(event.get("outcome"), dict):
            return fail(f"trajectory[{index}] context and outcome must be objects")

    summary_facets = [
        {"key": "answer_count", "label": "Answer count", "role": "score", "kind": "numerical", "value": len(answers)},
        {"key": "trajectory_event_count", "label": "Trajectory event count", "role": "score", "kind": "numerical", "value": len(trajectory)},
    ]
    contexts.append({"key": "survey.summary", "label": "Survey summary", "contextType": "trial_summary", "facets": summary_facets})
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
    (verifier_dir() / "structured_output.json").write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

