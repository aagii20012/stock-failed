"""Twelfth pass: the sealed conflict texts, so the package quotes rather than paraphrases."""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


EV = load("reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
PROT = load("config/generation_2/g2_rotation_ra3_protocol.json")
CRIT = load("config/generation_2/g2_gate_criteria_ra3.json")

for name, node in (("CRIT", CRIT), ("PROT", PROT)):
    cf = node["conflicts_found"]
    print("=" * 100)
    print("%s.conflicts_found  type=%s len=%d" % (name, type(cf).__name__, len(cf)))
    if isinstance(cf, dict):
        for key in sorted(cf):
            print("   %-24s %s" % (key, safe(json.dumps(cf[key], default=str))[:260]))
    else:
        for item in cf:
            print("   %s" % safe(json.dumps(item, default=str))[:260])

print("=" * 100)
print("EV.conflicts_declared_in_the_gate_criteria:")
print(safe(json.dumps(EV["conflicts_declared_in_the_gate_criteria"], indent=1))[:2600])

print("=" * 100)
print("EV.prior_attempt_modules_immutable:")
print(safe(json.dumps(EV["prior_attempt_modules_immutable"], indent=1, default=str))[:1800])

print("=" * 100)
print("PROT.explicit_non_authorizations (%d):" % len(PROT["explicit_non_authorizations"]))
for item in PROT["explicit_non_authorizations"]:
    print("   - %s" % safe(item)[:160])

print("=" * 100)
print("PROT.runs_per_variant:")
print(safe(json.dumps(PROT["runs_per_variant"], indent=1))[:700])

print("=" * 100)
print("PROT.what_makes_this_genuinely_cross_sectional:")
print(safe(json.dumps(PROT["what_makes_this_genuinely_cross_sectional"], default=str))[:900])

print("=" * 100)
print("PROT.concentration_ceiling:")
print(safe(json.dumps(PROT["concentration_ceiling"], indent=1, default=str))[:1600])

print("=" * 100)
print("CRIT.evaluation_integrity_rules keys/type: %s" % type(CRIT["evaluation_integrity_rules"]).__name__)
print(safe(json.dumps(CRIT["evaluation_integrity_rules"], indent=1, default=str))[:1400])
