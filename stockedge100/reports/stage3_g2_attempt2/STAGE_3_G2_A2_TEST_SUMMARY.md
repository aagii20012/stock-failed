# Stage 3 (Generation 2, Attempt 2) test summary

Command: `cd stockedge100 && python -m pytest tests -q`
Raw output: [pytest_stage3_g2_attempt2_output.txt](pytest_stage3_g2_attempt2_output.txt)

**1141 passed, 1 failed, 0 skipped.**

The one failure is deliberate, pre-existing and inherited. It is not an Attempt 2 regression, it is
not weakened here, and it is not skipped.

## The failing test

```
FAILED tests/unit/test_stage4_preregistration.py::test_no_stage_4_module_can_reach_restricted_data_or_a_broker
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

| File | Tests | What it establishes |
| --- | ---: | --- |
| `tests/adversarial/test_g2_engine_multiposition.py` | 59 | Generation 2 Attempt 1 floor. **Unmodified.** |
| `tests/adversarial/test_g2_ra1_risk_architecture.py` | 51 | **New.** The five risk-architecture mechanisms and the nine required adversarial tests `AT-A` ... `AT-I`, each section opening with a control and closing with an injected defect that must be caught. |
| `tests/adversarial/test_g2_selection_return_blind.py` | 97 | Generation 2 Attempt 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage1_adversarial.py` | 29 | Generation 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage2_defects.py` | 42 | Generation 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage3_attempt2_defects.py` | 30 | Generation 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage3_defects.py` | 47 | Generation 1 floor. **Unmodified.** |
| `tests/integration/test_stage1_data_foundation.py` | 33 | Generation 1 floor. **Unmodified.** |
| `tests/integration/test_stage2_backtest.py` | 37 | Generation 1 floor. **Unmodified.** |
| `tests/integration/test_stage3_attempt2_backtest.py` | 19 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_g2_cost_derivation.py` | 50 | Generation 2 Attempt 1 floor. **Unmodified.** |
| `tests/unit/test_g2_window_guard.py` | 48 | Generation 2 Attempt 1 floor. **Unmodified.** |
| `tests/unit/test_stage0_governance.py` | 27 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage1_calendar_partition.py` | 34 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage1_preregistration.py` | 17 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage2_engine.py` | 54 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage3_attempt2_implementation.py` | 51 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage3_attempt2_preregistration.py` | 71 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage3_strategies.py` | 69 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage4_evaluation.py` | 92 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage4_evidence.py` | 37 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage4_preregistration.py` | 148 | Generation 1 floor. **Unmodified**, including the one red marker. |
| **Total** | **1142** | 1141 passed, 1 failed by design |

Attempt 1 left the floor at **1091** tests. Attempt 2 adds **51**, all of them in one new
file, for a total of **1142**. The new file is:

```
tests/adversarial/test_g2_ra1_risk_architecture.py
```

Every other file in the table is byte-identical to the state Attempt 1 left it in. That is re-hashed,
not asserted: Attempt 1's `STAGE_3_G2_ARTIFACT_MANIFEST.json` recorded a SHA-256 for each of the
**22** `tests/**/*.py` files that existed when its package was built, every one
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

- **`AT-A`** — 11 tests. Sealed requirement: Aggregate exposure never exceeds 50% of equity at any session, including mid-rebalance, verified after every fill and not only at session close.
- **`AT-B`** — 4 tests. Sealed requirement: Volatility scaling reduces position size when trailing realized portfolio volatility exceeds 10% annualized, verified against a hand-constructed high-volatility equity fixture with an independently computed expected scalar.
- **`AT-C`** — 4 tests. Sealed requirement: A position breaching the 8% stop is exited at the NEXT session's open, not at the same close, and the exit is a full sell.
- **`AT-D`** — 7 tests. Sealed requirement: The de-risk ladder steps down at the declared thresholds and back up only after the declared recovery condition, verified against a hand-constructed drawdown-and-recovery fixture that visits every band in both directions.
- **`AT-E`** — 3 tests. Sealed requirement: The re-entry lockout genuinely blocks a return to a higher sizing band before its cooldown elapses, verified by a fixture in which recovery is available and blocked for exactly the declared number of sessions.
- **`AT-F`** — 5 tests. Sealed requirement: Determinism: identical inputs produce identical trade, equity, ranking and risk-state digests on a clean rerun.
- **`AT-G`** — 5 tests. Sealed requirement: The Generation 2 window guard still blocks any read at or after 2021-08-01, exercised through the Attempt 2 loading path.
- **`AT-H`** — 5 tests. Sealed requirement: No Generation 1 or Attempt 1 module is modified: every module listed in attempt_1_modules_immutable re-hashes to its recorded digest.
- **`AT-I`** — 6 tests. Sealed requirement: The selection input cannot carry a performance figure: the dataclass field tuple equals SELECTION_FIELD_NAMES and the import-time assertion fires when it does not.

That accounts for 50 of the 51 tests. The remaining one covers the shared fixtures and
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
