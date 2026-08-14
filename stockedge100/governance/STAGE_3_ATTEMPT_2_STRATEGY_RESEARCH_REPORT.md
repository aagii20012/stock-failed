# StockEdge100 — Stage 3 Attempt 2 strategy research report

| Field | Value |
| --- | --- |
| Document id | `SE100-GOV-3002` |
| Project | StockEdge100, generation 1 |
| Stage | Prompt stage 3, second attempt — constitutional gate 3 (development admissibility) |
| Session type | Implementation and development evaluation of the sealed Attempt 2 specification. No validation read, no holdout read, no broker contact. |
| Governing document | `SE100-GOV-0001` — `governance/STAGE_0_CONSTITUTION.md`, FROZEN, v1.0.0 |
| Pre-registration | `SE100-GOV-0007` — `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.{md,json}`, sealed `2026-08-10T11:59:33Z` under run `SE100-R-20260810T115933Z` |
| Design-session record | `SE100-GOV-3001` — `PASS — STAGE_3_ATTEMPT_2_PREREGISTRATION_FROZEN`, run `SE100-R-20260810T131107Z`, exit status `GATE_NOT_PASSED` |
| Attempt 1 record | `SE100-GOV-0006` — `FAIL — STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT`, run `SE100-R-20260810T101622Z`. Unmodified. |
| Evidence | `SE100-EVID-3002` — `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json`, generated `2026-08-12T13:19:21Z`, exit status `0` |
| Development window | `1993-01-29` → `2021-07-31`, from `governance/STAGE_1_HOLDOUT_LOCK.json` |
| Authored (UTC) | 2026-08-13T11:52:47Z |
| Verdict | `PASS — STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT` |
| Gate 3 | **Passed on the development window only.** Two of three pre-registered candidates were admitted. This authorizes consideration of the next prospectively governed stage and nothing else. |
| Validation window | `LOCKED`, unread |
| Final holdout | `SEALED`, unread |
| `live_trading_authorized` | `false` |

The `run_id` of this evaluation session and the repository-state digest are deliberately **not**
written into this file. `repo_state_id` is computed over `governance/*.md` among other patterns, so
writing a tree digest here would invalidate it on write. Both values live in
`reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.json` and in the append-only `runs/`
record for this session, which are outside the digest's patterns. Individual **file** digests are
quoted below, because a file digest is not a digest of the tree that contains this file.

---

## 1. The result, stated first

Three pre-registered candidates were implemented from the sealed Attempt 2 specification and
evaluated once each on the development window, together with their twelve registered robustness
neighbours and three non-gating stressed-cost runs. Eighteen runs, exactly as declared. Fifteen of
the eighteen gate.

| Candidate | Total return | Max drawdown | Profit factor | Closed trades | Shutdown | Admitted |
| --- | --- | --- | --- | --- | --- | --- |
| `SE100-S3A2-C1-PULLBACK-RA1` | `0.0986` | `0.1467` | `1.1058` | 489 | none | **Yes** |
| `SE100-S3A2-C2-MEANREV-RA1` | `0.5599` | `0.1260` | `1.4402` | 333 | none | **Yes** |
| `SE100-S3A2-C3-DEFENSIVE-RA1` | `1.0490` | `0.0953` | `4.2529` | 98 | none | No — `S3-C6` `NOT_MET` |

Drawdowns are quoted at the four-decimal figure the evidence file records in
`deepest_drawdown_4dp`; returns and profit factors are quoted rounded for reading. Full-precision
values are in the machine-readable record and are reproduced condition by condition in section 10.

`admissible_candidate_exists` is `true`. Gate 3 is passed.

Three things about that result matter more than the headline, and are stated here rather than buried:

1. **The risk architecture did what it was designed to do, and that is the whole of the news.**
   Attempt 1's six candidates all breached the frozen 15% drawdown ceiling; Attempt 2's three
   primaries all stayed under it, the deepest being C1 at `0.1467`. Every other condition C1 and C2
   satisfy, they also satisfied in Attempt 1's equivalent signal form. What changed is the drawdown,
   and the drawdown is what the sealed risk architecture was built to change.
2. **Neither admitted candidate beats buy-and-hold SPY over the same window** — not on the index
   series and not on the tradable series. The only candidate that beats tradable SPY is C3, which
   was rejected. Benchmarks do not gate this stage, and they are reported in section 15 because a
   pass that omitted them would be misleading.
3. **C3's rejection was declared as a likely outcome before any result existed.** The sealed
   protocol records, under C3's own `s3_c6_disclosed_risk`, that S3-C6 was "the condition most likely
   to reject C3 even if the risk architecture works". It is the condition that rejected C3. Section
   12 quotes the disclosure in full.

This is a development-window admissibility result. It is not an edge, not a forecast, and not trade
readiness. Section 19 states precisely what it authorizes.

---

## 2. What this session was allowed to do

The design session of `2026-08-10` sealed a specification and explicitly did **not** evaluate it.
Its verdict, `PASS — STAGE_3_ATTEMPT_2_PREREGISTRATION_FROZEN`, authorized implementation of the
sealed design and nothing further. This session did exactly that, in the order the sealed protocol
requires: implement, test, freeze the implementation, run the declared evaluations once, evaluate
the frozen conditions, build the package, stop.

What this session did not do, and what the evidence file records as `explicit_non_authorizations`,
quoted from `SE100-EVID-3002`:

> No data of any kind is downloaded, purchased, or acquired by this attempt. Every price comes from
> the Stage 1 normalized dataset already on disk.

> No validation-window or holdout-window data is read. The window guard raises `WindowViolation`
> structurally rather than relying on discipline.

> No frozen artifact is edited, regenerated, replaced, superseded, or re-encoded. Attempt 1's
> `SE100-CFG-3001`, `SE100-CFG-3002`, its pre-registration, its decision record, its manifest, its
> checksum records, and its run record are read-only and byte-for-byte unchanged.

> No Attempt 1 candidate is re-run, re-parameterised, repaired, or combined with an Attempt 2
> candidate.

> No Gate 3 condition, threshold, denominator, predicate, boundary, undefined case, or
> not-evaluable treatment is changed. The 15% maximum-drawdown ceiling is unchanged.

> No candidate is combined with any other candidate. Constitution section 8 prohibits combination
> until each component has an independent verdict, and no Attempt 2 component has one.

> No machine learning, no optimiser, no search over any parameter grid, and no fit of any kind.

> No fundamental, earnings, or intraday data is introduced. None exists in this project.

> No paper order, no live order, no cancel, no replace, no liquidation, no broker call, and no
> unattended scheduling.

> No Alpaca credential is read, and no credential presence is tested by this attempt.

> No strategy is selected as a winner, and no expected income, profit, or return is claimed for any
> period, past or future.

> `live_trading_authorized` remains `false`.

One further limit deserves its own line, because a passed gate invites the opposite reading. The
evidence file records it as `no_selection_in_this_stage`:

> Gate 3 is admissibility, not selection. Every candidate that satisfies every hard condition is
> recorded as admitted; the stage does not rank admitted candidates, does not name a winner, and
> does not carry a preference forward. Choosing which admitted candidate proceeds is a later-stage
> decision under the constitution's own rules.

C1 and C2 are therefore both admitted and neither is preferred. C2's return is more than five times
C1's; that fact selects nothing.

---

## 3. Integrity verification performed before anything was implemented

Verification came first, and it was verification of the tree rather than of this prompt's claims.

**Frozen artifacts.** Eleven checksum records were verified, each from the working directory its own
entries are relative to, and all eleven reported `OK`:

| Record | Entries | Verified from |
| --- | --- | --- |
| `governance/STAGE_0_FREEZE.sha256` | 2 | `stockedge100/governance/` |
| `governance/STAGE_1_FREEZE.sha256` | 2 | `stockedge100/governance/` |
| `governance/STAGE_1_PREREGISTRATION.sha256` | 4 | `stockedge100/` |
| `governance/STAGE_2_PREREGISTRATION.sha256` | 4 | `stockedge100/` |
| `governance/STAGE_3_PREREGISTRATION.sha256` | 4 | `stockedge100/` |
| `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256` | 4 | `stockedge100/` |
| `reports/stage0/STAGE_0_VERIFICATION.sha256` | 8 | `stockedge100/` |
| `reports/stage1/STAGE_1_DATA_READINESS.sha256` | 19 | `stockedge100/` |
| `reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256` | 20 | `stockedge100/` |
| `reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256` | 26 | `stockedge100/` |
| `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256` | 31 | `stockedge100/` |

The first two use bare filenames and the other nine use project-root-relative paths. Running
`sha256sum -c` on the first two from the project root reports a file-not-found failure that is an
operator error and not an integrity failure; both were verified from `governance/`.

**The sealed inputs this evaluation is bound to**, with the digests recomputed in this session:

| Path | Document | sha256 |
| --- | --- | --- |
| `governance/STAGE_0_CONSTITUTION.md` | `SE100-GOV-0001` | `b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5` |
| `governance/STAGE_0_CONSTITUTION.json` | `SE100-GOV-0001` | `af45fda6b37bed50768d5f3d01d4a91175da93e708c9daf1b630e35a981e2ff5` |
| `governance/STAGE_1_HOLDOUT_LOCK.json` | `SE100-GOV-0003` | `9696161c4c5612fc7f6b3e5a3410917f20ad5707cb9b89b8bcc39cb70831dfb3` |
| `governance/STAGE_1_UNIVERSE.json` | `SE100-GOV-0002` | `01601a60fa950a2429f72a2e9f627ec5af4c1853d1b47ffab35e81debc7eb67a` |
| `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.md` | `SE100-GOV-0007` | `d9e34b3ce61f5998fe91c0b7b551a29a778fdb410330e60d6919c0a94ec447c6` |
| `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json` | `SE100-GOV-0007` | `9a92dbdf88c2cc6e3a9a9ee80debba6bdcd9f70a45b50e8c5bbe127455afaca6` |
| `config/stage3_attempt2_strategy_protocol.json` | `SE100-CFG-3003` | `77f1451c20e37640bd2843ff86d69eb54cbc0ebb592a696972fbdea6e05b5433` |
| `config/stage3_attempt2_gate_criteria_binding.json` | `SE100-CFG-3004` | `a482f499173c0d7e2b0ca158b2edf7cb2e25a516ac2eb361e1441b2964006c8e` |
| `config/stage3_gate_criteria.json` | `SE100-CFG-3002` | `310f1c978380f4a1d6b98b8c368975b1515476b032c123afb06f1dd597e3e18d` |
| `config/stage3_strategy_protocol.json` | `SE100-CFG-3001` | `04dbe3fa8c6b2a9e725a66d24f5dc0a3a7e3567e70d38bfd2e96869cc6e169b6` |
| `config/stage2_cost_model.json` | `SE100-CFG-2001` | `f62d98436445cfc436463765ff6006dd234a3082ddf429992296645e697586e2` |

Every one of these is byte-for-byte the value recorded before Attempt 2 had any strategy code. The
evidence file re-records eight of them under `sealed_inputs.digests_recomputed_at_load`, recomputed
at evaluation time rather than copied, together with
`sealed_before_any_attempt_2_strategy_code: true`.

**Starting state.** The repository-state identifier recomputed at the start of this session by the
project's canonical method reproduced the sealed ending identifier of the design session exactly, so
this session began from the sealed Attempt 2 state with no unexplained difference. Per the rule
above, the value is not written here: the binding copies are the field in
`runs/SE100-R-20260810T131107Z.json` and `starting_repo_state_id` in this session's
machine-readable decision record. That value could in fact be quoted safely, because it is a digest
of a tree state that predates this file — but no governance report in this project quotes a
repository-state digest of any kind, and the convention is worth more than the convenience.

**Partition guards.** Both guards were confirmed active before any candidate ran, and both are
structural rather than procedural. `BacktestEngine.__init__` calls the window check on both bounds
and raises `WindowViolation`; every decision constructs a market view bounded by the decision
session and raises `LookAheadError` on any attempt to read past it. The evidence file states of the
Attempt 2 code path: "Attempt 2 adds no code path that could bypass them." `boundary_changes` is
recorded as `"None."`

**Restricted partitions.** `validation_observations_read` is `false` and
`holdout_observations_read` is `false` in the evidence file, and no test in the suite touches either
partition. The evidence file's own qualification of that claim is quoted rather than paraphrased,
because it is narrower than it first reads:

> It is a statement about what reached a computation: the normalized per-symbol CSVs are opened in
> full at load time, as they were at Gate 2 and at Attempt 1's Gate 3, so it is not a claim that no
> later-dated row was ever read off disk.

**Attempt 1.** No Attempt 1 artifact was opened for writing at any point. Its pre-registration,
protocol, criteria, decision record, manifest, checksum record and run record are unchanged, and its
verdict stands as issued.

**No unauthorized prior implementation.** At the start of this session no Attempt 2 strategy module
and no Attempt 2 result artifact existed. The design session's own record states
`attempt_2_strategy_implementation_present_at_sealing: none` and
`attempt_2_performance_generated_before_sealing: none`, and the file listing confirmed it. Every
Attempt 2 strategy file named in section 4 was created in this session, after the verification above
completed.

---

## 4. What was implemented, and how each rule traces to a sealed field

Nine modules were added under `src/stockedge100/strategies/` and `src/stockedge100/reporting/`:

| Module | Responsibility |
| --- | --- |
| `strategies/attempt2_config.py` | Loads and seal-checks `SE100-CFG-3003`, `SE100-CFG-3004`, `SE100-CFG-3002` |
| `strategies/attempt2_indicators.py` | `VOL20`, and the RSI and moving averages the three candidates need |
| `strategies/attempt2_risk.py` | RA1-1 … RA1-8 as one shared component |
| `strategies/attempt2_candidates.py` | C1, C2, C3 signal logic on top of the shared risk component |
| `strategies/attempt2_runner.py` | Variant planning, dataset loading, single-variant execution |
| `strategies/attempt2_harness.py` | The eighteen declared runs, condition evaluation, rollup, gate verdict |
| `strategies/attempt2_traceability.py` | The field-by-field map from sealed field to code to test |
| `reporting/attempt2_evidence.py` | Emits `SE100-EVID-3002` |
| `reporting/stage3_attempt2_evaluation_package.py` | Builds this decision package |

**The traceability map is executable, not prose.** `attempt2_traceability.py` holds 127 rows. Each
row names a sealed document and a JSON path within it, the code object that implements it, and the
tests that exercise it. `verify()` resolves both ends of every row — it walks the sealed path in the
loaded configuration and imports the named code object — and reports:

| Property | Value |
| --- | --- |
| Rows | 127 |
| Distinct sealed paths required | 118 |
| Rows sourced from `SE100-CFG-3003` | 110 |
| Rows sourced from `SE100-CFG-3004` | 8 |
| Rows sourced from `SE100-CFG-3002` | 9 |
| Distinct implementation references | 74 |
| Distinct named tests | 90 |
| `all_rows_resolve` | `true` |
| `missing_coverage` | empty |
| `duplicate_rows` | empty |

`missing_coverage()` works the other direction, which is the direction that catches real omissions:
it enumerates the sealed paths that *must* be covered and reports any that no row claims. It returns
empty. A row that pointed at a sealed path which does not exist, or at a code object which does not
import, would fail `verify()` rather than merely reading oddly.

**No discretionary choice was required.** Every parameter, threshold, timing rule, ordering rule and
edge case came from a sealed field. The one place where the sealed text admits two readings —
`SE100-CFG-3001`'s `shared_rules.sizing_rule`, which says position size is not a research variable
"in this stage" and on a broad reading would prohibit RA1-2 — was already resolved *before* this
session, prospectively, in the sealed binding's `recorded_interpretations` as `A2-INTERP-1`, and is
carried forward here as a recorded conflict rather than a decision taken now. See section 18. No
specification-ambiguity blocker was needed.

---

## 5. RA1 as implemented

All three candidates share one risk architecture, implemented once in `attempt2_risk.py` and
identical across candidates by construction rather than by convention. The sealed `design_intent` is
the reason it exists:

> S3-C2 is satisfied if and only if the constitution section 5.1 research shutdown never fires. RA1
> is the structural answer to that: it lowers exposure, caps single-position loss, reduces size as
> account drawdown grows, and bounds time at risk. Every constant below is either taken from a
> frozen artifact or derived arithmetically from constants that are, and none was selected by
> inspecting an Attempt 1 equity path.

| Rule | Sealed content, as implemented |
| --- | --- |
| RA1-1 exposure ceiling | `f_base = 0.50`. Applies to the defensive leg too, with the disclosed consequence that a SHY-holding candidate sits at roughly 50% SHY and 50% cash. |
| RA1-2 volatility-targeted entry sizing | At entry only. `sigma_target = 0.10` annualised, `sigma = VOL20` at the decision close, `f_vol = sigma_target / sigma`, `f = min(f_cap, f_vol)` where `f_cap` is the RA1-5 rung. `sigma == 0` → `NO_ENTRY_ZERO_VOLATILITY`; `f < 0.05` → `NO_ENTRY_VOLATILITY_FLOOR`; `budget = f * equity` below `1.00` → `NO_ENTRY_SIZE_FLOOR`. It can never *increase* exposure above `f_cap`. |
| RA1-3 per-position loss control | `L = 0.08` against `P_ref`, the close of the decision session that scheduled the entry. Exit reason `EXIT_LOSS_CONTROL`. Not a stop order and not a bound: the sealed text quotes §5.2 — "Stops are risk tools, not guarantees; overnight gaps may exceed intended losses." |
| RA1-4 maximum holding period | Per-candidate `H`, counted in decision sessions where the symbol was open, current session included. Reason `EXIT_MAX_HOLD`. |
| RA1-5 account de-risk ladder | Read at entry only, to set `f_cap`. `hwm` is the running maximum of account equity over decision sessions, updated whether flat or not; `dd = (hwm - equity) / hwm`; `dd < 0.08 → 0.50`, `0.08 ≤ dd < 0.10 → 0.25`, `dd ≥ 0.10 → 0.125`. The equity series is byte-identical to the one the §5.1 shutdown reads. It never blocks an entry. |
| RA1-6 re-entry lockout | After `EXIT_LOSS_CONTROL` or `EXIT_MAX_HOLD`, no re-entry in that symbol for `R = 5` decision sessions from the exit-scheduling session. Blocked entries recorded as `NO_ENTRY_LOCKOUT`. An `EXIT_SIGNAL` creates no lockout. |
| RA1-7 conflict resolution | The shared flat-first rule, unchanged. Every symbol switch costs a full session out of the market; a switch following a risk exit costs at least six. |
| RA1-8 all-or-nothing positions | No partial entry or exit, no scaling, no averaging down, no pyramiding. The sealed reason is not only §5.1 but that partial exits would make the closed-trade series ambiguous — and that series is the basis of S3-C3 through S3-C6. |

Exit precedence is `EXIT_LOSS_CONTROL` → `EXIT_MAX_HOLD` → `EXIT_SIGNAL`, and the sealed text is
explicit that this is "Reason attribution only. The precedence changes no exit decision… so it
cannot affect any metric." The implementation matches: precedence selects the label on an exit that
would happen regardless.

The shutdown relationship is enforced for every run — primary, neighbour and stressed — and a
candidate emits nothing while the shutdown is active. No candidate reads the ceiling.

**RA1 as it actually behaved.** The diagnostics below are recomputed from each primary's own run
record and are the most informative single table in this report, because they say which parts of the
architecture bore weight:

| Diagnostic | C1 pullback | C2 mean reversion | C3 defensive |
| --- | --- | --- | --- |
| Decision sessions | 6978 | 7077 | 4585 |
| Entries emitted / filled | 489 / 489 | 333 / 333 | 99 / 99 |
| `EXIT_LOSS_CONTROL` | 4 | 8 | 0 |
| `EXIT_MAX_HOLD` | 0 | 4 | 5 |
| `EXIT_SIGNAL` | 485 | 321 | 93 |
| `NO_ENTRY_LOCKOUT` | 14 | 9 | 25 |
| `NO_ENTRY_ZERO_VOLATILITY` | 0 | 0 | 0 |
| `NO_ENTRY_VOLATILITY_FLOOR` | 0 | 0 | 0 |
| `NO_ENTRY_SIZE_FLOOR` | 0 | 0 | 0 |
| Sessions at `f_cap = 0.50` | 2884 | 6476 | 4477 |
| Sessions at `f_cap = 0.25` | 761 | 442 | 108 |
| Sessions at `f_cap = 0.125` | 3333 | 159 | 0 |
| Sessions with shutdown active | 0 | 0 | 0 |
| Exits caused by shutdown | 0 | 0 | 0 |

Four readings of that table are worth stating.

The **loss control almost never fires**: 4 exits in 489 round trips for C1, 8 in 333 for C2, none at
all for C3. RA1-3 is not what kept these candidates under the ceiling.

The **volatility floor never bound**. The sealed protocol predicted this: `f_floor = 0.05` binds only
above 200% annualised volatility, and the development window never presented it. All three
`NO_ENTRY_VOLATILITY_FLOOR` counts are zero, as is every `NO_ENTRY_SIZE_FLOOR` and every
`NO_ENTRY_ZERO_VOLATILITY`.

The **ladder is where C1 spent its life**. C1 sat at the deepest rung, `f_cap = 0.125`, for 3333 of
its 6978 decision sessions — 47.8% of them. C2 spent 159 sessions there and C3 none. C1 and C2
answer the same 15% ceiling by very different routes: C2 by rarely being far below its high-water
mark at all, C1 by trading at an eighth of equity for nearly half its history.

The **middle rung was never skipped in practice**. The sealed drawdown arithmetic noted that its
illustrative worst-case path skips the `0.25` rung; the realised paths did not, spending 761, 442 and
108 sessions there respectively.

---

## 6. Why RA1 is not a stop at 14.99%

The operating constraint on the design was that RA1 must not become a mechanical device for stopping
just short of the ceiling. The sealed text commits to that in advance:

> RA1 is not a device for stopping at 14.99%. No rule references the 15% ceiling, no rule references
> a drawdown level between 10% and 15%, and no rule is conditioned on proximity to the shutdown. The
> deepest level RA1 reacts to is 10%, which is the constitution's own section 5.2 hard risk halt…

Three checks, and all three are measurements rather than assertions.

**No implemented rule reads the ceiling.** The deepest drawdown level any RA1 rule references is
`0.10`, the §5.2 hard halt. The three parameters that could have encoded the ceiling — the ladder's
two rung boundaries and its three fractions — are `0.08`, `0.10`, `0.50`, `0.25`, `0.125`. Each is a
frozen constant or a halving of one. `engine_shutdown_relationship` records
`no_candidate_reads_the_ceiling`, and the code path bears that out: the candidates receive a
shutdown flag and emit nothing when it is set, and they never receive the level.

**The realised drawdowns are not clustered under the ceiling.** A mechanical stop-at-14.99% device
would produce primaries bunched just below `0.15`. The three primaries came in at `0.1467`, `0.1260`
and `0.0953`, and the twelve neighbours range from `0.0765` to `0.1544`. The spread is what one
expects from a size discipline, not from a boundary detector.

**One neighbour crossed the line, and nothing caught it.** `SE100-S3A2-C1-PULLBACK-RA1#N1`
(`sma_long: 150`) reached a drawdown of `0.1544` and tripped the §5.1 research shutdown on
`2020-02-27`. Its equity was liquidated at the next open, entries were blocked, and it never
re-armed. That is the strongest available evidence that RA1 is not a ceiling-avoidance mechanism:
a registered neighbour, running the same architecture with one signal parameter changed, breached the
ceiling and the machinery let it. Had RA1 been a stop at 14.99%, N1 would have stopped at 14.99%.

The sealed `drawdown_arithmetic` — computed by hand before any code existed, and labelled in the
protocol itself as "NOT a prediction, NOT a guarantee" — worked out that seven consecutive
maximum-loss round trips are required to breach the ceiling, six leaving drawdown at `14.15%`. That
arithmetic was about a worst case that did not occur; only four loss-control exits happened for C1 in
total. It is recorded here because it was the design's stated reasoning, not because it predicted the
outcome.

---

## 7. Eighteen declared runs, fifteen of them gating

The pre-registration declares 18 runs and 15 gating variants. The distinction is sealed, and it is
reproduced exactly rather than inferred. From the evidence file's `iteration_budget`:

| Field | Value |
| --- | --- |
| `candidates` | 3 |
| `runs_per_candidate` | one primary run plus four robustness-neighbour runs, plus one non-gating stressed-cost run of the primary |
| `gating_variants_per_candidate` | 5 |
| `max_variants_per_candidate` | 5 |
| `total_declared_gating_variants` | 15 |
| `total_declared_non_gating_stress_runs` | 3 |
| `total_declared_runs` | 18 |
| `gating_variants_executed` | 15 |
| `non_gating_stress_runs_executed` | 3 |
| `runs_executed` | 18 |
| `candidates_evaluated` | 3 |
| `revisions_made` | 0 |
| `variants_rerun_after_seeing_a_result` | 0 |
| `determinism_reruns_outside_the_declared_budget` | 3 |

So: 3 primaries + 12 neighbours = 15 gating variants, and 3 stressed-cost runs of the primaries
which are declared but do not gate. 15 + 3 = 18.

Two sealed clarifications sit alongside those counts and are the reason the arithmetic is not a
loophole. `neighbour_runs_are_not_iterations`: a neighbour is a diagnostic of the primary, not
another attempt at passing. `stress_runs_are_not_iterations`: a stressed-cost run cannot admit
anything, so running one buys no extra chance of a pass.

The three determinism re-runs are recorded outside the declared budget, and the sealed `rerun_policy`
is explicit about why that is not a loophole either:

> a re-run of an unchanged variant must reproduce byte-identical output. A re-run that produced a
> DIFFERENT number would be a determinism defect and a blocker, not a better result.

No valid completed evaluation was repeated. No variant was rerun after its result was seen. No
unregistered variant was evaluated. No unregistered post-result diagnostic was run on development
observations.

---

## 8. Three defects found before any result existed

The sealed `post_seal_defect_rule` permits correcting a technical defect before the first valid
completed evaluation, provided the defect, the correction, the tests and the evidence that no valid
result was seen first are all recorded. Three defects were found and corrected under that rule. All
three were found by the dry-run and test passes, before any candidate had produced a performance
number.

| # | Defect | Correction | Detected by |
| --- | --- | --- | --- |
| 1 | The stressed-cost helper probed `stress['cost_model']['stress_multiplier']`, a key that does not exist in `SE100-CFG-2001`. | The multiplier is now an explicit `Decimal` parameter supplied by the caller from the sealed field that does exist. | Evidence-generation dry run, before any run executed |
| 2 | The rollup's `decisive_row` emitted the gate's condition *prose* in the field reserved for its verdict *token*. | Split into two fields: `gate_verdict_condition` for the prose and `gate_verdict_token` for the token, the token derived from the sealed `verdict_token_derivation`. | Package builder dry run |
| 3 | `attempt2_config.py` named a dead `require_seal=False` parameter in a docstring, which the frozen lexical guard at `tests/adversarial/test_stage3_defects.py` correctly refuses. | The dead parameter was removed entirely rather than the docstring reworded, so the seal check has no bypass to name. | The frozen Stage 3 adversarial suite |

Defect 3 deserves emphasis because of which direction it was caught from. A frozen test written in a
previous stage failed against new code, and the resolution was to change the new code. The suite went
from `1 failed, 559 passed` to `560 passed` by deletion of a bypass, not by relaxation of a test. No
test was weakened, skipped, xfailed or deleted at any point in this session.

A fourth item was corrected in a test fixture rather than in engine code, and is recorded because it
was a wrong belief rather than a typo: an integration fixture asserted that the 5% cash buffer holds
at every equity point. It does not, and the minimum observed cash fraction across a full run is
`0.04120977268852710606552764159`. The buffer is a *pre-trade* sizing constraint, not a post-trade
invariant of the equity path; mark-to-market movement after a fill can carry the ratio below it
without any rule having been broken. The fixture now asserts the constraint the engine actually
enforces.

After the first valid completed evaluation, no code and no parameter was revised. The evaluation ran
once, at `2026-08-12T13:13:21Z` through `2026-08-12T13:19:21Z`, exit status `0`.

---

## 9. What the three candidates did

Full per-variant metrics for all fifteen gating variants are in the machine-readable results. The
primaries:

| Metric | C1 pullback | C2 mean reversion | C3 defensive |
| --- | --- | --- | --- |
| Universe | `SPY` | `SPY` | `SPY`, `SHY` |
| Warm-up sessions | 200 | 101 | 200 |
| First session | `1993-11-11` | `1993-06-23` | `2003-05-14` |
| Last session | `2021-07-31` | `2021-07-31` | `2021-07-31` |
| Sessions | 6979 | 7078 | 4586 |
| Final equity | `109.86` | `155.99` | `204.8953406953044240008` |
| Total return | `0.0986` | `0.5599` | `1.048953406953044240008` |
| CAGR | `0.0034` | `0.0159` | `0.0402` |
| Max drawdown | `0.1467` | `0.1260` | `0.0953` |
| Sharpe, 0% risk-free | `0.1285` | `0.4202` | `0.7655` |
| Profit factor | `1.1058` | `1.4402` | `4.2529` |
| Closed trades | 489 | 333 | 98 |
| Wins / losses / scratches | 309 / 175 / 5 | 230 / 101 / 2 | 38 / 59 / 1 |
| Win rate | `0.6319` | `0.6907` | `0.3878` |
| Exposure fraction | `0.2479` | `0.1666` | `0.9730` |
| Longest flat streak | 376 sessions | 107 sessions | 6 sessions |
| Fills | 978 | 666 | 197 |
| Dividend events | 27 | 14 | 101 |
| Stale marks | 0 | 0 | 0 |
| Rejections | 0 | 0 | 0 |
| Shutdown | none | none | none |
| Open positions at end | 0 | 0 | 1 |

C3's single open position at the end of the window is why its reconstructed closed-trade return
(`1.0354`) is lower than its equity-curve return (`1.048953406953044240008`): the last leg was still
held on `2021-07-31`. The gap is accounted for, not an inconsistency, and section 10 shows both
figures where S3-C5 uses them.

C3's start date is `2003-05-14` rather than `1993`, because SHY's inception binds the run window and
the sealed warm-up of 200 sessions applies from there. It is therefore evaluated over roughly
eighteen years against C1's and C2's twenty-eight, and its CAGR and Sharpe are not comparable to
theirs on equal terms. The sealed protocol already records that C3's window differs from Attempt 1's
F6 for the same reason and that "the two candidates are not a matched comparison."

Two structural notes on the numbers. Sharpe uses a 0% risk-free rate, because Stage 1 acquired no
Treasury-bill series and the constitution permits the proxy when point-in-time data are unavailable;
the direction of the bias is to flatter a strategy and penalise cash, and C3, which holds SHY, is the
candidate most affected. And exposure fraction counts sessions with any position open, which is why
C3 reads `0.9730` — a regime strategy is almost always in one leg or the other — while C1 and C2,
which sit in cash between trades, read `0.2479` and `0.1666`.

---

## 10. Condition by condition

The seven conditions are `SE100-CFG-3002`'s, adopted unchanged. `SE100-CFG-3004` records each row as
`"adopted": "unchanged"`, with two entries carrying a re-derivation note rather than a change:
S3-C6's `applies_to` enumeration and S3-C7's declaring-artifact reference. Both re-derivations are
described in section 11. The `0.15` drawdown ceiling and its inclusive boundary are unchanged, and
the binding states the position plainly: "Unchanged. Attempt 2 lowers the risk taken to meet the
ceiling; it does not raise the ceiling to meet the risk."

Conditions are conjunctive **within** a candidate. Satisfaction means
`verdict in (MET, NOT_APPLICABLE_BY_CONDITION_TEXT)`; `NOT_MET`, `NOT_EVALUABLE`, `NOT_RUN`,
`UNKNOWN`, `MISSING_EVIDENCE` and absence are all not satisfied.

### `SE100-S3A2-C1-PULLBACK-RA1` — admitted

| Condition | Required verbatim | Predicate | Measured | Verdict |
| --- | --- | --- | --- | --- |
| S3-C1 | total return is positive | `> 0` | `0.0986` | `MET` |
| S3-C2 | maximum drawdown is no worse than 15% | `<= 0.15` | `0.1467059341675684739975927832247007` | `MET` |
| S3-C3 | profit factor is at least 1.10 | `>= 1.1` | `1.105782641347494903980259628795194` | `MET` |
| S3-C4 | at least 30 closed trades exist, unless a lower-frequency protocol predeclared a longer evidence requirement before results | `>= 30` | `489` | `MET` |
| S3-C5 | performance is not dependent on one trade: removing the single best trade leaves total return above 0% | both removals `> 0` | `min(0.074248012204971731131652158305661, 0.075098659003831417624521072796943)` | `MET` |
| S3-C6 | no single instrument contributes more than 50% of total strategy profit for a multi-instrument strategy | `<= 0.50` | not applicable — `declared_instrument_count = 1` | `NOT_APPLICABLE_BY_CONDITION_TEXT` |
| S3-C7 | reasonable neighboring parameter values do not reverse the sign of net return | all four signs match | 4 of 4 match, primary sign `+1` | `MET` |

C1's S3-C2 margin is the tightest of the three: `0.1467` against a ceiling of `0.15`, a margin of
about 33 basis points of drawdown. That is a real fragility and it is recorded as one in section 20.

### `SE100-S3A2-C2-MEANREV-RA1` — admitted

| Condition | Predicate | Measured | Verdict |
| --- | --- | --- | --- |
| S3-C1 | `> 0` | `0.5599` | `MET` |
| S3-C2 | `<= 0.15` | `0.1260098725439263296638239081881548` | `MET` |
| S3-C3 | `>= 1.1` | `1.440207563487695573551379825457976` | `MET` |
| S3-C4 | `>= 30` | `333` | `MET` |
| S3-C5 | both removals `> 0` | `min(0.508779557964264543991870607164014, 0.508779557964264543991870607164014)` | `MET` |
| S3-C6 | `<= 0.50` | not applicable — `declared_instrument_count = 1` | `NOT_APPLICABLE_BY_CONDITION_TEXT` |
| S3-C7 | all four signs match | 4 of 4 match, primary sign `+1` | `MET` |

C2's two S3-C5 removals are identical because both the best-by-multiple and best-by-P&L trade are the
same one, trade index 52 (multiple `1.033881982139730344948345298546664`, P&L `3.87`); the evidence
records `j1_equals_j2: true`. Removing it leaves `0.5088`, a long way above zero.

### `SE100-S3A2-C3-DEFENSIVE-RA1` — not admitted

| Condition | Predicate | Measured | Verdict |
| --- | --- | --- | --- |
| S3-C1 | `> 0` | `1.048953406953044240008` | `MET` |
| S3-C2 | `<= 0.15` | `0.09533757051577858300688104129544525` | `MET` |
| S3-C3 | `>= 1.1` | `4.252906063462142632736412189758090` | `MET` |
| S3-C4 | `>= 30` | `98` | `MET` |
| S3-C5 | both removals `> 0` | `min(0.764597527949447955003124783001182, 0.783600000000000000000000000000002)` | `MET` |
| S3-C6 | `<= 0.50` | `0.9796214023565771682441568475951323` | **`NOT_MET`** |
| S3-C7 | all four signs match | 4 of 4 match, primary sign `+1` | `MET` |

C3 satisfies six of seven and fails one. Because conditions are conjunctive within a candidate, six
of seven is a failed candidate. It is not admitted, it is not carried forward, and its higher return
and lower drawdown than either admitted candidate change nothing about that.

**How S3-C5 is measured.** The sealed measurement basis is quoted rather than restated, because the
exactness claim in it is the reason a reconstruction is admissible at all: "Closed trades only, in
exit order. Because the sealed cost model permits at most one open risky position, trades are
sequential and non-overlapping, so a compounded reconstruction is exact rather than an
approximation." The procedure starts at `E[0] = 100.00` and applies `E[i] = E[i-1] + pnl[i]`, with
`r[i] = E[i]/E[i-1]`. Two removals are evaluated for each candidate — the best trade by return
multiple and the best by absolute P&L — and both must leave a positive total return. For C1 they are
different trades (index 48 and index 132) and both removals leave `0.0742` and `0.0751`. The
reconstructed totals reproduce the equity-curve totals to the last decimal for C1 (`0.0986`) and C2
(`0.5599`); C3's reconstruction is `1.0354` against an equity curve of `1.048953406953044240008`,
the difference being the one position still open at the window's end.

**S3-C4 needed no exception.** The sealed condition allows a lower-frequency protocol to have
predeclared a longer evidence requirement before results. None did, and none needed to: the closed
trade counts are 489, 333 and 98 against a floor of 30. `exception_invoked` is recorded as false for
every candidate.

**No condition was `NOT_EVALUABLE` for any candidate.** No profit factor was undefined, no candidate
had zero closed trades, and no neighbour failed to run. Every one of the 21 condition evaluations
returned either `MET`, `NOT_MET` or `NOT_APPLICABLE_BY_CONDITION_TEXT`.

---

## 11. The rollup, and why aggregating on `MET` would have produced a false failure

Every one of the seven per-condition rollup rows reads `PASS`. That fact decides nothing, and the
evidence file carries the warning in the artifact itself:

> A per-condition rollup row aggregates SATISFACTION across candidates and therefore means only "at
> least one candidate satisfied this condition". It is not evidence that any candidate satisfied all
> of them, and it settles nothing on its own.

The shape of the reporting is prescribed for a specific reason, also recorded in the evidence:

> Aggregating a per-condition row on `verdict == MET` rather than on satisfaction produced a false
> FAIL for S3-C6 in Attempt 1's first rollup. The rollup must aggregate on satisfaction. It is
> recorded here so the same defect is not reintroduced by a fresh implementation.

Attempt 2's implementation is a fresh one, and S3-C6 is exactly where the old defect would have
reappeared:

| Row | Satisfied by ≥1 | `met_by` | `not_met_by` | `not_applicable_for` |
| --- | --- | --- | --- | --- |
| S3-C1 | `true` | C1, C2, C3 | — | — |
| S3-C2 | `true` | C1, C2, C3 | — | — |
| S3-C3 | `true` | C1, C2, C3 | — | — |
| S3-C4 | `true` | C1, C2, C3 | — | — |
| S3-C5 | `true` | C1, C2, C3 | — | — |
| S3-C6 | `true` | *(empty)* | C3 | C1, C2 |
| S3-C7 | `true` | C1, C2, C3 | — | — |

S3-C6's `met_by` list is **empty**. No candidate met it: C3 failed it and C1 and C2 were not subject
to it. Aggregated on `verdict == MET`, that row would read `FAIL` and the report would appear to
show a failed condition. Aggregated on satisfaction, which is the sealed rule, it reads `PASS`
because C1 and C2 satisfied it by condition text. Both readings are visible in the table above
precisely because the three lists are kept separate, which is what the sealed
`required_reporting_shape` demands.

**The decisive row.** The gate is decided by one row and not by the seven above:

| Field | Value |
| --- | --- |
| `admissible_candidate_exists` | **`true`** |
| `satisfied_definition` | `verdict in (MET, NOT_APPLICABLE_BY_CONDITION_TEXT)` |
| `within_candidate` | `CONJUNCTIVE` — all seven evaluated for every candidate; all applicable ones must be satisfied by that same candidate |
| `across_candidates` | `DISJUNCTIVE` — one admissible candidate is enough to pass Gate 3 |
| Candidates evaluated | 3 |
| Admitted candidates | `SE100-S3A2-C1-PULLBACK-RA1`, `SE100-S3A2-C2-MEANREV-RA1` |
| Gate verdict | `PASS` |
| Gate verdict token | `STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT` |

No passing condition was combined across candidates. C1's admission rests on C1's own seven
verdicts; C2's on C2's own. The sealed binding asks how many admissible candidates are required and
answers "Exactly one."

**The two re-derivations.** Neither changes a condition; both were sealed before results.

`A2-REDERIVE-1` concerns S3-C6's scope. The sealed `applies_to` enumeration names Attempt 1's F5 and
F6 by identifier. Read literally against Attempt 2, that enumeration is empty — which would silently
make S3-C6 not-applicable even for a candidate declaring two instruments, and that is a weakening.
The rule applied instead is the structural one the condition text implies:
`declared_instrument_count > 1`. It makes S3-C6 applicable to C3 and not applicable to C1 and C2,
with their instrument counts recorded as the evidence. The binding's own words: "It is not a blank
pass."

`A2-REDERIVE-2` concerns S3-C7's declaring artifact. For Attempt 2 the artifact that declares the
neighbours is `SE100-CFG-3003`, not Attempt 1's `SE100-CFG-3001`. The count is enforced in code:
`src/stockedge100/strategies/gate.py` raises when a candidate does not present exactly four sealed
neighbours.

---

## 12. C3, and a failure mode declared before the result

C3 failed S3-C6 with a measured concentration of `0.9796214023565771682441568475951323` against a
ceiling of `0.50`. The evidence:

| Field | Value |
| --- | --- |
| `declared_instrument_count` | 2 |
| `declared_universe` | `SPY`, `SHY` |
| `total_closed_trade_pnl` | `103.54` |
| `pnl_by_instrument` | `SPY 101.43`, `SHY 2.11` |
| `share_by_instrument` | `SPY 0.9796214023565771682441568475951323`, `SHY 0.02037859764342283175584315240486768` |
| `largest_contributor` | `SPY` |

SPY produced 97.96% of C3's closed-trade profit and SHY produced 2.04%.

This is not a surprise and it must not be reported as one. The sealed protocol carries, under C3's
own `s3_c6_disclosed_risk`, the following — written before any Attempt 2 code existed and before any
result was seen:

> This is the condition most likely to reject C3 even if the risk architecture works. A regime
> strategy whose risk leg is an equity index and whose defensive leg is a short-duration Treasury
> fund has no reason to split profit evenly between them, and F6 failed this condition in Attempt 1.
> It is declared here, before any result, that C3 was kept in the candidate set with that failure
> mode understood and accepted, because a three-candidate set with no multi-instrument candidate
> would leave S3-C6 not-applicable for every candidate and would answer less of the research
> question.

Everything in that paragraph came true. C3 was rejected by the named condition, for the named
reason, and Attempt 1's F6 failed the same condition before it. The disclosure is the reason this
report can state that C3's rejection is a confirmation of a pre-registered expectation rather than a
discovery, and the reason C3's retention in the candidate set is not a multiplicity abuse: the third
candidate was included knowing it was the one most likely to fail, which is the opposite of adding
candidates to buy a pass.

It also means something narrower than it may appear. S3-C6 is a *concentration* condition, not a
performance condition. C3's return of `1.0490` was the highest of the three, its drawdown of
`0.0953` the shallowest, and its profit factor of `4.2529` the largest. None of that survives a
failed hard condition, and none of it is carried forward. A reader tempted to prefer C3 on those
numbers is reading a rejected candidate.

---

## 13. The robustness neighbours

Each candidate declares exactly four neighbours — the count the gate enforces in code — and all
twelve ran. Their role is fixed by the sealed binding and is worth quoting because a passed gate
invites exactly the misuse it forbids: "Diagnostic only." Whether a better-performing neighbour may
be promoted: "No. Never. Under no result." And: "A candidate whose primary fails but whose four
neighbours all pass is a FAILED candidate." A neighbour that failed to run would be `NOT_RUN`, which
the binding notes is "Not a pass."

| Variant | Changed parameter | Total return | Max drawdown | Profit factor | Closed trades | Sign matches | Shutdown |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 `#N1` | `sma_long: 150` | `0.0267` | `0.1544` | `1.0322` | 466 | yes | `2020-02-27` |
| C1 `#N2` | `sma_short: 20` | `0.2156` | `0.0997` | `1.1870` | 361 | yes | none |
| C1 `#N3` | `vol_target: 0.08` | `0.0887` | `0.1293` | `1.0839` | 489 | yes | none |
| C1 `#N4` | `f_base: 0.35` | `0.1309` | `0.0942` | `1.1282` | 489 | yes | none |
| C2 `#N1` | `rsi_entry_below: 5` | `0.1039` | `0.1439` | `1.2512` | 176 | yes | none |
| C2 `#N2` | `exit_sma: 10` | `0.2291` | `0.1466` | `1.2722` | 301 | yes | none |
| C2 `#N3` | `vol_target: 0.08` | `0.4327` | `0.1265` | `1.3797` | 333 | yes | none |
| C2 `#N4` | `loss_control: 0.12` | `0.2239` | `0.1332` | `1.3082` | 332 | yes | none |
| C3 `#N1` | `sma_long: 150` | `0.9824` | `0.0819` | `3.0886` | 146 | yes | none |
| C3 `#N2` | `defensive_symbol: null` | `0.8336` | `0.0965` | `3.1238` | 64 | yes | none |
| C3 `#N3` | `vol_target: 0.08` | `1.0085` | `0.0796` | `4.4297` | 98 | yes | none |
| C3 `#N4` | `f_base: 0.35` | `0.7506` | `0.0765` | `4.2353` | 98 | yes | none |

All twelve returns are positive and all twelve match their primary's sign, so S3-C7 is `MET` for
every candidate, `4 of 4` in each case, with `neighbours_not_run` empty.

Four observations, three of which cut against the candidates.

**Three of four C1 neighbours outperform C1's primary**, `#N2` by more than double. The primary is
what gates; a neighbour that looks better is a signal about the fragility of the primary's specific
parameter choice, not a candidate. Under the sealed rules it cannot be promoted and it is not.

**C1 `#N1` breached the ceiling and tripped the shutdown.** At `sma_long: 150` instead of 200,
drawdown reached `0.1544` and the §5.1 research shutdown fired on `2020-02-27`. Sign stability is
unaffected — the run still ended at `+0.0267` — but the finding is that C1's compliance with S3-C2 is
not robust to a 25% change in its long moving-average length. Section 20 records this as a
limitation.

**C2's neighbours all sit within a narrow band** of `0.1039` to `0.4327`, all below the primary's
`0.5599`, with drawdowns from `0.1265` to `0.1466`. The primary is the best of its five, which is
the pattern one worries about; but the neighbours were declared before results and their parameters
were not searched, so the pattern is an observation rather than evidence of selection.

**C2 `#N4` loosens rather than tightens** its risk control, `loss_control: 0.12` against the sealed
`0.08`. The sealed note explains the choice: it "tests whether the candidate's sign depends on the
specific loss limit rather than on a level that flatters it." It does not — `#N4` returns `0.2239`,
still positive.

The neighbours keep the count of admissibility trials at 3 rather than 15. The binding states the
numerical consequence directly: "It keeps the number of admissibility trials at 3 for Attempt 2
rather than 15."

---

## 14. Determinism

The sealed condition is that "each primary reproduces its own trades and equity digests on a re-run".
All three primaries were re-run once, outside the declared budget, and all three reproduced
byte-identical trade and equity digests.

| Candidate | `trades_digest` | `equity_digest` | Identical on re-run |
| --- | --- | --- | --- |
| C1 | `95d9a60146ee8962e1f1ae2b74d771162c957634d5cfca66b1d183c70de35f64` | `3757036560e060005d30a86a0d6a5ec60ce5351256b97079c52cd514f710bb20` | yes |
| C2 | `299dc2c4cec963668bc08c67601f431851695c78c5f1d7e056fa9f42e1e6112d` | `e50d787ef2733034ab7a418823b255d785ff0038d0fa657a38e89b7d44ff67d8` | yes |
| C3 | `48c7467add4db1de605eb86dc7f1255997607ffe56990594523ea512418f1a44` | `a29bc9b6342635de0e4bb33e37d2ce23671678981c158fae05099ce706ea366e` | yes |

`all_identical` is `true`.

Random seeds are recorded as `null`, and the evidence file states why the field is present rather
than omitted: "There are none to declare. The field is present and null rather than absent, so that
its absence cannot later be read as an omission." Nothing in the engine or in any Attempt 2 module
draws a random number; determinism here is a property of exact Decimal arithmetic over a fixed input
series, not of a fixed seed.

---

## 15. Benchmarks, which do not gate this stage

Gate 3 has no benchmark condition. Buy-and-hold comparisons are reported because omitting them from
a passing report would misrepresent what was achieved.

| Candidate | Strategy return | SPY index | SPY tradable | Beats index | Beats tradable |
| --- | --- | --- | --- | --- | --- |
| C1 | `0.0986` | `14.8163` | `1.1376` | no | no |
| C2 | `0.5599` | `15.6909` | `1.2440` | no | no |
| C3 | `1.0490` | `5.6298` | `0.4550` | no | **yes** |

Each candidate is compared over its own run window, which is why the SPY figures differ between
rows — C3's window starts in 2003.

The finding is unflattering and it is the honest one: **neither admitted candidate beats buying and
holding SPY**, on either benchmark series, over the window on which it was admitted. C1 returned
`0.0986` where tradable SPY returned `1.1376` over the same sessions. The only candidate that beats
tradable SPY is C3, and C3 was rejected.

That is not a contradiction of the gate. Gate 3 asks whether a specification is admissible — positive
after cost, within the drawdown ceiling, with enough trades, not dependent on one trade, not
concentrated, sign-stable under neighbouring parameters. It does not ask whether the specification
beats the market, and a candidate that clears admissibility with a low return has cleared exactly
what was asked and nothing more. It does mean that any later claim of value for C1 or C2 must be
argued on risk-adjusted or drawdown grounds rather than on return, and that the comparison at Gate 4
will be a harder test than this one.

---

## 16. Stressed costs, which do not gate this stage

Three non-gating stressed-cost runs of the primaries were declared and executed at a `2.0`
multiplier on trading friction. The stress scales friction only; the sealed note records that
`min_order_notional_usd` and `research_shutdown_drawdown` stay at their base values, so the 15%
shutdown level is the same under stress.

| Candidate | Return, base → stressed | Drawdown, base → stressed | Closed trades | Shutdown under stress |
| --- | --- | --- | --- | --- |
| C1 | `0.0986` → `0.0018` | `0.1467` → `0.1530` | 489 → 432 | **`2018-02-05`** |
| C2 | `0.5599` → `0.3311` | `0.1260` → `0.1269` | 333 → 333 | none |
| C3 | `1.0490` → `0.9347` | `0.0953` → `0.0978` | 98 → 98 | none |

No flags were raised on any stressed run.

**C1 does not survive doubled costs.** Its return falls from `0.0986` to `0.0018` — 18 basis points
over twenty-eight years — its drawdown crosses the 15% level to `0.1530`, and the research shutdown
fires on `2018-02-05`, three and a half years before the window ends. Had the stressed run been the
gating one, C1 would have failed S3-C2 outright and very nearly failed S3-C1.

This does not change C1's admission. The gating cost model is the base model, that was fixed before
results, and adjusting which cost model gates after seeing the outcome is precisely what the sealed
rules forbid. But it is the single most important qualification on this report's `PASS`: **C1 is
admitted on a cost assumption it cannot survive being doubled.** C2 loses 41% of its return under
the same stress and keeps a positive result with an unchanged drawdown and an unchanged trade count.
C3, already rejected, is the most robust of the three to cost stress.

Section 20 carries this forward as a limitation, and it belongs in whatever prospective
pre-registration governs Gate 4.

---

## 17. Nine candidates against one development window

This is an adaptive second attempt and every disclosure the sealed protocol requires on that point is
reproduced here.

**Attempt 1's results were known before Attempt 2 was designed.** The sealed
`known_prior_evidence.attempt_1_headline_fact`:

> All six candidates produced positive after-cost total return and all six passed neighbour sign
> stability, and all six breached the 15% maximum-drawdown ceiling of S3-C2. Three additionally
> missed the 30-closed-trade floor of S3-C4, two failed the profit-concentration condition S3-C6, and
> one failed the best-trade-removal condition S3-C5.

**The development data are not pristine.** Six specifications have already been evaluated on this
window and their results read. Attempt 2's three candidates were designed with those results in
hand. Three of the three hold their entry and exit signal in the same rule *form* as a rejected
Attempt 1 candidate: C1's form is F2's, C2's is F3's, C3's is F6's. New code does not make Attempt 2
an independent confirmation of anything.

**The adaptation is disclosed as an adaptation.** The sealed protocol does not describe RA1 as an
insight; it describes it as a response to a measured failure. Attempt 1's most useful finding,
quoted in the seal:

> The observation in section 7 — that the risk control and the quality gate are the same number, so
> any candidate volatile enough to trip one has failed the other — is the most useful thing this
> stage produced, and it belongs to whoever writes the next pre-registration.

RA1 is the answer built to that observation, and C2's sealed record is candid about the resulting
thinness of the distinction from F3. F3's sealed exit rule stated that "There is no stop, no time
exit, and no profit target: adding one would be a rule chosen after the fact." The seal's own answer:

> That sentence is correct about F3 and remains correct about F3 permanently… Declaring a stop and a
> time exit prospectively in a NEW candidate that restarts at Gate 3 under a new pre-registration is
> the route constitution section 11 provides… The distinction is real but it is thin… the reason a
> stop and a time exit are being declared at all is that Attempt 1 showed unstopped, untimed mean
> reversion breached the ceiling. That is an adaptation, and it is disclosed as one.

C1's record is equally direct about the counter-argument against it:

> A reader may reasonably say that reusing a rejected signal and bolting risk controls onto it is a
> repair of F2 by another name… the honest position is that C1's result is a second look at the same
> signal on the same data by the same researcher.

**Cumulative counts, exactly as sealed:**

| Count | Attempt 1 | Attempt 2 | Cumulative |
| --- | --- | --- | --- |
| Primary candidates | 6 | 3 | **9** |
| Gating variants | 30 | 15 | **45** |
| Declared runs | 30 | 18 | **48** |
| Revisions permitted | — | 0 | **0** |
| Distinct signal forms | 6 | 0 new | **6** |

The last row is the one that matters most for interpreting this pass. Nine distinct *specifications*
have now been tested at Gate 3, but only six distinct *signal forms*: Attempt 2 introduced no new
signal idea, only new risk machinery around three existing ones.

**Multiplicity is disclosed and not corrected numerically.** The sealed text:

> …the probability that at least one of nine specifications passes by chance exceeds the probability
> that any single pre-specified one does… Nothing in this attempt corrects for it numerically. The
> correction the constitution relies on is that an admitted candidate must still survive Gate 4
> robustness, Gate 5's single sealed holdout read, and the duration-based paper and shadow gates.
> Attempt 2 weakens none of those and earns no relief from any of them.

Two admitted candidates out of nine cumulative specifications, on data that six of those
specifications have already seen, is weaker evidence than two out of two on fresh data would be. That
is the correct way to read section 1's table, and no part of this report claims otherwise.

---

## 18. Conflicts and observations recorded, not repaired

Nothing below was fixed. Every item is recorded so that a later reader finds the discrepancy already
described rather than discovering it.

**`A2-EVAL-CONFLICT-1` — the operating prompt's verdict tokens do not exist in any sealed artifact.**
The prompt for this session named `STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY_MET` and
`STAGE_3_ATTEMPT_2_STRATEGIES_REJECTED_IN_DEVELOPMENT` as the pass and fail equivalents. Neither
string appears in `SE100-CFG-3002`, in `SE100-CFG-3004`, in the pre-registration, or anywhere else in
the repository. The sealed `verdict_token_derivation` in `SE100-CFG-3002` defines exactly two tokens
for this gate: `pass_token: STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT` and
`fail_token: STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT`. The prompt itself instructs that the exact
token be derived from repository governance and that no pass token be invented when the governing
artifacts define another. The sealed token is therefore used, and the divergence from the prompt's
wording is recorded here. The token in the machine-readable record is read from that sealed field at
build time rather than written as a literal.

**`A2-EVAL-CONFLICT-2` — `SE100-CFG-3002` contains five U+2014 em-dash bytes.** They sit inside prose
fields. Attempt 1 recorded them; this attempt confirms the count is exactly five and that there is no
U+FFFD replacement character anywhere in the file. The file is frozen, so the characters stay.

**`A2-EVAL-OBS-1` — `profit_factor` is recorded at two precisions in the evidence file.** Every
primary's `runs[…].profit_factor` and its corresponding `S3-C3.measured` are the same quotient
computed under different Decimal contexts. `strategies/gate.condition_3` is decorated to run under
the engine context at 34-digit precision; `backtest/metrics.profit_factor` carries no such decorator
and inherits the caller's context, which is Python's 28-digit default. It is the only metric function
in `metrics.py` without the decorator and the only one of the four directly comparable run/condition
pairs that diverges — `total_return`, `max_drawdown` and `closed_trades` agree to the last digit for
all three candidates. Verified by recomputing `gross_profit / gross_loss` from the S3-C3 evidence at
both precisions: the 34-digit result reproduces `S3-C3.measured` byte for byte and the 28-digit
result reproduces the run field byte for byte, for all three candidates. The divergence is at the
28th significant digit. The gate reads `condition_3`, so the decisive figure is the 34-digit one, and
no candidate's profit factor is within `1e-27` of the `1.10` threshold. `metrics.py` is Stage 2 code,
byte-unchanged in this session, and Attempt 2 added no code path to it. It is disclosed rather than
repaired: the sealed rules forbid revising code after a valid completed evaluation and forbid
rerunning one.

**Carried forward from Attempt 1 and from the design session, unchanged:**

`S3-CONFLICT-1` — `SE100-CFG-3002`'s Markdown declares seven thresholds where its JSON companion
declares five. The Markdown is authoritative. Unrepaired.

`S3-CONFLICT-2` — the criteria file defines no `pass_result` key, so the pass token is derived from
`verdict_token_derivation`. Unrepaired.

`S3-CONFLICT-3` — the S3-C2 quality ceiling and the §5.1 research shutdown are the same 15% measured
on the same equity series, so a candidate volatile enough to trip the shutdown has already failed the
condition. Attempt 2 adopted this identity as its design target rather than treating it as a defect.

`S3-CONFLICT-4-ATTEMPT-2` — `SE100-CFG-3001`'s `shared_rules.sizing_rule` states that position size
is not a research variable "in this stage", which on a broad reading would prohibit RA1-2's
volatility-targeted sizing. The broad reading was rejected prospectively in the sealed binding's
`recorded_interpretations` as `A2-INTERP-1`, before any Attempt 2 code existed. Recorded, not
repaired.

---

## 19. What this `PASS` means, and what it does not

**It means** that two of three pre-registered Attempt 2 specifications satisfied every applicable
hard condition of constitutional gate 3 on the development window, under the sealed cost model, with
the evaluation run exactly once and reproducing byte-identically on re-run. It means the risk
architecture declared before any result achieved the specific structural goal it was declared for:
the §5.1 research shutdown did not fire for any of the three primaries, where in Attempt 1 it fired
for all six.

**It authorizes exactly one thing:** consideration of the next separately governed stage. Under the
constitution and the sealed protocol it does not authorize execution of Stage 4, access to the
validation window, unsealing of the holdout, paper trading, shadow-live operation, live trading, or
any expansion of capital or risk. Each of those needs its own prospective pre-registration and, where
the constitution requires it, explicit recorded human authorization.

**It does not mean any of the following**, and this list is deliberate:

- It is not evidence of an edge. Two specifications out of nine cumulative, on a window six of those
  nine have already seen, is a weak signal by construction.
- It is not a forecast. No expected return, income or profit is claimed for any period.
- It is not a claim to beat the market. Neither admitted candidate beats buy-and-hold SPY on this
  window on either benchmark series.
- It is not robust to doubled costs for C1, whose stressed run trips the research shutdown.
- It is not a selection. C1 and C2 are both admitted and neither is preferred; C2's larger return
  selects nothing.
- It is not trade readiness. StockEdge100 is not trade-ready, and nothing in this report should be
  read as suggesting it is.

The sealed non-authorizations of section 2 remain in force after this pass exactly as they were
before it.

---

## 20. Limitations that survive this stage

1. **C1's drawdown margin is 33 basis points.** `0.1467` against a `0.15` ceiling. A modestly
   different window, a modestly different cost, or a modestly different parameter would put it over.
2. **C1's ceiling compliance is not robust to its own neighbour.** `#N1`, at `sma_long: 150`, reached
   `0.1544` and tripped the research shutdown on `2020-02-27`.
3. **C1 does not survive doubled trading costs.** Return falls to `0.0018`, drawdown rises to
   `0.1530`, and the shutdown fires on `2018-02-05`.
4. **Neither admitted candidate beats buy-and-hold SPY** on this window, on either benchmark series.
5. **The development data are not pristine.** Nine cumulative specifications have now been evaluated
   on this window and their results read.
6. **No new signal form was tested.** All three candidates reuse the signal form of a rejected
   Attempt 1 candidate; only the risk machinery is new.
7. **Multiplicity is disclosed but not corrected numerically.** No family-wise or false-discovery
   adjustment was applied to any threshold.
8. **C3's window is shorter and not comparable.** It begins `2003-05-14` because SHY's inception
   binds it, so its CAGR and Sharpe are not on equal terms with C1's and C2's.
9. **Sharpe uses a 0% risk-free rate**, because no Treasury-bill series exists in the project. The
   bias flatters strategies and penalises cash, and affects SHY-holding C3 most.
10. **Drawdown is measured at session closes.** Every reported drawdown is a lower bound on the true
    intraday figure, so every S3-C2 margin is narrower in reality than in the table.
11. **The loss control is not a bound.** RA1-3 exits on a close, not on a stop order; an overnight gap
    can exceed 8% and the sealed text says so, quoting §5.2.
12. **The volatility floor and the size floor were never exercised.** All three counts are zero on
    this window, so those two branches of RA1-2 have unit-test coverage but no realised evidence.
13. **One position was open at C3's window end**, so C3's closed-trade reconstruction and its
    equity-curve return differ by construction.
14. **The evaluation is single-window and single-cost-model for gating purposes.** Nothing here
    speaks to any period after `2021-07-31`.
15. **`profit_factor` is recorded at two precisions** in the evidence file, as described in
    `A2-EVAL-OBS-1`. Disclosed, not repaired.
16. **Two candidates are admitted, and the constitution requires only one.** Admitting two neither
    strengthens the evidence nor implies a comparison between them.

---

## 21. Tests

Full detail is in `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_EVALUATION_TEST_SUMMARY.md`, with raw
output in `reports/stage3_attempt2/pytest_stage3_attempt2_evaluation_output.txt`.

| Property | Value |
| --- | --- |
| Command | `cd stockedge100 && python -m pytest tests -q` |
| Collection command | `cd stockedge100 && python -m pytest tests -q --collect-only` |
| Passed | 560 |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Collected | 560 |
| Test modules | 15 |
| Excluded for restricted-partition risk | none |

Running totals across stages: 27 → 140 → 273 → 389 → 460 → 560. This session added 100 tests in three
new modules — `tests/unit/test_stage3_attempt2_implementation.py` (51),
`tests/adversarial/test_stage3_attempt2_defects.py` (30) and
`tests/integration/test_stage3_attempt2_backtest.py` (19) — and subtracted none.

**The regression floor is intact by digest, not by assertion.** Against the 95 code hashes recorded
in the design session's run record: 12 test files recorded, 12 unchanged, 0 changed, 0 missing, 15
live (3 added); 49 source files recorded, 0 changed, 0 missing, 58 live (9 added). No frozen test was
weakened, deleted, skipped or marked xfail. The one frozen test that failed against new code —
`tests/adversarial/test_stage3_defects.py`'s lexical guard against naming a seal bypass — was
satisfied by removing the bypass from the new code.

**No test needed exclusion for restricted-partition risk.** The suite contains 25 date literals later
than the development window's end, 24 in `tests/unit/test_stage1_calendar_partition.py` and one at
`tests/adversarial/test_stage1_adversarial.py:316`. Every one is calendar arithmetic or a guard
assertion — they exist to check that the partition boundaries are where the holdout lock says they
are, and several assert that reading past a boundary *raises*. None loads a validation or holdout
observation.

**Coverage of the required test list.** All 28 items the operating prompt enumerates are covered, and
the mapping from item to test is tabulated in the test summary. The traceability map names 90 distinct
tests across 118 sealed paths, `missing_coverage()` is empty, and the map's own `verify()` resolves
every row.

**Determinism.** Verified as described in section 14: all three primaries reproduce byte-identical
trade and equity digests on re-run.

**Restricted-data access.** None. `validation_observations_read: false`,
`holdout_observations_read: false`. No `WindowViolation` and no `LookAheadError` was raised by any
evaluation run, because none was provoked.

---

## 22. Gate 3 assessment

| Constitution §9 gate 3 condition | Rollup verdict | Basis |
| --- | --- | --- |
| S3-C1 total return is positive | `PASS` | Met by C1, C2, C3 |
| S3-C2 maximum drawdown is no worse than 15% | `PASS` | Met by C1, C2, C3; deepest primary `0.1467` |
| S3-C3 profit factor is at least 1.10 | `PASS` | Met by C1, C2, C3 |
| S3-C4 at least 30 closed trades | `PASS` | Met by C1, C2, C3; no exception invoked |
| S3-C5 removing the single best trade leaves total return above 0% | `PASS` | Met by C1, C2, C3, both removals each |
| S3-C6 no single instrument contributes more than 50% of total profit | `PASS` | Satisfied by C1 and C2 by condition text; **not met by C3**; met by none |
| S3-C7 neighbouring parameter values do not reverse the sign of net return | `PASS` | Met by C1, C2, C3; 4 of 4 neighbours each |
| **`admissible_candidate_exists`** | **`PASS`** | **`true`. Conjunctive within candidate, disjunctive across. Admitted: C1, C2. Rejected: C3 on S3-C6. Candidates evaluated: 3. This row alone decides the gate.** |

Each of the first seven rows aggregates satisfaction across candidates and settles nothing on its
own. The eighth row decides the gate.

| Field | Value |
| --- | --- |
| Gate | 3 — development admissibility |
| Verdict | `PASS` |
| Token | `STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT` |
| Condition satisfied | At least one pre-registered candidate satisfies EVERY hard condition of Gate 3. |
| Highest genuinely passed research gate after this stage | **3** |
| `live_trading_authorized` | `false` |

---

## 23. Authorization state after this stage

| Activity | State |
| --- | --- |
| Attempt 2 strategy research on the development window | `COMPLETE_ON_THE_DEVELOPMENT_WINDOW` |
| Further Attempt 2 development work | `LOCKED` — the evaluation is complete and unrepeatable; 0 revisions permitted |
| Validation window (`2021-08-01` → `2024-07-31`) | `LOCKED`, unread |
| Final holdout (`2024-08-01` → `2026-07-31`) | `SEALED`, unread |
| Stage 4 validation | `NOT_AUTHORIZED_REQUIRES_A_SEPARATE_PROSPECTIVE_PREREGISTRATION` |
| Alpaca paper trading | `LOCKED` |
| Shadow-live operation | `LOCKED` |
| Alpaca live trading | `LOCKED` |
| Capital or risk expansion | `LOCKED` |

Every lock above was locked before this session and remains locked after it. A passed Gate 3 changes
the state of exactly one row — the first — and unlocks nothing.

---

## 24. Next authorized action

**One action, and it is a design action rather than an evaluation action:** open a separate session to
write and seal a prospective pre-registration for Stage 4 validation, covering which admitted
candidate or candidates are carried forward, the validation protocol, the gate 4 conditions, and the
rule for a single validation read. That pre-registration must be sealed before any validation
observation is read.

This session does not perform it, does not begin it, and does not decide which of C1 and C2 it should
name. Gate 3 admitted both and ranked neither.

---

## Verdict

**`PASS — STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT`**

Three pre-registered Attempt 2 candidates were implemented from the sealed specification and
evaluated once on the development window `1993-01-29` → `2021-07-31`, in eighteen declared runs of
which fifteen gate. `SE100-S3A2-C1-PULLBACK-RA1` and `SE100-S3A2-C2-MEANREV-RA1` satisfied every
applicable hard condition of constitutional gate 3 and are admitted. `SE100-S3A2-C3-DEFENSIVE-RA1`
satisfied six of seven and failed S3-C6 with a `0.9796` single-instrument profit share — the failure
mode its own sealed record declared, before any result, as the one most likely to reject it.
`admissible_candidate_exists` is `true`, and one admissible candidate is all Gate 3 requires.

The shared risk architecture achieved the structural goal it was declared for: no primary tripped the
§5.1 research shutdown, where in Attempt 1 all six candidates did. One registered neighbour did trip
it, which is the clearest available evidence that the architecture is a size discipline rather than a
device for stopping just short of the ceiling.

This result authorizes consideration of the next separately governed stage and nothing else.
Validation stays `LOCKED` and unread, the holdout stays `SEALED` and unread, Stage 4 stays
unauthorized pending its own prospective pre-registration, and `live_trading_authorized` stays
`false`. Neither admitted candidate beats buy-and-hold SPY over the window on which it was admitted,
C1 does not survive doubled trading costs, and two admissions out of nine cumulative specifications
on data that six of them have already seen is weak evidence by construction. StockEdge100 is not
trade-ready.
