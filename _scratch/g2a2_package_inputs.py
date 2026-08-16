"""Dump the sealed strings the Attempt 2 package builder must index, so none is hand-typed.

The 842-character adaptation disclosure is deliberately NEVER printed: the sealed encoding_note
forbids writing it to a cp1252 console, and printing it would raise UnicodeEncodeError anyway.
Only its length and digest are shown. ASCII output only.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


protocol = load("config/generation_2/g2_rotation_ra1_protocol.json")
criteria = load("config/generation_2/g2_gate_criteria_ra1.json")
lock = load("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json")
ev = load("reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json")


def line(label, value, width=110):
    text = json.dumps(value) if not isinstance(value, str) else value
    text = text.replace("\n", " ")
    if len(text) > width:
        text = text[:width] + " ..."
    print("  %-46s %s" % (label, text))


print("== protocol scalars ==")
for key in ("artifact_id", "generation_id", "attempt", "strategy_id", "candidate_index",
            "family", "declared_before_any_strategy_code"):
    line("protocol[%s]" % key, protocol[key])

print()
print("== protocol top-level keys ==")
for key in protocol:
    print("   ", key)

print()
print("== run_span ==")
for key, value in protocol["run_span"].items():
    line(key, value)

print()
print("== risk_architecture (top level) ==")
for key, value in protocol["risk_architecture"].items():
    if isinstance(value, list):
        line(key, "list(%d)" % len(value))
    elif isinstance(value, dict):
        line(key, "dict %s" % sorted(value))
    else:
        line(key, value)

print()
print("== risk_architecture components ==")
comps = protocol["risk_architecture"]["components"]
for key, comp in comps.items():
    print("   ", key, "|", str(comp.get("name"))[:60], "|", sorted(comp)[:12])

print()
print("== runs_per_variant / grid ==")
line("grid.size", protocol["grid"]["size"])
line("grid.axes", protocol["grid"]["axes"])
line("runs_per_variant", protocol["runs_per_variant"])

print()
print("== attempt_1_ref ==")
for key, value in protocol["attempt_1_ref"].items():
    line(key, value)

print()
print("== multiple_comparisons_disclosure ==")
print(protocol["multiple_comparisons_disclosure"])

print()
print("== structural_consequences_declared_before_running ==")
sc = protocol["structural_consequences_declared_before_running"]
print("  type:", type(sc).__name__)
print(json.dumps(sc, indent=2)[:3000])

print()
print("== explicit_non_authorizations ==")
print(json.dumps(protocol["explicit_non_authorizations"], indent=2)[:2000])

print()
print("== gate_evaluation_scope ==")
print(json.dumps(protocol["gate_evaluation_scope"], indent=2)[:2500])

print()
print("== representative_selection_rule keys ==")
print(" ", sorted(protocol["representative_selection_rule"]))

print()
print("== criteria verdict_token_derivation ==")
print(json.dumps(criteria["verdict_token_derivation"], indent=2)[:3000])

print()
print("== criteria top-level keys ==")
print(" ", sorted(criteria))

print()
print("== partition lock keys ==")
print(" ", sorted(lock))
print()
print("validation_reuse_disclosure:")
print(lock["validation_reuse_disclosure"].encode("ascii", "backslashreplace").decode("ascii"))

print()
print("== disclosure identity (never printed) ==")
line("characters", ev["adaptation_disclosure_carriage"]["characters"])
line("sha256_of_utf8", ev["adaptation_disclosure_carriage"]["sha256_of_utf8"])
line("must_appear_verbatim_in",
     protocol["adaptation_disclosure_carriage_requirement"]["must_appear_verbatim_in"], 400)

print()
print("== evidence: gate_scope ==")
print(json.dumps(ev["gate_scope"], indent=2)[:2500])

print()
print("== evidence: selection keys ==")
print(" ", sorted(ev["selection"]))
line("return_blind_enforcement", ev["selection"].get("return_blind_enforcement"), 400)

print()
print("== evidence: run_span_recheck ==")
print(json.dumps(ev["run_span_recheck"], indent=2)[:1500])

print()
print("== evidence: window ==")
print(json.dumps(ev["window"], indent=2)[:1500])

print()
print("== evidence: universe keys ==")
print(" ", sorted(ev["universe"]))

print()
print("== evidence: attempt_1_module_verification ==")
amv = ev["attempt_1_module_verification"]
for key in sorted(amv):
    if key == "modules":
        line(key, "list/dict(%d)" % len(amv[key]))
    else:
        line(key, amv[key])
