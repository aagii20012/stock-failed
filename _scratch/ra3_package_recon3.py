"""Third reconnaissance pass: the remaining nodes the builder reads, plus the on-disk inventory
of what Attempt 3 has already written and what the checksum records cover."""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def show(label, node, limit=260):
    print("-- %s" % label)
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                print("   %-42s %s[%d] %s"
                      % (key, type(value).__name__, len(value),
                         safe(json.dumps(value, default=str))[:limit]))
            else:
                print("   %-42s %s" % (key, safe(repr(value))[:limit]))
    else:
        print("   %s" % safe(json.dumps(node, default=str))[:limit])


EV = json.loads((ROOT / "reports/stage3_g2_attempt3/"
                 "STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))

for name in ("gate", "selection_determinism", "run_span_recheck",
             "reported_for_every_variant_coverage", "multiple_comparisons_disclosure",
             "conflicts_declared_in_the_gate_criteria", "prior_attempt_modules_immutable",
             "universe", "mechanics_carried_unchanged", "gate_evaluation_scope",
             "structural_consequences_declared_before_running"):
    print("=" * 100)
    show("EVIDENCE.%s" % name, EV.get(name, "<ABSENT>"))

print("=" * 100)
print("EVIDENCE.selection keys with short values")
sel = EV["selection"]
for key, value in sel.items():
    if key in ("inputs", "neighbour_scores"):
        print("   %-34s <elided, %d entries>" % (key, len(value)))
    elif isinstance(value, (dict, list)):
        print("   %-34s %s" % (key, safe(json.dumps(value, default=str))[:300]))
    else:
        print("   %-34s %s" % (key, safe(repr(value))[:300]))

print("=" * 100)
print("EVIDENCE.variant_table[0] keys: %s" % sorted(EV["variant_table"][0]))
print("EVIDENCE.variant_table[0]: %s" % safe(json.dumps(EV["variant_table"][0]))[:900])
print("EVIDENCE.runs[0] keys: %s" % sorted(EV["runs"][0]))
print("EVIDENCE.explicit_non_authorizations:")
for item in EV["explicit_non_authorizations"]:
    print("   - %s" % safe(item)[:150])

print("=" * 100)
print("EVIDENCE.attempt_2_ref keys: %s" % sorted(EV["attempt_2_ref"]))
print("EVIDENCE.attempt_1_ref keys: %s" % sorted(EV["attempt_1_ref"]))
print("evidence_digest_covers = %s" % safe(EV["evidence_digest_covers"]))
print("evidence_digest        = %s" % EV["evidence_digest"])
print("command                = %s" % safe(EV["command"]))
print("artifact_id            = %s" % EV["artifact_id"])

CRIT = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json")
                  .read_text(encoding="utf-8"))
print("=" * 100)
print("CRITERIA.conflicts_found (%s):" % type(CRIT["conflicts_found"]).__name__)
cf = CRIT["conflicts_found"]
if isinstance(cf, list):
    for item in cf:
        print("   %s" % safe(json.dumps(item, default=str))[:220])
else:
    show("conflicts_found", cf)
print("CRITERIA.reported_but_not_gating: %s" % safe(json.dumps(CRIT["reported_but_not_gating"]))[:400])

print("=" * 100)
print("on-disk: governance/generation_2 (RA3 only)")
for path in sorted((ROOT / "governance/generation_2").glob("*")):
    if "RA3" in path.name or "A3" in path.name:
        print("   %-62s %d bytes" % (path.name, path.stat().st_size))
print("on-disk: config/generation_2")
for path in sorted((ROOT / "config/generation_2").glob("*")):
    print("   %-62s %d bytes" % (path.name, path.stat().st_size))
print("on-disk: reports/stage3_g2_attempt3")
for path in sorted((ROOT / "reports/stage3_g2_attempt3").glob("*")):
    print("   %-62s %d bytes" % (path.name, path.stat().st_size))
print("on-disk: reports/stage3_g2_attempt2 (template inventory)")
for path in sorted((ROOT / "reports/stage3_g2_attempt2").glob("*")):
    print("   %-62s %d bytes" % (path.name, path.stat().st_size))
