# AI Vocal Coach - First-Week Journey

This independent MatrAIx survey tests the first-use and free-first-week funnel
for a complete AI vocal-learning system. It follows voice-profile setup,
priority diagnosis, source evidence and confidence, matched practice, midweek
retention, safety stops, day-7 improvement, continued practice, and a CNY 68
monthly subscription decision. It does not test model accuracy or claim that
every user will improve in seven days.

## Default 200-persona study

The task samples `matraix-persona-1m` with exactly 50 personas from each
`ind_music` level:

| Research layer | Persona proxy | Runs |
| --- | --- | ---: |
| Beginner / little formal exposure | `ind_music=None` | 50 |
| KTV, casual, or self-taught hobbyist | `ind_music=Some exposure` | 50 |
| Experienced learner, creator, performer, or adjacent professional | `ind_music=Experienced` | 50 |
| Veteran performer, teacher, coach, or institutional user | `ind_music=Veteran` | 50 |
| **Total** |  | **200** |

The first two layers are 100 of 200 respondents. The proxies set the research
scenario but do not force favourable answers. Adult age, music interest, trust,
and economic posture remain diverse.

## Funnel interpretation

The 20 questions record baseline role and practice, then explicit stage
decisions. Critical options encode continuation, delay, or exit together with
the primary reason so aggregate response bars can be read as a funnel. Because
the shared survey form is non-branching, respondents who hypothetically leave
still answer later-stage counterfactual questions; do not count those later
answers as observed retention. Build the strict funnel sequentially from:

1. `q3_stage_profile_setup`
2. `q4_stage_priority_result`
3. `q5_stage_evidence_confidence`
4. `q7_stage_exercise_start`
5. `q10_stage_midweek_decision`
6. `q13_stage_day7_clear_improvement`
7. `q15_postweek_practice_intent`
8. `q16_subscription_decision_68`

Use `q12_improvement_threshold` to segment the day-7 success definition and
`q14_stage_day7_weak_improvement` as the failure-recovery path. Compare every
stage by `ind_music`, `q0_research_role`, baseline frequency, trust, and
economic motivation. Simulated responses are directional hypotheses for later
validation with real singers, teachers, and longitudinal product telemetry.
