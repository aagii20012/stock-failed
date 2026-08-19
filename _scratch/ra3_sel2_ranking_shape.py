"""What does the ranking look like when the shutdown screen knocks variants out?"""

import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import g2_rotation_ra3 as rot
from stockedge100.strategies import g2_selection_v2 as sel

VARIANTS = rot.rotation_variants()
IDS = [v.variant_id for v in VARIANTS]
PREFIX = "SE100-G2-S3-C3-ROTATION-RA3-"


def gradient(shutdown_for=()):
    return tuple(
        sel.SelectionInputV2(
            variant_id=v.variant_id,
            shutdown_events=1 if v.variant_id in shutdown_for else 0,
            fill_count=100 + i,
            ladder_descents=10 * i,
            lockout_arms=10 * i,
            stops_filled=i % 4,
        )
        for i, v in enumerate(VARIANTS, start=1)
    )


knocked = (PREFIX + "L03-K1-MONTHLY", PREFIX + "L03-K3-QUARTERLY")
r = sel.select_representative_v2(gradient(knocked))
print("selected=%s step=%s eligible=%d ineligible=%d ranking=%d"
      % (r.selected, r.decided_at_step, len(r.eligible), len(r.ineligible), len(r.ranking)))
print("ineligible type=%s  eligible type=%s" % (type(r.ineligible).__name__,
                                                type(r.eligible).__name__))
print()
print("ranking rows in order:")
for row in r.ranking:
    print("   elig=%-5s score=%s fill=%-4s shut=%s %s"
          % (row["eligible"], row["instability_score"], row["fill_count"],
             row["shutdown_events"], row["variant_id"].replace(PREFIX, "")))

print()
print("all eligible rows precede all ineligible rows: %s"
      % ([row["eligible"] for row in r.ranking]
         == sorted([row["eligible"] for row in r.ranking], reverse=True)))
keys = [(not row["eligible"], Decimal(row["instability_score"]), row["fill_count"],
         row["variant_id"]) for row in r.ranking]
print("sorted by (not eligible, score, fill, id): %s" % (keys == sorted(keys)))
keys2 = [(Decimal(row["instability_score"]), row["fill_count"], row["variant_id"])
         for row in r.ranking]
print("sorted by (score, fill, id) alone: %s" % (keys2 == sorted(keys2)))
print("ranking[0] is selected: %s" % (r.ranking[0]["variant_id"] == r.selected))

print()
print("no-shutdown control: ranking length=%d, all eligible=%s"
      % (len(sel.select_representative_v2(gradient()).ranking),
         all(row["eligible"] for row in sel.select_representative_v2(gradient()).ranking)))

print()
r_all = sel.select_representative_v2(gradient(tuple(IDS)))
print("all-shutdown: selected=%r ranking=%d eligible=%d"
      % (r_all.selected, len(r_all.ranking), len(r_all.eligible)))

print()
r_one = sel.select_representative_v2(gradient(tuple(IDS[1:])))
print("one survivor: selected=%s step=%s ranking[0]=%s"
      % (r_one.selected.replace(PREFIX, ""), r_one.decided_at_step,
         r_one.ranking[0]["variant_id"].replace(PREFIX, "")))
