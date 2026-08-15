# Stage 3 (Generation 2) test summary

Command: `cd stockedge100 && python -m pytest tests -q`
Raw output: [pytest_stage3_g2_output.txt](pytest_stage3_g2_output.txt)

**1090 passed, 1 failed, 0 skipped.**

The one failure is deliberate and pre-existing. It is not a Generation 2 regression, it is not
weakened here, and it is not skipped.

## The failing test

```
FAILED tests/unit/test_stage4_preregistration.py::test_no_stage_4_module_can_reach_restricted_data_or_a_broker
```

This is Generation 1's permanent red marker, recorded as `S4-CONFLICT-7` in the Stage 4
pre-registration package. `src/stockedge100/strategies/stage4_evaluation.py` imports
`load_dataset` and the calendar module — which it must, because a validation stage has to read data —
and the test asserts that no Stage 4 module reaches restricted data at all. The two statements
cannot both hold, and the conflict was recorded rather than resolved by loosening the assertion.
Generation 2 inherits it untouched. Editing it would be weakening a test to make a gate look
cleaner, which the constitution forbids and this stage does not need: the failure has nothing to do
with the Generation 2 verdict.

## Composition

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
| `tests/unit/test_stage3_strategies.py` | 69 | Stage 3 floor. **Unmodified.** |
| `tests/adversarial/test_stage3_defects.py` | 47 | Stage 3 floor. **Unmodified.** |
| `tests/unit/test_stage3_attempt2_preregistration.py` | 71 | Stage 3 Attempt 2 floor. **Unmodified.** |
| `tests/unit/test_stage3_attempt2_implementation.py` | 51 | Stage 3 Attempt 2 floor. **Unmodified.** |
| `tests/integration/test_stage3_attempt2_backtest.py` | 19 | Stage 3 Attempt 2 floor. **Unmodified.** |
| `tests/adversarial/test_stage3_attempt2_defects.py` | 30 | Stage 3 Attempt 2 floor. **Unmodified.** |
| `tests/unit/test_stage4_preregistration.py` | 148 | Stage 4 floor. **Unmodified**, including the one red marker. |
| `tests/unit/test_stage4_evidence.py` | 37 | Stage 4 floor. **Unmodified.** |
| `tests/unit/test_stage4_evaluation.py` | 92 | Stage 4 floor. **Unmodified.** |
| `tests/unit/test_g2_window_guard.py` | 48 | **New.** The development bound, the two prohibited holdout periods, and the loader that must not be able to return a post-bound bar. |
| `tests/unit/test_g2_cost_derivation.py` | 50 | **New.** That the Generation 2 cost model differs from the sealed Generation 1 model at exactly one declared pointer — position breadth — and nowhere else. |
| `tests/adversarial/test_g2_engine_multiposition.py` | 59 | **New.** The multi-position engine: the position count, the two ceilings, the execution boundary, look-ahead, and determinism. |
| `tests/adversarial/test_g2_selection_return_blind.py` | 97 | **New.** That the representative-selection rule cannot see a return, by permutation rather than by assertion. |
| **Total** | **1091** | 1090 passed, 1 failed by design |

Generation 1 left the floor at **837**. Generation 2 adds **254** and removes nothing. No test was
weakened, skipped, `xfail`ed, deleted, or had an exclusion added to it.

`tests/conftest.py` was not touched — it is hashed in the Stage 0 manifest. Every Generation 2
fixture is defined locally in the file that uses it. No Generation 2 test writes into `data/`,
`governance/`, `config/`, or `reports/`; the tests that need a different file layout build one under
`tmp_path` and redirect the loader onto it with `monkeypatch`.

## `test_g2_window_guard.py` — the guard that makes §5(3) checkable

The operating instruction requires that this stage's code be *prevented* from reading 2021-08-01 or
later, not merely trusted not to. The guard is two independent mechanisms and the tests attack both.

Four controls come first: the lock states the partition the file was written against, the Stage 3
window is accepted and ends exactly on the bound, an interior window is accepted, and the guard
reports the state it is enforcing. Without those, every rejection below would be equally consistent
with a guard that rejects everything.

Then: a window ending one day past the bound is rejected while one ending exactly on it is accepted;
every post-bound end is rejected whatever the start (parametrised across starts, so the rejection is
not an artifact of one pair); a backwards window is rejected rather than silently producing an empty
result; the validation window is *constructible* but not runnable in Stage 3, which is the honest
shape — validation is a real window that this stage may not run, not a nonexistent one. Both
prohibited periods — Generation 1's sealed holdout and Generation 2's — cannot be intersected at
all, the refusal says in as many words that no result reopens either, and the two are asserted to be
**adjacent with no gap**, because a window slipping between 2026-07-31 and 2026-08-01 would defeat
both checks individually.

The second mechanism audits what was actually loaded. A series carrying a post-bound bar is rejected
even if every other symbol is clean; the check reads the **bar map**, not the session index, and the
inverse disagreement is caught too; an empty series is a refusal rather than a vacuous pass; a file
holding only post-bound sessions is a refusal rather than an empty result; and the loader stops at
the bound instead of loading everything and discarding the tail. Finally, a tampered partition lock
halts the guard rather than moving its bounds, and a lock authorizing more than development cannot
produce a Stage 3 window.

## `test_g2_cost_derivation.py` — the cost model is Generation 1's

The instruction holds the cost model constant and puts revising it out of scope. But a multi-position
strategy needs a cost model that admits more than one position, so *something* had to change. The
tests pin exactly what.

The derivation is expressed as a single declared pointer into the sealed Generation 1 mapping. Every
permitted position count differs from the sealed model **at most at that pointer** — asserted by
flattening both mappings to RFC 6901 pointers and diffing every leaf, including list elements and
escaped reserved characters — and `k` equal to the sealed value produces no difference at all, which
is the control that makes the diff meaningful. A second difference injected anywhere is refused; a
derivation that silently drops a field is refused; a type change that compares equal is still
counted as a difference. The stressed scenario scales the frictions without touching breadth. A
tampered declaration, an appended override, a declaration whose sealed value disagrees with the
sealed file, and a missing declaration are each refused, and a control confirms the substitution
harness itself is clean and the real declaration still loads after every substitution.

## `test_g2_engine_multiposition.py` — the new engine capability

The instruction is explicit that holding more than one risky position is new engine capability
requiring its own adversarial tests before it is trusted, and names six things the tests must catch.
Each has its own section here, and each section has a control.

**More than k positions.** The book never exceeds the variant's position count; the book *actually
reaches* k, so the bound is not vacuous; a greedy probe asking for more is refused by the declared
reason; the portfolio refuses the surplus even with the engine-level check removed, so the invariant
is not carried by one line; and the engine's own invariant reports a book wider than the limit.

**The 95% gross ceiling and the 50% concentration ceiling.** The whole book stays inside the sealed
gross cap; an oversized request at k=3 is clamped by the aggregate ceiling and at k=1 by the
concentration ceiling; the clamp labels are the declared ones rather than a generic truncation; a
holding left out of the marks is a halt, not a smaller sum — the failure mode where an unmarked
position makes exposure *look* compliant; and the ceiling is read from the seal, not from the caller.

**Trading at the close that generated the signal.** Every fill happens strictly after the session
that decided it; no fill was priced at any close in the dataset, checked against the dataset's own
close values rather than against the engine's bookkeeping; an order that would fill at, or before,
its own decision close cannot be *constructed*; and executing a scheduled order on the wrong session
is an invariant violation.

**Tomorrow's bar in today's ranking.** The ranking is unchanged when every future bar is removed,
and unchanged when the future is replaced by a *different* future — the stronger form, since
deletion alone can be passed by code that reads a fixed-length tail. A bar the decision can see does
change the ranking (the control). An interior bar is invisible by the sealed formula, which is a
property of total-return momentum and is asserted rather than assumed. A symbol without enough
history is excluded rather than scored zero. The visibility bound cannot be moved after
construction, and a whole run is unchanged by data after its end.

**Determinism.** A clean rerun reproduces the run exactly; a rerun from a freshly built dataset does
too; the symbol insertion order of the dataset does not change the result; the stressed scenario is
deterministic and differs from the base one. Two negative controls: one perturbed bar changes the
digest, and the digests cover decisions and not only the equity curve — a digest that only summed
the curve would be satisfied by two different trade sequences reaching the same equity.

## `test_g2_selection_return_blind.py` — the property the whole verdict rests on

The instruction requires the representative to be chosen "without inspecting return figures as part
of the selection itself". Asserting that in prose is worth nothing; this file establishes it by
permutation.

The baseline selection is well-formed and decided at step 2. The permutations are then shown to
*really move the returns* (the control), and a return-aware ordering is shown to move under those
same permutations (the second control — without it, "the selection did not move" is equally
consistent with permutations that changed nothing). Given both: permuting every return leaves the
selection byte-identical, leaves the recorded projection byte-identical, and extreme returns do not
move it either. No stub return reaches the record.

Structurally: `SelectionInput` carries exactly the declared fields, no declared field names a
performance figure, and the record is frozen so a figure cannot be attached afterwards.

The screen and the tiebreak are then tested in both directions — a shutdown in the stressed run
alone still disqualifies; a variant missing its stressed run is refused rather than screened on half
its evidence; a duplicated run, an undeclared run label, a partial grid and duplicate variant ids are
each refused; step 1 decides when exactly one variant survives; step 3 breaks a tie
lexicographically; the tiebreak is return-blind too; turnover sums both runs rather than reading one;
and moving a shutdown event, or a fill count, does change the selection.

The no-candidate path — the one this stage actually took — is tested directly: when every variant
shuts down at least once the rule yields no candidate, and that path is return-blind too. Finally,
the sealed steps are asserted to be the three this module implements, and a renamed, duplicated,
missing, or fourth sealed step halts rather than being reinterpreted or ignored.

## What the suite deliberately does not cover

The decision package. `tests/**/*.py` is one of the patterns `repo_state_id` is computed over, so a
test asserting that digest would invalidate the value it asserts the moment it was written. The
package is verified by re-running the recomputation from `_scratch/`, not by a test.
