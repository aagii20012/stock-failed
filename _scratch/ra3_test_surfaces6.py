"""Sixth pass: the exact call surfaces the AT-A..AT-M module invokes, gathered in one place.

Everything here was established across passes 1-5 but is needed verbatim while the test file is
being typed: field names, signatures, return-dict keys, and the literal values the assertions pin.
"""

import dataclasses
import inspect
import json
import pathlib
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def show(title, text):
    print("   --- %s ---" % title)
    for line in safe(text).splitlines():
        print("   |%s" % line)


print("=" * 100)
print("1. g2_runner_ra3")
from stockedge100.strategies import g2_runner_ra3 as RUN

print("   GridRunRA3 fields = %s" % [f.name for f in dataclasses.fields(RUN.GridRunRA3)])
for name in ("run_one", "run_grid", "selection_inputs", "gate_inputs", "run_labels",
             "scenario_for_label", "load_grid_dataset", "verify_prior_attempt_modules",
             "_assert_selection_surface"):
    obj = getattr(RUN, name, None)
    print("   def %-30s %s" % (name, inspect.signature(obj) if obj else "<ABSENT>"))
print("   consts: %s" % [n for n in dir(RUN) if n.isupper()])
for n in [n for n in dir(RUN) if n.isupper()]:
    print("      %-34s %s" % (n, safe(repr(getattr(RUN, n)))[:120]))
print()
show("selection_inputs", inspect.getsource(RUN.selection_inputs))
print()
show("_assert_selection_surface", inspect.getsource(RUN._assert_selection_surface))
print()
show("verify_prior_attempt_modules", inspect.getsource(RUN.verify_prior_attempt_modules))

print()
print("=" * 100)
print("2. g2_selection_v2 call surface")
from stockedge100.strategies import g2_selection_v2 as S

for fn in (S.dissimilarity, S.neighbours_of, S.score_neighbourhood, S.select_representative_v2,
           S.check_neighbourhood_structure, S.check_seal_agreement, S.load_selection_rule):
    print("   def %-30s %s" % (fn.__name__, inspect.signature(fn)))
print("   NeighbourhoodScore fields = %s" % [f.name for f in dataclasses.fields(S.NeighbourhoodScore)])
print("   SelectionResultV2 fields  = %s" % [f.name for f in dataclasses.fields(S.SelectionResultV2)])
print("   QUANTITIES = %s" % (S.QUANTITIES,))
print("   SELECTION_V2_FIELD_NAMES = %s" % (S.SELECTION_V2_FIELD_NAMES,))
print("   FORBIDDEN_FIELD_SUBSTRINGS = %s" % (S.FORBIDDEN_FIELD_SUBSTRINGS,))
print("   EXPECTED_STEP_CRITERIA = %s" % (S.EXPECTED_STEP_CRITERIA,))
print("   SCORE_DECIMALS=%s SELECTION_RULE_ID=%s" % (S.SCORE_DECIMALS, S.SELECTION_RULE_ID))
print("   check_neighbourhood_structure() ->")
for k, v in S.check_neighbourhood_structure().items():
    print("      %-34s %s" % (k, safe(json.dumps(v, ensure_ascii=False, default=str))[:200]))
print()
show("score_neighbourhood", inspect.getsource(S.score_neighbourhood))
print()
show("select_representative_v2", inspect.getsource(S.select_representative_v2))
print()
show("_assert_structural_enforcement", inspect.getsource(S._assert_structural_enforcement))

print()
print("=" * 100)
print("3. g2_engine_ra3 checkers and constants")
from stockedge100.backtest import g2_engine_ra3 as E3

print("   __all__ = %s" % getattr(E3, "__all__", None))
for n in ("RA3_BAND_COUNT", "RA3_SHALLOWEST_ENGAGEMENT", "DELETED_RA2_TIER",
          "RISK_DERIVED_ATTRIBUTES", "PROTOCOL_ID", "STRATEGY_ID"):
    print("   %-28s %s" % (n, safe(repr(getattr(E3, n, "<ABSENT>")))[:160]))
print("   def attributes_derived_from_risk %s" % inspect.signature(E3.attributes_derived_from_risk))
arch = E3.load_risk_architecture_ra3()
print("   arch bands: %s" % [(b.band, str(b.dd_from), str(b.dd_to_exclusive), str(b.scalar))
                             for b in arch.bands])
print("   exposure_ceiling=%s stop_fraction=%s lockout_sessions=%s vol_target=%s"
      % (arch.exposure_ceiling, arch.stop_fraction, arch.lockout_sessions,
         getattr(arch, "vol_target", "<none>")))
print("   check_generation_1_provenance ->")
for k, v in E3.check_generation_1_provenance(arch).items():
    print("      %-34s %s" % (k, safe(json.dumps(v, ensure_ascii=False, default=str))[:180]))
print("   check_single_difference_from_ra2 ->")
for k, v in E3.check_single_difference_from_ra2(arch).items():
    print("      %-34s %s" % (k, safe(json.dumps(v, ensure_ascii=False, default=str))[:180]))
print()
show("RotationEngineRA3.__init__", inspect.getsource(E3.RotationEngineRA3.__init__))
print()
show("attributes_derived_from_risk", inspect.getsource(E3.attributes_derived_from_risk))

print()
print("=" * 100)
print("4. g2_gate_ra3 alias guard surface")
from stockedge100.strategies import g2_gate_ra3 as G

print("   PROSE_ALIASES (%d):" % len(G.PROSE_ALIASES))
for entry in G.PROSE_ALIASES:
    print("      %s" % safe(repr(entry)))
for n in ("load_criteria_ra3", "check_prose_alias_adapter", "_check_prose_renames_are_as_declared",
          "_pointers_dropped_since_attempt_2", "_keys_the_frozen_evaluators_read",
          "check_thresholds_against_seal", "expected_neighbour_count", "prior_attempt_tokens"):
    obj = getattr(G, n, None)
    print("   def %-40s %s" % (n, inspect.signature(obj) if obj else "<ABSENT>"))
print()
show("_check_prose_renames_are_as_declared",
     inspect.getsource(G._check_prose_renames_are_as_declared))
print()
show("check_prose_alias_adapter", inspect.getsource(G.check_prose_alias_adapter))
print("   check_prose_alias_adapter() ->")
for k, v in G.check_prose_alias_adapter().items():
    print("      %-34s %s" % (k, safe(json.dumps(v, ensure_ascii=False, default=str))[:180]))
print("   prior_attempt_tokens() -> %s" % safe(G.prior_attempt_tokens()))
print("   expected_neighbour_count sig ok")

print()
print("=" * 100)
print("5. g2_rotation_ra3 helpers the fixtures use")
from stockedge100.strategies import g2_rotation_ra3 as R

for n in ("rotation_variants", "variant_by_id", "rotation_cost_model", "build_candidate",
          "eligible_universe"):
    obj = getattr(R, n, None)
    print("   def %-24s %s" % (n, inspect.signature(obj) if obj else "<ABSENT>"))
print("   RotationCandidateRA3 bases: %s" % [b.__name__ for b in R.RotationCandidateRA3.__bases__])
print("   variant fields: %s" % [f.name for f in dataclasses.fields(R.rotation_variants()[0])])
print("   18 ids:")
for v in R.rotation_variants():
    print("      %s  L%s K%s %s w=%s" % (v.variant_id, v.lookback_months, v.top_k,
                                         v.rebalance_frequency, v.target_weight))
