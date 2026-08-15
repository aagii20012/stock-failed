"""Smoke-test the Generation 2 rotation candidate. ASCII output only.

Checks the three things the candidate can get wrong on its own, before any engine is involved:
the grid rebuilt from the sealed axes, the calendar reproducing the sealed rebalance counts, and
the total-return signal agreeing with the adjusted-close identity it is supposed to equal.
"""

from __future__ import annotations

import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import g2_rotation as rot  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402
from stockedge100.backtest.market import MarketView  # noqa: E402


def main() -> int:
    protocol = rot.load_protocol()
    print("protocol:", protocol["artifact_id"], "| strategy:", protocol["strategy_id"])
    print("universe:", len(rot.eligible_universe()), "members")

    print()
    print("=== the grid, rebuilt from the sealed axes ===")
    variants = rot.rotation_variants()
    print("  count:", len(variants))
    for v in variants[:3] + variants[-2:]:
        print(f"  {v.index:2d} {v.variant_id:48s} w={v.target_weight} "
              f"rebalances={v.scheduled_rebalance_sessions}")
    weights = sorted({(v.top_k, str(v.target_weight)) for v in variants})
    print("  weights:", weights)
    print("  k*w:", [(k, str(int(k) * Decimal(w))) for k, w in weights])

    print()
    print("=== month_offset ===")
    for day, months in ((dt.date(2021, 3, 31), -1), (dt.date(2021, 1, 31), -12),
                        (dt.date(2020, 2, 29), -12), (dt.date(2008, 7, 28), -3)):
        print(f"  {day} {months:+3d} -> {rot.month_offset(day, months)}")

    print()
    print("=== rebalance calendar vs the sealed counts ===")
    series = guard.load_stage_3_dataset(rot.eligible_universe())
    guard.assert_series_within_bound(series)
    run = protocol["run_span"]
    start = dt.date.fromisoformat(run["run_start"])
    end = dt.date.fromisoformat(run["run_end"])
    sessions = sorted({s for ps in series.values() for s in ps.sessions if start <= s <= end})
    print("  run sessions:", len(sessions), "declared:", run["run_sessions"],
          "match:", len(sessions) == run["run_sessions"])
    for frequency, declared in (("MONTHLY", 157), ("QUARTERLY", 53)):
        hits = []
        previous = None
        for session in sessions:
            if rot.is_scheduled_rebalance(session, previous, frequency):
                hits.append(session)
            previous = session
        print(f"  {frequency:9s} {len(hits):3d} declared {declared} match {len(hits) == declared}"
              f" | first3 {[d.isoformat() for d in hits[:3]]} last2 {[d.isoformat() for d in hits[-2:]]}")

    print()
    print("=== total_return vs the adj_close identity ===")
    window = guard.stage_3_window()
    as_of = dt.date(2021, 7, 30)
    view = MarketView(series, as_of, window)
    worst = None
    for symbol in ("SPY", "TLT", "VYM", "XLE", "QQQ", "HYG"):
        for lookback in (3, 6, 12):
            got = rot.total_return(view, symbol, as_of, lookback)
            ref = rot.month_offset(as_of, -lookback)
            bars = rot._bars_back_to(view, symbol, as_of, ref)
            base = None
            for bar in reversed(bars):
                if bar.session <= ref:
                    base = bar
                    break
            expect = bars[-1].adj_close / base.adj_close - 1
            gap = abs(got - expect)
            if worst is None or gap > worst[0]:
                worst = (gap, symbol, lookback, got, expect)
            if symbol == "SPY":
                print(f"  SPY {lookback:2d}m t0={base.session} TR={got.quantize(Decimal('0.000001'))} "
                      f"adj={expect.quantize(Decimal('0.000001'))} gap={gap:.2e}")
    print(f"  worst gap over 18 pairs: {worst[0]:.3e} ({worst[1]} {worst[2]}m)")

    print()
    print("=== ranking at one date ===")
    variant = rot.variant_by_id("SE100-G2-S3-C1-ROTATION-L06-K3-MONTHLY")
    from stockedge100.backtest.g2_costs import rotation_cost_model
    candidate = rot.RotationCandidate(variant, rotation_cost_model(variant.top_k))
    scored, excluded = candidate.rank(view, as_of)
    print("  ranked:", len(scored), " excluded:", excluded or "none")
    print("  top 5:", [(s, str(v.quantize(Decimal('0.0001')))) for v, s in scored[:5]])
    print("  bottom 3:", [(s, str(v.quantize(Decimal('0.0001')))) for v, s in scored[-3:]])

    print()
    print("=== ranking at inception, when the universe is thinnest ===")
    early = dt.date(2008, 7, 28)
    view_early = MarketView(series, early, window)
    for lookback in (3, 12):
        v = rot.variant_by_id(f"SE100-G2-S3-C1-ROTATION-L{lookback:02d}-K3-MONTHLY")
        c = rot.RotationCandidate(v, rotation_cost_model(3))
        scored, excluded = c.rank(view_early, early)
        print(f"  {lookback:2d}m ranked {len(scored)} excluded {excluded or 'none'} "
              f"top3 {[s for _, s in scored[:3]]}")

    print()
    print("=== target() is unreachable ===")
    try:
        candidate.target(view, None)
    except NotImplementedError as exc:
        print("  OK refused:", str(exc).splitlines()[0][:80])
    return 0


if __name__ == "__main__":
    sys.exit(main())
