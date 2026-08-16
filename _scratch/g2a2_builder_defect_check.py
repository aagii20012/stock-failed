"""Verify (or refute) the two suspected defects in g2_stage3_attempt2_package.py against disk.

Nothing is edited here. ASCII output only.

  Defect 1  the limitation prose says the exposure maximum runs "0.5044 to 0.5184"; the README and
            the report say 0.5043 to 0.5184. The evidence stores these as high-precision decimal
            STRINGS, so they must be coerced before comparison -- and the report carries both 0.5043
            and 0.5044, so the context of each has to be read, not guessed.
  Defect 2  body.engine_capability_added.adversarial_tests says the test file "covers requirements
            AT-A through AT-G"; the protocol declares AT-A through AT-I.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "stockedge100"

ev = json.loads((ROOT / "reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json")
                .read_text(encoding="utf-8"))
report = (ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md").read_text(
    encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")

print("=== DEFECT 1: the exposure-maximum range, recomputed from the evidence ===")
vt = ev["variant_table"]
vals = []
for r in vt:
    for k in ("base_max_gross_fraction_observed", "stress_max_gross_fraction_observed"):
        vals.append((Decimal(str(r[k])), r["variant_id"], k))
vals.sort()
print("  %d measured values over %d variants" % (len(vals), len(vt)))
print("  minimum %s" % vals[0][0])
print("          %s / %s" % (vals[0][1], vals[0][2]))
print("  maximum %s" % vals[-1][0])
print("          %s / %s" % (vals[-1][1], vals[-1][2]))
lo4 = vals[0][0].quantize(Decimal("0.0001"))
hi4 = vals[-1][0].quantize(Decimal("0.0001"))
print("  half-even to 4dp : %s to %s" % (lo4, hi4))
print("  truncated to 4dp : %s to %s"
      % (str(vals[0][0])[:6], str(vals[-1][0])[:6]))

base_only = sorted((Decimal(str(r["base_max_gross_fraction_observed"])), r["variant_id"])
                   for r in vt)
print("  base-only minimum: %s (%s)" % (base_only[0][0], base_only[0][1]))
print("  base-only maximum: %s (%s)" % (base_only[-1][0], base_only[-1][1]))

print()
print("  where each literal appears in the report:")
for needle in ("0.5043", "0.5044"):
    for line in report.splitlines():
        if needle in line:
            trimmed = line.strip()
            print("    %s | %s" % (needle, (trimmed[:150] + "...") if len(trimmed) > 150
                                   else trimmed))
print()
print("  where each literal appears in the README:")
for needle in ("0.5043", "0.5044"):
    hits = [ln.strip() for ln in readme.splitlines() if needle in ln]
    print("    %s -> %d line(s)" % (needle, len(hits)))
    for ln in hits:
        print("        %s" % ((ln[:150] + "...") if len(ln) > 150 else ln))

print()
print("=== DEFECT 2: how many adversarial-test requirements are declared ===")
doc = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json")
                 .read_text(encoding="utf-8"))
block = doc["adversarial_test_requirements"]
ids = sorted(k for k in block if re.fullmatch(r"AT-[A-Z]", k))
print("  declared ids (%d): %s" % (len(ids), ids))
print("  non-id keys        : %s" % [k for k in block if k not in ids])
for k in ids:
    v = block[k]
    print("    %-5s %s" % (k, (str(v)[:120] + "...") if len(str(v)) > 120 else str(v)))
