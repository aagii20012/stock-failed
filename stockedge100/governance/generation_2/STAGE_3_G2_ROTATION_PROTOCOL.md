# Stage 3 (Generation 2) — cross-sectional rotation pre-registration

| Field | Value |
|---|---|
| Document id | `SE100-GOV-2003` |
| Status | `SEALED` |
| Project | StockEdge100 |
| Generation | 2 |
| Generation id | `SE100-GEN2-7394207c543401e2` |
| Stage | 3 |
| Gate | 3 — development admissibility |
| Authored (UTC) | 2026-08-15T04:19:56Z |
| Charter | [STAGE_10_GENERATION_2_CHARTER.md](STAGE_10_GENERATION_2_CHARTER.md) (`SE100-GOV-2001`) |
| Partition lock | [STAGE_1_G2_PARTITION_LOCK.md](STAGE_1_G2_PARTITION_LOCK.md) (`SE100-GOV-2002`) |
| Constitution | `SE100-GOV-0001` §§3, 4, 5.1, 6, 7, 9 gate 3, 10, 11 |
| Machine companion | `STAGE_3_G2_ROTATION_PROTOCOL.json`, sealed by `STAGE_3_G2_ROTATION_PROTOCOL.sha256` |
| `live_trading_authorized` | `false` |

This document pre-registers one candidate strategy and its parameter grid **before any Generation 2
strategy code exists**. Section 12 records the measurement that establishes that claim. What is
frozen here is not a prediction about the result; it is every choice that could otherwise be made
after seeing one.

---

## 1. What is pre-registered

| Field | Value |
|---|---|
| Strategy id | `SE100-G2-S3-C1-ROTATION` |
| Family | `CROSS_SECTIONAL_RELATIVE_STRENGTH` |
| Candidate count | 1 |
| Grid size | 18 variants |
| Runs | 2 per variant (`#BASE`, `#STRESS`) — 36 total |

**Hypothesis.** Relative strength among the eligible ETF universe persists over a multi-week to
multi-month horizon sufficiently to justify periodically rotating exposure toward the
currently-strongest names.

**Why this is genuinely cross-sectional.** The signal is a *rank* over 34 instruments computed at
every rebalance, not a per-symbol trigger. No symbol has a standing claim on the portfolio, there is
no default holding, and there is no threshold that lets the strategy sit in one name because nothing
else qualified — at every rebalance the top-k by rank are held and everything else is not. A run
that nevertheless holds one symbol throughout would be an empirical finding about the universe, and
Gate 3's condition S3-C6 is the thing that catches it. Generation 1's validated candidate put 100%
of its profit into SPY; that outcome is the reason Generation 2 exists, and the gate is left able to
reject a repeat of it.

Configuration companion: `config/generation_2/g2_rotation_protocol.json` (`SE100-CFG-3101`).
Gate criteria: `config/generation_2/g2_gate_criteria.json` (`SE100-CFG-3102`).
Cost derivation: `config/generation_2/g2_cost_model.json` (`SE100-CFG-2101`).

---

## 2. Eligible universe

The frozen 34-member universe `SE100-U1-d4917c2f7f1cd834`, unchanged:

```
AGG BND DIA DVY EEM EFA HYG IEF IVV IWM IYR LQD MDY QQQ SHY SPY TIP TLT
VEA VGK VIG VNQ VTI VWO VYM XLB XLE XLF XLI XLK XLP XLU XLV XLY
```

Re-checked for liquidity and eligibility on development data only. All 34 pass; **no symbol is added
and none is removed**, and no membership decision anywhere in Generation 2 refers to a performance
figure. `AAPL` is present in `data/normalized/daily/` as a Stage 2 engine fixture, is not a universe
member, and is excluded by name.

The universe is fixed for the whole run. It is *not* re-derived per rebalance from inception dates:
see §6 for why the run instead starts late enough that every member already exists.

---

## 3. Ranking signal

N-month total return, price plus dividends, computed only from data available as of the decision
date. Grid: **lookback ∈ {3, 6, 12} months**.

For a decision at the close of session `t1`, with `t0` the last session on or before the calendar
date `t1` shifted back N months (day-of-month clamped to the length of the target month):

```
TR(t0 -> t1) = ( close[t1] / close[t0] ) / prod over s in (t0, t1] of ( 1 - D[s] / close[s-1] ) - 1
```

`D[s]` is the cash dividend with ex-date `s`. Prices are split-adjusted, so the ratio of closes is
already free of split effects and the product re-introduces the dividend the split-adjusted series
drops.

Two properties are the reason the formula is written out rather than delegated to a column:

- It equals `adj[t1] / adj[t0] - 1` for a provider-consistent adjusted series, but it touches only
  sessions in `(t0, t1]`. An adjusted-close column read at `t1` embeds every dividend *after* `t1`
  as well; using it would be look-ahead that no window bound could catch, because every session it
  reads is in the past.
- It is computed inside `decide()` from `MarketView.history()`, so `LookAheadError` is structural
  rather than a convention the strategy is trusted to follow.

**No caching.** The signal is recomputed at each rebalance from the view then in force.

**No other signal.** There is no volatility filter, no absolute-momentum or trend overlay, no
move-to-cash-when-negative rule, and no skip-month. The candidate is relative strength alone. Adding
any of these after a result would be a new candidate under constitution §11, restarting at Gate 3.

**Ranking rule.** Sort by `(-signal, symbol)` — descending signal, ties broken by ascending ticker.
There is no threshold: the top-k are held whatever their signal is, including when all 34 are
negative. A symbol lacking a bar at `t0` or `t1` is not ranked; §6 arranges that this never occurs.

---

## 4. Portfolio construction

| Field | Value |
|---|---|
| Position count | Top-k, grid **k ∈ {1, 2, 3}** |
| Sizing | Equal weight across the k held positions |
| Gross exposure ceiling | 0.95 of equity (sealed, constitution §3) |
| Cash floor | 0.05 of equity (sealed) |
| Concentration ceiling | 0.50 of equity for any single position, at any rebalance |

Target weight per position:

```
w(k) = min( 0.95 / k , 0.50 ), quantized to 9 decimals, ROUND_DOWN
```

| k | `w(k)` | `k · w(k)` |
|---|---|---|
| 1 | 0.500000000 | 0.500000000 |
| 2 | 0.475000000 | 0.950000000 |
| 3 | 0.316666666 | 0.949999998 |

The quantization is not cosmetic. At `prec=34, ROUND_HALF_EVEN`, `0.95 / 3` rounds *up*, and three
such weights sum to `0.9500000000000000000000000000000001` — one ulp above the sealed ceiling. Left
alone, the aggregate headroom clamp would bind on the third buy of every k=3 rebalance for a pure
representation reason and would look like a risk constraint doing work. Nine decimals matches the
sealed sizing block's `share_decimals`, and `ROUND_DOWN` guarantees `k · w(k) ≤ 0.95` exactly.

**Ceilings are enforced, not assumed.** `RotationEngine._execute_buy` clamps each buy by a
per-position headroom of `0.50 · equity − position value` and by an aggregate headroom of
`0.95 · equity − total position value`, both computed from marks taken at the **fill session's
open**. A clamp that reduces a buy below the sealed `min_order_notional` rejects it; because
`orders.REASONS` is a closed declared set that `orders.py` owns and Generation 2 does not modify, the
rejection carries the existing `INSUFFICIENT_CASH` reason with the binding clamp named in the detail
string.

**No trim, no top-up.** A position that survives a rebalance is left exactly as it is. Only exits and
entries trade. Drift away from equal weight between rebalances is therefore expected and is not
corrected. This is the smaller-turnover reading and it is frozen here so it cannot be swapped for the
rebalance-to-target reading after a turnover figure is known — see G2-CONFLICT-10.

---

## 5. Rebalance calendar

Grid: **{monthly, quarterly}**. Fixed calendar rule, never signal-triggered.

A session is a scheduled rebalance if it is the run's own first session, or if its calendar month
differs from the previous session's calendar month (and, for quarterly, that month is January, April,
July, or October). The comparison looks only backwards, at the session already consumed, so the
calendar is decidable at the close of the deciding session — a month-*end* rule is not, because
knowing that today is the last session of the month requires knowing that tomorrow is in the next
one. See G2-CONFLICT-8.

Measured over the run span of §6:

| Frequency | Scheduled rebalances | First three | Last two |
|---|---|---|---|
| MONTHLY | 157 | 2008-07-28, 2008-08-01, 2008-09-02 | 2021-06-01, 2021-07-01 |
| QUARTERLY | 53 | 2008-07-28, 2008-10-01, 2009-01-02 | 2021-04-01, 2021-07-01 |

The first entry of each list is the inception rebalance, which establishes the initial book and
closes nothing.

---

## 6. Window, run span, and the guard

**Authorized window: development only, 1993-01-29 → 2021-07-31.** Nothing in this stage reads
2021-08-01 or later. The last actual exchange session inside the window is 2021-07-30; 2021-07-31 is
a Saturday.

All eighteen variants share one run span:

| Field | Value |
|---|---|
| Run start | 2008-07-28 (Monday) |
| Run end | 2021-07-30 |
| Run sessions | 3276 |
| Binding member | VEA, inception 2007-07-26 |
| Members with no bar at run start | none |
| Members ending before run end | none |
| Development union sessions | 7178 |

The start is the first session `S` for which `S` shifted back twelve months is on or after the latest
inception in the universe. That is a property of the *grid*, not of any variant: a 3-month variant
could begin earlier, and letting it would mean the eighteen variants were measured over different
periods and their returns were not comparable — which would corrupt S3-C7, whose whole content is a
comparison of neighbouring variants' returns. One start for all eighteen costs the short-lookback
variants some history and buys comparability, and the choice is frozen here rather than made once a
return is visible.

**Enforcement.** `stockedge100.strategies.g2_window_guard` implements exactly the three behaviours
sealed in `STAGE_1_G2_PARTITION_LOCK.md` §4: it asserts the window handed to a run ends on or before
2021-07-31; it asserts that no `PriceSeries` loaded for a run contains a session after 2021-07-31,
by inspecting the loaded bars rather than trusting the loader; and it raises on any attempt to
construct a Generation 2 research window intersecting either prohibited period, 2024-08-01 →
2026-07-31 or 2026-08-01 → 2028-07-31. It is covered by tests that fail if it is removed or
weakened, whose names and counts are recorded in the Stage 3 (Generation 2) test summary.

---

## 7. Execution

| Field | Value |
|---|---|
| Decision point | Close of the scheduled rebalance session `t` |
| Earliest fill | Open of session `t+1` |
| Fill reference price | Open |
| Entry | Rotate into the current top-k at the next session's open |
| Exit | Sold when it drops out of the top-k at a scheduled rebalance |
| Discretionary exits | None between rebalances |
| Order sequencing | All SELLs before all BUYs |

There is **no same-close execution**: the close that produces a ranking never fills an order derived
from it.

`RotationEngine._execute` re-sorts the session's orders by `(0 if SELL else 1, symbol, order_id)`.
The base engine sorts by `(symbol, side, order_id)`, which for a one-position portfolio was
immaterial and for a rotation is not: a sell of `XLU` would otherwise execute after a buy of `AGG`,
and the buy would be sized against cash the sell had not yet released. Recorded as G2-CONFLICT-14
together with the open-marking change of §4.

**T+1 settlement is not modelled**, inherited unchanged from Generation 1's engine and disclosed
rather than repaired. Proceeds from a same-session sell are available to a same-session buy. In a
cash account this is optimistic. It is disclosed as a limitation of the Generation 1 engine that
Generation 2 does not fix, because fixing it would be a cost-model change and the operating
instruction puts the cost model out of scope.

---

## 8. The grid — all 18 variants, declared before any is run

Variant id format `SE100-G2-S3-C1-ROTATION-L{lookback:02d}-K{k}-{FREQUENCY}`. The lookback is
zero-padded so that lexicographic order over variant ids equals numeric order over lookbacks, which
matters because the third tiebreak of §9 is lexicographic.

| # | Variant id | Lookback | k | Frequency | Weight/position | Target gross | Rebalances |
|---|---|---|---|---|---|---|---|
| 1 | `SE100-G2-S3-C1-ROTATION-L03-K1-MONTHLY` | 3 | 1 | MONTHLY | 0.500000000 | 0.500000000 | 157 |
| 2 | `SE100-G2-S3-C1-ROTATION-L03-K1-QUARTERLY` | 3 | 1 | QUARTERLY | 0.500000000 | 0.500000000 | 53 |
| 3 | `SE100-G2-S3-C1-ROTATION-L03-K2-MONTHLY` | 3 | 2 | MONTHLY | 0.475000000 | 0.950000000 | 157 |
| 4 | `SE100-G2-S3-C1-ROTATION-L03-K2-QUARTERLY` | 3 | 2 | QUARTERLY | 0.475000000 | 0.950000000 | 53 |
| 5 | `SE100-G2-S3-C1-ROTATION-L03-K3-MONTHLY` | 3 | 3 | MONTHLY | 0.316666666 | 0.949999998 | 157 |
| 6 | `SE100-G2-S3-C1-ROTATION-L03-K3-QUARTERLY` | 3 | 3 | QUARTERLY | 0.316666666 | 0.949999998 | 53 |
| 7 | `SE100-G2-S3-C1-ROTATION-L06-K1-MONTHLY` | 6 | 1 | MONTHLY | 0.500000000 | 0.500000000 | 157 |
| 8 | `SE100-G2-S3-C1-ROTATION-L06-K1-QUARTERLY` | 6 | 1 | QUARTERLY | 0.500000000 | 0.500000000 | 53 |
| 9 | `SE100-G2-S3-C1-ROTATION-L06-K2-MONTHLY` | 6 | 2 | MONTHLY | 0.475000000 | 0.950000000 | 157 |
| 10 | `SE100-G2-S3-C1-ROTATION-L06-K2-QUARTERLY` | 6 | 2 | QUARTERLY | 0.475000000 | 0.950000000 | 53 |
| 11 | `SE100-G2-S3-C1-ROTATION-L06-K3-MONTHLY` | 6 | 3 | MONTHLY | 0.316666666 | 0.949999998 | 157 |
| 12 | `SE100-G2-S3-C1-ROTATION-L06-K3-QUARTERLY` | 6 | 3 | QUARTERLY | 0.316666666 | 0.949999998 | 53 |
| 13 | `SE100-G2-S3-C1-ROTATION-L12-K1-MONTHLY` | 12 | 1 | MONTHLY | 0.500000000 | 0.500000000 | 157 |
| 14 | `SE100-G2-S3-C1-ROTATION-L12-K1-QUARTERLY` | 12 | 1 | QUARTERLY | 0.500000000 | 0.500000000 | 53 |
| 15 | `SE100-G2-S3-C1-ROTATION-L12-K2-MONTHLY` | 12 | 2 | MONTHLY | 0.475000000 | 0.950000000 | 157 |
| 16 | `SE100-G2-S3-C1-ROTATION-L12-K2-QUARTERLY` | 12 | 2 | QUARTERLY | 0.475000000 | 0.950000000 | 53 |
| 17 | `SE100-G2-S3-C1-ROTATION-L12-K3-MONTHLY` | 12 | 3 | MONTHLY | 0.316666666 | 0.949999998 | 157 |
| 18 | `SE100-G2-S3-C1-ROTATION-L12-K3-QUARTERLY` | 12 | 3 | QUARTERLY | 0.316666666 | 0.949999998 | 53 |

**No expansion.** 3 × 3 × 2 = 18 is the whole grid. No nineteenth variant, no re-run with a shifted
axis, and no "one more lookback" is authorized by this document under any result.

**Multiplicity.** Eighteen parameterisations are searched over the development window. That is a real
multiple-comparisons cost. It is bounded in advance by declaring the grid in full here, by selecting
the representative with a rule that cannot see a return (§9), and by evaluating Gate 3 on that one
representative rather than on whichever of the eighteen looks best (§10).

---

## 9. Representative selection rule — frozen, and blind to returns

Applied mechanically after all 36 runs complete, in this order:

1. **Zero research-shutdown events**, counted across *both* runs of the variant. Any variant with a
   shutdown in its base run, its stress run, or both is eliminated.
2. **Lowest turnover** among survivors, where turnover is the total number of fills across both runs.
3. **Lexicographic variant id**, if step 2 still ties.

The shutdown trip-wire is the same mechanism Generation 1 used: constitution §5.1, 15% below the
running high-water mark, action `LIQUIDATE_AT_NEXT_OPEN_AND_BLOCK_ENTRIES`, at most once per run. A
variant's shutdown count is therefore in {0, 1, 2}.

Two readings of "zero research-shutdown events" were available — base run only, or both runs. **Both
runs** is adopted: it is the more restrictive, it eliminates more variants, and it is equally blind
to returns. A variant that survives its base costs and dies under the sealed 2× stress assumption has
told us something about its fragility, and the looser reading would discard that.

Turnover is measured as the **count of fills**, not gross notional. Gross notional is a currency
quantity that moves with the equity curve, and a variant that compounded further would post a higher
notional for the same trading behaviour — which would smuggle performance into a rule whose entire
purpose is to exclude it. Fill count has no such coupling. Recorded as G2-CONFLICT-13.

**Nothing about returns enters the selection.** Return, drawdown, profit factor, Sharpe, and trade
P&L are recorded for all 36 runs for the record, and none of them is an input to which variant is
chosen. The selection function is given only shutdown counts, fill counts, and variant ids; a
permutation test in the test suite asserts that permuting every return figure leaves the selection
unchanged.

**If every variant has ≥ 1 shutdown**, no variant advances. The stage records
`FAIL — STAGE_3_G2_NO_CANDIDATE` and stops. The grid is not loosened, the rule is not relaxed, the
shutdown threshold is not raised, and no nineteenth variant is added.

**If a representative is selected and then fails Gate 3**, the stage also records
`FAIL — STAGE_3_G2_NO_CANDIDATE`. The runner-up is **not** promoted. Promoting it would make the
selection rule a first attempt rather than a rule, and would let the gate result choose the
parameterisation — which is the exact failure the rule exists to prevent. Recorded as
G2-CONFLICT-11.

---

## 10. Gate 3 evaluation

Evaluated on the **representative's `#BASE` run only**, from `config/generation_2/g2_gate_criteria.json`
(`SE100-CFG-3102`). All seven conditions of the frozen gate apply, conjunctively; the sealed
five-threshold JSON companion and the seven-condition Markdown are both quoted verbatim in that file,
and the same S3-CONFLICT-1 resolution Generation 1 recorded is carried over — the Markdown is
authoritative and more restrictive.

Conditions S3-C1, S3-C2, S3-C3, S3-C4 and S3-C6 are Generation 1's, unchanged, evaluated by
Generation 1's own `stockedge100.strategies.gate`. Two are redefined because Generation 1's
measurement does not survive a portfolio holding more than one position:

- **S3-C5** — the best-trade-removed reconstruction. Generation 1's sequential
  `E[i] = E[i-1] + pnl[i]` is exact only because at most one position could be open. See
  G2-CONFLICT-6.
- **S3-C7** — the robustness neighbours. Generation 1's implementation demands exactly four; a
  three-axis grid yields three to five. See G2-CONFLICT-7.

The stress run gates nothing at Gate 3, exactly as in Generation 1, and is reported in full. The
seventeen non-selected variants are reported descriptively and are **never** used to reach a verdict;
the only place a non-selected variant's number enters a condition is S3-C7, which reads the *sign* of
a neighbour's return and nothing else.

Verdict tokens, sealed in `SE100-CFG-3102` before any result:

- `PASS — STAGE_3_G2_STRATEGY_ADMITTED_IN_DEVELOPMENT`
- `FAIL — STAGE_3_G2_NO_CANDIDATE`

Neither string exists in any Generation 1 artifact, and the second is not the negation of the
constitution's own `STRATEGY_REJECTED_IN_DEVELOPMENT`. See G2-CONFLICT-12.

---

## 11. Structural consequences, declared before running

Three consequences of the choices above are visible now, from the calendar alone, without any price.
They are written down here so that meeting or missing them later is a measurement and not a surprise.

**SC-1 — the quarterly variants may not reach 30 closed trades.** A quarterly variant has 53
scheduled rebalances, of which the first only opens positions, so at most 52 can close anything. At
k=1 that caps closed trades at 52 and reaching the sealed floor of 30 requires the top-ranked symbol
to change at 30 of those 52 rebalances. The binding risk is low turnover, not the calendar. The
30-trade floor is **not** lowered and the lower-frequency exception of the frozen gate text is **not**
invoked — that exception permits a *longer* evidence requirement, never a smaller count, so it could
not lower the floor even if invoked. A quarterly variant that falls short simply fails S3-C4.

**SC-2 — position sizes clear the minimum notional.** With starting equity of USD 100.00 and k=3, a
position is about USD 31.67 against a sealed `min_order_notional` of USD 1.00, so no entry is
structurally rejected at inception. Fractional shares are permitted, so no per-share price in the
universe makes a position unbuyable.

**SC-3 — k=1 is structurally half in cash.** At k=1 the 0.50 concentration ceiling binds before the
0.95 gross ceiling, so a k=1 variant holds 50% cash by construction and its return is roughly halved
relative to an unconstrained single-name version. This is declared, not corrected. Relaxing the
ceiling for k=1 would be a risk-architecture change made to improve a return. See G2-CONFLICT-9.

---

## 12. Contamination measurement — taken before this seal

The claim that this pre-registration precedes the strategy code is checked, not asserted. Measured
at authoring time, immediately before sealing:

| Predicate | Count |
|---|---|
| Generation 2 modules under `src/stockedge100/strategies/` | 0 |
| Generation 2 modules under `src/stockedge100/backtest/` | 0 |
| Generation 2 test modules under `tests/` | 0 |
| Generation 2 modules under `src/stockedge100/reporting/` | 2 |

The two existing modules are `src/stockedge100/reporting/g2_partition_lock.py`, the Stage 1 sealer,
and `src/stockedge100/reporting/g2_rotation_preregistration.py`, this document's own sealer.
**That is a real narrowing of the predicate and is recorded as such**, exactly as Generation 1
recorded the same exclusion: a sealing program is not a strategy, but "zero Generation 2 modules"
would have been false and the honest count is stated instead of the convenient one. Neither reads a
price field in any window and neither produces a strategy output; the Stage 1 sealer's
`sessions_only()` function is the mechanism, and this document's sealer touches the acquired data not
at all.

The sealer for this document re-measures all four counts at build time and refuses to write if the
first three are not zero.

---

## 13. Windows referenced, and the mandated disclosure

| Window | Range | State under this document |
|---|---|---|
| Development | 1993-01-29 → 2021-07-31 | **OPEN** — the only window this stage reads |
| Validation | 2021-08-01 → 2024-07-31 | **LOCKED** — not read here |
| Generation 1 holdout | 2024-08-01 → 2026-07-31 | **SPENT AND PROHIBITED** — never read again |
| Generation 2 holdout | 2026-08-01 → 2028-07-31 | **SEALED** — not readable before 2028-07-31 passes |

This document references the validation window, so the disclosure mandated by the Generation 2
operating instruction and sealed in `STAGE_1_G2_PARTITION_LOCK.md` §2 is reproduced here verbatim:

> Generation 2's validation window (2021-08-01 → 2024-07-31) overlaps the exact period Generation 1
> used for its own Gate 4 validation read. The researcher therefore already knows, from Generation
> 1's published report, approximately how SPY (and by extension the broad market) behaved in this
> window — including its Sharpe ratio (≈0.20), total return (≈2.15%), and fold-by-fold sign pattern
> (7 of 12 positive). Generation 2 tests a different hypothesis (cross-sectional multi-asset
> selection vs. single-symbol mean reversion) over the same calendar period, which limits but does
> not eliminate the concern. This is a real multiplicity cost, disclosed and not minimized, and it is
> the reason Generation 2's validation result alone — without a clean holdout confirmation — cannot
> be treated as sufficient evidence of an edge.

Nothing in this stage reads the validation window. The disclosure is reproduced because the window is
named, not because it is used.

---

## 14. Conflicts and interpretations

Nine conflicts are recorded here. G2-CONFLICT-1 through -5 are in the charter and are not repeated.

**G2-CONFLICT-6 — S3-C5's reconstruction basis does not survive k > 1.**
Generation 1's `condition_5` reconstructs equity as `E[i] = E[i-1] + pnl[i]` over closed trades in
exit order, and the sealed criteria state plainly that this is exact "because the sealed cost model
permits at most one open risky position, trades are sequential and non-overlapping". Generation 2
holds up to three at once. Two trades opened at the same rebalance would be charged against different
equity bases purely because of the order they closed in, and the second would be credited with a base
the first had already inflated.
*Resolution:* the per-trade multiple is taken against the equity that existed when the trade was
entered — `r[i] = 1 + pnl[i] / E_entry[i]`, with `E_entry[i]` the account equity at the close of the
session immediately preceding that trade's entry fill, or starting equity if there is none. Both of
Generation 1's removals are kept (largest multiple, largest P&L) and both must still leave a positive
value. The equity-curve total return is reported alongside the reconstruction with the gap stated;
they are not expected to agree and no attempt is made to force them to. Generation 1's module is not
modified; Generation 2 evaluates this condition in `stockedge100.strategies.g2_gate`.

**G2-CONFLICT-7 — S3-C7 demands exactly four neighbours; the grid yields three to five.**
`condition_7` raises `ConfigViolation` on any neighbour count other than four, because Generation 1's
protocol declared four per candidate.
*Resolution:* Generation 2 defines neighbours structurally — every variant differing from the
representative in exactly one axis by exactly one step, on the orderings lookback 3 < 6 < 12, k
1 < 2 < 3, frequency MONTHLY < QUARTERLY. The count is 3 at a double corner, 5 when interior on both
the lookback and k axes, 4 otherwise, and it is a function of the representative's grid position
rather than a choice. Every neighbour is already a declared grid member and is already run, so the
condition creates no new run and no new parameterisation. The same sign-stability predicate applies,
including "zero matches nothing".

**G2-CONFLICT-8 — a month-end rebalance calendar is not backward-decidable.**
The natural phrasing of "monthly rebalance" is the last session of the month, which cannot be
identified at that session's close without reading the next one.
*Resolution:* the calendar is first-session-of-month, detected by comparing the current session's
month with the previous session's. The inception rebalance is added explicitly so the run is not
unallocated until the first month boundary.

**G2-CONFLICT-9 — equal weighting and the 50% ceiling disagree at k=1.**
Equal weight across k positions subject to a 0.95 gross ceiling gives 0.95 at k=1; the 0.50
concentration ceiling gives 0.50.
*Resolution:* the ceiling binds, because it is the more restrictive constraint and the operating
instruction names it as a requirement. The consequence — k=1 variants hold 50% cash by construction —
is declared as SC-3 and is not corrected.

**G2-CONFLICT-10 — "equal weight" does not say when.**
Equal weight could mean equal at entry, or rebalanced to equal at every scheduled date.
*Resolution:* equal at entry. Continuing holdings are not trimmed or topped up. This is chosen before
any turnover figure exists, because the two readings differ in turnover and turnover is the second
step of the selection rule.

**G2-CONFLICT-11 — a selected representative that fails the gate.**
The operating instruction names a `FAIL` token for the case where every variant had a shutdown, and
does not name one for a representative that passes selection and fails Gate 3.
*Resolution:* both paths emit `FAIL — STAGE_3_G2_NO_CANDIDATE`, and the report states which path was
taken. The runner-up is never promoted.

**G2-CONFLICT-12 — the verdict tokens exist in no Generation 1 artifact.**
`STAGE_3_G2_STRATEGY_ADMITTED_IN_DEVELOPMENT` and `STAGE_3_G2_NO_CANDIDATE` appear only in the
operating instruction, and the project rule is that a token comes from disk. The fail token is also
not the negation of the constitution's frozen `STRATEGY_REJECTED_IN_DEVELOPMENT`; it names the absence
of a candidate rather than the rejection of one.
*Resolution:* `config/generation_2/g2_gate_criteria.json` seals both tokens before any Generation 2
strategy module exists and before any variant is run, so neither can be shaped by an outcome, and it
records the constitutional equivalent alongside. No sealed Generation 1 derivation is edited.

**G2-CONFLICT-13 — turnover has two plausible measures.**
Fill count and gross traded notional both describe turnover.
*Resolution:* fill count. Gross notional scales with the equity curve, so a variant that compounded
further would post a larger notional for identical trading behaviour, which would make the tiebreak
partly a performance ranking.

**G2-CONFLICT-14 — the base engine's buy path is wrong for a multi-position book.**
Two defects, both invisible at k=1. `BacktestEngine._execute_buy` marks already-held positions with
`_mark(symbol, session)`, which returns that session's **close**, while filling at that session's
**open** — same-session close information used at the open. And `_schedule` sorts orders by
`(symbol, side, order_id)`, so a sell can execute after a buy that needed its proceeds.
*Resolution:* `RotationEngine` marks at the open using its own helper — deliberately not `_mark`,
whose `self._last_close[symbol] = bar.close` side effect must not fire — and re-sorts to
`(0 if SELL else 1, symbol, order_id)`. The base engine is not modified and Generation 1's results
are untouched.

**G2-CONFLICT-15 — Gate 3's disjunction across candidates, with one candidate.**
Generation 1 evaluated Gate 3 as a disjunction across six independently declared candidates.
Generation 2 declares one candidate whose parameterisation a frozen rule fixes.
*Resolution:* the disjunction is over a set of size one. Evaluating all eighteen variants and passing
if any passes would make the selection rule decorative and would be precisely the multiplicity abuse
it exists to prevent.

---

## 15. Adversarial tests required before any variant is trusted

Multi-position support is new engine capability, not a strategy change. It is not trusted until tests
exist that fail if the engine:

1. holds more than k positions at once;
2. exceeds the 0.95 gross exposure ceiling across the combined k positions;
3. exceeds the 0.50 single-position concentration ceiling;
4. buys or sells at the close that generated the ranking signal;
5. uses a bar dated after the decision session in that session's ranking;
6. produces different results from identical inputs on a clean rerun.

Five further tests are required by this document:

7. the window guard rejects a research window ending after 2021-07-31;
8. the window guard rejects a `PriceSeries` containing a session after 2021-07-31, detected from the
   loaded bars rather than from the loader's arguments;
9. the window guard raises on a window intersecting either prohibited holdout period;
10. permuting every return figure across the 36 runs leaves the selected representative unchanged;
11. the Generation 2 cost derivation refuses to build a `CostModel` when the difference set against
    the sealed Generation 1 model is anything other than the single declared JSON pointer.

Counts and names go into the Stage 3 (Generation 2) test summary. The Stage 0 regression floor is not
reduced: no existing test is weakened, skipped, or deleted to let any of this pass.

---

## 16. Binding rules

1. This grid is complete at eighteen variants. No variant is added, removed, or re-parameterised
   under any result.
2. The representative-selection rule is applied exactly as written in §9, on shutdown counts, fill
   counts, and variant ids alone.
3. Gate 3 is evaluated on the representative's base run only. No other variant is evaluated against
   the gate.
4. No parameter, threshold, symbol, weight, or rule may be chosen using any value inside the
   validation window or either holdout window.
5. A defect discovered after this seal is reported and its effect disclosed; this document is not
   rewritten to accommodate it.
6. Stage 4 validation for Generation 2 requires a separate, explicitly authorized session. Nothing in
   this document, and no result produced under it, authorizes one.
7. `live_trading_authorized` remains `false`. This document authorizes no order, no broker
   connection, no credential read, and no scheduling of either.
