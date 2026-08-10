# AI Vocal Coach - Safety Red Team

Independent MatrAIx safety-policy study covering pain, persistent hoarseness,
fatigue, extreme high notes, harmful imitation, and minors/recording privacy. It
tests risk reduction, likely compliance, interruption burden, effective safety
copy, and mandatory human escalation. It does not test medical or model
accuracy.

## Fixed 200-person study

The task uses `matraix-persona-1m` and takes 50 personas from each level of the
`ind_music` dimension:

| Research quota | Persona proxy | Runs |
| --- | --- | ---: |
| Beginner / little formal exposure | `ind_music=None` | 50 |
| Broad hobbyist / some exposure | `ind_music=Some exposure` | 50 |
| Experienced singer or music-adjacent professional | `ind_music=Experienced` | 50 |
| Veteran professional, teacher, coach, or senior practitioner | `ind_music=Veteran` | 50 |
| **Total** |  | **200** |

The same validated persona strategy as the concept-feedback task is used, so
the first two strata remain the beginner/hobbyist half. The sampled personas are
adults, but all respondents evaluate a hypothetical minor/privacy scenario.

## Instrument and interpretation

The 15 questions include six concrete vignettes plus compliance, message-copy,
over-interruption, escalation, risk-reduction, and false-positive trade-off
items. Reporting scans rationales for compliance, bypass intent, proportionality,
human escalation, non-diagnostic language, and minor privacy concerns.

Compare every result by `ind_music` stratum. Simulated responses are directional
hypotheses for later usability tests with real singers, teachers, clinicians,
parents, and minors; they are not clinical validation or population estimates.
