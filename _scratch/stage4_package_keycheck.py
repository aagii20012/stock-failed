"""Confirm every key stage4_evaluation_package.py reads actually exists on disk.

Cheaper than discovering a KeyError inside the real build, which cannot be re-run without
invalidating the digest it just recorded. ASCII-only output: the console is cp1252.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(ROOT / "src"))


def out(text):
    sys.stdout.write(str(text).encode("ascii", "backslashreplace").decode("ascii") + "\n")


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


ev = load("reports/stage4/STAGE_4_VALIDATION_EVIDENCE.json")
crit = load("config/stage4_gate_criteria.json")
proto = load("config/stage4_validation_protocol.json")
seal = load("governance/STAGE_4_PREREGISTRATION.json")
sel = load("config/stage4_representative_selection.json")
lock = load("governance/STAGE_1_HOLDOUT_LOCK.json")
uni = load("governance/STAGE_1_UNIVERSE.json")

ok = True


def probe(label, fn):
    global ok
    try:
        value = fn()
    except Exception as exc:
        ok = False
        out("  MISSING  %-52s %s: %s" % (label, type(exc).__name__, exc))
    else:
        text = json.dumps(value, default=str)
        out("  ok       %-52s %s" % (label, text[:76]))


out("== evidence top-level keys ==")
out("  " + ", ".join(sorted(ev)))
out("")

out("== evidence ==")
probe("artifact_id", lambda: ev["artifact_id"])
probe("evidence_digest_covers", lambda: ev["evidence_digest_covers"])
probe("representative (keys)", lambda: sorted(ev["representative"]))
probe("datasets (keys)", lambda: sorted(ev["datasets"]))
probe("datasets", lambda: ev["datasets"])
probe("single_validation_read (keys)", lambda: sorted(ev["single_validation_read"]))
probe("svr.validation_partition", lambda: ev["single_validation_read"]["validation_partition"])
probe("svr.run_bounds", lambda: ev["single_validation_read"]["run_bounds"])
probe("svr.validation_dataset_loads", lambda: ev["single_validation_read"]["validation_dataset_loads"])
probe("svr.validation_reading_sessions", lambda: ev["single_validation_read"]["validation_reading_sessions"])
probe("svr.validation_window_engine_runs", lambda: ev["single_validation_read"]["validation_window_engine_runs"])
probe("svr.holdout", lambda: ev["single_validation_read"]["holdout"])
probe("holdout_unreachability_proof (keys)", lambda: sorted(ev["holdout_unreachability_proof"]))
probe("folds (keys)", lambda: sorted(ev["folds"]))
probe("folds.declared_test_folds", lambda: ev["folds"]["declared_test_folds"])
probe("folds.declared_train_folds", lambda: ev["folds"]["declared_train_folds"])
probe("folds.completed / positive", lambda: [ev["folds"]["completed"], ev["folds"]["positive"]])
probe("gate_evidence (keys)", lambda: sorted(ev["gate_evidence"]))
probe("gate_evidence.base (keys)", lambda: sorted(ev["gate_evidence"]["base"]))
probe("gate_evidence.stress (keys)", lambda: sorted(ev["gate_evidence"]["stress"]))
probe("gate_evidence.invariance (keys)", lambda: sorted(ev["gate_evidence"]["invariance"]))
probe("strategy_invariance (keys)", lambda: sorted(ev["strategy_invariance"]))
probe("runs[0] (keys)", lambda: sorted(ev["runs"][0]))
out("")

out("== base measures the package quotes ==")
for key in ("total_return", "sharpe", "sharpe_risk_free_annual", "max_drawdown", "profit_factor",
            "closed_trades", "shutdown_session"):
    probe("base." + key, (lambda k: (lambda: ev["gate_evidence"]["base"][k]))(key))
out("")

out("== stress measures the package quotes ==")
for key in ("total_return", "stress_multiplier", "shutdown_enforced", "shutdown_session"):
    probe("stress." + key, (lambda k: (lambda: ev["gate_evidence"]["stress"][k]))(key))
out("")

out("== invariance clauses ==")
for key in ("all_digests_equal", "digests_equal", "digests_total",
            "validation_evaluation_run_records", "validation_window_engine_runs",
            "declared_run_count", "conflict_note"):
    probe("invariance." + key, (lambda k: (lambda: ev["gate_evidence"]["invariance"][k]))(key))
out("")

out("== gate condition entries ==")
for cond in ev["gate"]["conditions"]:
    out("  %-7s verdict=%-14s satisfied=%-5s measured=%s"
        % (cond["id"], cond["verdict"], cond["satisfied"], str(cond["measured"])[:34]))
out("")

out("== sealed criteria per condition ==")
for cond in crit["conditions"]:
    for key in ("required_verbatim", "boundary", "measurement", "predicate"):
        if key not in cond:
            ok = False
            out("  MISSING  %s.%s" % (cond["id"], key))
    out("  %-7s keys: %s" % (cond["id"], ", ".join(sorted(cond))))
out("")

out("== protocol ==")
probe("runs_declared (keys)", lambda: sorted(proto["runs_declared"]))
probe("runs_declared.count", lambda: proto["runs_declared"]["count"])
probe("runs_declared.count_is_a_hard_limit", lambda: proto["runs_declared"]["count_is_a_hard_limit"])
probe("runs_declared.sessions_reading_validation", lambda: proto["runs_declared"]["sessions_reading_validation"])
probe("runs_declared.re_runs_...", lambda: proto["runs_declared"]["re_runs_permitted_after_a_valid_completed_run"])
probe("runs_declared.runs[*].run_label", lambda: [r["run_label"] for r in proto["runs_declared"]["runs"]])
probe("post_seal_defect_rule (keys)", lambda: sorted(proto["post_seal_defect_rule"]))
probe("no_retuning_rule.what_a_fail_does_not_authorize", lambda: proto["no_retuning_rule"]["what_a_fail_does_not_authorize"])
probe("no_retuning_rule.what_a_fail_does_authorize", lambda: proto["no_retuning_rule"]["what_a_fail_does_authorize"])
probe("stage_5_remains_prohibited_conditions", lambda: len(proto["stage_5_remains_prohibited_conditions"]))
probe("explicit_non_authorizations", lambda: proto["explicit_non_authorizations"])
out("")

out("== seal ==")
probe("document_id", lambda: seal["document_id"])
probe("declared_utc", lambda: seal["declared_utc"])
probe("validation_evaluation_authorized_for", lambda: seal["validation_evaluation_authorized_for"])
probe("binding_consequences[7]", lambda: seal["binding_consequences"][7])
probe("binding_consequences count", lambda: len(seal["binding_consequences"]))
probe("sealed_digests_for_s4_c7 (keys)", lambda: sorted(seal["sealed_digests_for_s4_c7"]))
probe("sd.declared_set_size", lambda: seal["sealed_digests_for_s4_c7"]["declared_set_size"])
probe("sd.own_digest_excluded", lambda: seal["sealed_digests_for_s4_c7"]["own_digest_excluded"])
probe("sd.own_digest_location", lambda: seal["sealed_digests_for_s4_c7"]["own_digest_location"])
probe("sd.recheck_rule", lambda: seal["sealed_digests_for_s4_c7"]["recheck_rule"])
probe("sd.entries count", lambda: len(seal["sealed_digests_for_s4_c7"]["entries"]))
probe("contamination_predicates (keys)", lambda: sorted(seal["contamination_predicates"]))
probe("cp.definitions.gate_3...", lambda: seal["contamination_predicates"]["definitions"]["gate_3_attempt_2_records_verify"][:70])
out("")

out("== selection / lock / universe ==")
probe("selection.artifact_id", lambda: sel["artifact_id"])
probe("selection keys", lambda: sorted(sel))
probe("selection.selection_rule_id", lambda: sel.get("selection_rule_id", "<absent, .get used>"))
probe("lock.holdout_start", lambda: lock["holdout_start"])
probe("lock.holdout_end", lambda: lock["holdout_end"])
probe("universe.universe_version", lambda: uni["universe_version"])
out("")

out("== shared builder surface ==")
try:
    from stockedge100.audit import sha256_file
    from stockedge100.reporting.stage_package import StageDecision
    import dataclasses
    out("  ok       sha256_file imported")
    fields = [f.name for f in dataclasses.fields(StageDecision)]
    out("  ok       StageDecision fields: %s" % ", ".join(fields))
    params = getattr(StageDecision, "__dataclass_params__", None)
    out("  ok       frozen=%s" % (params.frozen if params else "unknown"))
except Exception as exc:
    ok = False
    out("  MISSING  builder surface: %s: %s" % (type(exc).__name__, exc))

out("")
out("ALL KEYS RESOLVE" if ok else "SOMETHING IS MISSING -- fix before the dry run")
