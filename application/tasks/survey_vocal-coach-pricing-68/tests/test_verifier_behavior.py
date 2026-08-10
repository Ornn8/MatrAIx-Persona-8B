from __future__ import annotations

import importlib.util
import json
from pathlib import Path

TEST_STATE_PATH = Path(__file__).with_name("test_state.py")
SPEC = importlib.util.spec_from_file_location("pricing_verifier", TEST_STATE_PATH)
assert SPEC and SPEC.loader
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def _payload(price_values: list[str]) -> dict:
    values = [
        "beginner",
        "self",
        "fair",
        "practice_app",
        "start_monthly_68",
        "progress_stalls",
        "monthly_68",
        "core_68",
        "vocal_coach_subscription",
        *price_values,
        "repeated_progress",
        "CNY 68 fits a complete guided system if progress continues.",
    ]
    answers = [
        {"questionId": qid, "value": value}
        for qid, value in zip(VERIFIER.EXPECTED_IDS, values, strict=True)
    ]
    event = {
        "timestamp": "2026-08-10T00:00:00Z",
        "actor": "persona",
        "action": "complete_survey",
        "context": {},
        "outcome": {},
    }
    return {"answers": answers, "trajectory": [event]}


def _run(tmp_path: Path, monkeypatch, price_values: list[str]) -> int:
    output_dir = tmp_path / "output"
    verifier_dir = tmp_path / "verifier"
    output_dir.mkdir()
    result_path = output_dir / "survey_result.json"
    result_path.write_text(
        json.dumps(_payload(price_values), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(VERIFIER, "RESULT_PATH", result_path)
    monkeypatch.setenv("HARBOR_VERIFIER_DIR", str(verifier_dir))
    return VERIFIER.main()


def test_verifier_accepts_complete_ordered_response(tmp_path, monkeypatch) -> None:
    assert _run(
        tmp_path,
        monkeypatch,
        ["cny_19", "cny_49", "cny_88", "cny_168"],
    ) == 0
    structured = json.loads(
        (tmp_path / "verifier" / "structured_output.json").read_text(encoding="utf-8")
    )
    assert structured["presenceCheck"]["passed"] is True
    assert len(structured["contexts"]) == 16


def test_verifier_rejects_unordered_van_westendorp_response(
    tmp_path, monkeypatch
) -> None:
    assert _run(
        tmp_path,
        monkeypatch,
        ["cny_49", "cny_29", "cny_88", "cny_168"],
    ) == 1
