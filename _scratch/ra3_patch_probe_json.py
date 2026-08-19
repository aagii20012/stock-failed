"""Print the exact key paths the README patch needs, so no literal is guessed."""
import json
import sys
from pathlib import Path

ROOT = Path.cwd()
if not (ROOT / "governance").is_dir():
    sys.exit("wrong cwd: %s" % ROOT)

EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json"
                 ).read_text(encoding="utf-8"))
PR = json.loads((ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
                 ).read_text(encoding="utf-8"))


def ascii_only(v):
    return repr(v).encode("ascii", "backslashreplace").decode("ascii")


cr = EV["candidate_results"][0]
print("### candidate_results[0] keys")
for k in sorted(cr.keys()):
    print("  ", k, "->", type(cr[k]).__name__)

print("### admission_basis keys")
for k in sorted(cr["admission_basis"].keys()):
    v = cr["admission_basis"][k]
    if isinstance(v, (bool, int, list)) or (isinstance(v, str) and len(v) < 90):
        print("  ", k, "=", ascii_only(v))
    else:
        print("  ", k, "-> str len", len(v))

print("### selection keys")
for k in sorted(EV["selection"].keys()):
    print("  ", k, "->", type(EV["selection"][k]).__name__)

print("### top-level keys containing 'score' or 'neighbour'")
for k in sorted(EV.keys()):
    if "score" in k or "neighbour" in k or "select" in k:
        print("  ", k, "->", type(EV[k]).__name__)

print("### ladder_engagement_comparison keys")
lec = EV["ladder_engagement_comparison"]
for k in sorted(lec.keys()):
    print("  ", k, "->", type(lec[k]).__name__)
for k in sorted(lec.keys()):
    if isinstance(lec[k], dict):
        print("###", "ladder_engagement_comparison[%s] keys" % k)
        for kk in sorted(lec[k].keys()):
            print("  ", kk, "->", ascii_only(lec[k][kk])[:160])
        break

print("### contamination_measurement keys")
cm = PR["contamination_measurement"]
for k in sorted(cm.keys()):
    v = cm[k]
    if isinstance(v, str) and len(v) > 90:
        print("  ", k, "-> str len", len(v), "tail:", ascii_only(v[-70:]))
    else:
        print("  ", k, "=", ascii_only(v)[:200])
