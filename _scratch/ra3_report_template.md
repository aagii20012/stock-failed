# Stage 3 (Generation 2, Attempt 3) — rotation under a reverted ladder and a stability selection rule, development research report

| Field | Value |
|---|---|
| Document id | `SE100-GOV-2008` |
| Project | StockEdge100 |
| Generation | 2 |
| Generation id | `@@GENERATION_ID@@` |
| Stage | 3 — **Attempt 3** |
| Gate | 3 — development admissibility |
| Session type | Development research, single stage, single verdict |
| Candidate | `@@STRATEGY_ID@@` (candidate index 3) |
| Governing document | `SE100-GOV-0001` (constitution, FROZEN) §§3, 4, 5.1, 6, 7, 9 gate 3, 10, 11, 19 |
| Charter | [STAGE_10_GENERATION_2_CHARTER.md](STAGE_10_GENERATION_2_CHARTER.md) (`SE100-GOV-2001`) |
| Partition lock | [STAGE_1_G2_PARTITION_LOCK.md](STAGE_1_G2_PARTITION_LOCK.md) (`SE100-GOV-2002`) |
| Attempt 1 | [STAGE_3_G2_ROTATION_RESEARCH_REPORT.md](STAGE_3_G2_ROTATION_RESEARCH_REPORT.md) (`SE100-GOV-2004`) — **CLOSED, READ-ONLY** |
| Attempt 2 | [STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md](STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md) (`SE100-GOV-2006`) — **CLOSED, READ-ONLY** |
| Pre-registration | [STAGE_3_G2_ROTATION_RA3_PROTOCOL.md](STAGE_3_G2_ROTATION_RA3_PROTOCOL.md) (`SE100-GOV-2007`, sealed before any Attempt 3 code existed) |
| Protocol config | `config/generation_2/g2_rotation_ra3_protocol.json` (`SE100-CFG-3105`) |
| Gate criteria | `config/generation_2/g2_gate_criteria_ra3.json` (`SE100-CFG-3106`) |
| Evidence | `reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json` (`SE100-EVID-3103`) |
| Development window read | @@WINDOW_START@@ → @@BOUND@@ (run span @@RUN_START@@ → @@RUN_END@@, @@SESSIONS@@ sessions) |
| Latest session loaded | @@LATEST_LOADED@@ |
| Validation window | 2021-08-01 → 2024-07-31 — **not read** |
| Generation 1 holdout | 2024-08-01 → 2026-07-31 — **spent and prohibited, not read** |
| Generation 2 holdout | 2026-08-01 → 2028-07-31 — **sealed; does not exist in calendar time** |
| Authored (UTC) | @@AUTHORED_UTC@@ |
| Verdict | `@@VERDICT@@` |
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
stressed one, over @@RUN_START@@ → @@RUN_END@@ (@@SESSIONS@@ sessions). That is 36 runs. The grid, the
signal, the universe, the calendar, the cost model and the gate thresholds are Attempt 2's, unchanged.
Two things changed, both disclosed before the run: the de-risk ladder lost one rung, and the
representative-selection rule was replaced.

Four findings, in the order they were established:

1. **The reverted ladder measurably loosened the throttle, and no variant breached the research
   shutdown.** Across the 36 runs the ladder descended @@S:LAD_LADDER_DESCENTS_A3@@ times against
   Attempt 2's @@S:LAD_LADDER_DESCENTS_A2@@, blocked @@S:LAD_LOCKOUT_RECOVERIES_BLOCKED_A3@@ recoveries
   against @@S:LAD_LOCKOUT_RECOVERIES_BLOCKED_A2@@, and held full sizing on
   @@S:LAD_FULLSIZE_A3@@ sessions against @@S:LAD_FULLSIZE_A2@@. Every one of those statistics differs
   from Attempt 2's on at least @@S:LAD_STOPS_FILLED_DIFFERING@@ of the 36 runs and three of them on all
   36. Zero shutdown events were recorded, and the deepest maximum drawdown anywhere in the grid was
   @@S:A3_DD_MAX_STRESS_PCT@@ against a 15% ceiling — so the declared cost of removing a rung (SC-8)
   did not materialise.
2. **Ordinary-market returns came back, but not because of the ladder.** The grid returned
   @@S:A3_RET_MIN_PCT@@ to @@S:A3_RET_MAX_PCT@@ on base with a median of @@S:A3_RET_MEDIAN_PCT@@, and
   @@S:A3_POS_BASE@@ of 18 variants were positive. Attempt 2's grid, however, was *also*
   @@S:A2_POS_BASE@@ of 18 positive, with a higher best (@@S:A2_RET_MAX_PCT@@ against
   @@S:A3_RET_MAX_PCT@@) and a similar median (@@S:A2_RET_MEDIAN_PCT@@ against
   @@S:A3_RET_MEDIAN_PCT@@). What changed is *which* variant the selection rule picked, not what the
   grid earned. §12 states this plainly, because the sealed adaptation disclosure's reasoning is only
   partly borne out and the part that is not borne out is the part about returns.
3. **A representative exists, and it is not the grid's floor.** SE100-G2-SEL-2 selected
   `@@S:REPRESENTATIVE_SHORT@@` on a neighbourhood-instability score of @@S:REP_SCORE@@ over
   @@S:REP_NEIGHBOURS@@ neighbours, ahead of `@@S:RUNNER_UP@@` at @@S:RUNNER_UP_SCORE@@ — a margin of
   @@S:SEL_MARGIN@@. It ranks @@S:A3_REP_RANK_BY_RETURN@@ of 18 by return. Attempt 2's rule, applied to
   this grid, would have selected `@@S:A3_LOWEST_TURNOVER_VARIANT@@` at @@S:A3_LOWEST_TURNOVER_RET_PCT@@,
   which is this grid's *minimum*. The change of representative is attributable to SEL-2 and not to RA3.
4. **The gate failed on one condition, and it is a condition neither prior attempt failed alone.**
   @@S:CONDITIONS_MET@@ of the seven Gate 3 conditions are MET on both runs. The sole failure is
   **S3-C6**, the concentration condition: @@S:S3_C6_BASE_PCT@@% of the representative's gross profit
   came from its largest contributor on base and @@S:S3_C6_STRESS_PCT@@% on stress, against a ceiling of
   @@S:S3_C6_THRESHOLD_PCT@@%.

The verdict is `@@VERDICT@@`, on the sealed second fail route —
`@@FAIL_ROUTE@@` — not Attempt 1's no-representative route. Both routes
emit the same token by seal; the route is recorded separately in the decision record and here.

---

## 2. Why this attempt exists, and what it costs

Attempt 1 ran the rotation grid with no risk architecture. All eighteen variants breached the
constitutional research-shutdown drawdown ceiling — @@S:A1_RUNS_SHUTDOWN@@ of 36 runs, with
@@S:A1_SHUTDOWN_EVENTS@@ shutdown events — and no representative could be selected at all. Attempt 2
added a five-component risk architecture and every variant survived, but its representative-selection
rule preferred the variant that traded least, which on that grid was also that grid's worst-returning
variant, and the gate failed. This attempt was designed **after** both of those results were seen.

The constitution does not forbid an adaptation. It forbids a silent one. The sealed protocol therefore
carries a single paragraph of disclosure that must appear byte-identically wherever this attempt's
development result is referenced. It was substituted here mechanically from the sealed file, as a
single unbroken block, so that byte-identity is checkable by string comparison rather than asserted:

> @@ADAPTATION_DISCLOSURE@@

The sealed carriage requirement states the enforcement:

> @@DISCLOSURE_ENFORCEMENT@@

The five required carriers are the protocol Markdown, the protocol JSON, this report, the research JSON
and the evidence JSON. The decision record produced by the package builder is a sixth. The string is
@@DISCLOSURE_LEN@@ characters of UTF-8 and its SHA-256 is `@@DISCLOSURE_SHA@@`; Attempt 2's equivalent
was 842 characters. It carries two non-ASCII characters that a reader diffing the attempts should
expect: U+2014 EM DASH, as every governance artifact in this tree does, and U+2212 MINUS SIGN in the
phrase naming the removed tier. No diagnostic script in this session printed the string; they compared
it and reported a boolean.

The sealed statement of what changed, in the protocol's own words:

> @@WHAT_THIS_CHANGES@@

And the lineage statement carried forward unchanged from Attempt 2's protocol, describing the
architecture this attempt still runs minus one rung:

> @@WHAT_THIS_ADDS@@

Two things changed rather than one, which means this attempt cannot attribute its outcome to either.
That was stated before the run and is restated in §17 and as `G2A3-CONFLICT-33`. It bounds the
*attribution*. It does not bound the multiplicity, which is now three adaptations on one hypothesis
family and is disclosed as such.

---

## 3. What was sealed before any code existed

| Field | Value |
|---|---|
| Seal run id | `@@SEAL_RUN_ID@@` |
| Sealed (UTC) | @@SEAL_UTC@@ |
| `repo_state_id` at seal | `@@SEAL_REPO_STATE_ID@@` |
| Protocol Markdown | `STAGE_3_G2_ROTATION_RA3_PROTOCOL.md` — `@@SHA_PROTOCOL_MD@@` |
| Protocol JSON | `STAGE_3_G2_ROTATION_RA3_PROTOCOL.json` — `@@SHA_PROTOCOL_JSON@@` |
| Protocol config | `config/generation_2/g2_rotation_ra3_protocol.json` — `@@SHA_PROTOCOL_CFG@@` |
| Gate criteria | `config/generation_2/g2_gate_criteria_ra3.json` — `@@SHA_CRITERIA@@` |
| Cost model | `config/generation_2/g2_cost_model.json` — `@@SHA_COST_MODEL@@` |
| Partition lock JSON | `STAGE_1_G2_PARTITION_LOCK.json` — `@@SHA_LOCK_JSON@@` |
| Charter | `STAGE_10_GENERATION_2_CHARTER.md` — `@@SHA_CHARTER@@` |

Every digest in that table was recomputed from the named file by the renderer that wrote this document
and compared against the value the sealer recorded. A mismatch would have refused the render.

**How "before any code" is measured.** Attempt 1's predicate was path-based: it refused to seal if any
module basename under `strategies/` or `backtest/` contained `g2_`. That test was correct when
`strategies/` held no Generation 2 code, and by Attempt 3 it is vacuous — Attempt 1's own modules live
there and are supposed to. Attempt 2 replaced it with a content-based predicate and Attempt 3 carries
that form:

> @@DECL_PREDICATE@@

That is a statement about the contents of every `.py` file in the tree at seal time, not about a list
of filenames, and it is re-checkable after the fact against the sealed `repo_state_id`. The sealing
program is itself a `.py` file under `src/` and would falsify the predicate if it named the candidate id
as a literal; it loads the id from the protocol config at run time instead, and the protocol discloses
that indirection rather than leaving it to be found.

The predicate is paired with an immutability check, which is the half that matters here. Every one of
the **@@S:MODULE_COUNT@@** Attempt 1 and Attempt 2 modules was re-hashed at seal time against the digest
its own run record recorded, and again after this session's work. None moved. The count is read from the
seal rather than typed, so a silently shortened list fails loudly; the operating instruction for this
attempt implies nine modules and the sealed figure is @@S:MODULE_COUNT@@, which is
`G2A3-CONFLICT-34`.

Everything the gate would later depend on was fixed at that moment: the eighteen variant ids and their
enumeration order, the three RA3 ladder bands and their scalars, the four other RA3 constants, the
six-field selection input, the four selection steps, the seven gate conditions and their thresholds, the
two verdict tokens, and the run span the runner would be required to reproduce.

---

## 4. Window, bound and run span

The development bound is @@BOUND@@ and the last session inside it is @@LATEST_LOADED@@. The window guard
is `stockedge100.strategies.g2_window_guard`, imported unmodified from Attempt 1 rather than
re-derived: every series is truncated while parsing, not after, and the bound is re-asserted after
loading. A second derivation of the same bound is a second place for it to be wrong.

The run span is not merely quoted from Attempt 2's protocol. The Attempt 3 runner **refuses to run** if
any value differs from the sealed one, recomputes all of it from the loaded series, and writes the
recomputation to `reports/stage3_g2_attempt3/run_span_recheck.json`. The recheck recorded zero
differences.

| Field | Value |
|---|---|
| Development window | @@WINDOW_START@@ → @@BOUND@@ |
| Run span | @@RUN_START@@ → @@RUN_END@@ |
| Sessions in the run | @@SESSIONS@@ |
| Development union sessions | @@UNION_SESSIONS@@ |
| Binding symbol | `@@BINDING_SYMBOL@@` (inception @@BINDING_INCEPTION@@) |

The run starts twelve months after the binding symbol's inception because the longest lookback in the
grid is twelve months and a ranking signal may not be computed from a partial history. The scheduled
rebalance counts on this session list are @@MONTHLY_REB@@ monthly and @@QUARTERLY_REB@@ quarterly, both
recomputed by the runner and both equal to the sealed values.

No session at or after 2021-08-01 was read by any module in this session. The three prohibited windows
are recorded in the evidence with explicit read-flags, all false.

---

## 5. Universe

| Field | Value |
|---|---|
| Source | `governance/STAGE_1_UNIVERSE.json` |
| Universe version | `@@UNIVERSE_VERSION@@` |
| Identity digest | `@@UNIVERSE_IDENTITY@@` |
| Members | @@MEMBERS@@ |
| Members eligible at run start | @@MEMBERS@@ of @@MEMBERS@@ |
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

> @@SINGLE_DIFF@@

**The change removes a degree of freedom rather than adding one.** RA2's ladder had four bands, and
Attempt 2's own protocol recorded that only its band 1 — the `[0.05, 0.08)` rung at scalar `0.75` — was
new relative to Generation 1's sealed RA1-5. Deleting it leaves:

> @@LADDER_PROVENANCE@@

Expressed as absolute ceilings, which is the form that makes the identity checkable:

> @@LADDER_ABS_CEILINGS@@

The evidence records `ladders_are_identical: @@S:LADDERS_IDENTICAL@@` against Generation 1's RA1-5, and
records the deleted tier explicitly as the triple @@S:DELETED_TIER@@ — one threshold and one scalar,
which the protocol counts as @@DOF_REMOVED@@.

The combined scalar is unchanged in form:

> `@@COMBINED_FORMULA@@`

It applies to the entry budget at the fill open and to the aggregate ceiling at every session. It does
**not** apply to the per-position stop, which is an absolute condition on price, or to the
constitutional research shutdown, which belongs to the engine and was not modified.

The ladder's asymmetry is the mechanism and is unchanged: descent is immediate and to the full computed
band, recovery is at most one band per session and only after the lockout has elapsed. Under RA3 a
recovery from the deepest band to full sizing needs at least two sessions after expiry; under RA2 it
needed three. Band boundaries remain closed below and open above, so a drawdown of exactly 0.08 is
band 1.

**What would have falsified the reasoning.** The protocol declared this before the run:

> @@LADDER_FALSIFY@@

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
| `AT-H` | all @@S:MODULE_COUNT@@ prior-attempt modules re-hash to their recorded digests |
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

The cost model is `config/generation_2/g2_cost_model.json` (`@@SHA_COST_MODEL@@`), sealed at Stage 1 of
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

> @@WHY_NOT_GRIDDED@@

---

## 10. Representative selection: `SE100-G2-SEL-2`

The rule replaces Attempt 2's unnamed lowest-turnover rule, which selected
`@@S:A2_REPRESENTATIVE@@`. Four steps, frozen before any variant ran:

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

> @@SEL2_MECHANISM@@

> @@SEL2_IMPORT_ASSERTION@@

The neighbour relation, sealed:

> @@SEL2_NEIGHBOURS_DEF@@

> @@SEL2_NEIGHBOUR_COUNTS@@

The operating instruction for this attempt described neighbourhoods of 2, 3 or 4 variants. The sealed
geometry on this grid gives 3, 4 or 5, and the representative has @@S:REP_NEIGHBOURS@@. The sealed
geometry governs; the instruction's counts are not repeated as fact anywhere in this package. That is
`G2A3-CONFLICT-27`.

**Why the rule changed.** The sealed reasoning, which is about the shape of the old rule and not about
any return it produced:

> @@SEL2_WHY@@

**What was checked retrospectively, and what was not.**

> @@SEL2_RETRO@@

> @@SEL2_RETRO_NOT@@

> @@SEL2_RETRO_WHY@@

**No reselection.**

> @@NO_RESELECTION@@

A declared structural consequence that turned out to matter, `SC-7`:

> @@SC7_CONSEQUENCE@@

The per-quantity components are therefore in §14's neighbour table rather than left to be inferred.
On this grid the architecture engaged often enough that the score is not a pure fill-count rule, but
`fill_count` is visibly the largest of the four components for the representative.

---

## 11. Step 1: the eligibility screen

All eighteen variants recorded zero research-shutdown events across both runs. Eighteen variants
survived step 1 and the no-representative fail route was not taken. This is the first attempt in the
family where the screen eliminated nothing and a representative was chosen on the stability criterion
rather than by survival.

@@TABLE_RANKING@@

The selected variant is rank 1 by score. `@@S:RUNNER_UP@@` is @@S:SEL_MARGIN@@ behind — a margin
smaller than one part in four thousand of either score. The two variants differ on one axis (`k`), which
is exactly the situation step 3 exists for, and step 3 was **not** reached because the scores are not
equal. §17 records what that narrow margin does and does not mean.

---

## 12. Attempt 1, Attempt 2, Attempt 3

The three grids are the same eighteen parameterisations over the same sessions with the same signal and
the same costs. Only the risk architecture and the selection rule differ. Row-by-row comparison is
therefore meaningful, which is unusual and is a consequence of the grid never having been widened.

@@TABLE_THREEWAY_AGG@@

The token row withholds Attempt 1's and Attempt 2's verdict tokens rather than reproducing them.
The sealed `prior_attempt_tokens_note` in this attempt's evidence states that no Attempt 3 artifact
may emit any of the four tokens belonging to the two closed attempts. The emitter that built the
table read both prior tokens from the closed attempts' own admissibility records, asserted that each
is on this attempt's withheld list and that neither equals this attempt's own token, and emitted the
result of that assertion together with the path that carries the string. The renderer refuses if any
of the four reaches this document.

@@TABLE_A1_A2_A3@@

Attempt 1's shutdowns were not spread evenly. They cluster in the 2008–2011 window:

@@TABLE_A1_MONTHS@@

**Three things this table establishes, and one it refutes.**

*Established.* Attempt 1's failure was not marginal: its best maximum drawdown anywhere on base was
@@S:A1_DD_MIN_PCT@@, so every Attempt 1 variant would have failed the 15% condition `S3-C2` even if the
research shutdown had not fired first. Attempt 2 and Attempt 3 both eliminated that failure mode
completely — zero shutdowns, worst drawdowns @@S:A2_DD_MAX_PCT@@ and @@S:A3_DD_MAX_PCT@@ on base. And
RA3's looser ladder did not cost drawdown control: its worst base drawdown is within a fifth of a
percentage point of RA2's, and its best is @@S:A3_DD_MIN_PCT@@ against RA2's @@S:A2_DD_MIN_PCT@@.

*Refuted.* The sealed disclosure reasons that RA2's 5% rung was "a plausible cause of RA2's
near-constant throttling", with the implication that removing it would recover suppressed
ordinary-market return. The throttling half is confirmed — §16's comparison is unambiguous. The return
half is not. Attempt 2's grid was already @@S:A2_POS_BASE@@ of 18 positive, with a **higher** maximum
(@@S:A2_RET_MAX_PCT@@ against @@S:A3_RET_MAX_PCT@@) and a median within two points of Attempt 3's. The
grid did not need rescuing. What produced Attempt 2's @@S:A2_REP_RET_PCT@@ headline was its
*selection rule*: `lowest turnover` chose the variant with the fewest fills (@@S:A2_REP_FILLS@@, rank
@@S:A2_REP_FILLS_RANK@@ of 18), and on that grid the least-active variant was also the
worst-returning one — `A2_REP_IS_WORST` is `@@S:A2_REP_IS_WORST@@`, at rank
@@S:A2_REP_RANK_BY_RETURN@@ of 18 by return.

The same rule applied to *this* grid would have selected `@@S:A3_LOWEST_TURNOVER_VARIANT@@` at
@@S:A3_LOWEST_TURNOVER_RET_PCT@@ — again the grid minimum, and again the same parameterisation. So the
representative moved off the floor because **SEL-2** replaced a corner-seeking criterion with a
dispersion one, not because RA3 loosened the ladder. Stated as a counterfactual it is stark: RA3 alone,
under Attempt 2's rule, would have produced a representative earning @@S:A3_LOWEST_TURNOVER_RET_PCT@@
over thirteen years; SEL-2 alone, on Attempt 2's grid, would have selected some other variant from a
grid whose median was @@S:A2_RET_MEDIAN_PCT@@.

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

The representative is `@@S:REPRESENTATIVE@@`, selected before any gate condition was evaluated.

@@TABLE_GATE@@

**Scope.** `SE100-CFG-3105` scopes the gate across both runs; `SE100-CFG-3106` lists the stressed run as
reported-but-not-gating for `S3-C1` and `S3-C4`. Neither outranks the other, so the more restrictive
reading governs and both readings are reported. Here they agree: the permissive base-only reading would
give `@@PERMISSIVE_READING@@`. `G2A2-CONFLICT-25`, inherited and resolved the same way.

**Outcome.**

| Field | Value |
|---|---|
| Conditions evaluated | 7 |
| Satisfied on both runs | @@S:CONDITIONS_MET@@ |
| Not satisfied on `#BASE` | @@S:BASE_NOT_SATISFIED@@ |
| Not satisfied on `#STRESS` | @@S:STRESS_NOT_SATISFIED@@ |
| Fail route | `@@FAIL_ROUTE@@` |
| Candidates evaluated | 1 |
| Admitted candidates | 0 |
| `admissible_candidate_exists` | **false** |

The last line of that table is the one that decides the stage. The seven condition rows are conjunctive
within a candidate and the stage verdict is a disjunction across candidates; with one live candidate the
disjunction is over a one-member set, which is `G2A3-CONFLICT-24`.

**Where the representative actually fails.** `S3-C6` requires that no single symbol contribute more
than @@S:S3_C6_THRESHOLD_PCT@@% of gross profit. The representative's largest contributor supplied
@@S:S3_C6_BASE_PCT@@% on base and @@S:S3_C6_STRESS_PCT@@% on stress, from @@S:REP_SYMBOLS@@ distinct
symbols traded over @@S:REP_TRADES@@ closed trades. The condition text is a concentration test, and a
`k`-of-34 rotation that spends much of thirteen years in a small number of persistent leaders is
structurally exposed to it. Attempt 2's representative failed the same condition more severely
(@@S:A2_C6_BASE@@ and @@S:A2_C6_STRESS@@ as ratios against a 0.50 ceiling), so this is not a new failure
mode — but Attempt 2 failed three other conditions alongside it on base and four on stress, and this
attempt fails only this one.

Everything else clears with margin: return @@S:REP_BASE_RET_PCT@@ base and @@S:REP_STRESS_RET_PCT@@
stress, maximum drawdown @@S:REP_DD_BASE_PCT@@ and @@S:REP_DD_STRESS_PCT@@ against 15%, profit factor
@@S:S3_C3_BASE_PF@@ and @@S:S3_C3_STRESS_PF@@ against 1.10, @@S:REP_TRADES@@ closed trades against 30,
and the best-trade-removed return positive on both removals in both runs. The neighbourhood-stability
condition `S3-C7` is `@@S:A3_C7_STRESS_MEASURED@@` on stress, where Attempt 2's representative measured
`@@S:A2_C7_STRESS_MEASURED@@`.

**A measurement note that matters.** Two profit-factor figures exist for this representative and they
differ. The gate reads the episode ledger, which pairs each entry with its eventual exit across
throttle trims and partial reductions, and it measures @@S:S3_C3_BASE_PF@@ on base. The engine's own
`Portfolio.trades` recorder measures @@S:REP_PF_RECORDER@@ on base and @@S:REP_PF_RECORDER_STRESS@@ on
stress. The divergence is not an error in either: a throttle trim closes part of a position in the
recorder's view and does not close an episode in the ledger's, so the two count different things. The
gate condition names closed trades, the ledger is the thing that has them, and the ledger figure is the
one the gate used. The recorder figure is reported so that a reader recomputing from the trade payload
does not conclude the gate was mis-measured. `G2A2-CONFLICT-18`, inherited.

**Selection traced, not asserted.** The scores below are SEL-2's own computed output, read from the
evidence rather than recomputed in prose. The representative's neighbourhood and the four
per-quantity mean dissimilarities that produce its score:

@@TABLE_NEIGHBOURS@@

And the raw quantities those dissimilarities are computed from, summed across both runs:

@@TABLE_OWN@@

The representative's score of @@S:REP_SCORE@@ is the mean of its four component means over its
@@S:REP_NEIGHBOURS@@ neighbours. `ladder_descents` and `lockout_arms` are numerically identical
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

@@TABLE_BASE@@

**Stressed cost model.**

@@TABLE_STRESS@@

@@S:A3_POS_BASE@@ of 18 variants are positive on base and @@S:A3_POS_STRESS@@ of 18 on stress. The best
base return in the grid is `@@S:BEST_VARIANT@@` at @@S:BEST_RET_PCT@@, with a maximum drawdown of
@@S:BEST_DD_PCT@@, a profit factor of @@S:BEST_PF@@ and @@S:BEST_TRADES@@ closed trades. It was not
selected: its instability score is @@S:BEST_SCORE@@, rank @@S:BEST_RANK@@ of 18. Re-selecting on return
is forbidden and was not done.

---

## 16. Risk-architecture statistics

**Per variant, base run.**

@@TABLE_RISK_BASE@@

**Per variant, stressed run.**

@@TABLE_RISK_STRESS@@

**The comparison the operating instruction requires.** RA3's ladder statistics must be shown to differ
from Attempt 2's, or the change was aimed at the wrong mechanism:

@@TABLE_LADDER_AB@@

Every one of those seven statistics differs, on between @@S:LAD_STOPS_FILLED_DIFFERING@@ and all 36
runs. The direction is uniform on the throttling measures: fewer descents, fewer ascents, far fewer
blocked recoveries, and @@S:LAD_FULLSIZE_A3@@ sessions at full sizing against
@@S:LAD_FULLSIZE_A2@@ — an increase of about forty-five percent in the time the strategy was allowed to
be fully invested. The stop measures move the other way, and that is expected rather than surprising:
larger positions reach an 8%-from-basis condition more often, so `stops_triggered` rose from
@@S:LAD_STOPS_TRIGGERED_A2@@ to @@S:LAD_STOPS_TRIGGERED_A3@@ while `stops_filled` rose only from
@@S:LAD_STOPS_FILLED_A2@@ to @@S:LAD_STOPS_FILLED_A3@@.

**Band depth.** RA3 has three bands, not four, so no `band 3` figure exists for this attempt and none is
reported. Band 0 is full sizing.

@@TABLE_BAND_DEPTH@@

Every variant reached at least band 1 in both runs, and @@S:BAND2_COUNT@@ of 18 on base reached the
deepest band. @@S:BAND0_COUNT@@ variants stayed in full sizing throughout, which means the ladder
engaged on the whole grid and the SC-7 degenerate case did not occur.

**Two regimes in the stop numbers.** Across the grid @@S:STOPS_TRIGGERED@@ stop conditions were observed
and @@S:STOPS_FILLED@@ became fills, a ratio of @@S:STOP_FILL_RATIO@@, with @@S:STOPS_PREEMPTED@@
pre-empted — a stop condition observed on a session where a scheduled exit or a throttle trim had
already taken precedence for that symbol. The pre-empted column is not a lost exit: the position was
being closed or reduced anyway, by a rule with higher precedence. The ratio is low because the stop
condition is re-observed on every subsequent session until the position leaves the book, so one
underwater position can contribute many triggers and one fill. @@S:STOP_OUTLIER_COUNT@@ variant-runs
show that pattern at extremes; the widest is @@S:STOP_OUTLIER_MAX@@.

**Throttle and exposure, base run.**

@@TABLE_THROTTLE@@

Two columns deserve reading carefully. **Sessions breaching the ceiling** is non-zero for every variant,
with maximum gross fractions from @@S:GROSS_MIN_PCT@@ to @@S:GROSS_MAX_PCT@@ against a 50% ceiling. That
is not a broken clamp. The clamp binds at the fill open; between opens the held positions appreciate,
and an appreciation that carries gross above the ceiling is detected at the next close and trimmed at the
following open. The excess ranges from @@S:GROSS_EXCESS_MIN_PCT@@ to @@S:GROSS_EXCESS_MAX_PCT@@ of
equity and is the one-session execution lag made visible, which the protocol declared.

**Combined scalar.** Its minimum anywhere in the grid is @@S:SCALAR_MIN_OBSERVED@@ and its per-variant
means run from @@S:SCALAR_MEAN_MIN@@ to @@S:SCALAR_MEAN_MAX@@. Attempt 2's per-variant means ran from
@@S:A2_SCALAR_MEAN_MIN@@ to @@S:A2_SCALAR_MEAN_MAX@@; on base alone Attempt 3's run from
@@S:A3_SCALAR_MEAN_MIN_BASE@@ to @@S:A3_SCALAR_MEAN_MAX_BASE@@. The strategy still spends a great deal
of its life below full sizing — the representative alone is below 1 on @@S:REP_SCALAR_BELOW_ONE@@
sessions with a mean of @@S:REP_SCALAR_MEAN@@ and a minimum of @@S:REP_SCALAR_MIN@@ — because the
volatility term is unchanged and it, not the ladder, accounts for most of the throttling that remains.
Removing a ladder rung did not remove `f_vol`, and a reader looking for the ladder change in the scalar
means will find only part of it there.

**Turnover and the instability score.**

@@TABLE_TURNOVER@@

Fill counts span @@S:A3_FILLS_MIN@@ to @@S:A3_FILLS_MAX@@ across the grid — a factor of five — while
ladder descents span only @@S:DESCENTS_MIN@@ to @@S:DESCENTS_MAX@@ and lockout arms @@S:LOCKOUT_MIN@@ to
@@S:LOCKOUT_MAX@@. That spread is why `fill_count` dominates the instability score, exactly as `SC-7`
predicted it might.

---

## 17. Limitations

**17.1 This is the third disclosed adaptation on one hypothesis family.** The verbatim disclosure in §2
is the binding statement. Cumulative multiplicity across the family is now @@S:CUM_VARIANTS@@ variants
and @@S:CUM_RUNS@@ runs, and the sealed protocol is explicit that these are not independent tests:

> @@MC_ADAPTIVE@@

No correction is applied to the thresholds, and the reason is not convenience:

> @@MC_NOCORR@@

> @@MC_THIRD@@

**17.2 The development window has now been read three times.** It is not pristine and cannot be made so.
The validation window carries its own disclosed cost, sealed in the partition lock before any of this:

> @@VALIDATION_REUSE@@

**17.3 Two changes, one result.** RA3 and SEL-2 changed together. §12 shows their effects are separable
in *direction* — the throttle statistics moved because of RA3, the representative moved because of SEL-2
— but that is an argument from the counterfactual application of each rule, not a controlled comparison.
No run was made with one change alone, and making one is explicitly not authorized. `G2A3-CONFLICT-33`.

**17.4 This is a development result.** It is in-sample by construction. A development FAIL is
informative in one direction only: it says this specification does not clear the admissibility floor on
data it was allowed to see. It says nothing about out-of-sample behaviour, because there is no
out-of-sample evidence to say it with.

**17.5 The verdict is bounded by the run span.** @@RUN_START@@ → @@RUN_END@@ is one sample of one
market regime sequence. The @@SESSIONS@@ sessions include 2008, 2010, 2011, 2015, 2018 and 2020,
which is a reasonable variety of drawdowns and not a guarantee of coverage.

**17.6 Better variants exist in the grid and were not selected.** `@@S:BEST_VARIANT@@` returned
@@S:BEST_RET_PCT@@ against the representative's @@S:REP_BASE_RET_PCT@@ and would very likely have passed
`S3-C1` through `S3-C5`. Whether it would have passed `S3-C6` is not stated here, because the gate was
not run on it and running it now would be a search over eighteen candidates for one that passes.
Re-selecting on return is forbidden and was not done.

**17.7 The selection margin is very narrow.** @@S:SEL_MARGIN@@ separates the representative from
`@@S:RUNNER_UP@@`. A rule whose top two candidates differ by one part in four thousand is, on this grid,
close to indifferent between them, and a trivially different dissimilarity denominator or a different
choice among the four quantities could reverse the order. The rule is sealed and the order it produced
stands, but its discriminating power at the top of the ranking should not be overstated. Note also that
the runner-up is `@@S:A3_LOWEST_TURNOVER_VARIANT@@`'s sibling on the `k` axis rather than a distant
variant, so the near-tie is between two adjacent parameterisations and not between two different
strategies.

**17.8 The dissimilarity denominator carries a floor of 1.** A pair that is zero on both sides scores 0
rather than dividing by zero. That is disclosed rather than repaired, and for the representative no pair
was zero on both sides. `G2A3-CONFLICT-32`.

**17.9 The exposure ceiling was exceeded on sessions in every variant.** By between
@@S:GROSS_EXCESS_MIN_PCT@@ and @@S:GROSS_EXCESS_MAX_PCT@@ of equity, for one session at a time, by the
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
drawdown anywhere was @@S:A3_DD_MAX_STRESS_PCT@@ and no variant shut down. That the declared risk did
not materialise is a result, not a vindication of the reasoning that predicted it, and on a different
thirteen-year window it could go the other way. `G2A3-CONFLICT-29`.

**17.13 Costs are modelled, not observed.** No order was placed, no broker or credential was reachable
from any module in this attempt, and the fills are the engine's own simulation under a frozen cost
model.

---

## 18. Conflicts

The numbering is one space shared by `SE100-CFG-3105` and `SE100-CFG-3106`. `SE100-CFG-3105` states the
rule, and this is its text rather than a paraphrase of it:

> @@CONFLICT_NUMBERING@@

Read "this file" there as `SE100-CFG-3105`. Four ids below 26 therefore carry the `G2A3` prefix and are
Attempt 3 ids, not Attempt 2 ids: the prefix is what makes `G2A3-CONFLICT-19` and `G2A2-CONFLICT-19` two
distinct entries. Ids 34 to 38 were taken by the protocol config before the run. Ids 39, 40 and 41 were
taken during implementation, in `g2_rotation_ra3.py`, `g2_gate_ra3.py` and
`test_g2_sel2_selection_rule.py`. Id 42 is taken by this session's decision package, and 43 is free.

| Id | Conflict | Resolution |
|---|---|---|
| `G2A3-CONFLICT-19` | One of RA2's three ladder rungs is gone, so the engineered component of any MET verdict here is smaller than Attempt 2's by exactly that rung and no more. | Recorded in the sealed criteria before the run. Supersedes `G2A2-CONFLICT-18`'s scope. |
| `G2A3-CONFLICT-21` | The operating instruction names no verdict token at all, which is a change from both prior attempts. | The token was derived from `SE100-CFG-3106`'s `verdict_token_derivation`, which is the disk. The builder asserts the derived string against the evidence's own rather than restating a literal. |
| `G2A3-CONFLICT-22` | Across three attempts one hypothesis family has now been run under three ladder geometries — none at all, 5/8/10, and 8/10 — which is a search over risk architectures and not a robustness test of one. | Disclosed, not repaired. Carried forward as @@S:CUM_VARIANTS@@ cumulative variants and @@S:CUM_RUNS@@ cumulative runs on one family. |
| `G2A3-CONFLICT-24` | Candidate index 3 is the only live candidate, so the constitution's cross-candidate disjunction is taken over a one-member set. | The gate is decided by the `admissible_candidate_exists` row alone; the seven condition rows settle nothing on their own. |
| `G2A2-CONFLICT-25` | `SE100-CFG-3105` scopes the gate across both runs while `SE100-CFG-3106` lists the stress run as reported-but-not-gating for `S3-C1` and `S3-C4`, and neither outranks the other. | Inherited and resolved as Attempt 2 resolved it. The more restrictive reading governs and both readings are reported in full; here they agree — the permissive base-only reading gives `@@PERMISSIVE_READING@@`. |
| `G2A3-CONFLICT-26` | SEL-2 reads dispersion across a neighbourhood where Attempt 2's rule read a level, and the sealed protocol states plainly that Attempt 2's rule was the more conservative of the two. | This is the reason Attempt 3 required its own pre-registration rather than a re-run of Attempt 2's. |
| `G2A3-CONFLICT-27` | The operating instruction describes neighbourhoods of 2, 3 or 4 variants; the sealed geometry on this grid gives 3, 4 or 5, and the representative has @@S:REP_NEIGHBOURS@@. | The sealed geometry governs. The instruction's counts are not repeated as fact anywhere in this package. |
| `G2A3-CONFLICT-28` | `SE100-CFG-3103`'s closure sentence states that no Attempt 3 is authorized by that file. | Satisfied by the operating instruction, which authorizes one attempt and no more. |
| `G2A3-CONFLICT-29` | Removing a rung moves RA3 strictly toward Attempt 1 on the one axis that produced Attempt 1's failure mode, so a larger drawdown was the declared cost of the change. | No variant breached the research shutdown and the deepest maximum drawdown across all 36 runs was @@S:DEEPEST_DD_PCT@@ against a 15% limit. The declared risk did not materialise, which is a result and not a vindication of the reasoning. |
| `G2A3-CONFLICT-30` | `governance/*` is single-level and `config/**` is recursive, so this attempt's subtree splits down the middle of `repo_state_id`. | Both directions are asserted at build time and both hold. Widening the patterns is not available, because the patterns are themselves sealed by every earlier stage's digest. |
| `G2A3-CONFLICT-31` | `RotationEngineRA3` subclasses `RotationEngineRA1`, which belongs to a closed attempt. | It re-derives exactly the risk and sessions-in-band state it must after calling `super()`, which an AST test enforces. Subclassing reads the closed module without modifying it. |
| `G2A3-CONFLICT-32` | The dissimilarity denominator carries a floor of 1, so a pair that is zero on both sides scores 0 rather than dividing by zero. | Disclosed, not repaired. For the selected representative no pair was zero on both sides, so the floor did not decide this selection. |
| `G2A3-CONFLICT-33` | This is the third disclosed adaptation on one hypothesis family, and a PASS here would not on its own have distinguished which of the two changes produced it. | The attempt failed, so the question is moot for this result and remains live for the family. |
| `G2A3-CONFLICT-34` | @@S:MODULE_COUNT@@ prior-attempt modules are held immutable, not the nine the operating instruction implies. | The count is read from the seal rather than typed into the package, so a silently shortened list fails loudly instead of passing. |
| `G2A3-CONFLICT-35` | This pre-registration was written after two attempts' development results were known, and both of its changes were chosen in response to the second. | Pre-registration constrains what happens after the seal; it cannot undo what was known before. The adaptation is disclosed verbatim in five carriers, the multiplicity is quantified, and no threshold was adjusted in either direction to compensate. Supersedes `G2A2-CONFLICT-6`'s scope. |
| `G2A3-CONFLICT-36` | Both fail routes of this attempt emit the same verdict token. | The route is recorded separately: `@@FAIL_ROUTE@@`, which is the gate-reached-and-missed route and not Attempt 1's no-representative route. |
| `G2A3-CONFLICT-37` | Attempt 2's operating prompt named verdict tokens that existed in no artifact; Attempt 3's names none at all and directs that the sealed criteria file be grepped instead. | The failure mode is removed rather than resolved a second time. The tokens are minted once, in `SE100-CFG-3106`, and the four belonging to Attempts 1 and 2 are asserted absent from every Attempt 3 verdict field. Supersedes `G2A2-CONFLICT-8`'s scope. |
| `G2A3-CONFLICT-38` | Attempt 2's sealed pre-registration states that no Attempt 3 is authorized. | A stage artifact's self-imposed closure rule is not a constitutional provision and does not outrank the operator. What it does outrank is a silent reopening, which is not what happened: the adaptation is disclosed verbatim in five carriers and the decision package carries it in the sixth. |
| `G2A3-CONFLICT-39` | The sealed `mechanics_carried_unchanged.method` states that only the variant id format and the ids themselves differ from Attempt 2's. Compared pointer by pointer, four further pointers differ. | Three are additive provenance notes and the fourth is `gate_evaluation_scope.criteria_source`, which could not have been otherwise. None of the four is a mechanic. The seal is not edited; the checker implements the true predicate and reports the unused entries of both allow-lists, so a list that only ever widens shows up as evidence rather than passing quietly. |
| `G2A3-CONFLICT-40` | Two prose pointers were renamed between Attempt 2's criteria seal and Attempt 3's — `S3-C3`'s attempt note and `S3-C6`'s scope-interpretation significance note. | Both are evidence text read by no predicate. Attempt 2's evaluators are called unmodified against an adapted view binding the old names to the new values, and the adapter check proves the view differs from the seal in exactly those two pointers, that both aliases carry byte-identical values to their RA3 originals, and that the sealed object itself is unmutated. |
| `G2A3-CONFLICT-41` | Three lists of banned selection-input substrings exist and no two are equal. `ratio` and `factor` are named in the seal's AT-I prose and enforced by neither implementation, so a field named `information_ratio` would pass every substring check. | Widening an implemented list to match a prompt's prose is the one repair this project forbids, so the gap is asserted rather than closed. The frozen dataclass makes it moot on this attempt: the selection surface carries exactly six fields and no return field can reach it whatever the substring lists say. |
| `G2A3-CONFLICT-42` | The sealed adaptation disclosure reasons that the removed rung had suppressed ordinary-market returns as well as crisis losses. Half of that reasoning is confirmed by this attempt's own measurement and half is refuted. | The throttle did loosen — ladder descents fell from @@S:LAD_LADDER_DESCENTS_A2@@ to @@S:LAD_LADDER_DESCENTS_A3@@ across the same 36 runs. Grid returns did not improve: Attempt 2's grid was already positive on @@S:A2_POS_BASE@@ of 18 base runs and its best run, @@S:A2_RET_MAX_PCT@@, exceeded this attempt's @@S:A3_RET_MAX_PCT@@. The representative moved off the grid floor because SEL-2 replaced the lowest-turnover rule, not because a rung was removed. Section 12 carries the three-way measurement; the sealed text is not edited. |

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
- **Not** promoting `@@S:RUNNER_UP@@` or any other variant in place of the representative that failed.
- **Not** isolating the two changes by re-running either alone. An isolation run is a further attempt
  and requires its own authorization and its own disclosure of the multiplicity it adds.
- **Not** any adjustment to an RA3 constant, a SEL-2 quantity, weight or threshold, or the width of the
  grid.

---

## 20. What was not touched

This is a checked claim, not an assurance. Three mechanisms:

1. **Digest re-verification.** All @@S:MODULE_COUNT@@ Attempt 1 and Attempt 2 modules were re-hashed
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
| Collected | @@TESTS_TOTAL@@ |
| Passed | @@TESTS_PASSED@@ |
| Failed | @@TESTS_FAILED@@ |
| Pre-existing floor | @@TESTS_FLOOR@@ |
| New in this attempt | @@TESTS_NEW@@ |

The one failure is `test_no_stage_4_module_can_reach_restricted_data_or_a_broker`, the permanent red
recorded as `S4-CONFLICT-7` at Stage 4 and inherited untouched by every stage since. It is a test whose
own governance record documents why it fails and why it may not be repaired here. It was not weakened,
skipped, xfailed or deleted, and no test was.

The @@TESTS_NEW@@ new tests are distributed across the thirteen adversarial requirements of §7. The
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
@@VERDICT@@
```

Gate 3 (development admissibility): **NOT PASSED**.

The risk architecture worked and the selection rule worked, in the narrow senses each was changed to
address. No variant breached the research shutdown, the ladder engaged @@S:LAD_LADDER_DESCENTS_A3@@
times rather than @@S:LAD_LADDER_DESCENTS_A2@@, the representative earned @@S:REP_BASE_RET_PCT@@ rather
than @@S:A2_REP_RET_PCT@@, and @@S:CONDITIONS_MET@@ of seven gate conditions were satisfied on both
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
