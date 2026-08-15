"""Which fixture bars does a decision actually read? ASCII output only.

The first draft of the non-vacuity tests bumped a mid-month bar and nothing changed -- correctly,
because ``total_return`` reads exactly two bars (the decision close and the lookback anchor). This
finds the scheduled rebalance sessions inside the 2010 fixture and prints the ranking at each, so
the tests can bump a bar a decision genuinely sees.
"""

from __future__ import annotations

import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import BASE  # noqa: E402
from stockedge100.backtest.dataset import series_from_rows  # noqa: E402
from stockedge100.backtest.g2_costs import rotation_cost_model  # noqa: E402
from stockedge100.backtest.market import MarketView  # noqa: E402
from stockedge100.data.calendar import sessions_between  # noqa: E402
from stockedge100.strategies import g2_rotation as rot  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402

SYMBOLS = ("AAA", "BBB", "CCC", "DDD", "EEE")
RATES = (4, 3, 2, 1, 0)
FIRST = dt.date(2010, 1, 4)
LAST = dt.date(2010, 12, 31)
OPEN_DISCOUNT = Decimal("0.25")


def build_series(first=FIRST, last=LAST, *, bump=None):
    sessions = sessions_between(first, last)
    months = []
    for day in sessions:
        key = (day.year, day.month)
        if key not in months:
            months.append(key)
    series = {}
    for index, symbol in enumerate(SYMBOLS):
        close = Decimal(200 + 10 * index)
        rows = []
        for day in sessions:
            close += RATES[(index + months.index((day.year, day.month))) % len(RATES)]
            value = close
            if bump is not None and bump[0] == symbol and bump[1] == day:
                value = close + Decimal(bump[2])
            rows.append(
                {
                    "session": day.isoformat(),
                    "open": f"{value - OPEN_DISCOUNT}",
                    "high": f"{value}",
                    "low": f"{value - OPEN_DISCOUNT}",
                    "close": f"{value}",
                }
            )
        series[symbol] = series_from_rows(symbol, rows)
    return series


def main() -> int:
    series = build_series()
    sessions = series["AAA"].sessions
    window = guard.generation_2_window("probe", "2009-12-01", "2011-01-31")

    variant = rot.variant_by_id("SE100-G2-S3-C1-ROTATION-L03-K3-MONTHLY")
    costs = rotation_cost_model(variant.top_k, BASE)
    inside = []
    previous = None
    for day in sessions:
        if rot.is_scheduled_rebalance(day, previous, variant.frequency):
            inside.append(day)
        previous = day
    print("scheduled monthly rebalances inside the fixture:", len(inside))
    print("  ", [d.isoformat() for d in inside])

    print()
    print("prices on 2010-09-30:")
    for symbol in SYMBOLS:
        bar = series[symbol].bars[dt.date(2010, 9, 30)]
        print(f"   {symbol} open={bar.open} close={bar.close}")

    print()
    for day in inside:
        candidate = rot.RotationCandidate(variant, costs, universe=SYMBOLS)
        scored, excluded = candidate.rank(MarketView(series, day, window), day)
        order = [s for _, s in scored]
        print(f"  {day}  order={order}  excluded={excluded}")

    # Does a bump on a rebalance session flip the order?
    target = inside[5]
    candidate = rot.RotationCandidate(variant, costs, universe=SYMBOLS)
    scored, _ = candidate.rank(MarketView(series, target, window), target)
    laggard = scored[-1][1]
    print()
    print(f"  target={target} laggard={laggard}")
    bumped = build_series(bump=(laggard, target, 900))
    candidate2 = rot.RotationCandidate(variant, costs, universe=SYMBOLS)
    scored2, _ = candidate2.rank(MarketView(bumped, target, window), target)
    print(f"    before={[s for _, s in scored]}")
    print(f"    after ={[s for _, s in scored2]}")

    # And on the DECISION date used by the look-ahead section?
    decision = dt.date(2010, 9, 30)
    candidate3 = rot.RotationCandidate(variant, costs, universe=SYMBOLS)
    base_rank, _ = candidate3.rank(MarketView(series, decision, window), decision)
    lag = base_rank[-1][1]
    bumped2 = build_series(bump=(lag, decision, 900))
    candidate4 = rot.RotationCandidate(variant, costs, universe=SYMBOLS)
    new_rank, _ = candidate4.rank(MarketView(bumped2, decision, window), decision)
    print()
    print(f"  decision={decision} laggard={lag}")
    print(f"    before={[s for _, s in base_rank]}")
    print(f"    after ={[s for _, s in new_rank]}")
    print(f"    is {decision} a scheduled rebalance? {decision in inside}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
