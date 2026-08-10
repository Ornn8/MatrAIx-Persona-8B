# AI Vocal Coach - CNY 68 Pricing and Packaging

This independent MatrAIx task tests the proposed CNY 68 monthly package after a
complete seven-day free trial. It triangulates price perception, conditioned
conversion, cancellation, payment cadence, package trade-offs, share of wallet,
payer role, and four Van Westendorp thresholds.

## Default 200-person run

The strategy samples exactly 50 personas from each `ind_music` level in the 1M
pool: `None`, `Some exposure`, `Experienced`, and `Veteran`. The first two
strata provide 100 beginner/broad-hobbyist proxies; the latter two provide 100
experienced/veteran proxies. Role and likely payer are measured separately.

## Instrument map

The instrument has 15 required questions:

- Role and payer: q0-q1.
- CNY 68 perception, comparison anchor, improvement-conditioned conversion,
  and cancellation: q2-q5.
- Monthly/quarterly/pay-per-use and 39/68/98 package choices: q6-q7.
- Share-of-wallet forced choice: q8.
- Van Westendorp thresholds on fixed CNY points: q9-q12.
- Retention proof and open pricing explanation: q13-q14.

For Van Westendorp analysis, map `cny_N` to N and reject or separately flag any
response where q9 >= q10, q10 >= q11, or q11 >= q12. Report CNY 68 conversion
by `ind_music`, q0 role, q1 payer, and economic motivation. Simulated responses
are directional product hypotheses, not market conversion forecasts.
