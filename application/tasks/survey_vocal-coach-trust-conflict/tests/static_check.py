from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


TASK_DIR = Path(__file__).resolve().parents[1]
EXPECTED_FILES = {
    "task.toml",
    "persona_strategy.json",
    "instruction.md",
    "reporting.json",
    "README.md",
    "input/context.md",
    "input/questionnaire.yaml",
    "tests/test.sh",
    "tests/verifier_env.sh",
    "tests/test_state.py",
}
EXPECTED_STRATA = ["None", "Some exposure", "Experienced", "Veteran"]
EXPECTED_QUESTION_IDS = [f"q{i}_{suffix}" for i, suffix in enumerate([
    "research_role",
    "decision_context",
    "baseline_trust",
    "evidence_ab",
    "high_confidence_behavior",
    "low_confidence_ab",
    "low_confidence_behavior",
    "user_disagreement_ab",
    "user_disagreement_behavior",
    "teacher_conflict_ab",
    "teacher_override_effect",
    "professional_control",
    "known_error_repair_ab",
    "post_error_behavior",
    "accuracy_claim_ab",
    "adoption_boundary",
    "professional_acceptance",
    "final_trust",
    "decisive_boundary",
])]
REQUIRED_CONSTRUCTS = {
    "evidence_format_behavior",
    "uncertainty_calibration_preference",
    "low_confidence_next_action",
    "user_disagreement_handling",
    "teacher_conflict_behavior",
    "teacher_override_adoption_effect",
    "known_error_repair_preference",
    "post_error_retention_behavior",
    "accuracy_claim_acceptance",
    "autonomous_adoption_boundary",
    "professional_workflow_acceptance",
}
REQUIRED_SIGNAL_KEYS = {
    "source_evidence_required",
    "uncertainty_admission_builds_trust",
    "user_dispute_control_required",
    "human_confirmation_boundary",
    "teacher_authority_required",
    "error_repair_can_restore_trust",
    "professional_workflow_acceptable",
}


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    for relative in sorted(EXPECTED_FILES):
        check((TASK_DIR / relative).is_file(), f"missing {relative}", errors)

    task_toml = (TASK_DIR / "task.toml").read_text(encoding="utf-8")
    check(
        'name = "application/vocal-coach-trust-conflict"' in task_toml,
        "task.toml has the wrong independent task name",
        errors,
    )

    strategy = json.loads((TASK_DIR / "persona_strategy.json").read_text(encoding="utf-8"))
    check(strategy.get("pool") == "persona/datasets/matraix-persona-1m", "wrong persona pool", errors)
    check(strategy.get("defaultMode") == "stratified", "defaultMode must be stratified", errors)
    check(strategy.get("stratifyFields") == ["ind_music"], "must stratify only by ind_music", errors)
    check(
        strategy.get("dimensionFilters", {}).get("ind_music") == EXPECTED_STRATA,
        "ind_music strata or order is wrong",
        errors,
    )
    per_group = strategy.get("sampleSizePerValueGroup")
    check(per_group == 50, "sampleSizePerValueGroup must be 50", errors)
    check(per_group * len(EXPECTED_STRATA) == 200, "four strata must total 200", errors)
    check("sampleSize" not in strategy, "do not use mixed-pool sampleSize", errors)

    questionnaire = yaml.safe_load((TASK_DIR / "input/questionnaire.yaml").read_text(encoding="utf-8"))
    questions = questionnaire.get("questions", [])
    ids = [question.get("id") for question in questions]
    check(questionnaire.get("id") == "vocal_coach_trust_conflict_v1", "wrong questionnaire id", errors)
    check(ids == EXPECTED_QUESTION_IDS, "question ids/order must match the 19-question design", errors)
    check(len(ids) == len(set(ids)) == 19, "question ids must be 19 and unique", errors)
    constructs = {question.get("construct") for question in questions}
    check(REQUIRED_CONSTRUCTS <= constructs, "one or more trust/conflict constructs are missing", errors)
    check(all(question.get("required") is True for question in questions), "all questions must be required", errors)
    ab_questions = [question for question in questions if "A/B" in str(question.get("prompt", ""))]
    check(len(ab_questions) >= 6, "expected at least six concrete A/B scenarios", errors)
    for question in questions:
        qtype = question.get("type")
        check(qtype in {"single_choice", "likert", "free_text"}, f"unsupported type in {question.get('id')}", errors)
        if qtype == "single_choice":
            options = question.get("options") or []
            option_ids = [option.get("id") for option in options]
            check(len(option_ids) >= 2, f"{question.get('id')} needs options", errors)
            check(len(option_ids) == len(set(option_ids)), f"duplicate option id in {question.get('id')}", errors)
        if qtype == "likert":
            check(question.get("minValue") == 1 and question.get("maxValue") == 5, f"{question.get('id')} must be 1-5", errors)

    reporting = json.loads((TASK_DIR / "reporting.json").read_text(encoding="utf-8"))
    signals = reporting["contextRules"][0]["signalScans"][0]["signals"]
    signal_keys = {signal.get("key") for signal in signals}
    check(signal_keys == REQUIRED_SIGNAL_KEYS, "reporting signal keys do not match the study", errors)

    combined_text = "\n".join(
        (TASK_DIR / relative).read_text(encoding="utf-8")
        for relative in EXPECTED_FILES
        if relative.endswith((".md", ".json", ".yaml", ".toml"))
    )
    check("vocal-coach-concept-feedback" not in combined_text, "new task references the old task id", errors)
    for relative in ("tests/test.sh", "tests/verifier_env.sh"):
        raw = (TASK_DIR / relative).read_bytes()
        check(b"\r\n" not in raw, f"{relative} must use LF line endings", errors)

    if errors:
        print("STATIC CHECK FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("STATIC CHECK PASSED")
    print("- independent task: application/vocal-coach-trust-conflict")
    print("- questionnaire: 19 required questions, 6 A/B scenarios")
    print("- persona quota: 4 x 50 = 200")
    print("- reporting signals: 7")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

