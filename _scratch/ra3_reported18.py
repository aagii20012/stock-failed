"""The eighteen reported-but-not-gating quantities in full, and the columns that can carry them.

`variant_table`'s last loop turns REPORTED_COVERAGE into a check: every column named for a quantity
must exist on every row for every label, or the build refuses. Attempt 2 mapped sixteen quantities;
CFG-3105 declares eighteen. Guessing the mapping from the first sixteen and appending two would leave
whichever of the sixteen CFG-3105 reworded pointing at a column that no longer exists.

Prints the sealed prose laundered to ASCII: cp1252 kills the process on U+2014.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
P2 = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text("utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def wrap(text, indent=8, width=108):
    text = safe(text)
    while text:
        print("%s%s" % (" " * indent, text[:width]))
        text = text[width:]


print("=" * 100)
print("1. CFG-3105 reported_for_every_variant_but_not_gating, all eighteen in full")
new = P3["reported_for_every_variant_but_not_gating"]
old = P2["reported_for_every_variant_but_not_gating"]
for i, item in enumerate(new):
    flag = "SAME AS ATT2" if i < len(old) and item == old[i] else "*** DIFFERS/NEW ***"
    print("   [%2d] %s" % (i, flag))
    wrap(item)

print()
print("=" * 100)
print("2. quantities Attempt 2 had that CFG-3105 dropped or reworded")
for i, item in enumerate(old):
    if item not in new:
        print("   old[%2d] no longer present verbatim:" % i)
        wrap(item)

print()
print("=" * 100)
print("3. the exact column names grid_report emits, from one real row")
from stockedge100.strategies import g2_runner_ra3 as RUN
from stockedge100.strategies import g2_rotation_ra3 as R

series = RUN.load_grid_dataset()
run = RUN.run_one(R.rotation_variants()[0], RUN.GATE_RUN_LABEL, series)
rows = RUN.grid_report([run])
names = sorted(rows[0])
print("   %d columns" % len(names))
for i in range(0, len(names), 3):
    print("      %s" % "  ".join("%-34s" % n for n in names[i:i + 3]))
print("   selection_score present without a selection argument: %s" % ("selection_score" in rows[0]))

print()
print("=" * 100)
print("4. other CFG-3105 sections the body carries verbatim -- top-level shapes")
for key in ("what_this_attempt_adds_over_attempt_1", "what_this_attempt_changes_from_attempt_2",
            "multiple_comparisons_disclosure", "representative_selection_rule",
            "gate_evaluation_scope", "structural_consequences_declared_before_running",
            "explicit_non_authorizations", "declared_before_any_strategy_code",
            "declared_before_any_strategy_code_measurement", "eligible_universe", "grid",
            "runs_per_variant", "risk_architecture", "run_span",
            "what_this_attempt_adds_over_attempt_1_carriage", "prior_attempt_modules_immutable"):
    node = P3.get(key, "<ABSENT>")
    kind = type(node).__name__
    if isinstance(node, dict):
        print("   %-48s dict %s" % (key, list(node)))
    elif isinstance(node, list):
        print("   %-48s list[%d]" % (key, len(node)))
    else:
        print("   %-48s %s %s" % (key, kind, safe(node)[:60]))
