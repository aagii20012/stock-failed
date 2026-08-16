# Stage 3 (Generation 2, Attempt 2) — rotation with risk architecture, development research report

| Field | Value |
|---|---|
| Document id | `SE100-GOV-2006` |
| Project | StockEdge100 |
| Generation | 2 |
| Generation id | `@@GENERATION_ID@@` |
| Stage | 3 — **Attempt 2** |
| Gate | 3 — development admissibility |
| Session type | Development research and evaluation |
| Strategy id | `@@STRATEGY_ID@@` |
| Governing document | `SE100-GOV-0001` (constitution, FROZEN) §§3, 4, 5.1, 6, 7, 9 gate 3, 10, 11, 19 |
| Charter | [STAGE_10_GENERATION_2_CHARTER.md](STAGE_10_GENERATION_2_CHARTER.md) (`SE100-GOV-2001`) |
| Partition lock | [STAGE_1_G2_PARTITION_LOCK.md](STAGE_1_G2_PARTITION_LOCK.md) (`SE100-GOV-2002`) |
| Attempt 1 | [STAGE_3_G2_ROTATION_RESEARCH_REPORT.md](STAGE_3_G2_ROTATION_RESEARCH_REPORT.md) (`SE100-GOV-2004`) — **CLOSED, READ-ONLY** |
| Pre-registration | [STAGE_3_G2_ROTATION_RA1_PROTOCOL.md](STAGE_3_G2_ROTATION_RA1_PROTOCOL.md) (`SE100-GOV-2005`), sealed |
| Protocol config | `config/generation_2/g2_rotation_ra1_protocol.json` (`SE100-CFG-3103`), sealed |
| Gate criteria | `config/generation_2/g2_gate_criteria_ra1.json` (`SE100-CFG-3104`), sealed |
| Evidence | `reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json` (`SE100-EVID-3102`) |
| Development window read | @@WINDOW_START@@ → @@BOUND@@ (run span @@RUN_START@@ → @@RUN_END@@, @@SESSIONS@@ sessions) |
| Latest session loaded | @@LATEST_LOADED@@ |
| Validation window | 2021-08-01 → 2024-07-31 — **not read** |
| Generation 1 holdout | 2024-08-01 → 2026-07-31 — **sealed, not read** |
| Generation 2 holdout | 2026-08-01 → 2028-07-31 — **does not exist in calendar time** |
| Authored (UTC) | @@AUTHORED_UTC@@ |
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
   drawdown fell — the worst in Attempt 2 is @@A2_DD_MAX_STRESS@@ against Attempt 1's worst of
   @@A1_DD_MAX@@ — and the whole grid now sits inside the 15% research-shutdown ceiling (§12).
2. **A representative therefore exists for the first time.** Step 1 of the selection rule admitted
   all eighteen variants instead of none; step 2 (lowest turnover, return-blind) decided on
   `@@REPRESENTATIVE@@` at @@REP_FILLS@@ fills across both runs, with no tie (§10, §11).
3. **The representative failed Gate 3.** Three of seven hard conditions are not satisfied on its base
   run and four of six on its stress run. Profit factor (@@REP_PF@@ against a 1.10 floor), the
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

> @@ADAPTATION_DISCLOSURE@@

The sealed `enforcement` clause reads, in as many words: *"The sealer and the package builder both
assert byte-equality of this string against the value in this file. A paraphrase is a failure, not a
stylistic choice."* It is carried in `governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md`,
the same file's `.json`, this report,
`reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json`, and the decision record
`reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json`.

The point of restricting the change to risk architecture is stated in the protocol and is worth
repeating here, because it bounds what this attempt can and cannot claim:

> @@WHAT_THIS_ADDS@@

That bounds the *attribution*, not the multiplicity. It does not make the development window pristine
again and it does not make a development pass evidence of an edge. See §17.

## 3. What was pre-registered, and when

The pre-registration was sealed in a separate phase of this session, **before any strategy,
engine, gate or runner code for Attempt 2 existed**, and the seal is recorded:

| Field | Value |
|---|---|
| Seal run id | `@@SEAL_RUN_ID@@` |
| Sealed (UTC) | @@SEAL_UTC@@ |
| `repo_state_id` at seal | `@@SEAL_REPO_STATE@@` |
| Protocol Markdown | `governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md` — `@@PROTO_MD_SHA@@` |
| Protocol JSON | `governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json` — `@@PROTO_JSON_SHA@@` |
| Protocol config | `config/generation_2/g2_rotation_ra1_protocol.json` — `@@PROTOCOL_CFG_SHA@@` |
| Gate criteria | `config/generation_2/g2_gate_criteria_ra1.json` — `@@CRITERIA_CFG_SHA@@` |
| Cost model | `config/generation_2/g2_cost_model.json` — `@@COST_MODEL_SHA@@` |
| Partition lock JSON | `governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json` — `@@LOCK_SHA@@` |
| Charter | `governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md` — `@@CHARTER_SHA@@` |

**How "before any code" is measured.** Attempt 1 sealed a path-based predicate — that no module with
a given filename existed. By Attempt 2 that predicate had become vacuous: Attempt 1's modules exist,
and a new attempt's code could have been written into a file whose name the predicate never
mentioned. The Attempt 2 seal therefore records a **content**-based measurement instead:

> @@DECL_PREDICATE@@

That is a statement about the contents of every `.py` file in the tree at seal time, not about a
list of filenames, and it is re-checkable after the fact against the sealed `repo_state_id`.

Everything the gate would later depend on was fixed at that moment: the eighteen-variant grid, the
run span, the universe, the cost model, the five risk constants and their combination rule, the
seven gate conditions and their measurement bases, the three-step selection rule, the two verdict
tokens, and the nine adversarial test requirements `AT-A` … `AT-I` in the protocol's own words.

## 4. The window actually read, and how that was enforced

The development bound is **@@BOUND@@**, carried from the partition lock. The run span is
**@@RUN_START@@ → @@RUN_END@@**, @@SESSIONS@@ sessions, unchanged from Attempt 1 and carried from
Attempt 1's protocol config (`@@A1_SPAN_SHA@@`)
rather than recomputed with a free hand. The binding symbol is `@@BINDING@@`, inception
@@BINDING_INCEPTION@@: the run starts at the first session on which a 12-month lookback has a
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
| Latest session loaded, any symbol | @@LATEST_LOADED@@ |
| Development bound | @@BOUND@@ |
| Validation window read | `false` |
| Generation 1 holdout read | `false` |
| Generation 2 holdout read | `false` |

The latest bar this session touched is **@@LATEST_LOADED@@**, one session inside the bound. The
validation data exists on disk and is technically reachable; it was not reached. The guard rejects a
window ending after the bound rather than silently truncating it, and it refuses to intersect either
holdout at all — Generation 2's holdout does not exist in calendar time and may not be read in any
future session before it does.

## 5. Universe and the eligibility re-check

Unchanged from Attempt 1 and re-verified rather than assumed:

| Field | Value |
|---|---|
| Universe version | `@@UNIVERSE_VERSION@@` |
| Universe identity digest | `@@UNIVERSE_ID@@` |
| Declared members | @@UNIV_DECLARED@@ |
| Loaded members | @@UNIV_LOADED@@ |
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

Unchanged: `config/generation_2/g2_cost_model.json` (`@@COST_MODEL_SHA@@`), which differs from the
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
`@@REPRESENTATIVE@@` at **@@REP_FILLS@@ fills**, and no other eligible variant matched that
count, so step 3 was not reached and the lexicographic tiebreak was never exercised on real data.

The representative was fixed at that point and never revisited. `no_reselection` is sealed; a
representative that fails the gate is not replaced by a runner-up, and §17.6 records what that costs
here, honestly.

## 12. Attempt 1 versus Attempt 2: the trip-wire

This is the one comparison the operating instruction asked for explicitly, and it is the strongest
result in this package.

@@TABLE_A1_A2@@

Attempt 1's shutdown events clustered in the post-crisis period; Attempt 2 has none to cluster:

@@TABLE_A1_MONTHS@@

Attempt 1's worst base-run drawdown was @@A1_DD_MAX@@ and its best was @@A1_DD_MIN@@ — the whole grid
was at or through the 15% ceiling. Attempt 2's range is **@@A2_DD_MIN@@ to @@A2_DD_MAX@@**, entirely
inside it, and every single variant improved. On the stress side the worst is @@A2_DD_MAX_STRESS@@,
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

Representative: **`@@REPRESENTATIVE@@`**, decided at step 2.

@@TABLE_GATE@@

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

**Where the representative actually fails.** Profit factor is **@@REP_PF@@** against a floor of 1.10 —
close, and a miss. The best-trade-removed condition fails decisively: removing the single largest
winner takes total return to **@@REP_BTR_BASE@@** on the base run and **@@REP_BTR_STRESS@@** on the
stress run, so the variant's entire positive return is one trade. Concentration fails by a wide
margin: the largest single-instrument contribution is **@@REP_CONC_BASE@@×** total strategy profit on
the base run and **@@REP_CONC_STRESS@@×** on the stress run, which is what a ratio looks like when
total profit is small and offsetting positions are large. On the stress run total return is negative
outright (@@REP_STRESS_RET@@).

Those three failures are consistent with each other and with the representative's shape:
@@REP_TRADES@@ closed trades over thirteen years, a base return of @@REP_BASE_RET@@, and a result
that rests on one position. This is a variant that survived the drawdown screen because it barely
traded, and the gate correctly declines to call that an edge.

**A measurement note that matters.** `S3-C3`, `S3-C4`, `S3-C5` and `S3-C6` are measured on the
**episode ledger**, not on `Portfolio.trades`. Attempt 2's throttle and ladder *trim* positions, and
the frozen trade recorder attributes a trim's proceeds to no trade at all — so the frozen recorder
would silently under-count realised P&L for exactly the mechanisms this attempt added. The divergence
is visible in the numbers: the descriptive grid table reports a profit factor of **@@REP_PF_RECORDER@@**
for this variant's base run on the recorder basis, while the gate measures **@@REP_PF@@** on the
ledger basis. The ledger is the correct basis and was sealed as such before any run
(`G2A2-CONFLICT-18`, §18). The gate figure is the binding one; §15's is descriptive.

## 15. Grid results — descriptive record only

Reported for completeness, as the operating instruction requires. **None of it gates anything.** The
gate was evaluated on the representative alone (§14), and no figure below was an input to the
selection that produced it. Profit factors here are on the frozen-recorder basis, which differs from
the gate's ledger basis for the reason given in §14.

**`#BASE` runs** — the modelled cost model.

@@TABLE_BASE@@

**`#STRESS` runs** — the same variants at 2× frictions.

@@TABLE_STRESS@@

## 16. Risk-architecture activity and turnover, for the record

Ladder activations and re-entry-lockout triggers per variant, as the operating instruction requires.
Descriptive only.

**`#BASE` runs.**

@@TABLE_RISK_BASE@@

**`#STRESS` runs.**

@@TABLE_RISK_STRESS@@

@@BAND3_COUNT@@ of eighteen variants reached the deepest ladder band (0.25 sizing) on the base run;
@@BAND2_COUNT@@ reached band 2 only. Every downward transition armed the lockout, and the lockout
blocked between @@LOCKOUT_MIN@@ and @@LOCKOUT_MAX@@ recovery attempts per base run — so it is doing
work rather than being nominally present.

Stop behaviour splits into two regimes. Most variants trigger a few dozen stops per run and fill
nearly all of them; @@STOP_OUTLIER_COUNT@@ of the 36 runs trigger at least three times what they
fill, the most extreme being @@STOP_OUTLIER_MAX@@. The gap is the
**pre-empted** column: a
position already closed by a scheduled rebalance or by the throttle before the stop's next-open fill
could execute. Both counts are reported because reporting only the triggers would overstate the stop's
activity and reporting only the fills would hide it.

The exposure throttle and the combined scalar, base runs:

@@TABLE_THROTTLE@@

Two columns deserve reading carefully. **Max gross fraction** sits between @@GROSS_MIN@@ and
@@GROSS_MAX@@ across all 36 runs — the table above is base-only, and its own minimum is therefore the
slightly higher @@GROSS_MIN_BASE@@ — that
is, slightly *above* the 0.50 ceiling, which is `G2A2-CONFLICT-27` and is disclosed rather than
papered over (§17.7, §18). **Legs below minimum notional** counts throttle legs that were computed and
then not issued because they fell under the minimum lot; that number is large because the throttle is
evaluated every session, and it is reported so that "throttle legs" is not read as "sessions on which
the throttle wanted to act".

The combined scalar spent most of the span below 1: between @@SCALAR_SESS_MIN@@ and
@@SCALAR_SESS_MAX@@ sessions out of @@SESSIONS@@, depending on variant, with means from
@@SCALAR_MEAN_MIN@@ to @@SCALAR_MEAN_MAX@@. The strategy was de-levered for the majority of the run.

Turnover, which is what step 2 of the selection rule reads:

@@TABLE_TURNOVER@@

## 17. Disclosed limitations

**17.1 — The adaptation.** §2 carries the sealed disclosure verbatim and it is not repeated here.
It is the governing limitation on everything in this report: the development window is no longer
pristine for this hypothesis family, and no development result from this attempt can by itself
establish a trading edge.

**17.2 — Validation-window reuse.** Sealed as `validation_reuse_disclosure` in the partition lock
JSON (`SE100-GOV-2002`) and reproduced verbatim, substituted mechanically as a single unbroken line:

> @@VALIDATION_REUSE@@

**17.3 — Multiple comparisons, cumulative across attempts.** Eighteen variants and 36 runs this
attempt; eighteen and 36 in Attempt 1; **36 variants and 72 runs cumulative** on this hypothesis
family. Sealed, verbatim:

> @@MC_NOCORR@@

> @@MC_ADAPTIVE@@

**17.4 — This is a development result.** Nothing here is evidence about the validation window, the
Generation 1 holdout, or the Generation 2 holdout. A development failure is not evidence that the
hypothesis is false out of sample; it is evidence that this grid, on this span, under this risk
architecture and these thresholds, produced nothing admissible.

**17.5 — The verdict is bounded by the run span.** @@RUN_START@@ → @@RUN_END@@. A grid run on a later
start that excluded 2008 would very likely have produced different figures, and this stage cannot say
what they would have been. It did not run one, and running one now to find out would be precisely the
post-hoc adjustment the frozen protocol forbids.

**17.6 — Better variants exist in the grid and were not selected.** This must be stated plainly.
`@@BEST_VARIANT@@` returned **@@BEST_RET@@** on its base run with a @@BEST_DD@@ drawdown, a
@@BEST_PF@@ profit factor and @@BEST_TRADES@@ closed trades, and on the descriptive figures would
plausibly have cleared several conditions the representative missed. The frozen return-blind rule
selected the lowest-turnover variant instead, whose base return is @@REP_BASE_RET@@. That is the rule
working as designed, not failing: a rule that could see @@BEST_RET@@ would be a rule that selects on
return, and taking the best of eighteen and gating on it is
the abuse the rule exists to prevent. **Re-selecting on return is forbidden and was not done.** No
runner-up is promoted, in this session or a later one, and the figures above are recorded here so that
the cost of the rule is visible rather than buried.

**17.7 — The aggregate exposure ceiling drifts slightly above 0.50.** Measured maxima run
@@GROSS_MIN@@ to @@GROSS_MAX@@ (§16). The ceiling is enforced at the fill open, and open-to-close
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
report; `-25` … `-28` were found during evaluation, after the seal, and are disclosed here and in the
decision record.

| Id | Conflict | Resolution |
|---|---|---|
| `G2A2-CONFLICT-18` | The frozen trade recorder attributes a partial trim's proceeds to no trade, so `S3-C3`/`C4`/`C5`/`C6` measured on `Portfolio.trades` would under-count exactly the mechanisms Attempt 2 adds. | The gate reads a purpose-built **episode ledger**. Sealed before any run. The recorder is not edited; §15 reports its basis and §14 reports the ledger's, with the divergence quantified. |
| `G2A2-CONFLICT-21` | The instruction's fail token names the **absence** of an admissible candidate; the constitution's names the **rejection** of one. | Both recorded. The sealed token `STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE` is emitted, with `STRATEGY_REJECTED_IN_DEVELOPMENT` recorded as the constitutional equivalent. |
| `G2A2-CONFLICT-24` | Attempt 1's tokens `STAGE_3_G2_STRATEGY_ADMITTED_IN_DEVELOPMENT` / `STAGE_3_G2_NO_CANDIDATE` are close enough to Attempt 2's to be emitted by accident. | Sealed as withheld. The package builder asserts that the token it writes is one of Attempt 2's two sealed tokens **and is neither of Attempt 1's**. |
| `G2A2-CONFLICT-25` | `SE100-CFG-3103` scopes the gate across both runs; `SE100-CFG-3104` measures `S3-C1` and `S3-C4` on the base run and lists the stress run as `reported_but_not_gating`. Sealed in the same session; neither outranks the other. | The **more restrictive** reading is adopted: all seven conditions on `#BASE`, and `S3-C1` … `S3-C6` also on `#STRESS`. `S3-C7` is evaluated once on base runs, because its own sealed `what_is_read` fixes the neighbour side to base-run total return. Both sets reported in full; a permissive base-only reading is recorded and would have given the same `false`. |
| `G2A2-CONFLICT-26` | Generation 2 declares one candidate, so §9's cross-candidate disjunction is over a set of size one and the rollup row settles nothing on its own. | Disclosed. The gate is decided by the `admissible_candidate_exists` row alone, which is present in the conditions table rather than omitted. |
| `G2A2-CONFLICT-27` | Measured maximum gross exposure exceeds the sealed 0.50 ceiling by @@GROSS_EXCESS_MIN@@ to @@GROSS_EXCESS_MAX@@. | Disclosed, not corrected. The ceiling is enforced at the fill open; open-to-close drift on held positions carries the book above it before the next throttle. Correcting it would require intra-session trading the execution convention forbids. |
| `G2A2-CONFLICT-28` | `AT-A` is worded as "verified after every fill and not only at session close", which the implementation satisfies, but the *observed* breach is a close-time phenomenon the wording does not cover. | Both statements kept. The test asserts what it says — no **fill** leaves the book above the scaled ceiling — and the close-time drift is reported separately as `-27` rather than by weakening the test to match the measurement. |
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

**@@TESTS_PASSED@@ passed, @@TESTS_FAILED@@ failed, @@TESTS_SKIPPED@@ skipped — @@TESTS_TOTAL@@
collected.** Full breakdown:
[STAGE_3_G2_A2_TEST_SUMMARY.md](../../reports/stage3_g2_attempt2/STAGE_3_G2_A2_TEST_SUMMARY.md).

The single failure is Generation 1's permanent red marker,
`test_no_stage_4_module_can_reach_restricted_data_or_a_broker`, recorded as `S4-CONFLICT-7`. It is
inherited untouched. It was not weakened, skipped, `xfail`ed, deleted, or excluded to make this
stage's suite look clean, and it has nothing to do with the Generation 2 Attempt 2 verdict.

Attempt 1 left the floor at **@@TESTS_PRIOR@@** tests. Attempt 2 adds **@@TESTS_NEW@@** — all in
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

The evidence file is `@@EVIDENCE_BYTES@@` bytes, written `@@EVIDENCE_UTC@@`, with file digest
`@@EVIDENCE_SHA@@`. It carries a self-digest, `@@EVIDENCE_SELF@@`, covering every field of that file
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
time — `@@REPRESENTATIVE@@`, selected return-blind at step 2 on
lowest turnover, @@REP_FILLS@@ fills. Gate 3 was reached and evaluated on it, and it did not satisfy three of
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
