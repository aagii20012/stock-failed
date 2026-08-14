# Stage 3 Attempt 2 design-session test summary

Command: `cd stockedge100 && python -m pytest tests/unit/test_stage0_governance.py tests/unit/test_stage1_preregistration.py tests/unit/test_stage3_attempt2_preregistration.py -q`
Raw output: [pytest_stage3_attempt2_output.txt](pytest_stage3_attempt2_output.txt)

**115 passed, 0 failed, 0 skipped.**

The new file alone: `cd stockedge100 && python -m pytest tests/unit/test_stage3_attempt2_preregistration.py -q`
→ **71 passed, 0 failed, 0 skipped.**

## Why the broad command was not run

This session may not run a backtest, simulation, parameter sweep, or performance calculation, and may
not load market observations for performance analysis. `python -m pytest tests -q` would do both:

- `tests/integration/test_stage1_data_foundation.py:73` reads every normalised CSV in the dataset.
- `tests/integration/test_stage2_backtest.py:373` calls `load_dataset(("SPY",))` and drives the
  engine over it.

So the recorded command is a three-file selection that reads only governance documents, `config/`
JSON, `src/` text, `runs/` records, and trees the tests build themselves under `tmp_path`. No test in
the selection opens a price file, computes a return, or touches the validation or holdout windows.

The two pre-existing files in the selection are there as controls rather than as coverage: Stage 0's
27 tests re-verify the constitution and its freeze record, and Stage 1's 17 re-verify a
pre-registration seal of the same shape as the one added here, so a failure in the new 71 is
attributable to the new file and not to a moved artifact underneath it.

## The floor did not fall

`python -m pytest tests --collect-only -q` → **460 tests collected in 1.15s**. Collection imports
every test module but executes no test body; neither integration file loads data at import time
(their module-level statements are string and date constants only), so the count is obtained without
running the reads the paragraph above forbids.

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
| `tests/unit/test_stage3_attempt2_preregistration.py` | 71 | The Attempt 2 seal, its four contamination predicates in both directions, Attempt 1 immutability, the unchanged Gate 3 criteria, candidate completeness, the adaptation disclosure, the partition and authorisation state, and MD/JSON agreement. |
| **Total** | **460** | |

Stage 0 contributed 27, Stage 1 brought the total to 140, Stage 2 to 273, Stage 3 Attempt 1 to 389.
This design session adds **71**. Nothing was weakened, skipped, `xfail`ed, or removed; the floor only
rises.

Because the whole suite was deliberately not executed, "**Unmodified.**" above is asserted by digest
rather than by a green run. Every `tests/**/*.py` entry in the Attempt 1 run record
`runs/SE100-R-20260810T101622Z.json` was recomputed against disk: **11 recorded, 11 unchanged, 0
changed, 0 missing**, against 12 live files — the one addition being
`tests/unit/test_stage3_attempt2_preregistration.py`. A weakened or deleted test would appear as a
changed or missing entry there, so the claim is falsifiable without running the reads that are out of
scope.

`tests/conftest.py` was not touched; it is one of the 11 verified entries. Every fixture the new file
needs is defined locally in it. No test writes into `data/`, `governance/`, `config/`, or `reports/` —
the contamination tests build a synthetic tree under `tmp_path` and `monkeypatch` the sealing
program's five module-level path constants (`PROJECT_ROOT`, `SRC_DIR`, `STRATEGY_DIR`, `REPORTS_DIR`,
`RUNS_DIR`) onto it.

## The new file

**Three clean controls first.** The three sealed artifacts are present; the seal parses and declares
itself sealed; and a synthetic candidate whose seven condition verdicts are all satisfied *is*
admissible under the sealed rule. The third matters most: Attempt 1 admitted nothing, and a rule that
admits nothing would look identical to a correct one without a control that requires it to admit
something. A failure below these three is attributable to the assertion rather than to a moved
artifact or an evaluator that refuses everything.

**The seal.** The three digests the seal covers are pinned as literals in the test file, written out
independently of `STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256`, so rewriting an artifact *and* its
checksum record together still fails the suite. The record is verified from the project root, because
Stage 1's, Stage 2's and Stage 3's pre-registration records all use project-root-relative paths — only
`STAGE_0_FREEZE.sha256` and `STAGE_1_FREEZE.sha256` use bare filenames. The record covers the seal
JSON and does not name itself, because nothing hashes itself. The seal carries no 64-hex string other
than the digests it is permitted to quote, and the Markdown document carries none at all; both
predicates search for the **value**, not for a field name, since the prose is expected to name
`repo_state_id` when it says where the value lives. The declared UTC timestamp is asserted to parse
and to agree with the run record's, so a hand-typed time would fail.

**The four contamination predicates, in both directions.** Attempt 1 could prove its ordering with two
counts of zero over `strategies/` and `reports/`. Both directories are now legitimately non-empty and
may not be emptied, so Attempt 2 proves it with four narrower predicates plus an immutability check —
and a predicate hard-wired to return nothing would also have recorded four zeros. Each is therefore
tested on a synthetic tree that must read empty and then on planted contamination that must be
caught:

| Predicate | Must not catch | Must catch |
| --- | --- | --- |
| `attempt_2_strategy_modules` | the sealing program itself, which lives under `src/stockedge100/reporting/` and is exempt by the sealed definition | a `.py` path anywhere else under `src/stockedge100/` containing `attempt2` |
| `modules_naming_an_attempt_2_candidate` | an Attempt 1 family module | any Attempt 2 candidate id appearing inside an existing `strategies/` module |
| `attempt_2_report_artifacts` | `reports/stage3/` | any file under an `attempt2` path in `reports/` |
| `attempt_2_run_records` | the Attempt 1 run record | `ATTEMPT_2`, or a candidate id, in any `runs/` record |

The `reporting/` exemption is asserted to be a narrowing rather than a blanket skip: a second
`attempt2`-named file under `reporting/` is also exempt, while the `strategies/` hit is still caught.
A parametrised test then forces each predicate non-empty in turn and requires `sealer.build()` to
return **3** with neither the JSON nor the `.sha256` written, so the predicates are wired to refusal
and not merely reported. Running `build()` against the real, already-sealed tree returns **2** —
refusal because the record exists — which is the guard that makes the seal unrepeatable.

**Attempt 1 immutability.** Both `governance/STAGE_3_PREREGISTRATION.sha256` and
`reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256` verify entry-for-entry from the project root, and
the Attempt 2 seal's `supersedes` is `None` while its `relationship_to_attempt_1` opens "None of
Attempt 1 is modified, superseded, re-run, or repaired." and names `SE100-GOV-0006` explicitly.

**Gate 3 unchanged.** `config/stage3_gate_criteria.json` is pinned by digest independently of the
binding file, so a criteria change would fail here even if the binding were updated to match. Every
`conditions_adopted` value starts with `unchanged`; the maximum-drawdown ceiling is asserted to still
be 15% on the same session-close equity series; the two conditions carrying a re-derivation
annotation (S3-C6, S3-C7) are required to be exactly the two with entries in `rederivations`, and each
entry is required to quote the sealed text it re-derives, say why the re-derivation is necessary, and
state what it leaves unchanged. The admissibility rule is applied from the sealed
`satisfied_definition` rather than from a literal — conjunctive within a candidate, disjunctive across
candidates, with `NOT_APPLICABLE_BY_CONDITION_TEXT` satisfied without being met and `NOT_MET`,
`NOT_EVALUABLE`, `NOT_RUN`, `UNKNOWN` and a missing verdict all not satisfied. The combination rule is
tested in both directions on synthetic verdict tables; no real result is read, because none exists.

**Candidate completeness.** Three unique ids, each from an authorised family, each specifying all 31
required fields, with variant counts inside the declared caps and the cumulative
Attempt 1 + Attempt 2 experiment count arithmetically consistent. A candidate missing any one field
fails on its own line, so a later implementation session has nothing left to decide by inspecting
results.

**The adaptation is disclosed, not hidden.** Eleven required substrings of the joined disclosure are
asserted individually — including "adaptive second attempt", "All six Attempt 1 candidates breached
the 15% maximum-drawdown ceiling", "no longer pristine", "Researcher degrees of freedom are higher",
"false-discovery risk", "cumulative count across both attempts", "independent confirmation", "not
evidence of a trading edge", and "not concealed behind a new strategy identifier" — so removing any
single disclosure fails its own assertion rather than being absorbed by a loose containment check.
Development data is separately asserted to be declared no longer pristine, and the cumulative
experiment count is asserted to span both attempts.

**Partitions and the window guard.** The permitted partition is `development window only, bounds read
from governance/STAGE_1_HOLDOUT_LOCK.json`; the binding's authorised windows are `["development"]`
with validation `LOCKED` and holdout `SEALED`, and the seal repeats all three. The prohibited list is
required to name validation, holdout, and `AAPL` — the Stage 1 split fixture, which is not a universe
member and is also in `excluded_symbols`. The guard itself is exercised structurally on **dates only,
reading no observation**: a session one day past the development window's end is asserted not to be
contained and to raise `WindowViolation`. `governance/STAGE_1_HOLDOUT_LOCK.json` is read and asserted
still `LOCKED` / `SEALED`.

**Authorisation.** `stage_4_authorized`, `paper_trading_authorized`, `shadow_live_authorized` and
`live_trading_authorized` are each asserted `False`, in the seal and in the protocol.
`strategy_research_authorized_for` must name "three candidates sealed here" and end "Nothing else.".
Stage 4's continuing prohibition carries its conditions in both files, and at least eight explicit
non-authorisations are required. What happens on a bad outcome is asserted to be fixed before any
outcome exists: the attempt-level abandonment rule, the missing/invalid-data rule, the post-seal
defect rule, the partial/failed-run rule, the no-retuning rule and the reproducibility requirements
must all be non-empty, and the last of these must address seeds even though nothing in the design is
stochastic.

**Design decisions that must be settled prospectively.** Neighbours are asserted diagnostic and never
promotable to representative; a shutdown breach liquidates and never re-arms; no result may be re-run
after a valid completed evaluation; the permitted parameter grid is a boundary rather than a search
space; each excluded Attempt 1 family carries a prospective reason; and no candidate combines rejected
families. The one new indicator declares its own arithmetic in the protocol text.

**MD/JSON agreement.** The document must name every candidate id and the attempt id, state the same
research question as the protocol after prose normalisation, name the risk-architecture id together
with every `RA1-n` mechanism key the protocol specifies, and reproduce the three Attempt 1 closed-trade
counts that the family-exclusion reasoning relies on — the only Attempt 1 numbers carried forward into
Attempt 2's design. The human-readable and machine-readable halves of the seal therefore cannot drift
apart on any of those.

## What the suite deliberately does not cover

**The decision package.** `tests/**/*.py` is one of the patterns `repo_state_id` is computed over, so
a test asserting that digest would invalidate the value it asserts the moment it was written. The
package is verified by re-running the recomputation, not by a test.

**Anything about whether the Attempt 2 candidates work.** No strategy module exists for them, by
design and by the seal's own evidence. Nothing here measures a return, a drawdown, or a trade count;
the suite tests that the specification is complete, unchanged where it must be unchanged, and sealed
before implementation — not that it is profitable.
