"""Exercise every public entry point of g2_selection_v2 before any test file depends on it.

The interesting checks are the ones the module cannot make about itself: the neighbour sets for one
variant of each 3/4/5 class written out by hand and compared, the refusal paths, determinism across a
clean recomputation, and the G2A3-CONFLICT-32 both-zero disclosure actually appearing in the output.

Console is cp1252: launder every string that came off a UTF-8 seal.
"""

import sys

sys.path.insert(0, "d:/Product/stock-trade-alpaca/stockedge100/src")

from decimal import Decimal, localcontext

from stockedge100.backtest.costs import ENGINE_CONTEXT
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.strategies import g2_selection_v2 as sel
from stockedge100.strategies.g2_rotation_ra3 import rotation_variants


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


failures = []


def check(label, condition, detail=""):
    mark = "ok  " if condition else "FAIL"
    if not condition:
        failures.append(label)
    print("  [%s] %-58s %s" % (mark, label, safe(detail)[:88]))


def refuses(label, fn, expect=ConfigViolation):
    try:
        fn()
    except Exception as exc:
        check(label, isinstance(exc, expect), "%s: %s" % (type(exc).__name__, safe(exc)[:60]))
        return
    check(label, False, "no raise")


P = "SE100-G2-S3-C3-ROTATION-RA3"

print("=" * 100)
print("import-time structural enforcement (already ran; re-run explicitly)")
sel._assert_structural_enforcement()
check("field tuple as declared", sel.SELECTION_V2_FIELD_NAMES == (
    "variant_id", "shutdown_events", "fill_count", "ladder_descents", "lockout_arms", "stops_filled"))
check("six fields, no more", len(sel.SELECTION_V2_FIELD_NAMES) == 6)
check("no field names a performance quantity", all(
    banned not in name.lower()
    for name in sel.SELECTION_V2_FIELD_NAMES
    for banned in sel.FORBIDDEN_FIELD_SUBSTRINGS))
check("'shutdown' survives the 'drawdown' ban", "drawdown" not in "shutdown_events")

print()
print("=" * 100)
print("check_seal_agreement() -- the module's constants against the sealed node")
agreement = sel.check_seal_agreement()
check("rule id", agreement["rule_id"] == "SE100-G2-SEL-2", agreement["rule_id"])
check("four steps in sealed order", agreement["steps"] == {
    1: "zero_research_shutdown_events",
    2: "lowest_neighbourhood_instability_score",
    3: "lowest_turnover",
    4: "lexicographic_variant_id"}, agreement["steps"])
check("four quantities", agreement["quantities"] == list(sel.QUANTITIES), agreement["quantities"])
check("dissimilarity formula", agreement["dissimilarity"].replace(" ", "") == "abs(a-b)/max(abs(a),abs(b),1)")
check("nine decimal places", agreement["score_decimals"] == 9)
print("   no-candidate verdict:  %s" % safe(agreement["no_candidate_verdict"]))
print("   second-fail verdict:   %s" % safe(agreement["second_fail_verdict"]))
check("both fail routes share one token",
      agreement["no_candidate_verdict"] == agreement["second_fail_verdict"])

print()
print("=" * 100)
print("check_neighbourhood_structure() -- 3/4/5 counts, 8/8/2 partition, symmetry")
structure = sel.check_neighbourhood_structure()
check("eighteen variants", structure["variant_count"] == 18)
check("partition is 8/8/2", structure["partition"] == {3: 8, 4: 8, 5: 2}, structure["partition"])
check("symmetric", structure["symmetric"] is True)
check("directed pairs = 8*3+8*4+2*5", structure["total_directed_pairs"] == 8 * 3 + 8 * 4 + 2 * 5,
      structure["total_directed_pairs"])
check("directed pair count is even (symmetry implies it)", structure["total_directed_pairs"] % 2 == 0)
print("   sealed prose: %s" % safe(structure["sealed_partition_prose"])[:150])

print()
print("=" * 100)
print("neighbour sets written out by hand -- one variant of each 3/4/5 class")
HAND = {
    # corner of both ordered axes: lookback at an end, k at an end -> 1 + 1 + 1
    "%s-L03-K1-MONTHLY" % P: [
        "%s-L03-K1-QUARTERLY" % P, "%s-L03-K2-MONTHLY" % P, "%s-L06-K1-MONTHLY" % P],
    # middle of one ordered axis only -> 2 + 1 + 1
    "%s-L06-K1-MONTHLY" % P: [
        "%s-L03-K1-MONTHLY" % P, "%s-L06-K1-QUARTERLY" % P, "%s-L06-K2-MONTHLY" % P,
        "%s-L12-K1-MONTHLY" % P],
    # middle of both ordered axes -> 2 + 2 + 1
    "%s-L06-K2-QUARTERLY" % P: [
        "%s-L03-K2-QUARTERLY" % P, "%s-L06-K1-QUARTERLY" % P, "%s-L06-K2-MONTHLY" % P,
        "%s-L06-K3-QUARTERLY" % P, "%s-L12-K2-QUARTERLY" % P],
}
for variant_id, expected in HAND.items():
    actual = list(sel.neighbours_of(variant_id))
    check("%s -> %d neighbours" % (variant_id.replace(P + "-", ""), len(expected)),
          actual == sorted(expected),
          "" if actual == sorted(expected) else "got %s" % [a.replace(P + "-", "") for a in actual])
    for n in actual:
        print("        %s" % n.replace(P + "-", ""))

refuses("neighbours_of refuses an unknown id", lambda: sel.neighbours_of("%s-L99-K9-DAILY" % P))

print()
print("=" * 100)
print("dissimilarity() -- abs(a-b)/max(abs(a),abs(b),1)")
# The expectations must be evaluated under ENGINE_CONTEXT too.  Python's default context is 28
# significant digits and the sealed one is 34, so a bare `Decimal(4) / Decimal(7)` here disagrees with
# the module in the last six digits -- a script defect that reads exactly like a module defect.
with localcontext(ENGINE_CONTEXT):
    CASES = [((0, 0), Decimal(0)), ((5, 5), Decimal(0)), ((0, 5), Decimal(1)), ((5, 0), Decimal(1)),
             ((1, 0), Decimal(1)), ((3, 7), Decimal(4) / Decimal(7)),
             ((100, 90), Decimal(10) / Decimal(100))]
for (a, b), expected in CASES:
    got = sel.dissimilarity(a, b)
    check("d(%d,%d)" % (a, b), got == Decimal(expected), "%s" % got)
check("both-zero and identical-nonzero are indistinguishable (CONFLICT-32)",
      sel.dissimilarity(0, 0) == sel.dissimilarity(7, 7) == Decimal(0))

print()
print("=" * 100)
print("score_neighbourhood() on a synthetic grid")
variants = rotation_variants()
# Deterministic, index-derived counters.  stops_filled is zero everywhere on purpose, so the
# both-zero disclosure has something to disclose.
inputs = [
    sel.SelectionInputV2(
        variant_id=v.variant_id,
        shutdown_events=0,
        fill_count=100 + 7 * v.index,
        ladder_descents=3 * (v.index % 5),
        lockout_arms=v.index % 3,
        stops_filled=0,
    )
    for v in variants
]
scores = sel.score_neighbourhood(inputs)
check("eighteen scores", len(scores) == 18)
check("every score is a Decimal at nine dp",
      all(-s.score.as_tuple().exponent == 9 for s in scores.values()))
check("every score in [0, 1]", all(Decimal(0) <= s.score <= Decimal(1) for s in scores.values()))
check("stops_filled mean is zero everywhere",
      all(s.per_quantity_mean["stops_filled"] == 0 for s in scores.values()))
check("stops_filled both-zero count equals the neighbour count everywhere",
      all(s.per_quantity_both_zero["stops_filled"] == len(s.neighbours) for s in scores.values()))
check("fill_count never both-zero here",
      all(s.per_quantity_both_zero["fill_count"] == 0 for s in scores.values()))
sample = scores["%s-L06-K2-QUARTERLY" % P]
print("   sample %s" % sample.variant_id.replace(P + "-", ""))
for key, value in sorted(sample.to_json().items()):
    print("      %-38s %s" % (key, safe(value))[:100])

print()
print("=" * 100)
print("determinism -- a clean recomputation from freshly built inputs")
fresh = [sel.SelectionInputV2(i.variant_id, i.shutdown_events, i.fill_count, i.ladder_descents,
                              i.lockout_arms, i.stops_filled) for i in inputs]
again = sel.score_neighbourhood(fresh)
check("identical scores", {k: v.score for k, v in scores.items()} == {k: v.score for k, v in again.items()})
check("identical per-quantity means",
      all(scores[k].per_quantity_mean == again[k].per_quantity_mean for k in scores))
check("order-independent", {k: v.score for k, v in sel.score_neighbourhood(list(reversed(fresh))).items()}
      == {k: v.score for k, v in scores.items()})

print()
print("=" * 100)
print("select_representative_v2() -- the four steps")
result = sel.select_representative_v2(inputs)
check("all eighteen eligible here", len(result.eligible) == 18)
check("a representative was selected", result.selected is not None, result.selected)
check("selected is eligible", result.selected in result.eligible)
check("selected has the lowest score among eligible",
      scores[result.selected].score == min(scores[v].score for v in result.eligible),
      "%s @ %s" % (result.selected.replace(P + "-", ""), scores[result.selected].score))
check("decided at step 2 or 3", result.decided_at_step in (2, 3), result.decided_at_step)
check("ranking covers all eighteen", len(result.ranking) == 18)
check("ranking is ordered by score", [Decimal(r["instability_score"]) for r in result.ranking]
      == sorted(Decimal(r["instability_score"]) for r in result.ranking))
print("   top five:")
for row in result.ranking[:5]:
    print("      %-26s score=%s fills=%d" % (row["variant_id"].replace(P + "-", ""),
                                             row["instability_score"], row["fill_count"]))

print()
print("=" * 100)
print("step 1 -- the eligibility screen actually eliminates")
mixed = [sel.SelectionInputV2(i.variant_id, 0 if n >= 3 else 2, i.fill_count, i.ladder_descents,
                              i.lockout_arms, i.stops_filled) for n, i in enumerate(inputs)]
partial = sel.select_representative_v2(mixed)
check("three variants eliminated", len(partial.ineligible) == 3, sorted(
    v.replace(P + "-", "") for v in partial.ineligible))
check("selected is not among the eliminated", partial.selected not in partial.ineligible)
check("ineligible variants still scored", all(v in partial.scores for v in partial.ineligible))
check("an ineligible neighbour still counts toward a score",
      partial.scores[inputs[0].variant_id].score == scores[inputs[0].variant_id].score,
      "scores unchanged by eligibility, as sealed")

none_eligible = [sel.SelectionInputV2(i.variant_id, 1, i.fill_count, i.ladder_descents,
                                      i.lockout_arms, i.stops_filled) for i in inputs]
empty = sel.select_representative_v2(none_eligible)
check("no eligible -> no representative", empty.selected is None)
check("no eligible -> decided at step 1", empty.decided_at_step == 1)
check("no eligible -> all eighteen ineligible", len(empty.ineligible) == 18)

print()
print("=" * 100)
print("refusal paths")
refuses("float in a counter slot",
        lambda: sel.SelectionInputV2("%s-L03-K1-MONTHLY" % P, 0, 0.0421, 0, 0, 0))
refuses("Decimal in a counter slot",
        lambda: sel.SelectionInputV2("%s-L03-K1-MONTHLY" % P, 0, Decimal("12"), 0, 0, 0))
refuses("bool in a counter slot",
        lambda: sel.SelectionInputV2("%s-L03-K1-MONTHLY" % P, 0, True, 0, 0, 0))
refuses("negative counter",
        lambda: sel.SelectionInputV2("%s-L03-K1-MONTHLY" % P, 0, -1, 0, 0, 0))
refuses("empty variant id", lambda: sel.SelectionInputV2("", 0, 0, 0, 0, 0))
refuses("frozen: cannot reassign a counter",
        lambda: setattr(inputs[0], "fill_count", 0), Exception)
refuses("duck-typed input rejected", lambda: sel.score_neighbourhood(
    [type("Fake", (), {"variant_id": v.variant_id, "shutdown_events": 0, "fill_count": 1,
                       "ladder_descents": 0, "lockout_arms": 0, "stops_filled": 0,
                       "quantity": lambda self, n: 1})() for v in variants]))
refuses("partial grid rejected", lambda: sel.score_neighbourhood(inputs[:17]))
refuses("duplicate variant rejected", lambda: sel.score_neighbourhood(inputs + [inputs[0]]))
refuses("unknown variant rejected", lambda: sel.score_neighbourhood(
    inputs[:17] + [sel.SelectionInputV2("%s-L99-K9-DAILY" % P, 0, 1, 0, 0, 0)]))
refuses("quantity() refuses an unscored name", lambda: inputs[0].quantity("shutdown_events"))

print()
print("=" * 100)
print("FAILURES: %d" % len(failures))
for label in failures:
    print("   %s" % label)
sys.exit(1 if failures else 0)
