# Stage 3 (Generation 2, Attempt 2) test summary

Command: `cd stockedge100 && python -m pytest tests -q`
Raw output: [pytest_stage3_g2_attempt2_output.txt](pytest_stage3_g2_attempt2_output.txt)

**@@PASSED@@ passed, @@FAILED@@ failed, 0 skipped.**

The one failure is deliberate, pre-existing and inherited. It is not an Attempt 2 regression, it is
not weakened here, and it is not skipped.

## The failing test

```
FAILED @@FAILING@@
```

This is Generation 1's permanent red marker, recorded as `S4-CONFLICT-7` in the Stage 4
pre-registration package and inherited unchanged by Generation 2 Attempt 1 before it reached Attempt
2. `src/stockedge100/strategies/stage4_evaluation.py` imports `load_dataset` and the calendar module
— which it must, because a validation stage has to read data — and the test asserts that no Stage 4
module reaches restricted data at all. The two statements cannot both hold, and the conflict was
recorded rather than resolved by loosening the assertion.

Attempt 2 touches neither side of it. Editing the test would be weakening a test to make a gate look
cleaner, which the constitution forbids and this attempt does not need: the failure has nothing to do
with the Attempt 2 verdict, which is reached from the development evidence file and the sealed gate
criteria alone.

## Composition

@@TABLE_COMPOSITION@@

Attempt 1 left the floor at **@@PRIOR@@** tests. Attempt 2 adds **@@NEW@@**, all of them in one new
file, for a total of **@@TOTAL@@**. The new file is:

```
@@NEW_FILE@@
```

Every other file in the table is byte-identical to the state Attempt 1 left it in. That is re-hashed,
not asserted: Attempt 1's `STAGE_3_G2_ARTIFACT_MANIFEST.json` recorded a SHA-256 for each of the
**@@PRIOR_FILES_VERIFIED@@** `tests/**/*.py` files that existed when its package was built, every one
of them recomputes to its recorded digest now, and the new file above appears in that manifest not at
all. No test was edited, renamed, weakened, deleted or skipped; the red marker above is carried
forward rather than silenced; `tests/conftest.py` is untouched.

The floor is a one-way ratchet by constitution: later work adds to it and never subtracts. The
composition table above is generated from a real `pytest --collect-only -q` run grouped by file, not
transcribed, so a row cannot drift away from the suite it claims to describe.

## What the new file establishes

`config/generation_2/g2_rotation_ra1_protocol.json` declares nine required adversarial tests in its
own words, sealed before any of this code existed. Each is quoted below with the number of tests that
implement it, counted from the collected ids rather than asserted:

@@LIST_AT@@

That accounts for @@AT_ATTRIBUTED@@ of the @@NEW@@ tests. @@HARNESS_CLAUSE@@ the shared fixtures and
the independent replay the exposure assertions are built on — a test that the replay reconciles with
the engine it audits, without which the whole `AT-A` group could pass vacuously against a broken
engine.

Two properties of the file are worth stating explicitly, because they are what make the group
something other than a restatement of the implementation:

- **Every section opens with a control and closes with an injected defect.** The control establishes
  that the assertion is not vacuous on the fixture; the injection mutates the sealed architecture —
  a loosened ceiling, a disabled stop, a flat ladder, a zero cooldown, a changed byte — and requires
  the test to go red. A check that cannot fail proves nothing, and the injections are placed where
  the engine could actually go wrong rather than where they are easiest to reach.
- **The exposure assertions replay the fill stream rather than reading the engine's own summary.**
  Asking `clamp_summary()` whether the clamp worked is asking the defendant for a verdict. The replay
  reconstructs cash and quantities from the ordered fill records alone and recomputes the pre-fill
  equity each buy was sized against, sharing no line of code with the clamp it audits.

The fixtures are synthetic symbols on real XNYS sessions in 2010–2011 — inside Generation 2's
development window by a decade — and nothing in the file reads `data/`. Every open is its close minus
a fixed discount, so the set of opens and the set of closes are provably disjoint and "no fill
happened at the close that generated the signal" becomes a set-membership question rather than an
argument.

## What the suite deliberately does not cover

**The decision package.** `tests/**/*.py` is itself a `repo_state_id` pattern, so a test that
asserted the package's `repo_state_id` would invalidate the digest it asserts the moment it was
added. The package is verified by rerunning the recomputation from `_scratch/`, outside the governed
tree, not by a test inside it.

**The Attempt 2 result itself.** No test asserts a return, a drawdown, a profit factor or a verdict.
Those are measurements, and a test that pinned them would convert a research finding into a
requirement — which is how a suite starts defending a number instead of a mechanism. What the suite
pins is the machinery that produced the measurements: the exposure ceiling, the volatility scalar,
the stop's fill timing, the ladder's bands, the lockout's cooldown, determinism, the window bound,
Attempt 1's immutability, and the return-blindness of the selection input.

**Generation 2's holdout.** There is no test that reads it, because reading it is what the test would
have to do. `AT-G` asserts the opposite property — that the loading path refuses any read at or after
the development bound, and that the holdout window is declared prohibited — which is the only form
of assurance available that does not itself commit the violation.
