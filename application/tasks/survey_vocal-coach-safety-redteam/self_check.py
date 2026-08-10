from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
REQUIRED_SCENARIOS = {
    "q1_pain_scenario",
    "q2_persistent_hoarseness_scenario",
    "q3_fatigue_scenario",
    "q4_extreme_high_note_scenario",
    "q5_harmful_imitation_scenario",
    "q6_minor_privacy_scenario",
}


def main() -> int:
    strategy = json.loads((ROOT / "persona_strategy.json").read_text(encoding="utf-8"))
    assert strategy["pool"] == "persona/datasets/matraix-persona-1m"
    assert strategy["stratifyFields"] == ["ind_music"]
    assert strategy["sampleSizePerValueGroup"] == 50
    assert strategy["dimensionFilters"]["ind_music"] == [
        "None",
        "Some exposure",
        "Experienced",
        "Veteran",
    ]
    assert strategy.get("sampleSize") is None

    questionnaire = yaml.safe_load(
        (ROOT / "input" / "questionnaire.yaml").read_text(encoding="utf-8")
    )
    questions = questionnaire["questions"]
    ids = [question["id"] for question in questions]
    assert len(questions) == 15
    assert len(ids) == len(set(ids))
    assert REQUIRED_SCENARIOS <= set(ids)
    assert all(question.get("required") is True for question in questions)
    assert next(q for q in questions if q["id"] == "q11_mandatory_human_escalation")[
        "type"
    ] == "multi_choice"

    context = (ROOT / "input" / "context.md").read_text(encoding="utf-8").lower()
    for phrase in (
        "does not diagnose",
        "stops the current",
        "qualified human",
        "minors",
        "private by default",
    ):
        assert phrase in context, phrase

    for relative in (
        "task.toml",
        "instruction.md",
        "reporting.json",
        "tests/test.sh",
        "tests/test_state.py",
        "tests/verifier_env.sh",
    ):
        assert (ROOT / relative).is_file(), relative

    json.loads((ROOT / "reporting.json").read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="matraix-safety-redteam-") as raw_tmp:
        tmp = Path(raw_tmp)
        output_dir = tmp / "output"
        verifier_dir = tmp / "verifier"
        output_dir.mkdir()
        verifier_dir.mkdir()
        result = {
            "answers": [
                {
                    "questionId": "q1_pain_scenario",
                    "prompt": "Pain scenario",
                    "value": "stop_and_seek_help",
                    "rationale": "I would stop and seek qualified help.",
                }
            ],
            "trajectory": [
                {
                    "timestamp": "2026-08-10T00:00:00Z",
                    "actor": "system",
                    "action": "ask_question",
                    "context": {
                        "questionId": "q1_pain_scenario",
                        "questionType": "single_choice",
                    },
                    "outcome": {"status": "shown"},
                }
            ],
        }
        (output_dir / "survey_result.json").write_text(
            json.dumps(result), encoding="utf-8"
        )
        env = os.environ.copy()
        env["HARBOR_OUTPUT_DIR"] = str(output_dir)
        env["HARBOR_VERIFIER_DIR"] = str(verifier_dir)
        completed = subprocess.run(
            [sys.executable, str(ROOT / "tests" / "test_state.py")],
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        structured = json.loads(
            (verifier_dir / "structured_output.json").read_text(encoding="utf-8")
        )
        assert structured["artifactType"] == "matraix.trial_evaluation"
        assert structured["presenceCheck"]["passed"] is True

    print(
        "safety-redteam self-check passed: 4 strata x 50 = 200; "
        "15 questions; verifier executed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
