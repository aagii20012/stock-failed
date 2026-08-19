"""Exact shapes the Attempt 3 sealer must consume, read rather than guessed.

The Attempt 2 sealer is the template and most of its edits are mechanical, but
four of them depend on structure that changed between the two configs:

  * `attempt_1_modules_immutable` became `prior_attempt_modules_immutable`
  * there are now two pinned prior attempts (`attempt_1_ref`, `attempt_2_ref`),
    not one, and the pinning loop keys on a `<name>`/`<name>_sha256` pairing
  * RA2-4's four ladder bands became RA3-4's three
  * two prior run records must be located, not one

Guessing any of those is how a sealer silently checks nothing.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
P = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json")
               .read_text(encoding="utf-8"))
C = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json")
               .read_text(encoding="utf-8"))


def dump(name, node):
    print("=" * 90)
    print(name)
    print(json.dumps(node, indent=2, ensure_ascii=False)[:2600])


dump("prior_attempt_modules_immutable", P["prior_attempt_modules_immutable"])
dump("attempt_1_ref", P["attempt_1_ref"])
dump("attempt_2_ref", P["attempt_2_ref"])
dump("declared_before_any_strategy_code_measurement",
     P["declared_before_any_strategy_code_measurement"])
dump("risk_architecture.components.RA3-4", P["risk_architecture"]["components"]["RA3-4"])
dump("representative_selection_rule (top-level keys)",
     {k: (v if not isinstance(v, (dict, list)) else "<%s>" % type(v).__name__)
      for k, v in P["representative_selection_rule"].items()})
dump("gate_evaluation_scope", P["gate_evaluation_scope"])
dump("runs_per_variant", P["runs_per_variant"])
dump("grid (minus variants)", {k: v for k, v in P["grid"].items() if k != "variants"})
dump("multiple_comparisons_disclosure", P["multiple_comparisons_disclosure"])
dump("verdict_token_derivation", C["verdict_token_derivation"])

print("=" * 90)
print("scalar / ref fields the sealer pins or restates")
for k in ("artifact_id", "strategy_id", "candidate_index", "family", "attempt",
          "gate_criteria_ref", "constitution_ref", "charter_ref", "partition_lock_ref",
          "cost_model_derivation_ref", "declared_before_any_strategy_code",
          "live_trading_authorized", "gate_criteria_sha256_not_recorded_here"):
    v = P.get(k, "<<ABSENT>>")
    print("  %-42s %s" % (k, (v[:110] + "...") if isinstance(v, str) and len(v) > 110 else v))

print()
print("criteria scalars")
for k in ("artifact_id", "attempt", "gate_id", "protocol_ref", "live_trading_authorized",
          "attempt_2_counterpart", "attempt_2_counterpart_sha256",
          "attempt_1_counterpart", "attempt_1_counterpart_sha256",
          "generation_1_counterpart", "generation_1_counterpart_sha256"):
    v = C.get(k, "<<ABSENT>>")
    print("  %-42s %s" % (k, v))
