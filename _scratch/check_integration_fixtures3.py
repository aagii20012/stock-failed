"""Round three: gate.condition_2 on real and synthetic results, plus run_all's call sites."""

import ast
import datetime as dt
import inspect
import sys
from decimal import Decimal

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, CostModel
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.backtest.engine import BacktestEngine, BacktestResult, EquityPoint, OrderRequest
from stockedge100.backtest.orders import BUY
from stockedge100.backtest.window import development_window
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies import attempt2_harness, gate
from stockedge100.strategies.attempt2_config import load_attempt2_config

CONFIG = load_attempt2_config()
COSTS = CostModel(load_stage2_config().cost_model, BASE)
WINDOW = development_window()
SESSIONS = sessions_between(dt.date(2000, 1, 3), dt.date(2000, 6, 30))
COUNT = 45


def prices(symbol, closes, *, skip=()):
    rows = []
    for index, close in enumerate(closes):
        if index in skip:
            continue
        rows.append({
            "session": SESSIONS[index].isoformat(),
            "open": str(close), "high": str(close), "low": str(close),
            "close": str(close), "adj_close": str(close),
            "volume": "1000", "dividend": "0", "split_ratio": "1",
        })
    return series_from_rows(symbol, rows)


def ramp(count, first=80):
    return [str(first + index) for index in range(count)]


class Greedy:
    name = "TEST-GREEDY"

    def __init__(self, symbol, budget):
        self.symbol = symbol
        self.budget = budget

    def decide(self, view, context):
        if context.open_symbols:
            return []
        return [OrderRequest(symbol=self.symbol, side=BUY, budget=self.budget, tag="TEST")]


def synthetic(equities):
    curve = [
        EquityPoint(session=SESSIONS[i], cash=Decimal(e), equity=Decimal(e),
                    stale_mark=False, position_count=0)
        for i, e in enumerate(equities)
    ]
    return BacktestResult(
        label="SYNTH", scenario="baseline", symbols=("SPY",),
        start=curve[0].session, end=curve[-1].session, equity_curve=curve,
        fills=[], rejections=[], trades=[], dividend_events=[], stale_marks=0,
        shutdown_session=None, starting_equity=Decimal(equities[0]),
        final_cash=Decimal(equities[-1]), final_equity=Decimal(equities[-1]),
        open_positions={}, cost_model=COSTS.to_json(),
    )


print("--- condition_2 on synthetic curves ---")
for label, curve in (
    ("exactly 15%", ["100", "85", "90"]),
    ("15.01%", ["100", "84.99", "90"]),
    ("nothing", ["100", "101", "102"]),
):
    verdict = gate.condition_2(synthetic(curve), CONFIG.criteria)
    print(f"  {label}: {verdict.verdict} measured={verdict.measured} threshold={verdict.threshold}")
    print(f"     evidence={verdict.evidence}")

print("\n--- condition_2 on the real crash run ---")
closes = ramp(30) + ["87.2000"] * 5 + ramp(COUNT - 35, first=140)
engine = BacktestEngine(
    {"SPY": prices("SPY", closes)}, COSTS, WINDOW, Greedy("SPY", Decimal("1000")),
    start=SESSIONS[20], end=SESSIONS[COUNT - 1], label="CRASH",
)
crash = engine.run()
v = gate.condition_2(crash, CONFIG.criteria)
print("  ", v.verdict, v.measured, v.evidence)

print("\n--- condition_2 on the clean run ---")
clean = BacktestEngine(
    {"SPY": prices("SPY", ramp(COUNT))}, COSTS, WINDOW, Greedy("SPY", Decimal("50")),
    start=SESSIONS[20], end=SESSIONS[COUNT - 1], label="CLEAN",
).run()
v = gate.condition_2(clean, CONFIG.criteria)
print("  ", v.verdict, v.measured, v.evidence)

print("\n--- ConditionVerdict fields ---")
print("  ", [f.name for f in __import__("dataclasses").fields(v)])

print("\n--- run_all call sites ---")
source = inspect.getsource(attempt2_harness.run_all)
tree = ast.parse(inspect.cleandoc(source))
calls = [
    node for node in ast.walk(tree)
    if isinstance(node, ast.Call)
    and getattr(node.func, "id", getattr(node.func, "attr", None)) == "run_variant"
]
print("  run_variant call sites:", len(calls))
for node in calls:
    kw = {k.arg: ast.unparse(k.value) for k in node.keywords}
    print("   line", node.lineno, kw)
print("  suffix constants:",
      [(n, getattr(attempt2_harness, n))
       for n in dir(attempt2_harness) if "SUFFIX" in n])
print("  budget:", CONFIG.iteration_budget)
