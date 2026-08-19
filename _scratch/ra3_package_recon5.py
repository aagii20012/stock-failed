"""Fifth reconnaissance pass: the exact nodes whose KEY NAMES the Attempt 3 builder dereferences.

Attempt 3's evidence writer restructured `selection` (no `step_1`/`step_2`/`step_3`, no
`representative_exists`), so every guard and every evidence sentence copied from the Attempt 2
template has to be re-pointed at a measured key rather than a remembered one. This prints those
nodes in full.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def dump(label, node, limit=3000):
    print("=" * 100)
    print(label)
    print(safe(json.dumps(node, indent=1, default=str))[:limit])


EV = json.loads((ROOT / "reports/stage3_g2_attempt3/"
                 "STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))

sel = EV["selection"]
dump("SELECTION.result", sel["result"], 2200)
dump("SELECTION.selected_score", sel["selected_score"], 1800)
dump("SELECTION.neighbour_scores[0]", sel["neighbour_scores"][0], 1200)
print("   neighbour_scores variant ids: %s"
      % [r["variant_id"].replace("SE100-G2-S3-C3-ROTATION-RA3-", "") for r in sel["neighbour_scores"]])
dump("SELECTION.inputs[0]", sel["inputs"][0], 400)

dump("STAGE_VERDICT", EV["stage_verdict"], 3000)

cand = EV["candidate_results"][0]
print("=" * 100)
print("CANDIDATE keys: %s" % sorted(cand))
for key, value in cand.items():
    if isinstance(value, dict):
        print("   %-40s dict %s" % (key, sorted(value)))
    elif isinstance(value, list):
        print("   %-40s list[%d]" % (key, len(value)))
    else:
        print("   %-40s %s" % (key, safe(repr(value))[:150]))

print("=" * 100)
print("CANDIDATE.conditions rows:")
for row in cand["conditions"]:
    print("   %s" % safe(json.dumps(row, default=str))[:320])
print("CANDIDATE.stress_evaluation keys: %s" % sorted(cand["stress_evaluation"]))
print("CANDIDATE.stress_evaluation.conditions rows:")
for row in cand["stress_evaluation"]["conditions"]:
    print("   %s" % safe(json.dumps(row, default=str))[:320])

dump("CANDIDATE.admission_basis", cand["admission_basis"], 3000)

print("=" * 100)
print("DETERMINISM (minus run_digests):")
for key, value in EV["determinism"].items():
    if key == "run_digests":
        print("   %-38s <elided %d>" % (key, len(value)))
    else:
        print("   %-38s %s" % (key, safe(json.dumps(value, default=str))[:260]))

print("=" * 100)
print("RECONCILIATION:")
for key, value in EV["reconciliation"].items():
    if isinstance(value, (dict, list)) and len(value) > 6:
        print("   %-38s %s[%d]" % (key, type(value).__name__, len(value)))
    else:
        print("   %-38s %s" % (key, safe(json.dumps(value, default=str))[:260]))

dump("LADDER.per_statistic", EV["ladder_engagement_comparison"]["per_statistic"], 2600)
dump("LADDER.sessions_at_full_sizing",
     EV["ladder_engagement_comparison"]["sessions_at_full_sizing"], 1400)

for name in ("what_this_attempt_changes_from_attempt_2", "variant_table_is_descriptive_only",
             "reported_for_every_variant_coverage", "prior_attempt_modules_immutable",
             "conflicts_declared_in_the_gate_criteria", "mechanics_carried_unchanged",
             "multiple_comparisons_disclosure", "representative_selection_rule",
             "gate_evaluation_scope", "universe", "hypothesis", "generated_utc", "command",
             "artifact_id", "candidate_index", "strategy_id", "family", "attempt"):
    node = EV.get(name, "<ABSENT>")
    dump("EVIDENCE.%s" % name, node, 1500)

CRIT = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json")
                  .read_text(encoding="utf-8"))
dump("CRITERIA.verdict_token_derivation", CRIT["verdict_token_derivation"], 3200)
print("=" * 100)
print("CRITERIA.conditions:")
for cond in CRIT["conditions"]:
    print("   %s" % safe(json.dumps(cond, default=str))[:420])
dump("CRITERIA.reported_but_not_gating", CRIT.get("reported_but_not_gating"), 900)
print("=" * 100)
print("CRITERIA scalars/short:")
for key, value in CRIT.items():
    if not isinstance(value, (dict, list)):
        print("   %-46s %s" % (key, safe(repr(value))[:180]))
    else:
        print("   %-46s %s[%d]" % (key, type(value).__name__, len(value)))
