"""Design probe for the Generation 2 adversarial-test fixtures. ASCII output only.

The engine tests need a synthetic dataset small enough to run in milliseconds and shaped so that
the properties under test are actually exercised: the ranking has to rotate (otherwise the exit
path is never taken), the research shutdown must never fire (otherwise a ceiling test is really a
shutdown test), and no bar's open may equal any bar's close (which is what turns "no fill happened
at a close" into a one-line assertion).

Nothing here becomes an artifact. It exists to check the fixture before it is written into a test.
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
from stockedge100.backtest.g2_engine import RotationEngine  # noqa: E402
from stockedge100.data.calendar import sessions_between  # noqa: E402
from stockedge100.strategies import g2_rotation as rot  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402

SYMBOLS = ("AAA", "BBB", "CCC", "DDD", "EEE")
RATES = (4, 3, 2, 1, 0)          # price units added per session, by phase; never negative
FIRST = dt.date(2010, 1, 4)
LAST = dt.date(2010, 12, 31)


def synthetic_series():
    """Five symbols on real XNYS sessions.

    Closes are whole units and opens are ``close - 0.25``, so the two sets are disjoint by
    construction: an integer reference price on a fill would mean the engine had executed at a
    close. Each symbol's growth rate rotates through ``RATES`` month by month with a per-symbol
    phase offset, so the trailing-return ordering changes and the strategy actually rotates.
    """
    sessions = sessions_between(FIRST, LAST)
    months: list[tuple[int, int]] = []
    for day in sessions:
        key = (day.year, day.month)
        if key not in months:
            months.append(key)

    series = {}
    for index, symbol in enumerate(SYMBOLS):
        close = 200 + 10 * index
        rows = []
        for day in sessions:
            month_index = months.index((day.year, day.month))
            close += RATES[(index + month_index) % len(RATES)]
            rows.append(
                {
                    "session": day.isoformat(),
                    "open": f"{close - Decimal('0.25')}",
                    "high": f"{close}",
                    "low": f"{close - Decimal('0.25')}",
                    "close": f"{close}",
                }
            )
        series[symbol] = series_from_rows(symbol, rows)
    return series


def main() -> int:
    series = synthetic_series()
    sessions = series["AAA"].sessions
    print("sessions", len(sessions), sessions[0], "->", sessions[-1])

    opens = {bar.open for one in series.values() for bar in one.bars.values()}
    closes = {bar.close for one in series.values() for bar in one.bars.values()}
    print("opens n =", len(opens), " closes n =", len(closes),
          " intersection =", len(opens & closes), "(must be 0)")

    window = guard.generation_2_window("g2_fixture", "2009-12-01", "2011-01-31")
    guard.assert_run_window(window)
    print("window", window.name, window.start, "->", window.end)

    for variant_id in (
        "SE100-G2-S3-C1-ROTATION-L03-K1-MONTHLY",
        "SE100-G2-S3-C1-ROTATION-L03-K3-MONTHLY",
        "SE100-G2-S3-C1-ROTATION-L03-K2-QUARTERLY",
    ):
        variant = rot.variant_by_id(variant_id)
        costs = rotation_cost_model(variant.top_k, BASE)
        candidate = rot.RotationCandidate(variant, costs, universe=SYMBOLS)
        engine = RotationEngine(
            series, costs, window, candidate,
            start=sessions[0], end=sessions[-1],
            label=variant_id, budget_weight=candidate.weight,
        )
        result = engine.run()
        evidence = candidate.evidence()
        held = sorted({f.fill.symbol for f in result.fills})
        bad = [f for f in result.fills if f.fill.reference_price in closes]
        print()
        print(f"  {variant_id}")
        print(f"    k={variant.top_k} w={candidate.weight} sessions={len(result.equity_curve)}")
        print(f"    rebalances scheduled={evidence['scheduled_rebalances']} "
              f"executed={evidence['executed_rebalances']} "
              f"exclusions={evidence['exclusion_events']}")
        print(f"    fills={len(result.fills)} trades={len(result.trades)} "
              f"symbols traded={held}")
        print(f"    shutdown={result.shutdown_session}  "
              f"max positions={max(p.position_count for p in result.equity_curve)}")
        print(f"    final equity={result.final_equity.quantize(Decimal('0.01'))}")
        print(f"    clamps={engine.clamp_summary()['binding_clamp_counts']} "
              f"rejections={engine.clamp_summary()['clamp_rejections']}")
        print(f"    fills priced at a close: {len(bad)} (must be 0)")
        reasons = {}
        for rejection in result.rejections:
            reasons[rejection.reason] = reasons.get(rejection.reason, 0) + 1
        print(f"    rejection reasons={reasons or 'none'}")

    # An over-sized request: does the concentration clamp actually bind at k=1?
    variant = rot.variant_by_id("SE100-G2-S3-C1-ROTATION-L03-K1-MONTHLY")
    costs = rotation_cost_model(1, BASE)
    candidate = rot.RotationCandidate(variant, costs, universe=SYMBOLS)
    engine = RotationEngine(
        series, costs, window, candidate,
        start=sessions[0], end=sessions[-1],
        label="oversize", budget_weight=Decimal("0.95"),
    )
    result = engine.run()
    print()
    print("  injected budget_weight=0.95 at k=1")
    print("    clamps", engine.clamp_summary()["binding_clamp_counts"])
    print("    fills", len(result.fills), "shutdown", result.shutdown_session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
