"""Print the exact key shape of the Attempt 2 evidence file so the package builder reads real
field names rather than guessed ones.

Nothing here is part of the repository state.
"""

import json
from pathlib import Path

ROOT = Path(r"d:\Product\stock-trade-alpaca\stockedge100")
EVIDENCE = ROOT / "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json"
body = json.loads(EVIDENCE.read_text(encoding="utf-8"))


def shape(value, depth=0, prefix=""):
    pad = "  " * depth
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}: {type(v).__name__}[{len(v)}]")
                if depth < 1:
                    shape(v, depth + 1)
            else:
                s = str(v)
                print(f"{pad}{k} = {s[:110]}")
    elif isinstance(value, list):
        if value and isinstance(value[0], dict):
            print(f"{pad}[0] keys: {list(value[0])}")
        elif value:
            print(f"{pad}[0] = {str(value[0])[:110]}")


print("=== TOP LEVEL ===")
for k, v in body.items():
    if isinstance(v, (dict, list)):
        print(f"  {k}: {type(v).__name__}[{len(v)}]")
    else:
        print(f"  {k} = {str(v)[:110]}")

for key in (
    "window", "windows", "cost_model", "iteration_budget", "stage_verdict",
    "multiple_comparisons_disclosure", "no_selection_in_this_stage",
    "explicit_non_authorizations", "adaptive_research_disclosure", "determinism",
    "protocol_identity", "seal", "contamination", "attempt", "ra1",
):
    if key in body:
        print(f"\n=== {key} ===")
        shape(body[key], 1)

print("\n=== candidates[0] top keys ===")
c0 = body["candidates"][0]
for k, v in c0.items():
    if isinstance(v, (dict, list)):
        print(f"  {k}: {type(v).__name__}[{len(v)}]")
    else:
        print(f"  {k} = {str(v)[:110]}")

print("\n=== candidates[0]['gate'] ===")
shape(c0["gate"], 1)

print("\n=== candidates[0]['gate']['conditions'][0] full ===")
print(json.dumps(c0["gate"]["conditions"][0], indent=2)[:2500])

print("\n=== candidates[0]['plan'] keys ===")
print(list(c0["plan"]))

print("\n=== a run's keys ===")
first_run = next(iter(c0["runs"].values()))
print(list(first_run))
