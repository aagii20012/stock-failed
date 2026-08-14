"""Print the exact key names this session's evaluator hard-codes, so none of them is a guess."""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
crit = json.loads((ROOT / "config/stage4_gate_criteria.json").read_text(encoding="utf-8"))


def out(text):
    sys.stdout.write(str(text).encode("ascii", "backslashreplace").decode("ascii") + "\n")


out("== criteria top-level keys ==")
for k, v in crit.items():
    out("  %-46s %-6s %s" % (k, type(v).__name__, len(v) if isinstance(v, (list, dict, str)) else v))

out("")
out("== verdict_token_derivation ==")
out(json.dumps(crit["verdict_token_derivation"], indent=2))

out("")
out("== every condition predicate, with its Decimal literal count ==")
import re
lit = re.compile(r"Decimal\('([-0-9.]+)'\)")
for entry in crit["conditions"]:
    found = lit.findall(str(entry["predicate"]))
    out("  %-8s literals=%d %s" % (entry["id"], len(found), found))
    out("      %s" % entry["predicate"])

out("")
out("== companion thresholds ==")
out(json.dumps(crit["frozen_gate_json_companion_verbatim"], indent=2))

out("")
out("== evaluation_integrity_rules ==")
out(json.dumps(crit["evaluation_integrity_rules"], indent=2))

out("")
out("== incoherent_combinations_refused ==")
out(json.dumps(crit["incoherent_combinations_refused"], indent=2))
