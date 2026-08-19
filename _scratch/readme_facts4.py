import json
from pathlib import Path
ROOT = Path.cwd()
assert (ROOT / "governance").is_dir(), "wrong cwd: %s" % ROOT
EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
cr = EV["candidate_results"][0]
print("variant_id =", cr["variant_id"])
print("admitted =", cr["admitted"])
print("conditions_met =", cr["conditions_met"])
print("conditions_not_met =", cr["conditions_not_met"])
print("conditions_not_applicable =", cr["conditions_not_applicable"])
print("conditions_not_evaluable =", cr["conditions_not_evaluable"])
print()
for c in cr["conditions"]:
    print(" ", c.get("condition_id"), "|", c.get("verdict"), "|", str(c.get("observed"))[:44], "|", c.get("threshold"))
print()
print("admission_basis:", json.dumps(cr["admission_basis"], ensure_ascii=True, indent=1)[:1800])
