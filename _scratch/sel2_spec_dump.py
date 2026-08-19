"""Print the sealed SEL-2 node from the CONFIG protocol, key by key.

The selection module will load ``config/generation_2/g2_rotation_ra3_protocol.json`` -- the same file
the RA3 engine loads -- not the governance record.  Attempt 2's runner dereferences ``criterion``,
``scope``, ``eliminates``, ``definition``, ``why_not_gross_notional``, ``attempt_2_note`` and
``purpose`` off the sealed steps; a near-copy that guesses a key that moved becomes a KeyError 36 runs
in.  Read the shape first, and diff the two files so "the config says what the record says" is
measured rather than assumed.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
CFG = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
GOV = json.loads(
    (ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json").read_text("utf-8")
)


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


rule = CFG["representative_selection_rule"]

print("=" * 98)
print("config protocol top-level keys")
for key in CFG:
    value = CFG[key]
    kind = "%s(%d)" % (type(value).__name__, len(value)) if isinstance(value, (dict, list)) else safe(repr(value))[:60]
    print("  %-52s %s" % (key, kind))

print()
print("=" * 98)
print("representative_selection_rule, verbatim")
print(safe(json.dumps(rule, indent=2, ensure_ascii=False)))

print()
print("=" * 98)
print("the config node and the governance node agree byte-for-byte?")
a = json.dumps(rule, sort_keys=True, ensure_ascii=False)
b = json.dumps(GOV["representative_selection_rule"], sort_keys=True, ensure_ascii=False)
print("  identical: %s   (config %d chars, governance %d chars)" % (a == b, len(a), len(b)))

print()
print("=" * 98)
print("runs_per_variant / run label declaration")
print(safe(json.dumps(CFG.get("runs_per_variant", "<ABSENT>"), indent=2, ensure_ascii=False))[:1200])

print()
print("=" * 98)
print("grid axes and the 18 variant ids")
grid = CFG["grid"]
for key in grid:
    if key != "variants":
        print("  %-30s %s" % (key, safe(json.dumps(grid[key], ensure_ascii=False))[:120]))
for entry in grid["variants"]:
    print("   %2d  %-46s L=%-3s k=%s  %s"
          % (entry["index"], entry["variant_id"], entry["lookback_months"],
             entry["top_k"], entry["rebalance_frequency"]))
