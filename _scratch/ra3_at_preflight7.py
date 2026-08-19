"""Seventh preflight: what the RA3 loader actually does with a widened exposure ceiling."""

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
RA3_1 = PROTO["risk_architecture"]["components"]["RA3-1"]

print("RA3-1 keys      = %s" % sorted(RA3_1))
print("RA3-1['value']  = %r" % RA3_1["value"])
print("sealed load     -> exposure_ceiling=%s" % eng3.load_risk_architecture_ra3().exposure_ceiling)
print()


def attempt(name, mutate):
    doc = copy.deepcopy(PROTO)
    mutate(doc)
    try:
        arch = eng3.load_risk_architecture_ra3(doc)
        print("   %-46s -> LOADED exposure_ceiling=%s" % (name, arch.exposure_ceiling))
    except Exception as exc:                                          # noqa: BLE001
        print("   %-46s -> %s: %s" % (name, type(exc).__name__, safe(str(exc))[:200]))


attempt("clean deep copy", lambda d: None)
attempt("RA3-1.value widened to 0.60",
        lambda d: d["risk_architecture"]["components"]["RA3-1"].__setitem__("value", "0.60"))
attempt("RA3-1.value widened to 1.00",
        lambda d: d["risk_architecture"]["components"]["RA3-1"].__setitem__("value", "1.00"))
attempt("RA3-1.value tightened to 0.25",
        lambda d: d["risk_architecture"]["components"]["RA3-1"].__setitem__("value", "0.25"))


def drop_clamp(d):
    node = d["risk_architecture"]["components"]["RA3-1"]["enforcement"]["part_a_entry_clamp"]
    node["clamp_names"] = list(node["clamp_names"])[:-1]


attempt("a clamp name removed", drop_clamp)
