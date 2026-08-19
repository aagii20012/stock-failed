"""Recompute SEL-2's selection from the evidence file's own inputs, independently of its result.

Not a re-read of `selected_score`: this rebuilds `SelectionInputV2` records from the recorded
per-variant statistics, calls `select_representative_v2`, and compares the recomputed winner and
score table against what the evidence recorded. A disagreement is the finding.

The dataclass field names are not the serialised ones (`score` on the object, `instability_score`
in the JSON), so the comparison is written against both spellings deliberately.
"""

import json
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import g2_selection_v2 as sel

EVID = ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json"
doc = json.loads(EVID.read_text(encoding="utf-8"))
node = doc["selection"]

records = [sel.SelectionInputV2(**row) for row in node["inputs"]]
print("rebuilt %d SelectionInputV2 records from the evidence file" % len(records))

result = sel.select_representative_v2(records)
selected_id = result.selected.variant_id if hasattr(result.selected, "variant_id") else result.selected
print("recomputed winner = %s" % selected_id)
print("recorded  winner  = %s" % node["selected_variant_id"])
assert selected_id == node["selected_variant_id"], "SELECTION DISAGREES"
assert result.decided_at_step == node["decided_at_step"], "STEP DISAGREES"
print("decided_at_step   = %d (agrees)" % result.decided_at_step)
print("eligible = %d of %d, ineligible = %d"
      % (len(result.eligible), len(records), len(result.ineligible)))
print()

scores = dict(result.scores)          # mapping variant_id -> NeighbourhoodScore
selected = scores[selected_id]
print("ranking (as the rule ordered it): %s"
      % [r if isinstance(r, str) else getattr(r, "variant_id", r) for r in result.ranking][:4])


def short(v):
    return v.replace("SE100-G2-S3-C3-ROTATION-RA3-", "")


print("full instability ranking (lower is more stable):")
ordered = sorted(scores.values(), key=lambda s: (s.score, s.variant_id))
for rank, s in enumerate(ordered, 1):
    mark = "  <== SELECTED" if s.variant_id == selected_id else ""
    print("   %2d. %-22s %s  n=%d%s"
          % (rank, short(s.variant_id), s.score, len(s.neighbours), mark))

print()
print("selected variant, per-quantity mean dissimilarity:")
for q, v in sorted(selected.per_quantity_mean.items()):
    print("   %-18s %s" % (q, v))
print("   own quantities: %s" % json.dumps(selected.own_quantities, default=str))
print("   both-zero quantities: %s" % json.dumps(selected.per_quantity_both_zero, default=str))
print("   neighbours (%d), with their own scores:" % len(selected.neighbours))
for n in selected.neighbours:
    print("      %-22s score=%s" % (short(n), scores[n].score))

runner_up = ordered[1]
print()
print("margin over runner-up %s:" % short(runner_up.variant_id))
print("   %s vs %s  ->  %s"
      % (selected.score, runner_up.score,
         Decimal(str(runner_up.score)) - Decimal(str(selected.score))))

print()
print("recorded selected_score agrees with recomputed: %s"
      % (node["selected_score"]["instability_score"] == str(selected.score)))
recorded_table = {r["variant_id"]: r["instability_score"] for r in node["neighbour_scores"]}
disagree = [v for v, s in recorded_table.items() if s != str(scores[v].score)]
print("recorded neighbour_scores rows: %d, disagreements: %d %s"
      % (len(recorded_table), len(disagree), disagree))
