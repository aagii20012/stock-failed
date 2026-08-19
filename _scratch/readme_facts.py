import json, sys
from pathlib import Path
ROOT = Path.cwd()
assert (ROOT / "governance").is_dir(), "wrong cwd: %s" % ROOT
EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
print("top keys:", sorted(EV.keys()))
sv = EV["stage_verdict"]
print("stage_verdict keys:", sorted(sv.keys()))
for k in ("verdict", "verdict_token", "fail_route", "admitted_candidates"):
    print("  ", k, "=", EV["stage_verdict"].get(k))
cr = EV["candidate_results"][0]
print("candidate keys:", sorted(cr.keys()))
