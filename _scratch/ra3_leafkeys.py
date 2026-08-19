"""Exact leaf key lists for the nodes the generator indexes directly.  The
keymap dump stopped at depth 3 and these sit below it; guessing a leaf name is
how a field gets silently dropped from a sealed document."""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
P = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json")
               .read_text(encoding="utf-8"))
C = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json")
               .read_text(encoding="utf-8"))


def show(path, node):
    if isinstance(node, dict):
        print("%-62s {%d} %s" % (path, len(node), list(node)))
    elif isinstance(node, list):
        kinds = sorted({type(x).__name__ for x in node})
        print("%-62s [%d] of %s" % (path, len(node), ",".join(kinds)))
        if node and isinstance(node[0], dict):
            print("%-62s      row keys: %s" % ("", list(node[0].keys())))
    else:
        print("%-62s <%s> %r" % (path, type(node).__name__,
                                 (node[:90] + "...") if isinstance(node, str)
                                 and len(node) > 90 else node))


comp = P["risk_architecture"]["components"]
for cid in ("RA3-1", "RA3-2", "RA3-3", "RA3-4", "RA3-5"):
    show("risk_architecture.components.%s" % cid, comp[cid])

show("risk_architecture.combined_scalar", P["risk_architecture"]["combined_scalar"])
show("risk_architecture.state_ownership", P["risk_architecture"]["state_ownership"])
show("refs_reverified", P["refs_reverified"])
show("eligible_universe", P["eligible_universe"])
show("ranking_signal", P["ranking_signal"])
show("position_sizing", P["position_sizing"])
show("position_sizing.target_weights", P["position_sizing"]["target_weights"])
show("concentration_ceiling", P["concentration_ceiling"])
show("rebalance", P["rebalance"])
show("rebalance.measured_counts", P["rebalance"]["measured_counts"])
show("window", P["window"])
show("window.development", P["window"]["development"])
show("window.prohibited[0]", P["window"]["prohibited"][0])
show("run_span", P["run_span"])
show("execution", P["execution"])
show("execution.order_kinds_this_attempt_may_issue",
     P["execution"]["order_kinds_this_attempt_may_issue"])
show("grid", P["grid"])
show("grid.variants[0]", P["grid"]["variants"][0])
show("multiple_comparisons_disclosure", P["multiple_comparisons_disclosure"])
show("representative_selection_rule", P["representative_selection_rule"])
show("representative_selection_rule.structural_enforcement",
     P["representative_selection_rule"]["structural_enforcement"])
show("representative_selection_rule.no_candidate_path",
     P["representative_selection_rule"]["no_candidate_path"])
show("representative_selection_rule.second_fail_path",
     P["representative_selection_rule"]["second_fail_path"])
show("representative_selection_rule.retrospective_check_disclosure",
     P["representative_selection_rule"]["retrospective_check_disclosure"])
for i, st in enumerate(P["representative_selection_rule"]["steps"]):
    show("representative_selection_rule.steps[%d]" % i, st)
show("gate_evaluation_scope", P["gate_evaluation_scope"])
scs = P["structural_consequences_declared_before_running"]
for k in scs:
    show("structural_consequences.%s" % k, scs[k])
show("declared_before_any_strategy_code_measurement",
     P["declared_before_any_strategy_code_measurement"])
show("prior_attempt_modules_immutable", P["prior_attempt_modules_immutable"])
show("adaptation_disclosure_carriage_requirement",
     P["adaptation_disclosure_carriage_requirement"])
show("reproducibility_requirements", P["reproducibility_requirements"])
show("adversarial_test_requirements", P["adversarial_test_requirements"])
show("conflicts_found", P["conflicts_found"])
for cf in P["conflicts_found"]:
    print("    %-22s keys=%s" % (cf["id"], list(cf)))
show("conflicts_declared_in_the_gate_criteria", P["conflicts_declared_in_the_gate_criteria"])
show("post_seal_defect_rule", P["post_seal_defect_rule"])
show("serialisation", P["serialisation"])
show("mechanics_carried_unchanged", P["mechanics_carried_unchanged"])
show("constitution_ref", P["constitution_ref"])
show("gate_criteria_ref", P["gate_criteria_ref"])
show("charter_ref", P["charter_ref"])
show("partition_lock_ref", P["partition_lock_ref"])
show("cost_model_derivation_ref", P["cost_model_derivation_ref"])
show("gate_criteria_sha256_not_recorded_here", P["gate_criteria_sha256_not_recorded_here"])
show("attempt_1_ref", P["attempt_1_ref"])
show("attempt_2_ref", P["attempt_2_ref"])

print()
print("=" * 78)
show("criteria.verdict_token_derivation", C["verdict_token_derivation"])
show("criteria.conditions", C["conditions"])
show("criteria.evaluation_integrity_rules", C["evaluation_integrity_rules"])
show("criteria.windows", C["windows"])
show("criteria.conflicts_found", C["conflicts_found"])
show("criteria.reported_but_not_gating", C["reported_but_not_gating"])
