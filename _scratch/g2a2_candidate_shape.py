"""Exact key shapes of candidate_results[0] and its stress_evaluation, for the package builder.

The builder aggregates on ``satisfied``, not on ``verdict == "MET"`` - aggregating on MET produced a
false FAIL for S3-C6 in Generation 1 Stage 3. This script exists so the aggregation is written
against the real key names rather than remembered ones. ASCII output only.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
ev = json.loads(
    (ROOT / "reports" / "stage3_g2_attempt2"
     / "STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8")
)

cand = ev["candidate_results"][0]
print("candidate_results length:", len(ev["candidate_results"]))
print()
print("== top-level keys of candidate_results[0] ==")
for key in cand:
    value = cand[key]
    kind = type(value).__name__
    if isinstance(value, (dict, list)):
        print("  %-46s %s(%d)" % (key, kind, len(value)))
    else:
        print("  %-46s %s = %s" % (key, kind, str(value)[:60]))

print()
print("== stress_evaluation keys ==")
for key in cand["stress_evaluation"]:
    value = cand["stress_evaluation"][key]
    kind = type(value).__name__
    if isinstance(value, (dict, list)):
        print("  %-46s %s(%d)" % (key, kind, len(value)))
    else:
        print("  %-46s %s = %s" % (key, kind, str(value)[:60]))

print()
print("== every base condition row, all keys ==")
for row in cand["conditions"]:
    print("  %s  verdict=%-28s satisfied=%s" % (row["id"], row["verdict"], row["satisfied"]))
    for key in sorted(row):
        if key in ("id", "verdict", "satisfied"):
            continue
        text = json.dumps(row[key]) if not isinstance(row[key], str) else row[key]
        text = text.replace("\n", " ")
        print("        %-22s %s" % (key, text[:150]))
    print()

print("== every stress condition row (compact) ==")
for row in cand["stress_evaluation"]["conditions"]:
    print("  %s  verdict=%-28s satisfied=%-5s measured=%s" % (
        row["id"], row["verdict"], row["satisfied"], str(row["measured"])[:40]))

print()
print("== admission_basis ==")
for key, value in cand["admission_basis"].items():
    text = json.dumps(value) if not isinstance(value, str) else value
    print("  %-46s %s" % (key, text.replace("\n", " ")[:160]))

print()
print("== selection step_1 / step_2 / step_3 ==")
for key in ("step_1", "step_2", "step_3"):
    print("  %s: %s" % (key, json.dumps(ev["selection"][key])[:600]))

print()
print("== evidence: reconciliation / determinism / grid ==")
for section in ("reconciliation", "grid"):
    print("  %s: %s" % (section, json.dumps(ev[section])[:600]))
print("  determinism keys:", sorted(ev["determinism"]))
print("  determinism.all_identical:", ev["determinism"]["all_identical"],
      "runs_compared:", ev["determinism"]["runs_compared"])

print()
print("== evidence: reported_for_every_variant_coverage ==")
print(" ", json.dumps(ev["reported_for_every_variant_coverage"])[:800])

print()
print("== evidence: risk_architecture summary keys ==")
print(" ", sorted(ev["risk_architecture"]) if isinstance(ev["risk_architecture"], dict) else "list")

print()
print("== evidence: structural_consequences / non_authorizations types ==")
print("  structural:", type(ev["structural_consequences_declared_before_running"]).__name__)
print("  non_auth:", type(ev["explicit_non_authorizations"]).__name__,
      len(ev["explicit_non_authorizations"]))
print("  live_trading_authorized:", ev["live_trading_authorized"])
