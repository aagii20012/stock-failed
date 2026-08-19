"""Can step 3 (lowest turnover) be reached synthetically, and is the ranking sorted as declared?"""

import dataclasses
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import g2_rotation_ra3 as rot
from stockedge100.strategies import g2_selection_v2 as sel

VARIANTS = rot.rotation_variants()
IDS = [v.variant_id for v in VARIANTS]
LOOKBACKS = [3, 6, 12]
KS = [1, 2, 3]
FREQS = ["MONTHLY", "QUARTERLY"]


def parity(v):
    return (LOOKBACKS.index(v.lookback_months) + KS.index(v.top_k)
            + FREQS.index(v.frequency)) % 2


def mk(fill_of):
    return tuple(
        sel.SelectionInputV2(variant_id=v.variant_id, shutdown_events=0,
                             fill_count=fill_of(v), ladder_descents=7,
                             lockout_arms=7, stops_filled=2)
        for v in VARIANTS
    )


print("checkerboard 100/120:")
inputs = mk(lambda v: 100 if parity(v) == 0 else 120)
scores = sel.score_neighbourhood(inputs)
distinct = sorted({str(s.score) for s in scores.values()})
print("   distinct scores=%s" % distinct)
res = sel.select_representative_v2(inputs)
print("   selected=%s step=%s fill=%s"
      % (res.selected, res.decided_at_step,
         [i.fill_count for i in inputs if i.variant_id == res.selected]))

print()
print("checkerboard, then one parity-0 variant lowered to 99:")
target = next(v for v in VARIANTS if parity(v) == 0)
inputs2 = mk(lambda v: (99 if v.variant_id == target.variant_id
                        else (100 if parity(v) == 0 else 120)))
scores2 = sel.score_neighbourhood(inputs2)
print("   distinct scores=%d" % len({str(s.score) for s in scores2.values()}))
res2 = sel.select_representative_v2(inputs2)
print("   selected=%s step=%s" % (res2.selected, res2.decided_at_step))

print()
print("ranking sort key check on the gradient fixture:")
grad = tuple(
    sel.SelectionInputV2(variant_id=v.variant_id, shutdown_events=0,
                         fill_count=100 + index, ladder_descents=10 * index,
                         lockout_arms=10 * index, stops_filled=index % 4)
    for index, v in enumerate(VARIANTS, start=1)
)
res3 = sel.select_representative_v2(grad)
keys = [(Decimal(row["instability_score"]), row["fill_count"], row["variant_id"])
        for row in res3.ranking]
print("   ranking sorted by (score, fill_count, variant_id): %s" % (keys == sorted(keys)))
print("   ranking row keys: %s" % sorted(res3.ranking[0]))
print("   first row = selected: %s" % (res3.ranking[0]["variant_id"] == res3.selected))

print()
print("all-identical fixture ranking is lexicographic:")
same = mk(lambda v: 100)
res4 = sel.select_representative_v2(same)
ids = [row["variant_id"] for row in res4.ranking]
print("   lexicographic: %s  step=%s selected=%s" % (ids == sorted(ids), res4.decided_at_step,
                                                     res4.selected))
print("   every score zero: %s"
      % all(row["instability_score"] == "0.000000000" for row in res4.ranking))
print("   sample score repr: %r" % res4.ranking[0]["instability_score"])
print("   both_zero counts on the all-identical fixture: %s"
      % res4.scores[res4.selected].per_quantity_both_zero)

print()
print("zero-everything fixture (both-zero ambiguity, G2A3-CONFLICT-32):")
zeros = tuple(sel.SelectionInputV2(variant_id=v.variant_id, shutdown_events=0, fill_count=0,
                                   ladder_descents=0, lockout_arms=0, stops_filled=0)
              for v in VARIANTS)
z = sel.score_neighbourhood(zeros)
one = z[IDS[0]]
print("   score=%s both_zero=%s" % (one.score, one.per_quantity_both_zero))
