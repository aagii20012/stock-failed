"""Static pre-flight for g2_stage3_attempt3_evidence.py, before it runs seventy-two backtests.

The grid plus the determinism replay is thirty-six runs twice. A KeyError raised on the last line of
`run_all_g2_attempt3` -- assembling the body, after every backtest has completed -- costs the whole
run. Every subscript in the module is a literal against a sealed JSON, and every callee is a name in
a module RA3 renamed things in, so both are checkable without running anything.

Four sections:
  1. every `protocol["..."]` / `criteria["..."]` subscript, extracted from the AST, against the files
  2. every function the module calls on runner/gate/engine/selection, against those modules
  3. the declared column tuples against grid_report's actual output on one real row
  4. the coverage map against the sealed eighteen -- same count, and every column named is declared
"""

import ast
import inspect
import json
import pathlib
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

MODULE = ROOT / "src/stockedge100/reporting/g2_stage3_attempt3_evidence.py"
SRC = MODULE.read_text("utf-8")
TREE = ast.parse(SRC)

P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
C3 = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))

failures = []


def check(label, ok, detail=""):
    print("   %-6s %s%s" % ("ok" if ok else "FAIL", label, ("  " + detail) if detail else ""))
    if not ok:
        failures.append(label)


print("=" * 100)
print("1. protocol[...] and criteria[...] subscripts against the sealed files")
subscripts = {"protocol": set(), "criteria": set()}
for node in ast.walk(TREE):
    if not isinstance(node, ast.Subscript):
        continue
    value = node.value
    if not isinstance(value, ast.Name) or value.id not in subscripts:
        continue
    key = node.slice
    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        subscripts[value.id].add(key.value)

for name, keys in sorted(subscripts.items()):
    sealed = P3 if name == "protocol" else C3
    print("   --- %s: %d distinct top-level subscripts ---" % (name, len(keys)))
    for key in sorted(keys):
        check("%s[%r]" % (name, key), key in sealed)

print()
print("=" * 100)
print("2. nested subscripts written as protocol['a']['b']")
for node in ast.walk(TREE):
    if not isinstance(node, ast.Subscript):
        continue
    inner = node.value
    if not isinstance(inner, ast.Subscript):
        continue
    base = inner.value
    if not isinstance(base, ast.Name) or base.id not in subscripts:
        continue
    if not (isinstance(inner.slice, ast.Constant) and isinstance(node.slice, ast.Constant)):
        continue
    outer_key, inner_key = inner.slice.value, node.slice.value
    if not isinstance(outer_key, str) or not isinstance(inner_key, str):
        continue
    sealed = P3 if base.id == "protocol" else C3
    parent = sealed.get(outer_key)
    ok = isinstance(parent, dict) and inner_key in parent
    check("%s[%r][%r]" % (base.id, outer_key, inner_key), ok)

print()
print("=" * 100)
print("3. every attribute call on an imported module resolves")
import stockedge100.reporting.g2_stage3_attempt3_evidence as EV
from stockedge100.strategies import g2_gate_ra3 as gate
from stockedge100.strategies import g2_runner_ra3 as runner
from stockedge100.strategies import g2_window_guard as guard

MODULES = {"runner": runner, "gate": gate, "guard": guard}
calls = set()
for node in ast.walk(TREE):
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        if node.value.id in MODULES:
            calls.add((node.value.id, node.attr))
for alias, attr in sorted(calls):
    check("%s.%s" % (alias, attr), hasattr(MODULES[alias], attr))

print("   --- bare names imported from engine / selection ---")
for name in ("load_risk_architecture_ra3", "check_generation_1_provenance",
             "check_single_difference_from_ra2", "attributes_derived_from_risk",
             "select_representative_v2", "SelectionInputV2", "SELECTION_V2_FIELD_NAMES"):
    check("evidence.%s" % name, hasattr(EV, name))

print("   --- signatures of the six functions with keyword contracts ---")
for fn in (runner.run_grid, runner.grid_report, runner.recheck_run_span,
           runner.select_representative_ra3, runner.gate_inputs,
           gate.evaluate_representative_ra3, gate.stage_verdict_ra3, gate.condition_5_ra1,
           EV.select_representative_v2):
    print("      %-34s %s" % (fn.__name__, inspect.signature(fn)))

print()
print("=" * 100)
print("4. declared column tuples against one real grid_report row")
from stockedge100.strategies import g2_rotation_ra3 as R

series = runner.load_grid_dataset()
run = runner.run_one(R.rotation_variants()[0], runner.GATE_RUN_LABEL, series)
row = runner.grid_report([run])[0]
emitted = set(row)
declared = set(EV._PER_RUN_COLUMNS) | set(EV._VARIANT_LEVEL_COLUMNS)
# selection_score is absent without a selection= argument; that is expected here and only here.
check("declared - emitted == {selection_score}", declared - emitted == {"selection_score"},
      repr(sorted(declared - emitted)))
check("emitted - declared == {}", not (emitted - declared), repr(sorted(emitted - declared)))
check("no column is in both tuples",
      not (set(EV._PER_RUN_COLUMNS) & set(EV._VARIANT_LEVEL_COLUMNS)))
check("_PER_RUN_COLUMNS has no duplicates",
      len(EV._PER_RUN_COLUMNS) == len(set(EV._PER_RUN_COLUMNS)))
print("      per_run=%d variant_level=%d emitted=%d"
      % (len(EV._PER_RUN_COLUMNS), len(EV._VARIANT_LEVEL_COLUMNS), len(emitted)))

print()
print("=" * 100)
print("5. REPORTED_COVERAGE against the sealed eighteen")
sealed = P3["reported_for_every_variant_but_not_gating"]
check("count matches the seal", len(EV.REPORTED_COVERAGE) == len(sealed),
      "map=%d sealed=%d" % (len(EV.REPORTED_COVERAGE), len(sealed)))
check("every scope is per_run or per_variant",
      all(s in ("per_run", "per_variant") for _, _, s in EV.REPORTED_COVERAGE))
known = declared | set(EV._PER_RUN_EXTRA_COLUMNS)
for quantity, columns, scope in EV.REPORTED_COVERAGE:
    for column in columns:
        check("coverage column %r (%s)" % (column, scope), column in known)
        if scope == "per_variant":
            check("   ...and %r is variant-level" % column,
                  column in EV._VARIANT_LEVEL_COLUMNS)
        elif column not in EV._PER_RUN_EXTRA_COLUMNS:
            check("   ...and %r is per-run" % column, column in EV._PER_RUN_COLUMNS)

print()
print("=" * 100)
print("6. the disclosure, compared not printed")
import hashlib
text = P3["adaptation_disclosure_verbatim"]
check("length 1507", len(text) == 1507, str(len(text)))
check("sha256 matches the operating instruction",
      hashlib.sha256(text.encode("utf-8")).hexdigest()
      == "ce1d6476f44562310fb059c5817645baa25477cc4f6168b414f3423834c8e925")
check("EVIDENCE_REL is on the sealed carrier list",
      EV.EVIDENCE_REL in P3["adaptation_disclosure_carriage_requirement"]["must_appear_verbatim_in"])

print()
print("=" * 100)
print("RESULT: %d failure(s)%s" % (len(failures), (": " + repr(failures)) if failures else ""))
