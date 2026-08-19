"""Exact text of the list-shaped blocks the Attempt 3 Markdown must transcribe."""

import json
import pathlib


def a(s):
    return str(s).encode("ascii", "backslashreplace").decode("ascii")


proto = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra3_protocol.json").read_text(encoding="utf-8"))

print("########## structural_consequences_declared_before_running")
for k, v in proto["structural_consequences_declared_before_running"].items():
    print("\n-- %s" % k)
    if isinstance(v, dict):
        for kk, vv in v.items():
            print("   %-26s %s" % (kk, a(vv)))
    else:
        print("   %s" % a(v))

print("\n\n########## adversarial_test_requirements")
for k, v in proto["adversarial_test_requirements"].items():
    print("\n-- %s" % k)
    if isinstance(v, dict):
        for kk, vv in v.items():
            print("   %-26s %s" % (kk, a(vv)))
    else:
        print("   %s" % a(v))

print("\n\n########## explicit_non_authorizations (%d)"
      % len(proto["explicit_non_authorizations"]))
for i, s in enumerate(proto["explicit_non_authorizations"], 1):
    print("  %2d. %s" % (i, a(s)))

print("\n\n########## selection step 2 neighbour detail")
sel = proto["representative_selection_rule"]
step2 = sel["steps"][1] if isinstance(sel.get("steps"), list) else sel
print(a(json.dumps(step2, indent=2, ensure_ascii=False)))
