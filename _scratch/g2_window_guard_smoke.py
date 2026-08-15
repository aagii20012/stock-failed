"""Smoke-test the Generation 2 window guard. ASCII output only."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.errors import WindowViolation  # noqa: E402
from stockedge100.backtest.window import ResearchWindow  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402


def expect_raise(label, fn):
    try:
        fn()
    except WindowViolation as exc:
        print(f"  OK   {label}: {str(exc).splitlines()[0][:110]}")
        return
    print(f"  FAIL {label}: no WindowViolation raised")


def main() -> int:
    print("=== guard state ===")
    print(json.dumps(guard.guard_state(), indent=1))
    print()

    print("=== check 1: run window ===")
    window = guard.stage_3_window()
    print("  stage_3_window ->", window.to_json())
    expect_raise(
        "development+1 day",
        lambda: guard.assert_run_window(
            ResearchWindow("development", window.start, dt.date(2021, 8, 1))
        ),
    )
    expect_raise(
        "validation window",
        lambda: guard.assert_run_window(
            ResearchWindow("validation", dt.date(2021, 8, 1), dt.date(2024, 7, 31))
        ),
    )
    print()

    print("=== check 3: prohibited intersection ===")
    for label, lo, hi in guard.prohibited_windows():
        expect_raise(f"exact {label}", lambda lo=lo, hi=hi: guard.generation_2_window("x", lo, hi))
        expect_raise(
            f"one day into {label}",
            lambda lo=lo: guard.generation_2_window("x", dt.date(1993, 1, 29), lo),
        )
    ok = guard.generation_2_window("gap", dt.date(2024, 8, 1) - dt.timedelta(days=1), dt.date(2024, 7, 31))
    print("  OK   validation window itself constructs (check 3 does not cover it):", ok.to_json())
    print()

    print("=== check 2: loaded bars ===")
    series = guard.load_stage_3_dataset(["SPY", "VEA", "TLT"])
    for symbol, one in series.items():
        print(f"  {symbol:<5} {len(one)} bars  {one.first_session} .. {one.last_session}")
    last = guard.assert_series_within_bound(series)
    print("  last_seen:", last)

    # A series carrying one post-bound bar must be rejected, however it got there.
    from stockedge100.backtest.dataset import PriceSeries, load_series

    full = load_series("SPY")
    poisoned = PriceSeries(symbol="SPY", bars=dict(full.bars), sessions=full.sessions)
    expect_raise("post-bound bar present", lambda: guard.assert_series_within_bound({"SPY": poisoned}))

    clipped = series["SPY"]
    hidden_bars = dict(clipped.bars)
    extra = dt.date(2021, 8, 2)
    hidden_bars[extra] = full.bars[extra]
    hidden = PriceSeries(symbol="SPY", bars=hidden_bars, sessions=clipped.sessions)
    expect_raise("bar map hides a session", lambda: guard.assert_series_within_bound({"SPY": hidden}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
