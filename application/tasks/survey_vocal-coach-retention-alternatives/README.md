# AI Vocal Coach - Two-week Retention Alternatives

This is a non-questionnaire-style product behavior simulation implemented with
the survey task schema. Each persona moves through a stateful 14-day diary and
selects a concrete action after activation, reminders, failure, visible
improvement, repeated content, a busy day, reassessment, the CNY 68 paywall, a
plateau, teacher disagreement, a safety stop, private sharing, and a final
reassessment.

## Fixed 200-person cohort

`persona_strategy.json` draws 50 personas from each `ind_music` stratum in the
1M pool:

| Layer | Persona proxy | Runs |
| --- | --- | ---: |
| 1 | `None` — beginner | 50 |
| 2 | `Some exposure` — KTV, casual, or self-taught hobbyist | 50 |
| 3 | `Experienced` — advanced student, creator, or performer | 50 |
| 4 | `Veteran` — senior performer, teacher, coach, or institution user | 50 |
| **Total** |  | **200** |

The first two layers are exactly half of the study. They are sampling proxies,
not predetermined responses.

## Structured retention proxies

Aggregate the categorical option ids directly. Primary endpoint definitions:

- **Activated:** `d01_activation` is `complete_assessment_and_exercise`,
  `complete_assessment_only`, or `shortened_sample_then_exercise`.
- **D7 retained:** `d07_first_reassessment` is any active choice other than
  `stop_despite_improvement` or `inactive_after_stop`.
- **D7 retested:** Day 7 choice starts with `complete_retest`.
- **Paid conversion:** `d08_subscription` is `subscribe_now`,
  `review_results_then_subscribe`, or `ask_teacher_then_subscribe`.
- **D14 retained paid:** `q16_final_state` is `retained_paid_active` or
  `retained_paid_safety_pause`.
- **D14 retested:** Day 14 choice starts with `complete_retest`.
- **Safe pause:** Day 12 is `stop_training_follow_guidance`,
  `contact_human_before_return`, or `keep_account_safety_pause`; do not count
  these as churn unless a later choice explicitly cancels.
- **Practice adherence:** use `q15_practice_days`; audit it against daily choices.
- **Churn trigger:** distribution of `q17_primary_churn_trigger`, split by actual
  final state so near-churn and realized churn are not conflated.
- **Sharing/teacher collaboration:** use `q19_collaboration_behavior` and audit
  against Days 7, 11, 13, and 14.
- **Forward retention:** use `q20_next_30_days`.

Report all endpoints overall and by `ind_music` stratum. Also publish transition
rates for activation -> D7 retained -> paid conversion -> D14 retained. Treat
the results as directional behavioral hypotheses from simulated personas, not
real retention, efficacy, conversion, or market-size estimates.

