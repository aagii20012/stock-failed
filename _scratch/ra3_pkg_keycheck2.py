"""Eighteenth pass: the four key lists the last probe left ambiguous."""

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

print("EV top-level keys:")
print(safe(sorted(EV)))
print("-" * 100)
print("EV.risk_architecture keys: %s" % safe(sorted(EV["risk_architecture"])))
print("-" * 100)
print("PROT.risk_architecture keys: %s" % safe(sorted(PROT["risk_architecture"])))
print("-" * 100)
print("CRIT.verdict_token_derivation keys: %s" % safe(sorted(CRIT["verdict_token_derivation"])))
print(safe(json.dumps(CRIT["verdict_token_derivation"], indent=1))[:5000])
print("-" * 100)
print("EV.selection.rule_source: %s" % safe(json.dumps(EV["selection"]["rule_source"])))
print("EV.selection.no_reselection: %s" % safe(json.dumps(EV["selection"]["no_reselection"]))[:600])
print("EV.selection.scored_quantities: %s" % safe(json.dumps(EV["selection"]["scored_quantities"])))
print("EV.selection.steps:")
print(safe(json.dumps(EV["selection"]["steps"], indent=1)))
print("EV.selection.note:")
print(safe(EV["selection"]["note"]))
print("-" * 100)
print("EV.selection.inputs type=%s" % type(EV["selection"]["inputs"]).__name__)
inp = EV["selection"]["inputs"]
if isinstance(inp, dict):
    print("   keys: %s" % safe(sorted(inp)))
else:
    print("   len=%d first=%s" % (len(inp), safe(json.dumps(inp[0]))))
print("-" * 100)
print("EV.selection.neighbour_scores len=%d" % len(EV["selection"]["neighbour_scores"]))
print(safe(json.dumps(EV["selection"]["neighbour_scores"][0], indent=1)))
print("-" * 100)
print("PROT.structural_consequences SC keys: %s"
      % safe(sorted(PROT["structural_consequences_declared_before_running"])))
for k in ("SC-6", "SC-7", "SC-8"):
    node = PROT["structural_consequences_declared_before_running"][k]
    print("   %s: %s" % (k, safe(json.dumps(node, indent=1))[:900]))
print("-" * 100)
print("EV.risk_architecture.generation_1_provenance:")
print(safe(json.dumps(EV["risk_architecture"].get("generation_1_provenance", "<absent>"),
                      indent=1))[:1400])
