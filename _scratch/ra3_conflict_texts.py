"""Fifteenth pass: full sealed text of every conflict the package will cite, plus three loose ends.

The package must quote the seal rather than paraphrase it, and recon12 truncated at 260 chars.
"""

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

WANT = {
    "G2A3-CONFLICT-19", "G2A3-CONFLICT-21", "G2A3-CONFLICT-22", "G2A3-CONFLICT-24",
    "G2A3-CONFLICT-26", "G2A3-CONFLICT-27", "G2A3-CONFLICT-28", "G2A3-CONFLICT-29",
    "G2A3-CONFLICT-30", "G2A3-CONFLICT-31", "G2A3-CONFLICT-32", "G2A3-CONFLICT-33",
    "G2A2-CONFLICT-18", "G2A2-CONFLICT-20", "G2A2-CONFLICT-23", "G2A2-CONFLICT-25",
    "G2A3-CONFLICT-34", "G2A3-CONFLICT-35", "G2A3-CONFLICT-36", "G2A3-CONFLICT-37",
    "G2A3-CONFLICT-38",
}

for name, node in (("CRIT", CRIT), ("PROT", PROT)):
    print("=" * 100)
    print("%s.conflicts_found" % name)
    for item in node["conflicts_found"]:
        cid = item.get("id") if isinstance(item, dict) else None
        if cid in WANT:
            print("-" * 100)
            print(safe(json.dumps(item, indent=1, default=str)))

print("=" * 100)
print("PROT.structural_consequences_declared_before_running:")
print(safe(json.dumps(PROT["structural_consequences_declared_before_running"], indent=1))[:4000])

print("=" * 100)
print("EV.selection_determinism keys: %s" % safe(sorted(EV["selection_determinism"])))
print(safe(json.dumps(EV["selection_determinism"], indent=1, default=str))[:1400])

print("=" * 100)
print("EV.multiple_comparisons_disclosure:")
print(safe(json.dumps(EV["multiple_comparisons_disclosure"], indent=1, default=str))[:2200])

print("=" * 100)
print("PROT.adaptation_disclosure_carriage_requirement.must_appear_verbatim_in:")
for rel in PROT["adaptation_disclosure_carriage_requirement"]["must_appear_verbatim_in"]:
    print("   %s" % rel)

print("=" * 100)
print("EV.ladder_engagement_comparison (full):")
print(safe(json.dumps(EV["ladder_engagement_comparison"], indent=1, default=str))[:2600])

print("=" * 100)
sel = EV["selection"]["selected_score"]
rep = EV["selection"]["result"]["selected_variant_id"]
row = next(r for r in EV["variant_table"] if r["variant_id"] == rep)
for key in ("base_profit_factor", "base_total_return", "stress_total_return",
            "base_max_gross_fraction_observed", "base_combined_scalar_minimum",
            "base_ladder_descents", "base_lockout_arms", "base_stops_filled",
            "base_fill_count", "base_closed_trades"):
    print("   rep row %-38s %s" % (key, safe(row.get(key, "<absent>"))))
print("   rep row keys: %s" % safe(sorted(row)))
