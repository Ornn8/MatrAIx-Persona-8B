# AI Vocal Coach - Product Concept Feedback

This MatrAIx survey tests an unbuilt AI vocal-training platform concept. It
measures demand, evidence-based diagnostic trust, privacy acceptance, realistic
trial intent, payment preference, and role-specific proof of value. It does not
test model accuracy.

## Default 200-run study

The task uses `matraix-persona-1m` and takes 50 personas from each level of the
`ind_music` dimension:

| Research quota | Persona proxy | Runs |
| --- | --- | ---: |
| Beginner / little formal exposure | `ind_music=None` | 50 |
| Broad hobbyist / some exposure | `ind_music=Some exposure` | 50 |
| Experienced singer or music-adjacent professional | `ind_music=Experienced` | 50 |
| Veteran professional, teacher, coach, or senior practitioner | `ind_music=Veteran` | 50 |
| **Total** |  | **200** |

The first two rows form the required beginner-plus-broad-hobbyist half: 100 of
200 runs. These are sampling proxies, not assumed answers. Question
`q0_research_role` records the respondent's actual consumer or professional role
for analysis. All sampled personas are adults who are passionate about or
interested in music; trust and spending postures remain diverse.

## Questionnaire and analysis

The 12 questions separate role, activity, unmet need, concept value, first-use
value, evidence-based trust, blockers, privacy, trial intent, payment, proof of
value, and an open trust boundary. Consumer and professional paths share one
instrument but have explicit role and role-specific response options.

Critical value, trust, trial, and payment questions request short rationales.
`reporting.json` groups these reasons by response and scans for evidence trust,
human-validation needs, privacy blockers, credible trial intent, and credible
payment intent.

Before interpreting market demand, compare results by `q0_research_role` and by
the `ind_music` strata. Treat simulated responses as directional hypotheses for
later validation with real singers and teachers, not as market-size estimates.
