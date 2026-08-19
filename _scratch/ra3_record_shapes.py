"""Print the actual shape of the two nodes the verifier guessed wrong.

The verifier's job is to distrust the sealer's summary; when it fails, the first question is which
of the two is wrong.  Read the nodes rather than adjusting the predicate to whatever passes.
"""

import json
import pathlib

JS = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100/governance/generation_2"
                  "/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json")
record = json.loads(JS.read_text("utf-8"))

def safe(text):
    """cp1252 cannot encode U+2014/U+2212, and the console kills the process rather than degrade.

    The mandated disclosure carries both by design, so any dump of this record must be laundered
    before it reaches stdout.  Non-ASCII becomes a codepoint marker so its presence stays visible.
    """
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


print("=" * 92)
print("all 52 top-level keys with their types and scalar values")
for key in record:
    value = record[key]
    if isinstance(value, (dict, list)):
        print("  %-52s %s(%d)" % (key, type(value).__name__, len(value)))
    else:
        print("  %-52s %s" % (key, safe(repr(value))[:150]))

print()
print("=" * 92)
for key in ("sealed_before_any_result_was_seen", "representative_selection_rule"):
    print("-- %s " % key + "-" * max(2, 80 - len(key)))
    print(safe(json.dumps(record.get(key, "<ABSENT>"), indent=2, ensure_ascii=False))[:3000])
    print()

print("=" * 92)
print("any key mentioning 'sealed', 'result', 'selection' or 'blind'")
for key in record:
    if any(t in key for t in ("sealed", "result", "selection", "blind")):
        print("  %s" % key)
