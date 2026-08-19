import json
from pathlib import Path
ROOT = Path.cwd()
assert (ROOT / "governance").is_dir(), "wrong cwd: %s" % ROOT
EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
def show(label, obj, depth=0):
    print(label, "->", json.dumps(obj, indent=2, ensure_ascii=True)[:2600])
show("selection", EV["selection"])
show("ladder_engagement_comparison", EV["ladder_engagement_comparison"])
show("multiple_comparisons_disclosure", EV["multiple_comparisons_disclosure"])
