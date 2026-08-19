"""Pass 21: dump every remaining field the Attempt 3 research report must quote.

Three files, so each stays readable:
  _scratch/ra3_rep_A.txt  protocol (SE100-CFG-3105)
  _scratch/ra3_rep_B.txt  gate criteria (SE100-CFG-3106) + partition lock
  _scratch/ra3_rep_C.txt  evidence structural nodes (SE100-EVID-3103)

Everything is laundered to ASCII on the way out: the sealed disclosure carries U+2212,
which cp1252 cannot encode, and these files are read back with the Read tool.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
OUT = pathlib.Path("d:/Product/stock-trade-alpaca/_scratch")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


EV = load("reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
PROT = load("config/generation_2/g2_rotation_ra3_protocol.json")
CRIT = load("config/generation_2/g2_gate_criteria_ra3.json")
LOCK = load("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json")


def dump(node, limit=None):
    text = safe(json.dumps(node, indent=1, default=str))
    return text if limit is None else text[:limit]


# ---------------------------------------------------------------- A: protocol
a = []
a.append("=== PROT scalars ===")
for k in sorted(PROT):
    v = PROT[k]
    if isinstance(v, (str, int, float, bool)) or v is None:
        a.append("%-56s %s" % (k, safe(v)[:300]))

a.append("")
a.append("=== PROT.window ===")
a.append(dump(PROT["window"]))
a.append("")
a.append("=== PROT.run_span ===")
a.append(dump(PROT["run_span"]))
a.append("")
a.append("=== PROT.grid ===")
a.append(dump(PROT["grid"], 2500))
a.append("")
for key in ("ranking_signal", "ranking_rule", "position_count", "rebalance",
            "eligible_universe", "position_sizing", "execution", "serialisation",
            "gate_evaluation_scope", "reported_for_every_variant_but_not_gating",
            "mechanics_carried_unchanged", "refs_reverified",
            "reproducibility_requirements", "adversarial_test_requirements",
            "explicit_non_authorizations", "what_this_attempt_changes_from_attempt_2",
            "what_this_attempt_adds_over_attempt_1",
            "what_this_attempt_adds_over_attempt_1_carriage",
            "what_makes_this_genuinely_cross_sectional",
            "declared_before_any_strategy_code_measurement",
            "attempt_1_ref", "attempt_2_ref", "charter_ref", "constitution_ref",
            "partition_lock_ref", "cost_model_derivation_ref", "gate_criteria_ref",
            "concentration_ceiling", "post_seal_defect_rule", "declaration_note",
            "prior_attempt_modules_immutable"):
    a.append("=== PROT.%s ===" % key)
    a.append(dump(PROT.get(key, "<absent>"), 3000))
    a.append("")

a.append("=== PROT.risk_architecture.components (names/values only) ===")
for cid in sorted(PROT["risk_architecture"]["components"]):
    comp = PROT["risk_architecture"]["components"][cid]
    a.append("  %-8s %-34s %s" % (cid, safe(comp.get("name", "?")),
                                  safe(json.dumps(comp.get("value", comp.get("bands", "-")),
                                                  default=str))[:260]))
a.append("")
a.append("=== PROT.risk_architecture.components['RA3-4'] (the ladder, in full) ===")
a.append(dump(PROT["risk_architecture"]["components"]["RA3-4"], 6000))
a.append("")
a.append("=== PROT.risk_architecture.components['RA3-5'] ===")
a.append(dump(PROT["risk_architecture"]["components"]["RA3-5"], 2500))
a.append("")
a.append("=== PROT.representative_selection_rule.steps (3+) ===")
a.append(dump(PROT["representative_selection_rule"]["steps"], 7000))
a.append("")
a.append("=== PROT.representative_selection_rule other keys ===")
for k in sorted(PROT["representative_selection_rule"]):
    if k in ("steps", "structural_enforcement"):
        continue
    a.append("  %-44s %s" % (k, safe(json.dumps(PROT["representative_selection_rule"][k],
                                                default=str))[:500]))
a.append("")
a.append("=== PROT.structural_consequences_declared_before_running ===")
a.append(dump(PROT["structural_consequences_declared_before_running"], 9000))
a.append("")
a.append("=== PROT.conflicts_found ===")
a.append(dump(PROT["conflicts_found"], 9000))
(OUT / "ra3_rep_A.txt").write_text("\n".join(a), encoding="utf-8")

# ------------------------------------------------- B: gate criteria + lock
b = []
b.append("=== CRIT scalars ===")
for k in sorted(CRIT):
    v = CRIT[k]
    if isinstance(v, (str, int, float, bool)) or v is None:
        b.append("%-56s %s" % (k, safe(v)[:400]))
b.append("")
b.append("=== CRIT.conditions ===")
for cond in CRIT["conditions"]:
    b.append("  --- %s ---" % safe(cond.get("id", "?")))
    for k in sorted(cond):
        b.append("      %-40s %s" % (k, safe(json.dumps(cond[k], default=str))[:700]))
b.append("")
for key in ("windows", "frozen_gate_text_verbatim", "frozen_gate_json_companion_verbatim",
            "evaluation_integrity_rules", "reported_but_not_gating",
            "adaptation_disclosure_carried", "relationship_to_attempt_1_criteria",
            "relationship_to_attempt_2_criteria", "relationship_to_generation_1_criteria",
            "declaration_note", "conflicts_found"):
    b.append("=== CRIT.%s ===" % key)
    b.append(dump(CRIT.get(key, "<absent>"), 9000))
    b.append("")
b.append("=== LOCK.validation_reuse_disclosure ===")
b.append(dump(LOCK.get("validation_reuse_disclosure", "<absent>"), 4000))
b.append("")
b.append("=== LOCK.validation_reuse_disclosure_sources ===")
b.append(dump(LOCK.get("validation_reuse_disclosure_sources", "<absent>"), 2500))
b.append("")
for key in ("authorized_windows", "partition", "holdout_state", "holdout_read_authorized",
            "generation_1_holdout_state", "validation_window_state", "stage_3_authorized",
            "stage_4_authorized", "locked_utc", "run_id", "artifact_id",
            "generation_identity", "repo_state_id_location", "enforcement",
            "sealed_data_on_disk_note", "coverage_measured_from_disk", "status"):
    b.append("=== LOCK.%s ===" % key)
    b.append(dump(LOCK.get(key, "<absent>"), 2500))
    b.append("")
(OUT / "ra3_rep_B.txt").write_text("\n".join(b), encoding="utf-8")

# ------------------------------------------------------- C: evidence nodes
c = []
c.append("=== EV top-level keys ===")
c.append(safe(sorted(EV)))
c.append("")
c.append("=== EV scalars ===")
for k in sorted(EV):
    v = EV[k]
    if isinstance(v, (str, int, float, bool)) or v is None:
        c.append("%-56s %s" % (k, safe(v)[:300]))
c.append("")
for key in ("sealed_inputs", "window", "run_span_recheck", "universe", "cost_model",
            "determinism", "reconciliation", "tests", "artifacts",
            "prior_attempt_module_verification", "gate_scope", "stage_verdict",
            "adaptation_disclosure_carriage", "grid",
            "representative_selection_rule", "explicit_non_authorizations",
            "mechanics_carried_unchanged", "limitations", "conflicts_found",
            "conflicts_declared_in_the_gate_criteria"):
    c.append("=== EV.%s ===" % key)
    c.append(dump(EV.get(key, "<absent>"), 9000))
    c.append("")
c.append("=== EV.selection (minus result.all_scores / inputs / neighbour_scores) ===")
sel = {k: v for k, v in EV["selection"].items()
       if k not in ("inputs", "neighbour_scores", "result")}
c.append(dump(sel, 6000))
c.append("")
c.append("=== EV.selection.result (minus all_scores) ===")
res = {k: v for k, v in EV["selection"]["result"].items() if k != "all_scores"}
c.append(dump(res, 6000))
(OUT / "ra3_rep_C.txt").write_text("\n".join(c), encoding="utf-8")

print("wrote A=%d B=%d C=%d chars"
      % (len((OUT / "ra3_rep_A.txt").read_text(encoding="utf-8")),
         len((OUT / "ra3_rep_B.txt").read_text(encoding="utf-8")),
         len((OUT / "ra3_rep_C.txt").read_text(encoding="utf-8"))))
