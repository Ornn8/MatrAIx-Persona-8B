from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import tomllib
import yaml


TASK_DIR = Path(__file__).resolve().parents[1]


def _questionnaire() -> dict:
    return yaml.safe_load((TASK_DIR / "input" / "questionnaire.yaml").read_text(encoding="utf-8"))


def test_bundle_schema_and_fixed_quota() -> None:
    task = tomllib.loads((TASK_DIR / "task.toml").read_text(encoding="utf-8"))
    strategy = json.loads((TASK_DIR / "persona_strategy.json").read_text(encoding="utf-8"))
    reporting = json.loads((TASK_DIR / "reporting.json").read_text(encoding="utf-8"))
    questionnaire = _questionnaire()

    assert task["metadata"]["type"] == "survey"
    assert task["environment"]["definition"] == "application/shared-survey-form"
    assert reporting["schemaVersion"] == "1.0"
    assert strategy["defaultMode"] == "stratified"
    assert strategy["stratifyFields"] == ["ind_music"]
    assert strategy["sampleSizePerValueGroup"] == 50
    assert strategy["dimensionFilters"]["ind_music"] == [
        "None",
        "Some exposure",
        "Experienced",
        "Veteran",
    ]
    assert strategy["sampleSizePerValueGroup"] * len(strategy["dimensionFilters"]["ind_music"]) == 200
    assert questionnaire["schemaVersion"] == "1.0"


def test_diary_has_14_days_and_structured_outcomes() -> None:
    questions = _questionnaire()["questions"]
    ids = [question["id"] for question in questions]
    assert len(ids) == len(set(ids)) == 22
    assert [question_id for question_id in ids if question_id.startswith("d")] == [
        f"d{day:02d}_{suffix}"
        for day, suffix in enumerate(
            [
                "activation",
                "reminder",
                "failure_recovery",
                "early_improvement",
                "repetition",
                "busy_day",
                "first_reassessment",
                "subscription",
                "missed_time",
                "plateau",
                "teacher_conflict",
                "safety_pause",
                "private_sharing",
                "second_reassessment",
            ],
            start=1,
        )
    ]
    assert {"q15_practice_days", "q16_final_state", "q17_primary_churn_trigger", "q18_reassessment_behavior", "q19_collaboration_behavior", "q20_next_30_days"} <= set(ids)
    for question in questions:
        assert question.get("required") is True
        if question["type"] == "single_choice":
            option_ids = [option["id"] for option in question["options"]]
            assert option_ids and len(option_ids) == len(set(option_ids))


def test_verifier_accepts_shared_survey_result(tmp_path, monkeypatch) -> None:
    questionnaire = _questionnaire()
    answers = []
    trajectory = []
    for question in questionnaire["questions"]:
        value = question["options"][0]["id"] if question["type"] == "single_choice" else "Concrete simulated behavior summary."
        answers.append({"questionId": question["id"], "prompt": question["prompt"], "value": value})
        trajectory.append(
            {
                "timestamp": "2026-08-10T00:00:00Z",
                "actor": "survey",
                "action": "ask_question",
                "context": {"questionId": question["id"], "questionType": question["type"]},
                "outcome": {"recorded": True},
            }
        )

    output_dir = tmp_path / "output"
    verifier_dir = tmp_path / "verifier"
    output_dir.mkdir()
    (output_dir / "survey_result.json").write_text(
        json.dumps({"answers": answers, "trajectory": trajectory}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HARBOR_VERIFIER_DIR", str(verifier_dir))

    spec = importlib.util.spec_from_file_location("retention_test_state", TASK_DIR / "tests" / "test_state.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RESULT_PATH = output_dir / "survey_result.json"
    assert module.main() == 0
    structured = json.loads((verifier_dir / "structured_output.json").read_text(encoding="utf-8"))
    assert structured["presenceCheck"]["passed"] is True
    assert len([context for context in structured["contexts"] if context["contextType"] == "question_response"]) == 22

