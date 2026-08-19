import json
from pathlib import Path
ROOT = Path.cwd()
assert (ROOT / "governance").is_dir(), "wrong cwd: %s" % ROOT
EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
cr = EV["candidate_results"][0]
se = cr["stress_evaluation"]
print("stress keys:", sorted(se.keys()) if isinstance(se, dict) else type(se))
conds = se.get("conditions") if isinstance(se, dict) else None
if conds:
    for c in conds:
        print("  ", c.get("id"), c.get("verdict"), str(c.get("measured"))[:44])
pm = EV["prior_attempt_module_verification"]
print()
print("module verification keys:", sorted(pm.keys()) if isinstance(pm, dict) else pm)
for k, v in (pm.items() if isinstance(pm, dict) else []):
    if k in ("modules", "module_digests", "digests"):
        print("  ", k, "= <%d entries>" % (len(v) if hasattr(v, "__len__") else -1))
    else:
        print("  ", k, "=", json.dumps(v, ensure_ascii=True)[:400])
print()
print("immutable:", json.dumps(EV["prior_attempt_modules_immutable"], ensure_ascii=True)[:600])
