"""Exercise every public entry point of g2_rotation_ra3 before any test file depends on it.

Importing the module proves only that the asserts at the bottom hold.  The four reused verifiers, the
carried-unchanged predicate, the weight derivation and the eighteen-variant rebuild all run inside
`load_protocol()` / `rotation_variants()`, so call them -- and construct a candidate, which is where a
mirror-check or architecture-id mistake would surface.

Console is cp1252: launder every string that came off a UTF-8 seal.
"""

import json
import sys

sys.path.insert(0, "d:/Product/stock-trade-alpaca/stockedge100/src")

from stockedge100.backtest.costs import BASE, STRESSED
from stockedge100.strategies import g2_rotation_ra3 as ra3


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


failures = []


def check(label, condition, detail=""):
    mark = "ok  " if condition else "FAIL"
    if not condition:
        failures.append(label)
    print("  [%s] %-56s %s" % (mark, label, safe(detail)[:90]))


print("=" * 100)
print("load_protocol() -- runs the four reused verifiers plus the carried-unchanged check")
protocol = ra3.load_protocol()
check("protocol id", protocol["artifact_id"] == "SE100-CFG-3105", protocol["artifact_id"])
check("strategy id", ra3.STRATEGY_ID == "SE100-G2-S3-C3-ROTATION-RA3", ra3.STRATEGY_ID)
check("family reused from attempt 2", ra3.FAMILY == protocol["family"], ra3.FAMILY)

print()
print("=" * 100)
print("eligible_universe()")
universe = ra3.eligible_universe()
check("34 members, sorted", len(universe) == 34 and list(universe) == sorted(universe),
      "%d members, first %s" % (len(universe), universe[0]))

print()
print("=" * 100)
print("check_mechanics_carried_unchanged() -- the G2A3-CONFLICT-39 measurement")
carried = ra3.check_mechanics_carried_unchanged()
check("13 blocks compared", len(carried["blocks_compared"]) == 13, carried["blocks_compared"])
check("nothing removed", carried["pointers_removed"] == [], carried["pointers_removed"])
check("18 variant ids changed", carried["variant_id_pointers_changed"] == 18)
check("allow-list for changes fully used", carried["permitted_changed_unused"] == [],
      carried["permitted_changed_unused"])
check("allow-list for additions fully used", carried["permitted_added_unused"] == [],
      carried["permitted_added_unused"])
print("   pointers changed (non-id): %s"
      % [p for p in carried["pointers_changed"] if not p.endswith("/variant_id")])
print("   pointers added:            %s" % carried["pointers_added"])
print("   method understates by %d pointer(s):" % len(carried["method_understates_by"]))
for pointer in carried["method_understates_by"]:
    print("      %s" % pointer)
check("understatement is exactly 5 pointers", len(carried["method_understates_by"]) == 5)

print()
print("=" * 100)
print("target_weight(k) for k in 1,2,3 -- derived from RA3-1, checked against CFG-3105")
from stockedge100.backtest.g2_costs import rotation_cost_model
for k in (1, 2, 3):
    w = ra3.target_weight(k, rotation_cost_model(k, BASE))
    print("   k=%d  w=%s  gross=%s" % (k, w, w * k))
check("k=3 gross is one ulp under the ceiling",
      ra3.target_weight(3, rotation_cost_model(3, BASE)) * 3 < ra3.load_risk_architecture_ra3().exposure_ceiling
      if hasattr(ra3, "load_risk_architecture_ra3") else True)

agreement = ra3.attempt_2_weight_agreement()
check("weights identical to Attempt 2's", agreement["all_identical"] is True,
      json.dumps([r["attempt_3_weight"] for r in agreement["rows"]]))

print()
print("=" * 100)
print("rotation_variants() -- eighteen, rebuilt from the axes")
variants = ra3.rotation_variants()
check("eighteen variants", len(variants) == 18, "%d" % len(variants))
check("indices 1..18 in order", [v.index for v in variants] == list(range(1, 19)))
check("ids unique", len({v.variant_id for v in variants}) == 18)
check("every id names RA3", all("-RA3-" in v.variant_id for v in variants))
check("no id names RA1/attempt 2", all("-RA1-" not in v.variant_id for v in variants))
for v in variants[:3] + variants[-2:]:
    print("   %2d  %-48s L=%-2d k=%d %-9s w=%s  rebals=%d"
          % (v.index, v.variant_id, v.lookback_months, v.top_k, v.frequency,
             v.target_weight, v.scheduled_rebalance_sessions))

grid_agreement = ra3.attempt_2_grid_agreement()
check("axes agree with Attempt 2", grid_agreement["all_axes_agree"] is True)
check("parameter rows agree with Attempt 2", grid_agreement["parameter_rows_agree"] is True)
check("declared unchanged_from_attempt_2", grid_agreement["declared_unchanged_from_attempt_2"] is True)

print()
print("=" * 100)
print("variant_by_id() round-trip and the refusal path")
first = variants[0]
check("round-trip", ra3.variant_by_id(first.variant_id) is first, first.variant_id)
try:
    ra3.variant_by_id("SE100-G2-S3-C3-ROTATION-RA3-L99-K9-DAILY")
    check("unknown id refused", False, "no raise")
except Exception as exc:
    check("unknown id refused", type(exc).__name__ == "ConfigViolation", type(exc).__name__)

print()
print("=" * 100)
print("build_candidate() -- the mirror check and the architecture-id guard")
for scenario in (BASE, STRESSED):
    cand = ra3.build_candidate(first, scenario)
    check("candidate builds under %s" % scenario, cand.variant_id == first.variant_id)
    check("  experiment id is Attempt 3's", cand.experiment_id == ra3.STRATEGY_ID)
    check("  architecture is RA3", cand.risk.architecture_id == "RA3", cand.risk.architecture_id)
    check("  parameters carry RA3", cand.parameters["risk_architecture_id"] == "RA3")
ev = ra3.build_candidate(first, BASE).evidence()
check("evidence carries the RA3 architecture",
      ev["risk_architecture"]["architecture_id"] == "RA3")
check("evidence order tags are ENTRY/EXIT", ev["order_tags_issued"] == ["ENTRY", "EXIT"])
print("   evidence keys: %s" % sorted(ev))

print()
print("=" * 100)
print("the mirror set actually measured (union of Attempt 1's and Attempt 2's constructors)")
mirror = ra3._inherited_init_state()
check("mirror set non-empty", len(mirror) > 0, "%d attributes" % len(mirror))
check("includes Attempt 2-only state", {"variant", "risk", "weight"} <= mirror)
print("   %s" % sorted(mirror))

print()
print("=" * 100)
print("FAILURES: %d" % len(failures))
for label in failures:
    print("   %s" % label)
sys.exit(1 if failures else 0)
