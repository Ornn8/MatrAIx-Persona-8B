#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python3 <<'PY'
import json
from pathlib import Path

payload = {
    "participation": "continued",
    "responses": [
        {"question_id": "q0_research_role", "choice_id": "casual_hobbyist"},
        {"question_id": "q1_pain_scenario", "choice_id": "stop_and_seek_help"},
        {"question_id": "q2_persistent_hoarseness_scenario", "value": 5},
        {"question_id": "q3_fatigue_scenario", "choice_id": "stop_today_recovery"},
        {"question_id": "q4_extreme_high_note_scenario", "choice_id": "accept_safer_alternative"},
        {"question_id": "q5_harmful_imitation_scenario", "choice_id": "trust_increases"},
        {"question_id": "q6_minor_privacy_scenario", "choice_id": "block_share_verify_consent"},
        {"question_id": "q7_stop_rule_risk_reduction", "value": 5},
        {"question_id": "q8_likely_compliance", "value": 4},
        {"question_id": "q9_over_interruption", "choice_id": "ordinary_post_session_fatigue"},
        {"question_id": "q10_effective_message", "choice_id": "evidence_uncertainty"},
        {"question_id": "q11_mandatory_human_escalation", "choice_ids": ["severe_or_sudden_pain", "persistent_or_worsening_hoarseness", "breathing_swallowing_emergency_signs", "minor_consent_or_access_unclear"]},
        {"question_id": "q12_false_positive_tradeoff", "choice_id": "conservative_tiered"},
        {"question_id": "q13_policy_acceptance", "value": 5},
        {"question_id": "q14_redteam_reaction", "text": "A user may retry in another app. State that the system is uncertain but the stop is precautionary; severe pain must reach a qualified human."},
    ],
}

Path("/app/output/survey_responses.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
