"""Fifth preflight: the RA3 protocol's component shape and the in-memory ladder injections."""

import copy
import json
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest import g2_engine_ra3 as eng3


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


PROTO = json.loads(eng3.PROTOCOL_PATH.read_text(encoding="utf-8"))
ARCHNODE = PROTO["risk_architecture"]

print("architecture node keys: %s" % sorted(ARCHNODE))
print("components:")
for name, node in ARCHNODE["components"].items():
    print("   %-8s keys=%s" % (name, sorted(node)))
print()
print("combined_scalar keys=%s" % sorted(ARCHNODE["combined_scalar"]))
print(safe(json.dumps(ARCHNODE["combined_scalar"], indent=3))[:900])

LADDER = next(name for name, node in ARCHNODE["components"].items() if "bands" in node)
print()
print("ladder component = %r" % LADDER)
print(safe(json.dumps(ARCHNODE["components"][LADDER], indent=3))[:1200])

print()
print("to_json():")
print(safe(json.dumps(eng3.load_risk_architecture_ra3().to_json(), indent=3))[:1400])

print()
print("=" * 100)
print("in-memory injections into load_risk_architecture_ra3(protocol=...)")


def attempt(name, mutate):
    doc = copy.deepcopy(PROTO)
    mutate(doc)
    try:
        arch = eng3.load_risk_architecture_ra3(doc)
        print("   %-52s -> LOADED bands=%d" % (name, len(arch.bands)))
    except Exception as exc:                                          # noqa: BLE001
        print("   %-52s -> %s: %s" % (name, type(exc).__name__, safe(str(exc))[:190]))


attempt("clean deep copy", lambda d: None)

def reinstate(doc):
    bands = doc["risk_architecture"]["components"][LADDER]["bands"]
    bands[0]["dd_to_exclusive"] = "0.05"
    bands.insert(1, {"band": 1, "dd_from": "0.05", "dd_to_exclusive": "0.08", "scalar": "0.75"})
    for index, band in enumerate(bands):
        band["band"] = index

attempt("RA2's deleted tier reinstated (four bands)", reinstate)

def shallow(doc):
    bands = doc["risk_architecture"]["components"][LADDER]["bands"]
    bands[0]["dd_to_exclusive"] = "0.06"
    bands[1]["dd_from"] = "0.06"

attempt("shallowest engagement moved to 0.06", shallow)

def two_band(doc):
    bands = doc["risk_architecture"]["components"][LADDER]["bands"]
    del bands[1]
    bands[0]["dd_to_exclusive"] = "0.10"
    bands[1]["band"] = 1

attempt("a rung Generation 1 sealed removed (two bands)", two_band)

def relabel(doc):
    doc["risk_architecture"]["id"] = "RA2"

attempt("architecture id relabelled RA2", relabel)

def unfreeze(doc):
    doc["risk_architecture"]["frozen_before_any_variant_is_run"] = False

attempt("frozen_before_any_variant_is_run flipped false", unfreeze)

def gridify(doc):
    doc["risk_architecture"]["not_part_of_the_grid"] = False

attempt("not_part_of_the_grid flipped false", gridify)

def ceiling(doc):
    for name, node in doc["risk_architecture"]["components"].items():
        if "ceiling_fraction_of_equity" in node:
            node["ceiling_fraction_of_equity"] = "0.60"

attempt("exposure ceiling widened to 0.60", ceiling)

print()
print("load_ra3_protocol injections (identity fields)")


def attempt_protocol(name, mutate):
    doc = copy.deepcopy(PROTO)
    mutate(doc)
    try:
        eng3.load_risk_architecture_ra3(doc)
        print("   %-52s -> LOADED" % name)
    except Exception as exc:                                          # noqa: BLE001
        print("   %-52s -> %s: %s" % (name, type(exc).__name__, safe(str(exc))[:160]))


attempt_protocol("attempt field set to 2", lambda d: d.__setitem__("attempt", 2))
