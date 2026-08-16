# Stage 3 (Generation 2, Attempt 2) — cross-sectional rotation under risk architecture RA2

| Field | Value |
|---|---|
| Document id | `SE100-GOV-2005` |
| Status | `SEALED` |
| Project | StockEdge100 |
| Generation | 2 |
| Generation id | `SE100-GEN2-7394207c543401e2` |
| Stage | 3 |
| Gate | 3 — development admissibility |
| Attempt | 2 |
| Authored (UTC) | 2026-08-15T09:25:58Z |
| Charter | [STAGE_10_GENERATION_2_CHARTER.md](STAGE_10_GENERATION_2_CHARTER.md) (`SE100-GOV-2001`) |
| Partition lock | [STAGE_1_G2_PARTITION_LOCK.md](STAGE_1_G2_PARTITION_LOCK.md) (`SE100-GOV-2002`) |
| Attempt 1 protocol | [STAGE_3_G2_ROTATION_PROTOCOL.md](STAGE_3_G2_ROTATION_PROTOCOL.md) (`SE100-GOV-2003`) — closed, read-only |
| Constitution | `SE100-GOV-0001` §§3, 4, 5.1, 6.1, 9 gate 3, 11 |
| Machine companion | `STAGE_3_G2_ROTATION_RA1_PROTOCOL.json`, sealed by `STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256` |
| Source of record | `config/generation_2/g2_rotation_ra1_protocol.json` (`SE100-CFG-3103`) |
| Gate criteria | `config/generation_2/g2_gate_criteria_ra1.json` (`SE100-CFG-3104`) |
| `live_trading_authorized` | `false` |

This document pre-registers a second candidate strategy and its parameter grid **before any Attempt 2
strategy, engine, gate or runner module exists**. Section 13 records the measurement that establishes
that claim.

It cannot make, and does not make, the claim Attempt 1's protocol made. Attempt 1 was written against
a development window no one had looked at for this hypothesis. This one is not. Section 14 carries the
disclosure that governs every use of this attempt's result, verbatim and unabridged.

---

## 1. What is pre-registered

| Field | Value |
|---|---|
| Strategy id | `SE100-G2-S3-C2-ROTATION-RA1` |
| Candidate index | C2 |
| Family | `CROSS_SECTIONAL_RELATIVE_STRENGTH_RISK_ARCHITECTURE` |
| Candidate count | 1 |
| Grid size | 18 variants |
| Runs | 2 per variant (`#BASE`, `#STRESS`) — 36 total |
| Risk architecture | `RA2`, five components, frozen, not gridded |

**Hypothesis.** Cross-sectional relative strength over a fixed 34-member ETF universe, held in an
equally weighted top-k basket and refreshed on a fixed calendar, produces a positive net return over
the Generation 2 development window while remaining inside the constitutional research-shutdown
ceiling, **when** exposure is capped at half of equity, scaled down by realized portfolio volatility,
staged down further as the equity drawdown deepens, and cut at the position level by a fixed stop.

**Why the candidate index is C2 and not C1.** Attempt 2 is a distinct candidate specification, not a
re-run of Attempt 1's candidate: it exits positions between scheduled rebalances, sizes them against
a scaled ceiling, and targets a different gross exposure. Constitution §9 makes a gate conjunctive
*within a candidate*, so reusing `C1` would attach Attempt 1's already-recorded `FAIL` to the same
candidate id and make two candidates evaluated once each look like one candidate evaluated twice.

**What this attempt adds over Attempt 1, and nothing else.** Attempt 1 tested the rotation signal with
no mechanism to reduce exposure before a research-shutdown breach: between scheduled rebalances it
issued no orders at all. Attempt 2 holds the signal, the universe, the calendar, the grid, the cost
model and the gate thresholds fixed and adds only risk architecture. Any difference in outcome is
therefore attributable to the risk architecture rather than to a re-tuned signal — which is the only
reason a second attempt on a contaminated window is worth running at all.

**What is genuinely cross-sectional about it.** The ranking scores all 34 eligible members against
each other on one date and takes the top k. It is not k independent single-symbol rules run side by
side: a symbol is held because it outranked the other 33, not because it cleared an absolute
threshold. The risk architecture added here is portfolio-level (aggregate ceiling, portfolio
volatility, portfolio drawdown ladder) with one position-level component (the stop), and none of it
re-scores a symbol against anything but the basket it is already in.

---

## 2. Eligible universe

Unchanged from Attempt 1 and from Stage 1.

| Field | Value |
|---|---|
| Source | `governance/STAGE_1_UNIVERSE.json` |
| Universe version | `SE100-U1-d4917c2f7f1cd834` |
| Member count | 34 |

```
AGG BND DIA DVY EEM EFA HYG IEF IVV IWM IYR LQD MDY QQQ SHY SPY TIP
TLT VEA VGK VIG VNQ VTI VWO VYM XLB XLE XLF XLI XLK XLP XLU XLV XLY
```

Generation 2 re-checks eligibility on development data only and never adds, drops or substitutes a
symbol. The membership is Stage 1's and is frozen.

`AAPL` is present in the data tree as a Stage 2 single-symbol fixture. It is never a member of the
eligible universe and is never ranked.

---

## 3. Ranking signal

Unchanged from Attempt 1. `stockedge100.strategies.g2_rotation.total_return` is **imported and called
unmodified**. Reimplementing a sealed formula for a second attempt would create two definitions of one
signal and a place for them to diverge; importing it keeps the signal literally identical and makes
"the signal did not change" checkable rather than asserted.

| Field | Value |
|---|---|
| Name | `N_MONTH_TOTAL_RETURN_BACKWARD_DIVIDEND_CHAIN` |
| Sort key | `(-signal, symbol)` |
| Tie-break | Ascending ticker, on exactly equal `Decimal` signals |

```
TR(t0 -> t1) = (close[t1] / close[t0]) / PROD over sessions s in (t0, t1] of (1 - D[s] / close[s-1]) - 1
```

**Look-ahead.** An adjusted-close read at `t1` would be a look-ahead: `adj_close[t1]` is a function of
every dividend paid after `t1`. The product form above touches only sessions inside the interval.
`adj_close` is never read by the ranking signal, in either attempt.

An undefined result means *excluded from this date's ranking*, recorded as an exclusion event. It
never means zero.

---

## 4. Portfolio construction and position sizing

**Changed from Attempt 1**, and this is the one change that is not risk architecture.

```
w(k) = min(A / k, C)   quantized to 9 dp, ROUND_DOWN
A = 0.50   (the RA2-1 aggregate exposure ceiling)
C = 0.50   (the sealed per-position concentration ceiling)
```

| k | Weight per position | Target gross |
|---|---|---|
| 1 | 0.500000000 | 0.500000000 |
| 2 | 0.250000000 | 0.500000000 |
| 3 | 0.166666666 | 0.499999998 |

Attempt 1 used `w(k) = min(0.95 / k, 0.50)`, sizing against the constitutional 95% gross ceiling.
RA2-1 caps aggregate exposure at 50% of equity, so sizing k positions at `0.95/k` each would demand
95% gross and be clamped down to 50% on every rebalance — the strategy would be defined by its clamp
rather than by its weights. The weight is derived from the ceiling that actually binds.
(`G2A2-CONFLICT-4`.)

**`ROUND_DOWN` is load-bearing.** At `prec=34` and `ROUND_HALF_EVEN`, `0.50 / 3` rounds up and three
such weights exceed the ceiling by one ulp, which would make the aggregate clamp bind on the last buy
of every k=3 rebalance for a pure representation reason. The `0.499999998` above is that ulp, taken
deliberately on the safe side.

**Equal weight is an entry rule.** A symbol that survives a rebalance is left exactly as it is —
never trimmed to target, never topped up. Carried unchanged from Attempt 1's `G2-CONFLICT-10`. The
Attempt 2 throttle is not an exception: it trims toward the *aggregate ceiling*, never toward a
per-position target, and it fires only when the ceiling is breached.

**The budget on the order is a record of intent, not the number that sizes the fill.** A frozen
`Order` has nowhere to carry a weight. The budget recorded on the `OrderRequest` is `w(k) * equity` at
the decision close; the engine re-evaluates `w(k) * f * equity` at the fill open, where `f` is the
combined risk scalar measured at the decision close. Carried from Attempt 1's `G2-CONFLICT-16`.

That scalar timing is not a choice. The engine's session loop records equity and updates risk state at
step 6 and takes decisions at step 7, and fills happen at step 2 of the following session, so the
scalar in force at fill time is necessarily the decision session's. Using `t+1`'s scalar would require
measuring a close that has not happened.

**Attempt 1's k=1 half-cash bias is removed.** Under `min(0.95/k, 0.50)`, k=1 targeted 50% gross while
k=2 and k=3 targeted 95%; Attempt 1 declared this as its SC-3, because the k=1 variants were
structurally half in cash and so structurally less likely to breach a screen whose first criterion is
zero shutdown events. Under `min(0.50/k, 0.50)` all three k values target the same 50% gross. The bias
is removed not by adjusting the selection rule but because the ceiling that produced it now applies
uniformly. This was **not** the reason RA2-1 was chosen — RA2-1 was specified in the operating prompt
as a risk control — and it is recorded because a reader comparing selection outcomes across the two
attempts needs to know the k axis is no longer confounded with gross exposure. (`G2A2-CONFLICT-7`.)

**The per-position concentration ceiling now binds nowhere.** At `C = 0.50` it is non-binding for k=2
and k=3 (targets 0.25 and 0.1666…) and exactly coincident with the aggregate ceiling at k=1. It is
left in place and still enforced: a clamp that never binds is not a clamp that may be removed, because
removing it would mean a future change to the aggregate ceiling silently removed the per-position
bound too. (`G2A2-CONFLICT-11`.)

---

## 5. Risk architecture `RA2`

Five components. **Every constant here is frozen and applied uniformly to all eighteen variants. None
of them is an axis of the grid.**

Searching them alongside the rotation parameters would cross from a disclosed risk control into
curve-fitting to 2008 and 2020 — the two episodes whose observation motivated this attempt in the
first place.

### 5.1 Provenance of the constants

RA2-1, RA2-2, RA2-3 and RA2-5 take the values specified in the operating prompt. RA2-4's ladder is
the prompt's proposed −5/−8/−10 staging at 75%/50%/25%; the prompt permitted a more principled
staging with documented reasoning, and none was found that was not itself a fit to the observed
drawdown dates, so the proposed staging is adopted unchanged.

That staging is nevertheless **not unsourced**, and the following is arithmetic rather than
judgement. Expressed as absolute aggregate ceilings — `f_base × ladder scalar` — three of RA2-4's
four bands reproduce the sealed Generation 1 `RA1-5` rungs exactly:

| Band | Drawdown from HWM | Scalar | Absolute ceiling | Generation 1 `RA1-5` | Same? |
|---|---|---|---|---|---|
| 0 | `dd < 0.05` | 1.00 | 0.500000000 | 0.500000000 (`dd < 0.08`) | yes |
| 1 | `0.05 <= dd < 0.08` | 0.75 | 0.375000000 | 0.500000000 (`dd < 0.08`) | **no — tightened** |
| 2 | `0.08 <= dd < 0.10` | 0.50 | 0.250000000 | 0.250000000 | yes |
| 3 | `dd >= 0.10` | 0.25 | 0.125000000 | 0.125000000 | yes |

Only band 1 is new, and it is new as a *subdivision* rather than as a value: `RA1-5` has no threshold
at 0.05 and holds its ceiling flat at 0.500000000 across the whole of `[0.05, 0.08)`, which RA2-4
splits and tightens to 0.375000000. RA2-4 is therefore a strict tightening of an architecture sealed
before Attempt 1's results existed, not a fresh choice made after seeing them, and the single degree
of freedom it adds is one threshold and one scalar.

RA2-2 and RA2-3 are carried from Generation 1's `RA1`
(`config/stage3_attempt2_strategy_protocol.json`), which is why this architecture is named RA2 and its
modules carry the `_ra1` suffix that names their lineage.

### 5.2 `RA2-1` — aggregate exposure ceiling, 0.50 of equity

```
gross(t)   = SUM over held symbols of quantity * close(t)
ceiling(t) = 0.50 * f(t) * equity(t)
gross(t) must not exceed ceiling(t)
```

**Part A — the entry clamp.** At the fill open the budget for an entry is clamped to
`max(0, 0.50 * f * equity_open - position_value_open)`, where `position_value_open` is the gross value
of the book as already settled on that open. Because the Attempt 1 engine executes all SELL legs
before any BUY leg and re-reads the book between buys, the clamp is evaluated against the settled book
and cannot be breached by the ordering of legs within one rebalance.

The clamp is named `AGGREGATE_RA2` and is evaluated in this order:

```
REQUESTED_BUDGET -> AGGREGATE_RA2 -> AGGREGATE -> CASH_FLOOR -> CONCENTRATION
```

`AGGREGATE_RA2` precedes the inherited `AGGREGATE` so the binding clamp is reported by its own name
rather than masked by a looser one. If the book is already at or above the ceiling when an entry is
decided, the clamp yields a budget of zero and the entry is rejected — the correct conservative
outcome, and not an error.

*Why a new clamp and not a lower cost-model ceiling.* `g2_costs.derive_mapping` permits exactly one
JSON-pointer difference from the Generation 1 sealed cost model, and that single permitted override is
already spent on `/account/max_open_risky_positions`. Lowering `max_gross_exposure_fraction` to 0.50
would require a second override and would silently change the meaning of every cost-model-derived
quantity Attempt 1 recorded. RA2-1 is therefore a new named clamp in the Attempt 2 engine subclass,
applied **in addition to — not instead of —** the inherited 0.95 `AGGREGATE` clamp, which remains in
place and is simply never the binding one. (`G2A2-CONFLICT-2`.)

*Rejection reason.* An entry clamped to zero is rejected as `INSUFFICIENT_CASH` with the clamp named
in the detail string. `stockedge100.backtest.orders.REASONS` is a closed declared set; inventing an
`AGGREGATE_RA2` reason at runtime would widen a sealed set. (`G2A2-CONFLICT-16`.)

**Part B — the continuous throttle.** At every session close `t` at which the strategy takes a
decision, compute the projected book after any `STOP` and `EXIT` legs already merged for that session.
If `projected_gross(t)` exceeds `ceiling(t)`, sell down the excess — largest projected position value
first, ties broken by ascending symbol — scheduling partial `SELL` legs for the next open.

This is mandatory, not an extra. A ladder that reduced sizing only at entries would do nothing at all
between scheduled rebalances, which is precisely when Attempt 1's drawdowns happened; a quarterly
variant takes 53 decisions about size in thirteen years. The operating prompt's statement of the
problem is that Attempt 1 had no mechanism to reduce exposure before a breach. **The continuous
throttle is that mechanism, and the de-risk ladder is inert without it.**

Worked example of the drift it catches: start gross 50, cash 50, equity 100, exposure 0.500. The
position doubles — gross 100, cash 50, equity 150, exposure 0.667. No order was placed and the ceiling
is breached by a third. Only a continuous measurement catches this.

*Minimum-notional skip.* A trim leg whose notional would fall below the sealed `min_order_notional` is
skipped rather than submitted, because the engine would reject it as `MIN_NOTIONAL` anyway. Skipped
legs are counted as `throttle_legs_below_min_notional` and reported per variant. The consequence is
that the ceiling can be transiently exceeded by **less than one minimum lot**; the ceiling assertion
admits exactly that slack and no more. (`G2A2-CONFLICT-17`.)

**Part C — measurement.** `max_gross_fraction_observed = max over sessions of gross(t) / equity(t)` is
recorded for every run and reported for every variant. The ceiling is a claim about behaviour; the
measurement is what makes it checkable. A run whose maximum observed gross fraction exceeds 0.50 by
more than the declared slack is a defect, not a result. The engine asserts the ceiling after every
fill and raises rather than continuing.

### 5.3 `RA2-2` — portfolio volatility target, 0.10 annualized

Measured on **the equity curve**.

> At session `t`, take the last 21 recorded equity points, form the 20 session-over-session simple
> returns `r_i = E_i / E_(i-1) - 1`, take the sample standard deviation with denominator 19, and
> multiply by `sqrt(252)`. That is `sigma_p(t)`.

```
f_vol(t) = min(1, 0.10 / sigma_p(t))   when sigma_p(t) > 0, else 1
           quantized to 9 dp, ROUND_DOWN
```

This is exactly the shape of `stockedge100.strategies.attempt2_indicators.vol20` — 21 bars, 20
returns, divide by 19, times `sqrt(252)` — applied to the equity curve rather than to a price series.
The window length, the sample denominator and the annualisation factor are Generation 1's and are not
re-chosen here.

*Why the equity curve and not a price series.* The operating prompt specifies a **portfolio-level**
volatility target. A weighted average of member volatilities is not the portfolio's volatility: it
ignores the correlations that are the entire reason a k=3 basket differs from three k=1 baskets, and
it ignores the cash. The equity curve is the portfolio's realized return series by definition. It also
sidesteps the `adj_close` look-ahead exception entirely — the equity curve is built from marks the
engine has already taken and contains no forward-looking column.

Before 21 points exist, `f_vol(t) = 1`. The strategy is not scaled down for lack of a measurement.
Before the first fill the equity curve is flat, every return is exactly zero, `sigma_p` is zero and
`f_vol` is 1 — correct, and not a special case: a portfolio of cash has no volatility to target.

*Self-reference, disclosed.* `sigma_p` is measured on an equity curve that `f_vol` itself influences.
Lower exposure produces lower measured volatility, which raises `f_vol`, which raises exposure. The
feedback is negative and therefore stabilising, and it is damped by a 20-session lag; it is not a
circularity that can diverge. It is **not corrected**, because correcting it would mean measuring a
counterfactual unlevered equity curve — a second backtest with its own assumptions. The realized
distribution of `f_vol` is reported instead: minimum, mean, and the count of sessions on which it was
below 1. (`G2A2-CONFLICT-13`.)

### 5.4 `RA2-3` — per-position stop, 0.08 from entry

```
reference = cost_basis / quantity
condition: close(t) <= (1 - 0.08) * reference
evaluated at:  session close
exit at:       next session open, whole position
reason tag:    STOP
```

*The reference price had to be frozen explicitly.* `stockedge100.backtest.portfolio.Position` carries
no entry price. It carries `cost_basis`, the all-in cash paid for the position including commission
and fees, because the engine debits `-fill.cash_delta`. The stop reference is therefore the all-in
per-share cost basis, not the raw fill reference price. The reference sits very slightly above the
traded price — by the per-share commission and fees, on the order of a basis point at the sealed cost
model — so the stop triggers marginally *earlier* than a raw-price stop would, which is the
conservative direction. Leaving "entry price" implied would have let the implementation choose between
two defensible readings after seeing which performed better. (`G2A2-CONFLICT-14`.)

The Attempt 1 portfolio prorates `cost_basis` on a partial sell, so `cost_basis / quantity` is
invariant under a throttle trim: a trimmed position keeps the same stop reference it had before.

*No per-symbol cooldown.* A symbol stopped out may be re-entered at a later scheduled rebalance if it
ranks in the top k. Generation 1's `RA1-6` five-session per-symbol bar is **not** carried. Adding one
would be a second free parameter and it was not specified.

Stop exits are counted per variant, and the realized loss at each stop fill is recorded, so the report
can state how far past 8% the one-session lag actually carried.

### 5.5 `RA2-4` — de-risk ladder

The load-bearing addition of this attempt.

```
dd(t) = (high_water(t) - equity(t)) / high_water(t)
```

`high_water(t)` is the running maximum of equity including session `t` — **the same high-water mark
the constitutional research shutdown uses**, read from the engine rather than recomputed, so the
ladder and the shutdown cannot disagree about the drawdown.

| Band | Condition | `f_ladder` |
|---|---|---|
| 0 | `0.00 <= dd < 0.05` | 1.00 |
| 1 | `0.05 <= dd < 0.08` | 0.75 |
| 2 | `0.08 <= dd < 0.10` | 0.50 |
| 3 | `dd >= 0.10` | 0.25 |

Each band is **closed at its lower bound and open at its upper bound**, so `dd` exactly equal to 0.05
is band 1, not band 0. Stated because a threshold is a decision, and an inequality direction chosen at
implementation time is a free parameter.

**Descent** is immediate and to the full computed band: if the band computed from `dd(t)` is above the
current band, the current band becomes that band in one step, at session `t`. There is no smoothing —
a fast drawdown is exactly the case the ladder exists for.

**Recovery** is at most one band per session, and only when the computed band is strictly below the
current band *and* the RA2-5 lockout has elapsed. Recovery from band 3 to band 0 therefore requires at
least three sessions after the lockout expires.

The asymmetry — immediate down, one step up, gated by a cooldown — is the mechanism. A symmetric
ladder would re-lever into a bear-market rally at the first band boundary it crossed back over, which
is the failure the lockout exists to prevent.

*Relationship to the shutdown threshold, and what it costs the gate.* The deepest rung fires at a 10%
drawdown. The constitutional research shutdown fires at 15%, and Gate 3's max-drawdown condition
`S3-C2` is also 15%. **The ladder is entirely inside the threshold it is trying to keep the strategy
away from, by construction.** This sharpens Attempt 1's `S3-CONFLICT-3`: a `MET` `S3-C2` was already
near-structural in Generation 2, because the representative-selection rule requires zero shutdown
events and a shutdown fires at the same 15%. In Attempt 2 the architecture additionally cuts exposure
to a quarter before that point is reached. `S3-C2` must therefore be read as almost entirely a
statement about the risk architecture and almost not at all about the signal, and it is **not
independent evidence of an edge**. (`G2A2-CONFLICT-15`.)

*What the ladder buys, as arithmetic.* Consider a walk of consecutive round trips each losing exactly
the 8% stop on the full permitted aggregate exposure, with the ladder read at each decision close.
This is **not a prediction and not a guarantee** — it is a property of the frozen constants, computed
before any variant was run, and it assumes a worst case no real path is obliged to follow.

| Trip | `dd` before | Band | `f_cap` | Loss this trip | `dd` after |
|---|---|---|---|---|---|
| 1 | 0.0000% | 0 | 0.500 | 4.000% | 4.0000% |
| 2 | 4.0000% | 0 | 0.500 | 4.000% | 7.8400% |
| 3 | 7.8400% | 1 | 0.375 | 3.000% | 10.6048% |
| 4 | 10.6048% | 3 | 0.125 | 1.000% | 11.4988% |
| 5 | 11.4988% | 3 | 0.125 | 1.000% | 12.3838% |
| 6 | 12.3838% | 3 | 0.125 | 1.000% | 13.2599% |
| 7 | 13.2599% | 3 | 0.125 | 1.000% | 14.1273% |
| 8 | 14.1273% | 3 | 0.125 | 1.000% | 14.9861% |
| 9 | 14.9861% | 3 | 0.125 | 1.000% | **15.8362% — breach** |

Nine consecutive maximum-loss round trips are required to breach 15%; eight leave the drawdown at
14.9861%. Under Generation 1's sealed `RA1-5` rungs the same walk breaches in **seven**. The band 1
rung therefore buys two additional maximum-loss round trips. Note that band 2 is skipped entirely in
this walk — the trip that starts at 7.8400% lands at 10.6048%, stepping over `[0.08, 0.10)` — which is
why the descent rule is "to the full computed band" and not "one band at a time".

This walk is **not** a device for stopping at 14.99%. No RA2 rule references the 15% ceiling, no rule
references a drawdown level between 10% and 15%, and no rule is conditioned on proximity to the
shutdown.

*Measured per variant:* downward transitions (ladder activations), upward transitions, deepest band
reached, sessions spent in each band, and sessions on which a recovery was computed but blocked by the
lockout.

### 5.6 `RA2-5` — re-entry lockout, 10 trading sessions

Armed by **any downward ladder transition**, expiring 10 trading sessions after the session on which
the transition occurred. Not armed by an upward transition — only de-risking arms the cooldown.

It **gates every upward transition, not only the final step to band 0**. The stricter reading is taken
deliberately: the prompt's phrase is "before exposure returns to full sizing", and gating only the
last step would let a strategy climb from band 3 to band 1 the session after a de-risk and sit at 75%
sizing through the drawdown that caused it.

Counted in **trading sessions**, by index into the run's session list. A calendar-day cooldown would
be shortened by a holiday and lengthened by a weekend for no reason connected to the market.

*Measured per variant:* the number of times the lockout was armed (equal to the number of downward
transitions), and the number of sessions on which a computed recovery was blocked by it.

### 5.7 The combined scalar

```
f(t) = f_vol(t) * f_ladder(t)    quantized to 9 dp, ROUND_DOWN
range: (0, 1]
```

`f(t) = 1` exactly when volatility is at or below target and the drawdown is below 5%.

**Multiplicative, not `min()`.** The two terms answer different questions — how violent is the market,
and how much have we already lost — and a portfolio in a violent drawdown should be smaller than one
in either condition alone. `min()` would discard whichever answer was less extreme.

| | |
|---|---|
| Applies to | the entry budget at the fill open: `w(k) * f * equity` |
| Applies to | the aggregate ceiling at every session: `0.50 * f * equity` |
| Does **not** apply to | the per-position stop, an absolute condition on price and not a sizing rule |
| Does **not** apply to | the constitutional research shutdown, which is the engine's and is not modified |

### 5.8 Where the risk state lives

The **Attempt 2 engine subclass** owns it. The candidate sees only `DecisionContext`, which carries
`(session, cash, equity, open_symbols, shutdown_active)` — no per-position cost basis, needed for the
stop, and no high-water mark, needed for the ladder. Extending `DecisionContext` would mean editing
`stockedge100/backtest/engine.py`, a Generation 1 file that is frozen and read-only.

This works because the Generation 1 session loop runs the risk step (step 6: record equity, update the
high-water mark, test the shutdown) **strictly before** the decision step (step 7: build the
`DecisionContext` and call the candidate). Risk state updated during step 6 is current when step 7
runs, in the same session, with no change to the base loop.

The Attempt 2 engine subclasses the Attempt 1 `RotationEngine` and overrides only its own methods.
Attempt 1's modules are imported, never modified.

---

## 6. Rebalance calendar

Unchanged from Attempt 1.

A session is a scheduled rebalance if it is the run's first session, or if its calendar month differs
from that of the previous session the strategy saw. A quarterly variant additionally requires that
month to be one of January, April, July and October.

The calendar looks **strictly backwards**. Month-end would need tomorrow's date to be decidable today.
See Attempt 1's `G2-CONFLICT-8`, carried unchanged.

| Frequency | Rebalance sessions | First three | Last |
|---|---|---|---|
| `MONTHLY` | 157 | 2008-07-28, 2008-08-01, 2008-09-02 | 2021-07-01 |
| `QUARTERLY` | 53 | 2008-07-28, 2008-10-01, 2009-01-02 | 2021-07-01 |

These counts are carried from `config/generation_2/g2_rotation_protocol.json`
(`1cc5f94ffa70d66e059182a6330bffab2a72f7e4f46db07e50c2924f42799810`). **The runner recomputes both on
the actual session list and refuses to run if either differs.** A carried measurement that is not
re-measured is a restated constant, and a restated constant can drift.

**The rebalance calendar governs entries and signal-driven exits only.** The stop, the throttle and
the ladder are evaluated at *every* session close, not only on rebalance sessions. That is the
departure from Attempt 1 recorded as `G2A2-CONFLICT-1`.

---

## 7. Window, run span, and the guard

| Field | Value |
|---|---|
| Development window | 1993-01-29 → 2021-07-31 (last session 2021-07-30) |
| Run start | 2008-07-28 (Monday) |
| Run end | 2021-07-30 |
| Run sessions | 3276 |
| Binding symbol | `VEA`, inception 2007-07-26 |
| Members missing a bar at run start | none |
| Symbols ending before run end | none |
| Development union sessions | 7178 |

The run span is unchanged from Attempt 1. Attempt 2 changes the strategy, not the data, the universe
or the window — an identical run span is what makes the two attempts comparable at all. **The runner
recomputes every value above from the loaded series and refuses to run if any differs.**

**Enforcement.** `stockedge100.strategies.g2_window_guard`, imported **unmodified** from Attempt 1.
Every series is truncated while parsing, not after, and the bound is re-asserted after loading.
Reusing the guard rather than re-deriving the bound is deliberate: a second derivation of the same
bound is a second place for it to be wrong.

---

## 8. Execution

| Event | Timing |
|---|---|
| Decision | at a session close |
| Fill | at the next session's open |
| Entry | a symbol entering the top k at a scheduled rebalance, bought at the next open |
| Signal exit | a symbol dropping out of the top k at a scheduled rebalance, sold in full at the next open |

### 8.1 Order kinds this attempt may issue

| Tag | Side | When | Quantity |
|---|---|---|---|
| `ENTRY` | BUY | scheduled rebalance only | sized by the budget rule |
| `EXIT` | SELL | scheduled rebalance only | whole position |
| `STOP` | SELL | any session close at which the RA2-3 condition holds | whole position |
| `THROTTLE` | SELL | any session close at which projected gross exceeds the scaled ceiling | partial, largest first |
| `SHUTDOWN` | SELL | the session a research shutdown triggers | whole position, issued by the engine |

### 8.2 Attempt 1's `no_discretionary_exits` clause is narrowed, not weakened

Attempt 1 sealed: *"Between scheduled rebalances the strategy issues no orders at all. There is no
stop, no trailing stop, no profit target, and no intra-period re-rank."*

Attempt 2 departs from this clause **deliberately and only in the direction of reducing exposure**.
Between scheduled rebalances Attempt 2 may issue `SELL` orders — a stop exit or a throttle trim — and
**may issue no `BUY` order of any kind**. There is still no profit target and still no intra-period
re-rank: the ranking is consulted only on scheduled rebalance sessions, exactly as before. The clause
is not weakened for entries; it is narrowed to entries. (`G2A2-CONFLICT-1`.)

### 8.3 One order per symbol per session

`stockedge100.backtest.orders.OrderBook.submit` refuses two orders in one symbol on one decision
session whatever the sides are, raising `DuplicateOrderError`.

Order kinds are merged by symbol under a frozen precedence before scheduling:

```
STOP > EXIT > THROTTLE > ENTRY
```

At most one request per symbol reaches the book. An `ENTRY` can never collide with a `STOP`, an `EXIT`
or a `THROTTLE`, because all three apply only to currently held symbols and an `ENTRY` is issued only
for symbols not currently held; the precedence is nonetheless applied unconditionally and the merged
list is **asserted** to have unique symbols, because "cannot happen" is a claim and not a guarantee.

A session on which a `STOP` suppresses an `EXIT` for the same symbol is counted and reported as
`stop_preempted_signal_exit`. Both are full sells, so the fill is identical; the count exists so the
report can say how often the stop was the binding reason rather than a redundant one.

### 8.4 Execution lag

A stop condition observed at the close of session `t` is exited at the open of session `t+1`, not at
the close of `t`. A throttle computed at the close of `t` is trimmed at the open of `t+1`. **The
strategy therefore carries one session of exposure past every risk signal it observes.**

This is not a defect. It is the direct consequence of next-session-open execution, which the
constitution requires and which both generations use everywhere. The research shutdown itself has
exactly the same lag: constitution §5.1 liquidates at the *next* open, not at the close that triggered
it. **Attempt 2 does not get a tighter execution convention than the shutdown it is trying to avoid.**

The gap between the close that triggered each stop and the open that filled it is recorded per fill,
so the report can state the realized slippage of the lag rather than assert it is small.
(`G2A2-CONFLICT-5`.)

---

## 9. The grid

18 variants. Enumeration order: `lookback_months` outer, then `top_k`, then `rebalance_frequency`.
**The index is part of the seal.**

Variant id format: `SE100-G2-S3-C2-ROTATION-RA1-L{lookback:02d}-K{k}-{FREQUENCY}`. The lookback is
zero-padded because the final tiebreak of the representative-selection rule is lexicographic, and an
unpadded `L12` would sort before `L3`.

| # | Variant id | Lookback | k | Rebalance | Weight/position | Target gross | Rebalance sessions |
|---|---|---|---|---|---|---|---|
| 1 | `SE100-G2-S3-C2-ROTATION-RA1-L03-K1-MONTHLY` | 3 | 1 | MONTHLY | 0.500000000 | 0.500000000 | 157 |
| 2 | `SE100-G2-S3-C2-ROTATION-RA1-L03-K1-QUARTERLY` | 3 | 1 | QUARTERLY | 0.500000000 | 0.500000000 | 53 |
| 3 | `SE100-G2-S3-C2-ROTATION-RA1-L03-K2-MONTHLY` | 3 | 2 | MONTHLY | 0.250000000 | 0.500000000 | 157 |
| 4 | `SE100-G2-S3-C2-ROTATION-RA1-L03-K2-QUARTERLY` | 3 | 2 | QUARTERLY | 0.250000000 | 0.500000000 | 53 |
| 5 | `SE100-G2-S3-C2-ROTATION-RA1-L03-K3-MONTHLY` | 3 | 3 | MONTHLY | 0.166666666 | 0.499999998 | 157 |
| 6 | `SE100-G2-S3-C2-ROTATION-RA1-L03-K3-QUARTERLY` | 3 | 3 | QUARTERLY | 0.166666666 | 0.499999998 | 53 |
| 7 | `SE100-G2-S3-C2-ROTATION-RA1-L06-K1-MONTHLY` | 6 | 1 | MONTHLY | 0.500000000 | 0.500000000 | 157 |
| 8 | `SE100-G2-S3-C2-ROTATION-RA1-L06-K1-QUARTERLY` | 6 | 1 | QUARTERLY | 0.500000000 | 0.500000000 | 53 |
| 9 | `SE100-G2-S3-C2-ROTATION-RA1-L06-K2-MONTHLY` | 6 | 2 | MONTHLY | 0.250000000 | 0.500000000 | 157 |
| 10 | `SE100-G2-S3-C2-ROTATION-RA1-L06-K2-QUARTERLY` | 6 | 2 | QUARTERLY | 0.250000000 | 0.500000000 | 53 |
| 11 | `SE100-G2-S3-C2-ROTATION-RA1-L06-K3-MONTHLY` | 6 | 3 | MONTHLY | 0.166666666 | 0.499999998 | 157 |
| 12 | `SE100-G2-S3-C2-ROTATION-RA1-L06-K3-QUARTERLY` | 6 | 3 | QUARTERLY | 0.166666666 | 0.499999998 | 53 |
| 13 | `SE100-G2-S3-C2-ROTATION-RA1-L12-K1-MONTHLY` | 12 | 1 | MONTHLY | 0.500000000 | 0.500000000 | 157 |
| 14 | `SE100-G2-S3-C2-ROTATION-RA1-L12-K1-QUARTERLY` | 12 | 1 | QUARTERLY | 0.500000000 | 0.500000000 | 53 |
| 15 | `SE100-G2-S3-C2-ROTATION-RA1-L12-K2-MONTHLY` | 12 | 2 | MONTHLY | 0.250000000 | 0.500000000 | 157 |
| 16 | `SE100-G2-S3-C2-ROTATION-RA1-L12-K2-QUARTERLY` | 12 | 2 | QUARTERLY | 0.250000000 | 0.500000000 | 53 |
| 17 | `SE100-G2-S3-C2-ROTATION-RA1-L12-K3-MONTHLY` | 12 | 3 | MONTHLY | 0.166666666 | 0.499999998 | 157 |
| 18 | `SE100-G2-S3-C2-ROTATION-RA1-L12-K3-QUARTERLY` | 12 | 3 | QUARTERLY | 0.166666666 | 0.499999998 | 53 |

**The grid is complete at eighteen and may not be widened, narrowed or re-centred.** The risk
architecture constants are not axes.

Each variant is run twice — `#BASE` and `#STRESS`, against the base and stressed cost models — for 36
runs. A variant satisfies a gate condition only if **both** of its runs satisfy it. The stressed cost
model is not a sensitivity check that may be waived.

### 9.1 Multiplicity

| Field | Value |
|---|---|
| Variants this attempt | 18 |
| Runs this attempt | 36 |
| Variants, Attempt 1 | 18 |
| Runs, Attempt 1 | 36 |
| Cumulative variants, this hypothesis family | 36 |
| Cumulative runs, this hypothesis family | 72 |

No multiplicity correction is applied to the gate thresholds, because the thresholds are
constitutional and may not be altered by a stage that would benefit from altering them. The
multiplicity is **disclosed** instead, and it is the reason a development pass is explicitly not
evidence of an edge.

The 36 cumulative variants are **not 36 independent tests**. Attempt 2's risk architecture was chosen
after seeing where Attempt 1 broke, so the effective number of researcher degrees of freedom is larger
than 36, and is not quantified here because any quantification would itself be a choice made after the
fact.

---

## 10. Representative selection rule

Frozen before any variant is run. Unchanged from Attempt 1. **Return-blind.**

| Order | Criterion | Scope |
|---|---|---|
| 1 | zero research-shutdown events | across **both** runs of the variant |
| 2 | lowest turnover — total fill count across both runs | tiebreak |
| 3 | lexicographic variant id | total order; reached only on a tie in both above |

**Structural enforcement.** The selection function accepts a frozen `SelectionInput` dataclass whose
fields are exactly `(variant_id, shutdown_events, fill_count, per_run)`. No return, drawdown, profit
factor or trade-count figure can reach it, because **there is no field to carry one**. The module
asserts at import that the dataclass's actual field tuple equals the declared `SELECTION_FIELD_NAMES`,
so a field added later — including one of Attempt 2's own new risk-architecture counters — fails the
import rather than silently widening what the selector can see.

**Attempt 2's new counters are explicitly excluded from selection.** The de-risk ladder activation
count and the re-entry lockout trigger count are reported for every variant and are **not** selection
inputs. Admitting them would make the selection a function of how hard the risk architecture worked,
which is a performance-adjacent quantity.

*Why fill count and not gross notional.* Gross notional traded is a partial return proxy — a variant
that compounded further trades larger notionals for the same decisions. Fill count is not. Carried
from Attempt 1's `G2-CONFLICT-13`.

*What changed underneath the tiebreak.* Fill count now includes `STOP` and `THROTTLE` legs. The
throttle in particular adds fills, so Attempt 2's turnover figures are **not comparable** with Attempt
1's, and the tiebreak now partly measures how often the risk architecture intervened. This is
disclosed as SC-4 and **the rule is not changed to compensate**, because changing a frozen selection
rule after seeing that it might behave differently is precisely what pre-registration exists to
prevent.

### 10.1 The two fail routes

| Route | Condition | Verdict |
|---|---|---|
| No eligible representative | all eighteen variants record ≥1 research-shutdown event | `FAIL — STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE` |
| Representative fails the gate | a representative is selected and fails ≥1 Gate 3 condition | `FAIL — STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE` |

The **same** token is emitted on both routes; the routes are distinguished in the decision record's
gate conditions and in the report prose, not in the token. Carried from Attempt 1's `G2-CONFLICT-11`.
(`G2A2-CONFLICT-9`.)

**If the representative fails, no runner-up is promoted.** Promoting one would convert a return-blind
selection into a search over eighteen candidates for one that passes.

**The representative is selected once**, before any gate condition is evaluated. It is not reselected,
re-ranked or substituted for any reason.

On either fail route **the attempt closes**. No Attempt 3 is authorized by this document, and no
Attempt 3 may be opened without a further disclosed adaptation and a separate authorization.

---

## 11. Gate 3 evaluation

| Field | Value |
|---|---|
| Evaluated on | the selected representative variant only, across both of its runs |
| Conjunctive | all Gate 3 conditions must be satisfied — constitution §9 |
| Criteria source | `config/generation_2/g2_gate_criteria_ra1.json` (`SE100-CFG-3104`) |
| Thresholds changed from Attempt 1 | none |
| Thresholds changed from Generation 1 | none |

The verdict tokens named in the operating prompt exist in no artifact on disk. They are sealed here
and in the gate criteria file, **which becomes the disk**:

| Outcome | Token |
|---|---|
| Pass | `STAGE_3_G2_ATTEMPT_2_STRATEGY_ADMITTED_IN_DEVELOPMENT` |
| Fail | `STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE` |

No existing derivation is edited to match a prompt. (`G2A2-CONFLICT-8`.)

### 11.1 Reported for every variant, gating nothing

Net return; maximum drawdown; profit factor; closed trade count; best-trade-removed return;
research-shutdown event count and the session of each; total fill count; de-risk ladder activations
(downward transitions); ladder upward transitions and deepest band reached; sessions spent in each
band; lockout arms and sessions on which a recovery was blocked; stop exits and the realized loss at
each; throttle legs issued and throttle legs skipped below minimum notional; maximum observed gross
exposure fraction; minimum, mean and sub-1 session count of the combined risk scalar; ranking digest.
Both runs, every figure.

---

## 12. Structural consequences, declared before running

**SC-1 — low turnover at quarterly k=1.** A quarterly k=1 variant has 53 scheduled rebalances and can
therefore close at most 52 positions by signal exit; Gate 3 requires at least 30 closed trades. *In
Attempt 2 the stop and the throttle can also close or reduce a position, so the closed-trade count is
no longer bounded by the rebalance count.* The direction of the change is upward, and it is the risk
architecture, not the signal, that produces the additional trades. A representative that clears the
30-trade condition mainly on stop exits has cleared it on evidence about its risk controls. Low
turnover remains the failure mode for quarterly k=1; it is now less likely to bind, and the reason is
disclosed.

**SC-2 — minimum notional margin is thinner than Attempt 1's.** Starting equity is $100.00 and the
sealed minimum order notional is $1.00. At k=3 and a 50% aggregate ceiling the per-position budget is
about $16.67, sixteen times the minimum — against about $31.67 in Attempt 1. With the combined risk
scalar at its ladder floor of 0.25 times a volatility scalar that can go lower still, a k=3 entry
budget can approach the minimum notional. Entries rejected as `MIN_NOTIONAL` or `ZERO_QUANTITY` are
counted and reported per variant rather than treated as absent decisions. A throttle trim on a small
position is the case most likely to fall below the minimum and be skipped (`G2A2-CONFLICT-17`).

**SC-3 — the k axis is no longer confounded with exposure.** See §4 and `G2A2-CONFLICT-7`.

**SC-4 — the tiebreak measures something new.** The continuous throttle adds `SELL` fills Attempt 1
could not produce, and total fill count is the representative-selection tiebreak. The tiebreak now
partly measures how often the risk architecture intervened — a variant whose exposure drifted above
the ceiling more often will have a higher fill count and lose the tiebreak to one that drifted less.
That is a defensible ordering (less intervention is less turnover is less cost) but it is **not the
same quantity Attempt 1's tiebreak measured**, and the two attempts' turnover figures are not
comparable. The rule is **not** changed to exclude throttle legs: it was frozen before Attempt 1 ran,
and adjusting it now, after reasoning about how it might behave, would be exactly the researcher
degree of freedom this document exists to constrain.

**SC-5 — the cash floor can never bind.** The sealed 5% minimum cash buffer cannot bind at a 50%
aggregate exposure ceiling, because cash is at least 50% of equity at all times. The `CASH_FLOOR`
clamp is present, enforced, and never the binding clamp. Reported as such rather than removed.
(`G2A2-CONFLICT-12`.)

**SC-6 — the architecture can only reduce return, and a `FAIL` on net return would be predictable.**
Every one of RA2-1, RA2-2, RA2-4 and RA2-5 scales sizing down or holds it, and RA2-3 exits. Attempt
2's expected gross return is therefore **lower** than Attempt 1's would have been on the same signal,
mechanically, before any question of whether the drawdown protection is worth it. Gate 3's first
condition is that net return is positive, and halving exposure roughly halves the return while the
fixed costs of trading do not halve. **A `FAIL` on `S3-C1` would be a predictable consequence of the
architecture and not a new fact about the signal.** This is declared now so that such a `FAIL` cannot
afterwards be presented as a surprising discovery, and so that a `PASS` cannot be presented as
evidence the architecture is free.

---

## 13. Contamination measurement

The claim in the header — that this document was sealed before any Attempt 2 strategy code existed —
is **measured by the sealing program before it writes anything**, and a disagreement is a refusal
rather than a warning.

**The predicate is content-based, not path-based.** Attempt 1's predicate refused to seal if any
module basename under `strategies/` or `backtest/` contained `g2_`. That predicate was correct when
`strategies/` held no Generation 2 code and is now vacuously false — Attempt 1's own six modules live
there and are supposed to. A path test would either refuse to seal forever or have to be loosened
until it tested nothing. The honest form is:

> No `.py` file under `src/stockedge100/` or `tests/` contains the string
> `SE100-G2-S3-C2-ROTATION-RA1` at seal time.

**The sealing program does not exempt itself from that predicate.** It is itself a `.py` file under
`src/stockedge100/` and would falsify the predicate if it hard-coded the candidate id. It does not: it
loads `strategy_id` from `config/generation_2/g2_rotation_ra1_protocol.json` at run time, so the
predicate is literally true rather than true-with-a-named-exception. This is disclosed rather than
left to be discovered, because a predicate satisfied by an indirection the reader cannot see is worth
no more than one that is simply false.

**A content predicate alone is not enough**, because it would pass while an Attempt 1 module was being
quietly rewritten. It is paired with an immutability check: every module below is re-hashed at seal
time and must equal its recorded digest. Any difference is a governance failure, not a value to
update.

| Path |
|---|
| `src/stockedge100/strategies/g2_rotation.py` |
| `src/stockedge100/strategies/g2_gate.py` |
| `src/stockedge100/strategies/g2_runner.py` |
| `src/stockedge100/strategies/g2_window_guard.py` |
| `src/stockedge100/backtest/g2_engine.py` |
| `src/stockedge100/backtest/g2_costs.py` |
| `src/stockedge100/reporting/g2_rotation_preregistration.py` |
| `src/stockedge100/reporting/g2_stage3_evidence.py` |
| `src/stockedge100/reporting/g2_stage3_package.py` |

Note that two of these — `g2_engine.py` and `g2_costs.py` — live under `backtest/`, not
`strategies/`. A verification sweep that looks only in `strategies/` will report success while
checking two-thirds of the set.

The measured digests are recorded in `STAGE_3_G2_ROTATION_RA1_PROTOCOL.json` and in the `runs/`
record, **not** in the config file, so that the config does not have to be rewritten to record a
measurement. (`G2A2-CONFLICT-3`.)

---

## 14. Windows referenced, and the two mandated disclosures

| Window | Span | State |
|---|---|---|
| Generation 2 development | 1993-01-29 → 2021-07-31 | the only window this attempt reads |
| Generation 2 validation | 2021-08-01 → 2024-07-31 | `LOCKED` — not read by this attempt |
| Generation 1 holdout | 2024-08-01 → 2026-07-31 | `SPENT_AND_PROHIBITED` — sealed and off-limits regardless of generation |
| Generation 2 holdout | 2026-08-01 → 2028-07-31 | `SEALED` — never to be read, by any code, at any stage, before that period exists in real calendar time |

### 14.1 The disclosure

The following text is binding. It is carried **verbatim** here, in the machine companion, in the
research report, and in both machine-readable records of this attempt's development result. The
sealer and the package builder assert byte-equality against the value stored in
`config/generation_2/g2_rotation_ra1_protocol.json`. **A paraphrase is a failure, not a stylistic
choice.**

> This pre-registration was designed after Attempt 1's development results were known. All eighteen
> Attempt 1 variants recorded at least one research-shutdown event, clustered at 2008-10 through
> 2011-10 (thirteen of eighteen), with additional single occurrences in mid-2010, January 2016, and
> March 2020 — periods of acute market stress that an unconstrained rotation strategy had no mechanism
> to survive. Attempt 2 adds risk architecture explicitly informed by this observation. The
> development window is no longer pristine for this hypothesis family. This adaptation increases
> researcher degrees of freedom and cumulative multiplicity across both attempts. No successful
> development result from Attempt 2 can, by itself, establish a trading edge — this mirrors exactly
> the disclosure Generation 1 made between its own Attempt 1 and Attempt 2.

(`G2A2-CONFLICT-6`.)

### 14.2 The validation-reuse disclosure

The window table above references Generation 2's validation window. Binding rule 7 of
[STAGE_1_G2_PARTITION_LOCK.md](STAGE_1_G2_PARTITION_LOCK.md) requires that the disclosure sealed in
its §2 be reproduced verbatim wherever that window is referenced, so it is reproduced here. It is a
disclosure about a window this attempt does not read; carrying it is not an authorization to read it.

> Generation 2's validation window (2021-08-01 → 2024-07-31) overlaps the exact period Generation 1
> used for its own Gate 4 validation read. The researcher therefore already knows, from Generation
> 1's published report, approximately how SPY (and by extension the broad market) behaved in this
> window — including its Sharpe ratio (≈0.20), total return (≈2.15%), and fold-by-fold sign pattern
> (7 of 12 positive). Generation 2 tests a different hypothesis (cross-sectional multi-asset
> selection vs. single-symbol mean reversion) over the same calendar period, which limits but does
> not eliminate the concern. This is a real multiplicity cost, disclosed and not minimized, and it
> is the reason Generation 2's validation result alone — without a clean holdout confirmation —
> cannot be treated as sufficient evidence of an edge.

(Carried under partition lock binding rule 7.)

---

## 15. Conflicts and interpretations

Seventeen, recorded in full in the machine companion. Summarised:

| Id | Conflict | Resolution |
|---|---|---|
| `G2A2-CONFLICT-1` | Per-session decisions depart from Attempt 1's sealed `no_discretionary_exits`. | Narrowed to entries, not weakened: risk-reducing SELLs only, no BUY between rebalances. |
| `G2A2-CONFLICT-2` | The 50% ceiling has no cost-model derivation route — the one permitted override is spent. | New named engine clamp `AGGREGATE_RA2` alongside the inherited 0.95 clamp. Cost model unmodified. |
| `G2A2-CONFLICT-3` | Attempt 1's path-based contamination predicate is now vacuously false. | Content-based predicate plus a paired immutability check. |
| `G2A2-CONFLICT-4` | Target weights change from `min(0.95/k, 0.50)` to `min(0.50/k, 0.50)`. | Derived from the ceiling that actually binds; declared before any run. |
| `G2A2-CONFLICT-5` | Stop and throttle carry one session of execution lag. | Accepted and measured. The shutdown itself obeys the same convention. |
| `G2A2-CONFLICT-6` | This pre-registration was written after Attempt 1's results were known. | Disclosed verbatim and asserted byte-identical downstream. |
| `G2A2-CONFLICT-7` | Attempt 1's declared k=1 half-cash bias is removed as a side effect of RA2-1. | Recorded so cross-attempt selection outcomes are not misread. |
| `G2A2-CONFLICT-8` | The prompt's verdict tokens exist in no artifact on disk. | Sealed here and in the gate criteria file. No existing derivation edited. |
| `G2A2-CONFLICT-9` | Both fail routes emit the same token. | Distinguished in the gate conditions and prose, not in the token. |
| `G2A2-CONFLICT-10` | `governance/generation_2/*` is **not** covered by `repo_state_id`; `config/generation_2/*.json` **is**. | Restates Attempt 1's `G2-CONFLICT-4`. Patterns not widened; both directions asserted explicitly. |
| `G2A2-CONFLICT-11` | The concentration ceiling now equals the aggregate ceiling and binds nowhere. | Left in place and still enforced. |
| `G2A2-CONFLICT-12` | The 5% minimum cash buffer can never bind at a 50% gross ceiling. | Enforced anyway, reported as never binding. |
| `G2A2-CONFLICT-13` | RA2-2's volatility is measured on an equity curve RA2-2 itself influences. | Negative, damped, cannot diverge. Not corrected; realized scalar distribution reported. |
| `G2A2-CONFLICT-14` | `Position` carries no entry price, so the stop reference had to be defined. | Frozen as `cost_basis / quantity` — conservative and invariant under a trim. |
| `G2A2-CONFLICT-15` | The ladder's deepest rung sits inside both the 15% shutdown and Gate 3's `S3-C2`. | Sharpens Attempt 1's `S3-CONFLICT-3`: a `MET` `S3-C2` is a statement about the architecture, not the signal. |
| `G2A2-CONFLICT-16` | `orders.REASONS` is a closed set with no aggregate-ceiling rejection. | Reject as `INSUFFICIENT_CASH` with the clamp named in the detail. Sealed set not widened. |
| `G2A2-CONFLICT-17` | A throttle trim below minimum notional is skipped, so the ceiling can be transiently exceeded. | Skipped legs counted; the ceiling assertion admits exactly that slack and no more. |

---

## 16. Adversarial tests required

Declared here **before the tests exist**, so the suite is written against a specification rather than
against the implementation's behaviour. Each item is a required test, not a suggestion.

| Id | Requirement |
|---|---|
| `AT-A` | Aggregate exposure never exceeds 50% of equity at any session, including mid-rebalance, verified after every fill and not only at session close. |
| `AT-B` | Volatility scaling reduces position size when trailing realized portfolio volatility exceeds 10% annualized, verified against a hand-constructed high-volatility equity fixture with an independently computed expected scalar. |
| `AT-C` | A position breaching the 8% stop is exited at the **next** session's open, not at the same close, and the exit is a full sell. |
| `AT-D` | The de-risk ladder steps down at the declared thresholds and back up only after the declared recovery condition, verified against a hand-constructed drawdown-and-recovery fixture that visits every band in both directions. |
| `AT-E` | The re-entry lockout genuinely blocks a return to a higher sizing band before its cooldown elapses, verified by a fixture in which recovery is available and blocked for exactly the declared number of sessions. |
| `AT-F` | Determinism: identical inputs produce identical trade, equity, ranking and risk-state digests on a clean rerun. |
| `AT-G` | The Generation 2 window guard still blocks any read at or after 2021-08-01, exercised through the Attempt 2 loading path. |
| `AT-H` | No Generation 1 or Attempt 1 module is modified: every module in §13 re-hashes to its recorded digest. |
| `AT-I` | The selection input cannot carry a performance figure: the dataclass field tuple equals `SELECTION_FIELD_NAMES` and the import-time assertion fires when it does not. |

**The existing suite is a permanent regression floor. No test is weakened, skipped or deleted to make
this attempt pass.**

### 16.1 Reproducibility

Two clean runs of the same variant and scenario must produce byte-identical trade payloads, equity
payloads, ranking digests **and risk-architecture state traces**.

In addition to Attempt 1's ranking digest, Attempt 2 records a SHA-256 over the per-session risk state
— band, lockout counter, volatility scalar, combined scalar — in session order. Equal equity curves
are weaker evidence than equal decisions, and equal decisions are weaker evidence than equal risk
state: two runs could agree on every fill while disagreeing about a band transition that never reached
an order.

No run id, timestamp or filesystem path enters any digested payload. There is no randomness in this
strategy; the seed field is `null` rather than absent, so that a future stage cannot read its absence
as an oversight.

---

## 17. Binding rules

1. **This document is sealed.** If a defect is found in it after sealing, it is reported as a blocker
   and recorded in the stage report. This document is not edited. A correction means a new artifact
   with a new id that supersedes this one, and the superseding artifact carries the reason. This
   applies equally to every Generation 1 artifact, every Generation 2 Attempt 1 artifact, and this
   one.
2. **Attempt 1 is closed.** Its verdict `FAIL — STAGE_3_G2_NO_CANDIDATE` stands permanently. Nothing
   in this attempt edits, deletes, reopens, re-runs, loosens or supersedes any Attempt 1 artifact or
   module. Attempt 1's files are pinned in the machine companion so that a change to any of them is
   **detectable**, not so that any of them may be changed.
3. **Generation 1 is closed and read-only**, always.
4. The eighteen-variant grid may not be widened, narrowed or re-centred.
5. No `RA2` constant may be grid-searched, tuned or adjusted — before or after seeing a result.
6. No runner-up is promoted if the representative fails the gate.
7. No Attempt 3 is authorized. If Attempt 2 fails, the attempt closes.
8. No existing test may be weakened, skipped or deleted.

### 17.1 Explicit non-authorizations

This document does **not** authorize:

- reading any session at or after **2021-08-01**, in this or any later stage;
- reading Generation 1's holdout (2024-08-01 → 2026-07-31), which is spent and prohibited regardless
  of generation;
- reading Generation 2's holdout (2026-08-01 → 2028-07-31), which is sealed and must never be read
  before that period exists in real calendar time;
- **Stage 4 validation**, which requires an explicit human go-ahead recorded in a later session;
- live trading, order placement, cancellation, replacement, liquidation, or unattended scheduling —
  `live_trading_authorized` remains `false`;
- reading, writing, printing or logging any broker credential; no module of this attempt may import a
  network client;
- editing, deleting, re-running, reopening or loosening any Generation 1 artifact or module;
- editing, deleting, re-running, reopening or loosening any Generation 2 Attempt 1 artifact or module;
- widening, narrowing or re-centring the grid;
- grid-searching, tuning or adjusting any `RA2` constant;
- promoting a runner-up;
- an Attempt 3;
- weakening, skipping or deleting any existing test.

---

*Machine companion: `STAGE_3_G2_ROTATION_RA1_PROTOCOL.json`, sealed by
`STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256`. The tree digest `repo_state_id` for the sealing run is
recorded in `runs/`, deliberately not in this document — `repo_state_id` covers files in this tree,
and a document that carried it would invalidate it on write.*
