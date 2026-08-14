"""Out-of-tree: compute every value the three Attempt 2 test files will pin by hand.

Reads sealed config and synthetic bars only. No market data, no evaluation.
"""

import datetime as dt
import inspect
import json
import sys
from decimal import Decimal

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, ZERO, CostModel, exact
from stockedge100.backtest.dataset import Bar, series_from_rows
from stockedge100.backtest.engine import DecisionContext
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.window import ResearchWindow
from stockedge100.strategies import attempt2_candidates as C
from stockedge100.strategies import attempt2_indicators as I
from stockedge100.strategies import attempt2_runner as R
from stockedge100.strategies import attempt2_traceability as T
from stockedge100.strategies.attempt2_config import load_attempt2_config

config = load_attempt2_config()
costs = CostModel(load_stage2_config().cost_model, BASE)
DAY_ZERO = dt.date(2000, 1, 3)


def bar(session, close, adj_close=None):
    value = Decimal(close)
    return Bar(
        session=session, open=value, high=value, low=value, close=value,
        adj_close=value if adj_close is None else Decimal(adj_close),
        volume=1_000, dividend=ZERO, split_ratio=Decimal(1),
    )


# -- 1. VOL20 on the alternating fixture ---------------------------------------------------------
print("== VOL20 ==")
prices = [Decimal(100)]
for i in range(20):
    prices.append(prices[-1] * (Decimal("1.1") if i % 2 == 0 else Decimal("0.9")))
alt = [bar(DAY_ZERO + dt.timedelta(days=i), "50", adj_close=f"{p:f}") for i, p in enumerate(prices)]
print("  bars:", len(alt))
value = I.vol20(alt)
print("  vol20 exact      :", value)
print("  vol20 8dp        :", value.quantize(Decimal("0.00000001")))


@exact
def closed_form():
    return (Decimal("0.2") / Decimal(19)).sqrt() * Decimal(252).sqrt()


print("  closed form      :", closed_form())
print("  equal            :", closed_form() == value)


@exact
def denominator_20():
    return (Decimal("0.2") / Decimal(20)).sqrt() * Decimal(252).sqrt()


print("  denominator 20   :", denominator_20(), "  differs:", denominator_20() != value)
print("  20 bars -> None  :", I.vol20(alt[:20]) is None)
print("  21 bars -> value :", I.vol20(alt[:21]) is not None)

# adj_close, not close: same closes, different adj_close
flat_close = [bar(b.session, "100", adj_close=f"{b.adj_close:f}") for b in alt]
print("  ignores close    :", I.vol20(flat_close) == value)
same_adj = [bar(b.session, f"{b.adj_close:f}", adj_close="100") for b in alt]
print("  flat adj -> 0    :", I.vol20(same_adj) == ZERO)

# -- 2. traceability counts ----------------------------------------------------------------------
print()
print("== traceability verify() ==")
print(json.dumps({k: v for k, v in T.verify(config).items() if k != "documents"}, indent=2))
print("  documents:", json.dumps(T.verify(config)["documents"]))
print("  named tests:", len(T.all_named_tests()))

# -- 3. warmup derivation ------------------------------------------------------------------------
print()
print("== warmup ==")
print("  rsi_warmup_changes:", config.rsi_warmup_changes)
for experiment in config.experiments:
    specs = R.variant_specs(experiment)
    largest = max(C.largest_lookback(s.parameters, config.rsi_warmup_changes) for s in specs)
    print(
        f"  {experiment['experiment_id']}: sealed={experiment['warmup_sessions']} "
        f"largest_lookback={largest} variants={len(specs)}"
    )

# -- 4. candidate signal fixtures ----------------------------------------------------------------
print()
print("== signal fixtures ==")


def view_at(series, session):
    window = ResearchWindow(name="test", start=dt.date(1990, 1, 1), end=dt.date(2030, 12, 31))
    return MarketView(series, session, window)


def context(session, held=()):
    return DecisionContext(
        session=session, cash=Decimal(100), equity=Decimal(100),
        open_symbols=held, shutdown_active=False,
    )


def synthetic_series(symbol, closes):
    rows = [
        {"session": session.isoformat(), "open": close, "close": close, "split_ratio": "1"}
        for session, close in sorted(closes.items())
    ]
    return series_from_rows(symbol, rows)


def spy(closes):
    return {"SPY": synthetic_series(
        "SPY", {DAY_ZERO + dt.timedelta(days=i): v for i, v in enumerate(closes)}
    )}


def build(experiment_id, parameters, universe):
    return C.build_candidate(
        experiment_id=experiment_id, variant_id=f"{experiment_id}#TEST",
        universe=universe, parameters=parameters, costs=costs,
        rsi_warmup_changes=config.rsi_warmup_changes,
    )


RA1 = {
    "f_base": "0.50", "vol_target": "0.10", "vol_floor_fraction": "0.05",
    "loss_control": "0.08", "max_hold": 20, "reentry_delay": 5,
    "ladder_rungs": [["0.08", "0.25"], ["0.10", "0.125"]],
}

# C1 pullback: 190 bars at 100, 9 at 130, decision bar variable
c1 = build(C.C1, {"sma_long": 200, "sma_short": 10, **RA1}, ("SPY",))
for last, expected in (("120", "SPY"), ("101", None), ("135", None)):
    closes = ["100"] * 190 + ["130"] * 9 + [last]
    series = spy(closes)
    day = DAY_ZERO + dt.timedelta(days=199)
    got = c1.target(view_at(series, day), context(day))
    sma200 = sum(Decimal(v) for v in closes) / 200
    sma10 = sum(Decimal(v) for v in closes[-10:]) / 10
    print(f"  C1 last={last}: sma200={sma200} sma10={sma10} target={got} expected={expected}")
short = spy(["100"] * 190 + ["130"] * 9)
day = DAY_ZERO + dt.timedelta(days=198)
print("  C1 199 bars ->", c1.target(view_at(short, day), context(day)))

# C2 mean reversion: 101 bars
c2 = build(C.C2, {"rsi_period": 2, "rsi_entry_below": 10, "exit_sma": 5, **RA1}, ("SPY",))
falling = [f"{200 - i}" for i in range(101)]
rising = [f"{100 + i}" for i in range(101)]
day = DAY_ZERO + dt.timedelta(days=100)
for label, closes in (("falling", falling), ("rising", rising)):
    series = spy(closes)
    flat_target = c2.target(view_at(series, day), context(day))
    held_target = c2.target(view_at(series, day), context(day, ("SPY",)))
    sma5 = sum(Decimal(v) for v in closes[-5:]) / 5
    print(
        f"  C2 {label}: close={closes[-1]} sma5={sma5} flat->{flat_target} held->{held_target}"
    )
print("  C2 100 bars ->", c2.target(
    view_at(spy(falling[:100]), DAY_ZERO + dt.timedelta(days=99)),
    context(DAY_ZERO + dt.timedelta(days=99)),
))

# C3 defensive: 200 SPY bars
sessions = [DAY_ZERO + dt.timedelta(days=i) for i in range(200)]
for last, expected in (("120", "SPY"), ("80", "SHY")):
    closes = ["100"] * 199 + [last]
    series = {
        "SPY": synthetic_series("SPY", dict(zip(sessions, closes))),
        "SHY": synthetic_series("SHY", {s: "50" for s in sessions}),
    }
    c3 = build(C.C3, {"sma_long": 200, "risk_symbol": "SPY", "defensive_symbol": "SHY", **RA1},
               ("SPY", "SHY"))
    day = sessions[-1]
    sma200 = sum(Decimal(v) for v in closes) / 200
    print(f"  C3 last={last}: sma200={sma200} target={c3.target(view_at(series, day), context(day))}"
          f" expected={expected}")
# SHY absent at t
series["SHY"] = synthetic_series("SHY", {s: "50" for s in sessions[:-1]})
print("  C3 SHY missing at t ->", c3.target(view_at(series, sessions[-1]), context(sessions[-1])))
c3_null = build(C.C3, {"sma_long": 200, "risk_symbol": "SPY", "defensive_symbol": None, **RA1},
                ("SPY", "SHY"))
print("  C3 defensive None ->", c3_null.target(view_at(series, sessions[-1]), context(sessions[-1])))
print("  C3 traded_symbols(null) ->",
      C.traded_symbols(C.C3, ("SPY", "SHY"), {"risk_symbol": "SPY", "defensive_symbol": None}))

# -- 5. source scans the tests will perform ------------------------------------------------------
print()
print("== source scans ==")
MODULES = [
    "attempt2_config", "attempt2_indicators", "attempt2_risk", "attempt2_candidates",
    "attempt2_runner", "attempt2_harness",
]
import importlib

for name in MODULES:
    module = importlib.import_module(f"stockedge100.strategies.{name}")
    source = inspect.getsource(module)
    hits = [t for t in ("rolling_max_close", "rolling_min_close", "momentum(") if t in source]
    floats = "float(" in source
    print(f"  {name}: unused_indicator_hits={hits} 'float('={floats}")

risk_source = inspect.getsource(
    importlib.import_module("stockedge100.strategies.attempt2_risk")
)
for token in ("0.15", "0.1499", "0.14", "15%"):
    print(f"  attempt2_risk contains {token!r}: {token in risk_source}")

print()
print("PINNED - no evaluation was executed")
