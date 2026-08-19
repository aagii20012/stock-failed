"""Pass 20: every field the Attempt 3 research report must quote, plus a line-ending census."""

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
LOCK = load("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json")

print("== line endings ==")
for rel in ("governance/generation_2/STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md",
            "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md",
            "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md",
            "README.md"):
    raw = (ROOT / rel).read_bytes()
    print("  %-62s bytes=%-8d CRLF=%-5d bare_LF=%d"
          % (rel.split("/")[-1], len(raw), raw.count(b"\r\n"),
             raw.count(b"\n") - raw.count(b"\r\n")))

print("\n== PROT top-level keys ==")
print(safe(sorted(PROT)))
print("\n== CRIT top-level keys ==")
print(safe(sorted(CRIT)))
print("\n== LOCK top-level keys ==")
print(safe(sorted(LOCK)))

print("\n== anything seal-ish in PROT ==")
for k in sorted(PROT):
    if any(t in k for t in ("seal", "contamination", "measure", "authored", "generated")):
        print("  %-56s %s" % (k, safe(json.dumps(PROT[k], default=str))[:400]))

print("\n== PROT.risk_architecture ==")
print(safe(json.dumps(PROT["risk_architecture"], indent=1))[:4500])

print("\n== PROT.adaptation_disclosure_carriage_requirement ==")
print(safe(json.dumps(PROT["adaptation_disclosure_carriage_requirement"], indent=1))[:2500])

print("\n== PROT.representative_selection_rule ==")
print(safe(json.dumps(PROT["representative_selection_rule"], indent=1))[:4000])

print("\n== PROT.multiple_comparisons_disclosure ==")
print(safe(json.dumps(PROT["multiple_comparisons_disclosure"], indent=1))[:3000])
