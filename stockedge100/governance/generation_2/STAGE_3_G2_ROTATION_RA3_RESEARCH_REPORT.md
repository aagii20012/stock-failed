# Stage 3 (Generation 2, Attempt 3) — rotation under a reverted ladder and a stability selection rule, development research report

| Field | Value |
|---|---|
| Document id | `SE100-GOV-2008` |
| Project | StockEdge100 |
| Generation | 2 |
| Generation id | `SE100-GEN2-7394207c543401e2` |
| Stage | 3 — **Attempt 3** |
| Gate | 3 — development admissibility |
| Session type | Development research, single stage, single verdict |
| Candidate | `SE100-G2-S3-C3-ROTATION-RA3` (candidate index 3) |
| Governing document | `SE100-GOV-0001` (constitution, FROZEN) §§3, 4, 5.1, 6, 7, 9 gate 3, 10, 11, 19 |
| Charter | [STAGE_10_GENERATION_2_CHARTER.md](STAGE_10_GENERATION_2_CHARTER.md) (`SE100-GOV-2001`) |
| Partition lock | [STAGE_1_G2_PARTITION_LOCK.md](STAGE_1_G2_PARTITION_LOCK.md) (`SE100-GOV-2002`) |
| Attempt 1 | [STAGE_3_G2_ROTATION_RESEARCH_REPORT.md](STAGE_3_G2_ROTATION_RESEARCH_REPORT.md) (`SE100-GOV-2004`) — **CLOSED, READ-ONLY** |
| Attempt 2 | [STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md](STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md) (`SE100-GOV-2006`) — **CLOSED, READ-ONLY** |
| Pre-registration | [STAGE_3_G2_ROTATION_RA3_PROTOCOL.md](STAGE_3_G2_ROTATION_RA3_PROTOCOL.md) (`SE100-GOV-2007`, sealed before any Attempt 3 code existed) |
| Protocol config | `config/generation_2/g2_rotation_ra3_protocol.json` (`SE100-CFG-3105`) |
| Gate criteria | `config/generation_2/g2_gate_criteria_ra3.json` (`SE100-CFG-3106`) |
| Evidence | `reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json` (`SE100-EVID-3103`) |
| Development window read | 1993-01-29 → 2021-07-31 (run span 2008-07-28 → 2021-07-30, 3276 sessions) |
| Latest session loaded | 2021-07-30 |
| Validation window | 2021-08-01 → 2024-07-31 — **not read** |
| Generation 1 holdout | 2024-08-01 → 2026-07-31 — **spent and prohibited, not read** |
| Generation 2 holdout | 2026-08-01 → 2028-07-31 — **sealed; does not exist in calendar time** |
| Authored (UTC) | 2026-08-19T09:52:10Z |
| Verdict | `FAIL — STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE` |
| Gate 3 | **NOT PASSED** |
| `live_trading_authorized` | `false` |

This report carries no `run_id` and no `repo_state_id`, for the reason Attempt 1 gave and Attempt 2
repeated: a tree digest quoted inside a member of the tree it describes is self-invalidating in the
general case. On this attempt's own subtree the pattern depth means `governance/generation_2/*.md` is
not in fact covered by `repo_state_id` — `governance/*` is single-level — so the self-invalidation
would not actually occur here. The convention is kept anyway, because a reader should not have to
reason about pattern depth to know whether a quoted digest is honest. Both values are in the decision
record and in the `runs/` record, which is where a reader should look for them.

The 64-hex values this report does quote are file digests and the universe identity digest. None is a
tree digest and none is this file's own digest. Every one was extracted from disk by the renderer that
produced this document; none was transcribed by hand.

---

## 1. What this session did

Eighteen rotation variants — lookback ∈ {3, 6, 12} months × top-k ∈ {1, 2, 3} × rebalance ∈
{monthly, quarterly} — were run twice each, once under the sealed base cost model and once under the
stressed one, over 2008-07-28 → 2021-07-30 (3276 sessions). That is 36 runs. The grid, the
signal, the universe, the calendar, the cost model and the gate thresholds are Attempt 2's, unchanged.
Two things changed, both disclosed before the run: the de-risk ladder lost one rung, and the
representative-selection rule was replaced.

Four findings, in the order they were established:

1. **The reverted ladder measurably loosened the throttle, and no variant breached the research
   shutdown.** Across the 36 runs the ladder descended 1008 times against
   Attempt 2's 1605, blocked 3719 recoveries
   against 6133, and held full sizing on
   53671 sessions against 36886. Every one of those statistics differs
   from Attempt 2's on at least 21 of the 36 runs and three of them on all
   36. Zero shutdown events were recorded, and the deepest maximum drawdown anywhere in the grid was
   14.36% against a 15% ceiling — so the declared cost of removing a rung (SC-8)
   did not materialise.
2. **Ordinary-market returns came back, but not because of the ladder.** The grid returned
   +1.48% to +53.41% on base with a median of +11.67%, and
   18 of 18 variants were positive. Attempt 2's grid, however, was *also*
   18 of 18 positive, with a higher best (+63.15% against
   +53.41%) and a similar median (+9.79% against
   +11.67%). What changed is *which* variant the selection rule picked, not what the
   grid earned. §12 states this plainly, because the sealed adaptation disclosure's reasoning is only
   partly borne out and the part that is not borne out is the part about returns.
3. **A representative exists, and it is not the grid's floor.** SE100-G2-SEL-2 selected
   `L03-K2-QUARTERLY` on a neighbourhood-instability score of 0.215471404 over
   4 neighbours, ahead of `L03-K1-QUARTERLY` at 0.215520012 — a margin of
   0.000048608. It ranks 11 of 18 by return. Attempt 2's rule, applied to
   this grid, would have selected `L12-K1-QUARTERLY` at +1.48%,
   which is this grid's *minimum*. The change of representative is attributable to SEL-2 and not to RA3.
4. **The gate failed on one condition, and it is a condition neither prior attempt failed alone.**
   6 of the seven Gate 3 conditions are MET on both runs. The sole failure is
   **S3-C6**, the concentration condition: 75.05% of the representative's gross profit
   came from its largest contributor on base and 97.72% on stress, against a ceiling of
   50.00%.

The verdict is `FAIL — STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE`, on the sealed second fail route —
`REPRESENTATIVE_FAILED_AT_LEAST_ONE_CONDITION` — not Attempt 1's no-representative route. Both routes
emit the same token by seal; the route is recorded separately in the decision record and here.

---

## 2. Why this attempt exists, and what it costs

Attempt 1 ran the rotation grid with no risk architecture. All eighteen variants breached the
constitutional research-shutdown drawdown ceiling — 36 of 36 runs, with
36 shutdown events — and no representative could be selected at all. Attempt 2
added a five-component risk architecture and every variant survived, but its representative-selection
rule preferred the variant that traded least, which on that grid was also that grid's worst-returning
variant, and the gate failed. This attempt was designed **after** both of those results were seen.

The constitution does not forbid an adaptation. It forbids a silent one. The sealed protocol therefore
carries a single paragraph of disclosure that must appear byte-identically wherever this attempt's
development result is referenced. It was substituted here mechanically from the sealed file, as a
single unbroken block, so that byte-identity is checkable by string comparison rather than asserted:

> This pre-registration was designed after both Attempt 1 and Attempt 2's development results were known. Attempt 1 (no risk architecture) failed via research-shutdown on all 18 variants, clustered around the 2008 financial crisis. Attempt 2 (RA2 risk architecture) survived every variant without a shutdown, but its representative — selected by a rule blind to return — earned approximately 0.4% over thirteen years, indicating the risk architecture suppressed ordinary-market returns as well as crisis losses. Attempt 3 makes two disclosed, evidence-informed changes: (1) a new representative-selection rule (SE100-G2-SEL-2) that screens for neighborhood stability across non-return risk-behavior statistics rather than raw turnover, and (2) a revised risk architecture (RA3) that removes a −5%-drawdown de-risk tier RA2 had added beyond Generation 1's own original architecture, on the reasoning that a 5%-from-peak dip is common in ordinary markets and is a plausible cause of RA2's near-constant throttling. Both changes were selected using only non-return diagnostics already on record — RA2's ladder-activation and combined-scalar statistics, and a retrospective (but not selection-informing) check of SEL-2 against Attempt 2's frozen data. No return figure from any prior attempt informed either change. This is nonetheless a third disclosed adaptation on the same hypothesis family, and cumulative multiplicity across all three attempts must be carried forward in any final assessment of this family.

The sealed carriage requirement states the enforcement:

> The sealer and the package builder both assert byte-equality of this string against the value in this file. A paraphrase is a failure, not a stylistic choice.

The five required carriers are the protocol Markdown, the protocol JSON, this report, the research JSON
and the evidence JSON. The decision record produced by the package builder is a sixth. The string is
1507 characters of UTF-8 and its SHA-256 is `ce1d6476f44562310fb059c5817645baa25477cc4f6168b414f3423834c8e925`; Attempt 2's equivalent
was 842 characters. It carries two non-ASCII characters that a reader diffing the attempts should
expect: U+2014 EM DASH, as every governance artifact in this tree does, and U+2212 MINUS SIGN in the
phrase naming the removed tier. No diagnostic script in this session printed the string; they compared
it and reported a boolean.

The sealed statement of what changed, in the protocol's own words:

> Exactly two things, and nothing else. (1) The de-risk ladder loses its 5-to-8 percent rung, reverting to the three-band spacing Generation 1's RA1-5 sealed before Attempt 1 was ever run. (2) The representative-selection rule changes from lowest turnover to SE100-G2-SEL-2, a neighbourhood-stability score over four risk-behaviour counters. The signal, the universe, the calendar, the grid, the cost model, the gate thresholds, the aggregate ceiling, the volatility target, the stop, the lockout, the throttle and the episode ledger are all held fixed. Because two things change rather than one, this attempt cannot by itself attribute an outcome to either. That is stated here, before the run, rather than discovered afterwards.

And the lineage statement carried forward unchanged from Attempt 2's protocol, describing the
architecture this attempt still runs minus one rung:

> Attempt 1 tested the rotation signal with no mechanism to reduce exposure before a research-shutdown breach: between scheduled rebalances it issued no orders at all. Attempt 2 holds the signal, the universe, the calendar, the grid, the cost model and the gate thresholds fixed and adds only risk architecture. Any difference in outcome is therefore attributable to the risk architecture rather than to a re-tuned signal - which is the only reason a second attempt on a contaminated window is worth running at all.

Two things changed rather than one, which means this attempt cannot attribute its outcome to either.
That was stated before the run and is restated in §17 and as `G2A3-CONFLICT-33`. It bounds the
*attribution*. It does not bound the multiplicity, which is now three adaptations on one hypothesis
family and is disclosed as such.

---

## 3. What was sealed before any code existed

| Field | Value |
|---|---|
| Seal run id | `SE100-R-20260816T072617Z` |
| Sealed (UTC) | 2026-08-16T07:26:17Z |
| `repo_state_id` at seal | `30982ba8abb718385ddb904d94423844811f43ed2e3e00c62b6bbd2d44c7a377` |
| Protocol Markdown | `STAGE_3_G2_ROTATION_RA3_PROTOCOL.md` — `37ed2ca25d30a4f14736f573053eb50c883c79f7c9ab0b62c181fddeb31f7a7d` |
| Protocol JSON | `STAGE_3_G2_ROTATION_RA3_PROTOCOL.json` — `c938dcd8dd3c7099c9db6145f92165d2758796f07a90be4804c5137e47a07e34` |
| Protocol config | `config/generation_2/g2_rotation_ra3_protocol.json` — `e9e8a8bc58c0ddb04b2b6c702d543b998c2d0a31487986a61e0a28509b5fbd1d` |
| Gate criteria | `config/generation_2/g2_gate_criteria_ra3.json` — `4fa3103862786e889668221ad7009fe4ead5cac999bc0d2f7d1aa0135cbb0ac0` |
| Cost model | `config/generation_2/g2_cost_model.json` — `b9491485b9560b948ec83d3eb86ee4946c1e83b128a368b71473d14ad0f73650` |
| Partition lock JSON | `STAGE_1_G2_PARTITION_LOCK.json` — `e17ea82c499d51cf23fc9986e7231dce6388f8a3c7394d3dd3c0e3d27fbacbe7` |
| Charter | `STAGE_10_GENERATION_2_CHARTER.md` — `865a2feffe683e0baf71f1ab976e286fbb2d003109ab47cfaffc1fe6a63dbc90` |

Every digest in that table was recomputed from the named file by the renderer that wrote this document
and compared against the value the sealer recorded. A mismatch would have refused the render.

**How "before any code" is measured.** Attempt 1's predicate was path-based: it refused to seal if any
module basename under `strategies/` or `backtest/` contained `g2_`. That test was correct when
`strategies/` held no Generation 2 code, and by Attempt 3 it is vacuous — Attempt 1's own modules live
there and are supposed to. Attempt 2 replaced it with a content-based predicate and Attempt 3 carries
that form:

> No .py file under src/stockedge100 or tests contains the string SE100-G2-S3-C3-ROTATION-RA3 at seal time.

That is a statement about the contents of every `.py` file in the tree at seal time, not about a list
of filenames, and it is re-checkable after the fact against the sealed `repo_state_id`. The sealing
program is itself a `.py` file under `src/` and would falsify the predicate if it named the candidate id
as a literal; it loads the id from the protocol config at run time instead, and the protocol discloses
that indirection rather than leaving it to be found.

The predicate is paired with an immutability check, which is the half that matters here. Every one of
the **17** Attempt 1 and Attempt 2 modules was re-hashed at seal time against the digest
its own run record recorded, and again after this session's work. None moved. The count is read from the
seal rather than typed, so a silently shortened list fails loudly; the operating instruction for this
attempt implies nine modules and the sealed figure is 17, which is
`G2A3-CONFLICT-34`.

Everything the gate would later depend on was fixed at that moment: the eighteen variant ids and their
enumeration order, the three RA3 ladder bands and their scalars, the four other RA3 constants, the
six-field selection input, the four selection steps, the seven gate conditions and their thresholds, the
two verdict tokens, and the run span the runner would be required to reproduce.

---

## 4. Window, bound and run span

The development bound is 2021-07-31 and the last session inside it is 2021-07-30. The window guard
is `stockedge100.strategies.g2_window_guard`, imported unmodified from Attempt 1 rather than
re-derived: every series is truncated while parsing, not after, and the bound is re-asserted after
loading. A second derivation of the same bound is a second place for it to be wrong.

The run span is not merely quoted from Attempt 2's protocol. The Attempt 3 runner **refuses to run** if
any value differs from the sealed one, recomputes all of it from the loaded series, and writes the
recomputation to `reports/stage3_g2_attempt3/run_span_recheck.json`. The recheck recorded zero
differences.

| Field | Value |
|---|---|
| Development window | 1993-01-29 → 2021-07-31 |
| Run span | 2008-07-28 → 2021-07-30 |
| Sessions in the run | 3276 |
| Development union sessions | 7178 |
| Binding symbol | `VEA` (inception 2007-07-26) |

The run starts twelve months after the binding symbol's inception because the longest lookback in the
grid is twelve months and a ranking signal may not be computed from a partial history. The scheduled
rebalance counts on this session list are 157 monthly and 53 quarterly, both
recomputed by the runner and both equal to the sealed values.

No session at or after 2021-08-01 was read by any module in this session. The three prohibited windows
are recorded in the evidence with explicit read-flags, all false.

---

## 5. Universe

| Field | Value |
|---|---|
| Source | `governance/STAGE_1_UNIVERSE.json` |
| Universe version | `SE100-U1-d4917c2f7f1cd834` |
| Identity digest | `d4917c2f7f1cd8344728a39165929b352766fbe7193b3c64e71a971749dcbf38` |
| Members | 34 |
| Members eligible at run start | 34 of 34 |
| Members dropped mid-run | 0 |

Membership is Stage 1's and is frozen. Generation 2 re-checks eligibility on development data only and
never adds, drops or substitutes a symbol. `AAPL` is present in the data tree as a Stage 2
single-symbol fixture; it has never been a member of the eligible universe and was never ranked here.

---

## 6. Risk architecture RA3

RA3 is RA2 with one band deleted. Four of its five components are the same objects, inherited by
import rather than reimplemented.

| Component | Name | Value | Provenance |
|---|---|---|---|
| `RA3-1` | aggregate exposure ceiling | `0.50` of equity | RA2-1 unchanged |
| `RA3-2` | portfolio volatility target | `0.10` annualized, measured on the equity curve | RA2-2 unchanged, itself Generation 1's RA1 |
| `RA3-3` | per-position stop | `0.08` from the all-in cost basis, exit at the next open | RA2-3 unchanged, itself Generation 1's RA1 |
| `RA3-4` | de-risk ladder | band 0: drawdown [0.00, 0.08) → 1.00; band 1: [0.08, 0.10) → 0.50; band 2: [0.10, ∞) → 0.25, measured from the equity high-water mark | **the one change** — Generation 1's RA1-5 spacing restored |
| `RA3-5` | re-entry lockout | `10` trading sessions, armed by any downward transition | RA2-5 unchanged |

The single difference, in the sealed protocol's own words:

> RA2-4's band 1 (0.05 <= dd < 0.08, scalar 0.75) is deleted and band 0 is extended to 0.08. No other threshold, scalar, formula, order of operations or code path differs. The engine subclasses Attempt 2's and overrides the band table and the state derived from it; see G2A3-CONFLICT-31.

**The change removes a degree of freedom rather than adding one.** RA2's ladder had four bands, and
Attempt 2's own protocol recorded that only its band 1 — the `[0.05, 0.08)` rung at scalar `0.75` — was
new relative to Generation 1's sealed RA1-5. Deleting it leaves:

> RA3-4 is not a new ladder. It is Generation 1's sealed RA1-5 ladder, restored. SE100-CFG-3103's own provenance field records that three of RA2-4's four bands reproduce the RA1-5 f_cap values exactly and that 'only band 1 is new'. Deleting band 1 therefore leaves an architecture with no post-Attempt-1 degree of freedom in it at all.

Expressed as absolute ceilings, which is the form that makes the identity checkable:

> Expressed as absolute aggregate ceilings (f_base * ladder scalar), RA3-4's three bands give 0.500000000 for dd < 0.08, 0.250000000 for 0.08 <= dd < 0.10 and 0.125000000 for dd >= 0.10. Those are the three RA1-5 f_cap values SE100-CFG-3103 names, in the same order, at the same thresholds.

The evidence records `ladders_are_identical: true` against Generation 1's RA1-5, and
records the deleted tier explicitly as the triple (0.05, 0.08, 0.75) — one threshold and one scalar,
which the protocol counts as One threshold (0.05) and one scalar (0.75) — precisely the pair SE100-CFG-3103 identified as 'the single degree of freedom it adds'..

The combined scalar is unchanged in form:

> `f(t) = f_vol(t) * f_ladder(t), quantized to nine decimal places, ROUND_DOWN.`

It applies to the entry budget at the fill open and to the aggregate ceiling at every session. It does
**not** apply to the per-position stop, which is an absolute condition on price, or to the
constitutional research shutdown, which belongs to the engine and was not modified.

The ladder's asymmetry is the mechanism and is unchanged: descent is immediate and to the full computed
band, recovery is at most one band per session and only after the lockout has elapsed. Under RA3 a
recovery from the deepest band to full sizing needs at least two sessions after expiry; under RA2 it
needed three. Band boundaries remain closed below and open above, so a drawdown of exactly 0.08 is
band 1.

**What would have falsified the reasoning.** The protocol declared this before the run:

> If RA3's ladder-descent counts are close to RA2's, the 5-percent rung was not the cause of the near-constant throttling and the change was aimed at the wrong mechanism. The descent counts are therefore reported per variant against Attempt 2's, and the comparison is required by the operating instruction rather than optional.

The comparison it demands is §16's second table. The descent counts are not close: 1008 against 1605.
The 5% rung was doing most of the throttling, which is what the change assumed.

---

## 7. Modules and adversarial tests

Eight new modules under `src/`, none of them a modification of anything that existed:

| Module | Role |
|---|---|
| `strategies/g2_rotation_ra3.py` | the candidate: ranking, scheduling, order requests |
| `strategies/g2_selection_v2.py` | SE100-G2-SEL-2 and the frozen `SelectionInputV2` |
| `strategies/g2_gate_ra3.py` | Gate 3 condition evaluation |
| `strategies/g2_runner_ra3.py` | the 36-run driver, span recheck, statistics collection |
| `backtest/g2_engine_ra3.py` | `RotationEngineRA3`, a subclass of Attempt 2's engine overriding the band table |
| `reporting/g2_rotation_ra3_preregistration.py` | the sealer |
| `reporting/g2_stage3_attempt3_evidence.py` | the evidence assembler |
| `reporting/g2_stage3_attempt3_package.py` | the decision-package builder |

Two new test files carry the thirteen adversarial requirements the protocol declared before the tests
existed — `AT-A` through `AT-M`. Each section opens with a **control** that a vacuous check would fail
and closes with an **injected defect** that must be caught, which is the discipline Attempt 2
established and this attempt inherits.

| Id | Requirement, abbreviated |
|---|---|
| `AT-A` | gross exposure never exceeds 50% of equity, checked after every fill and not only at session close |
| `AT-B` | volatility scaling reduces size against a hand-built high-volatility fixture with an independently computed expected scalar |
| `AT-C` | a stop breach exits at the **next** open, in full |
| `AT-D` | the ladder steps at the RA3 thresholds in both directions, including a 6% drawdown fixture asserting the ladder scalar is exactly 1 there — the single behavioural difference from RA2 |
| `AT-E` | the lockout blocks recovery for exactly the declared number of sessions |
| `AT-F` | determinism of trade, equity, ranking and risk-state digests |
| `AT-G` | the window guard still blocks 2021-08-01, exercised through the Attempt 3 loading path, asserting the module under test is the existing guard |
| `AT-H` | all 17 prior-attempt modules re-hash to their recorded digests |
| `AT-I` | `SelectionInputV2`'s field tuple equals the declared tuple, the import-time assertion fires when it does not, and no field name matches a performance vocabulary |
| `AT-J` | neighbour sets are correct at the grid edges: counts 3/4/5, partition 8/8/2, literal sets compared element by element, relation symmetric and closed over the grid |
| `AT-K` | SEL-2 is deterministic across two in-process computations and one serialisation round trip |
| `AT-L` | the loaded band table has exactly three bands, strictly decreasing scalars, no boundary below 0.08, and induced ceilings 0.500000000 / 0.250000000 / 0.125000000 |
| `AT-M` | the RA3 engine re-derives exactly the risk-dependent attributes Attempt 2's `__init__` assigns from `self.risk`, enforced by parsing that `__init__` |

`AT-M` is the reason `G2A3-CONFLICT-31` exists. Subclassing a closed module reads it without modifying
it, but a subclass that forgets to re-derive a cached attribute would silently run RA2's bands under
RA3's name. The test parses Attempt 2's `__init__` for the attributes assigned from `self.risk` and
asserts the subclass reassigns precisely that set — no more and no fewer.

---

## 8. Cost model

The cost model is `config/generation_2/g2_cost_model.json` (`b9491485b9560b948ec83d3eb86ee4946c1e83b128a368b71473d14ad0f73650`), sealed at Stage 1 of
Generation 2 and unchanged by any attempt. Each variant runs twice: once under the base parameters and
once under the stressed ones. A variant satisfies a gate condition only if **both** runs satisfy it;
the stressed model is not a sensitivity check that may be waived.

Costs, slippage and the minimum-notional throttle are modelled, not observed. No order was placed and
no broker was reachable from any module in this attempt.

---

## 9. The grid as executed

| Axis | Values |
|---|---|
| `lookback_months` | 3, 6, 12 |
| `top_k` | 1, 2, 3 |
| `rebalance_frequency` | `MONTHLY`, `QUARTERLY` |
| Variants | 18 |
| Runs per variant | 2 (`#BASE`, `#STRESS`) |
| Total runs | 36 |

The variant id format is `SE100-G2-S3-C3-ROTATION-RA3-L{lookback:02d}-K{k}-{FREQUENCY}`. The lookback is
zero-padded because SEL-2's final tiebreak is lexicographic and an unpadded `L12` would sort before
`L3`. Only the candidate index and the architecture segment differ from Attempt 2's ids, so variant *n*
of Attempt 3 is the same parameterisation as variant *n* of Attempts 1 and 2 and the three grids are
comparable row by row. That is what makes §12's table legitimate.

The grid is complete at eighteen and was not widened. The RA3 constants are not axes:

> Every constant below is fixed and applied uniformly to all eighteen variants. Searching them alongside the rotation parameters would cross from a disclosed risk control into curve-fitting to 2008 and 2020 - the two episodes whose observation motivated this attempt in the first place. The grid remains exactly the eighteen rotation parameterisations of Attempt 1 and is not widened.

---

## 10. Representative selection: `SE100-G2-SEL-2`

The rule replaces Attempt 2's unnamed lowest-turnover rule, which selected
`L12-K1-QUARTERLY`. Four steps, frozen before any variant ran:

1. **Eligibility.** Eliminate any variant with one or more research-shutdown events in **either** run.
   Unchanged from Attempt 2.
2. **Lowest neighbourhood instability score.** For each surviving variant, take its immediate grid
   neighbours — the variants reachable by exactly one single-axis step — and score the mean pairwise
   dissimilarity `abs(a - b) / max(abs(a), abs(b), 1)` across the four quantities
   `fill_count`, `ladder_descents`, `lockout_arms`, `stops_filled`, summed over both runs. Prefer the
   lowest.
3. **Tiebreak:** lowest total fill count.
4. **Final tiebreak:** lexicographic variant id.

**It cannot read a return.** That is structural, not procedural:

> The scoring function accepts a frozen SelectionInputV2 dataclass whose fields are exactly (variant_id, shutdown_events, fill_count, ladder_descents, lockout_arms, stops_filled). No return, drawdown, profit factor, Sharpe, trade-count or equity figure can reach it, because there is no field to carry one.

> The module asserts at import that the dataclass's actual field tuple equals the declared SELECTION_V2_FIELD_NAMES, in order. A field added later fails the import rather than silently widening what the selector can see. This is the same mechanism SE100-CFG-3103 required of Attempt 2's SelectionInput, extended to six fields.

The neighbour relation, sealed:

> The immediate grid neighbours of a variant are the variants reachable by exactly one single-axis step: lookback one position up or down the ordered list [3, 6, 12], k one position up or down the ordered list [1, 2, 3], and the rebalance frequency flipped. Every other axis value is held equal.

> 3, 4 or 5. The frequency axis has two values, so it contributes exactly one neighbour to every variant with no edge case. The lookback and k axes have three ordered values each and contribute one neighbour at an end and two in the middle. A variant at an end of both ordered axes has 1+1+1 = 3; at an end of one of them, 1+2+1 = 4; at the middle of both, 2+2+1 = 5. Over the eighteen variants the partition is 8 with three neighbours, 8 with four, and 2 with five.

The operating instruction for this attempt described neighbourhoods of 2, 3 or 4 variants. The sealed
geometry on this grid gives 3, 4 or 5, and the representative has 4. The sealed
geometry governs; the instruction's counts are not repeated as fact anywhere in this package. That is
`G2A3-CONFLICT-27`.

**Why the rule changed.** The sealed reasoning, which is about the shape of the old rule and not about
any return it produced:

> Attempt 2's rule preferred the variant that traded least. On a grid where every variant survived the eligibility screen, 'traded least' selected the quarterly k=1 corner — the parameterisation that by construction takes the fewest decisions and holds the fewest positions. Lowest turnover is a defensible tiebreak among near-equals and a poor primary criterion on a grid with no ties, because it is monotone in a structural property of the axes rather than in anything about the strategy's behaviour. SEL-2 prefers a variant whose immediate neighbours behave like it does, which is a stability criterion rather than a corner-seeking one. Turnover is retained as the tiebreak.

**What was checked retrospectively, and what was not.**

> SEL-2 was checked against Attempt 2's frozen recorded statistics before being sealed, to confirm it computes and produces a total order on real data rather than only on fixtures.

> It did not compare the variant SEL-2 would have chosen in Attempt 2 against that variant's return, drawdown or profit factor, and no such comparison informed the rule. The adaptation disclosure states this as 'a retrospective (but not selection-informing) check'.

> A rule tested on the data of a prior attempt is not fully independent of it, however narrow the test. Saying so is cheaper than defending it later.

**No reselection.**

> The representative is selected once, before any gate condition is evaluated. It is not reselected, re-ranked or substituted for any reason.

A declared structural consequence that turned out to matter, `SC-7`:

> If RA3 turns out to engage rarely, SEL-2 degenerates toward a fill-count dispersion rule and is closer to Attempt 2's turnover rule than its description suggests. The per-quantity components are reported so this is visible in the evidence rather than inferred.

The per-quantity components are therefore in §14's neighbour table rather than left to be inferred.
On this grid the architecture engaged often enough that the score is not a pure fill-count rule, but
`fill_count` is visibly the largest of the four components for the representative.

---

## 11. Step 1: the eligibility screen

All eighteen variants recorded zero research-shutdown events across both runs. Eighteen variants
survived step 1 and the no-representative fail route was not taken. This is the first attempt in the
family where the screen eliminated nothing and a representative was chosen on the stability criterion
rather than by survival.

| Rank | Variant | Eligible | Shutdowns | Instability score | Fills (both runs) |
|---:|---|---|---:|---:|---:|
| 1 | `L03-K2-QUARTERLY` **(selected)** | `true` | 0 | 0.215471404 | 298 |
| 2 | `L03-K1-QUARTERLY` | `true` | 0 | 0.215520012 | 283 |
| 3 | `L12-K1-QUARTERLY` | `true` | 0 | 0.246609961 | 195 |
| 4 | `L06-K2-QUARTERLY` | `true` | 0 | 0.247419599 | 336 |
| 5 | `L06-K1-QUARTERLY` | `true` | 0 | 0.248621581 | 265 |
| 6 | `L06-K2-MONTHLY` | `true` | 0 | 0.274579406 | 658 |
| 7 | `L12-K2-QUARTERLY` | `true` | 0 | 0.285600694 | 254 |
| 8 | `L06-K3-MONTHLY` | `true` | 0 | 0.290149221 | 955 |
| 9 | `L06-K1-MONTHLY` | `true` | 0 | 0.291302167 | 454 |
| 10 | `L12-K1-MONTHLY` | `true` | 0 | 0.292941999 | 359 |
| 11 | `L03-K2-MONTHLY` | `true` | 0 | 0.299993984 | 801 |
| 12 | `L03-K1-MONTHLY` | `true` | 0 | 0.316981929 | 614 |
| 13 | `L12-K2-MONTHLY` | `true` | 0 | 0.338753489 | 294 |
| 14 | `L06-K3-QUARTERLY` | `true` | 0 | 0.339590681 | 441 |
| 15 | `L12-K3-QUARTERLY` | `true` | 0 | 0.344422664 | 414 |
| 16 | `L03-K3-MONTHLY` | `true` | 0 | 0.347840893 | 1035 |
| 17 | `L12-K3-MONTHLY` | `true` | 0 | 0.401614635 | 700 |
| 18 | `L03-K3-QUARTERLY` | `true` | 0 | 0.423540495 | 610 |

The selected variant is rank 1 by score. `L03-K1-QUARTERLY` is 0.000048608 behind — a margin
smaller than one part in four thousand of either score. The two variants differ on one axis (`k`), which
is exactly the situation step 3 exists for, and step 3 was **not** reached because the scores are not
equal. §17 records what that narrow margin does and does not mean.

---

## 12. Attempt 1, Attempt 2, Attempt 3

The three grids are the same eighteen parameterisations over the same sessions with the same signal and
the same costs. Only the risk architecture and the selection rule differ. Row-by-row comparison is
therefore meaningful, which is unusual and is a consequence of the grid never having been widened.

| Measure, `#BASE` runs unless stated | Attempt 1 (no risk architecture) | Attempt 2 (`RA2`) | Attempt 3 (`RA3`) |
|---|---:|---:|---:|
| Variants | 18 | 18 | 18 |
| Runs | 36 | 36 | 36 |
| Research-shutdown events, summed | 36 | 0 | 0 |
| Runs recording a shutdown | 36 of 36 | 0 of 36 | 0 of 36 |
| Worst max drawdown | 0.1759 | 0.1397 | 0.1413 |
| Best max drawdown | 0.1505 | 0.0910 | 0.0971 |
| Lowest total return | -0.1636 | +0.0042 | +0.0148 |
| Highest total return | +0.2869 | +0.6315 | +0.5341 |
| Variants positive on `#BASE` | 10 of 18 | 18 of 18 | 18 of 18 |
| Variants positive on `#STRESS` | not reached | 17 of 18 | 16 of 18 |
| Ladder descents, summed over 36 runs | none (no ladder) | 1605 | 1008 |
| Sessions at full sizing, summed | every session (no throttle) | 36886 | 53671 |
| Representative | none — step 1 eliminated all 18 | `L12-K1-QUARTERLY` | `L03-K2-QUARTERLY` |
| Representative `#BASE` return | n/a | +0.0042 | +0.1034 |
| Representative `#STRESS` return | n/a | -0.0008 | +0.0811 |
| Gate 3 reached | no | yes | yes |
| Conditions not satisfied, `#BASE` | gate never reached | `S3-C3`, `S3-C5`, `S3-C6` | `S3-C6` |
| Verdict | `FAIL` | `FAIL` | `FAIL` |
| Verdict token | withheld, on record in `reports/stage3_g2/` | withheld, on record in `reports/stage3_g2_attempt2/` | `STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE` |

The token row withholds Attempt 1's and Attempt 2's verdict tokens rather than reproducing them.
The sealed `prior_attempt_tokens_note` in this attempt's evidence states that no Attempt 3 artifact
may emit any of the four tokens belonging to the two closed attempts. The emitter that built the
table read both prior tokens from the closed attempts' own admissibility records, asserted that each
is on this attempt's withheld list and that neither equals this attempt's own token, and emitted the
result of that assertion together with the path that carries the string. The renderer refuses if any
of the four reaches this document.

| Variant (lookback / k / frequency) | A1 `#BASE` return | A1 max DD | A1 shutdowns | A2 `#BASE` return | A2 max DD | A3 `#BASE` return | A3 max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| `L03-K1-MONTHLY` | +0.2534 | 0.1505 | 2 | +0.6315 | 0.1116 | +0.5341 | 0.1296 |
| `L03-K1-QUARTERLY` | -0.1636 | 0.1708 | 2 | +0.0691 | 0.1330 | +0.0616 | 0.1355 |
| `L03-K2-MONTHLY` | -0.0526 | 0.1590 | 2 | +0.4203 | 0.1045 | +0.4765 | 0.1022 |
| `L03-K2-QUARTERLY` | +0.1872 | 0.1604 | 2 | +0.0419 | 0.1052 | +0.1034 | 0.0994 |
| `L03-K3-MONTHLY` | -0.1450 | 0.1619 | 2 | +0.2869 | 0.1195 | +0.3499 | 0.1217 |
| `L03-K3-QUARTERLY` | -0.1125 | 0.1538 | 2 | +0.2811 | 0.0910 | +0.2966 | 0.0971 |
| `L06-K1-MONTHLY` | +0.2193 | 0.1759 | 2 | +0.1986 | 0.1263 | +0.1270 | 0.1354 |
| `L06-K1-QUARTERLY` | +0.0102 | 0.1618 | 2 | +0.0834 | 0.1382 | +0.1338 | 0.1413 |
| `L06-K2-MONTHLY` | +0.2869 | 0.1686 | 2 | +0.1927 | 0.1160 | +0.2649 | 0.1102 |
| `L06-K2-QUARTERLY` | -0.1153 | 0.1581 | 2 | +0.0448 | 0.1298 | +0.0664 | 0.1383 |
| `L06-K3-MONTHLY` | +0.2263 | 0.1551 | 2 | +0.1066 | 0.1188 | +0.1671 | 0.1270 |
| `L06-K3-QUARTERLY` | +0.2403 | 0.1552 | 2 | +0.0365 | 0.1160 | +0.0467 | 0.1189 |
| `L12-K1-MONTHLY` | +0.0044 | 0.1653 | 2 | +0.0633 | 0.1193 | +0.0212 | 0.1202 |
| `L12-K1-QUARTERLY` | -0.0465 | 0.1551 | 2 | +0.0042 | 0.1397 | +0.0148 | 0.1397 |
| `L12-K2-MONTHLY` | -0.0465 | 0.1604 | 2 | +0.1792 | 0.1154 | +0.1585 | 0.1125 |
| `L12-K2-QUARTERLY` | +0.0153 | 0.1519 | 2 | +0.1954 | 0.1031 | +0.1065 | 0.1095 |
| `L12-K3-MONTHLY` | +0.1029 | 0.1572 | 2 | +0.0892 | 0.1162 | +0.0843 | 0.1157 |
| `L12-K3-QUARTERLY` | -0.0302 | 0.1508 | 2 | +0.0709 | 0.0978 | +0.0795 | 0.1052 |

Attempt 1's shutdowns were not spread evenly. They cluster in the 2008–2011 window:

| Month of first shutdown | Attempt 1 runs | Attempt 2 runs | Attempt 3 runs |
|---|---:|---:|---:|
| 2008-10 | 4 | 0 | 0 |
| 2008-11 | 2 | 0 | 0 |
| 2009-03 | 2 | 0 | 0 |
| 2009-05 | 6 | 0 | 0 |
| 2010-02 | 2 | 0 | 0 |
| 2010-06 | 2 | 0 | 0 |
| 2010-07 | 4 | 0 | 0 |
| 2010-08 | 4 | 0 | 0 |
| 2010-12 | 2 | 0 | 0 |
| 2011-08 | 2 | 0 | 0 |
| 2011-10 | 2 | 0 | 0 |
| 2016-01 | 2 | 0 | 0 |
| 2020-03 | 2 | 0 | 0 |
| **Total** | **36** | **0** | **0** |

**Three things this table establishes, and one it refutes.**

*Established.* Attempt 1's failure was not marginal: its best maximum drawdown anywhere on base was
15.05%, so every Attempt 1 variant would have failed the 15% condition `S3-C2` even if the
research shutdown had not fired first. Attempt 2 and Attempt 3 both eliminated that failure mode
completely — zero shutdowns, worst drawdowns 13.97% and 14.13% on base. And
RA3's looser ladder did not cost drawdown control: its worst base drawdown is within a fifth of a
percentage point of RA2's, and its best is 9.71% against RA2's 9.10%.

*Refuted.* The sealed disclosure reasons that RA2's 5% rung was "a plausible cause of RA2's
near-constant throttling", with the implication that removing it would recover suppressed
ordinary-market return. The throttling half is confirmed — §16's comparison is unambiguous. The return
half is not. Attempt 2's grid was already 18 of 18 positive, with a **higher** maximum
(+63.15% against +53.41%) and a median within two points of Attempt 3's. The
grid did not need rescuing. What produced Attempt 2's +0.42% headline was its
*selection rule*: `lowest turnover` chose the variant with the fewest fills (189, rank
1 of 18), and on that grid the least-active variant was also the
worst-returning one — `A2_REP_IS_WORST` is `true`, at rank
18 of 18 by return.

The same rule applied to *this* grid would have selected `L12-K1-QUARTERLY` at
+1.48% — again the grid minimum, and again the same parameterisation. So the
representative moved off the floor because **SEL-2** replaced a corner-seeking criterion with a
dispersion one, not because RA3 loosened the ladder. Stated as a counterfactual it is stark: RA3 alone,
under Attempt 2's rule, would have produced a representative earning +1.48%
over thirteen years; SEL-2 alone, on Attempt 2's grid, would have selected some other variant from a
grid whose median was +9.79%.

**What this does and does not establish.** It does not establish that SEL-2 is a better rule. A rule
that happens to select a better-returning variant on the one grid where it has been run is not thereby
validated; that is the reasoning the constitution forbids, and SEL-2's justification is its dispersion
criterion, not its outcome. What the comparison establishes is narrower and it is the only part of this
section carrying evidential weight: **the two changes are separable in their effects, and the effect on
the reported return figure came from the selection rule.** The attempt still cannot isolate them
formally, because both changed at once and no run was made with only one changed. Isolating them is
explicitly not authorized.

---

## 13. Determinism

| Digest | Runs | Identical on rerun |
|---|---|---|
| trade payload | 36 | yes |
| equity payload | 36 | yes |
| ranking digest | 36 | yes |
| risk-state trace digest | 36 | yes |
| selection scores | 18 | yes |
| selection components | 18 | yes |
| neighbour sets | 18 | yes |
| selected variant | 1 | yes |

Eight digested quantities over 36 runs, `all_identical` true, seed `null` because the strategy contains
no randomness. Each digest is checked **not** to be a constant across variants before its stability is
reported: a field that is the same everywhere would satisfy an equality test vacuously and would prove
nothing about determinism. The selection determinism is tested directly against the recorded selection
inputs and through a serialisation round trip, not only end to end, so a determinism failure in the
selector cannot hide behind a determinism pass in the engine.

The risk-state trace digest is **not** comparable with Attempt 2's, and neither is expected to equal the
other: RA3's band alphabet is {0, 1, 2} where RA2's was {0, 1, 2, 3}. The protocol said so before the
run.

---

## 14. Gate 3

The representative is `SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY`, selected before any gate condition was evaluated.

| Condition | Required (verbatim) | `#BASE` verdict | measured | threshold | `#STRESS` verdict | measured |
|---|---|---|---|---|---|---|
| `S3-C1` | total return is positive | `MET` | 0.10337843028513874006 | > 0 | `MET` | 0.08107210940706772465 |
| `S3-C2` | maximum drawdown is no worse than 15% | `MET` | 0.09941232925528737112297704174156968 | <= 0.15 | `MET` | 0.09932170282394264800433103176555540 |
| `S3-C3` | profit factor is at least 1.10 | `MET` | 1.270402611534276387377584330794342 | >= 1.1 | `MET` | 1.200539083557951482479784366576819 |
| `S3-C4` | at least 30 closed trades exist, unless a lower-frequency protocol predeclared a longer evidence requirement before results | `MET` | 62 | >= 30 | `MET` | 62 |
| `S3-C5` | performance is not dependent on one trade: removing the single best trade leaves total return above 0% | `MET` | min(0.055666171814245462689982570080576, 0.055666171814245462689982570080576) | best_trade_removed_return > 0 for BOTH removals | `MET` | min(0.031717505233078233394772524945014, 0.031717505233078233394772524945014) |
| `S3-C6` | no single instrument contributes more than 50% of total strategy profit for a multi-instrument strategy | `NOT_MET` | 0.7505030181086519114688128772635815 | <= 0.50 | `NOT_MET` | 0.9771505376344086021505376344086022 |
| `S3-C7` | reasonable neighboring parameter values do not reverse the sign of net return | `MET` | 4/4 neighbours match | all 4 match, zero matches nothing | `MET` | 4/4 neighbours match |

**Scope.** `SE100-CFG-3105` scopes the gate across both runs; `SE100-CFG-3106` lists the stressed run as
reported-but-not-gating for `S3-C1` and `S3-C4`. Neither outranks the other, so the more restrictive
reading governs and both readings are reported. The resolved scope, quoted from `SE100-CFG-3106`'s own
entry for this conflict, is:
Admission requires all seven conditions satisfied on #BASE AND S3-C1 through S3-C6 satisfied on #STRESS.
The `#STRESS` column of the `S3-C7` row above is therefore reported, not gating; it is the only row of
the seven where that is so, and the decision record carries the distinction per row as `gating_runs` and
`reported_not_gating`. `S3-C7` is `MET` on both runs in any case, so nothing in the verdict turns on it.
The two readings agree here as well: the permissive base-only reading would
give `STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE`. `G2A2-CONFLICT-25`, inherited and resolved the same way.

**Outcome.**

| Field | Value |
|---|---|
| Conditions evaluated | 7 |
| Satisfied on both runs | 6 |
| Not satisfied on `#BASE` | `S3-C6` |
| Not satisfied on `#STRESS` | `S3-C6` |
| Fail route | `REPRESENTATIVE_FAILED_AT_LEAST_ONE_CONDITION` |
| Candidates evaluated | 1 |
| Admitted candidates | 0 |
| `admissible_candidate_exists` | **false** |

The last line of that table is the one that decides the stage. The seven condition rows are conjunctive
within a candidate and the stage verdict is a disjunction across candidates; with one live candidate the
disjunction is over a one-member set, which is `G2A3-CONFLICT-24`.

**Where the representative actually fails.** `S3-C6` requires that no single symbol contribute more
than 50.00% of gross profit. The representative's largest contributor supplied
75.05% on base and 97.72% on stress, from 24 distinct
symbols traded over 62 closed trades. The condition text is a concentration test, and a
`k`-of-34 rotation that spends much of thirteen years in a small number of persistent leaders is
structurally exposed to it. Attempt 2's representative failed the same condition more severely
(2.7176 and 6.8824 as ratios against a 0.50 ceiling), so this is not a new failure
mode — but Attempt 2 failed three other conditions alongside it on base and four on stress, and this
attempt fails only this one.

Everything else clears with margin: return +10.34% base and +8.11%
stress, maximum drawdown 9.94% and 9.93% against 15%, profit factor
1.2704 and 1.2005 against 1.10, 62 closed trades against 30,
and the best-trade-removed return positive on both removals in both runs. The neighbourhood-stability
condition `S3-C7` is `4/4 neighbours match` on stress, where Attempt 2's representative measured
`0/3 neighbours match`.

**A measurement note that matters.** Two profit-factor figures exist for this representative and they
differ. The gate reads the episode ledger, which pairs each entry with its eventual exit across
throttle trims and partial reductions, and it measures 1.2704 on base. The engine's own
`Portfolio.trades` recorder measures 1.2397 on base and 1.1690 on
stress. The divergence is not an error in either: a throttle trim closes part of a position in the
recorder's view and does not close an episode in the ledger's, so the two count different things. The
gate condition names closed trades, the ledger is the thing that has them, and the ledger figure is the
one the gate used. The recorder figure is reported so that a reader recomputing from the trade payload
does not conclude the gate was mis-measured. `G2A2-CONFLICT-18`, inherited.

**Selection traced, not asserted.** The scores below are SEL-2's own computed output, read from the
evidence rather than recomputed in prose. The representative's neighbourhood and the four
per-quantity mean dissimilarities that produce its score:

| Variant | Role | Neighbours | Instability score | mean dissimilarity, `fill_count` | mean dissimilarity, `ladder_descents` | mean dissimilarity, `lockout_arms` | mean dissimilarity, `stops_filled` |
|---|---|---:|---:|---:|---:|---:|---:|
| `L03-K2-QUARTERLY` | **representative** | 4 | 0.215471404 | 0.325717816 | 0.131846770 | 0.131846770 | 0.272474260 |
| `L03-K1-QUARTERLY` | neighbour | 3 | 0.215520012 | 0.217675920 | 0.224979842 | 0.224979842 | 0.194444444 |
| `L03-K2-MONTHLY` | neighbour | 4 | 0.299993984 | 0.316509255 | 0.283380840 | 0.283380840 | 0.316705003 |
| `L03-K3-QUARTERLY` | neighbour | 3 | 0.423540495 | 0.399717536 | 0.483333333 | 0.483333333 | 0.327777778 |
| `L06-K2-QUARTERLY` | neighbour | 5 | 0.247419599 | 0.259181864 | 0.217629219 | 0.217629219 | 0.295238095 |

And the raw quantities those dissimilarities are computed from, summed across both runs:

| Variant | Role | `fill_count` | `ladder_descents` | `lockout_arms` | `stops_filled` |
|---|---|---:|---:|---:|---:|
| `L03-K2-QUARTERLY` | **representative** | 298 | 44 | 44 | 32 |
| `L03-K1-QUARTERLY` | neighbour | 283 | 53 | 53 | 24 |
| `L03-K2-MONTHLY` | neighbour | 801 | 40 | 40 | 37 |
| `L03-K3-QUARTERLY` | neighbour | 610 | 60 | 60 | 60 |
| `L06-K2-QUARTERLY` | neighbour | 336 | 44 | 44 | 42 |

The representative's score of 0.215471404 is the mean of its four component means over its
4 neighbours. `ladder_descents` and `lockout_arms` are numerically identical
throughout, which is not a coincidence: under RA3-5 the lockout is armed by exactly the downward ladder
transitions, so the two counters are the same event counted twice. SEL-2 therefore effectively weights
that event double and reads three quantities rather than four. That was declared as a consequence of the
sealed field list and is not repaired here; the field list was frozen before the run and reweighting it
now is precisely the degree of freedom the seal exists to remove.

---

## 15. Per-variant results

None of this gates anything. The gate is decided by the representative alone, and these tables exist
because the protocol requires every variant to be reported whether or not it is selected — so that a
reader can see what the selection rule passed over, and so that a future attempt cannot present a
re-selection as a discovery.

**Base cost model.**

| # | Variant | Return | Max DD | Profit factor | Closed trades | Closed episodes | Distinct symbols | Shutdowns |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `L03-K1-MONTHLY` | +0.5341 | 0.1296 | 2.0295 | 105 | 105 | 21 | 0 |
| 2 | `L03-K1-QUARTERLY` | +0.0616 | 0.1355 | 1.3492 | 49 | 49 | 17 | 0 |
| 3 | `L03-K2-MONTHLY` | +0.4765 | 0.1022 | 1.6251 | 156 | 156 | 27 | 0 |
| 4 | `L03-K2-QUARTERLY` | +0.1034 | 0.0994 | 1.2397 | 62 | 62 | 24 | 0 |
| 5 | `L03-K3-MONTHLY` | +0.3499 | 0.1217 | 1.5262 | 234 | 234 | 29 | 0 |
| 6 | `L03-K3-QUARTERLY` | +0.2966 | 0.0971 | 1.5319 | 124 | 124 | 27 | 0 |
| 7 | `L06-K1-MONTHLY` | +0.1270 | 0.1354 | 1.3967 | 81 | 81 | 19 | 0 |
| 8 | `L06-K1-QUARTERLY` | +0.1338 | 0.1413 | 1.4949 | 40 | 40 | 15 | 0 |
| 9 | `L06-K2-MONTHLY` | +0.2649 | 0.1102 | 1.4499 | 144 | 144 | 25 | 0 |
| 10 | `L06-K2-QUARTERLY` | +0.0664 | 0.1383 | 1.2328 | 72 | 72 | 22 | 0 |
| 11 | `L06-K3-MONTHLY` | +0.1671 | 0.1270 | 1.2766 | 209 | 209 | 28 | 0 |
| 12 | `L06-K3-QUARTERLY` | +0.0467 | 0.1189 | 1.0652 | 95 | 95 | 26 | 0 |
| 13 | `L12-K1-MONTHLY` | +0.0212 | 0.1202 | 1.2616 | 66 | 66 | 18 | 0 |
| 14 | `L12-K1-QUARTERLY` | +0.0148 | 0.1397 | 1.3875 | 36 | 36 | 15 | 0 |
| 15 | `L12-K2-MONTHLY` | +0.1585 | 0.1125 | 1.4840 | 63 | 63 | 25 | 0 |
| 16 | `L12-K2-QUARTERLY` | +0.1065 | 0.1095 | 1.4305 | 46 | 46 | 21 | 0 |
| 17 | `L12-K3-MONTHLY` | +0.0843 | 0.1157 | 1.2726 | 156 | 156 | 29 | 0 |
| 18 | `L12-K3-QUARTERLY` | +0.0795 | 0.1052 | 1.1828 | 93 | 93 | 27 | 0 |

**Stressed cost model.**

| # | Variant | Return | Max DD | Profit factor | Closed trades | Closed episodes | Fills | Shutdowns |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `L03-K1-MONTHLY` | +0.5068 | 0.1316 | 1.9728 | 105 | 105 | 306 | 0 |
| 2 | `L03-K1-QUARTERLY` | +0.0434 | 0.1337 | 1.2817 | 49 | 49 | 141 | 0 |
| 3 | `L03-K2-MONTHLY` | +0.4612 | 0.1110 | 1.5582 | 181 | 181 | 434 | 0 |
| 4 | `L03-K2-QUARTERLY` | +0.0811 | 0.0993 | 1.1690 | 62 | 62 | 148 | 0 |
| 5 | `L03-K3-MONTHLY` | +0.3015 | 0.1245 | 1.4479 | 230 | 230 | 511 | 0 |
| 6 | `L03-K3-QUARTERLY` | +0.1323 | 0.1119 | 1.1595 | 139 | 139 | 323 | 0 |
| 7 | `L06-K1-MONTHLY` | +0.1197 | 0.1434 | 1.4466 | 81 | 81 | 227 | 0 |
| 8 | `L06-K1-QUARTERLY` | -0.0157 | 0.1436 | 1.1529 | 40 | 40 | 119 | 0 |
| 9 | `L06-K2-MONTHLY` | +0.1556 | 0.1218 | 1.2430 | 123 | 123 | 299 | 0 |
| 10 | `L06-K2-QUARTERLY` | +0.0074 | 0.1398 | 0.9890 | 72 | 72 | 168 | 0 |
| 11 | `L06-K3-MONTHLY` | +0.1526 | 0.1409 | 1.2448 | 222 | 222 | 491 | 0 |
| 12 | `L06-K3-QUARTERLY` | +0.0530 | 0.1183 | 1.0777 | 95 | 95 | 220 | 0 |
| 13 | `L12-K1-MONTHLY` | +0.0180 | 0.1226 | 1.2189 | 66 | 66 | 179 | 0 |
| 14 | `L12-K1-QUARTERLY` | -0.0008 | 0.1420 | 1.1709 | 36 | 36 | 92 | 0 |
| 15 | `L12-K2-MONTHLY` | +0.1513 | 0.1120 | 1.4878 | 64 | 64 | 148 | 0 |
| 16 | `L12-K2-QUARTERLY` | +0.1254 | 0.1069 | 1.5782 | 52 | 52 | 142 | 0 |
| 17 | `L12-K3-MONTHLY` | +0.0757 | 0.1175 | 1.2589 | 152 | 152 | 345 | 0 |
| 18 | `L12-K3-QUARTERLY` | +0.0318 | 0.1086 | 1.0581 | 83 | 83 | 188 | 0 |

18 of 18 variants are positive on base and 16 of 18 on stress. The best
base return in the grid is `L03-K1-MONTHLY` at +53.41%, with a maximum drawdown of
12.96%, a profit factor of 2.0295 and 105 closed trades. It was not
selected: its instability score is 0.316981929, rank 12 of 18. Re-selecting on return
is forbidden and was not done.

---

## 16. Risk-architecture statistics

**Per variant, base run.**

| # | Variant | Ladder descents | Ladder ascents | Deepest band | Lockout arms | Recoveries blocked | Stops triggered | Stops filled | Stops pre-empted |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `L03-K1-MONTHLY` | 39 | 39 | 2 | 39 | 140 | 9 | 9 | 0 |
| 2 | `L03-K1-QUARTERLY` | 25 | 25 | 2 | 25 | 74 | 12 | 12 | 0 |
| 3 | `L03-K2-MONTHLY` | 22 | 22 | 2 | 22 | 79 | 54 | 17 | 3 |
| 4 | `L03-K2-QUARTERLY` | 25 | 25 | 1 | 25 | 101 | 16 | 16 | 0 |
| 5 | `L03-K3-MONTHLY` | 13 | 13 | 2 | 13 | 49 | 238 | 24 | 10 |
| 6 | `L03-K3-QUARTERLY` | 20 | 20 | 1 | 20 | 65 | 576 | 29 | 6 |
| 7 | `L06-K1-MONTHLY` | 50 | 48 | 2 | 50 | 184 | 9 | 9 | 0 |
| 8 | `L06-K1-QUARTERLY` | 29 | 29 | 2 | 29 | 118 | 11 | 11 | 0 |
| 9 | `L06-K2-MONTHLY` | 30 | 30 | 2 | 30 | 134 | 28 | 11 | 2 |
| 10 | `L06-K2-QUARTERLY` | 20 | 20 | 2 | 20 | 85 | 21 | 21 | 0 |
| 11 | `L06-K3-MONTHLY` | 24 | 22 | 2 | 24 | 76 | 87 | 22 | 4 |
| 12 | `L06-K3-QUARTERLY` | 14 | 13 | 2 | 14 | 40 | 153 | 21 | 3 |
| 13 | `L12-K1-MONTHLY` | 37 | 35 | 2 | 37 | 128 | 15 | 15 | 1 |
| 14 | `L12-K1-QUARTERLY` | 44 | 43 | 2 | 44 | 142 | 12 | 12 | 0 |
| 15 | `L12-K2-MONTHLY` | 16 | 16 | 2 | 16 | 62 | 13 | 13 | 0 |
| 16 | `L12-K2-QUARTERLY` | 23 | 23 | 2 | 23 | 75 | 15 | 15 | 0 |
| 17 | `L12-K3-MONTHLY` | 38 | 37 | 2 | 38 | 157 | 24 | 24 | 0 |
| 18 | `L12-K3-QUARTERLY` | 25 | 25 | 2 | 25 | 84 | 29 | 29 | 0 |

**Per variant, stressed run.**

| # | Variant | Ladder descents | Ladder ascents | Deepest band | Lockout arms | Recoveries blocked | Stops triggered | Stops filled | Stops pre-empted |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `L03-K1-MONTHLY` | 39 | 39 | 2 | 39 | 124 | 9 | 9 | 0 |
| 2 | `L03-K1-QUARTERLY` | 28 | 28 | 2 | 28 | 74 | 12 | 12 | 0 |
| 3 | `L03-K2-MONTHLY` | 18 | 18 | 2 | 18 | 66 | 78 | 20 | 3 |
| 4 | `L03-K2-QUARTERLY` | 19 | 19 | 1 | 19 | 71 | 16 | 16 | 0 |
| 5 | `L03-K3-MONTHLY` | 10 | 10 | 2 | 10 | 49 | 32 | 23 | 0 |
| 6 | `L03-K3-QUARTERLY` | 40 | 40 | 2 | 40 | 153 | 31 | 31 | 0 |
| 7 | `L06-K1-MONTHLY` | 47 | 46 | 2 | 47 | 202 | 9 | 9 | 0 |
| 8 | `L06-K1-QUARTERLY` | 36 | 35 | 2 | 36 | 137 | 11 | 11 | 0 |
| 9 | `L06-K2-MONTHLY` | 16 | 15 | 2 | 16 | 58 | 111 | 11 | 6 |
| 10 | `L06-K2-QUARTERLY` | 24 | 23 | 2 | 24 | 85 | 21 | 21 | 0 |
| 11 | `L06-K3-MONTHLY` | 18 | 16 | 2 | 18 | 60 | 23 | 23 | 1 |
| 12 | `L06-K3-QUARTERLY` | 12 | 11 | 2 | 12 | 38 | 156 | 21 | 3 |
| 13 | `L12-K1-MONTHLY` | 31 | 29 | 2 | 31 | 110 | 15 | 15 | 1 |
| 14 | `L12-K1-QUARTERLY` | 44 | 43 | 2 | 44 | 173 | 12 | 12 | 0 |
| 15 | `L12-K2-MONTHLY` | 22 | 22 | 2 | 22 | 83 | 595 | 13 | 30 |
| 16 | `L12-K2-QUARTERLY` | 41 | 41 | 2 | 41 | 166 | 155 | 15 | 2 |
| 17 | `L12-K3-MONTHLY` | 45 | 44 | 2 | 45 | 181 | 21 | 21 | 0 |
| 18 | `L12-K3-QUARTERLY` | 24 | 24 | 2 | 24 | 96 | 683 | 31 | 10 |

**The comparison the operating instruction requires.** RA3's ladder statistics must be shown to differ
from Attempt 2's, or the change was aimed at the wrong mechanism:

| Statistic | Attempt 3 (`RA3`), 36 runs | Attempt 2 (`RA2`), 36 runs | Runs differing | Differs |
|---|---:|---:|---:|---|
| `ladder_descents` | 1008 | 1605 | 36 of 36 | `true` |
| `ladder_ascents` | 988 | 1571 | 35 of 36 | `true` |
| `lockout_arms` | 1008 | 1605 | 36 of 36 | `true` |
| `lockout_recoveries_blocked` | 3719 | 6133 | 36 of 36 | `true` |
| `stops_triggered` | 3312 | 1911 | 25 of 36 | `true` |
| `stops_filled` | 624 | 608 | 21 of 36 | `true` |
| sessions at sizing scalar `1.00` | 53671 | 36886 | 36 of 36 | `true` |

Every one of those seven statistics differs, on between 21 and all 36
runs. The direction is uniform on the throttling measures: fewer descents, fewer ascents, far fewer
blocked recoveries, and 53671 sessions at full sizing against
36886 — an increase of about forty-five percent in the time the strategy was allowed to
be fully invested. The stop measures move the other way, and that is expected rather than surprising:
larger positions reach an 8%-from-basis condition more often, so `stops_triggered` rose from
1911 to 3312 while `stops_filled` rose only from
608 to 624.

**Band depth.** RA3 has three bands, not four, so no `band 3` figure exists for this attempt and none is
reported. Band 0 is full sizing.

| Deepest ladder band reached | `#BASE` variants | `#STRESS` variants |
|---|---:|---:|
| band 1 | 2 | 1 |
| band 2 | 16 | 17 |

Every variant reached at least band 1 in both runs, and 16 of 18 on base reached the
deepest band. 0 variants stayed in full sizing throughout, which means the ladder
engaged on the whole grid and the SC-7 degenerate case did not occur.

**Two regimes in the stop numbers.** Across the grid 3312 stop conditions were observed
and 624 became fills, a ratio of 0.1884, with 85
pre-empted — a stop condition observed on a session where a scheduled exit or a throttle trim had
already taken precedence for that symbol. The pre-empted column is not a lost exit: the position was
being closed or reduced anyway, by a rule with higher precedence. The ratio is low because the stop
condition is re-observed on every subsequent session until the position leaves the book, so one
underwater position can contribute many triggers and one fill. 11 variant-runs
show that pattern at extremes; the widest is 683 triggered against 31 filled on `L12-K3-QUARTERLY` #STRESS.

**Throttle and exposure, base run.**

| # | Variant | Throttle legs | Legs below min notional | Sessions breaching ceiling | Max gross fraction | On session | Combined scalar min | Combined scalar mean | Sessions scalar < 1 |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 1 | `L03-K1-MONTHLY` | 97 | 1156 | 1253 | 0.5155 | 2020-11-09 | 0.2500 | 0.5920 | 2346 |
| 2 | `L03-K1-QUARTERLY` | 43 | 1111 | 1154 | 0.5137 | 2011-01-31 | 0.2500 | 0.4861 | 2617 |
| 3 | `L03-K2-MONTHLY` | 53 | 1154 | 634 | 0.5160 | 2008-11-20 | 0.2500 | 0.8558 | 1051 |
| 4 | `L03-K2-QUARTERLY` | 24 | 372 | 210 | 0.5112 | 2009-10-14 | 0.3305 | 0.7677 | 1570 |
| 5 | `L03-K3-MONTHLY` | 55 | 1723 | 630 | 0.5164 | 2008-11-20 | 0.2500 | 0.7010 | 1560 |
| 6 | `L03-K3-QUARTERLY` | 41 | 1650 | 599 | 0.5110 | 2009-10-05 | 0.2966 | 0.9047 | 768 |
| 7 | `L06-K1-MONTHLY` | 64 | 850 | 914 | 0.5184 | 2008-11-20 | 0.2500 | 0.6153 | 2205 |
| 8 | `L06-K1-QUARTERLY` | 65 | 916 | 981 | 0.5184 | 2008-11-20 | 0.2500 | 0.6138 | 2118 |
| 9 | `L06-K2-MONTHLY` | 69 | 1287 | 715 | 0.5113 | 2009-05-06 | 0.2500 | 0.7866 | 1401 |
| 10 | `L06-K2-QUARTERLY` | 24 | 1760 | 904 | 0.5112 | 2009-10-14 | 0.2377 | 0.5402 | 2295 |
| 11 | `L06-K3-MONTHLY` | 47 | 2092 | 768 | 0.5114 | 2009-05-18 | 0.1911 | 0.7218 | 1601 |
| 12 | `L06-K3-QUARTERLY` | 32 | 1230 | 451 | 0.5131 | 2008-12-16 | 0.2500 | 0.4850 | 2623 |
| 13 | `L12-K1-MONTHLY` | 48 | 968 | 1016 | 0.5128 | 2008-12-17 | 0.1639 | 0.6046 | 2079 |
| 14 | `L12-K1-QUARTERLY` | 30 | 932 | 962 | 0.5184 | 2008-11-20 | 0.1818 | 0.4330 | 2849 |
| 15 | `L12-K2-MONTHLY` | 18 | 202 | 120 | 0.5143 | 2009-11-05 | 0.2500 | 0.7304 | 1688 |
| 16 | `L12-K2-QUARTERLY` | 18 | 244 | 141 | 0.5146 | 2008-11-20 | 0.2500 | 0.8092 | 1133 |
| 17 | `L12-K3-MONTHLY` | 48 | 2214 | 807 | 0.5116 | 2008-12-17 | 0.2500 | 0.6956 | 1763 |
| 18 | `L12-K3-QUARTERLY` | 43 | 1696 | 623 | 0.5122 | 2010-04-14 | 0.2500 | 0.8266 | 1194 |

Two columns deserve reading carefully. **Sessions breaching the ceiling** is non-zero for every variant,
with maximum gross fractions from 51.10% to 51.84% against a 50% ceiling. That
is not a broken clamp. The clamp binds at the fill open; between opens the held positions appreciate,
and an appreciation that carries gross above the ceiling is detected at the next close and trimmed at the
following open. The excess ranges from 1.10% to 1.84% of
equity and is the one-session execution lag made visible, which the protocol declared.

**Combined scalar.** Its minimum anywhere in the grid is 0.1638 and its per-variant
means run from 0.3838 to 0.9047. Attempt 2's per-variant means ran from
0.3990 to 0.8652; on base alone Attempt 3's run from
0.4330 to 0.9047. The strategy still spends a great deal
of its life below full sizing — the representative alone is below 1 on 1570
sessions with a mean of 0.7677 and a minimum of 0.330469784 — because the
volatility term is unchanged and it, not the ladder, accounts for most of the throttling that remains.
Removing a ladder rung did not remove `f_vol`, and a reader looking for the ladder change in the scalar
means will find only part of it there.

**Turnover and the instability score.**

| Variant | Fills (both runs) | Ladder descents (both runs) | Lockout arms (both runs) | Stop fills (both runs) | Instability score |
|---|---:|---:|---:|---:|---:|
| `L12-K1-QUARTERLY` | 195 | 88 | 88 | 24 | 0.246609961 |
| `L12-K2-QUARTERLY` | 254 | 64 | 64 | 30 | 0.285600694 |
| `L06-K1-QUARTERLY` | 265 | 65 | 65 | 22 | 0.248621581 |
| `L03-K1-QUARTERLY` | 283 | 53 | 53 | 24 | 0.215520012 |
| `L12-K2-MONTHLY` | 294 | 38 | 38 | 26 | 0.338753489 |
| `L03-K2-QUARTERLY` | 298 | 44 | 44 | 32 | 0.215471404 |
| `L06-K2-QUARTERLY` | 336 | 44 | 44 | 42 | 0.247419599 |
| `L12-K1-MONTHLY` | 359 | 68 | 68 | 30 | 0.292941999 |
| `L12-K3-QUARTERLY` | 414 | 49 | 49 | 60 | 0.344422664 |
| `L06-K3-QUARTERLY` | 441 | 26 | 26 | 42 | 0.339590681 |
| `L06-K1-MONTHLY` | 454 | 97 | 97 | 18 | 0.291302167 |
| `L03-K3-QUARTERLY` | 610 | 60 | 60 | 60 | 0.423540495 |
| `L03-K1-MONTHLY` | 614 | 78 | 78 | 18 | 0.316981929 |
| `L06-K2-MONTHLY` | 658 | 46 | 46 | 22 | 0.274579406 |
| `L12-K3-MONTHLY` | 700 | 83 | 83 | 45 | 0.401614635 |
| `L03-K2-MONTHLY` | 801 | 40 | 40 | 37 | 0.299993984 |
| `L06-K3-MONTHLY` | 955 | 42 | 42 | 45 | 0.290149221 |
| `L03-K3-MONTHLY` | 1035 | 23 | 23 | 47 | 0.347840893 |

Fill counts span 195 to 1035 across the grid — a factor of five — while
ladder descents span only 13 to 50 and lockout arms 40 to
184. That spread is why `fill_count` dominates the instability score, exactly as `SC-7`
predicted it might.

---

## 17. Limitations

**17.1 This is the third disclosed adaptation on one hypothesis family.** The verbatim disclosure in §2
is the binding statement. Cumulative multiplicity across the family is now 54 variants
and 108 runs, and the sealed protocol is explicit that these are not independent tests:

> The 54 cumulative variants are not 54 independent tests. Attempt 2's risk architecture was chosen after seeing where Attempt 1 broke; Attempt 3's ladder change and selection rule were chosen after seeing how Attempt 2 behaved. The effective number of researcher degrees of freedom is larger than 54 and grows faster than the variant count, because each attempt conditions on all preceding results. It is not quantified here because any quantification would itself be a choice made after the fact.

No correction is applied to the thresholds, and the reason is not convenience:

> No multiplicity correction is applied to the gate thresholds, because the thresholds are constitutional and may not be altered by a stage that would benefit from altering them. The multiplicity is disclosed instead, and it is the reason a development pass is explicitly not evidence of an edge.

> A third adaptation on one hypothesis family is the point at which a development PASS carries very little evidential weight on its own. This is stated before the run. See G2A3-CONFLICT-33.

**17.2 The development window has now been read three times.** It is not pristine and cannot be made so.
The validation window carries its own disclosed cost, sealed in the partition lock before any of this:

> Generation 2's validation window (2021-08-01 → 2024-07-31) overlaps the exact period Generation 1 used for its own Gate 4 validation read. The researcher therefore already knows, from Generation 1's published report, approximately how SPY (and by extension the broad market) behaved in this window — including its Sharpe ratio (≈0.20), total return (≈2.15%), and fold-by-fold sign pattern (7 of 12 positive). Generation 2 tests a different hypothesis (cross-sectional multi-asset selection vs. single-symbol mean reversion) over the same calendar period, which limits but does not eliminate the concern. This is a real multiplicity cost, disclosed and not minimized, and it is the reason Generation 2's validation result alone — without a clean holdout confirmation — cannot be treated as sufficient evidence of an edge.

**17.3 Two changes, one result.** RA3 and SEL-2 changed together. §12 shows their effects are separable
in *direction* — the throttle statistics moved because of RA3, the representative moved because of SEL-2
— but that is an argument from the counterfactual application of each rule, not a controlled comparison.
No run was made with one change alone, and making one is explicitly not authorized. `G2A3-CONFLICT-33`.

**17.4 This is a development result.** It is in-sample by construction. A development FAIL is
informative in one direction only: it says this specification does not clear the admissibility floor on
data it was allowed to see. It says nothing about out-of-sample behaviour, because there is no
out-of-sample evidence to say it with.

**17.5 The verdict is bounded by the run span.** 2008-07-28 → 2021-07-30 is one sample of one
market regime sequence. The 3276 sessions include 2008, 2010, 2011, 2015, 2018 and 2020,
which is a reasonable variety of drawdowns and not a guarantee of coverage.

**17.6 Better variants exist in the grid and were not selected.** `L03-K1-MONTHLY` returned
+53.41% against the representative's +10.34% and would very likely have passed
`S3-C1` through `S3-C5`. Whether it would have passed `S3-C6` is not stated here, because the gate was
not run on it and running it now would be a search over eighteen candidates for one that passes.
Re-selecting on return is forbidden and was not done.

**17.7 The selection margin is very narrow.** 0.000048608 separates the representative from
`L03-K1-QUARTERLY`. A rule whose top two candidates differ by one part in four thousand is, on this grid,
close to indifferent between them, and a trivially different dissimilarity denominator or a different
choice among the four quantities could reverse the order. The rule is sealed and the order it produced
stands, but its discriminating power at the top of the ranking should not be overstated. Note also that
the runner-up is `L12-K1-QUARTERLY`'s sibling on the `k` axis rather than a distant
variant, so the near-tie is between two adjacent parameterisations and not between two different
strategies.

**17.8 The dissimilarity denominator carries a floor of 1.** A pair that is zero on both sides scores 0
rather than dividing by zero. That is disclosed rather than repaired, and for the representative no pair
was zero on both sides. `G2A3-CONFLICT-32`.

**17.9 The exposure ceiling was exceeded on sessions in every variant.** By between
1.10% and 1.84% of equity, for one session at a time, by the
mechanism §16 describes. A ceiling enforced at the open and measured at the close is not the same ceiling
a reader may assume from the phrase "never exceeds 50%".

**17.10 Two measurement bases coexist.** The episode ledger and the `Portfolio.trades` recorder count
different things and produce different profit factors, as §14 records. Every gate figure comes from the
ledger. A reader recomputing from the raw trade payload will get the recorder's numbers.

**17.11 Step 3 of the selection rule was never exercised**, and neither was step 4. No two variants tied
on the instability score. The tiebreak paths are tested against fixtures and have never run on real
data, in this attempt or in Attempt 2.

**17.12 One rung was removed and the drawdown did not grow.** SC-8 declared that removing the 5% rung put
`S3-C2` under more pressure and moved the research shutdown closer. Neither happened: the deepest
drawdown anywhere was 14.36% and no variant shut down. That the declared risk did
not materialise is a result, not a vindication of the reasoning that predicted it, and on a different
thirteen-year window it could go the other way. `G2A3-CONFLICT-29`.

**17.13 Costs are modelled, not observed.** No order was placed, no broker or credential was reachable
from any module in this attempt, and the fills are the engine's own simulation under a frozen cost
model.

---

## 18. Conflicts

The numbering is one space shared by `SE100-CFG-3105` and `SE100-CFG-3106`. `SE100-CFG-3105` states the
rule, and this is its text rather than a paraphrase of it:

> The Attempt 3 conflict numbering is one space shared by this file and SE100-CFG-3106, exactly as Attempt 2's was shared by SE100-CFG-3103 and SE100-CFG-3104. Ids 18 to 25 were taken by Attempt 2's criteria file; ids 26 to 33 are fresh ids taken by Attempt 3's criteria file; this file takes 34 onward. Four entries in Attempt 3's criteria file reuse a number below 26 on purpose: G2A3-CONFLICT-19, 21, 22 and 24 each supersede in scope the same-numbered G2A2 entry, so a superseding conflict keeps its predecessor's number and changes only its prefix. The prefix makes the two distinct ids. Nothing is duplicated across the two files, so the two cannot drift into disagreeing versions of one conflict.

Read "this file" there as `SE100-CFG-3105`. Four ids below 26 therefore carry the `G2A3` prefix and are
Attempt 3 ids, not Attempt 2 ids: the prefix is what makes `G2A3-CONFLICT-19` and `G2A2-CONFLICT-19` two
distinct entries. Ids 34 to 38 were taken by the protocol config before the run. Ids 39, 40 and 41 were
taken during implementation, in `g2_rotation_ra3.py`, `g2_gate_ra3.py` and
`test_g2_sel2_selection_rule.py`. Id 42 is taken by this session's decision package, and 43 is free.

| Id | Conflict | Resolution |
|---|---|---|
| `G2A3-CONFLICT-19` | One of RA2's three ladder rungs is gone, so the engineered component of any MET verdict here is smaller than Attempt 2's by exactly that rung and no more. | Recorded in the sealed criteria before the run. Supersedes `G2A2-CONFLICT-18`'s scope. |
| `G2A3-CONFLICT-21` | The operating instruction names no verdict token at all, which is a change from both prior attempts. | The token was derived from `SE100-CFG-3106`'s `verdict_token_derivation`, which is the disk. The builder asserts the derived string against the evidence's own rather than restating a literal. |
| `G2A3-CONFLICT-22` | Across three attempts one hypothesis family has now been run under three ladder geometries — none at all, 5/8/10, and 8/10 — which is a search over risk architectures and not a robustness test of one. | Disclosed, not repaired. Carried forward as 54 cumulative variants and 108 cumulative runs on one family. |
| `G2A3-CONFLICT-24` | Candidate index 3 is the only live candidate, so the constitution's cross-candidate disjunction is taken over a one-member set. | The gate is decided by the `admissible_candidate_exists` row alone; the seven condition rows settle nothing on their own. |
| `G2A2-CONFLICT-25` | `SE100-CFG-3105` scopes the gate across both runs while `SE100-CFG-3106` lists the stress run as reported-but-not-gating for `S3-C1` and `S3-C4`, and neither outranks the other. | Inherited and resolved as Attempt 2 resolved it. The more restrictive reading governs and both readings are reported in full; here they agree — the permissive base-only reading gives `STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE`. |
| `G2A3-CONFLICT-26` | SEL-2 reads dispersion across a neighbourhood where Attempt 2's rule read a level, and the sealed protocol states plainly that Attempt 2's rule was the more conservative of the two. | This is the reason Attempt 3 required its own pre-registration rather than a re-run of Attempt 2's. |
| `G2A3-CONFLICT-27` | The operating instruction describes neighbourhoods of 2, 3 or 4 variants; the sealed geometry on this grid gives 3, 4 or 5, and the representative has 4. | The sealed geometry governs. The instruction's counts are not repeated as fact anywhere in this package. |
| `G2A3-CONFLICT-28` | `SE100-CFG-3103`'s closure sentence states that no Attempt 3 is authorized by that file. | Satisfied by the operating instruction, which authorizes one attempt and no more. |
| `G2A3-CONFLICT-29` | Removing a rung moves RA3 strictly toward Attempt 1 on the one axis that produced Attempt 1's failure mode, so a larger drawdown was the declared cost of the change. | No variant breached the research shutdown and the deepest maximum drawdown across all 36 runs was 14.36% against a 15% limit. The declared risk did not materialise, which is a result and not a vindication of the reasoning. |
| `G2A3-CONFLICT-30` | `governance/*` is single-level and `config/**` is recursive, so this attempt's subtree splits down the middle of `repo_state_id`. | Both directions are asserted at build time and both hold. Widening the patterns is not available, because the patterns are themselves sealed by every earlier stage's digest. |
| `G2A3-CONFLICT-31` | `RotationEngineRA3` subclasses `RotationEngineRA1`, which belongs to a closed attempt. | It re-derives exactly the risk and sessions-in-band state it must after calling `super()`, which an AST test enforces. Subclassing reads the closed module without modifying it. |
| `G2A3-CONFLICT-32` | The dissimilarity denominator carries a floor of 1, so a pair that is zero on both sides scores 0 rather than dividing by zero. | Disclosed, not repaired. For the selected representative no pair was zero on both sides, so the floor did not decide this selection. |
| `G2A3-CONFLICT-33` | This is the third disclosed adaptation on one hypothesis family, and a PASS here would not on its own have distinguished which of the two changes produced it. | The attempt failed, so the question is moot for this result and remains live for the family. |
| `G2A3-CONFLICT-34` | 17 prior-attempt modules are held immutable, not the nine the operating instruction implies. | The count is read from the seal rather than typed into the package, so a silently shortened list fails loudly instead of passing. |
| `G2A3-CONFLICT-35` | This pre-registration was written after two attempts' development results were known, and both of its changes were chosen in response to the second. | Pre-registration constrains what happens after the seal; it cannot undo what was known before. The adaptation is disclosed verbatim in five carriers, the multiplicity is quantified, and no threshold was adjusted in either direction to compensate. Supersedes `G2A2-CONFLICT-6`'s scope. |
| `G2A3-CONFLICT-36` | Both fail routes of this attempt emit the same verdict token. | The route is recorded separately: `REPRESENTATIVE_FAILED_AT_LEAST_ONE_CONDITION`, which is the gate-reached-and-missed route and not Attempt 1's no-representative route. |
| `G2A3-CONFLICT-37` | Attempt 2's operating prompt named verdict tokens that existed in no artifact; Attempt 3's names none at all and directs that the sealed criteria file be grepped instead. | The failure mode is removed rather than resolved a second time. The tokens are minted once, in `SE100-CFG-3106`, and the four belonging to Attempts 1 and 2 are asserted absent from every Attempt 3 verdict field. Supersedes `G2A2-CONFLICT-8`'s scope. |
| `G2A3-CONFLICT-38` | Attempt 2's sealed pre-registration states that no Attempt 3 is authorized. | A stage artifact's self-imposed closure rule is not a constitutional provision and does not outrank the operator. What it does outrank is a silent reopening, which is not what happened: the adaptation is disclosed verbatim in five carriers and the decision package carries it in the sixth. |
| `G2A3-CONFLICT-39` | The sealed `mechanics_carried_unchanged.method` states that only the variant id format and the ids themselves differ from Attempt 2's. Compared pointer by pointer, four further pointers differ. | Three are additive provenance notes and the fourth is `gate_evaluation_scope.criteria_source`, which could not have been otherwise. None of the four is a mechanic. The seal is not edited; the checker implements the true predicate and reports the unused entries of both allow-lists, so a list that only ever widens shows up as evidence rather than passing quietly. |
| `G2A3-CONFLICT-40` | Two prose pointers were renamed between Attempt 2's criteria seal and Attempt 3's — `S3-C3`'s attempt note and `S3-C6`'s scope-interpretation significance note. | Both are evidence text read by no predicate. Attempt 2's evaluators are called unmodified against an adapted view binding the old names to the new values, and the adapter check proves the view differs from the seal in exactly those two pointers, that both aliases carry byte-identical values to their RA3 originals, and that the sealed object itself is unmutated. |
| `G2A3-CONFLICT-41` | Three lists of banned selection-input substrings exist and no two are equal. `ratio` and `factor` are named in the seal's AT-I prose and enforced by neither implementation, so a field named `information_ratio` would pass every substring check. | Widening an implemented list to match a prompt's prose is the one repair this project forbids, so the gap is asserted rather than closed. The frozen dataclass makes it moot on this attempt: the selection surface carries exactly six fields and no return field can reach it whatever the substring lists say. |
| `G2A3-CONFLICT-42` | The sealed adaptation disclosure reasons that the removed rung had suppressed ordinary-market returns as well as crisis losses. Half of that reasoning is confirmed by this attempt's own measurement and half is refuted. | The throttle did loosen — ladder descents fell from 1605 to 1008 across the same 36 runs. Grid returns did not improve: Attempt 2's grid was already positive on 18 of 18 base runs and its best run, +63.15%, exceeded this attempt's +53.41%. The representative moved off the grid floor because SEL-2 replaced the lowest-turnover rule, not because a rung was removed. Section 12 carries the three-way measurement; the sealed text is not edited. |

The full text of each, as written into the decision record, is in
`reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json` and in the decision record
this session's builder wrote. The table above is a summary and the JSON is the record.

---

## 19. What this session does not authorize

- **Not** Stage 4 validation. The validation window was not read and Stage 4 requires an explicit human
  go-ahead recorded in a later session.
- **Not** any read of a session at or after 2021-08-01, in this or any later stage.
- **Not** any read of Generation 1's holdout (2024-08-01 → 2026-07-31), which is spent and prohibited
  regardless of generation.
- **Not** any read of Generation 2's holdout (2026-08-01 → 2028-07-31), which is sealed and does not
  exist in calendar time.
- **Not** live trading, order placement, cancellation, replacement, liquidation or unattended
  scheduling. `live_trading_authorized` remains `false`.
- **Not** an Attempt 4. This attempt closes. Further work on this family requires a further disclosed
  adaptation and a separate authorization.
- **Not** promoting `L03-K1-QUARTERLY` or any other variant in place of the representative that failed.
- **Not** isolating the two changes by re-running either alone. An isolation run is a further attempt
  and requires its own authorization and its own disclosure of the multiplicity it adds.
- **Not** any adjustment to an RA3 constant, a SEL-2 quantity, weight or threshold, or the width of the
  grid.

---

## 20. What was not touched

This is a checked claim, not an assurance. Three mechanisms:

1. **Digest re-verification.** All 17 Attempt 1 and Attempt 2 modules were re-hashed
   against the digests their own run records recorded, at seal time and again after this session's work.
   `modules_that_moved` is empty in the evidence.
2. **Checksum records re-verified.** Attempt 1's and Attempt 2's `.sha256` records were re-run against
   the files they pin, from the directory holding the record. Every entry returned `OK`.
3. **New paths only.** Every file this session created is a new file in a new path. The eight `src/`
   modules carry `_ra3` or `_attempt3` in their names, the two test files are new, the two config
   artifacts and three governance artifacts are new, and `reports/stage3_g2_attempt3/` did not exist
   before this session.

The one exception, disclosed rather than buried: `README.md` was updated, and `README.md` is in
`repo_state_id`'s patterns. It is supposed to change — it is the tree's status page — and it was
rewritten before the decision package was built, not after. Nothing else tracked was modified.

`RotationEngineRA3` subclasses Attempt 2's `RotationEngineRA1`. Subclassing reads the closed module
without modifying it, and `AT-M` enforces that the subclass re-derives exactly the risk-dependent state
Attempt 2's `__init__` sets. `G2A3-CONFLICT-31`.

---

## 21. Tests

| Field | Value |
|---|---|
| Collected | 1265 |
| Passed | 1264 |
| Failed | 1 |
| Pre-existing floor | 1142 |
| New in this attempt | 123 |

The one failure is `test_no_stage_4_module_can_reach_restricted_data_or_a_broker`, the permanent red
recorded as `S4-CONFLICT-7` at Stage 4 and inherited untouched by every stage since. It is a test whose
own governance record documents why it fails and why it may not be repaired here. It was not weakened,
skipped, xfailed or deleted, and no test was.

The 123 new tests are distributed across the thirteen adversarial requirements of §7. The
existing suite is a permanent regression floor and this attempt added to it.

Full output: `reports/stage3_g2_attempt3/pytest_stage3_g2_attempt3_output.txt`. Per-requirement
breakdown: `reports/stage3_g2_attempt3/STAGE_3_G2_A3_TEST_SUMMARY.md`.

---

## 22. Artifacts

| Artifact | Path |
|---|---|
| Pre-registration (Markdown) | `governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md` |
| Pre-registration (JSON) | `governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json` |
| Pre-registration checksums | `governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256` |
| This report | `governance/generation_2/STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md` |
| Research JSON | `reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.json` |
| Evidence / decision input | `reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json` |
| Run-span recheck | `reports/stage3_g2_attempt3/run_span_recheck.json` |
| Test summary | `reports/stage3_g2_attempt3/STAGE_3_G2_A3_TEST_SUMMARY.md` |
| pytest capture | `reports/stage3_g2_attempt3/pytest_stage3_g2_attempt3_output.txt` |
| Protocol config | `config/generation_2/g2_rotation_ra3_protocol.json` |
| Gate criteria config | `config/generation_2/g2_gate_criteria_ra3.json` |

The decision record, artifact manifest, `.sha256` record and `runs/` reproducibility record were written
by the shared builder after this report was finished, and their names are in the manifest rather than
here — a report that named its own successor's filenames would be asserting something it cannot check.

The evidence JSON carries a self-digest field computed over the file with that field removed. Nothing
hashes itself: the surrounding `.sha256` record covers the evidence file, and the artifact manifest
excludes its own entry.

---

## 23. Reproduction

```bash
cd stockedge100
PYTHONPATH=src python -m stockedge100.strategies.g2_runner_ra3
PYTHONPATH=src python -m stockedge100.reporting.g2_stage3_attempt3_evidence
```

```bash
cd stockedge100
sha256sum -c governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256
```

Every path in this report is relative to the project root, `stockedge100/`, and so is every path inside
this attempt's checksum record — which is why that verification runs from `stockedge100/` and not from
the directory holding the record. The two conventions in this tree are not interchangeable, and both
were run in both directions before this sentence was written. `governance/STAGE_0_FREEZE.sha256` and
`governance/STAGE_1_FREEZE.sha256` carry bare filenames and verify only from `governance/`. Every
pre-registration record, this one included, carries project-root-relative paths and verifies only from
`stockedge100/`. Either one run from the wrong directory reports `FAILED open or read` on every line,
which is an operator error and not an integrity failure; the two are distinguishable in the output,
because a real integrity failure names the file and says `FAILED` without saying
`No such file or directory` first.

---

## 24. Next authorized action

**Human review of this package.** Nothing else.

Specifically not authorized without a separate, explicitly recorded human decision: Stage 4 validation,
an Attempt 4, an isolation run of either change, a fourth selection rule, any adjustment to RA3 or
SEL-2, and any read of any window at or after 2021-08-01.

---

## Verdict

```
FAIL — STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE
```

Gate 3 (development admissibility): **NOT PASSED**.

The risk architecture worked and the selection rule worked, in the narrow senses each was changed to
address. No variant breached the research shutdown, the ladder engaged 1008
times rather than 1605, the representative earned +10.34% rather
than +0.42%, and 6 of seven gate conditions were satisfied on both
runs. The attempt still fails, on a concentration condition that neither prior attempt failed in
isolation.

That is a more informative failure than either of the two before it. Attempt 1 said the signal cannot
survive 2008 unprotected. Attempt 2 said a protected version survives but, under a return-blind
corner-seeking selection rule, is represented by its least active and worst performing variant.
Attempt 3 says that with the throttle loosened and a stability-based representative, the specification
clears six of seven admissibility conditions and fails because its profits are concentrated in too few
symbols. A cross-sectional rotation holding one to three of thirty-four members is structurally
disposed to that outcome, which is a fact about the hypothesis family rather than about this
parameterisation.

Three adaptations have now been spent on this family and its development window has been read three
times. Whatever a fourth attempt would find, it would find on data that has told this researcher three
things already. That is the cost the disclosure in §2 exists to make visible, and it is the reason this
report ends here rather than with a proposal.

`live_trading_authorized`: `false`.
