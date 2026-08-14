"""Extract every value the strategy research report quotes, so none is typed from memory.

Nothing here is part of the repository state.
"""

import json
import sys
from pathlib import Path

ROOT = Path(r"d:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(ROOT / "src"))
from stockedge100.audit import sha256_file  # noqa: E402


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


ev = load("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json")
prereg = load("governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json")
protocol = load("config/stage3_attempt2_strategy_protocol.json")
binding = load("config/stage3_attempt2_gate_criteria_binding.json")
criteria = load("config/stage3_gate_criteria.json")

print("=== file digests to quote ===")
for rel in (
    "governance/STAGE_0_CONSTITUTION.md",
    "governance/STAGE_0_CONSTITUTION.json",
    "governance/STAGE_1_HOLDOUT_LOCK.json",
    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.md",
    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json",
    "config/stage3_attempt2_strategy_protocol.json",
    "config/stage3_attempt2_gate_criteria_binding.json",
    "config/stage3_gate_criteria.json",
    "config/stage3_strategy_protocol.json",
    "config/stage2_cost_model.json",
    "governance/STAGE_1_UNIVERSE.json",
):
    print(f"  {rel:58} {sha256_file(ROOT / rel)}")

print("\n=== prereg identity ===")
for key in (
    "document_id",
    "attempt_id",
    "status",
    "declared_utc",
    "run_id",
    "is_adaptive_second_attempt",
    "sealed_before_any_attempt_2_strategy_code",
    "candidates_declared",
    "candidate_ids",
    "shared_risk_architecture",
    "robustness_neighbours_per_candidate",
    "max_variants_per_candidate",
    "declared_gating_variants",
    "declared_runs",
    "revisions_permitted",
    "families_retained",
    "families_excluded",
):
    print(f"  {key:46} {prereg[key]}")
print("  gate:")
print(json.dumps(prereg["gate"], indent=4))

print("\n=== evidence identity ===")
for key in ("artifact_id", "generated_utc", "command", "evidence_digest", "evidence_digest_covers"):
    print(f"  {key:24} {ev[key]}")
print("  window:")
print(json.dumps(ev["window"], indent=4))
print("  cost_models:")
print(json.dumps(ev["cost_models"], indent=4))
print("  iteration_budget:")
print(json.dumps(ev["iteration_budget"], indent=4))
print("  determinism (minus runs):")
print(json.dumps({k: v for k, v in ev["determinism"].items() if k != "runs"}, indent=4))
print("  determinism runs:")
print(json.dumps(ev["determinism"]["runs"], indent=4))
print("  stage_verdict:")
print(json.dumps(ev["stage_verdict"], indent=4))
print("  per_condition_rollup.warning:")
print(json.dumps(ev["per_condition_rollup"]["warning"], indent=4))
print("  no_selection_in_this_stage:")
print(json.dumps(ev["no_selection_in_this_stage"], indent=4))
print("  explicit_non_authorizations:")
print(json.dumps(ev["explicit_non_authorizations"], indent=4))
print("  adaptive_research:")
print(json.dumps(ev["adaptive_research"], indent=4))
print("  sealed_inputs:")
print(json.dumps(ev["sealed_inputs"], indent=4))

print("\n=== per candidate: plan, conditions, summary ===")
for cand in ev["candidates"]:
    plan = cand["plan"]
    print(f"\n--- {plan['experiment_id']} ---")
    print(json.dumps(plan, indent=4)[:2400])
    print("  conditions:")
    for cond in cand["gate"]["conditions"]:
        print(
            f"    {cond['id']:8} {cond['verdict']:34} satisfied={cond['satisfied']!s:5} "
            f"measured={str(cond['measured'])[:40]:42} threshold={cond['threshold']}"
        )
    print(f"  candidate verdict: admitted={cand['gate']['admitted']}")
    print("  benchmark_comparison:")
    print(json.dumps(cand["benchmark_comparison"], indent=4))
    print("  stressed_cost_run:")
    print(json.dumps(cand["stressed_cost_run"], indent=4))

print("\n=== gate_summary ===")
print(json.dumps(ev["gate_summary"], indent=2))

print("\n=== sealed RA1 parameters (as sealed) ===")
print(json.dumps(protocol["shared_risk_architecture"], indent=2)[:6000])

print("\n=== declared runs vs gating variants, as sealed ===")
for key in protocol:
    if "run" in key or "variant" in key or "budget" in key:
        print(f"  {key}: {json.dumps(protocol[key])[:700]}")

print("\n=== criteria verdict_token_derivation ===")
print(json.dumps(criteria["verdict_token_derivation"], indent=2))

print("\n=== binding: conditions_adopted / drawdown ceiling / rederivations ===")
for key in (
    "bound_artifact",
    "conditions_adopted",
    "drawdown_ceiling_is_unchanged",
    "nothing_else_changed",
):
    print(f"  {key}: {json.dumps(binding[key])[:900]}")
print("  admissible_candidate_exists:")
print(json.dumps(binding["admissible_candidate_exists"], indent=4))
