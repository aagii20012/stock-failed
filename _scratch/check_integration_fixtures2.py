"""Round two: the remaining fixtures for tests/integration/test_stage3_attempt2_backtest.py."""

import copy
import dataclasses
import datetime as dt
import sys
from decimal import Decimal

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, CostModel
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.backtest.engine import BacktestEngine, OrderRequest
from stockedge100.backtest.errors import ConfigViolation, LookAheadError, WindowViolation
from stockedge100.backtest.orders import BUY, SELL
from stockedge100.backtest.window import (
    DEVELOPMENT, HOLDOUT, VALIDATION, ResearchWindow, development_window, window_named,
)
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies import attempt2_candidates, attempt2_runner, gate
from stockedge100.strategies.attempt2_config import load_attempt2_config
from stockedge100.strategies.runner import PRIMARY, CandidatePlan, VariantSpec, run_start_for

CONFIG = load_attempt2_config()
COSTS = CostModel(load_stage2_config().cost_model, BASE)
WINDOW = development_window()
SEALED_RA1 = next(
    e["primary_parameters"] for e in CONFIG.experiments
    if e["experiment_id"] == attempt2_candidates.C1
)
SCAFFOLD_SMA = 3
SESSIONS = sessions_between(dt.date(2000, 1, 3), dt.date(2000, 6, 30))
COUNT = 45


def prices(symbol, closes, *, adj=None, opens=None, skip=(), sessions=None):
    days = SESSIONS if sessions is None else sessions
    rows = []
    for index, close in enumerate(closes):
        if index in skip:
            continue
        open_ = close if opens is None else opens[index]
        high = max(Decimal(open_), Decimal(close))
        low = min(Decimal(open_), Decimal(close))
        rows.append({
            "session": days[index].isoformat(),
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


class Greedy:
    """Buys whenever flat, so a blocked entry leaves a rejection behind."""

    def __init__(self, symbol, budget):
        self.name = "TEST-GREEDY"
        self.symbol = symbol
        self.budget = budget
        self.decisions = []

    def decide(self, view, context):
        self.decisions.append(context.session)
        if context.open_symbols:
            return []
        return [OrderRequest(symbol=self.symbol, side=BUY, budget=self.budget, tag="TEST")]


print("--- window bounds refused ---")
for name in (VALIDATION, HOLDOUT):
    other = window_named(name)
    for kwargs in ({"start": other.start}, {"end": other.end}):
        try:
            BacktestEngine(
                {"SPY": prices("SPY", ramp(COUNT))}, COSTS, WINDOW,
                Greedy("SPY", Decimal("50")), **kwargs,
            )
            print(f"  {name} {kwargs}: NO RAISE")
        except WindowViolation as exc:
            print(f"  {name} {list(kwargs)}: WindowViolation ok -> {str(exc)[:70]}")

print("\n--- warm-up comes from inside the window ---")
span = sessions_between(dt.date(1992, 11, 2), dt.date(1993, 4, 30))
print("  span", len(span), span[0], span[-1])
series = {"SPY": prices("SPY", ramp(len(span)), sessions=span)}
inside = [d for d in series["SPY"].sessions if WINDOW.contains(d)]
print("  inside", len(inside), inside[0])
start, binding = run_start_for(("SPY",), 21, WINDOW, series)
print("  run start", start, "binding", binding, "== inside[20]", start == inside[20])
print("  naive 21st bar", series["SPY"].sessions[20],
      "in window:", WINDOW.contains(series["SPY"].sessions[20]))

print("\n--- run start needs warm-up for every declared symbol ---")
two = {
    "SPY": prices("SPY", ramp(COUNT)),
    "SHY": prices("SHY", ["50"] * (COUNT - 8), sessions=SESSIONS[8:]),
}
print("  ", run_start_for(("SPY", "SHY"), 5, WINDOW, two))
print("   SPY alone:", run_start_for(("SPY",), 5, WINDOW, two))
short = {"SPY": prices("SPY", ramp(3))}
try:
    run_start_for(("SPY",), 5, WINDOW, short)
except ConfigViolation as exc:
    print("   short:", str(exc)[:100])
try:
    run_start_for(("SPY", "IEF"), 5, WINDOW, two)
except ConfigViolation as exc:
    print("   missing:", str(exc)[:100])

print("\n--- short run refused ---")
spec, plan = scaffold()
real = attempt2_runner.run_variant(spec, plan, market(), COSTS, WINDOW, CONFIG.rsi_warmup_changes)
truncated = dataclasses.replace(real.result, end=SESSIONS[COUNT - 5])
original_run = BacktestEngine.run
BacktestEngine.run = lambda self: truncated
try:
    attempt2_runner.run_variant(spec, plan, market(), COSTS, WINDOW, CONFIG.rsi_warmup_changes)
    print("  NO RAISE")
except ConfigViolation as exc:
    print("  ConfigViolation:", str(exc)[:160])
finally:
    BacktestEngine.run = original_run

print("\n--- excluded symbols ---")
print("  excluded:", list(CONFIG.excluded_symbols))
required = attempt2_runner.required_symbols(CONFIG)
print("  required:", required)


class Shim:
    def __init__(self, experiments, excluded):
        self.experiments = experiments
        self.excluded_symbols = excluded


tampered = copy.deepcopy(CONFIG.experiments)
tampered[0]["universe"] = list(tampered[0]["universe"]) + ["AAPL"]
try:
    attempt2_runner.load_required_dataset(Shim(tampered, dict(CONFIG.excluded_symbols)))
    print("  NO RAISE")
except ConfigViolation as exc:
    print("  ConfigViolation:", exc)

print("\n--- look-ahead ---")


class Peeker:
    name = "TEST-PEEKER"

    def decide(self, view, context):
        view.bar("SPY", context.session + dt.timedelta(days=7))
        return []


engine = BacktestEngine(
    {"SPY": prices("SPY", ramp(COUNT))}, COSTS, WINDOW, Peeker(),
    start=SESSIONS[20], end=SESSIONS[COUNT - 1],
)
try:
    engine.run()
    print("  NO RAISE")
except LookAheadError as exc:
    print("  LookAheadError:", str(exc)[:110])

print("\n--- shutdown with a greedy probe ---")
closes = ramp(30) + ["87.2000"] * 5 + ramp(COUNT - 35, first=140)
series = {"SPY": prices("SPY", closes)}
probe = Greedy("SPY", Decimal("1000"))
engine = BacktestEngine(
    series, COSTS, WINDOW, probe, start=SESSIONS[20], end=SESSIONS[COUNT - 1], label="CRASH",
)
out = engine.run()
print("  shutdown", out.shutdown_session)
print("  rejection reasons", sorted({x.reason for x in out.rejections}))
print("  rejection count", len(out.rejections))
forced = [
    (s.isoformat(), o.side, o.tag)
    for s, book in engine._books.items() for o in book.orders if o.tag == "SHUTDOWN"
]
print("  forced orders", forced)
after = [x for x in out.rejections if x.order.decision_session >= out.shutdown_session]
print("  post-shutdown rejection reasons", sorted({x.reason for x in after}))
print("  buy fills after shutdown",
      [f.session.isoformat() for f in out.fills if f.fill.side == BUY
       and f.session > out.shutdown_session])
print("  sell fills", [(f.session.isoformat(), f.fill.side) for f in out.fills
                       if f.fill.side == SELL])
print("  final equity", out.final_equity, "high water", engine._high_water)

print("\n--- clean control: no shutdown ---")
clean = BacktestEngine(
    {"SPY": prices("SPY", ramp(COUNT))}, COSTS, WINDOW, Greedy("SPY", Decimal("50")),
    start=SESSIONS[20], end=SESSIONS[COUNT - 1], label="CLEAN",
)
cleaned = clean.run()
print("  shutdown", cleaned.shutdown_session)

print("\n--- _check_risk boundary ---")
probe_engine = BacktestEngine(
    {"SPY": prices("SPY", ramp(COUNT))}, COSTS, WINDOW, Greedy("SPY", Decimal("50")),
    start=SESSIONS[20], end=SESSIONS[COUNT - 1],
)
probe_engine._high_water = Decimal(100)
print("  at 85.00:", probe_engine._check_risk(SESSIONS[21], Decimal("85.00")))
print("  at 84.99:", probe_engine._check_risk(SESSIONS[22], Decimal("84.99")))
print("  shutdown session now", probe_engine._shutdown_session)
print("  drawdown limit", COSTS.research_shutdown_drawdown)
print("  criteria limit",
      CONFIG.criteria["frozen_gate_json_companion_verbatim"]["thresholds"]["max_drawdown_pct"])
