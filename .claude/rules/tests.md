---
paths: stockedge100/tests/**
---

# Test suite conventions

The suite is evidence, not scaffolding. It is the only thing standing between a sealed rule and a
rule that quietly became whatever the data needed it to be.

## The floor only rises

Stage 0 contributed 27 tests; Stage 1 brought the total to 140, Stage 2 to 273, Stage 3 Attempt 1 to
389, the Stage 3 Attempt 2 design session to 460, and the Attempt 2 implementation and evaluation
session to **560** (51 unit + 30 adversarial + 19 integration). A stage adds and never subtracts.
Never weaken, skip, `xfail`, or delete a test to make a gate pass. If a frozen test looks wrong,
that is a blocker to report — file an erratum, escalate, do not repair it in place.

`tests/conftest.py` is hashed in the Stage 0 artifact manifest. Leave it alone. Define a stage's
fixtures locally in that stage's own test module instead.

## When the session may not run the whole suite

Some sessions are forbidden to load market observations or compute performance — a design or
pre-registration session, for instance. `python -m pytest tests -q` violates that: 
[test_stage1_data_foundation.py:73](stockedge100/tests/integration/test_stage1_data_foundation.py#L73)
reads every normalised CSV and
[test_stage2_backtest.py:373](stockedge100/tests/integration/test_stage2_backtest.py#L373) calls
`load_dataset(("SPY",))` and drives the engine over it. Run a named selection instead, and include one
or two **pre-existing** files as controls so a failure is attributable to the new module rather than to
a moved artifact underneath it:

```bash
cd stockedge100 && python -m pytest tests/unit/test_stage0_governance.py tests/unit/test_stage1_preregistration.py tests/unit/test_stage3_attempt2_preregistration.py -q
```

`pytest tests --collect-only -q` is safe and gives the floor count: collection imports every module but
executes no body, and neither integration file loads data at import time.

Then assert the floor **by digest** rather than by a green run — recompute every `tests/**/*.py` entry
in the previous stage's run record against disk and report `recorded / unchanged / changed / missing`
against the live file count. A weakened or deleted test shows up as changed or missing, so "the floor
did not fall" stays falsifiable without running the reads that are out of scope. Say plainly in the
test summary that this is what happened and why.

## Nothing escapes tmp_path

No test may write into `data/`, `governance/`, `config/`, or `reports/`. Path constants are
module-level and resolved at call time, so redirect them with `monkeypatch.setattr` on the module
object — an autouse fixture is the reliable shape:

```python
@pytest.fixture(autouse=True)
def isolated_quarantine(monkeypatch, tmp_path):
    monkeypatch.setattr(quarantine_module, "QUARANTINE_DIR", tmp_path / "quarantine")
```

The universe builder needs the same treatment for `GOVERNANCE`, `UNIVERSE_PATH`,
`HOLDOUT_LOCK_PATH`, and `FREEZE_RECORD_PATH` before any rebuild test runs.

## Adversarial coverage is mandatory, not optional

A validation battery that has only ever seen clean data is untested. Every guard gets a test that
injects exactly one defect and asserts that guard reports it. Put two or three clean controls at the
top of the file — a clean series, a correctly applied split, a correctly applied dividend — so a
failure below them is attributable to the injected defect and not to the harness.

Assert the **sealed** severity, not the one that reads better. A dividend that does not reconcile is
`WARN` because the pre-registration says `WARN`; do not upgrade it to `FAIL` in the assertion because
it feels more rigorous.

Structural guards deserve tests as much as statistical ones: a window violation must raise, a
holdout lock with different boundaries must refuse to be overwritten, and a tampered sealed byte
must raise in the loader.

**Clean controls matter most when the stage fails.** Stage 3 rejected all six candidates and caught
47 injected defects. Without a control asserting that a synthetic candidate meeting every threshold
*is* admitted with stage verdict `PASS`, that outcome is indistinguishable from an evaluator that
rejects everything.

## Gate predicates get tested in both directions

Assert every condition `MET` on evidence that satisfies it **and** `NOT_MET` on evidence that does
not. A predicate hard-wired to return `NOT_MET` passes a one-sided test — and on a stage whose real
data fails everything, one-sided is all you would ever notice. Test the combination rule the same
way: one `NOT_MET` rejects the whole candidate, `NOT_EVALUABLE` is never a pass, and
`NOT_APPLICABLE_BY_CONDITION_TEXT` is satisfied without being met. Take the verdict tokens from the
sealed `verdict_token_derivation`, never from a literal in the test.

## Assert what the artifact says

When a test reads a frozen or sealed artifact, assert against its actual wording, not against the
phrasing you assumed it used. A Stage 1 test failed asserting `"DEVELOPMENT" in restriction` when the
sealed spec reads "No eligibility measurement may read validation-window or holdout-window data".
The test was wrong; the artifact was not. Fix the test.

Digests pinned in tests are written out **independently** of the freeze record, so that rewriting an
artifact and its freeze record together still fails the suite.

## Expected warnings

If a guard legitimately produces a numeric warning on adversarial input (divide-by-zero on a
non-positive adjusted close, say), mark the test and explain why in its docstring:

```python
@pytest.mark.filterwarnings("ignore:divide by zero:RuntimeWarning")
```

Never edit the module to silence it. The warning is the guard doing arithmetic on the garbage it was
handed; the assertion is that it still returns `FAIL`.
