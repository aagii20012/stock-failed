"""Dump the sealed Attempt 2 protocol/criteria key sets the evidence module must read.

ASCII output only. The adaptation disclosure carries em dashes and must never be printed to a
cp1252 console, so it is reported as a length and a boolean, never as text.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"

protocol = json.loads(
    (ROOT / "config" / "generation_2" / "g2_rotation_ra1_protocol.json").read_text(encoding="utf-8")
)
criteria = json.loads(
    (ROOT / "config" / "generation_2" / "g2_gate_criteria_ra1.json").read_text(encoding="utf-8")
)

print("== protocol top-level keys ==")
for key in protocol:
    value = protocol[key]
    kind = type(value).__name__
    size = len(value) if isinstance(value, (list, dict, str)) else ""
    print("  %-52s %-6s %s" % (key, kind, size))

print()
print("== criteria top-level keys ==")
for key in criteria:
    value = criteria[key]
    print("  %-52s %-6s %s" % (
        key, type(value).__name__,
        len(value) if isinstance(value, (list, dict, str)) else ""))

print()
print("== eligible_universe keys ==")
print(" ", sorted(protocol["eligible_universe"]))

print()
print("== adaptation disclosure (never printed) ==")
disc = protocol["adaptation_disclosure_verbatim"]
print("  type:", type(disc).__name__, " chars:", len(disc))
print("  ascii-safe:", disc.isascii())
print("  sha256-of-utf8:", __import__("hashlib").sha256(disc.encode("utf-8")).hexdigest())
req = protocol["adaptation_disclosure_carriage_requirement"]
print("  carriage keys:", sorted(req))
for path in req["must_appear_verbatim_in"]:
    print("    -", path)

print()
print("== explicit_non_authorizations ==")
print(" ", json.dumps(protocol["explicit_non_authorizations"], indent=2)[:1200])

print()
print("== gate_evaluation_scope keys ==")
print(" ", sorted(protocol["gate_evaluation_scope"]))

print()
print("== multiple_comparisons_disclosure type ==")
mcd = protocol["multiple_comparisons_disclosure"]
print(" ", type(mcd).__name__, sorted(mcd) if isinstance(mcd, dict) else len(mcd))
