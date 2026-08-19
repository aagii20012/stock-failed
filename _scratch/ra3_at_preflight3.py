"""Third preflight: AT-G's block behaviour and AT-H's injection surface, measured before assertion."""

import inspect
import json
import pathlib
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.errors import ConfigViolation
from stockedge100.strategies import g2_runner_ra3 as runner
from stockedge100.strategies import g2_window_guard as guard

print("=" * 100)
print("G. how the guard refuses")
print("   development_bound() = %r" % guard.development_bound())
print("   PARTITION_LOCK_ID = %r" % guard.PARTITION_LOCK_ID)
print("   PROHIBITED_LABELS = %r" % (guard.PROHIBITED_LABELS,))
print("   prohibited_windows():")
for row in guard.prohibited_windows():
    print("      %s" % (row,))

for name, args in (
    ("generation_2_window past the bound", ("probe", "2021-01-04", "2021-08-02")),
    ("generation_2_window ending exactly at the bound", ("probe", "2021-01-04", "2021-07-31")),
    ("generation_2_window into gen-2 holdout", ("probe", "2026-08-01", "2028-07-31")),
    ("generation_2_window into gen-1 holdout", ("probe", "2024-08-01", "2026-07-31")),
):
    try:
        w = guard.generation_2_window(*args)
        print("   %-46s -> OK %s..%s" % (name, w.start, w.end))
    except Exception as exc:                                          # noqa: BLE001
        print("   %-46s -> %s: %s" % (name, type(exc).__name__, str(exc)[:150]))

print()
print("   assert_series_within_bound on a contaminated series:")
import datetime as dt
from stockedge100.backtest.dataset import series_from_rows

def rows(dates):
    return [{"session": d, "open": "10", "high": "10", "low": "10", "close": "10"} for d in dates]

clean = {"AAA": series_from_rows("AAA", rows(["2021-07-29", "2021-07-30"]))}
dirty = {"AAA": series_from_rows("AAA", rows(["2021-07-30", "2021-08-02"]))}
print("      clean -> %s" % (guard.assert_series_within_bound(clean),))
try:
    guard.assert_series_within_bound(dirty)
    print("      dirty -> NO RAISE (bad)")
except Exception as exc:                                              # noqa: BLE001
    print("      dirty -> %s: %s" % (type(exc).__name__, str(exc)[:200]))

print()
print("   load_stage_3_dataset signature: %s" % inspect.signature(guard.load_stage_3_dataset))
print("   loader module of runner.load_grid_dataset's guard reference:")
src = inspect.getsource(runner)
for line in src.splitlines():
    if "g2_window_guard" in line:
        print("      |%s" % line)

print()
print("=" * 100)
print("H. verify_prior_attempt_modules injection surface")
print("   signature: %s" % inspect.signature(runner.verify_prior_attempt_modules))
print("   source:")
for line in inspect.getsource(runner.verify_prior_attempt_modules).splitlines():
    print("      |%s" % line)
