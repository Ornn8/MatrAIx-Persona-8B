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
EVENT_KEYS = {"timestamp", "actor", "action", "context", "outcome"}


def _verifier_dir() -> Path:
    explicit = os.environ.get("HARBOR_VERIFIER_DIR")
    if explicit:
        path = Path(explicit)
        path.mkdir(parents=True, exist_ok=True)
        return path
    path = Path("/logs/verifier")
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError as exc:
        raise RuntimeError(
            "HARBOR_VERIFIER_DIR is required outside a Harbor trial container"
        ) from exc


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _question_types(trajectory: list[object]) -> dict[str, str]:
    result: dict[str, str] = {}
    for event in trajectory:
        if not isinstance(event, dict) or event.get("action") != "ask_question":
            continue
        context = event.get("context")
        if not isinstance(context, dict):
            continue
        question_id = str(context.get("questionId") or "").strip()
        question_type = str(context.get("questionType") or "").strip().lower()
        if question_id and question_type:
            result[question_id] = question_type
    return result


def _kind(question_type: str | None, value: object) -> str:
    if question_type == "likert":
        return "numerical"
    if question_type in {"single_choice", "multi_choice"}:
        return "categorical"
    if question_type == "free_text":
        return "textual"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "numerical"
    if isinstance(value, (bool, list)):
        return "categorical"
    return "textual"


def main() -> int:
    if not RESULT_PATH.is_file():
        return fail("missing /app/output/survey_result.json")
    try:
        payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail("survey_result.json is not valid JSON: {}".format(exc))
    if not isinstance(payload, dict):
        return fail("survey_result.json must contain an object")
    answers = payload.get("answers")
    trajectory = payload.get("trajectory")
    if not isinstance(answers, list) or not answers:
        return fail("survey_result.answers must be a non-empty list")
    if not isinstance(trajectory, list) or not trajectory:
        return fail("survey_result.trajectory must be a non-empty list")

    for index, event in enumerate(trajectory):
        if not isinstance(event, dict):
            return fail("trajectory[{}] must be an object".format(index))
        missing = EVENT_KEYS - set(event)
        if missing:
            return fail(
                "trajectory[{}] missing keys: {}".format(
                    index, ", ".join(sorted(missing))
                )
            )
        if not isinstance(event.get("context"), dict):
            return fail("trajectory[{}].context must be an object".format(index))
        if not isinstance(event.get("outcome"), dict):
            return fail("trajectory[{}].outcome must be an object".format(index))

    question_types = _question_types(trajectory)
    contexts: list[dict[str, object]] = []
    fields: list[dict[str, object]] = []
    numeric_values: list[float] = []
    for index, answer in enumerate(answers):
        if not isinstance(answer, dict):
            return fail("answers[{}] must be an object".format(index))
        question_id = str(answer.get("questionId") or "").strip()
        if not question_id or "value" not in answer:
            return fail("answers[{}] requires questionId and value".format(index))
        value = answer["value"]
        question_type = question_types.get(question_id)
        kind = _kind(question_type, value)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            numeric_values.append(float(value))
        context_key = "question.{}".format(question_id)
        facets: list[dict[str, object]] = [
            {
                "key": "response",
                "label": "Selected response",
                "role": "primary",
                "kind": kind,
                "value": value,
            }
        ]
        fields.append(
            {
                "key": "{}.response".format(context_key),
                "label": "Selected response",
                "group": context_key,
                "role": "primary",
                "kind": kind,
                "value": value,
            }
        )
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
            fields.append(
                {
                    "key": "{}.reason".format(context_key),
                    "label": "Reason",
                    "group": context_key,
                    "role": "explanation",
                    "kind": "textual",
                    "value": rationale,
                }
            )
        context: dict[str, object] = {
            "key": context_key,
            "label": str(answer.get("prompt") or question_id),
            "contextType": "question_response",
            "facets": facets,
        }
        if question_type:
            context["questionType"] = question_type
        contexts.append(context)

    summary_facets: list[dict[str, object]] = [
        {
            "key": "answer_count",
            "label": "Answer count",
            "role": "score",
            "kind": "numerical",
            "value": len(answers),
        },
        {
            "key": "trajectory_event_count",
            "label": "Trajectory event count",
            "role": "score",
            "kind": "numerical",
            "value": len(trajectory),
        },
    ]
    if numeric_values:
        summary_facets.append(
            {
                "key": "mean_numeric_answer",
                "label": "Mean numeric answer",
                "role": "score",
                "kind": "numerical",
                "value": round(sum(numeric_values) / len(numeric_values), 4),
            }
        )
    contexts.append(
        {
            "key": "survey.summary",
            "label": "Survey summary",
            "contextType": "trial_summary",
            "facets": summary_facets,
        }
    )
    verifier_dir = _verifier_dir()
    (verifier_dir / "structured_output.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "artifactType": "matraix.trial_evaluation",
                "taskType": "survey",
                "presenceCheck": {
                    "passed": True,
                    "requiredArtifacts": ["survey_result.json"],
                    "missingArtifacts": [],
                },
                "sourceArtifacts": {
                    "surveyResult": "/app/output/survey_result.json"
                },
                "contexts": contexts,
                "fields": fields,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
