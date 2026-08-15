"""One full variant, end to end, timed. ASCII output only.

The point is the wall clock as much as the result: the runner has thirty-six of these to do, and
the ranking recomputes 34 signals from scratch at every rebalance because the seal forbids caching.
"""

from __future__ import annotations

import sys
import time
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import BASE, STRESSED, ZERO  # noqa: E402
from stockedge100.backtest.g2_costs import rotation_cost_model  # noqa: E402
from stockedge100.backtest.g2_engine import RotationEngine  # noqa: E402
from stockedge100.backtest.market import MarketView  # noqa: E402
from stockedge100.backtest.orders import BUY  # noqa: E402
from stockedge100.strategies import g2_rotation as rot  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402

VARIANT_ID = sys.argv[1] if len(sys.argv) > 1 else "SE100-G2-S3-C1-ROTATION-L06-K3-MONTHLY"
SCENARIO = STRESSED if len(sys.argv) > 2 and sys.argv[2] == "STRESSED" else BASE


def drawdown(curve):
    high = ZERO
    worst = ZERO
    for point in curve:
        if point.equity > high:
            high = point.equity
        drop = (high - point.equity) / high
        if drop > worst:
            worst = drop
    return worst


def main() -> int:
    variant = rot.variant_by_id(VARIANT_ID)
    costs = rotation_cost_model(variant.top_k, SCENARIO)
    candidate = rot.RotationCandidate(variant, costs)

    series = guard.load_stage_3_dataset(rot.eligible_universe())
    guard.assert_series_within_bound(series)
    window = guard.stage_3_window()
    protocol = rot.load_protocol()
    run = protocol["run_span"]

    started = time.time()
    engine = RotationEngine(
        series,
        costs,
        window,
        candidate,
        start=__import__("datetime").date.fromisoformat(run["run_start"]),
        end=__import__("datetime").date.fromisoformat(run["run_end"]),
        label=f"{variant.variant_id}#{SCENARIO}",
        budget_weight=candidate.weight,
    )
    result = engine.run()
    elapsed = time.time() - started

    print(f"{variant.variant_id}#{SCENARIO}")
    print(f"  elapsed        {elapsed:.1f}s  -> 36 runs ~ {36 * elapsed / 60:.0f} min")
    print("  sessions      ", len(result.equity_curve))
    print("  fills         ", len(result.fills))
    print("  closed trades ", len(result.trades))
    print("  final equity  ", result.final_equity.quantize(Decimal("0.01")))
    print("  net return    ", (result.final_equity / costs.starting_equity - 1).quantize(Decimal("0.000001")))
    print("  max drawdown  ", drawdown(result.equity_curve).quantize(Decimal("0.000001")))
    print("  max positions ", max(p.position_count for p in result.equity_curve))
    print("  shutdown      ", result.shutdown_session)

    reasons = {}
    for rejection in result.rejections:
        reasons[rejection.reason] = reasons.get(rejection.reason, 0) + 1
    print("  rejections    ", reasons or "none")
    print("  clamps        ", engine.clamp_summary()["binding_clamp_counts"])
    print("  evidence      ", candidate.evidence())

    gross = [(p.equity - p.cash) / p.equity for p in result.equity_curve if p.position_count]
    if gross:
        print("  gross at close: min", min(gross).quantize(Decimal("0.0001")),
              " max", max(gross).quantize(Decimal("0.0001")))

    buys = [f for f in result.fills if f.fill.side == BUY]
    print("  first 4 buys:", [(f.session.isoformat(), f.fill.symbol,
                               str((f.fill.quantity * f.fill.effective_price).quantize(Decimal("0.01"))))
                              for f in buys[:4]])
    print("  distinct symbols traded:", len({f.fill.symbol for f in result.fills}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
