"""Sixth preflight: the three remaining injections (AT-B target, AT-H digests, AT-M attributes)."""

import copy
import dataclasses
import datetime as dt
import pathlib
import sys
import types
from decimal import Decimal

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import BASE, ZERO
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.backtest.engine import EquityPoint
from stockedge100.backtest import g2_engine_ra3 as eng3
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies import g2_rotation_ra3 as rot
from stockedge100.strategies import g2_runner_ra3 as runner
from stockedge100.strategies import g2_window_guard as guard
from stockedge100.strategies.attempt2_indicators import VOL20_BARS


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


ONE = Decimal(1)
SYMBOLS = ("AAA", "BBB", "CCC", "DDD", "EEE")
OPEN_DISCOUNT = Decimal("0.25")
FIRST = dt.date(2010, 1, 4)
LAST = dt.date(2010, 6, 30)
WINDOW = guard.generation_2_window("g2_ra3_fixture", "2009-12-01", "2011-12-31")
K3 = "SE100-G2-S3-C3-ROTATION-RA3-L03-K3-MONTHLY"
HIGH_VOL_LEVELS = tuple(Decimal(1000) if i % 2 == 0 else Decimal(1020) for i in range(VOL20_BARS))


def tiny_series():
    sessions = sessions_between(FIRST, LAST)
    out = {}
    for index, symbol in enumerate(SYMBOLS):
        closes = [Decimal(200 + 10 * index) + Decimal(i) for i in range(len(sessions))]
        out[symbol] = series_from_rows(symbol, [
            {"session": s.isoformat(), "open": f"{c - OPEN_DISCOUNT}", "high": f"{c}",
             "low": f"{c - OPEN_DISCOUNT}", "close": f"{c}"}
            for s, c in zip(sessions, closes)
        ])
    return out


def make_engine(series, risk=None):
    variant = rot.variant_by_id(K3)
    candidate = rot.RotationCandidateRA3(
        variant, rot.rotation_cost_model(variant.top_k, BASE), universe=SYMBOLS)
    sessions = series[SYMBOLS[0]].sessions
    engine = eng3.RotationEngineRA3(
        series, candidate.costs, WINDOW, candidate, start=sessions[0], end=sessions[-1],
        label=K3, budget_weight=candidate.weight)
    if risk is not None:
        engine.risk = risk
    return engine


def seed(engine, levels):
    engine._equity = [
        EquityPoint(session=FIRST + dt.timedelta(days=i), cash=ZERO, equity=level,
                    stale_mark=False, position_count=0)
        for i, level in enumerate(levels)
    ]


series = tiny_series()
arch3 = eng3.load_risk_architecture_ra3()

print("=" * 100)
print("B. injection: the volatility target is load-bearing")
e = make_engine(series)
seed(e, HIGH_VOL_LEVELS)
print("   sealed target 0.10 -> %s" % e._volatility_scalar())
loose = dataclasses.replace(arch3, volatility_target=Decimal("1.00"))
e2 = make_engine(series, risk=loose)
seed(e2, HIGH_VOL_LEVELS)
print("   target widened 1.00 -> %s (below_one=%s)"
      % (e2._volatility_scalar(), e2.vol_scalar_sessions_below_one))
tight = dataclasses.replace(arch3, volatility_target=Decimal("0.05"))
e3 = make_engine(series, risk=tight)
seed(e3, HIGH_VOL_LEVELS)
print("   target tightened 0.05 -> %s" % e3._volatility_scalar())

print()
print("=" * 100)
print("H. injections into verify_prior_attempt_modules")
clean = runner.verify_prior_attempt_modules()
print("   clean -> module_count=%s a1=%s a2=%s moved=%s"
      % (clean["module_count"], clean["attempt_1_module_count"],
         clean["attempt_2_module_count"], clean["modules_that_moved"]))
print("   digest_source=%s" % clean["digest_source"])
print("   conflict_ref=%s" % clean["conflict_ref"])
print("   first three verified: %s" % sorted(clean["modules_verified"])[:3])
print("   excluded_and_why=%s" % safe(clean["excluded_and_why"])[:220])
print("   attempt_1_list_source=%s" % safe(clean["attempt_1_list_source"])[:160])

GOV = runner._governance_protocol()
DECL = runner.load_protocol()["prior_attempt_modules_immutable"]
print("   declared keys=%s count=%s" % (sorted(DECL), DECL["count"]))


def inject(name, gov_mutate=None, decl_mutate=None):
    gov = copy.deepcopy(GOV)
    proto = copy.deepcopy(runner.load_protocol())
    if gov_mutate:
        gov_mutate(gov)
    if decl_mutate:
        decl_mutate(proto["prior_attempt_modules_immutable"])
    saved_g, saved_p = runner._governance_protocol, runner.load_protocol
    runner._governance_protocol = lambda: gov
    runner.load_protocol = lambda: proto
    try:
        runner.verify_prior_attempt_modules()
        print("   %-50s -> NO RAISE" % name)
    except Exception as exc:                                          # noqa: BLE001
        print("   %-50s -> %s: %s" % (name, type(exc).__name__, safe(str(exc))[:190]))
    finally:
        runner._governance_protocol = saved_g
        runner.load_protocol = saved_p


inject("clean monkeypatch control", None, None)


def tamper_digest(gov):
    node = gov["contamination_measurement"]["prior_attempt_module_digests"]
    key = sorted(node)[0]
    node[key] = "0" * 64


inject("one recorded digest altered", tamper_digest)


def duplicate(decl):
    decl["attempt_2_modules"] = list(decl["attempt_2_modules"])
    decl["attempt_1_modules"] = list(decl["attempt_1_modules"])
    decl["attempt_2_modules"][0] = decl["attempt_1_modules"][0]


inject("a path listed under both attempts", None, duplicate)


def miscount(decl):
    decl["count"] = int(decl["count"]) + 1


inject("declared count raised by one", None, miscount)


def drop_from_governance(gov):
    node = gov["contamination_measurement"]["prior_attempt_module_digests"]
    node.pop(sorted(node)[0])


inject("one module dropped from the governance seal", drop_from_governance)

print()
print("=" * 100)
print("M. injection: RISK_DERIVED_ATTRIBUTES narrowed")
SOURCE_PATH = pathlib.Path(eng3.__file__)
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
LITERAL = 'RISK_DERIVED_ATTRIBUTES = frozenset({"risk", "sessions_in_band"})'
print("   literal occurrences: %d" % SOURCE.count(LITERAL))


def exec_as_module(source, name):
    module = types.ModuleType(name)
    module.__file__ = str(SOURCE_PATH)
    sys.modules[name] = module
    try:
        exec(compile(source, str(SOURCE_PATH), "exec"), module.__dict__)
        return module.__dict__
    finally:
        sys.modules.pop(name, None)


try:
    ns = exec_as_module(SOURCE, "_ra3_clean_probe")
    print("   clean source -> executed, RISK_DERIVED_ATTRIBUTES=%s"
          % sorted(ns["RISK_DERIVED_ATTRIBUTES"]))
except Exception as exc:                                              # noqa: BLE001
    print("   clean source -> %s: %s" % (type(exc).__name__, safe(str(exc))[:200]))

narrowed = SOURCE.replace(LITERAL, 'RISK_DERIVED_ATTRIBUTES = frozenset({"risk"})')
try:
    exec_as_module(narrowed, "_ra3_narrowed_probe")
    print("   narrowed -> NO RAISE")
except Exception as exc:                                              # noqa: BLE001
    print("   narrowed -> %s: %s" % (type(exc).__name__, safe(str(exc))[:250]))

widened = SOURCE.replace(
    LITERAL, 'RISK_DERIVED_ATTRIBUTES = frozenset({"risk", "sessions_in_band", "budget_weight"})')
try:
    exec_as_module(widened, "_ra3_widened_probe")
    print("   widened  -> NO RAISE")
except Exception as exc:                                              # noqa: BLE001
    print("   widened  -> %s: %s" % (type(exc).__name__, safe(str(exc))[:250]))

print()
print("=" * 100)
print("G. a tmp copy of the protocol declaring attempt 2")
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    import json
    doc = json.loads(eng3.PROTOCOL_PATH.read_text(encoding="utf-8"))
    doc["attempt"] = 2
    path = pathlib.Path(tmp) / "g2_rotation_ra3_protocol.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    saved = eng3.PROTOCOL_PATH
    eng3.PROTOCOL_PATH = path
    try:
        eng3.load_ra3_protocol()
        print("   attempt=2 copy -> NO RAISE")
    except Exception as exc:                                          # noqa: BLE001
        print("   attempt=2 copy -> %s: %s" % (type(exc).__name__, safe(str(exc))[:190]))
    finally:
        eng3.PROTOCOL_PATH = saved

    eng3.PROTOCOL_PATH = pathlib.Path(tmp) / "absent.json"
    try:
        eng3.load_ra3_protocol()
        print("   missing file   -> NO RAISE")
    except Exception as exc:                                          # noqa: BLE001
        print("   missing file   -> %s: %s" % (type(exc).__name__, safe(str(exc))[:120]))
    finally:
        eng3.PROTOCOL_PATH = saved
