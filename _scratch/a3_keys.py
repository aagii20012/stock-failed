"""Dump the exact key shape of episode_ledger.json so the report generator reads real keys."""

import json
from pathlib import Path

OUT = Path(r"D:\Product\stock-trade-alpaca\stockedge100\reports\diagnostics\attempt3_iwm_trace")
D = json.loads((OUT / "episode_ledger.json").read_text(encoding="utf-8"))

print("== top level ==")
for k, v in D.items():
    kind = type(v).__name__
    extra = f" len={len(v)}" if isinstance(v, (list, dict)) else f" = {v}"
    print(f"  {k:<52s} {kind}{extra}")

for block in ("sealed_source", "observation_method", "run_shape", "reconciliation"):
    print(f"\n== {block} ==")
    for k, v in D[block].items():
        if isinstance(v, dict):
            print(f"  {k}: dict keys={list(v)}")
        elif isinstance(v, list):
            print(f"  {k}: list len={len(v)} first={v[0] if v else None}")
        else:
            print(f"  {k} = {v}")

print("\n== iwm ==")
for k, v in D["iwm"].items():
    if isinstance(v, list):
        print(f"  {k}: list len={len(v)} first={v[0] if v else None}")
    elif isinstance(v, dict):
        print(f"  {k}: dict keys={list(v)}")
    else:
        print(f"  {k} = {v}")

print("\n== iwm.episodes[0] ==")
for k, v in D["iwm"]["episodes"][0].items():
    print(f"  {k} = {v}")

print("\n== risk_context ==")
for k, v in D["risk_context"].items():
    if isinstance(v, (list, dict)):
        print(f"  {k}: {type(v).__name__} -> {json.dumps(v)[:200]}")
    else:
        print(f"  {k} = {v}")

print("\n== per_symbol_context['IWM'] ==")
for k, v in D["per_symbol_context"]["IWM"].items():
    print(f"  {k} = {v}")

print("\n== full_episode_ledger[0] ==")
for k, v in D["full_episode_ledger"][0].items():
    print(f"  {k} = {v}")

print("\n== open episodes ==")
for e in D["full_episode_ledger"]:
    if not e["closed"]:
        print("  ", e["symbol"], e["entry_session"], e["entry_cash"])

print("\n== reproduction_checks ==")
c = D["reproduction_checks"]
print("  type:", type(c).__name__, "len:", len(c))
print("  first:", json.dumps(c[0]) if isinstance(c, list) else json.dumps(c)[:300])
print("  names:", [x["name"] for x in c] if isinstance(c, list) else None)
