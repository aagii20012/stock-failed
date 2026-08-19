import json
from pathlib import Path
ROOT = Path.cwd()
assert (ROOT / "governance").is_dir(), "wrong cwd: %s" % ROOT
EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
cr = EV["candidate_results"][0]
print("condition keys:", sorted(cr["conditions"][0].keys()))
for c in cr["conditions"]:
    cid = c.get("id") or c.get("condition")
    print(" ", cid, "|", c.get("verdict"), "|", json.dumps({k: v for k, v in c.items() if k not in ("id","verdict","what_is_read","requirement","note")}, ensure_ascii=True)[:300])
print()
print("scenario keys:", sorted(cr["scenario"].keys()) if isinstance(cr["scenario"], dict) else cr["scenario"])
