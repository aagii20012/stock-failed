"""Out-of-tree fixture arithmetic for tests/integration/test_stage3_attempt2_backtest.py.

Nothing here is part of the repository state. It exists so the fixture numbers in the integration
module are computed against the real implementation before they are written down as assertions.
"""

import datetime as dt
import sys
from decimal import Decimal

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, CostModel
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.backtest.engine import BacktestEngine, OrderRequest
from stockedge100.backtest.orders import BUY
from stockedge100.backtest.window import development_window
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies import attempt2_candidates, attempt2_runner
from stockedge100.strategies.attempt2_config import load_attempt2_config
from stockedge100.strategies.runner import PRIMARY, CandidatePlan, VariantSpec

CONFIG = load_attempt2_config()
COSTS = CostModel(load_stage2_config().cost_model, BASE)
WINDOW = development_window()
SEALED_RA1 = next(
    e["primary_parameters"] for e in CONFIG.experiments
    if e["experiment_id"] == attempt2_candidates.C1
)
SCAFFOLD_SMA = 3
SESSIONS = sessions_between(dt.date(2000, 1, 3), dt.date(2000, 6, 30))
print("sessions available:", len(SESSIONS), SESSIONS[0], SESSIONS[-1])
COUNT = 45


def prices(symbol, closes, *, adj=None, opens=None, skip=()):
    rows = []
    for index, close in enumerate(closes):
        if index in skip:
            continue
        open_ = close if opens is None else opens[index]
        high = max(Decimal(open_), Decimal(close))
        low = min(Decimal(open_), Decimal(close))
        rows.append({
            "session": SESSIONS[index].isoformat(),
            "open": str(open_), "high": f"{high:f}", "low": f"{low:f}",
            "close": str(close), "adj_close": str(close if adj is None else adj[index]),
            "volume": "1000", "dividend": "0", "split_ratio": "1",
        })
    return series_from_rows(symbol, rows)


def ramp(count, first=80):
    return [str(first + index) for index in range(count)]


def alternating(count, low="100", high="101"):
    return [high if index % 2 else low for index in range(count)]


def scaffold(*, universe=("SPY", "SHY"), defensive="SHY", last=COUNT - 1, **overrides):
    parameters = dict(SEALED_RA1)
    parameters.pop("sma_short", None)
    parameters.update({
        "sma_long": SCAFFOLD_SMA, "risk_symbol": "SPY", "defensive_symbol": defensive,
    })
    parameters.update(overrides)
    symbols = tuple(sorted({s for s in universe if s}))
    spec = VariantSpec(
        experiment_id=attempt2_candidates.C3,
        variant_id=f"{attempt2_candidates.C3}#SCAFFOLD",
        role=PRIMARY, index=0, universe=universe, parameters=parameters, symbols=symbols,
    )
    plan = CandidatePlan(
        experiment_id=attempt2_candidates.C3, family="DEFENSIVE_REGIME",
        declared_universe=universe, warmup_sessions=21, effective_warmup=21,
        run_start=SESSIONS[20], run_end=SESSIONS[last], binding_symbol="SPY",
        variants=(spec,), all_symbols=symbols,
    )
    return spec, plan


def market(skip=()):
    return {
        "SPY": prices("SPY", ramp(COUNT), adj=alternating(COUNT), skip=skip),
        "SHY": prices("SHY", ["50"] * COUNT, adj=["50"] * COUNT),
    }


print("\n--- clean run through run_variant ---")
spec, plan = scaffold()
run = attempt2_runner.run_variant(
    spec, plan, market(), COSTS, WINDOW, CONFIG.rsi_warmup_changes
)
r = run.result
print("start/end", r.start, r.end)
print("fills", len(r.fills), "trades", len(r.trades), "stale", r.stale_marks)
print("shutdown", r.shutdown_session)
print("final cash/equity", r.final_cash, r.final_equity)
print("counters", run.candidate.counters() if hasattr(run.candidate, "counters") else "n/a")
print("equity points", len(r.equity_curve))
print("first fill", r.fills[0].session, r.fills[0].fill.symbol, r.fills[0].fill.side)
print("rejections", [(x.reason, x.order.symbol) for x in r.rejections][:6])
flat = [p for p in r.equity_curve if p.position_count == 0]
print("flat points", len(flat), "cash==equity for all flat:",
      all(p.cash == p.equity for p in flat))
delta = sum((rec.fill.cash_delta for rec in r.fills), Decimal(0))
divs = sum((Decimal(e["cash_credited"]) for e in r.dividend_events), Decimal(0))
print("residual identity:", r.final_cash == r.starting_equity + delta + divs,
      r.final_cash, r.starting_equity + delta + divs)

print("\n--- determinism ---")
a = attempt2_runner.run_variant(spec, plan, market(), COSTS, WINDOW, CONFIG.rsi_warmup_changes)
b = attempt2_runner.run_variant(
    spec, plan, market(), COSTS, WINDOW, CONFIG.rsi_warmup_changes,
    gating=False, label_suffix="#RERUN",
)
print("identical:", a.result.trades_digest() == b.result.trades_digest(),
      a.result.equity_digest() == b.result.equity_digest())

print("\n--- one-session gap on the held symbol at index 30 ---")
gapped = attempt2_runner.run_variant(
    spec, plan, market(skip=(30,)), COSTS, WINDOW, CONFIG.rsi_warmup_changes
)
g = gapped.result
print("stale_marks", g.stale_marks)
print("stale points", [(p.session.isoformat(), p.position_count) for p in g.equity_curve if p.stale_mark])
print("SPY bar at gap:", gapped.result.symbols, SESSIONS[30])

print("\n--- staleness halt: 5 vs 6 consecutive missing sessions ---")


class BuyAndHold:
    def __init__(self, symbol, budget):
        self.name = "TEST-BUY-AND-HOLD"
        self.symbol = symbol
        self.budget = budget
        self.ordered = False
        self.decisions = []

    def decide(self, view, context):
        self.decisions.append(context.session)
        if self.ordered:
            return []
        self.ordered = True
        return [OrderRequest(symbol=self.symbol, side=BUY, budget=self.budget, tag="TEST")]


for gap in (5, 6):
    skip = tuple(range(25, 25 + gap))
    series = {"SPY": prices("SPY", ramp(COUNT), skip=skip)}
    engine = BacktestEngine(
        series, COSTS, WINDOW, BuyAndHold("SPY", Decimal("50")),
        start=SESSIONS[20], end=SESSIONS[COUNT - 1], label=f"GAP{gap}",
    )
    try:
        out = engine.run()
        print(f"gap {gap}: completed, stale_marks={out.stale_marks}")
    except Exception as exc:
        print(f"gap {gap}: {type(exc).__name__}: {str(exc)[:110]}")

print("\n--- greedy buy and the cash buffer ---")
series = {"SPY": prices("SPY", ramp(COUNT))}
probe = BuyAndHold("SPY", Decimal("1000"))
engine = BacktestEngine(
    series, COSTS, WINDOW, probe, start=SESSIONS[20], end=SESSIONS[COUNT - 1], label="GREEDY",
)
out = engine.run()
fill = out.fills[0].fill
print("decisions", len(probe.decisions), "unique", len(set(probe.decisions)))
print("expected decisions", len(sessions_between(SESSIONS[20], SESSIONS[COUNT - 1])) - 1)
print("fill session", out.fills[0].session, "decision", probe.decisions[0])
print("gross", fill.gross_notional, "cash_delta", fill.cash_delta)
point = next(p for p in out.equity_curve if p.session == out.fills[0].session)
print("cash after", point.cash, "equity", point.equity,
      "buffer ok", point.cash >= COSTS.min_cash_buffer_fraction * point.equity)
print("min cash fraction across curve:",
      min(p.cash / p.equity for p in out.equity_curve))
print("books:", all(
    o.fill_session > o.decision_session
    for book in engine._books.values() for o in book.orders
))

print("\n--- shutdown fixture ---")
for drop in ("0.80", "0.82", "0.84"):
    closes = ramp(30) + [f"{Decimal(109) * Decimal(drop):.4f}"] * 5 + ramp(COUNT - 35, first=140)
    series = {"SPY": prices("SPY", closes)}
    probe = BuyAndHold("SPY", Decimal("1000"))
    engine = BacktestEngine(
        series, COSTS, WINDOW, probe, start=SESSIONS[20], end=SESSIONS[COUNT - 1],
        label=f"CRASH{drop}",
    )
    out = engine.run()
    print(f"drop {drop}: shutdown={out.shutdown_session} "
          f"rejections={[(x.reason) for x in out.rejections]} "
          f"final_equity={out.final_equity}")
