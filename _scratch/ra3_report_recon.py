"""Pass 24: the last recon before the report emitter is written.

Two kinds of question, kept apart on purpose:
  (a) SCHEMA - key names for nodes the emitter will render mechanically (the conflict tables, the
      adversarial-test table, the ranking rows). I only need the keys; the emitter reads the values.
  (b) CONTENT - sealed prose I will paraphrase or quote by hand in sections 6, 10, 14 and 17, which
      I therefore have to read.

ASCII-laundered throughout; the disclosure paragraph carries U+2212 and is never printed whole.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
A3 = ROOT / "reports/stage3_g2_attempt3"


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def load(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


EV = load(A3 / "STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
PROT = load(ROOT / "config/generation_2/g2_rotation_ra3_protocol.json")
CRIT = load(ROOT / "config/generation_2/g2_gate_criteria_ra3.json")
LOCK = load(ROOT / "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json")
COST = load(ROOT / "config/generation_2/g2_cost_model.json")

print("=" * 78)
print("(a) SCHEMA ONLY - the emitter renders these; I need key names, not values")
print("=" * 78)


def schema(label, node):
    print("\n-- %s --" % label)
    if isinstance(node, list):
        print("   list len=%d" % len(node))
        if node and isinstance(node[0], dict):
            print("   item keys: %s" % sorted(node[0]))
            print("   item[0]  : %s" % safe(json.dumps(node[0], default=str))[:400])
        elif node:
            print("   item type: %s ; item[0]: %s" % (type(node[0]).__name__, safe(node[0])[:300]))
    elif isinstance(node, dict):
        print("   dict keys: %s" % sorted(node))
    else:
        print("   %s" % safe(node)[:300])


schema("PROT.conflicts_found", PROT["conflicts_found"])
schema("CRIT.conflicts_found", CRIT["conflicts_found"])
schema("PROT.adversarial_test_requirements", PROT["adversarial_test_requirements"])
# Corrected in pass 24: the 18-row ranking is under selection.result, and neighbour_scores holds
# only the selected variant's four neighbours. The 18 full scores are result.all_scores.
schema("EV.selection.result.ranking", EV["selection"]["result"]["ranking"])
schema("EV.selection.neighbour_scores", EV["selection"]["neighbour_scores"])
schema("EV.selection.result.all_scores", EV["selection"]["result"]["all_scores"])

print("\n-- conflict ids, PROT then CRIT --")
for label, node in (("PROT", PROT["conflicts_found"]), ("CRIT", CRIT["conflicts_found"])):
    ids = [c.get("id") if isinstance(c, dict) else str(c)[:20] for c in node]
    print("   %s (%d): %s" % (label, len(ids), ", ".join(str(i) for i in ids)))

print("\n-- adversarial test requirements (a dict keyed AT-A..AT-M, plus note/regression_floor) --")
ats = PROT["adversarial_test_requirements"]
for k in sorted(ats):
    v = ats[k]
    print("   %-18s %s" % (k, safe(v if isinstance(v, str) else json.dumps(v, default=str))[:260]))

print("\n" + "=" * 78)
print("(b) CONTENT - sealed prose that informs hand-written sections")
print("=" * 78)


def full(label, node, cut=700):
    print("\n-- %s --" % label)
    if isinstance(node, dict):
        for k in node:
            v = node[k]
            if isinstance(v, (str, int, float, bool)) or v is None:
                print("   %-42s %s" % (k, safe(v)[:cut]))
            else:
                print("   %-42s %s" % (k, safe(json.dumps(v, default=str))[:cut]))
    elif isinstance(node, list):
        for i, v in enumerate(node, 1):
            print("   [%02d] %s" % (i, safe(json.dumps(v, default=str) if not isinstance(v, str) else v)[:cut]))
    else:
        print("   %s" % safe(node)[:cut])


full("PROT.risk_architecture", PROT["risk_architecture"])
full("PROT.concentration_ceiling", PROT["concentration_ceiling"])
full("PROT.representative_selection_rule", PROT["representative_selection_rule"])
full("PROT.structural_consequences_declared_before_running",
     PROT["structural_consequences_declared_before_running"])
full("PROT.reproducibility_requirements", PROT["reproducibility_requirements"])
full("PROT.post_seal_defect_rule", PROT["post_seal_defect_rule"])
full("PROT.adaptation_disclosure_carriage_requirement",
     {k: v for k, v in PROT["adaptation_disclosure_carriage_requirement"].items()}
     if isinstance(PROT["adaptation_disclosure_carriage_requirement"], dict)
     else PROT["adaptation_disclosure_carriage_requirement"])
full("CRIT.evaluation_integrity_rules", CRIT["evaluation_integrity_rules"])
full("CRIT.reported_but_not_gating", CRIT["reported_but_not_gating"])
full("CRIT.windows", CRIT["windows"])
full("CRIT.relationship_to_attempt_2_criteria", CRIT["relationship_to_attempt_2_criteria"])
full("CRIT.relationship_to_generation_1_criteria", CRIT["relationship_to_generation_1_criteria"])
print("\n-- CRIT.declaration_note --\n   %s" % safe(CRIT["declaration_note"])[:900])

print("\n-- PROT scalars that name ids, titles and refs --")
for k in sorted(PROT):
    v = PROT[k]
    if isinstance(v, (str, int, float, bool)) or v is None:
        print("   %-46s %s" % (k, safe(v)[:200]))

print("\n-- CRIT scalars --")
for k in sorted(CRIT):
    v = CRIT[k]
    if isinstance(v, (str, int, float, bool)) or v is None:
        print("   %-46s %s" % (k, safe(v)[:200]))

print("\n-- EV top level --")
for k in sorted(EV):
    v = EV[k]
    if isinstance(v, (str, int, float, bool)) or v is None:
        print("   %-46s %s" % (k, safe(v)[:150]))
    else:
        print("   %-46s <%s len=%s>" % (k, type(v).__name__, len(v)))

print("\n-- LOCK.generation_identity --")
full("LOCK.generation_identity", LOCK.get("generation_identity", {}), cut=200)

print("\n-- cost model --")
full("COST", COST, cut=300)

print("\n-- governance/generation_2 listing --")
for p in sorted((ROOT / "governance/generation_2").iterdir()):
    print("   %-62s %8d" % (p.name, p.stat().st_size))

print("\n-- runs/ records mentioning attempt 3 --")
for p in sorted((ROOT / "runs").iterdir()):
    txt = p.read_text(encoding="utf-8")
    if "ATTEMPT_3" in txt or "attempt_3" in txt or "RA3" in txt:
        rec = json.loads(txt)
        print("   %-40s stage=%s" % (p.name, safe(rec.get("stage"))[:70]))
        print("        run_id=%s ts=%s" % (rec.get("run_id"), rec.get("timestamp_utc")))
        print("        repo_state_id=%s" % rec.get("repo_state_id"))
        print("        keys=%s" % sorted(rec))
