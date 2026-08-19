"""Second surface pass: the exact source text AT-I/AT-J/AT-L/AT-M re-exec or assert against.

Pass one gave names and signatures. It did not give the SelectionInputV2 body verbatim (the regex
stopped at the docstring's blank line) nor the import-time assertion, and both are load-bearing:
AT-I's negative control reads the module source, substitutes one extra field into the dataclass
body, and re-execs, so the substring it searches for must match byte for byte.
"""

import dataclasses
import inspect
import json
import pathlib
import re
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
print("1. g2_selection_v2 source: the dataclass, the assertion, the scorer")
from stockedge100.strategies import g2_selection_v2 as S

src = pathlib.Path(S.__file__).read_text("utf-8")
print("   file=%s  lines=%d" % (S.__file__, src.count("\n")))

m = re.search(r"@dataclass\(frozen=True\)\nclass SelectionInputV2:.*?(?=\n@|\n(?:def|class) )", src, re.S)
show("SelectionInputV2 block (decorator through last field)", m.group(0) if m else "<NOT FOUND>")

print()
print("   --- every line mentioning SELECTION_V2_FIELD_NAMES ---")
for i, line in enumerate(src.splitlines(), 1):
    if "SELECTION_V2_FIELD_NAMES" in line:
        print("   %4d |%s" % (i, safe(line)))

print()
show("_assert_structural_enforcement", inspect.getsource(S._assert_structural_enforcement))

print()
print("   --- call sites of _assert_structural_enforcement (import-time?) ---")
for i, line in enumerate(src.splitlines(), 1):
    if "_assert_structural_enforcement" in line:
        print("   %4d |%s" % (i, safe(line)))

print()
for fn in (S.dissimilarity, S.neighbours_of, S.score_neighbourhood,
           S.select_representative_v2, S.check_neighbourhood_structure, S.check_seal_agreement):
    print("   def %-30s %s" % (fn.__name__, inspect.signature(fn)))

print()
show("neighbours_of", inspect.getsource(S.neighbours_of))

print()
print("   FORBIDDEN_FIELD_SUBSTRINGS = %s" % (S.FORBIDDEN_FIELD_SUBSTRINGS,))
print("   SELECTION_V2_FIELD_NAMES   = %s" % (S.SELECTION_V2_FIELD_NAMES,))
print("   EXPECTED_STEP_CRITERIA     = %s" % (S.EXPECTED_STEP_CRITERIA,))
print("   NeighbourhoodScore fields  = %s" % [f.name for f in dataclasses.fields(S.NeighbourhoodScore)])
print("   SelectionResultV2 fields   = %s" % [f.name for f in dataclasses.fields(S.SelectionResultV2)])
struct = S.check_neighbourhood_structure()
print("   check_neighbourhood_structure() ->")
for k, v in struct.items():
    print("      %-32s %s" % (k, safe(json.dumps(v, ensure_ascii=False, default=str))[:180]))

print()
print("=" * 100)
print("2. g2_engine_ra3 source: __init__, risk_summary, the three checkers, the constants")
from stockedge100.backtest import g2_engine_ra3 as E

for name in ("RA3_BAND_COUNT", "RA3_SHALLOWEST_ENGAGEMENT", "DELETED_RA2_TIER",
             "RISK_DERIVED_ATTRIBUTES", "PROTOCOL_ID", "STRATEGY_ID",
             "GENERATION_1_PROTOCOL_PATH"):
    print("   %-28s %s" % (name, safe(repr(getattr(E, name, "<ABSENT>")))[:200]))

print()
show("RotationEngineRA3.__init__", inspect.getsource(E.RotationEngineRA3.__init__))
print()
show("RotationEngineRA3.risk_summary", inspect.getsource(E.RotationEngineRA3.risk_summary))
print()
show("attributes_derived_from_risk", inspect.getsource(E.attributes_derived_from_risk))
print()
print("   attributes_derived_from_risk() = %s" % sorted(E.attributes_derived_from_risk()))
print()
show("check_generation_1_provenance", inspect.getsource(E.check_generation_1_provenance))
print()
show("check_single_difference_from_ra2", inspect.getsource(E.check_single_difference_from_ra2))

arch = E.load_risk_architecture_ra3()
print()
print("   check_generation_1_provenance(arch) ->")
for k, v in E.check_generation_1_provenance(arch).items():
    print("      %-34s %s" % (k, safe(json.dumps(v, ensure_ascii=False, default=str))[:170]))
print("   check_single_difference_from_ra2(arch) ->")
for k, v in E.check_single_difference_from_ra2(arch).items():
    print("      %-34s %s" % (k, safe(json.dumps(v, ensure_ascii=False, default=str))[:170]))

print()
print("=" * 100)
print("3. existing return-blind test module: what AT-I must extend rather than duplicate")
blind = ROOT / "tests/adversarial/test_g2_selection_return_blind.py"
btext = blind.read_text("utf-8")
print("   lines=%d  tests=%d" % (btext.count("\n"), len(re.findall(r"^def test_", btext, re.M))))
print("   --- imports ---")
for line in btext.splitlines()[:60]:
    if line.startswith(("import ", "from ")) or line.startswith("    from ") or line.startswith("    import "):
        print("   |%s" % safe(line))
print("   --- the _exec_as_module helper, verbatim ---")
m = re.search(r"def _exec_as_module.*?(?=\n\ndef |\n\n@)", btext, re.S)
show("_exec_as_module", m.group(0) if m else "<NOT FOUND>")

print()
print("=" * 100)
print("4. g2_gate_ra3: PROSE_ALIASES in full, and the two guards' bodies")
from stockedge100.strategies import g2_gate_ra3 as G

print("   PROSE_ALIASES (%d):" % len(G.PROSE_ALIASES))
for entry in G.PROSE_ALIASES:
    print("      %s" % safe(repr(entry)))
show("_check_prose_renames_are_as_declared", inspect.getsource(G._check_prose_renames_are_as_declared))
show("_pointers_dropped_since_attempt_2", inspect.getsource(G._pointers_dropped_since_attempt_2))
show("_keys_the_frozen_evaluators_read", inspect.getsource(G._keys_the_frozen_evaluators_read))
print("   _pointers_dropped_since_attempt_2() = %s" % safe(sorted(G._pointers_dropped_since_attempt_2()))[:400])
print("   _keys_the_frozen_evaluators_read()  = %d entries" % len(G._keys_the_frozen_evaluators_read()))

print()
print("=" * 100)
print("5. g2_window_guard surface AT-G asserts against")
from stockedge100.strategies import g2_window_guard as guard

for name in sorted(n for n in dir(guard) if not n.startswith("_")):
    obj = getattr(guard, name)
    if inspect.isfunction(obj):
        print("   def   %-34s %s" % (name, inspect.signature(obj)))
print("   development_bound() = %s" % guard.development_bound())
print("   prohibited_windows() = %s" % safe(guard.prohibited_windows()))

print()
print("=" * 100)
print("6. runner: GridRunRA3 shape and run_one signature (AT-A..AT-F build engines directly)")
from stockedge100.strategies import g2_runner_ra3 as RUN

print("   GridRunRA3 fields = %s" % [f.name for f in dataclasses.fields(RUN.GridRunRA3)])
for name in ("run_one", "run_grid", "selection_inputs", "gate_inputs"):
    print("   def %-24s %s" % (name, inspect.signature(getattr(RUN, name))))
print("   SELECTION_FIELD_NAMES-ish names on runner: %s"
      % [n for n in dir(RUN) if "SELECT" in n.upper()])
