"""Smoke-test the Generation 2 RotationEngine. ASCII output only.

Deliberately uses a *signal-free* probe: the rotation target is a function of the month index alone,
so what is exercised here is the engine — sequencing, ceilings, determinism — and not a strategy.
"""

from __future__ import annotations

import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.config import dec  # noqa: E402
from stockedge100.backtest.costs import BASE, ZERO  # noqa: E402
from stockedge100.backtest.engine import DecisionContext, OrderRequest  # noqa: E402
from stockedge100.backtest.g2_costs import rotation_cost_model  # noqa: E402
from stockedge100.backtest.g2_engine import RotationEngine  # noqa: E402
from stockedge100.backtest.orders import BUY, SELL  # noqa: E402
from stockedge100.backtest.window import ResearchWindow  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402

SYMBOLS = ["AGG", "GLD" if False else "IWM", "TLT", "XLU"]
START = dt.date(2015, 1, 2)
END = dt.date(2016, 12, 30)

WEIGHTS = {1: dec("0.500000000"), 2: dec("0.475000000"), 3: dec("0.316666666")}


class CycleProbe:
    """Rotate through a fixed cyclic target set at each month change. No market data is read."""

    def __init__(self, symbols, k, budget_weight):
        self.name = f"cycle-k{k}"
        self.symbols = list(symbols)
        self.k = k
        self.budget_weight = budget_weight
        self._month = None
        self._step = 0

    def target(self):
        n = len(self.symbols)
        return sorted(self.symbols[(self._step + i) % n] for i in range(self.k))

    def decide(self, view, context: DecisionContext):
        month = (context.session.year, context.session.month)
        if month == self._month:
            return []
        self._month = month
        self._step += 1
        want = self.target()
        held = set(context.open_symbols)
        requests = []
        for symbol in sorted(held - set(want)):
            requests.append(OrderRequest(symbol=symbol, side=SELL, tag="EXIT"))
        for symbol in want:
            if symbol in held:
                continue
            requests.append(
                OrderRequest(
                    symbol=symbol,
                    side=BUY,
                    budget=(self.budget_weight * context.equity).quantize(Decimal("0.01")),
                    tag="ENTER",
                )
            )
        return requests


class StaggeredProbe:
    """Buys and sells, but never on the same session, with fixed-dollar budgets.

    Both engines must agree exactly on this probe: it avoids the sell-then-buy sequencing entirely,
    and a fixed budget of USD 10 is the smallest clamp under either engine's arithmetic, so the mark
    used to compute equity (open vs close) never reaches the fill.
    """

    def __init__(self, symbols, k):
        self.name = "staggered"
        self.symbols = list(symbols)
        self.k = k
        self._month = None
        self._step = 0

    def decide(self, view, context: DecisionContext):
        month = (context.session.year, context.session.month)
        if month == self._month:
            return []
        self._month = month
        self._step += 1
        held = set(context.open_symbols)
        if self._step % 2:
            for symbol in self.symbols:
                if symbol not in held and len(held) < self.k:
                    return [OrderRequest(symbol=symbol, side=BUY, budget=dec("10.00"), tag="ENTER")]
            return []
        for symbol in sorted(held):
            return [OrderRequest(symbol=symbol, side=SELL, tag="EXIT")]
        return []


def tally(records):
    counts = {}
    for record in records:
        counts[record.reason] = counts.get(record.reason, 0) + 1
    return counts or "none"


def _build(engine_class, k, weight, label, probe):
    series = guard.load_stage_3_dataset(SYMBOLS)
    guard.assert_series_within_bound(series)
    return engine_class(
        series,
        rotation_cost_model(k, BASE),
        guard.stage_3_window(),
        probe if probe is not None else CycleProbe(SYMBOLS, k, weight),
        start=START,
        end=END,
        label=label or f"k{k}",
    )


def run(k, weight, label="", probe=None):
    engine = _build(RotationEngine, k, weight, label, probe)
    return engine, engine.run()


def run_base(k, weight, label="", probe=None):
    """The same run under Generation 1's engine, for the two declared divergences."""
    from stockedge100.backtest.engine import BacktestEngine

    engine = _build(BacktestEngine, k, weight, label or "gen1", probe)
    return engine, engine.run()


def check_sequencing(result):
    """Within any fill session, no SELL may follow a BUY."""
    bad = []
    by_session = {}
    for record in result.fills:
        by_session.setdefault(record.session, []).append(record.fill.side)
    for session, sides in by_session.items():
        seen_buy = False
        for side in sides:
            if side == BUY:
                seen_buy = True
            elif seen_buy:
                bad.append(session)
                break
    return bad


def main() -> int:
    print("=== k=3, equal weight at entry ===")
    engine, result = run(3, WEIGHTS[3])
    print("  sessions      ", len(result.equity_curve))
    print("  fills         ", len(result.fills))
    print("  closed trades ", len(result.trades))
    print("  rejections    ", len(result.rejections))
    print("  final equity  ", result.final_equity.quantize(Decimal("0.0001")))
    print("  max positions ", max(p.position_count for p in result.equity_curve))
    print("  clamp summary ", engine.clamp_summary())
    print("  out-of-order sell sessions:", check_sequencing(result) or "none")

    reasons = {}
    for rejection in result.rejections:
        reasons[rejection.reason] = reasons.get(rejection.reason, 0) + 1
    print("  rejection reasons:", reasons or "none")
    print("  shutdown session:", result.shutdown_session)

    high = ZERO
    worst = None
    for point in result.equity_curve:
        if point.equity > high:
            high = point.equity
        drop = (high - point.equity) / high
        if worst is None or drop > worst[1]:
            worst = (point.session, drop)
    print("  peak equity:", high.quantize(Decimal("0.0001")),
          " worst drawdown:", worst[1].quantize(Decimal("0.000001")), "on", worst[0])
    print("  first 6 fills:", [(f.session.isoformat(), f.fill.side, f.fill.symbol,
                                str(f.fill.quantity), str(f.fill.effective_price))
                               for f in result.fills[:6]])
    print("  equity at 0/1/2/60/120:", [str(result.equity_curve[i].equity.quantize(Decimal("0.01")))
                                        for i in (0, 1, 2, 60, 120)])

    print()
    print("=== determinism: identical inputs, clean rerun ===")
    _, again = run(3, WEIGHTS[3])
    print("  trades digest equal:", result.trades_digest() == again.trades_digest())
    print("  equity digest equal:", result.equity_digest() == again.equity_digest())

    print()
    print("=== k=1: the concentration ceiling binds before the gross cap ===")
    engine1, result1 = run(1, dec("0.95"))
    invested = []
    for point in result1.equity_curve:
        if point.position_count:
            invested.append((point.equity - point.cash) / point.equity)
    print("  requested 0.95 of equity per buy; realized gross exposure at close:")
    print("    min", min(invested).quantize(Decimal("0.0001")),
          " max", max(invested).quantize(Decimal("0.0001")))
    print("  binding clamps:", engine1.clamp_summary()["binding_clamp_counts"])

    print()
    print("=== k=3, each buy requesting 0.95 of equity ===")
    engine3, result3 = run(3, dec("0.95"))
    print("  binding clamps:", engine3.clamp_summary()["binding_clamp_counts"])
    print("  clamp rejections:", engine3.clamp_summary()["clamp_rejections"])
    gross = [(p.equity - p.cash) / p.equity for p in result3.equity_curve if p.position_count]
    print("  realized gross exposure at close: min", min(gross).quantize(Decimal("0.0001")),
          " max", max(gross).quantize(Decimal("0.0001")))
    print("  max positions:", max(p.position_count for p in result3.equity_curve))
    details = [r.detail for r in result3.rejections if r.reason == "INSUFFICIENT_CASH"]
    if details:
        print("  first INSUFFICIENT_CASH detail:", details[0][:150])

    reasons3 = {}
    for rejection in result3.rejections:
        reasons3[rejection.reason] = reasons3.get(rejection.reason, 0) + 1
    print("  rejection reasons:", reasons3 or "none")
    for rejection in result3.rejections:
        if rejection.reason in ("INSUFFICIENT_CASH", "MIN_NOTIONAL"):
            print("  first budget-starved rejection:", rejection.reason, "|",
                  rejection.detail[:160])
            break

    print()
    print("=== G2-CONFLICT-14 defect 1: same-session sell-then-buy under the Gen 1 sequencing ===")
    base_engine, base_result = run_base(1, dec("0.40"))
    _, rot_result = run(1, dec("0.40"))
    print("  Gen 1 BacktestEngine fills:", len(base_result.fills),
          " rejections:", tally(base_result.rejections))
    print("  Gen 2 RotationEngine fills:", len(rot_result.fills),
          " rejections:", tally(rot_result.rejections))

    print()
    print("=== equivalence: no clamp binding and no same-session sell+buy -> identical ===")
    base_engine, base_result = run_base(3, None, probe=StaggeredProbe(SYMBOLS, 3))
    rot_engine, rot_result = run(3, None, probe=StaggeredProbe(SYMBOLS, 3))
    print("  fills:", len(base_result.fills), "vs", len(rot_result.fills),
          " sells:", sum(1 for f in rot_result.fills if f.fill.side == SELL))
    print("  binding clamps:", rot_engine.clamp_summary()["binding_clamp_counts"])
    print("  trades digest equal:", base_result.trades_digest() == rot_result.trades_digest())
    print("  equity digest equal:", base_result.equity_digest() == rot_result.equity_digest())
    print("  final equity:", base_result.final_equity.quantize(Decimal("0.000001")),
          "vs", rot_result.final_equity.quantize(Decimal("0.000001")))

    print()
    print("=== no order may fill on its own decision session ===")
    offenders = 0
    for record in result.fills:
        decided = record.order_id.split("-")[0:3]
        decided = dt.date(int(decided[0]), int(decided[1]), int(decided[2]))
        if record.session <= decided:
            offenders += 1
    print("  fills on or before their decision session:", offenders)
    return 0


if __name__ == "__main__":
    sys.exit(main())
