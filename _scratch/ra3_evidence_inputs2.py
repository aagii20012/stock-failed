"""The shapes the Attempt 3 evidence module consumes, and the two sealed clauses it must satisfy.

Attempt 2's evidence module reads eight fields off each grid row for its determinism claim, calls the
gate twice and subscripts the returned dicts. Under RA3 the gate module renamed `load_criteria` ->
`load_criteria_ra3` and grew a prose-alias adapter, and `reported_for_every_variant_but_not_gating`
went from sixteen entries to eighteen. Both new entries have to be *covered by columns* rather than
mentioned, because `variant_table`'s last loop turns the coverage map into a check.
"""

import inspect
import json
import pathlib
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
C3 = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def wrap(text, indent=6, width=112):
    text = safe(text)
    while text:
        print("%s%s" % (" " * indent, text[:width]))
        text = text[width:]


print("=" * 100)
print("1. reported_for_every_variant_but_not_gating [16] and [17], in full")
node = P3["reported_for_every_variant_but_not_gating"]
for i in (16, 17):
    print("   [%d]:" % i)
    wrap(node[i])

print()
print("=" * 100)
print("2. the four new CFG-3105 sections the evidence body should carry")
for key in ("attempt_2_ref", "mechanics_carried_unchanged", "refs_reverified",
            "gate_criteria_sha256_not_recorded_here", "what_this_attempt_adds_over_attempt_1_carriage"):
    print("   --- %s ---" % key)
    value = P3[key]
    if isinstance(value, str):
        wrap(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            print("      %-38s %s" % (k, safe(json.dumps(v, ensure_ascii=False))[:104]))
    else:
        for item in value:
            print("      - %s" % safe(json.dumps(item, ensure_ascii=False))[:120])

print()
print("=" * 100)
print("3. adaptation_disclosure_carriage_requirement -- the two keys Attempt 2 had no counterpart for")
req = P3["adaptation_disclosure_carriage_requirement"]
for key in ("attempt_3_encoding_addendum", "source"):
    print("   %s:" % key)
    wrap(str(req[key]))

print()
print("=" * 100)
print("4. conflicts_declared_in_the_gate_criteria (CFG-3105's pointer at CFG-3106)")
node = P3["conflicts_declared_in_the_gate_criteria"]
if isinstance(node, str):
    wrap(node)
elif isinstance(node, list):
    for item in node:
        print("   - %s" % safe(json.dumps(item, ensure_ascii=False))[:150])
else:
    for k, v in node.items():
        print("   %-36s %s" % (k, safe(json.dumps(v, ensure_ascii=False))[:110]))

print()
print("=" * 100)
print("5. grid_report row columns -- does every determinism field exist?")
from stockedge100.strategies import g2_runner_ra3 as RUN
src = (ROOT / "src/stockedge100/strategies/g2_runner_ra3.py").read_text("utf-8")
for field in ("trades_digest", "equity_digest", "ranking_digest", "risk_state_digest",
              "fills", "closed_trades", "total_return", "shutdown_session",
              "reconciliation_single_leg_compared", "reconciliation_mismatches",
              "reconciliation_vacuous", "grid_index", "lookback_months", "top_k",
              "rebalance_frequency", "research_shutdown_events", "closed_episodes",
              "selection_score", "attempt_2"):
    print("   %-38s appears in runner source: %s" % (field, ('"%s"' % field) in src))

print()
print("=" * 100)
print("6. gate_inputs returned keys (from the runner source)")
import re
m = re.search(r"def gate_inputs\(.*?\n(?=\ndef |\n@)", src, re.S)
body = m.group(0) if m else ""
print("   keys returned: %s" % sorted(set(re.findall(r'^\s{8}"([a-z0-9_]+)":', body, re.M))))

print()
print("=" * 100)
print("7. select_representative_ra3 returned keys")
m = re.search(r"def select_representative_ra3\(.*?\n(?=\ndef |\n@)", src, re.S)
body = m.group(0) if m else ""
print("   keys returned: %s" % sorted(set(re.findall(r'^\s{8}"([a-z0-9_]+)":', body, re.M))))

print()
print("=" * 100)
print("8. ladder_engagement_comparison returned keys")
m = re.search(r"def ladder_engagement_comparison\(.*?\n(?=\ndef |\n@)", src, re.S)
body = m.group(0) if m else ""
print("   keys returned: %s" % sorted(set(re.findall(r'^\s{8}"([a-z0-9_]+)":', body, re.M))))

print()
print("=" * 100)
print("9. evaluate_representative_ra3 / stage_verdict_ra3 returned keys")
gsrc = (ROOT / "src/stockedge100/strategies/g2_gate_ra3.py").read_text("utf-8")
for fn in ("evaluate_representative_ra3", "stage_verdict_ra3"):
    m = re.search(r"def %s\(.*?\n(?=\ndef |\n@)" % fn, gsrc, re.S)
    body = m.group(0) if m else ""
    print("   %-32s %s" % (fn, sorted(set(re.findall(r'^\s{8}"([a-z0-9_]+)":', body, re.M)))))

print()
print("=" * 100)
print("10. does evaluate_representative_ra3 adapt the criteria itself, or must the caller?")
m = re.search(r"def evaluate_representative_ra3\(.*?\n(?=\ndef |\n@)", gsrc, re.S)
body = m.group(0) if m else ""
for needle in ("adapted_criteria_for_frozen_prose", "condition_5_ra1", "condition_3_ra3",
               "condition_6_ra3", "condition_7_ra3", "condition_4_ra1", "check_thresholds_against_seal"):
    print("   %-36s called inside: %s" % (needle, needle in body))

print()
print("   --- adapted_criteria_for_frozen_prose docstring ---")
m = re.search(r'def adapted_criteria_for_frozen_prose\(.*?"""(.*?)"""', gsrc, re.S)
wrap(m.group(1).strip() if m else "<none>")

print()
print("=" * 100)
print("11. SelectionResultV2 / NeighbourhoodScore surfaces")
from dataclasses import fields
from stockedge100.strategies import g2_selection_v2 as S
for cls in (S.SelectionInputV2, S.NeighbourhoodScore, S.SelectionResultV2):
    print("   %-22s %s" % (cls.__name__, [f.name for f in fields(cls)]))
print("   select_representative_v2 %s" % inspect.signature(S.select_representative_v2))
print("   __all__ %s" % getattr(S, "__all__", None))
