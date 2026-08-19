"""Full text of the six sealed passages the runner quotes or asserts against.

Attempt 2's runner asserts substrings of its seal ("both of its runs", "only if both of its runs
satisfy it") so that a seal quietly reverted to an earlier wording refuses instead of running. Those
substrings have to be read, not remembered: an assertion written against remembered wording that
happens to be absent turns into a permanent refusal, and one written against wording that is present
for a different reason asserts nothing.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
C3 = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))
G3 = json.loads((ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json").read_text("utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def wrap(text, indent=6, width=112):
    text = safe(text)
    while text:
        print("%s%s" % (" " * indent, text[:width]))
        text = text[width:]


print("=" * 100)
print("1. CFG-3106's G2A2-CONFLICT-25 entry, in full")
for entry in C3.get("conflicts_declared_in_the_gate_criteria", C3.get("conflicts_found", [])):
    if isinstance(entry, dict) and entry.get("id") == "G2A2-CONFLICT-25":
        for key, value in entry.items():
            print("   %s:" % key)
            wrap(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)

print()
print("=" * 100)
print("2. CFG-3106 reported_but_not_gating[0], in full")
wrap(C3["reported_but_not_gating"][0])

print()
print("=" * 100)
print("3. CFG-3105 run_span.reverification_required + recheck_requirement, in full")
for key in ("recheck_requirement", "reverification_required", "why_unchanged", "carried_from"):
    print("   %s:" % key)
    wrap(str(P3["run_span"][key]))

print()
print("=" * 100)
print("4. CFG-3105 prior_attempt_modules_immutable prose keys, in full")
node = P3["prior_attempt_modules_immutable"]
print("   keys: %s" % list(node))
for key in node:
    if isinstance(node[key], str):
        print("   %s:" % key)
        wrap(node[key])

print()
print("=" * 100)
print("5. GOV-2007 representative_selection_rule + gate")
for section in ("representative_selection_rule", "gate"):
    print("   --- %s ---" % section)
    node = G3.get(section, {})
    if isinstance(node, dict):
        for key, value in node.items():
            print("      %-38s %s" % (key, safe(json.dumps(value, ensure_ascii=False))[:110]))

print()
print("=" * 100)
print("6. CFG-3105 structural_consequences_declared_before_running")
node = P3["structural_consequences_declared_before_running"]
if isinstance(node, list):
    for item in node:
        if isinstance(item, dict):
            print("   %-10s %s" % (item.get("id", "?"), safe(item.get("statement", ""))[:120]))
            for key in sorted(set(item) - {"id", "statement"}):
                print("             %-22s %s" % (key, safe(json.dumps(item[key], ensure_ascii=False))[:96]))
        else:
            print("   - %s" % safe(item)[:130])
else:
    for key, value in node.items():
        print("   %-30s %s" % (key, safe(json.dumps(value, ensure_ascii=False))[:120]))

print()
print("=" * 100)
print("7. CFG-3105 mechanics_carried_unchanged + what_this_attempt_changes_from_attempt_2")
for section in ("mechanics_carried_unchanged", "what_this_attempt_changes_from_attempt_2"):
    print("   --- %s ---" % section)
    node = P3.get(section, {})
    if isinstance(node, dict):
        for key, value in node.items():
            print("      %-34s %s" % (key, safe(json.dumps(value, ensure_ascii=False))[:110]))
    elif isinstance(node, list):
        for item in node:
            print("      - %s" % safe(json.dumps(item, ensure_ascii=False))[:120])
