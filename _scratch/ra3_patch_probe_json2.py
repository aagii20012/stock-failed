"""Second probe: the remaining nested structures the README patch reads."""
import json
import sys
from pathlib import Path

ROOT = Path.cwd()
if not (ROOT / "governance").is_dir():
    sys.exit("wrong cwd: %s" % ROOT)

EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json"
                 ).read_text(encoding="utf-8"))


def a(v):
    return repr(v).encode("ascii", "backslashreplace").decode("ascii")


cr = EV["candidate_results"][0]
st = cr["stress_evaluation"]
print("### stress_evaluation keys")
for k in sorted(st.keys()):
    v = st[k]
    print("  ", k, "=", a(v)[:110] if not isinstance(v, list) or k.startswith("conditions_") else a(v)[:110])

sel = EV["selection"]
print("### selection.selected_score")
for k in sorted(sel["selected_score"].keys()):
    print("  ", k, "=", a(sel["selected_score"][k])[:200])

print("### selection.neighbour_scores  (%d entries)" % len(sel["neighbour_scores"]))
for e in sel["neighbour_scores"]:
    print("  ", a({k: e[k] for k in e if k in ("variant_id", "instability_score", "neighbour_count")}))

print("### selection.result")
for k in sorted(sel["result"].keys()):
    print("  ", k, "=", a(sel["result"][k])[:160])

print("### ladder_engagement_comparison.sessions_at_full_sizing")
for k, v in EV["ladder_engagement_comparison"]["sessions_at_full_sizing"].items():
    print("  ", k, "=", a(v)[:160])

print("### prior_attempt_module_verification")
for k, v in EV["prior_attempt_module_verification"].items():
    print("  ", k, "=", a(v)[:150])

print("### multiple_comparisons_disclosure scalars")
for k, v in EV["multiple_comparisons_disclosure"].items():
    if isinstance(v, int):
        print("  ", k, "=", v)

print("### stage_verdict")
for k, v in EV["stage_verdict"].items():
    print("  ", k, "=", a(v)[:120])

print("### disclosure length =", len(EV["adaptation_disclosure_verbatim"]))
