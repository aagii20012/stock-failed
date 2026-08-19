"""Second pass: the nested structures the report tables index directly. ASCII output only."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
                .read_text(encoding="utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def dump(label, obj, width=200):
    print("=== %s" % label)
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                print("  %-46s %s(%d) %s" % (k, type(v).__name__, len(v), safe(v)[:width]))
            else:
                print("  %-46s %s" % (k, safe(v)[:width]))
    else:
        print("  %s" % safe(obj)[:width])
    print()


vt0 = EV["variant_table"][0]
cand = EV["candidate_results"][0]

dump("grid.axes", EV["grid"]["axes"])
dump("grid.runs_per_variant", EV["grid"]["runs_per_variant"])
dump("universe.excluded_symbols", EV["universe"]["excluded_symbols"])
dump("sealed_inputs.declared_before_any_strategy_code_measurement",
     EV["sealed_inputs"]["declared_before_any_strategy_code_measurement"], 400)
dump("risk_architecture.sealed", EV["risk_architecture"]["sealed"], 400)
dump("risk_architecture.as_loaded", EV["risk_architecture"]["as_loaded"], 400)
dump("risk_architecture.generation_1_provenance",
     EV["risk_architecture"]["generation_1_provenance"], 400)
dump("risk_architecture.single_difference_from_ra2",
     EV["risk_architecture"]["single_difference_from_ra2"], 400)
dump("risk_architecture.attempt_2_counterparts",
     EV["risk_architecture"]["attempt_2_counterparts"], 400)
dump("risk_architecture.attributes_derived_from_risk",
     EV["risk_architecture"]["attributes_derived_from_risk"], 400)
dump("ladder.per_statistic.ladder_descents",
     EV["ladder_engagement_comparison"]["per_statistic"]["ladder_descents"], 300)
dump("ladder.sessions_at_full_sizing",
     EV["ladder_engagement_comparison"]["sessions_at_full_sizing"], 400)
dump("ladder.statistics_compared", EV["ladder_engagement_comparison"]["statistics_compared"])
dump("vt0.base_ladder_sessions_in_band", vt0["base_ladder_sessions_in_band"])
dump("vt0.base_best_trade_removed_return", vt0["base_best_trade_removed_return"], 300)
dump("vt0.selection_score", vt0["selection_score"], 300)
dump("vt0.base_attempt_2", vt0["base_attempt_2"], 300)
dump("vt0.base_stop_exits[0]", vt0["base_stop_exits"][0], 300)
dump("cand.variant", cand["variant"], 300)
dump("cand.plan", cand["plan"], 300)
dump("cand.admission_basis", cand["admission_basis"], 400)
dump("cand.non_vacuity_check", cand["non_vacuity_check"], 300)
dump("cand.prose_alias_adapter", cand["prose_alias_adapter"], 300)
dump("cand.reconciliation", cand["reconciliation"], 300)
print("=== cand.conditions full")
for c in cand["conditions"]:
    print("  %s" % c["id"])
    for k in ("required_verbatim", "measured", "threshold", "verdict", "satisfied", "evidence",
              "note"):
        print("    %-20s %s" % (k, safe(c[k])[:400]))
    print()
print("=== cand.stress_evaluation.conditions measured/verdict")
for c in cand["stress_evaluation"]["conditions"]:
    print("  %-8s verdict=%-12s satisfied=%s" % (c["id"], c["verdict"], c["satisfied"]))
    print("    measured  %s" % safe(c["measured"])[:400])
    print("    threshold %s" % safe(c["threshold"])[:200])
print()
dump("cand.redefined_for_generation_2", {"v": cand["redefined_for_generation_2"]}, 400)
dump("cand.carried_over_unchanged", {"v": cand["carried_over_unchanged"]}, 400)
dump("gate_scope.neighbours", {"v": EV["gate_scope"]["neighbours"]}, 400)
dump("stage_verdict.prior_attempt_tokens_withheld",
     {"v": EV["stage_verdict"]["prior_attempt_tokens_withheld"]}, 400)
dump("determinism.fields_compared", {"v": EV["determinism"]["fields_compared"]}, 400)
dump("reported_for_every_variant_coverage.map",
     {"v": EV["reported_for_every_variant_coverage"]["map"][:2]}, 600)
dump("reported_for_every_variant_coverage.new_since_attempt_2",
     {"v": EV["reported_for_every_variant_coverage"]["new_since_attempt_2"]}, 400)
dump("reported_for_every_variant_coverage.not_supplied_by_grid_report",
     EV["reported_for_every_variant_coverage"]["not_supplied_by_grid_report"], 300)
