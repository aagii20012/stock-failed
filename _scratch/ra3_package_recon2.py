"""Second reconnaissance pass: the sections the Attempt 3 builder reads, with the bulky
per-run digest maps elided so the structure is legible."""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")

SKIP = {"run_digests", "per_run", "variants", "inputs", "neighbour_scores", "per_variant"}


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def outline(node, prefix="", depth=0, maxdepth=2):
    if depth > maxdepth or not isinstance(node, dict):
        return
    for key, value in node.items():
        if key in SKIP:
            size = len(value) if isinstance(value, (dict, list)) else "?"
            print("%s%s  <elided, %s entries>" % (prefix, key, size))
            continue
        if isinstance(value, dict):
            print("%s%s/  (%d keys)" % (prefix, key, len(value)))
            outline(value, prefix + "   ", depth + 1, maxdepth)
        elif isinstance(value, list):
            kind = type(value[0]).__name__ if value else "empty"
            print("%s%s[]  len=%d of %s" % (prefix, key, len(value), kind))
            if value and isinstance(value[0], dict) and depth < maxdepth:
                print("%s   [0] keys: %s" % (prefix, sorted(value[0])))
            elif value and isinstance(value[0], str):
                print("%s   [0] = %s" % (prefix, safe(value[0])[:160]))
        else:
            print("%s%s = %s" % (prefix, key, safe(repr(value))[:160]))


EV = json.loads((ROOT / "reports/stage3_g2_attempt3/"
                 "STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))

print("#" * 100)
print("EVIDENCE top-level keys (%d):" % len(EV))
for key in EV:
    value = EV[key]
    kind = ("dict[%d]" % len(value) if isinstance(value, dict)
            else "list[%d]" % len(value) if isinstance(value, list) else type(value).__name__)
    print("   %-46s %s" % (key, kind))

for section in ("reconciliation", "prior_attempt_module_verification", "gate_scope",
                "ladder_engagement_comparison", "adaptation_disclosure_carriage",
                "risk_architecture", "sealed_inputs", "conflicts", "provenance",
                "no_broker_access", "authorization_state", "turnover"):
    print("#" * 100)
    print("EVIDENCE.%s" % section)
    if section not in EV:
        print("   <ABSENT>")
        continue
    node = EV[section]
    if isinstance(node, list):
        print("   list of %d; [0] = %s" % (len(node), safe(json.dumps(node[0]))[:400]))
    else:
        outline(node, "   ")

print("#" * 100)
print("EVIDENCE.candidate_results[0] (outline)")
cand = EV["candidate_results"][0]
outline(cand, "   ", maxdepth=1)

print("#" * 100)
print("candidate conditions (%d):" % len(cand["conditions"]))
for cond in cand["conditions"]:
    print("   %s" % safe(json.dumps(cond))[:300])

print("#" * 100)
print("candidate admission_basis:")
print(safe(json.dumps(cand.get("admission_basis"), indent=2))[:1600])

CRIT = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json")
                  .read_text(encoding="utf-8"))
print("#" * 100)
print("CRITERIA top-level keys: %s" % sorted(CRIT))
print("verdict_token_derivation:")
print(safe(json.dumps(CRIT["verdict_token_derivation"], indent=2))[:2400])
print("condition ids: %s" % [c["id"] for c in CRIT["conditions"]])
print("conditions[0] keys: %s" % sorted(CRIT["conditions"][0]))
print("conditions[0]: %s" % safe(json.dumps(CRIT["conditions"][0], indent=1))[:900])
