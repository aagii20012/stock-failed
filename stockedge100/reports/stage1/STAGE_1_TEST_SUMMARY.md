# Stage 1 test summary

Command: `cd stockedge100 && PYTHONPATH=src python -m pytest tests -q`
Raw output: [pytest_stage1_output.txt](pytest_stage1_output.txt)

**140 passed, 0 failed, 0 skipped.**

## Composition

| File | Tests | What it establishes |
| --- | ---: | --- |
| `tests/unit/test_stage0_governance.py` | 27 | Stage 0 regression floor. **Unmodified by Stage 1.** |
| `tests/unit/test_stage1_calendar_partition.py` | 34 | The trading calendar and the §6.1 partition arithmetic, checked against independently known facts rather than against the price provider. |
| `tests/unit/test_stage1_preregistration.py` | 17 | The seal: rules were fixed before the data was visible, and the digests still hold. |
| `tests/integration/test_stage1_data_foundation.py` | 33 | The evidence chain end to end — pre-registration → raw → normalized → validated → universe → holdout lock. |
| `tests/adversarial/test_stage1_adversarial.py` | 29 | Every guard fires on an injected defect. |
| **Total** | **140** | |

Stage 0 contributed 27 tests. Stage 1 adds 113. Nothing was weakened, skipped, or removed; the
constitution's regression floor is a floor, and later stages only add to it.

## Why the adversarial file exists

A validation battery that has only ever seen clean data is untested. `test_stage1_adversarial.py`
builds synthetic series on real XNYS sessions and corrupts one thing at a time, asserting that the
sealed check for that defect reports it:

phantom (non-trading-day) session · duplicated session · sessions after the acquisition date ·
short gap trips the fraction limit but not the run limit · long gap trips the run limit · high below
the close (and is quarantined, not deleted) · negative volume · non-positive adjusted close ·
backward step in the adjustment factor · terminal factor away from one · a split recorded but never
applied · a split whose factor step is wrong · a dividend that does not reconcile (recorded at its
sealed WARN severity, not silently upgraded or dropped) · an unexplained extreme move · a declared
corporate action that is absent from the data · a penny-priced series in the development window.

Three controls sit at the top of that file — a clean series, a correctly applied split, a correctly
applied dividend — so that every failure below them is attributable to the injected defect and not
to the harness.

The same file also checks the guards that are structural rather than statistical:

- measuring eligibility on data past the development end raises `WindowViolation`, so the
  measurement-window restriction is enforced by the code rather than promised in prose;
- the universe builder returns exit code 5 and writes nothing when an existing holdout lock has
  different boundaries, so a holdout cannot be recomputed after results are seen;
- editing any sealed configuration byte, deleting a sealed file, or removing the seal itself raises
  `PreRegistrationViolation` in the loader that every Stage 1 module goes through.

Nothing in the suite writes to a frozen artifact. Quarantine output and every rebuild are redirected
into `tmp_path`.

## Determinism

`test_rebuilding_the_universe_from_the_same_inputs_is_reproducible` rebuilds the universe into a
temporary directory from the same sealed rules and the same acquired data, and asserts the result is
identical to the frozen artifact — same members, same `universe_version`, same assessments, and the
same `locked_utc` preserved on the holdout lock — modulo the `frozen_utc` stamp.
