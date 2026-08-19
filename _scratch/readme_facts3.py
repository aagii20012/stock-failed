import json
from pathlib import Path
ROOT = Path.cwd()
assert (ROOT / "governance").is_dir(), "wrong cwd: %s" % ROOT
EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
sel = EV["selection"]
print("selection non-input keys:", [k for k in sel if k not in ("inputs",)])
for k in sel:
    if k in ("inputs", "steps", "selection_input_fields", "scored_quantities"):
        continue
    print("  ", k, "=", json.dumps(sel[k], ensure_ascii=True)[:900])
