"""Out-of-tree smoke check for attempt2_harness. Reads sealed config; runs no evaluation."""

import json
import sys

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, STRESSED, CostModel
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.window import development_window
from stockedge100.strategies import attempt2_harness as H
from stockedge100.strategies.attempt2_config import load_attempt2_config

config = load_attempt2_config()
stage2 = load_stage2_config()
window = development_window()

print("== every protocol/binding/prereg key run_all() reads resolves ==")
for key in (
    "project", "generation", "attempt", "attempt_id", "inputs_bound", "partitions",
    "benchmarks", "cost_stress_treatment", "known_prior_evidence",
    "adaptive_research_disclosure", "multiple_comparisons_disclosure",
    "cumulative_experiment_count", "reproducibility_requirements",
    "explicit_non_authorizations", "no_selection_in_this_stage",
):
    assert key in config.protocol, key
print("protocol keys ok")
for key in ("artifact_id", "admissible_candidate_exists"):
    assert key in config.binding, key
print("binding keys ok  artifact_id =", config.binding["artifact_id"])
for key in (
    "document_id", "declared_utc", "run_id", "authorized_windows",
    "validation_window_state", "holdout_window_state",
    "sealed_before_any_attempt_2_strategy_code", "stage_4_authorized",
    "paper_trading_authorized", "shadow_live_authorized", "live_trading_authorized",
):
    assert key in config.preregistration, key
print("prereg keys ok  document_id =", config.preregistration["document_id"])
for key in ("gate_id", "gate_name", "constitution_ref"):
    assert key in config.criteria, key
print("criteria keys ok ", config.criteria["gate_id"], "|", config.criteria["gate_name"])

print()
print("== window block ==")
print(json.dumps(H._window_block(config, window), indent=2)[:1400])

print()
print("== cost block ==")
base = CostModel(stage2.cost_model, BASE)
stressed = CostModel(stage2.cost_model, STRESSED)
block = H._cost_block(base, stressed)
print("base gating           ", block["base"]["gating"])
print("base min_order_notional", block["base"]["min_order_notional_usd"])
print("base shutdown dd      ", block["base"]["research_shutdown_drawdown"])
print("stress multiplier     ", block["stressed"]["stress_multiplier"])
print("stress gating         ", block["stressed"]["gating"])
print("stress min_order_notional", block["stressed"]["min_order_notional_usd"])
print("stress shutdown dd    ", block["stressed"]["research_shutdown_drawdown"])

print()
print("== budget figures the three guards will compare against ==")
budget = dict(config.iteration_budget)
for key in (
    "total_declared_gating_variants",
    "total_declared_non_gating_stress_runs",
    "total_declared_runs",
    "revisions_permitted",
):
    print(f"  {key} = {budget[key]}")

print()
print("== rollup: aggregation must be on satisfaction, not on verdict == MET ==")


def cond(cid, verdict):
    return {
        "id": cid,
        "verdict": verdict,
        "satisfied": verdict in ("MET", "NOT_APPLICABLE_BY_CONDITION_TEXT"),
    }


IDS = ["S3-C1", "S3-C2", "S3-C3", "S3-C4", "S3-C5", "S3-C6", "S3-C7"]


def candidate(name, verdicts):
    conditions = [cond(cid, verdicts[i]) for i, cid in enumerate(IDS)]
    return {
        "experiment_id": name,
        "family": "f",
        "admitted": all(c["satisfied"] for c in conditions),
        "conditions": conditions,
        "conditions_met": sum(1 for c in conditions if c["verdict"] == "MET"),
        "conditions_not_met": [c["id"] for c in conditions if c["verdict"] == "NOT_MET"],
        "conditions_not_evaluable": [c["id"] for c in conditions if c["verdict"] == "NOT_EVALUABLE"],
        "conditions_not_applicable": [
            c["id"] for c in conditions if c["verdict"] == "NOT_APPLICABLE_BY_CONDITION_TEXT"
        ],
    }


NA = "NOT_APPLICABLE_BY_CONDITION_TEXT"
# The exact Attempt 1 defect: S3-C6 is NOT_APPLICABLE for the two single-instrument candidates and
# MET for nobody. Aggregating on verdict == MET yields a false FAIL for that row.
fake = [
    candidate("C1", ["MET", "MET", "MET", "MET", "MET", NA, "NOT_MET"]),
    candidate("C2", ["NOT_MET", "MET", "MET", "MET", "MET", NA, "NOT_EVALUABLE"]),
    candidate("C3", ["MET", "NOT_MET", "MET", "MET", "MET", "NOT_EVALUABLE", "MET"]),
]
rows = H.condition_rollup(fake)
for row in rows:
    print(
        f"  {row['id']}: satisfied_by_at_least_one={row['satisfied_by_at_least_one_candidate']}"
        f"  met_by={row['met_by']} not_met_by={row['not_met_by']}"
        f" not_applicable_for={row['not_applicable_for']}"
    )
c6 = [r for r in rows if r["id"] == "S3-C6"][0]
assert c6["met_by"] == [], c6
assert c6["not_applicable_for"] == ["C1", "C2"], c6
assert c6["not_met_by"] == ["C3"], c6
assert c6["satisfied_by_at_least_one_candidate"] is True, "the Attempt 1 false-FAIL defect returned"
print("  S3-C6 satisfied via NOT_APPLICABLE only -> the recorded Attempt 1 defect is not present")
assert [r["id"] for r in rows] == IDS

print()
print("== decisive row + coherence guards ==")
from stockedge100.strategies import gate as G

stage = G.stage_verdict(fake, config.criteria)
print("  verdict         ", stage["verdict"])
print("  condition_token ", stage["condition_token"])
print("  pass/fail tokens", stage["pass_token"], "|", stage["fail_token"])
row = H.decisive_row(stage, config.binding)
print("  decisive value  ", row["value"], " admitted:", row["admitted_candidates"])
print("  decides_the_gate", row["decides_the_gate"])
print("  verdict token   ", row["gate_verdict_token"])
assert row["value"] is False and stage["verdict"] == "FAIL"
assert row["gate_verdict_token"] == stage["fail_token"]
H._refuse_incoherent(stage, fake, config.binding)
print("  _refuse_incoherent accepted the coherent FAIL set")

# all-satisfied candidate -> PASS, must also be accepted
allgood = [candidate("C1", ["MET", "MET", "MET", "MET", "MET", NA, "MET"])]
s2 = G.stage_verdict(allgood, config.criteria)
H._refuse_incoherent(s2, allgood, config.binding)
row2 = H.decisive_row(s2, config.binding)
print("  _refuse_incoherent accepted the coherent PASS set; token:", row2["gate_verdict_token"])
assert row2["gate_verdict_token"] == s2["pass_token"]
assert row2["gate_verdict_token"] != s2["fail_token"]

for label, bad_stage, bad_results in (
    ("PASS with zero admitted", {**stage, "verdict": "PASS"}, fake),
    ("FAIL with an admitted candidate", {**s2, "verdict": "FAIL"}, allgood),
):
    try:
        H._refuse_incoherent(bad_stage, bad_results, config.binding)
    except ConfigViolation as exc:
        print(f"  refused {label}: {str(exc)[:90]}")
    else:
        raise SystemExit(f"NOT REFUSED: {label}")

# admitted flag flipped on while a condition is unsatisfied
tampered = json.loads(json.dumps(fake))
tampered[1]["admitted"] = True
try:
    H._refuse_incoherent({**stage, "verdict": "PASS", "admitted_candidates": ["C2"]}, tampered, config.binding)
except ConfigViolation as exc:
    print("  refused admitted-with-unsatisfied:", str(exc)[:110])
else:
    raise SystemExit("NOT REFUSED: admitted with unsatisfied conditions")

# admitted flag flipped off while everything is satisfied
tampered2 = json.loads(json.dumps(allgood))
tampered2[0]["admitted"] = False
try:
    H._refuse_incoherent(
        {**s2, "verdict": "FAIL", "admitted_candidates": []}, tampered2, config.binding
    )
except ConfigViolation as exc:
    print("  refused not-admitted-with-all-satisfied:", str(exc)[:110])
else:
    raise SystemExit("NOT REFUSED: not admitted with all satisfied")

# satisfied flag tampered away from the sealed definition
tampered3 = json.loads(json.dumps(fake))
tampered3[1]["conditions"][6]["satisfied"] = True
try:
    H._refuse_incoherent(stage, tampered3, config.binding)
except ConfigViolation as exc:
    print("  refused tampered satisfied flag:", str(exc)[:120])
else:
    raise SystemExit("NOT REFUSED: satisfied flag disagreeing with the sealed definition")

print()
print("== rollup refuses a candidate missing a condition ==")
missing = json.loads(json.dumps(fake))
del missing[2]["conditions"][3]
try:
    H.condition_rollup(missing)
except ConfigViolation as exc:
    print("  refused:", str(exc)[:120])
else:
    raise SystemExit("NOT REFUSED: candidate missing a sealed condition")

print()
print("SMOKE OK - no evaluation was executed")
