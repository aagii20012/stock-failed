"""Print every remaining field name the evaluation package builder needs, from the real files.

Nothing here is part of the repository state.
"""

import json
from pathlib import Path

ROOT = Path(r"d:\Product\stock-trade-alpaca\stockedge100")


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


ev = load("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json")
prereg = load("governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json")
run = load("runs/SE100-R-20260810T131107Z.json")

print("=== prereg scalars ===")
for k, v in prereg.items():
    if not isinstance(v, (dict, list)):
        print(f"  {k} = {v}")
print("\n=== prereg containers ===")
for k, v in prereg.items():
    if isinstance(v, (dict, list)):
        print(f"  {k}: {type(v).__name__}[{len(v)}]  {list(v)[:14] if isinstance(v, dict) else ''}")

print("\n=== prereg.gate ===")
print(json.dumps(prereg["gate"], indent=2)[:2200])

print("\n=== prereg.cumulative_experiment_count ===")
print(json.dumps(prereg["cumulative_experiment_count"], indent=2))

print("\n=== prereg.preregistered_files / checksum_record ===")
print(json.dumps(prereg["preregistered_files"], indent=2))
print(json.dumps(prereg["checksum_record"], indent=2))

print("\n=== prereg.contamination_predicates ===")
print(json.dumps(prereg["contamination_predicates"], indent=2)[:1800])

print("\n=== design run record top keys ===")
for k, v in run.items():
    if isinstance(v, (dict, list)):
        print(f"  {k}: {type(v).__name__}[{len(v)}]")
    else:
        print(f"  {k} = {str(v)[:110]}")

print("\n=== evidence: gate_summary[0] keys ===")
print(json.dumps(ev["gate_summary"][0], indent=2))

print("\n=== evidence: candidates[0].gate scalar keys ===")
g = ev["candidates"][0]["gate"]
for k, v in g.items():
    if not isinstance(v, (dict, list)):
        print(f"  {k} = {v}")
    else:
        print(f"  {k}: {type(v).__name__}[{len(v)}]")

print("\n=== evidence: S3-C5 condition, all three candidates ===")
for cand in ev["candidates"]:
    for cond in cand["gate"]["conditions"]:
        if cond["id"] == "S3-C5":
            print(" ", cand["gate"]["experiment_id"])
            print(json.dumps(cond, indent=2)[:1400])

print("\n=== evidence: S3-C6 + S3-C7 condition for C3 / C1 ===")
for cand in ev["candidates"]:
    for cond in cand["gate"]["conditions"]:
        if cond["id"] in ("S3-C6", "S3-C7"):
            print(" ", cand["gate"]["experiment_id"], cond["id"])
            print(json.dumps(cond, indent=2)[:1200])

print("\n=== evidence: per_condition_rollup.rows[0] ===")
print(json.dumps(ev["per_condition_rollup"]["rows"][0], indent=2))

print("\n=== evidence: per_condition_rollup keys ===")
print(list(ev["per_condition_rollup"]))

print("\n=== evidence: window ===")
print(json.dumps(ev["window"], indent=2)[:2200])

print("\n=== evidence: adaptive_research keys ===")
for k, v in ev["adaptive_research"].items():
    print(f"  {k}: {type(v).__name__}", (list(v) if isinstance(v, dict) else len(v) if isinstance(v, list) else str(v)[:80]))

print("\n=== evidence: determinism ===")
print(json.dumps(ev["determinism"], indent=2)[:1600])

print("\n=== evidence: candidates[0].benchmark_comparison ===")
print(json.dumps(ev["candidates"][0]["benchmark_comparison"], indent=2))

print("\n=== evidence: candidates[0].stressed_cost_run keys ===")
print(list(ev["candidates"][0]["stressed_cost_run"]))

print("\n=== evidence: sealed_inputs ===")
print(json.dumps(ev["sealed_inputs"], indent=2))

print("\n=== evidence: explicit_non_authorizations ===")
print(json.dumps(ev["explicit_non_authorizations"], indent=2)[:2400])
