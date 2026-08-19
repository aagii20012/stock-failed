"""Preflight for the SEL-2 test module: measure every number AT-I/AT-J/AT-K will assert.

The synthetic statistics below are invented for the test, so their scores cannot be looked up
anywhere. Compute them here, once, and let the test carry the measured values.
"""

import dataclasses
import json
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import g2_rotation_ra3 as rot
from stockedge100.strategies import g2_selection_v2 as sel

VARIANTS = [v.variant_id for v in rot.rotation_variants()]


def build(*, shutdown_for=(), spread=1):
    """Eighteen inputs whose counters vary with the variant index, so scores are not all equal."""
    out = []
    for index, vid in enumerate(VARIANTS, start=1):
        out.append(
            sel.SelectionInputV2(
                variant_id=vid,
                shutdown_events=1 if vid in shutdown_for else 0,
                fill_count=100 + spread * index,
                ladder_descents=10 * index,
                lockout_arms=10 * index,
                stops_filled=index % 4,
            )
        )
    return tuple(out)


inputs = build()
scores = sel.score_neighbourhood(inputs)
print("score type=%s" % type(scores[VARIANTS[0]]).__name__)
first = scores[VARIANTS[0]]
print("   score=%s (%s)" % (first.score, type(first.score).__name__))
print("   neighbours=%s" % (first.neighbours,))
print("   per_quantity_mean=%s" % {k: str(v) for k, v in first.per_quantity_mean.items()})
print("   per_quantity_both_zero=%s" % (first.per_quantity_both_zero,))
print("   own_quantities=%s" % (first.own_quantities,))

result = sel.select_representative_v2(inputs)
print()
print("select_representative_v2:")
print("   selected=%s" % result.selected)
print("   decided_at_step=%s" % result.decided_at_step)
print("   eligible=%d ineligible=%d" % (len(result.eligible), len(result.ineligible)))
print("   ranking[0:3]=%s" % (result.ranking[:3],))
print("   ranking element type=%s" % type(result.ranking[0]).__name__)
print("   scores keys=%d" % len(result.scores))
print("   selected score=%s" % scores[result.selected].score)

second = sel.select_representative_v2(build())
print("   deterministic in-process: selected=%s scores_equal=%s"
      % (second.selected == result.selected,
         all(scores[v].score == sel.score_neighbourhood(build())[v].score for v in VARIANTS)))

payload = [dataclasses.asdict(i) for i in inputs]
round_trip = tuple(sel.SelectionInputV2(**p) for p in json.loads(json.dumps(payload)))
third = sel.select_representative_v2(round_trip)
print("   round-trip: selected=%s equal=%s" % (third.selected, third.selected == result.selected))
print("   round-trip scores equal: %s"
      % all(sel.score_neighbourhood(round_trip)[v].score == scores[v].score for v in VARIANTS))
print("   round-trip breakdowns equal: %s"
      % all(sel.score_neighbourhood(round_trip)[v].per_quantity_mean
            == scores[v].per_quantity_mean for v in VARIANTS))

print()
print("shutdown screen:")
knocked = (VARIANTS[0], VARIANTS[5])
r2 = sel.select_representative_v2(build(shutdown_for=knocked))
print("   eligible=%d ineligible=%s" % (len(r2.eligible), sorted(r2.ineligible)[:2]))
print("   selected=%s step=%s" % (r2.selected, r2.decided_at_step))
print("   knocked-out variants absent from ranking: %s"
      % all(v not in [r[0] if isinstance(r, tuple) else getattr(r, "variant_id", r)
                      for r in r2.ranking] for v in knocked))

print()
print("all-shutdown -> no candidate:")
try:
    r3 = sel.select_representative_v2(build(shutdown_for=tuple(VARIANTS)))
    print("   returned selected=%r eligible=%d" % (r3.selected, len(r3.eligible)))
except Exception as exc:                                              # noqa: BLE001
    print("   raised %s: %s" % (type(exc).__name__, str(exc)[:200]))

print()
print("single eligible -> step 1:")
r4 = sel.select_representative_v2(build(shutdown_for=tuple(VARIANTS[1:])))
print("   selected=%s step=%s eligible=%d" % (r4.selected, r4.decided_at_step, len(r4.eligible)))

print()
print("partial grid to score_neighbourhood:")
try:
    sel.score_neighbourhood(inputs[:4])
    print("   accepted a partial grid")
except Exception as exc:                                              # noqa: BLE001
    print("   raised %s: %s" % (type(exc).__name__, str(exc)[:220]))

print()
print("unknown variant id:")
try:
    sel.neighbours_of("SE100-G2-S3-C3-ROTATION-RA3-L99-K9-MONTHLY")
    print("   accepted")
except Exception as exc:                                              # noqa: BLE001
    print("   raised %s: %s" % (type(exc).__name__, str(exc)[:160]))

print()
print("turnover tiebreak: two variants with identical counters")
tied = []
for index, vid in enumerate(VARIANTS, start=1):
    tied.append(sel.SelectionInputV2(variant_id=vid, shutdown_events=0, fill_count=100,
                                     ladder_descents=5, lockout_arms=5, stops_filled=1))
r5 = sel.select_representative_v2(tuple(tied))
print("   all-identical -> selected=%s step=%s score=%s"
      % (r5.selected, r5.decided_at_step, r5.scores[r5.selected].score))

tied2 = list(tied)
tied2[3] = dataclasses.replace(tied2[3], fill_count=90)
r6 = sel.select_representative_v2(tuple(tied2))
print("   one lower turnover at index 3 -> selected=%s step=%s"
      % (r6.selected, r6.decided_at_step))

print()
print("structural guard:")
import inspect
print(inspect.getsource(sel._assert_structural_enforcement))
