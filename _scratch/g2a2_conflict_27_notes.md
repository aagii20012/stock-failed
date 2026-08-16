# G2A2-CONFLICT-27 — measured facts (carry into the decision package verbatim)

All numbers below are measurements from variant 1 `#BASE`
(`SE100-G2-S3-C2-ROTATION-RA1-L03-K1-MONTHLY`), 3276 sessions. Do not re-derive from memory.

## The conflict

Two sealed sentences in `RA2-1.enforcement` cannot both hold.

`part_b.appreciation_drift_worked_example` states that a book sized at the open drifts above the
ceiling by the close with no order placed ("Start gross 50 ... exposure 0.667"), and that this is
precisely why a continuous throttle exists.

`part_c_measurement.purpose` states: "A run whose maximum observed gross fraction exceeds 0.50 by
more than the declared minimum-notional slack is a defect, not a result."

part_c's tolerance names only the min-notional term. Under part_b's own decide-at-close /
fill-at-next-open convention the close-time measurement necessarily also carries one session of
appreciation, which no throttle can pre-empt. So the tolerance is unachievable by construction, and
a literal reading would classify a correct run as defective.

## Measured decomposition of the peak

`max_gross_fraction_observed = 0.5155463571243270334747080073382534` on `2020-11-09`.

    session          gross         equity     gross/equity   excess_usd
    2020-11-06   68.488881     135.038881     0.50717897...     0.969440
    2020-11-09   70.821245     137.371245     0.51554635...     2.135622   <== peak
    2020-11-10   69.894211     138.564211     0.50441748...     0.612106

    carried into the peak session (prior close excess)   0.969440351652308115850
    added by the peak session itself                     1.166182079593357383750
    peak excess                                          2.135622431245665499600

`min_order_notional = 1.00`. The carry (0.969) is a sub-minimum residual, correctly skipped as
MIN_NOTIONAL and carried per `part_b.minimum_notional_skip` / G2A2-CONFLICT-17. The remainder
(1.166) is that session's appreciation. The throttle then acted at the next open: the excess falls
to 0.612 on 11-10.

So the excess is bounded by (one minimum lot carried) + (one session's appreciation) — the
structural limit of the sealed execution convention, not an engine fault.

## Distribution

- closes breaching nominal 0.50: **316 of 3276**
- closes whose excess exceeded one minimum lot: **25**
- closes whose excess exceeded two minimum lots: **1**

## The two counters are different quantities — label them distinctly

- Engine `throttle.sessions_breaching_ceiling` = **1077**. Increments at
  `g2_engine_ra1.py:808` when `projected_gross > exposure_ceiling * _combined_scalar * equity` —
  the **scaled** ceiling `0.50 * f(t) * equity`, on the **projected** book (after STOP/EXIT legs
  merged), on decision sessions only.
- Probe count = **316**. Closes where `gross / equity > 0.50` — the **nominal** ceiling, full
  close-marked book, every session.

`f(t) <= 1` always (combined_scalar min 0.25, mean 0.7533, 2355 of 3276 sessions below 1), so the
scaled ceiling is tighter and 1077 >= 316 is what the definitions predict. These are not in
conflict; reporting either as "the" breach count would be wrong.

## Why this does not affect the verdict

`max_gross_fraction_observed` is listed in the seal under
`reported_for_every_variant_but_not_gating`. It is a disclosure item. Verify that membership again
at report time rather than trusting this line.

## Resolution adopted

Report the measurement as declared. Do **not** treat it as an engine defect: the hard order-time
assertion `_assert_ceilings_hold` (`g2_engine_ra1.py:947-996`, priced at the open against
`0.50 * f * equity`) held on every fill across the run, and it raises rather than continuing.
Disclose the decomposition with the measured numbers above. Never edit part_c.
