"""Structural reconnaissance for the Attempt 3 package builder.

Prints the shape of every node the builder must read, from the files on disk, so the module is
written against measured structure rather than against Attempt 2's remembered structure.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def outline(node, prefix="", depth=0, maxdepth=2):
    if depth > maxdepth:
        return
    if isinstance(node, dict):
        for key in node:
            value = node[key]
            if isinstance(value, dict):
                print("%s%s/  (%d keys)" % (prefix, key, len(value)))
                outline(value, prefix + "   ", depth + 1, maxdepth)
            elif isinstance(value, list):
                kind = type(value[0]).__name__ if value else "empty"
                print("%s%s[]  len=%d of %s" % (prefix, key, len(value), kind))
                if value and isinstance(value[0], dict) and depth < maxdepth:
                    print("%s   [0] keys: %s" % (prefix, sorted(value[0])))
            else:
                print("%s%s = %s" % (prefix, key, safe(repr(value))[:150]))


EV = json.loads((ROOT / "reports/stage3_g2_attempt3/"
                 "STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))

for section in ("stage_verdict", "grid", "window", "determinism", "reconciliation",
                "prior_attempt_module_verification", "gate_scope", "gate",
                "ladder_engagement_comparison", "adaptation_disclosure_carriage",
                "risk_architecture", "run_span_recheck", "universe", "selection_determinism"):
    print("=" * 100)
    print("EVIDENCE.%s" % section)
    if section not in EV:
        print("   <ABSENT>")
        continue
    outline(EV[section], "   ")

print("=" * 100)
print("EVIDENCE.candidate_results[0]")
cand = EV["candidate_results"][0]
outline(cand, "   ", maxdepth=1)
print("   conditions[0]: %s" % safe(json.dumps(cand["conditions"][0]))[:500])
print("   admission_basis: %s" % safe(json.dumps(cand.get("admission_basis"), indent=2))[:1400])

print("=" * 100)
print("EVIDENCE scalar/top-level fields")
for key in sorted(EV):
    if not isinstance(EV[key], (dict, list)):
        print("   %-52s = %s" % (key, safe(repr(EV[key]))[:120]))

print("=" * 100)
print("EVIDENCE list fields")
for key in sorted(EV):
    if isinstance(EV[key], list):
        print("   %-52s len=%d" % (key, len(EV[key])))

CRIT = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json")
                  .read_text(encoding="utf-8"))
print("=" * 100)
print("CRITERIA top-level keys: %s" % sorted(CRIT))
print("verdict_token_derivation:")
print(safe(json.dumps(CRIT["verdict_token_derivation"], indent=2))[:2200])
print("conditions[0]: %s" % safe(json.dumps(CRIT["conditions"][0]))[:400])
print("condition ids: %s" % [c["id"] for c in CRIT["conditions"]])
