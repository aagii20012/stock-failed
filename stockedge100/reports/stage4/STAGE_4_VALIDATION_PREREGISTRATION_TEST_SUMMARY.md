# Stage 4 validation pre-registration test summary

Command: `cd stockedge100 && python -m pytest tests/unit/test_stage0_governance.py tests/unit/test_stage1_preregistration.py tests/unit/test_stage3_attempt2_preregistration.py tests/unit/test_stage4_preregistration.py -q`
Raw output: [pytest_stage4_output.txt](pytest_stage4_output.txt)

**263 passed, 0 failed, 0 skipped.**

The new file alone: `cd stockedge100 && python -m pytest tests/unit/test_stage4_preregistration.py -q`
→ **148 passed, 0 failed, 0 skipped.**

## Why the broad command was not run

This session may not read the validation dataset, may not access the final holdout, and may not run a
backtest or compute a performance figure. `python -m pytest tests -q` would violate all three:

- `tests/integration/test_stage1_data_foundation.py:73` reads every normalised CSV in the dataset.
- `tests/integration/test_stage2_backtest.py:373` calls `load_dataset(("SPY",))` and drives the
  engine over it.
- `tests/integration/test_stage3_attempt2_backtest.py` runs the Attempt 2 candidates.

The prohibition was checked **before** any test command ran, not inferred afterwards. So the recorded
command is a four-file selection that reads only governance documents, `config/` JSON, `src/` text,
`runs/` records, and trees the tests build themselves under `tmp_path`. **No test in the selection
opens a price file, computes a return, or touches the validation or holdout windows.**

The three pre-existing files are controls rather than coverage. Stage 0's 27 re-verify the
constitution and its freeze record; Stage 1's 17 and Stage 3 Attempt 2's 71 re-verify pre-registration
seals of the same shape as the one added here. A failure among the new 148 is therefore attributable
to the new file and not to a moved artifact underneath it.

## The floor did not fall

`python -m pytest tests --collect-only -q` → **708 tests collected in 3.93s**. Collection imports
every test module but executes no test body, and no integration module loads data at import time, so
the count is obtained without performing the reads the section above forbids.

| File | Tests | What it establishes |
| --- | ---: | --- |
| `tests/unit/test_stage0_governance.py` | 27 | Stage 0 regression floor. **Unmodified.** |
| `tests/unit/test_stage1_calendar_partition.py` | 34 | Stage 1 floor. **Unmodified.** |
| `tests/unit/test_stage1_preregistration.py` | 17 | Stage 1 floor. **Unmodified.** |
| `tests/integration/test_stage1_data_foundation.py` | 33 | Stage 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage1_adversarial.py` | 29 | Stage 1 floor. **Unmodified.** |
| `tests/unit/test_stage2_engine.py` | 54 | Stage 2 floor. **Unmodified.** |
| `tests/adversarial/test_stage2_defects.py` | 42 | Stage 2 floor. **Unmodified.** |
| `tests/integration/test_stage2_backtest.py` | 37 | Stage 2 floor. **Unmodified.** |
| `tests/unit/test_stage3_strategies.py` | 69 | Stage 3 Attempt 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage3_defects.py` | 47 | Stage 3 Attempt 1 floor. **Unmodified.** |
| `tests/unit/test_stage3_attempt2_preregistration.py` | 71 | Stage 3 Attempt 2 design floor. **Unmodified.** |
| `tests/unit/test_stage3_attempt2_implementation.py` | 51 | Stage 3 Attempt 2 evaluation floor. **Unmodified.** |
| `tests/adversarial/test_stage3_attempt2_defects.py` | 30 | Stage 3 Attempt 2 evaluation floor. **Unmodified.** |
| `tests/integration/test_stage3_attempt2_backtest.py` | 19 | Stage 3 Attempt 2 evaluation floor. **Unmodified.** |
| `tests/unit/test_stage4_preregistration.py` | 148 | The Stage 4 seal, the representative selection as a rule, the seven extracted Gate 4 conditions in both directions, the authored fold construction, the six sealing predicates in both directions, and the fail-closed proof that no validation observation is reachable. |
| **Total** | **708** | |

Stage 0 contributed 27, Stage 1 brought the total to 140, Stage 2 to 273, Stage 3 Attempt 1 to 389,
the Attempt 2 design session to 460, and the Attempt 2 implementation and evaluation session to 560.
This pre-registration session adds **148**. Nothing was weakened, skipped, `xfail`ed, or removed; the
floor only rises.

Because the whole suite was deliberately not executed, "**Unmodified.**" above is asserted **by
digest** rather than by a green run. Every `tests/**/*.py` entry in **both** Gate 3 Attempt 2 run
records — `runs/SE100-R-20260813T120406Z.json` (design) and `runs/SE100-R-20260813T140121Z.json`
(evaluation) — was recomputed against disk:

| Measure | Value |
| --- | ---: |
| Entries recorded across both run records | 15 |
| Unchanged against disk | 15 |
| Changed | 0 |
| Missing | 0 |
| Live `tests/**/*.py` files | 16 |
| Additions (this session) | 1 — `tests/unit/test_stage4_preregistration.py` |

A weakened or deleted test appears there as a changed or missing entry, so "the floor did not fall"
stays falsifiable without running the reads that are out of scope. Where a file is recorded in both
run records, the digest is required to match **both** recorded values, so a change made between the
two Gate 3 sessions would also surface.

`tests/conftest.py` is one of the 15 verified entries and was not touched; it is hashed in the Stage 0
artifact manifest, and every fixture the new file needs is defined locally in it.

No test wrote outside `tmp_path`. `runs/` held exactly 15 records after the run — the same 15 that
existed before it — and `reports/` held six stage directories, the sixth being `reports/stage4/`,
which the operator created with `mkdir` to hold this capture and which no test writes into. That sixth
directory is the `stage_4_report_artifacts` movement disclosed in
[STAGE_4_VALIDATION_PREREGISTRATION_REPORT.md](../../governance/STAGE_4_VALIDATION_PREREGISTRATION_REPORT.md)
§16, not a test escaping its sandbox. The contamination tests build a synthetic tree under `tmp_path`
and `monkeypatch` the sealing program's module-level path constants onto it.

## The new file

**Four clean controls first.** The four pre-registered files and the seal are on disk; the seal parses
and declares itself `SEALED` with `supersedes` `None`; a synthetic evidence table in which all seven
Gate 4 conditions are `MET` **does** yield the sealed pass token; and the frozen development window
still admits its own last session. The third matters most. A gate predicate hard-wired to fail would
be indistinguishable from a correct one without it — and this stage's own disclosure says a Gate 4
`FAIL` is a likely outcome, so that is exactly the failure mode that would otherwise go unnoticed. A
failure below these four is attributable to the assertion rather than to a moved artifact or an
evaluator that refuses everything.

**The seal.** The five digests `governance/STAGE_4_PREREGISTRATION.sha256` covers are pinned as
literals in the test file, written out **independently** of that record, so rewriting an artifact
together with its checksum record still fails this module. The record is verified from the project
root, because it uses project-root-relative paths — only `STAGE_0_FREEZE.sha256` and
`STAGE_1_FREEZE.sha256` use bare filenames. It covers five files and does not name itself, because
nothing hashes itself. A 64-hex sweep over the seal resolves every hit back to a file on disk and
requires none of them to be a tree digest or the file's own; `repo_state_id` is absent from the seal
as a value, and the seal's declared timestamp is asserted to parse and to agree with the run record's,
so a hand-typed time would fail.

**The selection is exercised as a rule, not as a conclusion.** The eligible set is required to be
exactly the two Gate 3 admitted candidates; C3 is required to be excluded *and* recorded as not
reconsidered; the search for a mandatory constitutional selection rule is required to have returned
empty with its method recorded; and the one constraint that did apply — the prohibition on promoting a
robustness neighbour — is required to be named. The rule is asserted return-blind by reading
`reads_no_return` and `reads_no_risk_adjusted_metric` from the sealed artifact, each of its five
provenance terms is required to name a frozen or sealed artifact and to have every digest it cites
resolve to a live file, and the screen arithmetic is **re-derived from `declared_runs`** — C1
two trips including its `#PRIMARY#STRESS` run, C2 zero — rather than read back from `screen_results`.
Each candidate's recorded `shutdown_trip_count`, `declared_run_count` and `screen_result` is required
to equal the value re-derived from its own `declared_runs` list, so a miscounted screen fails on its
own line; the survivor set is then required to be exactly the representative, the eliminated set
exactly C1, `survivor_count` 1, `rule_decides` `true` and `human_selection_required` `false`.

**Gate 4, in both directions.** Each of the seven conditions is required to quote its frozen phrase
from constitution lines 193–203. Each sealed threshold predicate is evaluated at its exact boundary in
**both** directions — a Sharpe of exactly `0.50` passes and `0.4999999` fails, a drawdown of exactly
`0.15` passes and `0.1500001` fails, a profit factor of exactly `1.15` passes and `1.1499999` fails, a
total return of `0` fails where `0.0000001` passes, and 9 of 12 folds passes where 8 of 12 fails.
Fewer than twelve completed folds is `NOT_EVALUABLE` and not a pass, and a fold return of exactly zero
is not positive. The strict/inclusive difference against Gate 5 is asserted preserved, not harmonised.
The verdict tokens are derived from the constitution's JSON companion rather than pinned as literals,
and each of `NOT_MET`, `NOT_EVALUABLE`, `NOT_RUN` and `UNKNOWN` is shown to fail the gate, as is a
missing condition. The twelve folds are recomputed from the frozen partition boundaries with
day-level adjacency and three-month arithmetic.

**The fail-closed section proves the pre-registration path cannot reach a restricted observation, and
it does so on dates alone** — a test that proves a module cannot read validation data may not read one
either. A `MarketView` cannot be constructed at a validation `as_of` even with no series supplied,
because the refusal happens on the date before any observation is involved. The development window
refuses validation and holdout dates; `window_named()` bounds equal the lock partition with
`holdout_state == "SEALED"`; the AST predicate reads empty over the live tree, and the sealing program
is itself inside that predicate's scope.

**The six sealing predicates, in both directions.** Attempt 1 could prove its ordering by counting
`strategies/` to zero. That is no longer available, so this seal uses six narrower predicates, two of
them **AST** questions rather than text searches, because a text search over either module would match
the words of its own predicate definition. Each predicate is exercised on a synthetic tree that must
read empty and then on planted contamination that must be caught. A parametrised test forces each of
five predicates non-empty in turn and requires the sealing program to return **3** with **nothing
written**, and each remaining refusal exit — 2, 4, 5, 6, 7, 8 — has its own test. One row of the AST
table is a deliberate control: a URL assembled at runtime is not claimed as a violation. And one test
exists because the sealing program's first dry-run failed on it — the URL marker table is **composed**
from schemes rather than written literally, so the predicate does not flag the file that defines it.

## What the suite deliberately does not cover

**The decision package.** `tests/**/*.py` is one of the patterns `repo_state_id` is computed over, so
a test asserting that digest would invalidate the value it asserts the moment it was written. The
package is verified by re-running the recomputation, not by a test. The builder was instead dry-run
out-of-tree with `build_stage_package` monkeypatched before it was allowed to write anything, and its
guard was exercised in both directions: an unmet seal condition flips the verdict to `BLOCKED` and
still writes the package, because a design session may legitimately end blocked and the constitution
keeps negative results on disk; while a gate row that is not `NOT_RUN`, a verdict borrowing either
Gate 4 token, and a `gate_passed` of `True` each refuse to write at all.

**Anything about whether the representative works on validation data.** No Stage 4 evaluator exists,
no validation observation was read, and no return, drawdown, trade count, fold return or equity value
for the validation window exists anywhere in this tree. This suite tests that the specification is
complete, extracted rather than invented, sealed before any evaluation, and unable to reach a
restricted observation — not that it is profitable.
