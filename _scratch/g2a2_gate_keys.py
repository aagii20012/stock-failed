"""Read-only: does every key and symbol g2_gate_ra1 reaches actually exist?

Written before the module is imported for real. A KeyError discovered during the grid run would
cost the whole run; a KeyError discovered after the decision package is built cannot be repaired
without invalidating the digest that package recorded.
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(ROOT / "src"))

fail = []


def check(label, ok, detail=""):
    print("%-58s %s %s" % (label, "ok " if ok else "FAIL", detail))
    if not ok:
        fail.append(label)


crit = json.loads((ROOT / "config" / "generation_2" / "g2_gate_criteria_ra1.json").read_text(encoding="utf-8"))
conds = {c["id"]: c for c in crit["conditions"]}

# --- top level keys load_criteria() reads
for key in ("artifact_id", "generation", "stage", "attempt", "declared_before_any_strategy_code",
            "attempt_1_counterpart", "attempt_1_counterpart_sha256",
            "generation_1_counterpart", "generation_1_counterpart_sha256",
            "frozen_gate_json_companion_verbatim", "verdict_token_derivation",
            "relationship_to_generation_1_criteria", "relationship_to_attempt_1_criteria"):
    check("criteria[%r]" % key, key in crit)

th = crit["frozen_gate_json_companion_verbatim"]["thresholds"]
for key in ("net_return_positive", "max_drawdown_pct", "profit_factor_min", "closed_trades_min",
            "best_trade_removed_return_positive"):
    check("thresholds[%r]" % key, key in th, repr(th.get(key)))

dv = crit["verdict_token_derivation"]
for key in ("pass_token", "fail_token", "pass_condition", "fail_condition", "conjunctive_note",
            "constitutional_fail_result_equivalent", "token_naming_note",
            "attempt_1_tokens_are_not_available_here", "fail_is_a_deliverable"):
    check("verdict_token_derivation[%r]" % key, key in dv)

for key in ("carried_over_unchanged", "redefined_for_generation_2"):
    check("relationship_to_generation_1_criteria[%r]" % key,
          key in crit["relationship_to_generation_1_criteria"])
for key in ("measurement_basis_changed", "measurement_basis_unchanged"):
    check("relationship_to_attempt_1_criteria[%r]" % key,
          key in crit["relationship_to_attempt_1_criteria"])

# --- per condition keys
def sub(cid, path):
    node = conds[cid]
    for part in path:
        if not isinstance(node, dict) or part not in node:
            return False, "missing at %r" % part
        node = node[part]
    return True, type(node).__name__

for cid, path in [
    ("S3-C3", ("measurement",)),
    ("S3-C3", ("predicate",)),
    ("S3-C3", ("undefined_cases", "no_closed_episodes")),
    ("S3-C3", ("undefined_cases", "no_losing_episodes")),
    ("S3-C3", ("attempt_2_note",)),
    ("S3-C4", ("measurement",)),
    ("S3-C4", ("exception_invoked",)),
    ("S3-C4", ("exception_note",)),
    ("S3-C4", ("counting_identity",)),
    ("S3-C4", ("not_evaluable_treatment",)),
    ("S3-C5", ("measurement", "basis")),
    ("S3-C5", ("measurement", "procedure")),
    ("S3-C5", ("measurement", "which_trade_is_removed")),
    ("S3-C5", ("measurement", "tie_handling")),
    ("S3-C5", ("measurement", "relation_to_headline_return")),
    ("S3-C5", ("measurement", "disclosure_requirement")),
    ("S3-C5", ("predicate",)),
    ("S3-C5", ("not_evaluable_treatment",)),
    ("S3-C6", ("measurement",)),
    ("S3-C6", ("predicate",)),
    ("S3-C6", ("scope_interpretation", "applies_to")),
    ("S3-C6", ("scope_interpretation", "rationale")),
    ("S3-C6", ("scope_interpretation", "why_it_always_applies")),
    ("S3-C6", ("scope_interpretation", "single_instrument_treatment")),
    ("S3-C6", ("scope_interpretation", "attempt_2_significance")),
    ("S3-C7", ("measurement", "neighbour_definition")),
    ("S3-C7", ("measurement", "axis_orderings")),
    ("S3-C7", ("measurement", "one_step_note")),
    ("S3-C7", ("measurement", "neighbour_count")),
    ("S3-C7", ("measurement", "no_new_runs")),
    ("S3-C7", ("measurement", "risk_constants_have_no_neighbours")),
    ("S3-C7", ("measurement", "what_is_read")),
    ("S3-C7", ("predicate",)),
    ("S3-C7", ("selection_prohibition",)),
    ("S3-C7", ("not_evaluable_treatment",)),
]:
    ok, detail = sub(cid, path)
    check("%s.%s" % (cid, ".".join(path)), ok, detail)

# the one key I am least sure of: does S3-C6 carry why_the_basis_matters_here, and where?
print()
print("S3-C6 top-level keys: %s" % sorted(conds["S3-C6"]))
print("S3-C3 top-level keys: %s" % sorted(conds["S3-C3"]))
print("S3-C4 top-level keys: %s" % sorted(conds["S3-C4"]))
print("S3-C5 top-level keys: %s" % sorted(conds["S3-C5"]))
print("S3-C7 top-level keys: %s" % sorted(conds["S3-C7"]))
print()

# --- symbols the module imports
import importlib
for mod, names in [
    ("stockedge100.audit", ["sha256_file"]),
    ("stockedge100.backtest.config", ["PROJECT_ROOT"]),
    ("stockedge100.backtest.costs", ["ZERO", "exact"]),
    ("stockedge100.backtest.engine", ["BacktestResult"]),
    ("stockedge100.backtest.errors", ["ConfigViolation", "DataIntegrityHalt", "InvariantViolation"]),
    ("stockedge100.backtest.metrics", ["profit_factor"]),
    ("stockedge100.strategies.gate", ["CONCENTRATION_MAX", "MET", "NOT_APPLICABLE", "NOT_EVALUABLE",
                                      "NOT_MET", "ConditionVerdict", "_condition", "_sign",
                                      "_threshold", "check_thresholds_against_seal", "condition_1",
                                      "condition_2"]),
    ("stockedge100.strategies.runner", ["contribution_by_symbol", "trade_pnls"]),
    ("stockedge100.backtest.g2_episodes_ra1", ["CONFLICT_ID", "LEDGER_ID", "RECONCILED_FIELDS",
                                               "Episode", "EpisodeLedger", "build_episode_ledger"]),
    ("stockedge100.backtest.g2_engine_ra1", ["load_risk_architecture"]),
    ("stockedge100.strategies.g2_rotation_ra1", ["STRATEGY_ID", "RotationCandidateRA1",
                                                 "RotationVariantRA1", "eligible_universe",
                                                 "load_protocol", "rotation_variants"]),
]:
    m = importlib.import_module(mod)
    for name in names:
        check("%s.%s" % (mod.rsplit(".", 1)[-1], name), hasattr(m, name))

# --- attribute-level checks
from stockedge100.backtest.engine import BacktestResult
from stockedge100.backtest.g2_episodes_ra1 import EpisodeLedger, Episode
from stockedge100.backtest.g2_episodes_ra1 import Reconciliation
from stockedge100.strategies.gate import ConditionVerdict
from stockedge100.strategies.g2_rotation_ra1 import RotationVariantRA1, rotation_variants

import dataclasses


def has(cls, attr):
    """hasattr misses plain dataclass fields: a field without a default is never a class attribute."""
    if hasattr(cls, attr):
        return True
    if dataclasses.is_dataclass(cls):
        return attr in {f.name for f in dataclasses.fields(cls)}
    return False


for cls, attr in [
    (BacktestResult, "total_return"), (BacktestResult, "equity_curve"), (BacktestResult, "trades"),
    (BacktestResult, "starting_equity"), (BacktestResult, "open_positions"),
    (BacktestResult, "label"), (BacktestResult, "scenario"),
    (EpisodeLedger, "closed_episodes"), (EpisodeLedger, "open_episodes"), (EpisodeLedger, "pnls"),
    (EpisodeLedger, "pnl_by_symbol"), (EpisodeLedger, "reconciliation"),
    (Episode, "sale_leg_count"), (Episode, "single_leg"), (Episode, "pnl"),
    (Episode, "entry_session"), (Episode, "exit_session"), (Episode, "close_index"),
    (Reconciliation, "to_json"), (Reconciliation, "vacuous"), (Reconciliation, "counts_agree"),
    (Reconciliation, "reconciled"), (Reconciliation, "single_leg_compared"),
    (Reconciliation, "mismatches"), (Reconciliation, "multi_leg_episodes"),
    (Reconciliation, "total_trimmed_proceeds"), (Reconciliation, "pnl_discrepancy"),
    (ConditionVerdict, "to_json"), (ConditionVerdict, "satisfied"),
    (RotationVariantRA1, "frequency"), (RotationVariantRA1, "to_json"),
    (RotationVariantRA1, "index"), (RotationVariantRA1, "variant_id"),
    (RotationVariantRA1, "lookback_months"), (RotationVariantRA1, "top_k"),
]:
    check("%s.%s" % (cls.__name__, attr), has(cls, attr))

v = rotation_variants()[0]
check("RotationVariantRA1 is hashable/eq", v == rotation_variants()[0])
check("rotation_variants() size 18", len(rotation_variants()) == 18, str(len(rotation_variants())))

print()
print("FAILED: %d" % len(fail))
for name in fail:
    print("  - %s" % name)
