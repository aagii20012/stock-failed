"""Fifth and final surface pass: the last four unknowns before the AT module is written.

  1. g2_gate_ra3's public loader (the two extra tests need a `criteria` object to feed
     _check_prose_renames_are_as_declared, and I do not have its name)
  2. does SelectionInputV2 carry to_json / any serialiser AT-K's round-trip needs
  3. RotationCandidateRA3's constructor signature and `.costs` / `.weight` attributes
     (make_engine mirrors run_one and reads both)
  4. attempt2_indicators constants, and whether ORDER_KIND_PRECEDENCE is reachable
"""

import dataclasses
import inspect
import json
import pathlib
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


print("=" * 100)
print("1. g2_gate_ra3 public surface")
from stockedge100.strategies import g2_gate_ra3 as G

print("   __all__ %s" % getattr(G, "__all__", None))
for name in sorted(n for n in dir(G) if not n.startswith("__")):
    obj = getattr(G, name)
    if inspect.isfunction(obj):
        print("   def   %-40s %s" % (name, inspect.signature(obj)))
    elif isinstance(obj, (str, int, tuple)) and not name.islower():
        print("   const %-40s %s" % (name, safe(repr(obj))[:110]))

print()
print("   PROSE_ALIASES = %s" % safe(repr(G.PROSE_ALIASES)))
print("   _pointers_dropped_since_attempt_2() -> %d" % len(G._pointers_dropped_since_attempt_2()))
print("   _keys_the_frozen_evaluators_read()  -> %d" % len(G._keys_the_frozen_evaluators_read()))

print()
print("=" * 100)
print("2. SelectionInputV2 serialisation")
from stockedge100.strategies import g2_selection_v2 as S

print("   members: %s" % [n for n in dir(S.SelectionInputV2) if not n.startswith("_")])
print("   dataclasses.asdict works: %s"
      % safe(dataclasses.asdict(S.SelectionInputV2("X", 0, 1, 2, 3, 4))))
print("   NeighbourhoodScore members: %s"
      % [n for n in dir(S.NeighbourhoodScore) if not n.startswith("_")])
print("   SelectionResultV2 members: %s"
      % [n for n in dir(S.SelectionResultV2) if not n.startswith("_")])
print("   SCORE_DECIMALS=%s SELECTION_RULE_ID=%s" % (S.SCORE_DECIMALS, S.SELECTION_RULE_ID))

print()
print("=" * 100)
print("3. RotationCandidateRA3 construction surface")
from stockedge100.strategies import g2_rotation_ra3 as R

v = R.rotation_variants()[0]
print("   variant[0] = %s  top_k=%s  target_weight=%s" % (v.variant_id, v.top_k, v.target_weight))
cand = R.build_candidate(v.variant_id, "BASE", universe=("AAA", "BBB", "CCC", "DDD", "EEE"))
print("   candidate type %s" % type(cand).__name__)
print("   has .costs=%s  has .weight=%s" % (hasattr(cand, "costs"), hasattr(cand, "weight")))
print("   weight=%s min_order_notional=%s"
      % (getattr(cand, "weight", "<none>"), getattr(cand.costs, "min_order_notional", "<none>")))
print("   rotation_cost_model sig: %s" % inspect.signature(R.rotation_cost_model))
print("   eligible_universe() size = %d" % len(R.eligible_universe()))
print("   ids: %s ... %s" % (R.rotation_variants()[0].variant_id,
                             R.rotation_variants()[-1].variant_id))
for want in ("SE100-G2-S3-C3-ROTATION-RA3-L03-K1-MONTHLY",
             "SE100-G2-S3-C3-ROTATION-RA3-L03-K2-MONTHLY",
             "SE100-G2-S3-C3-ROTATION-RA3-L03-K3-MONTHLY"):
    try:
        R.variant_by_id(want)
        print("   variant_by_id(%s) OK" % want)
    except Exception as exc:                                   # noqa: BLE001
        print("   variant_by_id(%s) FAILED %s" % (want, safe(exc)))

print()
print("=" * 100)
print("4. indicators + precedence + RA2 architecture for the 6%% contrast")
from stockedge100.strategies.attempt2_indicators import (
    TRADING_DAYS_PER_YEAR, VOL20_BARS, VOL20_RETURNS, VOL20_VARIANCE_DENOMINATOR)
from stockedge100.backtest.g2_engine_ra1 import ORDER_KIND_PRECEDENCE, load_risk_architecture
from decimal import Decimal

print("   TRADING_DAYS_PER_YEAR=%s VOL20_BARS=%s VOL20_RETURNS=%s VOL20_VARIANCE_DENOMINATOR=%s"
      % (TRADING_DAYS_PER_YEAR, VOL20_BARS, VOL20_RETURNS, VOL20_VARIANCE_DENOMINATOR))
print("   ORDER_KIND_PRECEDENCE=%s" % (ORDER_KIND_PRECEDENCE,))
ra2 = load_risk_architecture()
print("   RA2 bands: %s" % [(str(b.dd_from), str(b.dd_to_exclusive), str(b.scalar))
                            for b in ra2.bands])
print("   RA2 band_for(0.06)=%s scalar=%s"
      % (ra2.band_for(Decimal("0.06")), ra2.scalar_of(ra2.band_for(Decimal("0.06")))))

print()
print("=" * 100)
print("5. AT-H: the two config lists and the seal's digest map")
cfg = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
node = cfg["prior_attempt_modules_immutable"]
print("   count=%s a1=%d a2=%d" % (node["count"], len(node["attempt_1_modules"]),
                                   len(node["attempt_2_modules"])))
seal = json.loads((ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json")
                  .read_text("utf-8"))
digests = seal["contamination_measurement"]["prior_attempt_module_digests"]
print("   seal digest entries=%d" % len(digests))
print("   sets agree: %s"
      % (sorted(digests) == sorted(node["attempt_1_modules"] + node["attempt_2_modules"])))
print("   digests_recorded_by = %s" % safe(node["digests_recorded_by"])[:160])
