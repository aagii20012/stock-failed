"""Exercise every path in g2_gate_ra3.py that does not need a BacktestResult.

The seal checks, the plan, the token withholding and the neighbour relation all run without a single
variant having been backtested, so they can be wrong for a whole grid run before anything notices.
Run them first, and hand-verify the neighbour counts against the 3/4/5 partition rather than trusting
the module's own assertion -- a check that only confirms what you expect confirms nothing.

The 1507-char disclosure and the sealed prose are never printed: cp1252 kills the process on U+2014.
Digests and booleans only.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import g2_gate_ra3 as G
from stockedge100.strategies import g2_selection_v2 as S
from stockedge100.strategies import g2_rotation_ra3 as R
from stockedge100.strategies import g2_gate_ra1 as A2


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


print("=" * 100)
print("1. load_criteria_ra3 -- every seal check runs inside it")
criteria = G.load_criteria_ra3()
print("   artifact_id                %s" % criteria["artifact_id"])
print("   generation/stage/attempt   %s/%s/%s"
      % (criteria["generation"], criteria["stage"], criteria["attempt"]))
print("   conditions                 %s" % [c["id"] for c in criteria["conditions"]])
print("   three counterparts recomputed, thresholds sealed, axes agree, tokens checked: OK")

print()
print("=" * 100)
print("2. prior_attempt_tokens -- four withheld, read from the two closed files")
withheld = G.prior_attempt_tokens()
for token in withheld:
    print("   %s" % token)
d = criteria["verdict_token_derivation"]
print("   count                      %d" % len(withheld))
print("   RA3 pass_token             %s" % d["pass_token"])
print("   RA3 fail_token             %s" % d["fail_token"])
print("   collision with withheld    %s" % bool({d["pass_token"], d["fail_token"]} & set(withheld)))

print()
print("=" * 100)
print("3. check_prose_alias_adapter -- G2A3-CONFLICT-40")
ev = G.check_prose_alias_adapter(criteria)
for key in ("conflict_id", "pointers_added", "pointers_changed", "pointers_removed",
            "sealed_object_unmutated", "conditions_using_the_adapter",
            "conditions_using_the_seal_directly", "affects_a_predicate"):
    print("   %-36s %s" % (key, ev[key]))
for alias in ev["aliases"]:
    print("   alias %-8s %-24s <- %-24s identical=%s sha256[:16]=%s"
          % (alias["condition"], alias["alias_supplied"], alias["sealed_field"],
             alias["values_identical"], alias["value_sha256_prefix"]))
    print("          read_by %s" % alias["read_by"])

print()
print("   negative control 1: a THIRD aliased pointer must be refused by the diff assertion.")
print("   (Tampering with the *source* field is not a control -- the adapter would faithfully copy")
print("    the tampered value, which is correct behaviour; the criteria file's own checksum record")
print("    is what protects the source. The live question is whether the diff can see an extra key.)")
import copy as _copy
print("   dropped between CFG-3104 and CFG-3106: %d pointers"
      % len(G._pointers_dropped_since_attempt_2()))
for cid, path in sorted(G._pointers_dropped_since_attempt_2()):
    print("      %-8s %s" % (cid, ".".join(path)))
print("   of those, read by a frozen evaluator: %s"
      % sorted(("%s.%s" % (c, ".".join(p))) for c, p in G._derived_alias_pointers()))
print("   sealed keys recovered from g2_gate_ra1.py's AST: %d"
      % len(G._keys_the_frozen_evaluators_read()))
saved = G.PROSE_ALIASES
G.PROSE_ALIASES = saved + (("S3-C1", (), "attempt_2_status", "attempt_3_status"),)
try:
    G._check_prose_renames_are_as_declared(criteria)
    print("   *** NOT REFUSED -- the alias table is unchecked ***")
except Exception as exc:
    print("   refused: %s" % safe(exc)[-150:])
finally:
    G.PROSE_ALIASES = saved
print("   PROSE_ALIASES restored: %s" % (G.PROSE_ALIASES == saved))

print("   negative control 2: criteria carrying BOTH names must be refused at load")
both = _copy.deepcopy(criteria)
for c in both["conditions"]:
    if c["id"] == "S3-C3":
        c["attempt_2_note"] = "leftover from Attempt 2"
try:
    G._check_prose_renames_are_as_declared(both)
    print("   *** NOT REFUSED ***")
except Exception as exc:
    print("   refused: %s" % safe(exc)[:110])

print()
print("=" * 100)
print("4. build_plan_ra3")
plan = G.build_plan_ra3()
for key, value in sorted(plan.to_json().items()):
    if key == "declared_universe":
        value = "%d symbols" % len(value)
    print("   %-34s %s" % (key, safe(value)[:96]))

print()
print("=" * 100)
print("5. neighbour relation -- set from CFG-3105 via SEL-2, count from CFG-3106")
variants = R.rotation_variants()
print("   variants: %d" % len(variants))
buckets = {}
for v in variants:
    n = G.neighbours_of_ra3(v, criteria)
    buckets.setdefault(len(n), []).append(v.variant_id)
    # the count rule is Attempt 2's, applied to an RA3 variant -- duck compatibility, measured
    assert len(n) == A2.expected_neighbour_count(v, criteria), v.variant_id
print("   count partition (sealed 3/4/5): %s"
      % {k: len(v) for k, v in sorted(buckets.items())})
for size in sorted(buckets):
    print("      %d neighbours: %d variants" % (size, len(buckets[size])))

print()
print("   hand-verify one of each class, listing the actual neighbour ids:")
for size in sorted(buckets):
    vid = sorted(buckets[size])[0]
    v = R.variant_by_id(vid)
    n = G.neighbours_of_ra3(v, criteria)
    print("      %s  (L%s k%s %s)" % (vid, v.lookback_months, v.top_k, v.frequency))
    for m in n:
        print("         -> %-52s L%-3s k%-3s %s" % (m.variant_id, m.lookback_months, m.top_k, m.frequency))

print()
print("   symmetry: a in neighbours(b) iff b in neighbours(a)")
bad = []
for v in variants:
    for m in G.neighbours_of_ra3(v, criteria):
        back = [x.variant_id for x in G.neighbours_of_ra3(m, criteria)]
        if v.variant_id not in back:
            bad.append((v.variant_id, m.variant_id))
print("   asymmetric pairs: %d" % len(bad))

print()
print("   agreement with SEL-2's own neighbour set (same function, so must be identical):")
mismatch = 0
for v in variants:
    a = tuple(sorted(m.variant_id for m in G.neighbours_of_ra3(v, criteria)))
    b = tuple(sorted(S.neighbours_of(v.variant_id)))
    if a != b:
        mismatch += 1
print("   shared=%d mismatch=%d" % (len(variants), mismatch))

print()
print("=" * 100)
print("6. gate.py::condition_3 is unreachable from the RA3 path")
import inspect
src = inspect.getsource(G)
print("   'condition_3' imported from gate.py by g2_gate_ra3: %s"
      % ("condition_3," in src.split("from stockedge100.strategies.gate import")[1].split(")")[0]))
print("   evaluate_representative_ra3 calls condition_3_ra3:  %s" % ("condition_3_ra3(" in src))

print()
print("=" * 100)
print("7. S3-C7 measurement keys condition_7_ra3 dereferences")
spec = [c for c in criteria["conditions"] if c["id"] == "S3-C7"][0]
for key in ("neighbour_definition", "neighbour_count", "neighbour_count_conflict",
            "shared_with_selection", "one_step_note", "what_is_read", "no_new_runs",
            "risk_constants_have_no_neighbours", "axis_orderings"):
    print("   measurement.%-36s %s" % (key, "present" if key in spec["measurement"] else "*** ABSENT ***"))
for key in ("selection_prohibition", "not_evaluable_treatment", "id", "required_verbatim"):
    print("   %-48s %s" % (key, "present" if key in spec else "*** ABSENT ***"))

print()
print("=" * 100)
print("8. stage_verdict_ra3 -- both routes, no BacktestResult needed")
fail_no_rep = G.stage_verdict_ra3([], criteria, representative_exists=False,
                                  selection_note="every variant recorded a shutdown")
print("   route=%-38s token=%s" % (fail_no_rep["route"], fail_no_rep["verdict_token"]))
fake = {"variant_id": "SE100-G2-S3-C3-ROTATION-RA3-L12-K1-QUARTERLY", "admitted": False}
fail_rep = G.stage_verdict_ra3([fake], criteria, representative_exists=True, selection_note="n/a")
print("   route=%-38s token=%s" % (fail_rep["route"], fail_rep["verdict_token"]))
fake_pass = dict(fake, admitted=True)
ok = G.stage_verdict_ra3([fake_pass], criteria, representative_exists=True, selection_note="n/a")
print("   route=%-38s token=%s" % (ok["route"], ok["verdict_token"]))
print("   selection_rule_id           %s" % ok["selection_rule_id"])
print("   withheld carried into record %d" % len(ok["prior_attempt_tokens_withheld"]))
for label, kwargs in (
    ("admitted with no representative", dict(candidate_results=[fake_pass], representative_exists=False)),
    ("representative with no results", dict(candidate_results=[], representative_exists=True)),
    ("two candidates evaluated", dict(candidate_results=[fake, fake], representative_exists=True)),
):
    try:
        G.stage_verdict_ra3(criteria=criteria, selection_note="n/a", **kwargs)
        print("   *** %s NOT REFUSED ***" % label)
    except Exception as exc:
        print("   refused %-34s %s" % (label + ":", safe(exc)[:70]))

print()
print("=" * 100)
print("SMOKE COMPLETE")
