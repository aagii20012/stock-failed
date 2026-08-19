"""Corrected checks: (a) Gate 3 predicates/thresholds are unchanged from Attempt 2,
(b) the RA3 ladder really is RA2's minus the 5-8 percent rung, with band 0 extended."""

import json
import pathlib
from decimal import Decimal

crit3 = json.loads(
    pathlib.Path("config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))
crit2 = json.loads(
    pathlib.Path("config/generation_2/g2_gate_criteria_ra1.json").read_text("utf-8"))

print("== Gate 3 conditions: Attempt 3 vs Attempt 2")
c3 = {c["id"]: c for c in crit3["conditions"]}
c2 = {c["id"]: c for c in crit2["conditions"]}
print("   ids A3:", sorted(c3), "\n   ids A2:", sorted(c2))
print("   same id set:", sorted(c3) == sorted(c2))
for cid in sorted(c3):
    a, b = c3[cid], c2[cid]
    print("   %-6s required_verbatim same: %-5s | predicate same: %-5s" % (
        cid, a.get("required_verbatim") == b.get("required_verbatim"),
        a.get("predicate") == b.get("predicate")))
    if a.get("predicate") != b.get("predicate"):
        print("        A3: %s" % a.get("predicate"))
        print("        A2: %s" % b.get("predicate"))

print("\n== numeric thresholds, located rather than assumed")
for src, obj in (("A3", crit3), ("A2", crit2)):
    for key in obj:
        blob = json.dumps(obj[key])
        if any(t in blob for t in ('"15"', "15,", '"1.1"', "1.1,", '"30"', "30,")) and key in (
            "frozen_gate_json_companion_verbatim", "thresholds", "frozen_gate_text_verbatim"
        ):
            print("   %s.%s -> %s" % (src, key, blob[:400]))

print("\n== verdict tokens")
print("   A3:", json.dumps(crit3["verdict_token_derivation"].get("pass_token")),
      json.dumps(crit3["verdict_token_derivation"].get("fail_token")))
print("   A2:", json.dumps(crit2["verdict_token_derivation"].get("pass_token")),
      json.dumps(crit2["verdict_token_derivation"].get("fail_token")))
print("   disjoint:",
      not ({crit3["verdict_token_derivation"]["pass_token"],
            crit3["verdict_token_derivation"]["fail_token"]}
           & {crit2["verdict_token_derivation"]["pass_token"],
              crit2["verdict_token_derivation"]["fail_token"]}))

print("\n== RA3 ladder vs RA2, restated correctly")
p3 = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
p2 = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra1_protocol.json").read_text("utf-8"))
b3 = p3["risk_architecture"]["components"]["RA3-4"]["bands"]
b2 = p2["risk_architecture"]["components"]["RA2-4"]["bands"]


def scalar_at(bands, dd):
    dd = Decimal(dd)
    for b in bands:
        lo = Decimal(b["dd_from"])
        hi = None if b["dd_to_exclusive"] is None else Decimal(b["dd_to_exclusive"])
        if dd >= lo and (hi is None or dd < hi):
            return Decimal(b["scalar"])
    raise AssertionError("no band covers %s" % dd)


print("   %-8s %-8s %-8s %s" % ("dd", "RA2", "RA3", "differs"))
for dd in ["0.00", "0.02", "0.049", "0.05", "0.06", "0.079", "0.08", "0.09",
           "0.10", "0.12", "0.149", "0.15"]:
    s2, s3 = scalar_at(b2, dd), scalar_at(b3, dd)
    print("   %-8s %-8s %-8s %s" % (dd, s2, s3, "yes" if s2 != s3 else ""))

diff = [dd for dd in ["0.00", "0.02", "0.049", "0.05", "0.06", "0.079", "0.08", "0.09",
                      "0.10", "0.12", "0.149", "0.15"]
        if scalar_at(b2, dd) != scalar_at(b3, dd)]
print("   differing points:", diff)
print("   all differences inside [0.05, 0.08):",
      all(Decimal("0.05") <= Decimal(dd) < Decimal("0.08") for dd in diff))
print("   RA3 >= RA2 everywhere:",
      all(scalar_at(b3, dd) >= scalar_at(b2, dd)
          for dd in ["0.00", "0.02", "0.05", "0.06", "0.079", "0.08", "0.10", "0.20"]))

print("\n   contiguity: bands tile [0, inf) with no gap and no overlap")
assert b3[0]["dd_from"] == "0.00"
for a, b in zip(b3, b3[1:]):
    assert a["dd_to_exclusive"] == b["dd_from"], (a, b)
assert b3[-1]["dd_to_exclusive"] is None
print("   OK")

print("\n   absolute aggregate ceilings (0.50 base * ladder scalar):")
for b in b3:
    print("      band %d  dd>=%s  scalar %s  ->  %s" % (
        b["band"], b["dd_from"], b["scalar"],
        (Decimal("0.50") * Decimal(b["scalar"])).quantize(Decimal("0.000000001"))))
claim = p3["risk_architecture"]["components"]["RA3-4"]["provenance"]["absolute_ceilings"]
computed = [str((Decimal("0.50") * Decimal(b["scalar"])).quantize(Decimal("0.000000001")))
            for b in b3]
print("   protocol claims those three values:", all(v in claim for v in computed), computed)
