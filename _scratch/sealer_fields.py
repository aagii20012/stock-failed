"""Every config field the Attempt 3 sealer will read, checked to exist before it is written.

The Attempt 2 sealer indexes its protocol config with bare `[...]` in about thirty places.  Each
of those is a KeyError waiting to happen if a key was renamed between CFG-3103 and CFG-3105, and a
KeyError raised halfway through `build()` after the JSON has been written would leave a
half-sealed artifact.  Read them all first; a missing key here costs nothing.

Prints a type and a short rendering, never the whole value, so the cp1252 console survives.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
P = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json")
               .read_text(encoding="utf-8"))
C = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json")
               .read_text(encoding="utf-8"))

# (path, required) - dotted paths into the protocol config, in the order the sealer reads them.
PATHS = [
    "strategy_id",
    "candidate_index",
    "family",
    "hypothesis",
    "attempt",
    "constitution_ref",
    "gate_criteria_ref",
    "live_trading_authorized",
    "declared_before_any_strategy_code",
    "declared_before_any_strategy_code_measurement.predicate",
    "concentration_ceiling.value",
    "risk_architecture.id",
    "risk_architecture.frozen_before_any_variant_is_run",
    "risk_architecture.not_part_of_the_grid",
    "risk_architecture.components.RA3-1.value",
    "risk_architecture.combined_scalar.formula",
    "position_sizing.target_weight_formula",
    "position_sizing.target_weights",
    "position_sizing.target_gross_exposure",
    "grid.size",
    "grid.axes.lookback_months",
    "grid.axes.top_k",
    "grid.axes.rebalance_frequency",
    "grid.variant_id_format",
    "grid.variants",
    "runs_per_variant.count",
    "runs_per_variant.labels",
    "runs_per_variant.total_runs",
    "run_span.run_start",
    "rebalance.measured_counts.monthly",
    "window.development.from",
    "window.development.last_session",
    "window.prohibited",
    "window.enforcement",
    "eligible_universe.members",
    "eligible_universe.member_count",
    "eligible_universe.universe_version",
    "multiple_comparisons_disclosure.variants_this_attempt",
    "multiple_comparisons_disclosure.cumulative_variants_this_hypothesis_family",
    "representative_selection_rule.id",
    "gate_evaluation_scope.evaluated_on",
    "gate_evaluation_scope.thresholds_changed_from_attempt_1",
    "gate_evaluation_scope.thresholds_changed_from_attempt_2",
    "adaptation_disclosure_verbatim",
    "adaptation_disclosure_carriage_requirement",
    "structural_consequences_declared_before_running",
    "adversarial_test_requirements",
    "reproducibility_requirements",
    "conflicts_found",
    "post_seal_defect_rule",
    "explicit_non_authorizations",
    "prior_attempt_modules_immutable.attempt_1_modules",
    "prior_attempt_modules_immutable.attempt_2_modules",
    "attempt_1_ref.strategy_id",
    "attempt_1_ref.verdict",
    "attempt_1_ref.disposition",
    "attempt_2_ref.strategy_id",
    "attempt_2_ref.verdict",
    "attempt_2_ref.disposition",
]


def get(node, dotted):
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return "<<MISSING>>"
        node = node[part]
    return node


def render(v):
    if isinstance(v, str):
        return "str(%d) %s" % (len(v), (v[:64] + "...") if len(v) > 64 else v)
    if isinstance(v, list):
        return "list(%d) first=%s" % (len(v), json.dumps(v[0], ensure_ascii=False)[:52]
                                      if v else "<empty>")
    if isinstance(v, dict):
        return "dict(%d) keys=%s" % (len(v), list(v)[:6])
    return "%s %r" % (type(v).__name__, v)


missing = []
for dotted in PATHS:
    value = get(P, dotted)
    if value == "<<MISSING>>":
        missing.append(dotted)
    print("  %-62s %s" % (dotted, render(value)))

print()
print("MISSING FROM CFG-3105: %s" % (missing or "none"))

print()
print("multiple_comparisons_disclosure arithmetic")
m = P["multiple_comparisons_disclosure"]
for k, v in sorted(m.items()):
    if isinstance(v, (int, float, bool)):
        print("  %-52s %s" % (k, v))

print()
print("gate_evaluation_scope")
for k, v in P["gate_evaluation_scope"].items():
    print("  %-52s %s" % (k, render(v)))

print()
print("criteria fields the sealer reads")
for dotted in ("verdict_token_derivation.pass_token",
               "verdict_token_derivation.fail_token",
               "verdict_token_derivation.prior_attempt_tokens_are_not_available_here",
               "live_trading_authorized", "attempt"):
    print("  %-62s %s" % (dotted, render(get(C, dotted))))
