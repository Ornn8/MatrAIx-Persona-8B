#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python3 <<'PY'
import json
from pathlib import Path

payload = {
    "participation": "continued",
    "responses": [
        {"question_id": "q0_singing_frequency", "choice_id": "weekly"},
        {"question_id": "q1_primary_role", "choice_id": "learner"},
        {"question_id": "q2_current_pain", "choice_id": "no_practice_plan"},
        {"question_id": "q3_concept_value", "value": 4},
        {"question_id": "q4_first_value", "choice_id": "diagnosis"},
        {"question_id": "q5_trust_evidence", "choice_id": "trust_some"},
        {"question_id": "q6_teacher_relationship", "choice_id": "complement_teacher"},
        {"question_id": "q7_adoption_blocker", "choice_id": "wrong_feedback"},
        {"question_id": "q8_privacy_consent", "choice_id": "consent_conditional"},
        {"question_id": "q9_feedback_scope", "choice_id": "one_focus"},
        {"question_id": "q10_try_intent", "choice_id": "try_if_free"},
        {"question_id": "q11_payment_model", "choice_id": "free_core"},
        {"question_id": "q12_success_signal", "choice_id": "better_sound"},
        {"question_id": "q13_open_reaction", "text": "I would try it if the first diagnosis were private and easy to understand."},
        {"question_id": "q14_open_safety", "text": "It must never push me toward painful or unsafe singing just to reach a higher note."},
    ],
}

Path("/app/output/survey_responses.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
