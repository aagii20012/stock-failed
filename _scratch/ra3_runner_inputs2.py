"""The two things the runner still cannot be written without: the sealed conflict numbers it must
cite, and the exact shape g2_selection_v2 hands back.

Attempt 2's runner cites `G2A2-CONFLICT-25` for the base-vs-stress scope contradiction. CFG-3105 and
CFG-3106 were sealed knowing that contradiction exists, so Attempt 3's number is either already
allocated in `conflicts_found` / `conflicts_declared_in_the_gate_criteria` or it is not -- and
inventing one that collides with a sealed number would be worse than citing none.
"""

import json
import pathlib
import sys
from dataclasses import fields

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
C3 = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))
G3 = json.loads((ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json").read_text("utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


print("=" * 100)
print("1. every sealed conflict id, and where it is declared")
seen = {}
for label, doc in (("CFG-3105", P3), ("CFG-3106", C3), ("GOV-2007", G3)):
    for key in ("conflicts_found", "conflicts_declared_in_the_gate_criteria", "conflicts"):
        node = doc.get(key)
        if not node:
            continue
        entries = node if isinstance(node, list) else [node]
        for entry in entries:
            if isinstance(entry, dict):
                cid = entry.get("id") or entry.get("conflict_id") or "<unnamed>"
                seen.setdefault(cid, []).append("%s.%s" % (label, key))
                print("   %-10s %-22s %s" % (label, cid, safe(entry.get("summary") or entry.get("statement") or entry.get("title") or "")[:104]))
            else:
                print("   %-10s %s" % (label, safe(entry)[:120]))
print()
print("   distinct ids: %d -> %s" % (len(seen), sorted(seen)))

print()
print("=" * 100)
print("2. any sealed text mentioning the base/stress gate-scope contradiction")
blob = json.dumps({"P3": P3, "C3": C3, "G3": G3}, ensure_ascii=False)
for needle in ("G2A2-CONFLICT-25", "reported_but_not_gating", "gates nothing at Gate 3",
               "both of its runs"):
    print("   %-32s occurrences=%d" % (needle, blob.count(needle)))

print()
print("   CFG-3106 measurement basis of S3-C1 and S3-C4 (does it still say 'base run'?):")
for cond in C3["conditions"]:
    if cond["id"] in ("S3-C1", "S3-C4"):
        m = cond.get("measurement", {})
        for key in sorted(m):
            if "basis" in key or "run" in key or "scope" in key:
                print("      %s.%-24s %s" % (cond["id"], key, safe(m[key])[:130]))
print("   CFG-3106 reported_but_not_gating:")
node = C3.get("reported_but_not_gating")
if node is None:
    print("      *** absent ***")
elif isinstance(node, list):
    for item in node:
        print("      - %s" % safe(json.dumps(item, ensure_ascii=False))[:150])
else:
    for key, value in node.items():
        print("      %-30s %s" % (key, safe(json.dumps(value, ensure_ascii=False))[:130]))

print()
print("=" * 100)
print("3. g2_selection_v2 -- the shapes the runner consumes")
from stockedge100.strategies import g2_selection_v2 as S
import inspect

for cls in (S.SelectionInputV2, S.NeighbourhoodScore, S.SelectionResultV2):
    print("   %-22s fields: %s" % (cls.__name__, [f.name for f in fields(cls)]))
    meths = [n for n in dir(cls) if not n.startswith("_")]
    print("   %-22s methods/props: %s" % ("", meths))
print()
for label, fn in (("load_selection_rule", S.load_selection_rule),
                  ("check_neighbourhood_structure", S.check_neighbourhood_structure),
                  ("check_seal_agreement", S.check_seal_agreement),
                  ("dissimilarity", S.dissimilarity)):
    print("   %-30s %s" % (label, inspect.signature(fn)))
print("   EXPECTED_STEP_CRITERIA         %s" % S.EXPECTED_STEP_CRITERIA)
print("   FORBIDDEN_FIELD_SUBSTRINGS     %s" % list(S.FORBIDDEN_FIELD_SUBSTRINGS))

print()
print("=" * 100)
print("4. g2_engine_ra3 risk_summary / clamp_summary -- do the RA1 keys survive?")
from stockedge100.backtest import g2_engine_ra3 as E
from stockedge100.backtest import g2_engine_ra1 as E2
for name in ("risk_summary", "clamp_summary"):
    own = name in vars(E.RotationEngineRA3)
    print("   RotationEngineRA3 defines %-14s %s  (inherited from RA1: %s)"
          % (name, own, hasattr(E2.RotationEngineRA1, name)))
print("   RA3_BAND_COUNT=%s  RA3_SHALLOWEST_ENGAGEMENT=%s" % (E.RA3_BAND_COUNT, E.RA3_SHALLOWEST_ENGAGEMENT))
print("   DELETED_RA2_TIER: %s" % safe(json.dumps(E.DELETED_RA2_TIER, ensure_ascii=False, default=str))[:200])
print("   RISK_DERIVED_ATTRIBUTES: %s" % list(E.RISK_DERIVED_ATTRIBUTES))

print()
print("=" * 100)
print("5. adversarial_test_requirements (for the test module after the runner)")
node = P3.get("adversarial_test_requirements")
if isinstance(node, dict):
    for key, value in node.items():
        print("   %-30s %s" % (key, safe(json.dumps(value, ensure_ascii=False))[:150]))
elif isinstance(node, list):
    for item in node:
        print("   - %s" % safe(json.dumps(item, ensure_ascii=False))[:170])

print()
print("=" * 100)
print("6. reproducibility_requirements")
node = P3.get("reproducibility_requirements")
if isinstance(node, dict):
    for key, value in node.items():
        print("   %-30s %s" % (key, safe(json.dumps(value, ensure_ascii=False))[:150]))
elif isinstance(node, list):
    for item in node:
        print("   - %s" % safe(json.dumps(item, ensure_ascii=False))[:170])
