"""Run the RA1 test module's two synthetic fixtures under RA3 before the assertions are written.

The RA1 fixtures were tuned against RA2's ladder: the crash fixture's ~7.5% portfolio drawdown was
chosen to land in RA2's *second* band. Under RA3 that same drawdown stays in band 0, so every
downstream count the RA3 tests would assert (fills, stops, preemptions, clamp bindings) is an open
question rather than a carry-over. Measure them instead of guessing.

Nothing here writes; the fixtures are synthetic and never touch data/.
"""

import datetime as dt
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import BASE, ZERO
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.backtest.g2_engine_ra1 import CLAMP_NAMES_RA2, load_risk_architecture
from stockedge100.backtest.g2_engine_ra3 import RotationEngineRA3, load_risk_architecture_ra3
from stockedge100.backtest.orders import BUY
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies import g2_rotation_ra3 as rot
from stockedge100.strategies import g2_window_guard as guard

ONE = Decimal(1)
SYMBOLS = ("AAA", "BBB", "CCC", "DDD", "EEE")
OPEN_DISCOUNT = Decimal("0.25")
FIRST = dt.date(2010, 1, 4)
LAST = dt.date(2011, 6, 30)
CRASH_SESSION = dt.date(2010, 6, 15)
PREEMPT_SESSION = dt.date(2010, 7, 1)
CRASH_FRACTION = Decimal("0.15")
CRASH_DRIFTS = {"AAA": "0.10", "BBB": "0.08", "CCC": "0.06", "DDD": "0.04", "EEE": "0.02"}

PREFIX = "SE100-G2-S3-C3-ROTATION-RA3-L03-K%d-MONTHLY"
K1, K2, K3 = (PREFIX % k for k in (1, 2, 3))


def _rows(sessions, closes):
    return [
        {
            "session": s.isoformat(),
            "open": f"{c - OPEN_DISCOUNT}",
            "high": f"{c}",
            "low": f"{c - OPEN_DISCOUNT}",
            "close": f"{c}",
        }
        for s, c in zip(sessions, closes)
    ]


def build_growth_series(*, bump=None):
    sessions = sessions_between(FIRST, LAST)
    months = []
    for day in sessions:
        key = (day.year, day.month)
        if key not in months:
            months.append(key)
    rates = (Decimal(4), Decimal(3), Decimal(2), Decimal(1), ZERO)
    series = {}
    for index, symbol in enumerate(SYMBOLS):
        close = Decimal(200 + 10 * index)
        closes = []
        for day in sessions:
            close += rates[(index + months.index((day.year, day.month))) % len(rates)]
            shift = Decimal(bump[2]) if bump and bump[0] == symbol and day >= bump[1] else ZERO
            closes.append(close + shift)
        series[symbol] = series_from_rows(symbol, _rows(sessions, closes))
    return series


def build_crash_series(crash_session=CRASH_SESSION):
    sessions = sessions_between(FIRST, LAST)
    series = {}
    for symbol in SYMBOLS:
        close = Decimal(200)
        drift = Decimal(CRASH_DRIFTS[symbol])
        closes = []
        crashed = False
        for day in sessions:
            if symbol == "AAA" and day == crash_session:
                close = (close * (ONE - CRASH_FRACTION)).quantize(Decimal("0.01"))
                crashed = True
            elif symbol == "AAA" and crashed:
                pass
            else:
                close += drift
            closes.append(close)
        series[symbol] = series_from_rows(symbol, _rows(sessions, closes))
    return series


WINDOW = guard.generation_2_window("g2_ra3_fixture", "2009-12-01", "2011-12-31")


def make_engine(series, variant_id, *, risk=None, end=None):
    variant = rot.variant_by_id(variant_id)
    candidate = rot.RotationCandidateRA3(
        variant, rot.rotation_cost_model(variant.top_k, BASE), universe=SYMBOLS
    )
    sessions = series[SYMBOLS[0]].sessions
    engine = RotationEngineRA3(
        series, candidate.costs, WINDOW, candidate,
        start=sessions[0], end=end or sessions[-1],
        label=variant_id, budget_weight=candidate.weight,
    )
    if risk is not None:
        engine.risk = risk
    return engine, candidate, variant


def run(series, variant_id, **kw):
    engine, candidate, variant = make_engine(series, variant_id, **kw)
    return engine.run(), engine, candidate, variant


print("CLAMP_NAMES_RA2 =", CLAMP_NAMES_RA2)
print()

print("== growth fixture, k=3 ==")
result, engine, cand, _ = run(build_growth_series(), K3)
print("   fills=%d trades=%d shutdown=%s" % (len(result.fills), len(result.trades),
                                             result.shutdown_session))
print("   symbols traded:", sorted({r.fill.symbol for r in result.fills}))
print("   binding_clamp_counts:", dict(engine.binding_clamp_counts))
print("   ladder descents=%s ascents=%s deepest=%s lockout_arms=%s"
      % (engine.ladder_descents, engine.ladder_ascents, engine.deepest_band, engine.lockout_arms))
print("   vol_scalar_min=%s below_one=%s undefined=%s"
      % (engine.vol_scalar_min, engine.vol_scalar_sessions_below_one,
         engine.vol_scalar_undefined_sessions))
print("   stops triggered=%s filled=%s"
      % (engine.risk_summary()["stops"]["triggered"], engine.risk_summary()["stops"]["filled"]))
print("   min_order_notional=%s" % cand.costs.min_order_notional)

# peak exposure replay
cash = result.starting_equity
qty = {}
peak = ZERO
series_g = build_growth_series()
for record in result.fills:
    fill, session = record.fill, record.session
    marks = {s: series_g[s].bars[session].open for s in qty}
    before = cash + sum((qty[s] * marks[s] for s in qty), ZERO)
    cash += fill.cash_delta
    held = qty.get(fill.symbol, ZERO)
    held = held + fill.quantity if fill.side == BUY else held - fill.quantity
    if held == ZERO:
        qty.pop(fill.symbol, None)
    else:
        qty[fill.symbol] = held
    after = dict(marks)
    after[fill.symbol] = fill.reference_price
    gross = sum((qty[s] * after[s] for s in qty), ZERO)
    if before > ZERO:
        peak = max(peak, gross / before)
print("   replay final cash matches: %s" % (cash == result.final_cash))
print("   peak exposure fraction: %s" % peak)

print()
print("== growth fixture, k=3, budget_weight forced to 0.30 (AT-A binding test) ==")
engine, cand, _ = make_engine(build_growth_series(), K3)
engine.budget_weight = Decimal("0.30")
res2 = engine.run()
print("   binding_clamp_counts:", dict(engine.binding_clamp_counts))
cash = res2.starting_equity
qty = {}
peak2 = ZERO
for record in res2.fills:
    fill, session = record.fill, record.session
    marks = {s: series_g[s].bars[session].open for s in qty}
    before = cash + sum((qty[s] * marks[s] for s in qty), ZERO)
    cash += fill.cash_delta
    held = qty.get(fill.symbol, ZERO)
    held = held + fill.quantity if fill.side == BUY else held - fill.quantity
    if held == ZERO:
        qty.pop(fill.symbol, None)
    else:
        qty[fill.symbol] = held
    after = dict(marks)
    after[fill.symbol] = fill.reference_price
    gross = sum((qty[s] * after[s] for s in qty), ZERO)
    if before > ZERO:
        peak2 = max(peak2, gross / before)
print("   peak exposure fraction: %s" % peak2)

print()
for label, session in (("CRASH_SESSION", CRASH_SESSION), ("PREEMPT_SESSION", PREEMPT_SESSION)):
    print("== crash fixture (%s), k=1 ==" % label)
    crash = build_crash_series(session)
    result, engine, cand, _ = run(crash, K1)
    rs = engine.risk_summary()
    print("   fills=%d shutdown=%s" % (len(result.fills), result.shutdown_session))
    print("   stops triggered=%s filled=%s" % (rs["stops"]["triggered"], rs["stops"]["filled"]))
    print("   stop_events=%d  stop_preempted_signal_exit=%s"
          % (len(engine.stop_events), engine.stop_preempted_signal_exit))
    print("   ladder descents=%s ascents=%s deepest=%s recoveries_blocked=%s"
          % (engine.ladder_descents, engine.ladder_ascents, engine.deepest_band,
             engine.recoveries_blocked))
    print("   suppressed_legs=%d" % len(engine.suppressed_legs))
    print("   stop_events type=%s" % type(engine.stop_events).__name__)
    if isinstance(engine.stop_events, dict):
        for key in sorted(engine.stop_events):
            print("   stop event %s -> %s" % (key, engine.stop_events[key]))
    else:
        for entry in engine.stop_events:
            print("   stop event -> %s" % (entry,))
    print("   suppressed_legs sample: %s" % (engine.suppressed_legs[:2],))
    print("   risk_state_digest=%s" % engine.risk_state_digest())
    print("   trades_digest=%s" % result.trades_digest()[:16])
    print("   fills: %s" % [(r.session.isoformat(), r.fill.symbol, r.fill.side,
                             str(r.fill.reference_price)) for r in result.fills])

print()
print("== RA3 vs RA2 at 6% drawdown ==")
ra3 = load_risk_architecture_ra3()
ra2 = load_risk_architecture()
d = Decimal("0.06")
print("   RA3 band_for(0.06)=%s scalar=%s" % (ra3.band_for(d), ra3.scalar_of(ra3.band_for(d))))
print("   RA2 band_for(0.06)=%s scalar=%s" % (ra2.band_for(d), ra2.scalar_of(ra2.band_for(d))))
print("   RA3 absolute ceilings: %s"
      % [str((ra3.exposure_ceiling * b.scalar).quantize(Decimal("0.000000001")))
         for b in ra3.bands])
