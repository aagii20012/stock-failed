# Stage 4 - Validation Evaluation Pre-registration

- Document id: `SE100-GOV-0008`
- Project: StockEdge100
- Constitutional gate: 4, `validation_robustness`
- Status: sealed by `governance/STAGE_4_PREREGISTRATION.json`
- Declaration timestamp: in that record, emitted by the sealing program. Not hand-typed here.

## 1. Why this document exists

Gate 3 Attempt 2 admitted two candidates and ranked neither. The validation window may be read
once. Those two facts together mean that a validation evaluation cannot begin until two things are
fixed in advance and on the record: **which** single strategy is evaluated, and **how** the result
will be judged. If either is decided after the window is read, the result is a selection on
out-of-sample data wearing the clothes of a test.

This document and the three machine-readable files it seals fix both, before any validation
observation has been read. Nothing in this session read one. No validation row was loaded, no
validation price was read, no validation-period indicator was computed, no validation-period trade
was counted, and the final holdout was not touched. The evaluation itself is a separate,
separately authorized session that does not yet exist.

This is a pre-registration, not a result. It contains no validation performance figure, because
none may be generated at this stage and none exists.

## 2. Pre-registered files

Four files are sealed together. Their digests are recorded in
`governance/STAGE_4_PREREGISTRATION.json` and in the checksum record
`governance/STAGE_4_PREREGISTRATION.sha256`, which uses project-root-relative paths and therefore
verifies from `stockedge100/`:

```bash
cd stockedge100 && sha256sum -c governance/STAGE_4_PREREGISTRATION.sha256
```

| Artifact id | Path | What it fixes |
| --- | --- | --- |
| `SE100-CFG-4001` | `config/stage4_validation_protocol.json` | the procedure: what is read, how often, in how many runs, under what defect and failure rules |
| `SE100-CFG-4002` | `config/stage4_gate_criteria.json` | the criteria: the seven Gate 4 conditions, their measurement, the fold construction, the verdict tokens |
| `SE100-CFG-4003` | `config/stage4_representative_selection.json` | the selection: the rule, its provenance, and its full application to both admitted candidates |
| `SE100-GOV-0008` | `governance/STAGE_4_PREREGISTRATION.md` | this document |

The four are sealed **simultaneously**, so none of them carries the digest of another: a file
cannot contain the digest of a file that contains its own. They reference each other by artifact id
and path, and the enclosing checksum record carries every digest. Files sealed **earlier** are
bound by digest, and section 3 lists them.

This document carries no `repo_state_id` and no digest of itself. It lives in `governance/`, which
is one of the inputs to `repo_state_id`, so any tree digest written here would be stale on write.
The binding value is in the `runs/` record emitted by the sealing program.

## 3. Whether a validation evaluation is authorized at all

Gate 3 passed. `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json`
(sha256 `904cb6668202df8628bbb08a494511e8ee584fc49cc5de7b5782a35ddd38fb93`) records
`stage_verdict.verdict` = `PASS` with `pass_token` = `STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT`,
`candidates_evaluated` = 3, and `admitted_candidates` = `SE100-S3A2-C1-PULLBACK-RA1`,
`SE100-S3A2-C2-MEANREV-RA1`. That is the condition constitution gate 4 requires upstream, and it is
the authorization for a validation evaluation of one sealed representative under a frozen procedure.

It is not authorization to read validation data in *this* session. `SE100-CFG-4001` records
`validation_evaluation_authorized: true` for the sealed representative and the sealed procedure, and
`validation_access_authorized_in_this_session: false`. The distinction is the point of a
pre-registration: the authorization is created here and exercised elsewhere.

Files sealed earlier and bound by digest:

| Path | sha256 |
| --- | --- |
| `governance/STAGE_0_CONSTITUTION.md` | `b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5` |
| `governance/STAGE_0_CONSTITUTION.json` | `af45fda6b37bed50768d5f3d01d4a91175da93e708c9daf1b630e35a981e2ff5` |
| `governance/STAGE_1_UNIVERSE.json` | `01601a60fa950a2429f72a2e9f627ec5af4c1853d1b47ffab35e81debc7eb67a` |
| `governance/STAGE_1_HOLDOUT_LOCK.json` | `9696161c4c5612fc7f6b3e5a3410917f20ad5707cb9b89b8bcc39cb70831dfb3` |
| `config/stage2_cost_model.json` | `f62d98436445cfc436463765ff6006dd234a3082ddf429992296645e697586e2` |
| `config/stage2_engine_spec.json` | `c376d12b2392eb2558092a6ad245481b88e36123e7e087522374dd28b218ed21` |
| `config/stage3_gate_criteria.json` | `310f1c978380f4a1d6b98b8c368975b1515476b032c123afb06f1dd597e3e18d` |
| `config/stage3_attempt2_strategy_protocol.json` | `77f1451c20e37640bd2843ff86d69eb54cbc0ebb592a696972fbdea6e05b5433` |
| `config/stage3_attempt2_gate_criteria_binding.json` | `a482f499173c0d7e2b0ca158b2edf7cb2e25a516ac2eb361e1441b2964006c8e` |
| `src/stockedge100/strategies/attempt2_candidates.py` | `86563afe7fd2d6ca1594739c4cf4b67f42ce0cdb70fe1e2138c1e7bafeb56a2d` |
| `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.json` | `26eecacfe96420878ce647b86f68da8ed8a17fea1338d85ee982b190645ed466` |
| `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json` | `904cb6668202df8628bbb08a494511e8ee584fc49cc5de7b5782a35ddd38fb93` |

Each of these is quoted or adopted rather than copied. The measurement definitions Gate 4 needs -
the Sharpe basis, the drawdown basis, the profit-factor basis and its null-not-infinity rule, the
trade definition, the complete friction model and the `2.0` stress multiplier - already exist in
`SE100-CFG-2001` and are adopted unchanged by digest. Restating them would create a second copy
that could drift; recomputing one hash proves nothing changed.

## 4. The representative: `SE100-S3A2-C2-MEANREV-RA1`

### 4.1 No mandatory constitutional selection rule exists

The constitution defines gate conjunction within a candidate and says nothing about choosing among
candidates that pass. No frozen or sealed artifact carries a ranking rule, a tie-break, or a
primary-candidate designation. The Gate 3 Attempt 2 research report states on the record that Gate 3
admitted both and ranked neither. One constraint did apply:
`config/stage3_attempt2_gate_criteria_binding.json` answers the question of whether a robustness
neighbour may become its candidate's representative with, verbatim, "No. Never. Under no result."
The eligible set is therefore exactly the two admitted primaries.

`SE100-S3A2-C3-DEFENSIVE-RA1` was rejected at Gate 3 on S3-C6. It is ineligible and is not
reconsidered. The six Gate 3 Attempt 1 candidates were all rejected, every one on S3-C2 with a
development maximum drawdown above 15%; they are not revisited. No combination, average, or
portfolio of C1 and C2 is eligible, because under constitution section 11 that is a new candidate
that restarts at Gate 3.

### 4.2 The rule

`SE100-CFG-4003-R1`, the declared-variant research-shutdown screen:

> Eliminate any Gate 3 admitted candidate for which ANY of its declared runs - the PRIMARY
> parameterisation, any of its four declared robustness neighbours, or its section 7 required
> stressed-cost run - tripped the section 5.1 research shutdown on development data. If exactly one
> candidate survives, it is the representative. If both survive or neither survives, the rule does
> not decide and the stage stops for human selection.

Every term comes from a frozen or sealed artifact. The variant set was declared in
`SE100-CFG-3003` before any Attempt 2 code was written. The 15% level is constitution section 5.1
and `SE100-CFG-2001` `risk.research_shutdown_drawdown_fraction`. The stressed run is required by
constitution section 7. The scope "every run" is the scope at which `SE100-CFG-3004`
`shutdown_behaviour.enforced_for_every_run` records the shutdown was already enforced. This stage
chose no number.

The rule is **return-blind**: the predicate reads one boolean per declared run and never reads a
return, a Sharpe ratio, a profit factor, a drawdown magnitude, a trade count, or a benchmark
comparison. Had C1's returns exceeded C2's at every variant, C1 would still be eliminated. That
property is checkable by reading the predicate rather than by trusting its author, and it is what
distinguishes a prospective rule from a retrospective one.

### 4.3 The application

| Candidate | Declared runs | Shutdown trips | Where | Screen |
| --- | --- | --- | --- | --- |
| `SE100-S3A2-C1-PULLBACK-RA1` | 6 | **2** | `#N1` on 2020-02-27; `#PRIMARY#STRESS` on 2018-02-05 | ELIMINATED |
| `SE100-S3A2-C2-MEANREV-RA1` | 6 | **0** | - | SURVIVES |

Exactly one candidate survives, so the rule decides and no human selection is required. The
per-variant evidence for all twelve declared runs of both candidates, with each run's shutdown
session, maximum drawdown, trade digest and equity digest, is recorded in `SE100-CFG-4003`
`application.candidates`.

**The margin is recorded honestly.** C2 survives without a trip, but not comfortably.
`SE100-S3A2-C2-MEANREV-RA1#N2` reached a development drawdown of
`0.1465979382684879116079616515992935`, which is 34 basis points below the shutdown level, and
`#N1` reached `0.1438752249862801387348381472146044`, 61 basis points below it. Gate 4's S4-C3
ceiling is the same 15% on the same series. A representative whose development neighbours sat 34
basis points from that level has no margin to spare on a fresh window, and the drawdown condition
is a real risk of failure rather than a formality. This is written before any validation
observation exists.

### 4.4 What the rule is not

It is not a ranking; it produces a survivor set and would have decided nothing had both candidates
survived. It is not a claim that C1 is a bad strategy - C1 met every hard Gate 3 condition and
remains a Gate 3 admitted candidate on the record; it is simply not the one carried to validation.
It is not a repair of C1, because repairing C1's cost sensitivity would be a parameter change
creating a new candidate. And it is not a rule about magnitudes: the drawdowns above are recorded
for completeness and the predicate uses none of them.

Corroborating checks against **frozen** Gate 4 thresholds all agree with the screen and none was
used to build it: C1's development profit factor `1.105782641347494903980259629` is below Gate 4's
frozen `1.15` while C2's `1.440207563487695573551379825` is above it; C1's stressed development
return `0.0018` against C2's `0.3311`; C1's primary drawdown headroom of 33 basis points against
C2's 240. The one check that does **not** flatter the selected candidate is recorded in the same
list: neither candidate's development Sharpe at the sealed 0% cash rate - C1 `0.1284700281897133148507047085010721`,
C2 `0.4202409206802080245242547261750272` - reaches Gate 4's frozen floor of `0.50`.

### 4.5 The sealed parameterisation

`SE100-S3A2-C2-MEANREV-RA1`, family mean reversion, declared universe `["SPY"]`, declared warm-up
101 sessions, risk architecture `RA1`:

| Parameter | Value |
| --- | --- |
| `rsi_period` | 2 |
| `rsi_entry_below` | 10 |
| `exit_sma` | 5 |
| `f_base` | 0.50 |
| `vol_target` | 0.10 |
| `vol_floor_fraction` | 0.05 |
| `loss_control` | 0.08 |
| `max_hold` | 10 |
| `reentry_delay` | 5 |
| `ladder_rungs` | (0.08, 0.25), (0.10, 0.125) |

No value in that table may change. No robustness neighbour may be substituted for it. No risk
overlay, position-size cap, regime filter, or any other rule absent from the sealed specification
may be added. `SE100-CFG-4003` `prohibited_after_this_seal` states this as seven explicit
prohibitions, and the first of them is that the representative may not change **for any reason,
including a Gate 4 FAIL**.

## 5. The research question

> Does the single sealed Stage 4 representative, run unchanged on the locked validation window with
> no re-fitting of any kind, satisfy every hard condition of constitution gate 4? The question is
> deliberately not 'which of the Gate 3 admitted candidates performs better on validation' - that
> question would require reading the window twice and would make the selection a function of the
> result.

## 6. What may be read, and how often

The windows, from `governance/STAGE_1_HOLDOUT_LOCK.json`:

| Window | Range | State at the end of this session |
| --- | --- | --- |
| Development | 1993-01-29 to 2021-07-31 | read, no longer pristine |
| Validation | 2021-08-01 to 2024-07-31 | **LOCKED** |
| Final holdout | 2024-08-01 to 2026-07-31 | **SEALED** |

The single-read rule, verbatim from `SE100-CFG-4001`:

> The validation partition is read exactly once, in exactly one authorized session, from exactly one
> dataset load, with both declared runs executed inside that session against that load.

Two consequences worth stating plainly. The section 7 stressed-cost run is **not** a second read,
because "one read" is defined at the level of the session and the dataset load rather than at the
level of the engine invocation - two runs over one load is one read. And there is **no re-run**.
`SE100-CFG-3004` `rerun_policy.may_a_result_be_rerun_after_a_valid_completed_evaluation` answers,
verbatim, "No." A re-run that produced a different number would be a determinism defect and a
blocker, not a better result. `SE100-CFG-4001` `iteration_budget`
`re_runs_permitted_after_a_valid_completed_run` is `0`. What *is* re-run in full is a run that never
reached the window end, because that is `NOT_RUN` rather than a result.

A warm-up tail of 101 sessions from the **development** window precedes the first validation
session. That is a read of already-authorized development data, not of validation data, and it is
not look-ahead: the warm-up is strictly earlier than the first validation session. It is recorded
as interpretation `S4-INTERP-3` rather than left implicit.

## 7. The two declared runs

| Run label | Cost basis | Gates |
| --- | --- | --- |
| `SE100-S4-C2-MEANREV-RA1#VALIDATION#BASE` | complete base friction from `SE100-CFG-2001` | S4-C1, S4-C2, S4-C3, S4-C4, S4-C6 |
| `SE100-S4-C2-MEANREV-RA1#VALIDATION#STRESS` | exactly 2x the complete base friction | S4-C5 |

`runs_declared.count` is `2` and `count_is_a_hard_limit` is `true`. No robustness neighbour runs are
declared, and that is deliberate rather than an omission: Gate 4 states no neighbour condition, so
four extra runs on a once-readable window would gate nothing while multiplying the number of draws
taken from it. Five benchmark accounts (including SPY buy-and-hold and a 0% cash series) are
declared as reporting context; they are computed from the same single load, are not additional
reads, and gate nothing.

## 8. Gate 4, extracted rather than invented

The seven conditions are not this stage's invention. They are already frozen in
`governance/STAGE_0_CONSTITUTION.md` lines 193 to 203, and `SE100-CFG-4002` carries them verbatim:

> Pass only if, on the locked validation/walk-forward period: after-cost total return is positive;
> annualized Sharpe ratio is at least 0.50 using daily equity returns and a documented cash rate;
> maximum drawdown is no worse than 15%; profit factor is at least 1.15; stressed-cost total return
> remains positive; at least 70% of completed walk-forward test folds have positive after-cost
> return; no material rule, feature, universe, or parameter change is made in response to validation
> results. Fail verdict: STRATEGY_REJECTED_IN_VALIDATION.

| Condition | Requirement | Threshold source |
| --- | --- | --- |
| S4-C1 | after-cost total return is positive | frozen |
| S4-C2 | annualized Sharpe at least 0.50 on daily equity returns with a documented cash rate | frozen `0.5` |
| S4-C3 | maximum drawdown no worse than 15% | frozen `15` |
| S4-C4 | profit factor at least 1.15 | frozen `1.15` |
| S4-C5 | stressed-cost total return remains positive | frozen |
| S4-C6 | at least 70% of completed walk-forward test folds have positive after-cost return | frozen `70` |
| S4-C7 | no material rule, feature, universe, or parameter change in response to validation results | frozen, no numeric threshold |

Gates are conjunctive per constitution section 9. Unlike Gate 3, Gate 4 has **no disjunction across
candidates**: exactly one representative is evaluated, so the conjunction within that candidate *is*
the stage verdict, and there is no second candidate whose result could rescue it.

The documented cash rate S4-C2 requires already exists on disk. `SE100-CFG-2001`
`metrics.sharpe_note` states, verbatim, "The documented cash rate required by constitution gate 4 is
the 0% conservative proxy declared above." It is adopted, not chosen here. Its direction of bias is
recorded: a 0% cash rate cannot make S4-C2 harder to pass, so a Sharpe of at least 0.50 measured at
0% is weaker evidence than the same figure measured against a positive rate. No substitute cash
series may be introduced later, and no new data source - including a Treasury series - is
authorized.

### 8.1 Verdict tokens, fixed before any result

| Token | Value | How derived |
| --- | --- | --- |
| Fail | `STAGE_4_STRATEGY_REJECTED_IN_VALIDATION` | the constitution's gate 4 `fail_result` prefixed with the stage, exactly as `SE100-CFG-3002` prefixed gate 3's |
| Pass | `STAGE_4_STRATEGY_ADMITTED_IN_VALIDATION` | its negation, REJECTED to ADMITTED, exactly as `SE100-CFG-3002` derived gate 3's absent `pass_result` |

The constitution's gate 4 entry defines a `fail_result` and **no** `pass_result`. Rather than
invent one or borrow one, the pass token is derived by negation using the same method a sealed
artifact already used for the same omission at Gate 3, and it is fixed here, before any result
exists. Gate 5's `ELIGIBLE_FOR_PAPER_TRADING` is **not** Gate 4's pass token and may not be emitted
by a Gate 4 evaluation.

A `FAIL` is a deliverable. The constitution keeps negative and rejected results on disk, so the
Gate 4 evaluation package must be written whichever token it reaches.

## 9. The one measurement this stage authors: the fold construction

A repository-wide search for "walk-forward", "walk_forward" and "walkforward" returns only
restatements of the constitution's own sentence. **No fold definition exists anywhere on disk.**
S4-C6 is therefore unmeasurable until one is written, and constitution section 8's requirement of a
signed specification created before execution is the authority to write it prospectively. It is
recorded as `S4-CONFLICT-4` rather than presented as pre-existing.

`SE100-CFG-4002-WF1` fixes it:

- **12 consecutive test folds of 3 calendar months**, tiling the validation window exactly, anchored
  on 2021-08-01 rather than on natural quarters: fold 1 `2021-08-01` to `2021-10-31`, fold 2
  `2021-11-01` to `2022-01-31`, and so on to fold 12 `2024-05-01` to `2024-07-31`.
- **Zero train folds.** "Walk-forward" normally implies periodic re-fitting, and Gate 4's own
  seventh condition together with constitution section 11 forbids exactly that. The gate text names
  only "test folds". `train_folds` is the empty set, and the tension is recorded as `S4-CONFLICT-5`
  - recorded, not repaired.
- **Fold return** is measured on the base-cost daily closing marked equity: fold 1 against the
  sealed starting capital of USD 100.00, fold k against the last session of fold k-1. One
  continuous run, no force-close at fold boundaries. Positive means strictly greater than zero.
- **Per-fold session counts are deliberately not recorded here.** They are validation-partition
  coverage, and computing them in this session would be an inspection of the locked window.

Why twelve, decided before any result: three months is the shortest tiling block that reliably
contains enough sessions for a round trip of a strategy with `max_hold` 10 and `reentry_delay` 5;
70% of 12 is 8.4, so **9 folds pass and 8 fail** with no tie at the threshold; and a finer partition
is the more demanding test, because consistency must hold at higher resolution.

A completed fold is defined by three tests, and a fold after a research shutdown counts as
**COMPLETED with a return of exactly 0** rather than as absent. That matters: if a shutdown could
shrink the denominator, a strategy that failed early would face an easier 70% test than one that
survived. A run that does not reach 12 completed folds yields `NOT_EVALUABLE` for S4-C6, which is
never a pass.

## 10. Stressed cost changes status at Gate 4

At Gate 3 the stressed run was required and **non-gating**. `SE100-CFG-3004` states it in terms:
`cost_stress_is_not_a_gate_3_condition`. At Gate 4 the constitution makes "stressed-cost total
return remains positive" a hard condition, so the same run becomes **gating**. The multiplier is not
re-chosen: it is the `2.0` already sealed in `SE100-CFG-2001` with its `stress_applies_to` scope.

The development precedent is on the record. C1's stressed run returned `0.0018` and tripped the
research shutdown on 2018-02-05; C2's returned `0.3311` and tripped nothing. This is development
evidence and is not a prediction of either candidate's validation behaviour.

## 11. The two 15% numbers

Constitution section 5.1's research-shutdown level, sealed in `SE100-CFG-2001` as
`risk.research_shutdown_drawdown_fraction` = `0.15`, and Gate 4's S4-C3 drawdown ceiling of 15% are
the same number applied to the same series. So S4-C3 is met if and only if the shutdown never fires
(`S4-CONFLICT-3`). One consequence is worth stating before the fact: a shutdown during validation
fails S4-C3 immediately, and simultaneously drives every subsequent fold to a return of 0, which
alone puts S4-C6 out of reach. There is no arrangement of the remaining conditions that rescues a
shutdown.

## 12. What a FAIL does and does not authorize

`SE100-CFG-4001` `no_retuning_rule` fixes this before any result. A `FAIL` does **not** authorize
retuning the representative, substituting C1, promoting a neighbour, adding an overlay, relaxing a
threshold, re-reading the window, or a "Stage 4 Attempt 2". There is no Attempt 2 at Gate 4 in this
design: the window can be read once. What a `FAIL` authorizes is writing it down.

**A Gate 4 FAIL is a live and arguably likely outcome, and that is stated here rather than
discovered later.** Neither Gate 3 admitted candidate reached S4-C2's frozen Sharpe floor of `0.50`
on development data at the same 0% cash rate, and the selected representative's development
neighbours came within 34 basis points of the drawdown ceiling. The pre-registration is written to
make an honest negative result as reportable as a positive one.

If a defect in the sealed specification is discovered **before** any validation observation is read,
it is repaired by superseding this pre-registration with a new document id, never by editing this
one in place. If it is discovered **after**, the outcome is `INVALIDATED` - which is neither a fail
nor a pass - and the window has been spent.

## 13. Adaptive disclosure: what this session knew

This selection was made in a session with lawful access to Gate 3 development evidence. It is an
adaptive step and is disclosed as one.

What is independent is the rule's **output**: given the predicate, the answer is a function of
shutdown booleans in a sealed evidence file and no return enters it. What is **not** independent is
the choice of predicate, which was made by a researcher who had read the development evidence; a
different return-blind predicate might have selected differently. What limits that freedom is that
the predicate has no tunable part - once "shutdown trip over the declared variant set" is chosen,
the answer is fixed by the evidence and cannot be nudged. The full application for both candidates,
including every variant that did **not** trip, is recorded so a reader can verify the count instead
of trusting it.

The multiplicity accumulated in development is not reset by this stage. Gate 3 Attempt 1 ran 6
primary parameterisations; Gate 3 Attempt 2 ran 15 gating variants plus 3 non-gating stressed runs,
18 development runs; 24 development runs across both attempts. Stage 4 adds 2. Any later statistical
interpretation uses the cumulative count, and two runs of one frozen parameterisation on a fresh
window do not undo what came before. The representative keeps its Gate 3 identifier unchanged, so
this adaptation is not concealed behind a new strategy name.

## 14. Explicit non-authorizations

Nothing below is authorized by this pre-registration, and nothing below happened in this session:

1. No validation observation was read, and none may be read until a separately authorized
   evaluation session.
2. No Stage 4 evaluator, result, metric, or fold implementation was written. No empty or placeholder
   Stage 4 evaluator or result file was created.
3. No development backtest was run, and no development result was recomputed.
4. No new data source of any kind, including a Treasury or cash-rate series.
5. No network access, no broker connection, no Alpaca client, no credential read.
6. The final holdout stays **SEALED** regardless of the Gate 4 outcome. A Gate 4 pass authorizes
   only the next frozen evaluation step, which is the constitutional holdout gate, in its own
   separately authorized session.
7. Gate 5's `ELIGIBLE_FOR_PAPER_TRADING` may not be emitted by a Gate 4 evaluation.
8. `paper_trading_authorized`, `shadow_live_authorized`, `capital_or_risk_expansion_authorized` and
   `live_trading_authorized` all remain **false**.
9. StockEdge100 is a research project. It is not trade-ready and may not be described as
   trade-ready.

## 15. Pre-freeze contamination assessment

Measured before this pre-registration was written, not asserted afterwards. The predicates and their
definitions are recorded in `governance/STAGE_4_PREREGISTRATION.json`
`contamination_predicates`, each carrying its own definition so a reader can check what was counted:

| Predicate | Required |
| --- | --- |
| Stage 4 evaluator or result modules under `src/` | 0 |
| Stage 4 result artifacts under `reports/` | 0 |
| Stage 4 run records under `runs/` | 0 (measured before this seal writes its own) |
| Modules or tests that read validation or holdout observations during pre-registration | 0 |
| Gate 3 Attempt 2 checksum records verify entry-for-entry | true |

The fail-closed structural guards are exercised by `tests/unit/test_stage4_preregistration.py`,
which asserts on **dates only** that the development research window refuses a validation date and
that a market view constructed at a validation date refuses to be rebound. Those tests read no
observation.

---

*This document is a pre-registration. It records no validation performance, because none may be
generated at this stage and none exists. The next authorized action is the sealed Stage 4 validation
evaluation, in its own session, on the sealed representative, under the frozen procedure and
criteria named here.*
