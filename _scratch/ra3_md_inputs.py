"""Gather every measured value the Attempt 3 Markdown must carry, from disk.

Run from stockedge100/ with PYTHONPATH=src. Reads session dates only, never prices.
"""

import json
import pathlib
import re
import sys
from decimal import ROUND_DOWN, Decimal

from stockedge100.reporting.g2_partition_lock import (
    CHARTER_ID,
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    GENERATION_1_HOLDOUT_END,
    GENERATION_1_HOLDOUT_START,
    HOLDOUT_END,
    HOLDOUT_START,
    UNIVERSE,
    UNIVERSE_VERSION,
    VALIDATION_END,
    VALIDATION_START,
    generation_identity,
)
from stockedge100.reporting.g2_rotation_preregistration import (
    FREQUENCIES,
    LOOKBACKS,
    POSITION_COUNTS,
    WEIGHT_QUANTUM,
    measure_span,
)

span = measure_span()
print("== measure_span()")
for k in sorted(span):
    print("   %-40s %s" % (k, span[k]))

print("\n== identity")
ident = generation_identity()
for k in sorted(ident):
    print("   %-40s %s" % (k, ident[k]))
print("   %-40s %s" % ("charter_id", CHARTER_ID))
print("   %-40s %s" % ("universe_version", UNIVERSE_VERSION))
print("   %-40s %s" % ("universe_count", len(UNIVERSE)))
print("   %-40s %s" % ("windows", [DEVELOPMENT_START, DEVELOPMENT_END, VALIDATION_START,
                                   VALIDATION_END, GENERATION_1_HOLDOUT_START,
                                   GENERATION_1_HOLDOUT_END, HOLDOUT_START, HOLDOUT_END]))

proto = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra3_protocol.json").read_text(encoding="utf-8"))
ceiling = Decimal(proto["risk_architecture"]["components"]["RA3-1"]["value"])
conc = Decimal(proto["concentration_ceiling"]["value"])
print("\n== sizing (recomputed from RA3-1 %s and concentration %s)" % (ceiling, conc))
for k in POSITION_COUNTS:
    w = min(ceiling / Decimal(k), conc).quantize(WEIGHT_QUANTUM, rounding=ROUND_DOWN)
    print("   | %d | %.9f | %.9f |" % (k, w, (w * k).quantize(WEIGHT_QUANTUM)))

print("\n== grid table rows (Attempt 3 ids)")
counts = {"MONTHLY": span["monthly_rebalance_sessions"],
          "QUARTERLY": span["quarterly_rebalance_sessions"]}
for row in proto["grid"]["variants"]:
    w = Decimal(row["target_weight_per_position"])
    g = (w * row["top_k"]).quantize(WEIGHT_QUANTUM)
    print("| %d | `%s` | %d | %d | %s | %s | %.9f | %d |" % (
        row["index"], row["variant_id"], row["lookback_months"], row["top_k"],
        row["rebalance_frequency"], row["target_weight_per_position"], g,
        counts[row["rebalance_frequency"]]))

print("\n== axes/format")
print("   LOOKBACKS", LOOKBACKS, "POSITION_COUNTS", POSITION_COUNTS, "FREQUENCIES", FREQUENCIES)
print("   variant_id_format", proto["grid"]["variant_id_format"])

print("\n== Attempt 2 Markdown section headings (structure to mirror)")
md = pathlib.Path("governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md").read_text(
    encoding="utf-8")
print("   bytes:", len(md.encode("utf-8")), "lines:", md.count("\n"))
for line in md.splitlines():
    if line.startswith("#"):
        print("  ", line)

print("\n== conflicts in CFG-3105 and CFG-3106")
crit = json.loads(
    pathlib.Path("config/generation_2/g2_gate_criteria_ra3.json").read_text(encoding="utf-8"))
for label, obj in (("protocol", proto), ("criteria", crit)):
    for c in obj["conflicts_found"]:
        print("   %-9s %-18s %s" % (label, c["id"], str(c.get("title", c.get("summary", "")))[:95]))

print("\n== tokens")
print("  ", json.dumps(crit["verdict_token_derivation"], ensure_ascii=False)[:600])

print("\n== attempt refs carried in the protocol")
for k in sorted(proto):
    if "attempt_1" in k or "attempt_2" in k:
        print("   %s -> %s" % (k, json.dumps(proto[k], ensure_ascii=False)[:400]))

sys.stdout.flush()
