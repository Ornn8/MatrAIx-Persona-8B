from __future__ import annotations

import json
import tomllib
from pathlib import Path

import yaml

TASK_DIR = Path(__file__).resolve().parents[1]
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
PRICE_IDS = [
    "cny_9",
    "cny_19",
    "cny_29",
    "cny_39",
    "cny_49",
    "cny_68",
    "cny_88",
    "cny_108",
    "cny_138",
    "cny_168",
    "cny_198",
    "cny_268",
]


def test_task_definition_is_parseable_and_complete() -> None:
    questionnaire = yaml.safe_load(
        (TASK_DIR / "input" / "questionnaire.yaml").read_text(encoding="utf-8")
    )
    questions = questionnaire["questions"]
    assert questionnaire["id"] == "vocal_coach_pricing_68_v1"
    assert [question["id"] for question in questions] == EXPECTED_IDS
    assert all(question["required"] is True for question in questions)
    for question in questions:
        for option in question.get("options", []):
            assert set(option) == {"id", "label"}, (question["id"], option)
    for question in questions[9:13]:
        assert [option["id"] for option in question["options"]] == PRICE_IDS

    strategy = json.loads(
        (TASK_DIR / "persona_strategy.json").read_text(encoding="utf-8")
    )
    assert strategy["pool"] == "persona/datasets/matraix-persona-1m"
    assert strategy["stratifyFields"] == ["ind_music"]
    assert strategy["dimensionFilters"]["ind_music"] == [
        "None",
        "Some exposure",
        "Experienced",
        "Veteran",
    ]
    assert strategy["sampleSizePerValueGroup"] == 50

    reporting = json.loads((TASK_DIR / "reporting.json").read_text(encoding="utf-8"))
    assert reporting["schemaVersion"] == "1.0"
    task_toml = tomllib.loads((TASK_DIR / "task.toml").read_text(encoding="utf-8"))
    assert task_toml["task"]["name"] == "application/vocal-coach-pricing-68"
    assert task_toml["environment"]["definition"] == "application/shared-survey-form"


def test_playground_discovers_task_and_questionnaire() -> None:
    from backend.service.persona_strategy import validate_persona_strategy_file
    from backend.service.task_detail_service import get_task_detail

    repo_root = TASK_DIR.parents[2]
    detail = get_task_detail(
        "application/tasks/survey_vocal-coach-pricing-68",
        repo_root=repo_root,
    )
    assert detail["questionnaire"]["id"] == "vocal_coach_pricing_68_v1"
    assert len(detail["questionnaire"]["questions"]) == 15
    assert validate_persona_strategy_file(TASK_DIR) == []
