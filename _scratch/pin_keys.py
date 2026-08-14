"""Out-of-tree: dump the exact sealed key names the three test files will index. No evaluation."""

import json
import sys

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.strategies import attempt2_candidates as C
from stockedge100.strategies.attempt2_config import load_attempt2_config

config = load_attempt2_config()
p = config.protocol

print("== experiment keys ==")
for e in config.experiments:
    print(" ", e["experiment_id"], sorted(e.keys()))

print()
print("== permitted_parameter_grid_semantics ==")
print(json.dumps(p["permitted_parameter_grid_semantics"], indent=2)[:1500])

print()
print("== secondary_metrics keys ==", sorted(p["secondary_metrics"].keys()))

print()
print("== criteria keys of interest ==")
print("  reported_but_not_gating:", type(config.criteria["reported_but_not_gating"]).__name__)
print(json.dumps(config.criteria["reported_but_not_gating"], indent=2)[:900])

print()
print("== condition spec keys ==")
for cond in config.gate_conditions:
    print(" ", cond["id"], sorted(cond.keys()))

print()
print("== binding.neighbour_status ==")
print(json.dumps(config.binding["neighbour_status"], indent=2)[:1200])

print()
print("== binding.rerun_policy ==")
print(json.dumps(config.binding["rerun_policy"], indent=2)[:900])

print()
print("== protocol.partial_or_failed_run_rule ==")
print(json.dumps(p["partial_or_failed_run_rule"], indent=2)[:900])

print()
print("== protocol.missing_or_invalid_data_rule ==")
print(json.dumps(p["missing_or_invalid_data_rule"], indent=2)[:900])

print()
print("== risk_architecture keys ==", sorted(config.risk_architecture.keys()))
print("  RA1-5 keys:", sorted(config.risk_architecture["RA1-5"].keys()) if isinstance(config.risk_architecture["RA1-5"], dict) else "str")
print("  engine_shutdown_relationship:",
      json.dumps(config.risk_architecture["engine_shutdown_relationship"], indent=2)[:800])

print()
print("== attempt2_candidates namespace has sma/wilder_rsi ==",
      hasattr(C, "sma"), hasattr(C, "wilder_rsi"))

print()
print("== digests keys ==", sorted(config.digests.keys()))

print()
print("== shared_rules.adopted_unchanged ==", p["shared_rules"]["adopted_unchanged"])
print("== shared_rules.replaced keys ==", sorted(p["shared_rules"]["replaced"].keys()))
print("== adopted_text_restated_for_readability keys ==",
      sorted(p["shared_rules"]["adopted_text_restated_for_readability"].keys()))

print()
print("== benchmarks keys ==", sorted(p["benchmarks"].keys()))
print("== cost_stress_treatment keys ==", sorted(p["cost_stress_treatment"].keys()))
print(json.dumps(p["cost_stress_treatment"], indent=2)[:1200])

print()
print("== iteration_budget ==", json.dumps(p["iteration_budget"], indent=2))

print()
print("PINNED")
