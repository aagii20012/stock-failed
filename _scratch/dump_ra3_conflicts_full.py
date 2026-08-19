"""Dump every key of every conflict record in both Attempt 3 config artifacts."""

import json
import pathlib


def a(s):
    return str(s).encode("ascii", "backslashreplace").decode("ascii")


proto = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra3_protocol.json").read_text(encoding="utf-8"))
crit = json.loads(
    pathlib.Path("config/generation_2/g2_gate_criteria_ra3.json").read_text(encoding="utf-8"))

for label, doc in (("PROTOCOL CFG-3105", proto), ("CRITERIA CFG-3106", crit)):
    print("\n\n########## %s conflicts_found: %d" % (label, len(doc["conflicts_found"])))
    for c in doc["conflicts_found"]:
        print("\n-- %s   keys=%s" % (c.get("id"), sorted(c.keys())))
        for k, v in c.items():
            if k == "id":
                continue
            print("   %-24s %s" % (k, a(v)))
