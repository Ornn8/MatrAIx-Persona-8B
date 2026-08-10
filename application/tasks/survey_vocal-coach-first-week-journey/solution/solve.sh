#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python3 <<'PY'
import json
from pathlib import Path

choices = {
    "q0_research_role": "self_taught_hobbyist",
    "q1_current_frequency": "several_weekly",
    "q2_primary_first_week_goal": "identify_priority",
    "q3_stage_profile_setup": "complete_now",
    "q4_stage_priority_result": "continue_immediately",
    "q5_stage_evidence_confidence": "high_confidence_clip",
    "q6_teacher_conflict_decision": "compare_evidence_together",
    "q7_stage_exercise_start": "start_today",
    "q8_practice_frequency": "five_days_10",
    "q9_reminder_preference": "chosen_time_daily",
    "q10_stage_midweek_decision": "continue_as_planned",
    "q11_safety_stop_decision": "stop_rest_monitor",
    "q12_improvement_threshold": "easier_repeatable",
    "q13_stage_day7_clear_improvement": "continue_next_issue",
    "q14_stage_day7_weak_improvement": "recalibrate_new_exercise",
    "q15_postweek_practice_intent": "two_three_weekly",
    "q16_subscription_decision_68": "subscribe_if_next_plan_clear",
    "q17_subscription_blocker": "no_major_blocker",
    "q18_full_curriculum_expectation": "progressive_path",
    "q19_decisive_optimization": "clearer_day7_proof",
}
payload = {
    "participation": "continued",
    "responses": [
        {"question_id": question_id, "choice_id": choice_id}
        for question_id, choice_id in choices.items()
    ],
}
Path("/app/output/survey_responses.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
PY
