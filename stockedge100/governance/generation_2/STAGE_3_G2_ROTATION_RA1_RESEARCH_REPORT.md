# Stage 3 (Generation 2, Attempt 2) — rotation with risk architecture, development research report

| Field | Value |
|---|---|
| Document id | `SE100-GOV-2006` |
| Project | StockEdge100 |
| Generation | 2 |
| Generation id | `SE100-GEN2-7394207c543401e2` |
| Stage | 3 — **Attempt 2** |
| Gate | 3 — development admissibility |
| Session type | Development research and evaluation |
| Strategy id | `SE100-G2-S3-C2-ROTATION-RA1` |
| Governing document | `SE100-GOV-0001` (constitution, FROZEN) §§3, 4, 5.1, 6, 7, 9 gate 3, 10, 11, 19 |
| Charter | [STAGE_10_GENERATION_2_CHARTER.md](STAGE_10_GENERATION_2_CHARTER.md) (`SE100-GOV-2001`) |
| Partition lock | [STAGE_1_G2_PARTITION_LOCK.md](STAGE_1_G2_PARTITION_LOCK.md) (`SE100-GOV-2002`) |
| Attempt 1 | [STAGE_3_G2_ROTATION_RESEARCH_REPORT.md](STAGE_3_G2_ROTATION_RESEARCH_REPORT.md) (`SE100-GOV-2004`) — **CLOSED, READ-ONLY** |
| Pre-registration | [STAGE_3_G2_ROTATION_RA1_PROTOCOL.md](STAGE_3_G2_ROTATION_RA1_PROTOCOL.md) (`SE100-GOV-2005`), sealed |
| Protocol config | `config/generation_2/g2_rotation_ra1_protocol.json` (`SE100-CFG-3103`), sealed |
| Gate criteria | `config/generation_2/g2_gate_criteria_ra1.json` (`SE100-CFG-3104`), sealed |
| Evidence | `reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json` (`SE100-EVID-3102`) |
| Development window read | 1993-01-29 → 2021-07-31 (run span 2008-07-28 → 2021-07-30, 3276 sessions) |
| Latest session loaded | 2021-07-30 |
| Validation window | 2021-08-01 → 2024-07-31 — **not read** |
| Generation 1 holdout | 2024-08-01 → 2026-07-31 — **sealed, not read** |
| Generation 2 holdout | 2026-08-01 → 2028-07-31 — **does not exist in calendar time** |
| Authored (UTC) | 2026-08-15T13:42:08Z |
| Verdict | `FAIL — STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE` |
| Gate 3 | **NOT PASSED** |
| `live_trading_authorized` | `false` |

This report carries no `run_id` and no `repo_state_id`, for the reason Attempt 1 gave: a tree digest
quoted inside a member of the tree it describes is self-invalidating in the general case. Generation
2's governance subtree happens to fall outside `repo_state_id`'s single-level `governance/*.md`
pattern (`G2-CONFLICT-4`, restated in §18), but the convention is kept anyway, because a reader
should not have to reason about pattern depth to know whether a digest in a report is trustworthy.
Both values live in `reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json` and in the
appended `runs/` record, written by the builder rather than typed here.

The 64-hex values this report does quote are file digests and the universe identity digest. None is
a tree digest and none is this file's own digest. Every one was extracted from disk by the renderer
that produced this document; none was transcribed by hand.

---

## 1. What this session did

It ran Generation 2's **second** attempt at Gate 3, after Attempt 1 failed it. The hypothesis, the
universe, the calendar, the grid, the cost model, the execution convention, the gate thresholds and
the representative-selection rule are all unchanged from Attempt 1. The single change is the addition
of a **risk architecture** — an aggregate exposure ceiling, a portfolio volatility target, a
per-position stop, a de-risk ladder and a re-entry lockout — frozen in the pre-registration before
any variant ran, and applied uniformly to all eighteen variants (§6).

Eighteen variants, two cost scenarios each, 36 backtests, development data only. Then the frozen
return-blind selection rule, then Gate 3 on the representative it produced.

Three findings, in the order they were established:

1. **The risk architecture eliminated the research-shutdown breaches entirely.** Attempt 1 recorded a
   shutdown event in **36 of 36 runs**; Attempt 2 recorded **0 of 36**. Every variant's maximum
   drawdown fell — the worst in Attempt 2 is 0.1420 against Attempt 1's worst of
   0.1759 — and the whole grid now sits inside the 15% research-shutdown ceiling (§12).
2. **A representative therefore exists for the first time.** Step 1 of the selection rule admitted
   all eighteen variants instead of none; step 2 (lowest turnover, return-blind) decided on
   `SE100-G2-S3-C2-ROTATION-RA1-L12-K1-QUARTERLY` at 189 fills across both runs, with no tie (§10, §11).
3. **The representative failed Gate 3.** Three of seven hard conditions are not satisfied on its base
   run and four of six on its stress run. Profit factor (1.0729 against a 1.10 floor), the
   best-trade-removed condition and the single-instrument concentration condition all fail on both
   runs; total return additionally fails on the stress run (§14).

The verdict is `FAIL — STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE`. It arrives by the second of the two sealed
fail routes — a representative existed and did not satisfy every hard condition — where Attempt 1
arrived by the first, no representative existing at all. That is a different failure and a more
informative one, and it is still a failure.

## 2. Why this attempt exists, and what it costs

Attempt 1 (`SE100-G2-S3-C1-ROTATION`) ended `FAIL — STAGE_3_G2_NO_CANDIDATE` and is closed
permanently. Nothing in this session edited, deleted, reopened, re-ran or loosened any Attempt 1
artifact or module; the claim is checked rather than asserted, in §20.

This attempt was designed **after** that result was seen. The following text is sealed as
`adaptation_disclosure_verbatim` in the protocol config (`SE100-CFG-3103`) and in the pre-registration
Markdown and JSON (`SE100-GOV-2005`). It is one of five declared carriers; the package builder asserts
byte-equality against the sealed value and refuses to write if any carrier paraphrases it. It was
substituted here mechanically from the sealed file, as a single unbroken block, so that byte-identity
is checkable by string comparison rather than asserted:

> This pre-registration was designed after Attempt 1's development results were known. All eighteen Attempt 1 variants recorded at least one research-shutdown event, clustered at 2008-10 through 2011-10 (thirteen of eighteen), with additional single occurrences in mid-2010, January 2016, and March 2020 — periods of acute market stress that an unconstrained rotation strategy had no mechanism to survive. Attempt 2 adds risk architecture explicitly informed by this observation. The development window is no longer pristine for this hypothesis family. This adaptation increases researcher degrees of freedom and cumulative multiplicity across both attempts. No successful development result from Attempt 2 can, by itself, establish a trading edge — this mirrors exactly the disclosure Generation 1 made between its own Attempt 1 and Attempt 2.

The sealed `enforcement` clause reads, in as many words: *"The sealer and the package builder both
assert byte-equality of this string against the value in this file. A paraphrase is a failure, not a
stylistic choice."* It is carried in `governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md`,
the same file's `.json`, this report,
`reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json`, and the decision record
`reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json`.

The point of restricting the change to risk architecture is stated in the protocol and is worth
repeating here, because it bounds what this attempt can and cannot claim:

> Attempt 1 tested the rotation signal with no mechanism to reduce exposure before a research-shutdown breach: between scheduled rebalances it issued no orders at all. Attempt 2 holds the signal, the universe, the calendar, the grid, the cost model and the gate thresholds fixed and adds only risk architecture. Any difference in outcome is therefore attributable to the risk architecture rather than to a re-tuned signal - which is the only reason a second attempt on a contaminated window is worth running at all.

That bounds the *attribution*, not the multiplicity. It does not make the development window pristine
again and it does not make a development pass evidence of an edge. See §17.

## 3. What was pre-registered, and when

The pre-registration was sealed in a separate phase of this session, **before any strategy,
engine, gate or runner code for Attempt 2 existed**, and the seal is recorded:

| Field | Value |
|---|---|
| Seal run id | `SE100-R-20260815T095541Z` |
| Sealed (UTC) | 2026-08-15T09:55:41Z |
| `repo_state_id` at seal | `216894a87a7e47230d08b5980b15751f9de1b863183286b5635f3f2e301f867d` |
| Protocol Markdown | `governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md` — `40e39f13e85574dc15cdb11ae57bc8bb45a16c62164a08e6d545f4924c95553a` |
| Protocol JSON | `governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json` — `c1a4742b93ca1e34e6e119012f756720446ac9a125441c6ab4b802259858a2dc` |
| Protocol config | `config/generation_2/g2_rotation_ra1_protocol.json` — `0054edce91a8a49dc39f4f53529969902e318ddc3d67e9cc0307e2c015ca6880` |
| Gate criteria | `config/generation_2/g2_gate_criteria_ra1.json` — `3b9626214db6a6f6183384456489338ea19a277866e35a1aa6c09b0bacb3e625` |
| Cost model | `config/generation_2/g2_cost_model.json` — `b9491485b9560b948ec83d3eb86ee4946c1e83b128a368b71473d14ad0f73650` |
| Partition lock JSON | `governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json` — `e17ea82c499d51cf23fc9986e7231dce6388f8a3c7394d3dd3c0e3d27fbacbe7` |
| Charter | `governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md` — `865a2feffe683e0baf71f1ab976e286fbb2d003109ab47cfaffc1fe6a63dbc90` |

**How "before any code" is measured.** Attempt 1 sealed a path-based predicate — that no module with
a given filename existed. By Attempt 2 that predicate had become vacuous: Attempt 1's modules exist,
and a new attempt's code could have been written into a file whose name the predicate never
mentioned. The Attempt 2 seal therefore records a **content**-based measurement instead:

> No .py file under src/stockedge100 or tests contains the string SE100-G2-S3-C2-ROTATION-RA1 at seal time.

That is a statement about the contents of every `.py` file in the tree at seal time, not about a
list of filenames, and it is re-checkable after the fact against the sealed `repo_state_id`.

Everything the gate would later depend on was fixed at that moment: the eighteen-variant grid, the
run span, the universe, the cost model, the five risk constants and their combination rule, the
seven gate conditions and their measurement bases, the three-step selection rule, the two verdict
tokens, and the nine adversarial test requirements `AT-A` … `AT-I` in the protocol's own words.

## 4. The window actually read, and how that was enforced

The development bound is **2021-07-31**, carried from the partition lock. The run span is
**2008-07-28 → 2021-07-30**, 3276 sessions, unchanged from Attempt 1 and carried from
Attempt 1's protocol config (`1cc5f94ffa70d66e059182a6330bffab2a72f7e4f46db07e50c2924f42799810`)
rather than recomputed with a free hand. The binding symbol is `VEA`, inception
2007-07-26: the run starts at the first session on which a 12-month lookback has a
reference bar for **every** universe member, so all eighteen variants share one start date and none
is advantaged by a shorter history.

The span is not merely quoted. The runner recomputes `binding_symbol`, `binding_symbol_inception`,
`run_start`, `run_end` and `sessions` from the guard-loaded series in memory and **refuses to run**
if any value differs from the sealed one, cross-checked against three independent derivations
(`SE100-CFG-3103`, `SE100-GOV-2005`, and `reporting.g2_rotation_preregistration.measure_span()`).
No member is missing a bar at `run_start` and no member's series ends before `run_end`.

Enforcement of the bound is the Generation 2 window guard, reused unmodified from Attempt 1, and
exercised through the Attempt 2 loading path by tests `AT-G`. The recorded outcome:

| Check | Value |
|---|---|
| Latest session loaded, any symbol | 2021-07-30 |
| Development bound | 2021-07-31 |
| Validation window read | `false` |
| Generation 1 holdout read | `false` |
| Generation 2 holdout read | `false` |

The latest bar this session touched is **2021-07-30**, one session inside the bound. The
validation data exists on disk and is technically reachable; it was not reached. The guard rejects a
window ending after the bound rather than silently truncating it, and it refuses to intersect either
holdout at all — Generation 2's holdout does not exist in calendar time and may not be read in any
future session before it does.

## 5. Universe and the eligibility re-check

Unchanged from Attempt 1 and re-verified rather than assumed:

| Field | Value |
|---|---|
| Universe version | `SE100-U1-d4917c2f7f1cd834` |
| Universe identity digest | `d4917c2f7f1cd8344728a39165929b352766fbe7193b3c64e71a971749dcbf38` |
| Declared members | 34 |
| Loaded members | 34 |
| Missing at run start | none |
| Unchanged from Attempt 1 | `true` |

`AAPL` is present in the data tree as a Stage 2 single-symbol fixture. It was never a member of the
eligible universe and was never ranked, in either attempt; the exclusion is recorded in the evidence
file with that reason rather than left as an absence a reader would have to notice.

## 6. The risk architecture, frozen before any variant ran

The pre-registration seals five components as `RA2`, with their values as decimal strings, and marks
them `frozen_before_any_variant_is_run` and `not_part_of_the_grid`. None was tuned after a result was
seen; none is an axis of the grid; all eighteen variants received identical constants.

| Id | Component | Value |
|---|---|---|
| `RA2-1` | Aggregate exposure ceiling | 0.50 of equity |
| `RA2-2` | Portfolio volatility target | 0.10 annualized |
| `RA2-3` | Per-position stop | 0.08 loss from entry, evaluated at session close, exit at the next open |
| `RA2-4` | De-risk ladder | band 0: drawdown [0.00, 0.05) → 1.00; band 1: [0.05, 0.08) → 0.75; band 2: [0.08, 0.10) → 0.50; band 3: [0.10, ∞) → 0.25, measured from the equity high-water mark |
| `RA2-5` | Re-entry lockout | 10 trading sessions |

The ladder uses the −5% / −8% / −10% staging the operating instruction proposed. No more principled
alternative was substituted: the instruction permitted one but required it to be documented and
frozen before any run, and inventing a different staging after seeing where Attempt 1 broke would
have added a degree of freedom for no stated reason. The bands are closed below and open above, and
that convention is itself tested (`AT-D`).

The two scalars combine as sealed:

> `f(t) = f_vol(t) * f_ladder(t), quantized to nine decimal places, ROUND_DOWN.`

`applies_to` is likewise sealed and narrow — *"the entry budget at the fill open: w(k) * f * equity"*
and *"the aggregate ceiling at every session: 0.50 * f * equity"* — and the protocol states what the
combined scalar explicitly **does not** touch: the per-position stop, which fires on its own terms,
and the constitutional research shutdown, which is not a risk control the strategy may scale.

Descent down the ladder is immediate and to the full computed band; recovery is at most one band per
session and is gated by the lockout, which arms on every downward transition. That asymmetry is
deliberate — a symmetric ladder would re-lever into the same drawdown it had just reduced — and both
directions are tested.

## 7. Engine capability added, and its adversarial tests

Attempt 1's engine issues orders only at scheduled rebalances. Attempt 2 needs an engine that can act
**between** rebalances — to stop out a position, to trim the book back under a ceiling, to re-size on
a ladder transition — without that capability leaking into the signal. The new modules are additions
alongside Attempt 1's, never edits to them (§20):

| Module | What it adds |
|---|---|
| `backtest/g2_engine_ra1.py` | aggregate exposure throttling, volatility scaling, the per-position stop, the ladder state machine, the lockout timer |
| `backtest/g2_episodes_ra1.py` | the episode ledger — see §14 and `G2A2-CONFLICT-18` |
| `strategies/g2_rotation_ra1.py` | the Attempt 2 rotation strategy over the sealed grid |
| `strategies/g2_gate_ra1.py` | Gate 3 evaluation on the sealed criteria |
| `strategies/g2_runner_ra1.py` | the 36-run driver, the span recheck, and return-blind selection |
| `reporting/g2_rotation_ra1_preregistration.py` | the sealer |
| `reporting/g2_stage3_attempt2_evidence.py` | the evidence builder |
| `reporting/g2_stage3_attempt2_package.py` | the decision-package builder |

The protocol declared nine required adversarial tests, `AT-A` … `AT-I`, in its own words, before any
of that code existed. Each section of `tests/adversarial/test_g2_ra1_risk_architecture.py` opens with
a **control** that a vacuous check would fail, and closes with an **injected defect** that must be
caught — a loosened ceiling, a disabled stop, a flat ladder, a zero cooldown, a changed byte in an
Attempt 1 module, an added field on the selection input. A test that only ever passes proves nothing
about the mechanism it names; a test that catches a deliberate break proves something.

`AT-A` deserves a note. The ceiling is asserted after **every fill**, not only at session close, and
the tests establish separately that a sell never increases exposure, that residual drift over the
nominal ceiling stays under one minimum lot, and that the ceiling **binds** rather than being
satisfied by accident. The last of those is the one that matters: a ceiling that is never approached
is not evidence of a working ceiling. The measured drift is disclosed as `G2A2-CONFLICT-27` (§18).

## 8. Cost model

Unchanged: `config/generation_2/g2_cost_model.json` (`b9491485b9560b948ec83d3eb86ee4946c1e83b128a368b71473d14ad0f73650`), which differs from the
sealed Generation 1 model at exactly one declared pointer, position breadth, and nowhere else. Every
variant runs twice — `#BASE` at the modelled frictions and `#STRESS` at 2× — and the stress run is a
**gating** run, not a sensitivity check that may be waived (§14).

Attempt 2's risk architecture trades more than Attempt 1's did: stop legs and throttle legs are real
fills and pay real costs. That shows up directly in the stress results, where several variants lose
most of their base-run return, and in one case cross into negative territory (§15).

## 9. The grid as executed

Eighteen variants — lookback ∈ {3, 6, 12} months × k ∈ {1, 2, 3} × rebalance ∈ {monthly, quarterly} —
each run twice, **36 runs**, all completed. The grid, its axes and its variant ids were sealed before
any run; no variant was added, dropped, re-run with different constants, or re-labelled.

Execution is unchanged from Attempt 1: rank at the decision close, fill at the **next session's
open**, exit on a drop out of the top k at a scheduled rebalance. Attempt 2 adds three further exit
and re-size paths (stop, throttle, ladder), all of which also fill at an open, never at the close that
triggered them.

## 10. The representative-selection rule, and how it was applied

The rule is unchanged from Attempt 1 and was frozen before any variant ran:

1. **Eliminate** every variant with one or more research-shutdown events in **either** run.
2. Among survivors, take the **lowest turnover**, defined as total fill count across both runs.
3. If two variants tie on both, take the lexicographically first variant id.

**It cannot read a return.** That is enforced structurally, not by convention. `select_representative`
receives only `SelectionInputRA1` records, whose fields are exactly
`['variant_id', 'shutdown_events', 'fill_count', 'per_run']`, asserted equal to that tuple at **import
time** — so a field added to carry a performance figure raises before any selection can run. No
`BacktestResult`, measurement, equity curve, trade P&L, ladder activation count or lockout trigger
count is in scope at the point the representative is decided. Tests `AT-I` attack this by mutating the
dataclass and requiring the import-time assertion to fire, and by requiring that a variant missing one
of its two runs is **refused** rather than screened on half its evidence.

Two Attempt 2 notes on the rule, both sealed in advance:

- Fill count now includes `STOP` and `THROTTLE` legs. The tiebreak therefore partly measures
  risk-architecture intervention rather than signal turnover alone. This is disclosed as `SC-4` and
  deliberately **not corrected**: changing the definition of turnover between attempts, after seeing
  which variants trade most, is exactly the adjustment the frozen rule exists to prevent.
- Gross notional was rejected as the turnover definition, in both attempts, because a variant that
  compounded further trades larger notionals for the same decisions — making it a partial return
  proxy (`G2-CONFLICT-13`).

## 11. Step 1: all eighteen eligible

**Every one of the eighteen variants recorded zero research-shutdown events, in both of its runs.**
Step 1 eliminated nothing, where in Attempt 1 it eliminated everything.

Step 2 then decided. Turnover across both runs, ascending, is in §16; the lowest is
`SE100-G2-S3-C2-ROTATION-RA1-L12-K1-QUARTERLY` at **189 fills**, and no other eligible variant matched that
count, so step 3 was not reached and the lexicographic tiebreak was never exercised on real data.

The representative was fixed at that point and never revisited. `no_reselection` is sealed; a
representative that fails the gate is not replaced by a runner-up, and §17.6 records what that costs
here, honestly.

## 12. Attempt 1 versus Attempt 2: the trip-wire

This is the one comparison the operating instruction asked for explicitly, and it is the strongest
result in this package.

| # | Variant | A1 shutdown `#BASE` | A1 shutdown `#STRESS` | A1 max DD `#BASE` | A2 max DD `#BASE` | A2 shutdowns |
| --- | --- | --- | --- | ---: | ---: | ---: |
| 1 | `L03-K1-MONTHLY` | 2016-01-20 | 2016-01-15 | 0.1505 | 0.1116 | 0 |
| 2 | `L03-K1-QUARTERLY` | 2008-11-19 | 2008-11-19 | 0.1708 | 0.1330 | 0 |
| 3 | `L03-K2-MONTHLY` | 2009-03-09 | 2009-03-09 | 0.1590 | 0.1045 | 0 |
| 4 | `L03-K2-QUARTERLY` | 2010-06-07 | 2010-06-07 | 0.1604 | 0.1052 | 0 |
| 5 | `L03-K3-MONTHLY` | 2008-10-24 | 2008-10-24 | 0.1619 | 0.1195 | 0 |
| 6 | `L03-K3-QUARTERLY` | 2008-10-27 | 2008-10-27 | 0.1538 | 0.0910 | 0 |
| 7 | `L06-K1-MONTHLY` | 2020-03-12 | 2020-03-12 | 0.1759 | 0.1263 | 0 |
| 8 | `L06-K1-QUARTERLY` | 2011-08-04 | 2011-08-04 | 0.1618 | 0.1382 | 0 |
| 9 | `L06-K2-MONTHLY` | 2010-08-11 | 2010-08-11 | 0.1686 | 0.1160 | 0 |
| 10 | `L06-K2-QUARTERLY` | 2009-05-27 | 2009-05-27 | 0.1581 | 0.1298 | 0 |
| 11 | `L06-K3-MONTHLY` | 2010-08-12 | 2010-08-12 | 0.1551 | 0.1188 | 0 |
| 12 | `L06-K3-QUARTERLY` | 2010-12-14 | 2010-12-10 | 0.1552 | 0.1160 | 0 |
| 13 | `L12-K1-MONTHLY` | 2011-10-04 | 2011-10-04 | 0.1653 | 0.1193 | 0 |
| 14 | `L12-K1-QUARTERLY` | 2010-02-04 | 2010-02-04 | 0.1551 | 0.1397 | 0 |
| 15 | `L12-K2-MONTHLY` | 2009-05-27 | 2009-05-27 | 0.1604 | 0.1154 | 0 |
| 16 | `L12-K2-QUARTERLY` | 2009-05-26 | 2009-05-26 | 0.1519 | 0.1031 | 0 |
| 17 | `L12-K3-MONTHLY` | 2010-07-02 | 2010-07-02 | 0.1572 | 0.1162 | 0 |
| 18 | `L12-K3-QUARTERLY` | 2010-07-02 | 2010-07-02 | 0.1508 | 0.0978 | 0 |

Attempt 1's shutdown events clustered in the post-crisis period; Attempt 2 has none to cluster:

| Month | Attempt 1 runs shut down | Attempt 2 runs shut down |
| --- | ---: | ---: |
| 2008-10 | 4 | 0 |
| 2008-11 | 2 | 0 |
| 2009-03 | 2 | 0 |
| 2009-05 | 6 | 0 |
| 2010-02 | 2 | 0 |
| 2010-06 | 2 | 0 |
| 2010-07 | 4 | 0 |
| 2010-08 | 4 | 0 |
| 2010-12 | 2 | 0 |
| 2011-08 | 2 | 0 |
| 2011-10 | 2 | 0 |
| 2016-01 | 2 | 0 |
| 2020-03 | 2 | 0 |
| **Total** | **36** | **0** |

Attempt 1's worst base-run drawdown was 0.1759 and its best was 0.1505 — the whole grid
was at or through the 15% ceiling. Attempt 2's range is **0.0910 to 0.1397**, entirely
inside it, and every single variant improved. On the stress side the worst is 0.1420,
still inside.

**What this does and does not establish.** It establishes that the risk architecture does the thing
it was designed to do, on this window, mechanically and uniformly across all eighteen variants — and
`SC-6`, declared before any run, predicted the direction: *"The risk architecture reduces exposure and
can only reduce it… Attempt 2's expected gross return is lower than Attempt 1's would have been."* It
does **not** establish an edge, and it is not a surprise: the architecture was chosen after seeing
where Attempt 1 broke. A mechanism designed against known failure dates that then avoids those dates
is confirming its own construction, not discovering anything. That is the whole content of the
adaptation disclosure in §2, and it is why the gate — which the architecture was *not* tuned against —
is the only part of this session that carries evidential weight.

## 13. Determinism and reconciliation

| Check | Result |
|---|---|
| Runs compared on a clean rerun | 36 |
| Identical on every compared field | `true` |
| Fields compared | 8 (trade, equity, ranking and risk-state digests among them) |
| Runs reconciled against the independent replay | 36 |
| Reconciliation mismatches | 0 |
| Vacuous runs (a replay comparing nothing) | none |

The risk-state digest is checked to cover state that no other digest reaches, and each digest is
checked **not** to be a constant — a determinism result in which every digest is the same constant is
perfectly stable and worthless. The reconciliation is an independent replay of the engine's own
decisions, and the vacuity check exists because a replay that compares zero legs would otherwise
report a clean reconciliation.

## 14. Gate 3: evaluated on the representative, and not passed

Attempt 1 never reached this table. Attempt 2 does.

Representative: **`SE100-G2-S3-C2-ROTATION-RA1-L12-K1-QUARTERLY`**, decided at step 2.

| Condition | Required (verbatim) | `#BASE` verdict | measured | threshold | `#STRESS` verdict | measured |
|---|---|---|---|---|---|---|
| `S3-C1` | total return is positive | `MET` | 0.004221210809341463756 | > 0 | `NOT_MET` | -0.000805436201623164544 |
| `S3-C2` | maximum drawdown is no worse than 15% | `MET` | 0.1396851017217713172058464193097361 | <= 0.15 | `MET` | 0.1420128991297120600142654278172959 |
| `S3-C3` | profit factor is at least 1.10 | `NOT_MET` | 1.072939866369710467706013363028953 | >= 1.1 | `NOT_MET` | 1.029894490035169988276670574443142 |
| `S3-C4` | at least 30 closed trades exist, unless a lower-frequency protocol predeclared a longer evidence requirement before results | `MET` | 36 | >= 30 | `MET` | 36 |
| `S3-C5` | performance is not dependent on one trade: removing the single best trade leaves total return above 0% | `NOT_MET` | min(-0.0111713778050263521403667741091303, -0.0111713778050263521403667741091303) | best_trade_removed_return > 0 for BOTH removals | `NOT_MET` | min(-0.0187959786703338421765362263696300, -0.0187959786703338421765362263696300) |
| `S3-C6` | no single instrument contributes more than 50% of total strategy profit for a multi-instrument strategy | `NOT_MET` | 2.717557251908396946564885496183206 | <= 0.50 | `NOT_MET` | 6.882352941176470588235294117647059 |
| `S3-C7` | reasonable neighboring parameter values do not reverse the sign of net return | `MET` | 3/3 neighbours match | all 3 match, zero matches nothing | `NOT_MET` | 0/3 neighbours match |

**Scope.** The gate is evaluated on the selected representative only, across **both** of its runs. A
condition is satisfied only if both runs satisfy it; the stressed cost model is a gating run, not a
waiver. `S3-C7` is evaluated once, on base runs, because its own sealed `what_is_read` fixes the
neighbour comparison to base-run total return and gives no basis for a stress-side one; the stress-side
figure is reported and is explicitly **not gating**. This resolution is `G2A2-CONFLICT-25` (§18): two
artifacts sealed in the same session scoped the gate differently, neither outranks the other, and the
more restrictive reading was adopted.

**Outcome.**

| | Value |
|---|---|
| Conditions not satisfied, `#BASE` | `S3-C3`, `S3-C5`, `S3-C6` |
| Conditions not satisfied, `#STRESS` | `S3-C1`, `S3-C3`, `S3-C5`, `S3-C6` |
| All seven satisfied on `#BASE` | `false` |
| First six satisfied on `#STRESS` | `false` |
| A permissive base-only reading would give | `false` — the restrictive resolution changed nothing |
| `admissible_candidate_exists` | **`NOT_MET`** |
| Candidates evaluated | 1 |
| Admitted candidates | 0 |

The last line of that table is the one that decides the stage. Gates are conjunctive within a
candidate and the stage verdict is a disjunction across candidates; with one candidate the
disjunction is over a set of size one, and `admissible_candidate_exists` is `NOT_MET`.

**Where the representative actually fails.** Profit factor is **1.0729** against a floor of 1.10 —
close, and a miss. The best-trade-removed condition fails decisively: removing the single largest
winner takes total return to **-1.12%** on the base run and **-1.88%** on the
stress run, so the variant's entire positive return is one trade. Concentration fails by a wide
margin: the largest single-instrument contribution is **2.72×** total strategy profit on
the base run and **6.88×** on the stress run, which is what a ratio looks like when
total profit is small and offsetting positions are large. On the stress run total return is negative
outright (-0.08%).

Those three failures are consistent with each other and with the representative's shape:
36 closed trades over thirteen years, a base return of +0.42%, and a result
that rests on one position. This is a variant that survived the drawdown screen because it barely
traded, and the gate correctly declines to call that an edge.

**A measurement note that matters.** `S3-C3`, `S3-C4`, `S3-C5` and `S3-C6` are measured on the
**episode ledger**, not on `Portfolio.trades`. Attempt 2's throttle and ladder *trim* positions, and
the frozen trade recorder attributes a trim's proceeds to no trade at all — so the frozen recorder
would silently under-count realised P&L for exactly the mechanisms this attempt added. The divergence
is visible in the numbers: the descriptive grid table reports a profit factor of **1.2459**
for this variant's base run on the recorder basis, while the gate measures **1.0729** on the
ledger basis. The ledger is the correct basis and was sealed as such before any run
(`G2A2-CONFLICT-18`, §18). The gate figure is the binding one; §15's is descriptive.

## 15. Grid results — descriptive record only

Reported for completeness, as the operating instruction requires. **None of it gates anything.** The
gate was evaluated on the representative alone (§14), and no figure below was an input to the
selection that produced it. Profit factors here are on the frozen-recorder basis, which differs from
the gate's ledger basis for the reason given in §14.

**`#BASE` runs** — the modelled cost model.

| # | Variant | Return | Max DD | Profit factor | Closed trades | Closed episodes | Distinct symbols | Shutdowns |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `L03-K1-MONTHLY` | +0.6315 | 0.1116 | 1.9341 | 105 | 105 | 21 | 0 |
| 2 | `L03-K1-QUARTERLY` | +0.0691 | 0.1330 | 1.4116 | 49 | 49 | 17 | 0 |
| 3 | `L03-K2-MONTHLY` | +0.4203 | 0.1045 | 1.6714 | 157 | 157 | 27 | 0 |
| 4 | `L03-K2-QUARTERLY` | +0.0419 | 0.1052 | 1.1126 | 65 | 65 | 24 | 0 |
| 5 | `L03-K3-MONTHLY` | +0.2869 | 0.1195 | 1.5239 | 231 | 231 | 29 | 0 |
| 6 | `L03-K3-QUARTERLY` | +0.2811 | 0.0910 | 1.4140 | 110 | 110 | 27 | 0 |
| 7 | `L06-K1-MONTHLY` | +0.1986 | 0.1263 | 1.3916 | 81 | 81 | 19 | 0 |
| 8 | `L06-K1-QUARTERLY` | +0.0834 | 0.1382 | 1.4905 | 40 | 40 | 15 | 0 |
| 9 | `L06-K2-MONTHLY` | +0.1927 | 0.1160 | 1.4443 | 149 | 149 | 25 | 0 |
| 10 | `L06-K2-QUARTERLY` | +0.0448 | 0.1298 | 1.1319 | 57 | 57 | 22 | 0 |
| 11 | `L06-K3-MONTHLY` | +0.1066 | 0.1188 | 1.1802 | 195 | 195 | 28 | 0 |
| 12 | `L06-K3-QUARTERLY` | +0.0365 | 0.1160 | 1.0684 | 95 | 95 | 26 | 0 |
| 13 | `L12-K1-MONTHLY` | +0.0633 | 0.1193 | 1.2676 | 66 | 66 | 18 | 0 |
| 14 | `L12-K1-QUARTERLY` | +0.0042 | 0.1397 | 1.2459 | 36 | 36 | 15 | 0 |
| 15 | `L12-K2-MONTHLY` | +0.1792 | 0.1154 | 1.4808 | 83 | 83 | 26 | 0 |
| 16 | `L12-K2-QUARTERLY` | +0.1954 | 0.1031 | 1.7503 | 58 | 58 | 22 | 0 |
| 17 | `L12-K3-MONTHLY` | +0.0892 | 0.1162 | 1.1911 | 140 | 140 | 29 | 0 |
| 18 | `L12-K3-QUARTERLY` | +0.0709 | 0.0978 | 1.1853 | 74 | 74 | 27 | 0 |

**`#STRESS` runs** — the same variants at 2× frictions.

| # | Variant | Return | Max DD | Profit factor | Closed trades | Closed episodes | Fills | Shutdowns |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `L03-K1-MONTHLY` | +0.5715 | 0.1141 | 1.8346 | 105 | 105 | 319 | 0 |
| 2 | `L03-K1-QUARTERLY` | +0.0651 | 0.1334 | 1.4777 | 49 | 49 | 135 | 0 |
| 3 | `L03-K2-MONTHLY` | +0.3054 | 0.1120 | 1.4715 | 182 | 182 | 434 | 0 |
| 4 | `L03-K2-QUARTERLY` | +0.0038 | 0.1073 | 1.0015 | 66 | 66 | 156 | 0 |
| 5 | `L03-K3-MONTHLY` | +0.2210 | 0.1331 | 1.3605 | 260 | 260 | 562 | 0 |
| 6 | `L03-K3-QUARTERLY` | +0.2375 | 0.0929 | 1.3280 | 108 | 108 | 240 | 0 |
| 7 | `L06-K1-MONTHLY` | +0.1598 | 0.1309 | 1.3088 | 81 | 81 | 237 | 0 |
| 8 | `L06-K1-QUARTERLY` | +0.0640 | 0.1388 | 1.3885 | 40 | 40 | 123 | 0 |
| 9 | `L06-K2-MONTHLY` | +0.1559 | 0.1152 | 1.3400 | 141 | 141 | 340 | 0 |
| 10 | `L06-K2-QUARTERLY` | +0.0107 | 0.1323 | 0.9914 | 57 | 57 | 132 | 0 |
| 11 | `L06-K3-MONTHLY` | +0.1113 | 0.1185 | 1.1715 | 193 | 193 | 421 | 0 |
| 12 | `L06-K3-QUARTERLY` | +0.0412 | 0.1159 | 1.0870 | 95 | 95 | 216 | 0 |
| 13 | `L12-K1-MONTHLY` | +0.0463 | 0.1196 | 1.2278 | 66 | 66 | 182 | 0 |
| 14 | `L12-K1-QUARTERLY` | -0.0008 | 0.1420 | 1.1709 | 36 | 36 | 92 | 0 |
| 15 | `L12-K2-MONTHLY` | +0.1048 | 0.1172 | 1.3007 | 83 | 83 | 185 | 0 |
| 16 | `L12-K2-QUARTERLY` | +0.0828 | 0.1060 | 1.3284 | 46 | 46 | 111 | 0 |
| 17 | `L12-K3-MONTHLY` | +0.0239 | 0.1175 | 1.0996 | 153 | 153 | 336 | 0 |
| 18 | `L12-K3-QUARTERLY` | +0.0574 | 0.1007 | 1.1451 | 74 | 74 | 160 | 0 |

## 16. Risk-architecture activity and turnover, for the record

Ladder activations and re-entry-lockout triggers per variant, as the operating instruction requires.
Descriptive only.

**`#BASE` runs.**

| # | Variant | Ladder descents | Ladder ascents | Deepest band | Lockout arms | Recoveries blocked | Stops triggered | Stops filled | Stops pre-empted |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `L03-K1-MONTHLY` | 64 | 64 | 3.00 | 64 | 276 | 9 | 9 | 0 |
| 2 | `L03-K1-QUARTERLY` | 44 | 44 | 3.00 | 44 | 145 | 12 | 12 | 0 |
| 3 | `L03-K2-MONTHLY` | 41 | 41 | 3.00 | 41 | 172 | 25 | 17 | 3 |
| 4 | `L03-K2-QUARTERLY` | 58 | 58 | 3.00 | 58 | 236 | 20 | 17 | 0 |
| 5 | `L03-K3-MONTHLY` | 36 | 36 | 3.00 | 36 | 122 | 251 | 23 | 12 |
| 6 | `L03-K3-QUARTERLY` | 34 | 34 | 2.00 | 34 | 156 | 30 | 27 | 0 |
| 7 | `L06-K1-MONTHLY` | 49 | 48 | 3.00 | 49 | 191 | 8 | 8 | 0 |
| 8 | `L06-K1-QUARTERLY` | 40 | 39 | 3.00 | 40 | 156 | 11 | 11 | 0 |
| 9 | `L06-K2-MONTHLY` | 52 | 52 | 3.00 | 52 | 194 | 15 | 12 | 1 |
| 10 | `L06-K2-QUARTERLY` | 46 | 45 | 3.00 | 46 | 157 | 30 | 16 | 1 |
| 11 | `L06-K3-MONTHLY` | 45 | 43 | 3.00 | 45 | 173 | 37 | 20 | 2 |
| 12 | `L06-K3-QUARTERLY` | 25 | 23 | 3.00 | 25 | 76 | 151 | 21 | 3 |
| 13 | `L12-K1-MONTHLY` | 50 | 47 | 3.00 | 50 | 195 | 15 | 15 | 1 |
| 14 | `L12-K1-QUARTERLY` | 55 | 53 | 3.00 | 55 | 211 | 12 | 12 | 0 |
| 15 | `L12-K2-MONTHLY` | 37 | 37 | 3.00 | 37 | 126 | 15 | 15 | 0 |
| 16 | `L12-K2-QUARTERLY` | 51 | 51 | 3.00 | 51 | 186 | 17 | 17 | 0 |
| 17 | `L12-K3-MONTHLY` | 36 | 36 | 3.00 | 36 | 151 | 23 | 23 | 0 |
| 18 | `L12-K3-QUARTERLY` | 39 | 39 | 2.00 | 39 | 153 | 28 | 28 | 0 |

**`#STRESS` runs.**

| # | Variant | Ladder descents | Ladder ascents | Deepest band | Lockout arms | Recoveries blocked | Stops triggered | Stops filled | Stops pre-empted |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `L03-K1-MONTHLY` | 57 | 57 | 3.00 | 57 | 193 | 9 | 9 | 0 |
| 2 | `L03-K1-QUARTERLY` | 43 | 43 | 3.00 | 43 | 106 | 12 | 12 | 0 |
| 3 | `L03-K2-MONTHLY` | 52 | 52 | 3.00 | 52 | 224 | 246 | 19 | 11 |
| 4 | `L03-K2-QUARTERLY` | 52 | 51 | 3.00 | 52 | 162 | 402 | 17 | 6 |
| 5 | `L03-K3-MONTHLY` | 27 | 25 | 3.00 | 27 | 101 | 134 | 25 | 7 |
| 6 | `L03-K3-QUARTERLY` | 38 | 38 | 2.00 | 38 | 159 | 30 | 27 | 0 |
| 7 | `L06-K1-MONTHLY` | 51 | 48 | 3.00 | 51 | 215 | 9 | 9 | 0 |
| 8 | `L06-K1-QUARTERLY` | 53 | 52 | 3.00 | 53 | 220 | 11 | 11 | 0 |
| 9 | `L06-K2-MONTHLY` | 45 | 43 | 3.00 | 45 | 170 | 21 | 12 | 1 |
| 10 | `L06-K2-QUARTERLY` | 28 | 26 | 3.00 | 28 | 99 | 31 | 16 | 1 |
| 11 | `L06-K3-MONTHLY` | 51 | 49 | 3.00 | 51 | 179 | 18 | 18 | 1 |
| 12 | `L06-K3-QUARTERLY` | 24 | 22 | 3.00 | 24 | 75 | 153 | 21 | 3 |
| 13 | `L12-K1-MONTHLY` | 52 | 49 | 3.00 | 52 | 218 | 15 | 15 | 1 |
| 14 | `L12-K1-QUARTERLY` | 46 | 44 | 3.00 | 46 | 174 | 12 | 12 | 0 |
| 15 | `L12-K2-MONTHLY` | 35 | 35 | 3.00 | 35 | 136 | 16 | 16 | 0 |
| 16 | `L12-K2-QUARTERLY` | 51 | 51 | 3.00 | 51 | 203 | 15 | 15 | 0 |
| 17 | `L12-K3-MONTHLY` | 54 | 52 | 3.00 | 54 | 247 | 40 | 23 | 1 |
| 18 | `L12-K3-QUARTERLY` | 44 | 44 | 3.00 | 44 | 176 | 28 | 28 | 0 |

16 of eighteen variants reached the deepest ladder band (0.25 sizing) on the base run;
2 reached band 2 only. Every downward transition armed the lockout, and the lockout
blocked between 76 and 276 recovery attempts per base run — so it is doing
work rather than being nominally present.

Stop behaviour splits into two regimes. Most variants trigger a few dozen stops per run and fill
nearly all of them; 6 of the 36 runs trigger at least three times what they
fill, the most extreme being `L03-K2-QUARTERLY#STRESS` at 402 triggers against 17 fills. The gap is the
**pre-empted** column: a
position already closed by a scheduled rebalance or by the throttle before the stop's next-open fill
could execute. Both counts are reported because reporting only the triggers would overstate the stop's
activity and reporting only the fills would hide it.

The exposure throttle and the combined scalar, base runs:

| # | Variant | Throttle legs | Legs below min notional | Sessions breaching ceiling | Max gross fraction | On session | Combined scalar min | Combined scalar mean | Sessions scalar < 1 |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 1 | `L03-K1-MONTHLY` | 117 | 960 | 1077 | 0.5155 | 2020-11-09 | 0.2500 | 0.7533 | 2355 |
| 2 | `L03-K1-QUARTERLY` | 34 | 1003 | 1037 | 0.5112 | 2009-10-14 | 0.2500 | 0.4803 | 2904 |
| 3 | `L03-K2-MONTHLY` | 54 | 1067 | 588 | 0.5160 | 2008-11-20 | 0.2500 | 0.7885 | 1863 |
| 4 | `L03-K2-QUARTERLY` | 21 | 504 | 273 | 0.5112 | 2009-10-14 | 0.2500 | 0.6272 | 2838 |
| 5 | `L03-K3-MONTHLY` | 50 | 1440 | 532 | 0.5108 | 2010-09-24 | 0.2500 | 0.6745 | 2001 |
| 6 | `L03-K3-QUARTERLY` | 29 | 852 | 313 | 0.5110 | 2009-10-05 | 0.4871 | 0.8652 | 1665 |
| 7 | `L06-K1-MONTHLY` | 77 | 799 | 876 | 0.5129 | 2009-09-16 | 0.2500 | 0.7560 | 2032 |
| 8 | `L06-K1-QUARTERLY` | 45 | 792 | 837 | 0.5124 | 2008-07-30 | 0.2500 | 0.5810 | 2596 |
| 9 | `L06-K2-MONTHLY` | 61 | 1248 | 685 | 0.5113 | 2009-05-06 | 0.2500 | 0.7496 | 2066 |
| 10 | `L06-K2-QUARTERLY` | 17 | 736 | 385 | 0.5112 | 2009-10-14 | 0.2500 | 0.5245 | 2777 |
| 11 | `L06-K3-MONTHLY` | 34 | 1427 | 511 | 0.5138 | 2011-08-10 | 0.2500 | 0.7340 | 2144 |
| 12 | `L06-K3-QUARTERLY` | 26 | 1149 | 420 | 0.5131 | 2008-12-16 | 0.2500 | 0.4742 | 2743 |
| 13 | `L12-K1-MONTHLY` | 46 | 983 | 1029 | 0.5128 | 2008-12-17 | 0.2385 | 0.5910 | 2513 |
| 14 | `L12-K1-QUARTERLY` | 24 | 956 | 980 | 0.5184 | 2008-11-20 | 0.1896 | 0.3990 | 3166 |
| 15 | `L12-K2-MONTHLY` | 18 | 541 | 291 | 0.5127 | 2008-12-16 | 0.2500 | 0.6995 | 2266 |
| 16 | `L12-K2-QUARTERLY` | 39 | 752 | 415 | 0.5146 | 2008-11-20 | 0.2500 | 0.8231 | 1782 |
| 17 | `L12-K3-MONTHLY` | 26 | 1057 | 380 | 0.5116 | 2008-12-17 | 0.2500 | 0.7796 | 1908 |
| 18 | `L12-K3-QUARTERLY` | 7 | 231 | 84 | 0.5044 | 2011-07-07 | 0.5000 | 0.8359 | 1740 |

Two columns deserve reading carefully. **Max gross fraction** sits between 0.5043 and
0.5184 across all 36 runs — the table above is base-only, and its own minimum is therefore the
slightly higher 0.5044 — that
is, slightly *above* the 0.50 ceiling, which is `G2A2-CONFLICT-27` and is disclosed rather than
papered over (§17.7, §18). **Legs below minimum notional** counts throttle legs that were computed and
then not issued because they fell under the minimum lot; that number is large because the throttle is
evaluated every session, and it is reported so that "throttle legs" is not read as "sessions on which
the throttle wanted to act".

The combined scalar spent most of the span below 1: between 1665 and
3166 sessions out of 3276, depending on variant, with means from
0.3990 to 0.8652. The strategy was de-levered for the majority of the run.

Turnover, which is what step 2 of the selection rule reads:

| Variant | Fills (both runs) |
|---|---:|
| `L12-K1-QUARTERLY` | 189 |
| `L06-K1-QUARTERLY` | 249 |
| `L06-K2-QUARTERLY` | 264 |
| `L12-K2-QUARTERLY` | 267 |
| `L03-K1-QUARTERLY` | 268 |
| `L03-K2-QUARTERLY` | 309 |
| `L12-K3-QUARTERLY` | 317 |
| `L12-K1-MONTHLY` | 360 |
| `L12-K2-MONTHLY` | 371 |
| `L06-K3-QUARTERLY` | 432 |
| `L06-K1-MONTHLY` | 477 |
| `L03-K3-QUARTERLY` | 491 |
| `L12-K3-MONTHLY` | 644 |
| `L03-K1-MONTHLY` | 647 |
| `L06-K2-MONTHLY` | 701 |
| `L03-K2-MONTHLY` | 804 |
| `L06-K3-MONTHLY` | 848 |
| `L03-K3-MONTHLY` | 1076 |

## 17. Disclosed limitations

**17.1 — The adaptation.** §2 carries the sealed disclosure verbatim and it is not repeated here.
It is the governing limitation on everything in this report: the development window is no longer
pristine for this hypothesis family, and no development result from this attempt can by itself
establish a trading edge.

**17.2 — Validation-window reuse.** Sealed as `validation_reuse_disclosure` in the partition lock
JSON (`SE100-GOV-2002`) and reproduced verbatim, substituted mechanically as a single unbroken line:

> Generation 2's validation window (2021-08-01 → 2024-07-31) overlaps the exact period Generation 1 used for its own Gate 4 validation read. The researcher therefore already knows, from Generation 1's published report, approximately how SPY (and by extension the broad market) behaved in this window — including its Sharpe ratio (≈0.20), total return (≈2.15%), and fold-by-fold sign pattern (7 of 12 positive). Generation 2 tests a different hypothesis (cross-sectional multi-asset selection vs. single-symbol mean reversion) over the same calendar period, which limits but does not eliminate the concern. This is a real multiplicity cost, disclosed and not minimized, and it is the reason Generation 2's validation result alone — without a clean holdout confirmation — cannot be treated as sufficient evidence of an edge.

**17.3 — Multiple comparisons, cumulative across attempts.** Eighteen variants and 36 runs this
attempt; eighteen and 36 in Attempt 1; **36 variants and 72 runs cumulative** on this hypothesis
family. Sealed, verbatim:

> No multiplicity correction is applied to the gate thresholds, because the thresholds are constitutional and may not be altered by a stage that would benefit from altering them. The multiplicity is disclosed instead, and it is the reason a development pass is explicitly not evidence of an edge.

> The 36 cumulative variants are not 36 independent tests. Attempt 2's risk architecture was chosen after seeing where Attempt 1 broke, so the effective number of researcher degrees of freedom is larger than 36 and is not quantified here because any quantification would itself be a choice made after the fact.

**17.4 — This is a development result.** Nothing here is evidence about the validation window, the
Generation 1 holdout, or the Generation 2 holdout. A development failure is not evidence that the
hypothesis is false out of sample; it is evidence that this grid, on this span, under this risk
architecture and these thresholds, produced nothing admissible.

**17.5 — The verdict is bounded by the run span.** 2008-07-28 → 2021-07-30. A grid run on a later
start that excluded 2008 would very likely have produced different figures, and this stage cannot say
what they would have been. It did not run one, and running one now to find out would be precisely the
post-hoc adjustment the frozen protocol forbids.

**17.6 — Better variants exist in the grid and were not selected.** This must be stated plainly.
`L03-K1-MONTHLY` returned **+63.15%** on its base run with a 0.1116 drawdown, a
1.9341 profit factor and 105 closed trades, and on the descriptive figures would
plausibly have cleared several conditions the representative missed. The frozen return-blind rule
selected the lowest-turnover variant instead, whose base return is +0.42%. That is the rule
working as designed, not failing: a rule that could see +63.15% would be a rule that selects on
return, and taking the best of eighteen and gating on it is
the abuse the rule exists to prevent. **Re-selecting on return is forbidden and was not done.** No
runner-up is promoted, in this session or a later one, and the figures above are recorded here so that
the cost of the rule is visible rather than buried.

**17.7 — The aggregate exposure ceiling drifts slightly above 0.50.** Measured maxima run
0.5043 to 0.5184 (§16). The ceiling is enforced at the fill open, and open-to-close
price movement on positions
already held can carry the book above it before the next session's throttle acts. This is
`G2A2-CONFLICT-27` / `-28`, disclosed and not corrected: correcting it would require intra-session
trading the execution convention does not permit, and the residual is bounded by the tests to under
one minimum lot per leg. It is a real deviation from a sealed constant and is reported as one.

**17.8 — The tiebreak now partly measures the risk architecture.** `SC-4`, declared before any run and
marked `not_corrected`. Fill count includes stop and throttle legs, so a variant whose risk
architecture intervened less has an advantage in step 2 that is not purely about signal turnover.

**17.9 — One candidate family.** Generation 2 declares a single candidate, so the constitution's
cross-candidate disjunction is over a set of size one (`G2A2-CONFLICT-26`, restating
`G2-CONFLICT-15`). A disjunction over one element carries none of the robustness a disjunction over
several would.

**17.10 — The two measurement bases.** §14's gate figures and §15's descriptive figures disagree for
the same run, by construction. Anyone comparing them without reading §14's measurement note will
conclude the package contradicts itself. The ledger basis is the sealed one and the gate's is binding.

**17.11 — Step 3 was never exercised on real data.** As in Attempt 1, and for the opposite reason:
there step 1 eliminated everything, here step 2 decided outright. The lexicographic tiebreak is
covered only by unit tests on synthetic inputs.

## 18. Conflicts found and how each was resolved

Ids `G2A2-CONFLICT-1` … `-24` were resolved in the sealed artifacts **before** any variant ran, and
are recorded in the pre-registration. Those restated here are the ones that bear on reading this
report; `-25` … `-28` were found during evaluation and `-29` while assembling the decision package,
all after the seal, and are disclosed here and in the decision record.

| Id | Conflict | Resolution |
|---|---|---|
| `G2A2-CONFLICT-18` | The frozen trade recorder attributes a partial trim's proceeds to no trade, so `S3-C3`/`C4`/`C5`/`C6` measured on `Portfolio.trades` would under-count exactly the mechanisms Attempt 2 adds. | The gate reads a purpose-built **episode ledger**. Sealed before any run. The recorder is not edited; §15 reports its basis and §14 reports the ledger's, with the divergence quantified. |
| `G2A2-CONFLICT-21` | The instruction's fail token names the **absence** of an admissible candidate; the constitution's names the **rejection** of one. | Both recorded. The sealed token `STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE` is emitted, with `STRATEGY_REJECTED_IN_DEVELOPMENT` recorded as the constitutional equivalent. |
| `G2A2-CONFLICT-24` | Attempt 1's tokens `STAGE_3_G2_STRATEGY_ADMITTED_IN_DEVELOPMENT` / `STAGE_3_G2_NO_CANDIDATE` are close enough to Attempt 2's to be emitted by accident. | Sealed as withheld. The package builder asserts that the token it writes is one of Attempt 2's two sealed tokens **and is neither of Attempt 1's**. |
| `G2A2-CONFLICT-25` | `SE100-CFG-3103` scopes the gate across both runs; `SE100-CFG-3104` measures `S3-C1` and `S3-C4` on the base run and lists the stress run as `reported_but_not_gating`. Sealed in the same session; neither outranks the other. | The **more restrictive** reading is adopted: all seven conditions on `#BASE`, and `S3-C1` … `S3-C6` also on `#STRESS`. `S3-C7` is evaluated once on base runs, because its own sealed `what_is_read` fixes the neighbour side to base-run total return. Both sets reported in full; a permissive base-only reading is recorded and would have given the same `false`. |
| `G2A2-CONFLICT-26` | Generation 2 declares one candidate, so §9's cross-candidate disjunction is over a set of size one and the rollup row settles nothing on its own. | Disclosed. The gate is decided by the `admissible_candidate_exists` row alone, which is present in the conditions table rather than omitted. |
| `G2A2-CONFLICT-27` | Measured maximum gross exposure exceeds the sealed 0.50 ceiling by 0.0043 to 0.0184. | Disclosed, not corrected. The ceiling is enforced at the fill open; open-to-close drift on held positions carries the book above it before the next throttle. Correcting it would require intra-session trading the execution convention forbids. |
| `G2A2-CONFLICT-28` | `AT-A` is worded as "verified after every fill and not only at session close", which the implementation satisfies, but the *observed* breach is a close-time phenomenon the wording does not cover. | Both statements kept. The test asserts what it says — no **fill** leaves the book above the scaled ceiling — and the close-time drift is reported separately as `-27` rather than by weakening the test to match the measurement. |
| `G2A2-CONFLICT-29` | The sealed `adaptation_disclosure_carriage_requirement` says both the sealer and the package builder assert byte-equality of the 842-character disclosure in all five carriers. One carrier cannot meet it: `STAGE_3_G2_ROTATION_RA1_PROTOCOL.md` hard-wraps the paragraph inside a blockquote at 100 columns, storing 858 characters — the sealed 842 with eight spaces replaced by eight newline-and-`>` continuation markers, and nothing else. That file is frozen and may not be rewrapped. | The frozen file is not touched and the check is not silently loosened. The sealer never asserted byte-equality on Markdown either: it compared `reporting.g2_partition_lock.normalised_prose` of both sides, because a hard-wrapped document cannot be checked line by line. The builder **imports** that same function rather than restating it, so its reading of "verbatim" cannot drift from the sealer's, records `carries_byte_exact` alongside `carries_verbatim` for every carrier, and asserts that the normalisation covers this one path and no other. The three JSON carriers and this report remain byte-exact and are still refused if they are not. |
| `G2-CONFLICT-4` | `repo_state_id`'s governance pattern is single-level, so `governance/generation_2/*` is **not** covered by it, while `config/**/*.json` is recursive and `config/generation_2/*.json` **is**. | Disclosed, not fixed. This report and the Generation 2 pre-registration are held by their own `.sha256` records and this package's artifact manifest; the config files are additionally held by `repo_state_id`. Widening the pattern would make `repo_state_id` incomparable across stages, which is worse. |

## 19. What was not done, and is not authorized

- **Stage 4 validation was not run.** The validation-window data exists on disk and is technically
  reachable. It was not read. This package does not authorize it, and no candidate is admitted for it
  to validate.
- **Generation 1's sealed holdout (2024-08-01 → 2026-07-31) was not read**, by this stage or by any
  code it ran.
- **Generation 2's holdout (2026-08-01 → 2028-07-31) does not exist in calendar time** and was not
  read. It may not be read before that period exists, under any circumstance, in this or any future
  session.
- **No broker connection was made, no credential was read or written, and no order, cancel, replace
  or liquidation was issued.** `live_trading_authorized` remains `false`; `paper_trading_authorized`
  remains `false`.
- **No Generation 1 artifact and no Attempt 1 artifact was modified.** See §20.
- **No test was weakened, skipped, `xfail`ed, deleted, or excluded.** See §21.
- **No runner-up was promoted and no re-selection was performed** after the representative failed.

## 20. Generation 1 and Attempt 1 artifacts: a checked claim

Attempt 1 is closed. Its verdict `FAIL — STAGE_3_G2_NO_CANDIDATE` stands permanently and nothing here
supersedes, reopens, re-runs or loosens it.

The claim is **checked, not asserted**, by three independent mechanisms:

1. **Re-hashing (`AT-H`).** Every module on the sealed `attempt_1_modules_immutable` list — nine
   modules — is re-hashed at evidence-build time against the digests recorded in the pre-registration
   (`SE100-GOV-2005`, `contamination_measurement.attempt_1_module_digests`). The recorded result is
   `modules_that_moved: []`. The same list is re-hashed independently by the test suite, which also
   asserts that the runner's own verification agrees with the tests' — and includes an injected-defect
   case in which a changed byte must be caught.
2. **The Stage 0 freeze re-verification**, which the shared builder runs on every package build and
   records in the decision record, plus the `.sha256` records for the partition lock, Attempt 1's
   pre-registration and Attempt 2's, all re-verified by this package's builder before it writes.
3. **Every Generation 1 and Attempt 1 artifact this stage stood on is listed in the package's
   `frozen_inputs_read_only`** with its digest and the disposition `READ_ONLY_NOT_MODIFIED`, and the
   artifact manifest carries digests for the whole tracked tree, so a reader can diff against any
   earlier stage's manifest.

Attempt 2's work is entirely **new files in new paths**: five new modules and one new test file under
`src/` and `tests/`, two new config files under `config/generation_2/`, three new pre-registration
artifacts under `governance/generation_2/`, this report, and a new `reports/stage3_g2_attempt2/`
directory. Attempt 1's `reports/stage3_g2/` was not written to. No Attempt 1 module name was reused,
overwritten or shadowed; the Attempt 2 modules carry the `_ra1` suffix throughout.

## 21. Tests

**1141 passed, 1 failed, 0 skipped — 1142
collected.** Full breakdown:
[STAGE_3_G2_A2_TEST_SUMMARY.md](../../reports/stage3_g2_attempt2/STAGE_3_G2_A2_TEST_SUMMARY.md).

The single failure is Generation 1's permanent red marker,
`test_no_stage_4_module_can_reach_restricted_data_or_a_broker`, recorded as `S4-CONFLICT-7`. It is
inherited untouched. It was not weakened, skipped, `xfail`ed, deleted, or excluded to make this
stage's suite look clean, and it has nothing to do with the Generation 2 Attempt 2 verdict.

Attempt 1 left the floor at **1091** tests. Attempt 2 adds **51** — all in
`tests/adversarial/test_g2_ra1_risk_architecture.py`, covering `AT-A` … `AT-I` — and removes nothing.

## 22. Artifacts produced

| Path | What it is |
|---|---|
| `governance/generation_2/STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md` | this document (`SE100-GOV-2006`) |
| `reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json` | the evidence file (`SE100-EVID-3102`) |
| `reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json` | the machine-readable decision record |
| `reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.sha256` | checksum record over frozen inputs and produced artifacts |
| `reports/stage3_g2_attempt2/STAGE_3_G2_A2_ARTIFACT_MANIFEST.json` | artifact manifest (excludes its own entry) |
| `reports/stage3_g2_attempt2/STAGE_3_G2_A2_TEST_SUMMARY.md` | test summary |
| `reports/stage3_g2_attempt2/pytest_stage3_g2_attempt2_output.txt` | raw pytest capture |
| `reports/stage3_g2_attempt2/{grid_results,selection_inputs,selection_record,gate_record,stage_verdict,run_span_recheck,attempt_1_module_verification}.json` | the runner's intermediate records |
| `runs/SE100-R-*.json` | append-only reproducibility records (the seal, and this package) |

The evidence file is `727,419` bytes, written `2026-08-15T12:53:13Z`, with file digest
`6f0c8f861541cb38cf9769658a72dc28994c1763f844db164beed4355ce00b91`. It carries a self-digest, `9232aa948413c53420cb3272a67f6953a72f71a1de2def5fb7380be05431b83f`, covering every field of that file
except `generated_utc` and `evidence_digest`, as canonical JSON. That self-digest was recomputed from
the written file by an independent script following the coverage sentence literally, rather than by
re-running the writer's own function — the only check that catches a file whose stated coverage and
actual coverage disagree, which is a defect two-run stability cannot see.

## 23. Reproduction

```bash
cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_rotation_ra1_preregistration
cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_stage3_attempt2_evidence
cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_stage3_attempt2_package
```

Verify the Generation 2 seals from the project root:

```bash
cd stockedge100 && sha256sum -c governance/generation_2/STAGE_1_G2_PARTITION_LOCK.sha256
cd stockedge100 && sha256sum -c governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.sha256
cd stockedge100 && sha256sum -c governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256
```

All three Generation 2 records list **project-root-relative** paths. Only the Stage 0 and Stage 1
*freeze* records use bare filenames and must be verified from `governance/`. A mismatch reported from
the wrong working directory is an operator error, not an integrity failure.

## 24. Next authorized action

**Human review of this package.** Nothing else.

No candidate is admitted, so Stage 4 validation has nothing to validate and is not authorized. The
sealed protocol closes this attempt on a FAIL: **there is no Attempt 3 without a further disclosed
adaptation, authorized in a later session.** Any such attempt would need a new pre-registration and a
new disclosure covering three attempts' worth of cumulative multiplicity on the same window — and the
honest reading of two failures is that this window has been looked at enough.

Specifically not authorized by this package, and not to be inferred from it: a nineteenth variant, a
re-run with different risk constants, a loosened gate threshold, a narrowing of the gate to the base
run, a change to the turnover definition, the promotion of `L03-K1-MONTHLY` or any other runner-up,
and any read of the validation window or either holdout.

---

## Verdict

```
FAIL — STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE
```

Gate 3 (development admissibility): **NOT PASSED**.

The risk architecture worked: zero research-shutdown events across all 36 runs, against 36 of 36 in
Attempt 1, with every variant's drawdown reduced. A representative therefore existed for the first
time — `SE100-G2-S3-C2-ROTATION-RA1-L12-K1-QUARTERLY`, selected return-blind at step 2 on
lowest turnover, 189 fills. Gate 3 was reached and evaluated on it, and it did not satisfy three of
seven hard conditions on its base run or four of six on its stress run.
`admissible_candidate_exists` is `NOT_MET`: 18 of 18 variants survived the screen, 1 candidate was
evaluated, 0 were admitted.

The verdict is a statement about the representative, not about the grid's best return. No return
figure was an input to the selection that produced the representative — the rule physically cannot
read one — and the grid contains variants that on descriptive figures look far stronger. §17.6
records them, and re-selecting on them is forbidden.

This is a deliverable, anticipated in writing before any variant ran, and it is kept on disk. It does
not license a nineteenth variant, a re-run with different constants, a loosened threshold, a gate
narrowed to the base run, or the promotion of a runner-up.

`live_trading_authorized`: `false`.
