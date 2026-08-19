"""Pre-flight: run every AT-A..AT-F computation the test module will assert, and print the answers.

The RA1 fixtures were tuned against RA2's four-band ladder. Under RA3 the same synthetic prices sit
in band 0 throughout, so every count, fraction and excess the RA1 module pinned is an open question
here. Measuring them before the assertions are typed is the whole point: an assertion written from
the RA1 file and then "fixed" until it passes would be asserting the implementation's behaviour
rather than the seal's requirement.

Writes nothing. Synthetic prices only; data/ is never opened.
"""

import ast
import dataclasses
import datetime as dt
import inspect
import pathlib
import sys
from decimal import Decimal, localcontext

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import BASE, ZERO
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.backtest.engine import EquityPoint
from stockedge100.backtest.g2_engine_ra1 import (
    CLAMP_NAMES_RA2, ORDER_KIND_PRECEDENCE, RotationEngineRA1, SCALAR_DECIMALS,
    load_risk_architecture, quantize_scalar)
from stockedge100.backtest.g2_engine_ra3 import (
    RISK_DERIVED_ATTRIBUTES, RotationEngineRA3, attributes_derived_from_risk,
    load_risk_architecture_ra3)
from stockedge100.backtest.orders import BUY
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies import g2_rotation_ra3 as rot
from stockedge100.strategies import g2_window_guard as guard
from stockedge100.strategies.attempt2_indicators import (
    TRADING_DAYS_PER_YEAR, VOL20_BARS, VOL20_RETURNS, VOL20_VARIANCE_DENOMINATOR)

ONE = Decimal(1)
NOMINAL_CEILING = Decimal("0.50")
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
WINDOW = guard.generation_2_window("g2_ra3_fixture", "2009-12-01", "2011-12-31")


def _rows(sessions, closes):
    return [
        {"session": s.isoformat(), "open": f"{c - OPEN_DISCOUNT}", "high": f"{c}",
         "low": f"{c - OPEN_DISCOUNT}", "close": f"{c}"}
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


def exposure_report(result, series):
    cash = result.starting_equity
    quantities = {}
    records = []
    for record in result.fills:
        fill, session = record.fill, record.session
        marks = {s: series[s].bars[session].open for s in quantities}
        equity_before = cash + sum((quantities[s] * marks[s] for s in quantities), ZERO)
        cash += fill.cash_delta
        held = quantities.get(fill.symbol, ZERO)
        held = held + fill.quantity if fill.side == BUY else held - fill.quantity
        if held == ZERO:
            quantities.pop(fill.symbol, None)
        else:
            quantities[fill.symbol] = held
        after = dict(marks)
        after[fill.symbol] = fill.reference_price
        gross = sum((quantities[s] * after[s] for s in quantities), ZERO)
        records.append({
            "session": session, "symbol": fill.symbol, "side": fill.side,
            "equity_before": equity_before, "gross_after": gross,
            "fraction": (gross / equity_before) if equity_before > ZERO else ZERO,
            "open_positions": len(quantities),
        })
    assert cash == result.final_cash
    return records


def scalars_by_session(engine):
    out = {}
    for line in engine.risk_state_payload().splitlines():
        session, _band, _lock, _vol, combined = line.split("|")
        out[dt.date.fromisoformat(session)] = Decimal(combined)
    return out


print("=" * 100)
print("A. AT-A across k=1,2,3 at the grid's own weights, and k=3 forced to 0.30")

growth = build_growth_series()
sessions = list(growth[SYMBOLS[0]].sessions)

for label, variant_id, weight in (
    ("k=1", K1, None), ("k=2", K2, None), ("k=3", K3, None), ("k=3 @0.30", K3, Decimal("0.30")),
):
    engine, candidate, _ = make_engine(growth, variant_id)
    if weight is not None:
        engine.budget_weight = weight
    result = engine.run()
    records = exposure_report(result, growth)
    scalars = scalars_by_session(engine)

    buys = [r for r in records if r["side"] == BUY]
    sells = [r for r in records if r["side"] != BUY]
    # claim (1): every BUY at or under the scaled ceiling
    breaches_scaled = []
    for record in buys:
        decided = sessions[sessions.index(record["session"]) - 1]
        ceiling = NOMINAL_CEILING * scalars[decided] * record["equity_before"]
        if record["gross_after"] > ceiling:
            breaches_scaled.append((record["session"], record["symbol"],
                                    record["gross_after"] - ceiling))
    # claim (2): no SELL raises gross within the same session
    sell_raises = []
    for index, record in enumerate(records):
        if record["side"] == BUY or index == 0:
            continue
        previous = records[index - 1]
        if previous["session"] != record["session"]:
            continue
        if record["gross_after"] > previous["gross_after"]:
            sell_raises.append((record["session"], record["symbol"]))
    # claim (3): residual drift over the nominal ceiling
    over = [(r, r["gross_after"] - NOMINAL_CEILING * r["equity_before"]) for r in records
            if r["gross_after"] > NOMINAL_CEILING * r["equity_before"]]

    print("  -- %s --" % label)
    print("     fills=%d buys=%d sells=%d  starting_equity=%s"
          % (len(records), len(buys), len(sells), result.starting_equity))
    print("     peak fraction=%s" % max(r["fraction"] for r in records))
    print("     scaled-ceiling breaches after a BUY: %d %s" % (len(breaches_scaled),
                                                               breaches_scaled[:3]))
    print("     sells that raised gross: %d" % len(sell_raises))
    print("     records over nominal 0.50: %d  worst excess=%s  min_lot=%s"
          % (len(over), max((e for _, e in over), default=ZERO),
             candidate.costs.min_order_notional))
    print("     over-nominal sides: %s" % sorted({r["side"] for r, _ in over}))
    print("     binding_clamp_counts=%s" % dict(engine.binding_clamp_counts))
    print("     distinct combined scalars: %s" % sorted({str(v) for v in scalars.values()})[:6])

print()
print("  -- injection: 0.95 exposure ceiling, k=3 @0.30 --")
arch3 = load_risk_architecture_ra3()
loosened = dataclasses.replace(arch3, exposure_ceiling=Decimal("0.95"))
engine, candidate, _ = make_engine(growth, K3, risk=loosened)
engine.budget_weight = Decimal("0.30")
records = exposure_report(engine.run(), growth)
over = [r["gross_after"] - NOMINAL_CEILING * r["equity_before"] for r in records
        if r["gross_after"] > NOMINAL_CEILING * r["equity_before"]]
print("     breaches of nominal 0.50: %d  worst=%s  min_lot=%s  peak=%s"
      % (len(over), max(over, default=ZERO), candidate.costs.min_order_notional,
         max(r["fraction"] for r in records)))
print("     injection at k=1 (must be inert, per the RA1 note): ", end="")
engine1, cand1, _ = make_engine(growth, K1, risk=loosened)
rec1 = exposure_report(engine1.run(), growth)
over1 = [r["gross_after"] - NOMINAL_CEILING * r["equity_before"] for r in rec1
         if r["gross_after"] > NOMINAL_CEILING * r["equity_before"]]
print("breaches=%d worst=%s" % (len(over1), max(over1, default=ZERO)))

print()
print("=" * 100)
print("B. AT-B volatility scalar")

HIGH_VOL_LEVELS = tuple(Decimal(1000) if i % 2 == 0 else Decimal(1020) for i in range(VOL20_BARS))


def independent_vol_scalar(levels):
    with localcontext() as ctx:
        ctx.prec = 60
        w = list(levels)[-VOL20_BARS:]
        returns = [w[i] / w[i - 1] - ONE for i in range(1, VOL20_BARS)]
        assert len(returns) == VOL20_RETURNS
        mean = sum(returns) / Decimal(VOL20_RETURNS)
        squares = sum((v - mean) ** 2 for v in returns)
        sigma = (squares / Decimal(VOL20_VARIANCE_DENOMINATOR)).sqrt() * Decimal(
            TRADING_DAYS_PER_YEAR).sqrt()
        target = Decimal("0.10")
        return sigma, (ONE if sigma <= ZERO else min(ONE, target / sigma))


def _seed_equity(engine, levels):
    engine._equity = [
        EquityPoint(session=dt.date(2010, 1, 4) + dt.timedelta(days=i), cash=ZERO, equity=level,
                    stale_mark=False, position_count=0)
        for i, level in enumerate(levels)
    ]


sigma, expected = independent_vol_scalar(HIGH_VOL_LEVELS)
engine, _, _ = make_engine(growth, K3)
_seed_equity(engine, HIGH_VOL_LEVELS)
actual = engine._volatility_scalar()
print("   VOL20_BARS=%s VOL20_RETURNS=%s denom=%s TRADING_DAYS=%s SCALAR_DECIMALS=%s"
      % (VOL20_BARS, VOL20_RETURNS, VOL20_VARIANCE_DENOMINATOR, TRADING_DAYS_PER_YEAR,
         SCALAR_DECIMALS))
print("   sigma=%s expected=%s actual=%s diff=%s" % (sigma, expected, actual, abs(actual - expected)))
print("   quantized equal: %s  below_one=%s min=%s"
      % (actual == quantize_scalar(actual), engine.vol_scalar_sessions_below_one,
         engine.vol_scalar_min))

engine, _, _ = make_engine(growth, K3)
_seed_equity(engine, tuple(Decimal(1000) for _ in range(VOL20_BARS)))
print("   flat curve -> %s" % engine._volatility_scalar())

engine, _, _ = make_engine(growth, K3)
_seed_equity(engine, tuple(Decimal(1000) for _ in range(VOL20_BARS - 1)))
short = engine._volatility_scalar()
print("   short window -> %s undefined=%s" % (short, engine.vol_scalar_undefined_sessions))

engine, _, _ = make_engine(growth, K3)
quiet = tuple(Decimal(1000) + Decimal(i) / Decimal(1000) for i in range(VOL20_BARS))
_seed_equity(engine, quiet)
print("   quiet curve -> %s (mirror control: must be 1)" % engine._volatility_scalar())

print()
print("=" * 100)
print("C. AT-C stop mechanics")
for label, session in (("CRASH", CRASH_SESSION), ("PREEMPT", PREEMPT_SESSION)):
    crash = build_crash_series(session)
    result, engine, candidate, _ = run(crash, K1)
    rs = engine.risk_summary()
    by_order = {e["order_id"]: e for e in engine.stop_events}
    print("   -- %s --" % label)
    print("      stops triggered=%s filled=%s events=%d preempted=%s suppressed=%d"
          % (rs["stops"]["triggered"], rs["stops"]["filled"], len(engine.stop_events),
             engine.stop_preempted_signal_exit, len(engine.suppressed_legs)))
    print("      risk_summary()['stops'] keys: %s" % sorted(rs["stops"]))
    print("      fill entries: %s" % rs["stops"].get("fills"))
    held = {}
    for record in result.fills:
        f = record.fill
        oid = getattr(f, "order_id", None) or getattr(record, "order_id", None)
        if oid in by_order:
            print("      matched stop fill: order=%s session=%s qty=%s held_before=%s open=%s"
                  % (oid, record.session, f.quantity, held.get(f.symbol),
                     crash[f.symbol].bars[record.session].open))
        held[f.symbol] = held.get(f.symbol, ZERO) + (f.quantity if f.side == BUY else -f.quantity)
    print("      record attrs: %s" % [n for n in dir(result.fills[0]) if not n.startswith("_")])
    print("      fill attrs:   %s" % [n for n in dir(result.fills[0].fill) if not n.startswith("_")])

print("   -- injection: stop_fraction 1.00 --")
no_stop = dataclasses.replace(arch3, stop_fraction=Decimal("1.00"))
_, engine, _, _ = run(build_crash_series(), K1, risk=no_stop)
print("      triggered=%s filled=%s events=%d"
      % (engine.risk_summary()["stops"]["triggered"], engine.risk_summary()["stops"]["filled"],
         len(engine.stop_events)))
print("   ORDER_KIND_PRECEDENCE=%s" % (ORDER_KIND_PRECEDENCE,))

print()
print("=" * 100)
print("D. AT-D ladder driven directly")
HIGH_WATER = Decimal(1000)


def _equity_for(dd):
    return HIGH_WATER * (ONE - dd)


def _drive(engine, path):
    seen = []
    for index, equity in path:
        engine._advance_ladder(index, equity)
        seen.append(engine._band)
    return seen


print("   _advance_ladder sig: %s" % inspect.signature(RotationEngineRA1._advance_ladder))
print("   bands: %s" % [(b.band, str(b.dd_from), str(b.dd_to_exclusive), str(b.scalar))
                        for b in arch3.bands])
print("   band_for/scalar_of at the boundaries:")
for dd in ("0.00", "0.05", "0.06", "0.0799", "0.08", "0.0999", "0.10", "0.30"):
    b = arch3.band_for(Decimal(dd))
    print("      dd=%-7s band=%s scalar=%s" % (dd, b, arch3.scalar_of(b)))

engine, _, _ = make_engine(growth, K3)
engine._high_water = HIGH_WATER
down = [(i, _equity_for(Decimal(d)))
        for i, d in enumerate(("0.00", "0.06", "0.09", "0.12"))]
print("   descent path bands: %s" % _drive(engine, down))
print("   descents=%s deepest=%s arms=%s lockout_until=%s"
      % (engine.ladder_descents, engine.deepest_band, engine.lockout_arms,
         engine._lockout_until_index))
up = [(i, _equity_for(Decimal("0.00"))) for i in range(4, 26)]
print("   recovery bands: %s" % _drive(engine, up))
print("   ascents=%s blocked=%s sessions_in_band=%s"
      % (engine.ladder_ascents, engine.recoveries_blocked, dict(engine.sessions_in_band)))

print()
print("   RA3 vs RA2 at exactly 6%%:")
ra2 = load_risk_architecture()
d6 = Decimal("0.06")
print("      RA3 band=%s scalar=%s | RA2 band=%s scalar=%s"
      % (arch3.band_for(d6), arch3.scalar_of(arch3.band_for(d6)),
         ra2.band_for(d6), ra2.scalar_of(ra2.band_for(d6))))
engine, _, _ = make_engine(growth, K3)
engine._high_water = HIGH_WATER
_drive(engine, [(0, HIGH_WATER), (1, _equity_for(d6))])
print("      driving RA3 to 6%%: band=%s descents=%s" % (engine._band, engine.ladder_descents))

print()
print("   -- AT-E lockout arithmetic --")
engine, _, _ = make_engine(growth, K3)
engine._high_water = HIGH_WATER
_drive(engine, [(i, HIGH_WATER) for i in range(4)])
engine._advance_ladder(4, _equity_for(Decimal("0.12")))
print("      descent at 4 -> band=%s lockout_until=%s lockout_sessions=%s"
      % (engine._band, engine._lockout_until_index, arch3.lockout_sessions))
blocked = 0
for index in range(5, 4 + arch3.lockout_sessions):
    engine._advance_ladder(index, HIGH_WATER)
    if engine._band != 0:
        blocked += 1
print("      probes 5..%d blocked=%d recoveries_blocked=%s ascents=%s"
      % (4 + arch3.lockout_sessions - 1, blocked, engine.recoveries_blocked,
         engine.ladder_ascents))
print("      _lockout_remaining(5)=%s" % engine._lockout_remaining(5))
engine._advance_ladder(4 + arch3.lockout_sessions, HIGH_WATER)
print("      at 4+%d -> band=%s ascents=%s" % (arch3.lockout_sessions, engine._band,
                                               engine.ladder_ascents))

print()
print("   -- AT-D injection: single open-ended band --")
flat = dataclasses.replace(arch3, bands=(dataclasses.replace(arch3.bands[0],
                                                             dd_to_exclusive=None),))
engine, _, _ = make_engine(growth, K3, risk=flat)
engine.sessions_in_band = {0: 0}
engine._high_water = HIGH_WATER
print("      bands after injection: %s" % [(b.band, str(b.dd_from), str(b.dd_to_exclusive))
                                           for b in flat.bands])
print("      driven bands: %s descents=%s"
      % (_drive(engine, [(0, HIGH_WATER), (1, _equity_for(Decimal("0.30")))]),
         engine.ladder_descents))

print()
print("=" * 100)
print("F. AT-F determinism")


def digests(result, engine, candidate):
    return {"trades": result.trades_digest(), "equity": result.equity_digest(),
            "ranking": candidate.evidence()["ranking_digest"],
            "risk_state": engine.risk_state_digest()}


for variant_id in (K1, K2, K3):
    r1, e1, c1, _ = run(build_growth_series(), variant_id)
    r2, e2, c2, _ = run(build_growth_series(), variant_id)
    d1, d2 = digests(r1, e1, c1), digests(r2, e2, c2)
    print("   %s equal=%s distinct=%d lens=%s"
          % (variant_id.rsplit("RA3-", 1)[-1], d1 == d2, len(set(d1.values())),
             sorted({len(v) for v in d1.values()})))

r1, e1, c1, _ = run(build_growth_series(), K3)
r2, e2, c2, _ = run(build_growth_series(bump=("AAA", dt.date(2010, 6, 15), 40)), K3)
base, bumped = digests(r1, e1, c1), digests(r2, e2, c2)
print("   bump moves: %s" % {k: base[k] != bumped[k] for k in base})

r1, e1, c1, _ = run(build_crash_series(CRASH_SESSION), K1)
r2, e2, c2, _ = run(build_crash_series(PREEMPT_SESSION), K1)
a, b = digests(r1, e1, c1), digests(r2, e2, c2)
print("   crash-session shift moves: %s" % {k: a[k] != b[k] for k in a})
print("   payload lines == equity points: %s (%d vs %d)"
      % (e1.risk_state_payload().count("\n") == len(e1._equity),
         e1.risk_state_payload().count("\n"), len(e1._equity)))

print()
print("=" * 100)
print("M. AT-M attribute derivation")
print("   RISK_DERIVED_ATTRIBUTES        = %s" % sorted(RISK_DERIVED_ATTRIBUTES))
print("   derived from RotationEngineRA1 = %s" % sorted(attributes_derived_from_risk(RotationEngineRA1)))
print("   derived from RotationEngineRA3 = %s" % sorted(attributes_derived_from_risk(RotationEngineRA3)))
src = inspect.getsource(RotationEngineRA3.__init__)
tree = ast.parse("\n".join(line[4:] if line.startswith("    ") else line
                           for line in src.splitlines()))
assigned = sorted({
    t.attr for node in ast.walk(tree)
    for t in (node.targets if isinstance(node, ast.Assign) else
              [node.target] if isinstance(node, (ast.AnnAssign, ast.AugAssign)) else [])
    if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self"
})
print("   RA3.__init__ assigns           = %s" % assigned)
print("   guard source line: %s" % inspect.getsource(RotationEngineRA3).splitlines()[0])
