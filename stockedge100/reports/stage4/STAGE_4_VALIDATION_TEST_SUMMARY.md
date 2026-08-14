# Stage 4 validation evaluation — test summary

`cd stockedge100 && python -m pytest tests -q`, captured verbatim in
[`pytest_stage4_evaluation_output.txt`](pytest_stage4_evaluation_output.txt).

| Result | Count |
| --- | --- |
| passed | 836 |
| failed | 1 |
| skipped | 0 |
| collected | 837 |

The run exits **1**. That is not a defect and it is not a regression. It is one deliberate failure,
described below and in §10 and §12 of
[`STAGE_4_VALIDATION_REPORT.md`](../../governance/STAGE_4_VALIDATION_REPORT.md).

## The one failure is a disclosure, not a defect

```
FAILED tests/unit/test_stage4_preregistration.py::test_no_stage_4_module_can_reach_restricted_data_or_a_broker
E   AssertionError: assert ['src/stocked...r import ...'] == []
E     Left contains one more item: 'src/stockedge100/strategies/stage4_evaluation.py: call
E     load_dataset(), from stockedge100.backtest.dataset import load_dataset, from
E     stockedge100.data.calendar import ...'
```

This test asserts the sealed contamination predicate `stage_4_modules_touching_restricted_data_or_a_
broker` still measures **0**. It measures 1.

The predicate counts every `stage4`-named module under `src/` whose syntax tree calls a dataset
loader, imports the data-access layer, imports a network or broker package, reads an environment
variable, opens a connection, or carries a URL-scheme constant. Its sealed *purpose*, stated in the
same clause, is the fail-closed proof that **the pre-registration path** cannot read a restricted
observation or reach a broker. Its *mechanical scope* is wider than its purpose: it also covers the
evaluator that the pre-registration authorized. That evaluator must load a price series — that is the
whole of its job — so once it exists the predicate can never read 0 again. This is `S4-CONFLICT-7`.

The half of the predicate that guards against a broker, a network call, a credential read or a URL
**still measures 0**, and that is the half the safety claim rests on. Every hit on the data half is
resolved by name to a read the seal authorized, and the decision-package builder refuses to write a
package at all if any hit is left unresolved.

Four ways to make this test green were available and every one was refused: renaming the evaluator
out of the `stage4` path (hides a real dataset load from a predicate written to find it, and corrupts
predicate P1 as well); weakening, skipping, `xfail`-ing or deleting the test (forbidden outright);
editing the seal (forbidden after a validation read, regardless of intent); and restructuring the
evaluator so a differently named module holds the loader call (the rename in another costume). The
test is therefore left failing, visibly, as the disclosure mechanism.

Nothing in Gate 4 is measured by this predicate. `S4-C7`, the artifact-invariance condition, is
measured by digest recomputation over the sealed thirteen-artifact set and by run-record counting;
all thirteen digests recompute equal.

**Two implementations of the predicate exist and report different numbers.** The frozen sealer
function this test calls reports 1. The decision-package builder's wider reading of the sealed prose
reports 2 — it additionally sees `reporting/stage4_evidence.py`, whose `load_validation_series` call
the sealer's literal `LOADER_CALLS` frozenset cannot name because it was written before the evaluator
existed. Neither was edited to agree with the other; both counts are recorded in the decision record.
Neither is 0.

## The floor did not fall

`python -m pytest tests --collect-only -q` → **837 tests collected**.

| File | Collected | Status |
| --- | --- | --- |
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
| `tests/unit/test_stage4_preregistration.py` | 148 | Stage 4 pre-registration floor. **Unmodified** — 147 pass, 1 fails as described above. |
| `tests/unit/test_stage4_evaluation.py` | **92** | **Added by this session.** |
| `tests/unit/test_stage4_evidence.py` | **37** | **Added by this session.** |

Every pre-existing file collects exactly the count it collected at the Stage 4 pre-registration, whose
floor was 708. This session added 129 and removed none. The Stage 0 suite of 27 is intact.

## What this session's 129 tests cover

All of them were written and passing **before any validation observation was loaded**. The single
authorized read happened afterwards.

| Sealed rule | Covered by |
| --- | --- |
| The two exact registered run identifiers, and only those | run-label construction asserted against the sealed protocol strings; `label_suffix_for` raises on any unrecognised scenario rather than returning a usable label |
| Twelve fold boundaries | every start and end date asserted against the sealed `SE100-CFG-4002-WF1` construction, and independently against a synthetic calendar; contiguity, non-overlap, and containment inside the validation window |
| Zero training folds | asserted from the sealed declaration and from the constructed partition |
| Base and stressed cost treatment | the sealed 2.0 multiplier bound from disk, applied to the stressed run only, with the gating-condition split (`S4-C5` from stress, the rest from base) asserted |
| All seven Gate 4 conditions | each asserted `MET` on satisfying synthetic evidence and `NOT_MET` on non-satisfying synthetic evidence |
| Exact threshold boundaries | approached from both sides, on exact `Decimal` values, with no rounding before comparison — including Sharpe at exactly `0.50` and drawdown at exactly `0.15` |
| Conjunction logic | one `NOT_MET` rejects; `NOT_APPLICABLE_BY_CONDITION_TEXT` is satisfied without being met; aggregation is on satisfaction, not on `verdict == "MET"` |
| Missing / `NOT_RUN` / `UNKNOWN` / `NOT_EVALUABLE` | none is ever a pass; each is asserted separately |
| Both verdict tokens | derived from the sealed `verdict_token_derivation` against synthetic evidence, never restated as literals |
| Thirteen-artifact invariance | all thirteen recomputed, plus a tampered-digest injection that must be detected |
| Holdout access fails closed | any request for a date at or after the holdout start raises, and the raise is asserted, not the absence of a call |
| No broker path exists | an AST walk asserting no forbidden import root, no forbidden attribute access, and no URL-scheme constant |
| Deterministic serialisation and manifest policy | canonical JSON is stable across two runs at different timestamps; the manifest excludes its own entry |

## What no test can cover

No test can cover the decision package itself. `tests/**/*.py` is one of the `repo_state_id` patterns,
so a test asserting the package's `repo_state_id` would invalidate the value it asserts. The package
is verified by re-running the recomputation out of tree, not by a test.
