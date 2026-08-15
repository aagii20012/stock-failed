# Stage 3 (Generation 2) — cross-sectional rotation development research report

| Field | Value |
|---|---|
| Document id | `SE100-GOV-2004` |
| Project | StockEdge100 |
| Generation | 2 |
| Generation id | `SE100-GEN2-7394207c543401e2` |
| Stage | 3 |
| Gate | 3 — development admissibility |
| Session type | Development research and evaluation |
| Governing document | `SE100-GOV-0001` (constitution, FROZEN) §§3, 4, 5.1, 6, 7, 9 gate 3, 10, 11, 19 |
| Charter | [STAGE_10_GENERATION_2_CHARTER.md](STAGE_10_GENERATION_2_CHARTER.md) (`SE100-GOV-2001`) |
| Partition lock | [STAGE_1_G2_PARTITION_LOCK.md](STAGE_1_G2_PARTITION_LOCK.md) (`SE100-GOV-2002`) |
| Pre-registration | [STAGE_3_G2_ROTATION_PROTOCOL.md](STAGE_3_G2_ROTATION_PROTOCOL.md) (`SE100-GOV-2003`), sealed |
| Gate criteria | `config/generation_2/g2_gate_criteria.json` (`SE100-CFG-3102`), sealed |
| Evidence | `reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json` (`SE100-EVID-3101`) |
| Development window read | 1993-01-29 → 2021-07-31 (run span 2008-07-28 → 2021-07-30) |
| Validation window | 2021-08-01 → 2024-07-31 — **not read** |
| Generation 1 holdout | 2024-08-01 → 2026-07-31 — **sealed, not read** |
| Generation 2 holdout | 2026-08-01 → 2028-07-31 — **does not exist in calendar time** |
| Authored (UTC) | 2026-08-15T06:57:49Z |
| Verdict | `FAIL — STAGE_3_G2_NO_CANDIDATE` |
| Gate 3 | **NOT PASSED** |
| `live_trading_authorized` | `false` |

This report deliberately carries no `run_id` and no `repo_state_id`. `repo_state_id` is a digest over
a file set, and a report that quoted it would in the general case be a member of the set it was
describing. Generation 2's governance subtree happens not to be covered — `repo_state_id`'s
governance pattern is single-level, `governance/*.md`, so `governance/generation_2/*.md` falls
outside it (recorded as `G2-CONFLICT-4`) — but the convention is kept anyway, because a reader should
not have to reason about pattern depth to know whether a digest in a report is trustworthy. Both
values live in `reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json` and in the appended `runs/`
record, and they are written by the builder, not typed here.

The two 64-hex values this report does quote are the Generation 2 universe identity digest and the
evidence file's own self-digest. Neither is a tree digest and neither is this file's digest; both are
quoted so a reader can check them against disk.

---

## 1. What this session did

It ran Generation 2's first strategy research stage: eighteen pre-registered cross-sectional
rotation variants, two cost scenarios each, 36 backtests, over development data only. It then applied
a selection rule that had been frozen before any variant was run, and evaluated Gate 3 against sealed
criteria.

The rule admitted nothing. Every one of the eighteen variants recorded a research-shutdown event in
**both** of its runs, and the rule's first step requires zero. Steps 2 and 3 were never reached,
Gate 3 was never evaluated on a candidate, and the stage ends:

```
FAIL — STAGE_3_G2_NO_CANDIDATE
```

This was an anticipated outcome. The sealed protocol wrote the no-candidate path down in advance,
including the prohibition on repairing it, and the sealed criteria record `fail_is_a_deliverable`.
The result is kept on disk.

## 2. Position in the sequence, and what Generation 1 has to do with it

Generation 1 is closed. It ended `FAIL — STAGE_4_STRATEGY_REJECTED_IN_VALIDATION`: its admitted
candidate missed the validation Sharpe threshold and the fold-stability condition. Its diagnosis was
that the candidate, though nominally a universe strategy, only ever traded SPY — it had collapsed
onto a single symbol, so what looked like a portfolio result was a single-asset result wearing a
universe's clothes.

Generation 2 changes exactly one thing: the strategy must be genuinely cross-sectional. Same
provider, same USD 100 fractional-share account model, same daily bars, same cost model, same frozen
34-ETF universe. The charter (`SE100-GOV-2001`) records that constraint and the reasoning; this stage
is the first test of it.

No Generation 1 artifact was edited, regenerated, or reinterpreted. Generation 1 files under
`governance/`, `config/` and `reports/` were opened read-only for context. All Generation 2 artifacts
live in the new subtrees `governance/generation_2/` and `config/generation_2/`. §20 below states this
as a checked claim rather than an assurance.

## 3. What was pre-registered, and when

| Field | Value |
|---|---|
| Strategy id | `SE100-G2-S3-C1-ROTATION` |
| Family | `CROSS_SECTIONAL_RELATIVE_STRENGTH` |
| Hypothesis | Relative strength persists over multi-week to multi-month horizons |
| Ranking signal | N-month total return (price + dividends), from data available as of the decision date |
| Lookback axis | 3, 6, 12 months |
| Position count axis | top-k, k ∈ {1, 2, 3} |
| Rebalance axis | monthly, quarterly — fixed calendar rule, never signal-triggered |
| Entry | next session's **open**, never the close that produced the ranking |
| Exit | a name that drops out of top-k at a scheduled rebalance; no discretionary exits |
| Sizing | equal weight at entry, subject to 95% maximum gross exposure |
| Concentration ceiling | 50% of equity in any one position at any rebalance |
| Grid | 3 × 3 × 2 = **18 variants**, declared in full before any was run |
| Runs per variant | 2 — `#BASE` and `#STRESS` — both declared, neither conditional on the other |
| Total runs | **36** |

All of that was sealed in `STAGE_3_G2_ROTATION_PROTOCOL.md` / `.json`, hashed by
`STAGE_3_G2_ROTATION_PROTOCOL.sha256`, **before any Generation 2 strategy module existed**. §12 of
that document records the measurement that makes the claim falsifiable rather than self-reported: it
counted the strategy modules and strategy output files present at seal time, so the claim can be
contradicted by the record rather than only by trust.

The grid was not revised after any result was seen. The evidence file records
`revisions_after_seeing_a_result: 0`, `all_declared_runs_executed: true`, and
`runs_executed: 36`.

## 4. The window actually read, and how that was enforced

| Field | Value |
|---|---|
| Development partition | 1993-01-29 → 2021-07-31 |
| Development bound | 2021-07-31 |
| Latest session loaded anywhere | **2021-07-30** |
| Run span (common to all 18 variants) | 2008-07-28 → 2021-07-30, 3276 sessions |
| Development union across the universe | 1993-01-29 → 2021-07-30, 7178 sessions |
| Validation read | `false` |
| Generation 1 holdout read | `false` |
| Generation 2 holdout read | `false` |

The operating instruction required this to be *verified programmatically*, not held by convention.
It is enforced twice, by two mechanisms that would both have to fail together:

1. `load_grid_dataset` truncates at the development bound while loading. A post-bound bar is never
   materialised in the first place.
2. The loaded bars are then audited independently of the loader — reading the bar map, not the
   session index — and any bar dated after the bound is a refusal, not a warning.

`tests/unit/test_g2_window_guard.py` (48 tests) attacks both, including the cases where a single
post-bound bar hides among many clean symbols, where the session index and the bar map disagree in
either direction, and where a tampered partition lock is used to try to move the bound. It also
asserts that the two prohibited holdout periods are **adjacent with no gap**, so no window can slip
between 2026-07-31 and 2026-08-01.

**The run span is later than the partition start, and that is a deliberate cost.** It begins at
2008-07-28, the first session for which the *longest* lookback in the grid — 12 months — has a
reference bar for every universe member; the binding member is VEA, inception 2007-07-26. All
eighteen variants share that start, including the 3- and 6-month variants that could individually
have begun earlier. Letting each lookback start as early as it could would have made a cross-lookback
comparison partly a comparison of which market history each variant happened to see. The cost —
history the shorter lookbacks could have used — is paid deliberately, and §17 records what it means
for this verdict.

## 5. Universe and the eligibility re-check

| Field | Value |
|---|---|
| Universe version | `SE100-U1-d4917c2f7f1cd834` |
| Universe identity digest | `d4917c2f7f1cd8344728a39165929b352766fbe7193b3c64e71a971749dcbf38` |
| Members declared | 34 |
| Members loaded | 34 |
| Missing | none |
| Re-check window | development only, 1993-01-29 → 2021-07-31 |
| Outcome | all 34 pass; no symbol added, removed, or substituted |

The re-check was performed in the charter, §3, on development data only, and it is a liquidity and
structural question answered without reference to returns. No symbol may be added or dropped on the
basis of any performance figure, in this stage or any later one.

Every one of the 34 members has bars through 2021-07-30, so the sealed
`LIQUIDATE_AT_LAST_AVAILABLE_CLOSE` delisting path is not exercised by any run in this stage. That is
stated as a measured fact, not an assumption.

`AAPL` is present in `data/normalized/daily` as a Stage 2 engine fixture. It is not a member of the
frozen universe and was not ranked, held, or read by any Generation 2 run.

## 6. Engine capability added, and why it needed its own adversarial tests

Generation 1's engine held at most one risky position. A cross-sectional top-k strategy cannot exist
inside that constraint, so the engine had to change. The instruction was explicit that this is new
engine capability requiring its own adversarial tests before it is trusted for strategy research, and
not "just a strategy change".

The frozen `backtest/engine.py` was **not modified**. The capability is a new module,
`backtest/g2_engine.py`, which holds up to k positions and enforces:

- at most **k** open positions;
- **95%** maximum gross exposure across the combined book;
- **50%** maximum single-position concentration at any rebalance.

`tests/adversarial/test_g2_engine_multiposition.py` (59 tests) covers each of the six failure modes
the instruction named, each with its own control:

| Must fail if the engine… | Established by |
|---|---|
| exceeds k positions | the book never exceeds k, **and actually reaches k** so the bound is not vacuous; a greedy probe is refused; the portfolio refuses the surplus even with the engine-level check removed |
| exceeds 95% gross exposure | the whole book stays inside the sealed cap; an oversized request at k=3 is clamped by the aggregate ceiling; a holding left out of the marks is a halt, not a smaller sum |
| exceeds the 50% concentration ceiling | an oversized request at k=1 is clamped by it; the ceiling is read from the seal, not from the caller |
| trades at the close that generated the ranking | every fill is strictly after its decision session; no fill was priced at any close in the dataset; such an order **cannot be constructed** |
| uses tomorrow's bar in today's ranking | the ranking is unchanged when the future is deleted *and* when it is replaced by a different future; a visible bar does change it; the visibility bound is immutable after construction |
| is non-deterministic on a clean rerun | clean rerun, fresh-dataset rerun, and symbol-insertion-order invariance, with two negative controls |

The concentration ceiling has a consequence worth stating plainly: at **k=1** the 50% ceiling is
strictly more restrictive than the 95% gross cap, so a k=1 variant holds half its equity in cash by
construction. That is disclosed as `G2-CONFLICT-9`, not corrected — correcting it would mean
loosening a sealed ceiling to make a parameterisation look better.

## 7. Cost model

Unchanged from Generation 1 and out of scope for revision: 5 bps per side base, 10 bps per side
stressed (the sealed `stress_multiplier` of 2.0 applied to the complete friction assumption including
the TAF cap), same regulatory fees, applied exactly as Generation 1 applied them.

A multi-position strategy nevertheless needs a cost model that admits more than one position, so one
thing had to change. `tests/unit/test_g2_cost_derivation.py` (50 tests) pins exactly what: the
Generation 2 model differs from the sealed Generation 1 mapping at **exactly one declared pointer** —
position breadth — and nowhere else. The check flattens both mappings to RFC 6901 pointers and diffs
every leaf; `k` equal to the sealed value produces no difference at all, which is the control that
makes the diff meaningful; and a second difference injected anywhere is refused.

## 8. The grid as executed

All 36 declared runs executed. None was conditional on another's outcome. No variant was added,
removed, or re-parameterised after a result was seen.

| Field | Value |
|---|---|
| Variants declared | 18 |
| Runs per variant | 2 (`#BASE`, `#STRESS`) |
| Runs declared | 36 |
| Runs executed | **36** |
| All declared runs executed | `true` |
| Revisions after seeing a result | **0** |

## 9. The representative-selection rule, and how it was applied

The rule was frozen in `SE100-CFG-3101` before any variant ran:

1. **Zero research-shutdown events**, across **both** declared runs. (The instruction names the
   shutdown screen without saying whether it spans both runs. Requiring it across both is the more
   restrictive reading and is return-blind either way, so it was adopted: a variant that survives
   base costs but trips the trip-wire under doubled costs is not one this stage carries forward.)
2. **Lowest turnover** among the eligible, measured as total executed fills across both runs.
3. **Lexicographic variant id**, if step 2 ties.

And the sealed no-candidate path: if no variant is eligible at step 1, no variant advances, the
verdict is `FAIL — STAGE_3_G2_NO_CANDIDATE`, and the grid is not loosened, the threshold is not
raised, the screen is not narrowed to the base run, and the rule is not revised post hoc.

**Return-blindness is structural, not a promise.** `select_representative` receives only
`SelectionInput` records, whose fields are exactly:

```
['variant_id', 'shutdown_events', 'fill_count', 'per_run']
```

No `BacktestResult`, no measurement, no equity curve, and no trade P&L is in scope at the point the
representative is decided. The record is frozen, so a figure cannot be attached afterwards. Nothing
in that projection is a performance figure, and the chooser therefore *cannot* read one.

`tests/adversarial/test_g2_selection_return_blind.py` (97 tests) establishes this by permutation
rather than by assertion: permuting every return leaves the selection and the recorded projection
byte-identical, while two controls confirm the permutations really do move the returns and that a
return-aware ordering *would* have moved under exactly those permutations. Without the second
control, "the selection did not move" would be equally consistent with permutations that changed
nothing.

Turnover as fill count is a deliberate choice, recorded as `G2-CONFLICT-13`. Gross traded notional
was considered and rejected: a variant whose equity grows trades larger notionals for the same
activity, which would make the tiebreak a partial return proxy and break the return-blind property.

## 10. Result of step 1: nothing was eligible

| Field | Value |
|---|---|
| Variants considered | 18 |
| Eligible after step 1 | **0** |
| Ineligible | 18 |
| Representative exists | `false` |
| Decided at step | — (no step decided; the no-candidate path applied) |
| Decided by | `no_candidate_path` |
| Steps 2 and 3 | never reached |

Every variant recorded `research_shutdown_events: 2` — one in its base run and one in its stress
run. The screen requires zero. The sealed selection note, verbatim from the evidence file:

> All 18 declared variants recorded at least one research-shutdown event across their two declared runs, so no variant is eligible under step 1. The sealed no_candidate_path applies: the grid is not loosened, the shutdown threshold is not raised, the screen is not narrowed to the base run, and the rule is not revised post hoc.

Two of those four prohibitions would have produced a candidate. Narrowing the screen to the base run
would have admitted nothing either, since every base run also fired. Raising the threshold above 15%
would have. Both are forbidden, and the point of freezing the rule beforehand is that the
prohibition binds precisely when relaxing it would help.

## 11. Why every variant tripped the trip-wire

A 100% shutdown rate is the kind of number that is usually a bug. It was checked four ways before
being believed, and the checks are recorded because a reader should not have to take the rate on
faith.

**The trip-wire.** Constitution §5.1: 15% below the running high-water mark, action
`LIQUIDATE_AT_NEXT_OPEN_AND_BLOCK_ENTRIES`. It fires at most once per run, so a per-variant count
across two runs is 0, 1, or 2. Every variant scored 2.

**They did not all fire on one session.** The 36 runs fired on **18 distinct sessions**, spread from
2008-10-24 to 2020-03-12:

```
2008-10-24  2008-10-27  2008-11-19  2009-03-09  2009-05-26  2009-05-27
2010-02-04  2010-06-07  2010-07-02  2010-08-11  2010-08-12  2010-12-10
2010-12-14  2011-08-04  2011-10-04  2016-01-15  2016-01-20  2020-03-12
```

**Each base/stress pair fired on the same or an adjacent session.** Doubling frictions moves the
firing date by zero or one session, never wildly — the signature of a real equity path responding to
a small perturbation, not of a constant or a broken counter.

**Buy-and-hold on the same span is the control.** SPY first breaches the same 15% threshold on
**2008-10-03**, with a worst drawdown of **0.4789**; IVV on **2008-10-03**, worst **0.4790**. Both
are *before any variant fired*. AGG and SHY never breach it at all. The sealed run span opens
2008-07-28 — ten weeks before the worst equity drawdown in modern market history — so a long-only
rotation restricted to a 34-ETF universe tripping a 15% trip-wire in that window is a property of the
window, not a defect in the strategy or the engine.

**The shutdown's effect was verified from the fill stream, not from the engine's own counters.** Four
probe variants were chosen to span the earliest firing, the latest, the highest turnover and the
lowest. In all four: every shutdown liquidates the whole book at the next open with `SHUTDOWN`-tagged
sells, and no `BUY` fill occurs at or after the shutdown session. Four probes, zero failures. Reading
the counters would have been circular; reading the fills is not.

The honest summary is that a 15% research trip-wire and a run span opening in July 2008 are close to
incompatible for any long-only equity rotation. That is a finding about the interaction of two
frozen choices, and it is the finding this stage has. It is not a licence to change either one.

## 12. Cross-sectionality: the one thing Generation 2 set out to change

| Measure | Generation 1's validated candidate | Generation 2, this grid |
|---|---|---|
| Distinct symbols ever targeted | 1 (SPY only) | up to **21** |

Generation 2's strategy did not collapse onto a single symbol. The variants targeted as many as 21
distinct symbols across the run span, and the per-variant counts in §15 range from 2 to 21. Whatever
else this FAIL is, it is not a repeat of Generation 1's degeneracy. The change the charter set out to
make was made; it did not survive the shutdown screen.

## 13. Determinism

Not sampled — repeated in full. After the grid completed, the dataset was reloaded from disk and all
36 runs were re-executed on fresh strategy objects, then compared on six fields each: trade digest,
equity digest, ranking digest, fill count, final equity, and shutdown session.

| Field | Value |
|---|---|
| Runs compared | **36 of 36** |
| All identical | `true` |
| Mismatched runs | none |

## 14. Gate 3: not reached, and why that is not a pass

The sealed criteria define seven hard conditions, `S3-C1` … `S3-C7`. Gate 3 is evaluated **only** on
the representative produced by the frozen selection rule, on its `#BASE` run, with the stress run
reported and not gating — identical to Generation 1's Stage 3 treatment.

No representative was produced. All seven conditions are therefore recorded as **`NOT_RUN`**:

| Condition | Verdict |
|---|---|
| `S3-C1` … `S3-C7` | `NOT_RUN` — not evaluated; Gate 3 is evaluated only on a representative and none exists |
| **`admissible_candidate_exists`** | **`NOT_MET`** |

`NOT_RUN` is not `NOT_APPLICABLE`, and it is certainly not a pass. The distinction matters here: the
conditions were not inapplicable, they were never *reached*, because the return-blind screen that
runs before them admitted nothing. Constitution §9 is explicit that `NOT_RUN`, `UNKNOWN`,
`NOT_EVALUABLE`, and missing evidence are never a pass.

**The decisive row is `admissible_candidate_exists`, and only that row.** 0 of 18 declared variants
survived step 1 of the frozen selection rule, so no candidate reached Gate 3 and none can satisfy it.
The seven rows above settle nothing on their own: gates are conjunctive *within* a candidate and the
stage verdict is a disjunction *across* candidates — and here the candidate set is empty. A
conditions table that omitted this row would read as though the gate were irrelevant rather than
decided, which is why it is present and carries the determination.

Generation 2 declares one candidate family, so that disjunction is over a set of size one. Recorded
as `G2-CONFLICT-15`.

## 15. Grid results — descriptive record only

**These figures were not an input to any decision in this report.** They are published because the
instruction requires the full grid on the record, and because publishing only the variants that
survived a screen is how a research record becomes a sales document. Nothing below was read by the
selection rule, and nothing below can justify a different selection than the frozen rule produced.
Note in particular that the strongest variant by return (`L06-K2-MONTHLY`, +28.69%) failed the screen
on exactly the same terms as the weakest (`L03-K1-QUARTERLY`, −16.36%).

Variant ids are abbreviated; each is prefixed `SE100-G2-S3-C1-ROTATION-`.

### `#BASE` runs

| # | Variant | Return | Max DD | Profit factor | Closed trades | Distinct symbols | Shutdowns | Shutdown session |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `L03-K1-MONTHLY` | +0.2534 | 0.1505 | 1.3260 | 64 | 21 | 2 | 2016-01-20 |
| 2 | `L03-K1-QUARTERLY` | −0.1636 | 0.1708 | 0.0000 | 2 | 2 | 2 | 2008-11-19 |
| 3 | `L03-K2-MONTHLY` | −0.0526 | 0.1590 | 0.5602 | 9 | 7 | 2 | 2009-03-09 |
| 4 | `L03-K2-QUARTERLY` | +0.1872 | 0.1604 | 1.6094 | 14 | 12 | 2 | 2010-06-07 |
| 5 | `L03-K3-MONTHLY` | −0.1450 | 0.1619 | 0.1461 | 8 | 7 | 2 | 2008-10-24 |
| 6 | `L03-K3-QUARTERLY` | −0.1125 | 0.1538 | 0.1947 | 5 | 5 | 2 | 2008-10-27 |
| 7 | `L06-K1-MONTHLY` | +0.2193 | 0.1759 | 1.2534 | 76 | 19 | 2 | 2020-03-12 |
| 8 | `L06-K1-QUARTERLY` | +0.0102 | 0.1618 | 1.0493 | 8 | 6 | 2 | 2011-08-04 |
| 9 | `L06-K2-MONTHLY` | **+0.2869** | 0.1686 | 2.6797 | 20 | 11 | 2 | 2010-08-11 |
| 10 | `L06-K2-QUARTERLY` | −0.1153 | 0.1581 | 0.0595 | 5 | 5 | 2 | 2009-05-27 |
| 11 | `L06-K3-MONTHLY` | +0.2263 | 0.1551 | 1.9925 | 33 | 20 | 2 | 2010-08-12 |
| 12 | `L06-K3-QUARTERLY` | +0.2403 | 0.1552 | 2.7043 | 19 | 16 | 2 | 2010-12-14 |
| 13 | `L12-K1-MONTHLY` | +0.0044 | 0.1653 | 1.0174 | 10 | 7 | 2 | 2011-10-04 |
| 14 | `L12-K1-QUARTERLY` | −0.0465 | 0.1551 | 0.3395 | 5 | 5 | 2 | 2010-02-04 |
| 15 | `L12-K2-MONTHLY` | −0.0465 | 0.1604 | 0.4180 | 6 | 4 | 2 | 2009-05-27 |
| 16 | `L12-K2-QUARTERLY` | +0.0153 | 0.1519 | 1.8500 | 3 | 3 | 2 | 2009-05-26 |
| 17 | `L12-K3-MONTHLY` | +0.1029 | 0.1572 | 2.1575 | 21 | 16 | 2 | 2010-07-02 |
| 18 | `L12-K3-QUARTERLY` | −0.0302 | 0.1508 | 0.8176 | 15 | 14 | 2 | 2010-07-02 |

### `#STRESS` runs (2× frictions)

| # | Variant | Return | Max DD | Profit factor | Closed trades | Fills | Shutdown session |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `L03-K1-MONTHLY` | +0.2219 | 0.1513 | 1.2876 | 64 | 128 | 2016-01-15 |
| 2 | `L03-K1-QUARTERLY` | −0.1645 | 0.1714 | 0.0000 | 2 | 4 | 2008-11-19 |
| 3 | `L03-K2-MONTHLY` | −0.0565 | 0.1598 | 0.5331 | 9 | 18 | 2009-03-09 |
| 4 | `L03-K2-QUARTERLY` | +0.1795 | 0.1604 | 1.5802 | 14 | 28 | 2010-06-07 |
| 5 | `L03-K3-MONTHLY` | −0.1469 | 0.1626 | 0.1374 | 8 | 16 | 2008-10-24 |
| 6 | `L03-K3-QUARTERLY` | −0.1140 | 0.1544 | 0.1892 | 5 | 10 | 2008-10-27 |
| 7 | `L06-K1-MONTHLY` | +0.1733 | 0.1825 | 1.1991 | 76 | 152 | 2020-03-12 |
| 8 | `L06-K1-QUARTERLY` | +0.0063 | 0.1635 | 1.0302 | 8 | 16 | 2011-08-04 |
| 9 | `L06-K2-MONTHLY` | +0.2751 | 0.1706 | 2.5847 | 20 | 40 | 2010-08-11 |
| 10 | `L06-K2-QUARTERLY` | −0.1172 | 0.1585 | 0.0548 | 5 | 10 | 2009-05-27 |
| 11 | `L06-K3-MONTHLY` | +0.2146 | 0.1569 | 1.9310 | 33 | 66 | 2010-08-12 |
| 12 | `L06-K3-QUARTERLY` | +0.2384 | 0.1528 | 2.7351 | 19 | 38 | 2010-12-10 |
| 13 | `L12-K1-MONTHLY` | −0.0007 | 0.1659 | 0.9973 | 10 | 20 | 2011-10-04 |
| 14 | `L12-K1-QUARTERLY` | −0.0490 | 0.1565 | 0.3128 | 5 | 10 | 2010-02-04 |
| 15 | `L12-K2-MONTHLY` | −0.0489 | 0.1603 | 0.3956 | 6 | 12 | 2009-05-27 |
| 16 | `L12-K2-QUARTERLY` | +0.0140 | 0.1522 | 1.7447 | 3 | 6 | 2009-05-26 |
| 17 | `L12-K3-MONTHLY` | +0.0957 | 0.1575 | 2.0563 | 21 | 42 | 2010-07-02 |
| 18 | `L12-K3-QUARTERLY` | −0.0345 | 0.1509 | 0.7938 | 15 | 30 | 2010-07-02 |

Returns and drawdowns are rounded here for legibility. The evidence file carries them at full
`Decimal` precision, and the decision record reproduces the table verbatim from it.

## 16. Turnover, for the record

Turnover is the one figure the selection rule *would* have used, had step 1 admitted anything. It is
published so the counterfactual is inspectable — and it is worth seeing, because it shows the
tiebreak would not have picked the strongest variant either. Fills summed across both declared runs:

| Variant | Fills (both runs) |
|---|---:|
| `L03-K1-QUARTERLY` | 8 |
| `L12-K2-QUARTERLY` | 12 |
| `L03-K3-QUARTERLY` | 20 |
| `L06-K2-QUARTERLY` | 20 |
| `L12-K1-QUARTERLY` | 20 |
| `L12-K2-MONTHLY` | 24 |
| `L03-K3-MONTHLY` | 32 |
| `L06-K1-QUARTERLY` | 32 |
| `L03-K2-MONTHLY` | 36 |
| `L12-K1-MONTHLY` | 40 |
| `L03-K2-QUARTERLY` | 56 |
| `L12-K3-QUARTERLY` | 60 |
| `L06-K3-QUARTERLY` | 76 |
| `L06-K2-MONTHLY` | 80 |
| `L12-K3-MONTHLY` | 84 |
| `L06-K3-MONTHLY` | 132 |
| `L03-K1-MONTHLY` | 256 |
| `L06-K1-MONTHLY` | 304 |

Step 2 was never reached. This table decided nothing.

## 17. Disclosed limitations

**17.1 — Validation-window reuse.** The following text is sealed as
`validation_reuse_disclosure` in the partition lock JSON (`SE100-GOV-2002`) and is reproduced here
verbatim, as it must be in every report that references validation. It was substituted from the
sealed file mechanically rather than retyped, and as a single unbroken line, so that byte-identity
with the seal is checkable by string comparison rather than asserted:

> Generation 2's validation window (2021-08-01 → 2024-07-31) overlaps the exact period Generation 1 used for its own Gate 4 validation read. The researcher therefore already knows, from Generation 1's published report, approximately how SPY (and by extension the broad market) behaved in this window — including its Sharpe ratio (≈0.20), total return (≈2.15%), and fold-by-fold sign pattern (7 of 12 positive). Generation 2 tests a different hypothesis (cross-sectional multi-asset selection vs. single-symbol mean reversion) over the same calendar period, which limits but does not eliminate the concern. This is a real multiplicity cost, disclosed and not minimized, and it is the reason Generation 2's validation result alone — without a clean holdout confirmation — cannot be treated as sufficient evidence of an edge.

**17.2 — Multiple comparisons.** Sealed as `multiple_comparisons_disclosure` in the rotation protocol
config (`SE100-CFG-3101`, `config/generation_2/g2_rotation_protocol.json`), substituted the same way:

> Eighteen variants over one development window is eighteen looks at the same data. The grid is small, pre-registered in full, and spans axes chosen for being the obvious ones rather than for producing a good number, but none of that makes the multiplicity zero. Two mechanisms bound it. First, the representative that advances is chosen by a rule that never reads a return, so no amount of looking at returns can change which variant is carried forward. Second, the gate is evaluated on that single representative and is NOT a disjunction across eighteen candidates — taking the best of eighteen and gating on it would be precisely the abuse the frozen selection rule exists to prevent. The other seventeen are reported in full as a descriptive record. This disclosure is in addition to, and does not replace, the validation-window reuse disclosure in the partition lock.

**17.3 — This is a development result.** Nothing here is evidence about the validation window, the
Generation 1 holdout, or the Generation 2 holdout. A development result has never been evidence of an
edge in this project, and a development *failure* is correspondingly not evidence that the hypothesis
is false out of sample — it is evidence that this grid, on this span, under this trip-wire, produced
nothing admissible.

**17.4 — The verdict is bounded by the run span.** 2008-07-28 → 2021-07-30, which begins at the first
session where the 12-month lookback has a reference bar for every universe member. All eighteen
variants share that start (§4). A grid run on a later start that excluded 2008 would very likely have
produced a different shutdown count, and this stage cannot say what it would have been. It did not
run one, and running one now to find out would be exactly the post-hoc loosening the frozen rule
forbids.

**17.5 — The screen is the whole of the selection here.** Because step 1 eliminated everything, the
turnover tiebreak was never exercised on real data. This stage provides no evidence that steps 2 and
3 behave correctly beyond the unit tests that cover them — which do cover them, in both directions,
but on synthetic inputs.

**17.6 — The reported figures gate nothing.** Profit factor, drawdown and return were computed for
all 36 runs and are reported in full, but no Gate 3 hard condition was evaluated, because Gate 3 is
evaluated only on a representative and none exists. §15 is descriptive.

**17.7 — One candidate family.** Generation 2 declares a single candidate, so the constitution's
cross-candidate disjunction is over a set of size one (`G2-CONFLICT-15`). A disjunction over one
element carries none of the robustness that a disjunction over several would.

## 18. Conflicts found and how each was resolved

Every one was resolved in the sealed artifacts *before* any variant ran, and each is recorded in the
decision record.

| Id | Conflict | Resolution |
|---|---|---|
| `G2-CONFLICT-4` | `repo_state_id`'s governance pattern is single-level, so `governance/generation_2/*` is **not** covered by it, while `config/**/*.json` is recursive and `config/generation_2/*.json` **is**. | Disclosed, not fixed. The Generation 2 governance artifacts are covered by their own `.sha256` records and by this package's checksum record. Changing the pattern set would make `repo_state_id` values incomparable across stages, which is worse. |
| `G2-CONFLICT-6` | The constitution's best-trade-removed condition does not state the basis for the removal in a multi-position strategy. | Sealed as the single closed trade with the largest positive net contribution across the whole run. |
| `G2-CONFLICT-7` | The neighbour-robustness condition does not define neighbours for a three-axis grid. | Sealed as variants differing on exactly one axis by one step. |
| `G2-CONFLICT-8` | "Monthly" and "quarterly" do not define the rebalance session. | Sealed as the first session whose month boundary has been crossed, not the calendar month end. |
| `G2-CONFLICT-9` | At k=1 the 95% gross ceiling and the 50% concentration ceiling conflict. | The concentration ceiling is more restrictive and binds; a k=1 variant holds half its equity in cash by construction. Disclosed, not corrected. |
| `G2-CONFLICT-10` | "Equal-weight across k held positions" — sizing rule or continuously maintained? | Applied at entry, not maintained by drift between rebalances; maintaining it continuously would require the unscheduled trades the instruction forbids. |
| `G2-CONFLICT-11` | The instruction defines one FAIL path (no variant has zero shutdowns); the constitution implies a second (a representative exists and misses a hard condition). | Both sealed. The route actually taken — `NO_REPRESENTATIVE_EXISTS` — is recorded. |
| `G2-CONFLICT-12` | The instruction's fail token names the *absence* of a candidate; the constitution's names the *rejection* of one. | Both recorded; the sealed token `STAGE_3_G2_NO_CANDIDATE` is emitted, with `STRATEGY_REJECTED_IN_DEVELOPMENT` recorded as the constitutional equivalent. |
| `G2-CONFLICT-13` | The turnover tiebreak does not define turnover. | Sealed as fill count across both declared runs — a return-blind proxy. Gross notional was rejected as a partial return proxy. |
| `G2-CONFLICT-14` | The multi-position engine must mark open positions and sequence sells before buys within a rebalance; neither is specified. | Both sealed and adversarially tested. |
| `G2-CONFLICT-15` | Generation 2 declares one candidate, so the cross-candidate disjunction is over a set of size one. | Disclosed. |
| `G2-CONFLICT-16` | The frozen `Order` contract carries a budget measured at the decision close, but rotation buys execute at the next open. | The budget is re-measured at the open and the re-evaluation count recorded, rather than editing the frozen contract. |

## 19. What was not done, and is not authorized

- **Stage 4 validation was not run.** The validation-window data exists on disk and is technically
  reachable. It was not read. This package does not authorize it. Authorization requires an explicit
  human go-ahead in a separate session.
- **Generation 1's sealed holdout (2024-08-01 → 2026-07-31) was not read**, by this stage or by any
  code it ran.
- **Generation 2's holdout (2026-08-01 → 2028-07-31) does not exist in calendar time** and was not
  read. It may not be read before that period exists, under any circumstance, in this or any future
  session.
- **No broker connection was made, no credential was read or written, and no order was placed.**
  `live_trading_authorized` remains `false`; `paper_trading_authorized` remains `false`.
- **No Generation 1 artifact was modified.** See §20.

## 20. Generation 1 artifacts: a checked claim

No file under `governance/`, `config/`, or `reports/` belonging to Generation 1 was edited, deleted,
regenerated, or reinterpreted. Generation 2's artifacts are additions in new subtrees:

- `governance/generation_2/` — charter, partition lock, rotation protocol, this report, and the two
  `.sha256` records;
- `config/generation_2/` — cost model, rotation protocol, gate criteria;
- `reports/stage3_g2/` — evidence, decision record, checksum record, manifest, test summary, pytest
  capture;
- `src/stockedge100/{backtest,strategies,reporting}/g2_*.py` — new modules; no frozen module edited.

The claim is checkable rather than asserted. The Stage 0 freeze is re-verified by the builder on
every run and recorded in the decision record. Every Generation 1 artifact this stage stood on is
listed in the package's `frozen_inputs_read_only` with its digest and the disposition
`READ_ONLY_NOT_MODIFIED`, and the artifact manifest carries digests for the whole tracked tree, so a
reader can diff against any earlier stage's manifest.

The one exception worth naming: `src/stockedge100/reporting/stage_package.py`, the shared builder,
gained a `generation` field defaulting to `1`. Every Generation 1 record it wrote carries `1` and
stays byte-identical; a Generation 2 stage passes `2` rather than letting its package claim
Generation 1's lineage. That is an addition to a shared module, not an edit to a frozen artifact.

## 21. Tests

**1090 passed, 1 failed, 0 skipped.** Full breakdown:
[STAGE_3_G2_TEST_SUMMARY.md](../../reports/stage3_g2/STAGE_3_G2_TEST_SUMMARY.md).

The single failure is Generation 1's permanent red marker,
`test_no_stage_4_module_can_reach_restricted_data_or_a_broker`, recorded as `S4-CONFLICT-7`. It is
inherited untouched. It was not weakened, skipped, `xfail`ed, deleted, or excluded to make this
stage's suite look clean, and it has nothing to do with the Generation 2 verdict.

Generation 1 left the floor at 837 tests. Generation 2 adds **254** — 48 window-guard, 50 cost
derivation, 59 multi-position engine, 97 selection return-blindness — and removes nothing.

## 22. Artifacts produced

| Path | What it is |
|---|---|
| `governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md` | this document |
| `reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json` | the evidence file (`SE100-EVID-3101`) |
| `reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json` | the machine-readable decision record |
| `reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.sha256` | checksum record over frozen inputs and produced artifacts |
| `reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json` | artifact manifest (excludes its own entry) |
| `reports/stage3_g2/STAGE_3_G2_TEST_SUMMARY.md` | test summary |
| `reports/stage3_g2/pytest_stage3_g2_output.txt` | raw pytest capture |
| `runs/SE100-R-*.json` | append-only reproducibility record |

The evidence file carries a self-digest,
`0cff85e45ff24b0d6e44d729cfcdfda33e348e97c72f84bae7c25d0f4cfe9acf`, covering every field of that file
except `generated_utc` and `evidence_digest`, as canonical JSON. It was recomputed from the written
file by an independent script that follows the coverage sentence literally rather than re-running the
writer's own function — the only check that catches a file whose stated coverage and actual coverage
disagree, which is a defect two-run stability cannot see.

## 23. Reproduction

```bash
cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_stage3_evidence
cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_stage3_package
```

Verify the Generation 2 seals from the project root:

```bash
cd stockedge100 && sha256sum -c governance/generation_2/STAGE_1_G2_PARTITION_LOCK.sha256
cd stockedge100 && sha256sum -c governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.sha256
```

Both Generation 2 records list **project-root-relative** paths, as Generation 1's pre-registration
record does. Only the Stage 0 and Stage 1 *freeze* records use bare filenames and must be verified
from `governance/`. A mismatch reported from the wrong working directory is an operator error, not an
integrity failure.

## 24. Next authorized action

**Human review of this package.** Nothing else.

No candidate is admitted to validation, so Stage 4 has nothing to validate and is not authorized.
Any subsequent Generation 2 work restarts at Gate 3 with a **new pre-registration**. It may not reuse
this grid, loosen this rule, raise the shutdown threshold, narrow the screen to the base run, or
promote a runner-up. A nineteenth variant appended to this grid would be a different thing than a
pre-registration, and would be treated as such.

---

## Verdict

```
FAIL — STAGE_3_G2_NO_CANDIDATE
```

Gate 3 (development admissibility): **NOT PASSED**.

Every one of the eighteen declared variants recorded a research-shutdown event in both of its
declared runs, so step 1 of the frozen return-blind selection rule admitted nothing, no
representative was produced, and Gate 3 was never reached. `admissible_candidate_exists` is
`NOT_MET`: 0 of 18 variants survived the screen, 0 candidates were evaluated, 0 were admitted.

The verdict is a statement about the grid, not about any variant's return. No return figure was an
input to it — the selection rule physically cannot read one — and the strongest variant by return
failed the screen on exactly the same terms as the weakest.

This is a deliverable, anticipated in writing before any variant ran, and it is kept on disk. It does
not license a nineteenth variant, a re-run with a loosened grid, a raised shutdown threshold, a screen
narrowed to the base run, or the promotion of a runner-up.

`live_trading_authorized`: `false`.
