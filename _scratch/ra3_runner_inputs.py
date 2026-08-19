"""Everything g2_runner_ra3.py must read, dumped before a line of it is written.

Attempt 2's runner hardcodes subscripts into five sealed subtrees -- `runs_per_variant`,
`run_span`, `representative_selection_rule`, `gate_evaluation_scope` and
`attempt_1_modules_immutable`.  CFG-3105 renamed at least one of them already (`recheck_requirement`
-> `reverification_required`, per build_plan_ra3), and SEL-2 replaced the three-step rule outright.
Finding a KeyError at grid time -- after thirty-six backtests -- would be the worst possible place.

Also resolves which public callables the three new RA3 modules actually export, because the runner
is written against those names and `dir()` is cheaper than being wrong.
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


def dump(node, indent=6, width=150):
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)) and value:
                print("%s%s:" % (" " * indent, key))
                dump(value, indent + 3, width)
            else:
                print("%s%-34s %s" % (" " * indent, key, safe(json.dumps(value, ensure_ascii=False))[:width]))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            if isinstance(value, (dict, list)):
                print("%s[%d]" % (" " * indent, i))
                dump(value, indent + 3, width)
            else:
                print("%s[%d] %s" % (" " * indent, i, safe(json.dumps(value, ensure_ascii=False))[:width]))


print("=" * 100)
print("0. CFG-3105 top-level keys vs CFG-3103's")
a, b = list(P3), list(P2)
print("   RA3 : %s" % a)
print("   Att2: %s" % b)
print("   only-RA3 : %s" % sorted(set(a) - set(b)))
print("   only-Att2: %s" % sorted(set(b) - set(a)))

for section in ("runs_per_variant", "run_span", "representative_selection_rule",
                "gate_evaluation_scope"):
    print()
    print("=" * 100)
    print("%s -- RA3" % section)
    node3 = P3.get(section)
    if node3 is None:
        print("   *** ABSENT from CFG-3105 ***")
    else:
        dump(node3)
    node2 = P2.get(section, {})
    if isinstance(node3, dict) and isinstance(node2, dict):
        print("   only-RA3 keys : %s" % sorted(set(node3) - set(node2)))
        print("   only-Att2 keys: %s" % sorted(set(node2) - set(node3)))

print()
print("=" * 100)
print("prior-attempt immutability section (Attempt 2 called it attempt_1_modules_immutable)")
for key in sorted(P3):
    if "immutable" in key or "modules" in key:
        print("   CFG-3105 %s:" % key)
        dump(P3[key])

print()
print("=" * 100)
print("reported-but-not-gating list")
for key in sorted(P3):
    if "reported" in key:
        print("   CFG-3105 %s:" % key)
        dump(P3[key])

print()
print("=" * 100)
print("governance seal for Attempt 3 -- does one exist, and what span does it record?")
gov = ROOT / "governance" / "generation_2"
for path in sorted(gov.glob("*RA3*")):
    print("   %s  %d bytes" % (path.name, path.stat().st_size))
cand = gov / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
if cand.is_file():
    G = json.loads(cand.read_text("utf-8"))
    print("   artifact_id: %s" % G.get("artifact_id"))
    print("   top-level keys: %s" % list(G))
    for key in sorted(G):
        if "span" in key or "contamination" in key:
            print("   %s:" % key)
            dump(G[key], 6, 110)
else:
    print("   *** no STAGE_3_G2_ROTATION_RA3_PROTOCOL.json ***")

print()
print("=" * 100)
print("public surface of the three RA3 modules the runner imports")
from stockedge100.strategies import g2_rotation_ra3 as R
from stockedge100.strategies import g2_selection_v2 as S
from stockedge100.backtest import g2_engine_ra3 as E

for name, mod in (("g2_rotation_ra3", R), ("g2_selection_v2", S), ("g2_engine_ra3", E)):
    public = sorted(n for n in dir(mod) if not n.startswith("_"))
    declared = getattr(mod, "__all__", None)
    print("   %-18s __all__=%s" % (name, declared))
    print("   %-18s public=%s" % ("", public))
    print()

print("=" * 100)
print("signatures the runner calls")
import inspect
for label, fn in (
    ("rotation_variants", R.rotation_variants),
    ("variant_by_id", R.variant_by_id),
    ("eligible_universe", R.eligible_universe),
    ("load_protocol", R.load_protocol),
    ("neighbours_of", S.neighbours_of),
    ("score_neighbourhood", S.score_neighbourhood),
    ("select_representative_v2", S.select_representative_v2),
):
    try:
        print("   %-26s %s" % (label, inspect.signature(fn)))
    except Exception as exc:
        print("   %-26s <%s>" % (label, exc))
print("   SelectionInputV2 fields    %s" % list(S.SELECTION_V2_FIELD_NAMES))
print("   QUANTITIES                 %s" % list(S.QUANTITIES))
print("   SELECTION_RULE_ID          %s" % S.SELECTION_RULE_ID)
print("   build_candidate present in g2_rotation_ra3: %s" % hasattr(R, "build_candidate"))
if hasattr(R, "build_candidate"):
    print("   build_candidate            %s" % inspect.signature(R.build_candidate))
print("   RotationEngineRA3.__init__ %s" % inspect.signature(E.RotationEngineRA3.__init__))
