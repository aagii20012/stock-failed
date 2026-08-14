# Stage 4 — sealed validation execution and gate 4 decision report

| Field | Value |
| --- | --- |
| Document id | `SE100-GOV-4001` |
| Project | StockEdge100 |
| Stage | Prompt stage 4 — constitutional gate 4 (validation robustness). Execution and decision. |
| Session type | Sealed validation execution. One validation read, two registered runs, one gate decision. |
| Governing document | `SE100-GOV-0001` — `governance/STAGE_0_CONSTITUTION.md`, FROZEN, v1.0.0 |
| Pre-registration executed | `SE100-GOV-0008` — `governance/STAGE_4_PREREGISTRATION.{md,json}`, sealed `2026-08-13T14:01:21Z`, unmodified |
| Representative | `SE100-S3A2-C2-MEANREV-RA1`, selected by `SE100-CFG-4003` rule `SE100-CFG-4003-R1` |
| Evidence | `reports/stage4/STAGE_4_VALIDATION_EVIDENCE.json` (`SE100-EVID-4001`), generated `2026-08-14T14:32:26Z` |
| Evaluation run | `SE100-R-20260814T143226Z` |
| Authored (UTC) | 2026-08-14T14:43:47Z |
| **Verdict** | **`FAIL — STAGE_4_STRATEGY_REJECTED_IN_VALIDATION`** |
| Gate 4 evaluated | **Yes.** One evaluation of one representative on the locked validation window. |
| Gate 4 passed | **No.** Five of seven conditions MET; `S4-C2` and `S4-C6` NOT_MET. |
| Holdout | `2024-08-01`–`2026-07-31`, **SEALED**, sessions read `0`. Unchanged by this stage. |
| `live_trading_authorized` | `false` |

No repository-state digest is written into this file. `repo_state_id` is computed over
`governance/*.md` among other patterns, so a tree digest recorded here would invalidate itself on
write. The starting and ending values, and their reconciliation, live in
`reports/stage4/STAGE_4_VALIDATION.json` and in the append-only `runs/` records, which are outside
the digest's patterns. Individual **file** digests are quoted below; a file digest is not a digest of
the tree that contains this file.

---

## 1. What this session did, and what it did not

It verified the integrity of the whole controlling record, proved the representative byte-for-byte
identical to the implementation Gate 3 evaluated, implemented the sealed evaluation and gate logic
with tests written before any validation observation existed, loaded the validation partition once,
executed the two registered runs in the declared order, evaluated the seven sealed Gate 4 conditions
against the resulting evidence, and built this decision package.

It did **not** read the holdout, retune or modify the representative, reconsider
`SE100-S3A2-C1-PULLBACK-RA1` or the rejected `C3`, promote a neighbour, add a run, rerun a completed
run, change a fold boundary, change a cost or benchmark or metric, weaken a threshold, contact a
broker, read a broker credential, generate an order, or begin any form of trading.

The pre-registration disclosed that a Gate 4 failure was expected of this representative. That
disclosure did not enter the evaluation: the seven predicates were sealed on `2026-08-13`, coded
against synthetic evidence, tested in both directions, and applied mechanically to the measured
numbers. The verdict below is what the arithmetic produced.

## 2. Integrity verification performed before validation was loaded

All checks ran before any evaluator touched a validation observation.

| Check | Result |
| --- | --- |
| Stage 0 freeze (`governance/STAGE_0_FREEZE.sha256`, from `governance/`) | verified, both entries `OK` |
| Fourteen checksum records across `governance/` and `reports/` | every entry `OK`, none `FAILED`, none `MISSING` |
| Constitution, all Stage 0–4 governance reports, pre-registrations and manifests | read in full |
| Sealed Stage 4 protocol, gate criteria, representative selection | read in full and adopted by digest |
| `repo_state_id` recomputed and reconciled against the seal | reconciled, see §3 |
| Thirteen-artifact recheck set | 13 of 13 recompute equal, see §4 |
| Validation guard active | engine window and run bounds both end `2024-07-31`; holdout start `2024-08-01` |
| Holdout guard active | holdout state `SEALED`, `sessions_read` `0`, unreachability proved mechanically |
| Pre-existing Stage 4 evaluator, result, or validation run | none — no evaluator module and no evaluation run record existed at session start |
| Validation observation accessed after sealing | none prior to the single authorized load |
| Sealed records authorize this session | `validation_evaluation_authorized` `true`, scope "exactly one evaluation of `SE100-S3A2-C2-MEANREV-RA1`" |

The checksum records follow two conventions and were each verified from the working directory their
own convention requires: `STAGE_0_FREEZE.sha256` and `STAGE_1_FREEZE.sha256` carry bare filenames and
verify from `stockedge100/governance/`; the remaining twelve carry project-root-relative paths and
verify from `stockedge100/`. A failure from the wrong directory would be an operator error and not an
integrity failure, so neither was reported as one.

## 3. Repository state reconciliation

Two Stage 4 run records precede this session and they fix two different trees. `2026-08-13T14:01:21Z`
sealed the protocol (`runs/SE100-R-20260813T140121Z.json`, 115 entries); the pre-registration session
then wrote its own decision package, which closed Stage 4's design session and recorded the tree three
artifacts later (`runs/SE100-R-20260814T111459Z.json`, 118 entries). The second is the **ending**
`repo_state_id` this session was handed as its starting state, so it is the baseline reconciled below.
Its `repo_state_id` is the value the operating prompt gives as beginning `718be055`; the complete
digest is in the decision record and in that run record, not in this file, because `repo_state_id`
covers `governance/*.md` and a tree digest written here would invalidate itself on write.

Neither tree is supposed to equal the tree at evaluation time — this session added the evaluator the
seal authorized. What matters is that nothing already present changed. Comparing the `code_hashes` map
of the pre-registration package run with the map recorded at evaluation:

| Quantity | Value |
| --- | --- |
| Entries at the pre-registration package (start of this session) | 118 |
| Entries at evaluation | 123 |
| **Added** | **5** |
| **Changed** | **0** |
| **Removed** | **0** |

The five added files are `src/stockedge100/strategies/stage4_evaluation.py`,
`src/stockedge100/strategies/stage4_gate.py`, `src/stockedge100/reporting/stage4_evidence.py`,
`tests/unit/test_stage4_evaluation.py` and `tests/unit/test_stage4_evidence.py` — the authorized
evaluator, its gate logic, its evidence writer, and their tests. Zero changed and zero removed is the
mechanical evidence that every frozen artifact, every sealed configuration and every pre-existing
module is byte-for-byte unchanged. The exact digests are in the decision record.

The decision record carries four diffs rather than this one, because quoting a single baseline invites
the reader to mistake it for the other: seal → pre-registration package (115 → 118, `README.md`
changed, which it is supposed to do each stage), pre-registration package → evaluation (the table
above), evaluation → package build (this report and the package builder), and seal → package build.
`protected_paths_changed_or_removed` is empty in all four: across every pair of states, nothing under
`governance/` or `config/` moved and nothing was removed.

## 4. Strategy invariance — S4-C7

The sealed recheck set is thirteen artifacts. Twelve are listed in
`governance/STAGE_4_PREREGISTRATION.json` `sealed_digests_for_s4_c7.entries`; the thirteenth is that
record itself, whose digest is carried by `governance/STAGE_4_PREREGISTRATION.sha256` because nothing
hashes itself. Every one was recomputed from disk **before** the validation load and again as part of
the gate evaluation.

| Clause | Required | Measured |
| --- | --- | --- |
| Every sealed digest recomputes equal | 13 of 13 | **13 of 13** |
| Validation evaluation run records for the representative | exactly 1 | **1** (`SE100-R-20260814T143226Z.json`) |
| Validation-window engine runs | equal to the declared count | **2**, declared **2** |
| Representative parameters unchanged | true | **true** |

The no-tolerance rule was applied exactly as sealed: exact equality of every digest, no immaterial
change. `S4-C7` is **MET**.

The representative's implementation is `src/stockedge100/strategies/attempt2_candidates.py`, digest
`86563afe7fd2d6ca1594739c4cf4b67f42ce0cdb70fe1e2138c1e7bafeb56a2d` — the value sealed before any
Stage 4 evaluator existed, unchanged. No candidate class, indicator, band, sizing rule or risk
architecture was touched at any point in this session, before or after performance became visible.

## 5. The single validation read

| Field | Value |
| --- | --- |
| Validation partition | `2021-08-01` – `2024-07-31` |
| Engine visibility window | `2021-03-09` – `2024-07-31` (validation plus the sealed 101-session warmup) |
| Run bounds | `2021-08-01` – `2024-07-31` |
| Holdout window | `2024-08-01` – `2026-07-31`, `SEALED`, sessions read `0` |
| Validation dataset loads | **1** |
| Validation reading sessions | **1** |
| Validation-window engine runs | **2** |
| Universe | `["SPY"]` |
| `data/normalized/daily/SPY.csv` | `42c202dad76f60e34a35d45514539dc8e7e4b3bccd7945875b845eb1bed6963c` |
| `data/manifests/STAGE_1_NORMALIZED_MANIFEST.json` | `15b9ed6b090e79f21bc55e8f2c5bed7ca2eac8c51b83863d80c4cc45ebd5d184` |
| Exit status | `OK` |

The warmup extension is a **visibility** bound, not a run bound: it governs what history an indicator
may see on the first scored session, and the engine's `start`/`end` still bound which sessions are
traded and marked. Both bounds end `2024-07-31`, which precedes the holdout start, so no holdout bar
is reachable. `MarketView.history` returns bars filtered by `window.contains(day)` and `day <= as_of`,
and `as_of` is drawn from `sessions_between(run_start, run_end)`; with both bounds before the holdout
start the holdout is unreachable by construction rather than by convention. The proof is recorded in
the evidence file.

The partition was loaded once, both runs executed inside that one load, and the process exited before
any second load could occur. No partial result was inspected to decide what to do next, no
interactive diagnostic ran against validation data, no alternative metric was computed, and no
unregistered variant was executed.

## 6. The two registered runs

Both runs are registered in `config/stage4_validation_protocol.json` `runs_declared`, whose count of
2 is recorded there as a hard limit. They executed in the declared order.

| # | Run label | Scenario | Stress multiplier | Half-spread | Slippage | Friction per side | Conditions served |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `SE100-S4-C2-MEANREV-RA1#VALIDATION#BASE` | BASE | `1` | 2.5 bps | 2.5 bps | 5.0 bps | S4-C1, S4-C2, S4-C3, S4-C4, S4-C6 |
| 2 | `SE100-S4-C2-MEANREV-RA1#VALIDATION#STRESS` | STRESSED | `2.0` | 5.00 bps | 5.00 bps | 10.00 bps | S4-C5 |

The stress multiplier was not chosen by this stage. `2.0` is bound by digest from `SE100-CFG-2001`
`frictions.stress_multiplier`, applied to the complete friction assumption per
`frictions.stress_applies_to`. The evidence records the applied multiplier as equal to the sealed
value.

### Base-cost results

| Measure | Value |
| --- | --- |
| Equity points | 754 |
| Daily returns | 753 |
| Reached window end | `true` |
| Starting equity | `100.00` |
| Final equity | `102.15` |
| Total return | `0.0215` |
| Annualised Sharpe (cash rate `0.00`) | `0.2025294206503088680547420121230750` |
| Maximum drawdown | `0.03161389554784035323758760240844931` |
| Drawdown basis | daily marked equity including cash, peak to trough |
| Profit factor | `1.196526508226691042047531993` |
| Gross profit | `13.09` |
| Gross loss | `10.94` |
| Closed trades | 41 |
| Section 5.1 research shutdown | **never fired** (`shutdown_session` `null`, fraction `0.15`) |

### Stressed-cost results

| Measure | Value |
| --- | --- |
| Equity points | 754 |
| Final equity | `100.15` |
| Total return | `0.0015` |
| Stress multiplier applied | `2.0`, equal to the sealed value |
| Shutdown enforced | `true` |
| Section 5.1 research shutdown | **never fired** (`shutdown_session` `null`) |

Doubling the friction assumption consumed 93% of the base-cost return. `0.0015` is strictly positive,
so `S4-C5` is met — but it is met by 15 basis points over three years, and §11 records that as a
material limitation rather than a comfortable margin.

## 7. The twelve walk-forward folds

Fold construction `SE100-CFG-4002-WF1`: twelve contiguous calendar-aligned three-month out-of-sample
test folds spanning the validation partition, zero training folds. `S4-CONFLICT-5` records that this
degenerates the constitutional phrase "walk-forward" to pure out-of-sample partitioning because the
representative re-estimates no parameters; that resolution was sealed prospectively and is applied
here unchanged. Fold equity chains: each fold's baseline is the preceding fold's closing equity.

| # | Start | End | Sessions | Completed | Baseline equity | Closing equity | Fold return | Sign |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2021-08-01 | 2021-10-31 | 64 | yes | `100.00` | `100.65` | `0.0065` | + |
| 2 | 2021-11-01 | 2022-01-31 | 63 | yes | `100.65` | `99.36` | `-0.0128166915052160953800298063` | − |
| 3 | 2022-02-01 | 2022-04-30 | 62 | yes | `99.36` | `99.72` | `0.003623188405797101449275362` | + |
| 4 | 2022-05-01 | 2022-07-31 | 62 | yes | `99.72` | `100.15` | `0.004312073806658644203770558` | + |
| 5 | 2022-08-01 | 2022-10-31 | 65 | yes | `100.15` | `99.63` | `-0.0051922116824762855716425362` | − |
| 6 | 2022-11-01 | 2023-01-31 | 62 | yes | `99.63` | `102.14` | `0.025193214895111914082103784` | + |
| 7 | 2023-02-01 | 2023-04-30 | 61 | yes | `102.14` | `101.86` | `-0.0027413354219698453103583317` | − |
| 8 | 2023-05-01 | 2023-07-31 | 63 | yes | `101.86` | `103.11` | `0.012271745533084625957196152` | + |
| 9 | 2023-08-01 | 2023-10-31 | 65 | yes | `103.11` | `101.0882445391692330300` | `-0.0196077534752280765202211231` | − |
| 10 | 2023-11-01 | 2024-01-31 | 62 | yes | `101.0882445391692330300` | `101.78` | `0.006843085108305828525379588` | + |
| 11 | 2024-02-01 | 2024-04-30 | 62 | yes | `101.78` | `101.77` | `-0.0000982511298879937119276872` | − |
| 12 | 2024-05-01 | 2024-07-31 | 63 | yes | `101.77` | `102.15` | `0.003733909796600176869411418` | + |

Declared test folds 12, declared training folds 0, expected completed count 12, **completed 12**,
**positive 7**.

Fold 11 is worth naming: `-0.0000982…` is negative by roughly one part in ten thousand. `S4-C6`
counts strictly positive folds and this one is not one, so it counts against the ratio. Rounding it to
zero, or to "flat", would have changed 7 positives to 7 either way — but rounding *up* would have
made it 8, and 8 is still below the 9 required. The condition does not turn on this fold. The
sealed instruction not to round before comparison was followed regardless.

The twelve individual fold returns are reported and do not gate. The **ratio** gates; no single fold
does.

## 8. Gate 4 decision

The seven conditions are taken verbatim from `config/stage4_gate_criteria.json` (`SE100-CFG-4002`),
sealed before any validation observation existed. Every formula, threshold, denominator, boundary
rule and verdict semantic was extracted from that file rather than restated. Comparisons are exact
Decimal comparisons; no value was rounded before comparison.

| Id | Sealed condition | Predicate | Measured | Boundary | Verdict |
| --- | --- | --- | --- | --- | --- |
| S4-C1 | after-cost total return is positive | `total_return > 0` | `0.0215` | strict | **MET** |
| S4-C2 | annualized Sharpe ratio is at least 0.50 using daily equity returns and a documented cash rate | `sharpe >= 0.50` | `0.2025294206503088680547420121230750` | inclusive | **NOT_MET** |
| S4-C3 | maximum drawdown is no worse than 15% | `max_drawdown <= 0.15` | `0.03161389554784035323758760240844931` | inclusive | **MET** |
| S4-C4 | profit factor is at least 1.15 | `profit_factor >= 1.15` | `1.196526508226691042047531993` | inclusive | **MET** |
| S4-C5 | stressed-cost total return remains positive | `stressed_total_return > 0` | `0.0015` | strict | **MET** |
| S4-C6 | at least 70% of completed walk-forward test folds have positive after-cost return | `positive / completed >= 0.70` | `7 / 12 = 0.5833333333333333333333333333` | inclusive; smallest passing count with twelve folds is 9 | **NOT_MET** |
| S4-C7 | no material rule, feature, universe, or parameter change is made in response to validation results | mechanical, not asserted — every sealed digest recomputes, exactly one evaluation run record, engine runs equal declared | 13/13 equal, 1 record, 2 = 2 | exact equality, no tolerance | **MET** |

- Conditions: 7. MET: 5 (`S4-C1`, `S4-C3`, `S4-C4`, `S4-C5`, `S4-C7`). NOT_MET: 2 (`S4-C2`, `S4-C6`).
  NOT_EVALUABLE: 0. NOT_APPLICABLE_BY_CONDITION_TEXT: 0. NOT_RUN: 0. UNKNOWN: 0. Missing evidence: 0.
- Combination **within the candidate**: `CONJUNCTIVE`. Two conditions NOT_MET, therefore the
  conjunction is false.
- Combination **across candidates**: `NOT_APPLICABLE_EXACTLY_ONE_REPRESENTATIVE`. Gate 4 evaluates the
  single sealed representative. There is no disjunction to take and no
  `admissible_candidate_exists` row: that row belongs to a stage that ranks candidates, and this one
  does not.
- `gate_passed`: **false**.

Each threshold was additionally cross-checked against its companion key in the sealed criteria — the
literal in the predicate string against the separately recorded threshold value — and all seven agree.

**S4-C3 and the research shutdown.** `S4-CONFLICT-3` records that the Gate 4 drawdown ceiling and the
§5.1 research shutdown are the same number, 15%, measured against the same running high-water mark, so
`S4-C3` is met if and only if the shutdown never fires. It did not fire, on either run. Measured
drawdown of 3.16% leaves the ceiling untouched — but that is a consequence of a strategy that barely
moved, not of risk control that was tested and held.

### Verdict

```
FAIL — STAGE_4_STRATEGY_REJECTED_IN_VALIDATION
```

The token is `verdict_token_derivation.fail_token` in `config/stage4_gate_criteria.json`, taken from
disk. Its sealed `fail_condition` is "The single sealed representative fails at least one hard
condition of Gate 4, or any hard condition is NOT_EVALUABLE, NOT_RUN or UNKNOWN, or its evidence is
missing." Two hard conditions failed. The constitution's own Gate 4 text names the same fail verdict,
`STRATEGY_REJECTED_IN_VALIDATION`.

`SE100-S3A2-C2-MEANREV-RA1` is **rejected in validation**.

## 9. What this verdict means, and the terminal consequence

`governance/STAGE_4_PREREGISTRATION.json` `binding_consequences` item 8, sealed before the read:

> A Gate 4 FAIL is a deliverable, not a reason to retune, substitute, promote a neighbour, relax a
> threshold, or read the window again. There is no Attempt 2 at Gate 4 in this design.

`config/stage4_validation_protocol.json` `no_retuning_rule` lists what a fail does **not** authorize:
retuning C2's parameters and re-reading validation; substituting C1 or any neighbour of either
candidate; relaxing a threshold, re-cutting the folds, changing the cash rate, or reinterpreting
"positive"; reopening Gate 3 Attempt 2 to admit a different candidate; describing the fail as a defect
in the protocol. What it **does** authorize is recorded there in one sentence: "Recording the fail as
a deliverable, and stopping."

The same clause states the standing cost of what has now happened: any subsequent strategy work is a
new candidate restarting at Gate 3, disclosed as adaptive, "with the validation window's information
now known to the researcher and therefore permanently compromised for that candidate." The validation
window has been read. It cannot be unread, and it cannot be read again.

The holdout remains sealed. A Gate 4 pass would have authorized nothing but the separately governed
constitutional holdout gate, and only after explicit human authorization recorded there; a Gate 4 fail
authorizes not even that.

## 10. Conflicts

`S4-CONFLICT-1` through `S4-CONFLICT-5` were found and resolved prospectively by the pre-registration
and are recorded in `config/stage4_gate_criteria.json` `conflicts_found`. All five were applied here
exactly as sealed, and none was reopened. Two further conflicts were found during execution. Both are
**reported, not repaired**; no frozen or sealed artifact was edited.

### S4-CONFLICT-6 — the parameterisation is not where the seal says it is

The sealed invariance clause names `config/stage4_representative_selection.json` as the home of the
representative's parameterisation. That file carries no parameter values; they are in
`config/stage4_validation_protocol.json` `sealed_representative`. Both files are inside the
thirteen-artifact digest set and both recompute equal, so the clause's *purpose* — that the parameters
cannot have changed — is satisfied regardless of which of the two files is read. The evaluator
recorded the discrepancy in the evidence rather than choosing a file silently. Nothing in the verdict
turns on it.

### S4-CONFLICT-7 — the sealed P5 contamination predicate cannot survive its own authorization

`governance/STAGE_4_PREREGISTRATION.json` `contamination_predicates` P5 counts files under
`src/stockedge100/` with suffix `.py` whose relative path contains `stage4` whose parsed syntax tree
contains an import of the data-access layer, a call to a dataset loader, an import of a network or
broker package, an attribute access used to read an environment variable or open a connection, or a
string constant containing a URL scheme. Its sealed required value is 0, and its sealed purpose is
stated in the same clause: "It is the fail-closed proof that **the pre-registration path** cannot read
a validation or holdout observation and cannot reach a broker."

The predicate's stated purpose is scoped to the pre-registration path. Its mechanical scope is every
`stage4`-named module under `src/`. Once the evaluation the pre-registration authorizes actually
exists, the evaluator must call a dataset loader — that is the whole of its job — so the predicate
necessarily reads at least 1 and can never read 0 again.

Measured after the evaluation, by the package builder, before it wrote anything:

| Half of P5 | Count | Files and markers |
| --- | --- | --- |
| data-access half (dataset-loader call, data-layer import) | **2** | `strategies/stage4_evaluation.py` — `call load_dataset`, `from stockedge100.backtest.dataset`, `from stockedge100.data.calendar`; `reporting/stage4_evidence.py` — `call load_validation_series` |
| broker / network / environment-variable / URL half | **0** | none |

The half that guards against a broker, a network call, a credential read or a URL is **0**, exactly as
sealed, and remains the fail-closed proof it was written to be. The half that reads 2 reads 2 because
the authorized evaluator does the authorized thing. Both hits are resolved to a named cause in
`contamination_predicates.resolution` of the decision record, and the builder refuses to write a
package at all if any hit is left unresolved:

- `stage4_evaluation.py` loads the price series and the trading calendar; `stage4_evidence.py`
  re-reads the validation series to compute the evidence digest. Both are reads the seal authorized
  this session to perform, and both are inside the validation window.
- `from stockedge100.data.calendar` is a trading-calendar import, not a restricted observation. It is
  counted anyway, because the sealed text says "an import of the data-access layer" and
  `stockedge100.data` **is** the data-access layer. Narrowing the marker list to exclude it would be
  editing the predicate to improve the number.

**Two implementations of P5 exist and they report different numbers.** The table above is the package
builder's sweep and reads 2. The sealer's own function,
`reporting/stage4_preregistration.py::_stage_4_modules_touching_restricted_data`, reads **1** — and it
is that function the failing marker test calls, which is why §12 records the test as reporting 1. The
builder calls the frozen function directly rather than restating its number, so the two cannot drift:
both counts, the one-file difference between them, and the cause are in
`contamination_predicates.stage_4_modules_touching_restricted_data_or_a_broker` of the decision
record.

The cause is that the seal's prose and the seal's code are not the same predicate. The prose says "a
call to a dataset loader" without enumerating the loaders; the frozen code enumerates them in a
literal `LOADER_CALLS` frozenset written before the evaluator existed, so it cannot name
`load_validation_series`, and its `DATA_LAYER_MODULES` tuple is narrower than the builder's for the
same reason. The single module the builder sees and the frozen function does not is
`reporting/stage4_evidence.py`.

Neither was edited to agree with the other. Widening the frozen function after a validation read is
the post-seal edit `post_seal_defect_rule` forbids; narrowing the builder's sweep to match would
suppress a real loader call the sealed prose plainly covers. The wider count is reported as the
measurement, the frozen count as the reference, and both appear in the package. Nothing turns on the
choice: neither reading is 0, so `S4-CONFLICT-7` stands either way, and no Gate 4 condition is
measured by P5.

The package builder is itself a `stage4`-named module and therefore inside the predicate's scope. Its
own `URL_SCHEMES` marker table is composed at import time rather than written out, so the module
implementing P5 does not trip P5 — the same convention the sealer adopted after its first dry-run
failed exactly that way, pinned by
`test_the_url_marker_table_is_composed_so_the_predicate_does_not_flag_itself`. A second convention for
the same problem one stage later would have been the defect, not the fix.

Four repairs were available and every one was refused:

- **Renaming the evaluator out of the `stage4` path** would drop the count to 0 while the dataset load
  continued to happen. That hides a real load from a predicate designed to find it, and it is
  foreclosed anyway: predicate P1 names the same path substring to count Stage 4 evaluator modules, so
  the rename would corrupt a second sealed measurement to flatter the first.
- **Weakening, skipping, `xfail`-ing or deleting the test** that asserts the sealed value is forbidden
  outright.
- **Editing the seal** to narrow the predicate to its stated purpose would be a change to a sealed
  specification made with validation results in hand. `post_seal_defect_rule.after_a_validation_read`
  is explicit that this is forbidden regardless of intent and that its outcome would be INVALIDATED.
- **Restructuring the evaluator** so the loader is called from a differently named module is the
  rename in another costume.

So the marker test fails, deliberately and visibly, and is reported as a failure in §12 rather than
made to pass. `S4-CONFLICT-7` does not affect any Gate 4 condition: `S4-C7` is measured by digest
recomputation and run-record counting, not by P5, and every one of those clauses is met.

One consequence is worth stating plainly for whoever writes the next sealed predicate. P5 was sealed
as a count that must equal a constant, but the thing it protects — no reach to a broker, no reach to
restricted data outside the authorized window — is not a count. A predicate written as
"resolve every hit to a named cause, and assert no hit is of the forbidden kind" would have survived
its own authorization intact; a predicate written as `count == 0` could not, because the seal
authorized the very work that makes the count nonzero. That is a defect in the predicate's *form*,
disclosed here, and it is not repaired in this session: the seal is not editable after a validation
read.

## 11. Limitations

- **The verdict is a fail, and the evidence for the five met conditions is correspondingly thin.**
  Total return of 2.15% over three years, 41 closed trades, and a stressed-cost return of 15 basis
  points describe a strategy that barely traded and barely moved. `S4-C3` is met at 3.16% against a
  15% ceiling because the equity curve had almost no amplitude, not because a drawdown was survived.
  `S4-C5` is met by a margin that a single additional round trip could erase. None of this changes the
  verdict — a fail is a fail on `S4-C2` and `S4-C6` alone — but it should not be read as "close".
- **One symbol.** The universe is `["SPY"]`. Every figure above is a single-instrument result and
  carries no cross-sectional evidence whatever.
- **One representative, one read, one parameterisation.** The gate saw one candidate on one window
  once. It says nothing about `C1`, and nothing about `C2` on any other period.
- **The cash rate is 0.00%**, sealed and labelled conservative. Sharpe is computed against it. A
  realistic positive cash rate over 2021–2024 would lower the measured Sharpe further, not raise it.
- **`S4-CONFLICT-5`'s degeneration stands.** "Walk-forward" here means twelve contiguous out-of-sample
  quarters with no re-estimation, because the representative estimates nothing. The fold stability
  measurement is therefore weaker than the constitutional phrase suggests.
- **The validation window is now spent.** It has been read once, which is all the design permits.
- **No test can cover this decision package**, because `tests/**/*.py` is inside the `repo_state_id`
  patterns and adding one would invalidate the digest it would assert. The package is verified by
  recomputation, recorded in §12 and in the decision record.

## 12. Tests

The Stage 0 suite of 27 tests is a permanent regression floor and later stages add to it and never
subtract. The floor stood at **708** collected after the Stage 4 pre-registration session and stands
at **837** after this one. Every pre-existing file collects exactly what it collected before. No test
was weakened, skipped, `xfail`-ed or deleted.

Full-suite result: **836 passed, 1 failed, 837 collected.** The single failure is
`test_no_stage_4_module_can_reach_restricted_data_or_a_broker`, the `S4-CONFLICT-7` marker test
described in §10. It asserts the sealed P5 value of 0 and reports 1. It is left failing on purpose:
it is the disclosure mechanism for a conflict that cannot be repaired without either hiding a real
dataset load or editing a seal after a validation read.

The 1 this test reports and the 2 in §10's table are the same predicate measured by two
implementations — the frozen one this test calls, and the package builder's wider reading of the
sealed prose. §10 gives the one-module difference and the reason for it. Both counts are in the
decision record; neither implementation was edited to agree with the other.

The **129** tests added by this session — 92 in `test_stage4_evaluation.py` and 37 in
`test_stage4_evidence.py` — cover, before any validation observation was loaded: the two exact
registered run identifiers; all twelve fold boundaries by date and against synthetic series; the zero
training folds; base and stressed cost treatment and the sealed multiplier binding; all seven Gate 4
conditions asserted `MET` on satisfying evidence and `NOT_MET` on non-satisfying evidence; the exact
threshold boundaries approached from both sides; the conjunction rule, including that one `NOT_MET`
rejects, that `NOT_EVALUABLE` is never a pass, and that `NOT_APPLICABLE_BY_CONDITION_TEXT` is
satisfied without being met; missing, `NOT_RUN` and `UNKNOWN` handling; both verdict tokens derived
from the sealed `verdict_token_derivation` against synthetic evidence rather than from literals; the
thirteen-artifact invariance rule including a tampered-digest injection; that holdout access fails
closed; that no broker path exists; and deterministic serialisation and the manifest self-reference
policy.

Detail, including the per-file breakdown and the pytest capture, is in
`reports/stage4/STAGE_4_VALIDATION_TEST_SUMMARY.md` and
`reports/stage4/pytest_stage4_evaluation_output.txt`.

## 13. Defects found and corrected before the validation read

Every defect below was found by the out-of-tree dry run described in `CLAUDE.md`, corrected, and
covered by a test **before** any validation observation was loaded. None was corrected after
performance became visible. `post_seal_defect_rule` distinguishes a defect in the sealed specification
— which may not be repaired after a read — from a defect in this session's own implementation of it,
which must be repaired to implement the frozen specification faithfully. All of these are the latter.

| Defect | Correction | Validation loaded at the time | Performance visible at the time |
| --- | --- | --- | --- |
| Run-id collision: two records generated inside the same second would have overwritten an append-only record | `unique_run_id()` re-reads the clock and raises rather than overwriting | no | no |
| `label_suffix_for` failed **open** on an unrecognised scenario, returning a usable label instead of refusing | changed to raise; covered in both directions | no | no |
| `fold_construction` missing its `method` key in the emitted evidence | key added from the sealed construction record | no | no |
| `ConditionVerdict.to_json()` missing its `summary` key | key added | no | no |
| `Decimal` values not JSON-serialisable | `_jsonable` conversion preserving full precision as strings | no | no |
| `threshold_cross_check` field duplicated in the emitted gate block | de-duplicated | no | no |

No defect was found after the read, and no sealed specification was altered at any point.

## 14. Reproducibility

| Field | Value |
| --- | --- |
| Evaluation command | recorded in `reports/stage4/STAGE_4_VALIDATION_EVIDENCE.json` `command` |
| Evaluation run record | `runs/SE100-R-20260814T143226Z.json` |
| Evidence digest | `3a2ea8d9875c150aef8346f507f75cde6c307da01bed8a24281e53195b2de7c2`, recomputed from the written file |
| Random seed | `null` — the representative uses no randomness; recording `null` rather than an unused integer keeps the field honest |
| Determinism | trade and equity digests recorded per run |
| Python | 3.10.6 |
| Serialisation | `json.dumps(..., indent=2, sort_keys=True)` with a trailing newline, per the sealed serialisation rule |

The `repo_state_id` at evaluation, the code hashes, the dataset hashes and the starting/ending tree
digests are in `reports/stage4/STAGE_4_VALIDATION.json` and the `runs/` records, not here, for the
reason given under the header table.

## 15. Authorization state — unchanged by this stage

| Item | State |
| --- | --- |
| Final holdout `2024-08-01`–`2026-07-31` | **SEALED**, sessions read `0` |
| `holdout_access_authorized` | `false` |
| Stage 5 / paper trading | **NOT_AUTHORIZED** |
| `paper_trading_authorized` | `false` |
| `shadow_live_authorized` | `false` |
| `alpaca_paper_trading` | `LOCKED` |
| `alpaca_live_trading` | `LOCKED` |
| `live_trading_authorized` | **`false`** |
| `capital_or_risk_expansion_authorized` | `false` |
| Broker connection attempted | `false` |
| Broker credential accessed | `false` |
| Orders generated | `0` |

No order-submitting code exists in this repository and none was written by this stage. StockEdge100 is
**not** trade-ready and is not described as trade-ready anywhere in this package.

Gate 4 did not pass, so it authorizes nothing further. Even a Gate 4 pass would have authorized only
the separately governed constitutional holdout gate, and only after explicit human authorization
recorded at that gate; it would not have conferred `ELIGIBLE_FOR_PAPER_TRADING`, which is Gate 5's
token and which Gate 4 may not emit.

## 16. Artifacts

This package comprises the human-readable report (this file), the machine-readable Gate 4 decision
record, the validation evidence file carrying both runs and all twelve folds, the per-condition
verdicts, the test summary, the pytest capture, the artifact manifest, the SHA-256 checksum record,
and the append-only `runs/` reproducibility record. The manifest excludes its own entry, because
nothing hashes itself; the surrounding `.sha256` record covers it instead. Filenames and digests are
in the manifest.

`reports/` and `runs/` lie outside the `repo_state_id` patterns, so writing them does not perturb the
tree digest. `governance/*.md` does not, which is why this file was finished before the package was
built and nothing tracked was touched afterwards.

---

**Verdict: `FAIL — STAGE_4_STRATEGY_REJECTED_IN_VALIDATION`.** Gate 4 is not passed. The holdout
stays sealed. Stage 5 is not authorized and is not pre-registered. `live_trading_authorized` is
`false`.
