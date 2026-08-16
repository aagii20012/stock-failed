"""Check every key the Attempt 2 evidence module reads, without rerunning the six-minute grid.

The grid run already wrote its outputs to reports/stage3_g2_attempt2/, so the row shape, the
selection record and the gate record can all be checked against real data on disk. The sealed
protocol and criteria are read directly. ASCII output only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.reporting import g2_stage3_attempt2_evidence as E  # noqa: E402
from stockedge100.strategies import g2_runner_ra1 as R  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402
from stockedge100.strategies.g2_gate_ra1 import load_criteria  # noqa: E402
from stockedge100.backtest.g2_engine_ra1 import load_risk_architecture  # noqa: E402

OUT = ROOT / "reports" / "stage3_g2_attempt2"
failures: list[str] = []


def check(label: str, fn):
    try:
        value = fn()
    except Exception as exc:  # noqa: BLE001 - this script exists to report them
        failures.append("%s -> %s: %s" % (label, type(exc).__name__, exc))
        print("  FAIL %-58s %s: %s" % (label, type(exc).__name__, exc))
        return None
    shown = repr(value)
    if len(shown) > 70:
        shown = shown[:67] + "..."
    print("  ok   %-58s %s" % (label, shown))
    return value


print("== protocol keys the evidence module reads ==")
protocol = R.load_protocol()
criteria = load_criteria()

for key in (
    "generation_id", "attempt", "strategy_id", "candidate_index", "family", "hypothesis",
    "what_this_attempt_adds_over_attempt_1", "adaptation_disclosure_verbatim",
    "adaptation_disclosure_carriage_requirement", "attempt_1_ref", "artifact_id",
    "declared_before_any_strategy_code", "declared_before_any_strategy_code_measurement",
    "run_span", "eligible_universe", "risk_architecture", "grid", "runs_per_variant",
    "reproducibility_requirements", "reported_for_every_variant_but_not_gating",
    "multiple_comparisons_disclosure", "representative_selection_rule", "gate_evaluation_scope",
    "structural_consequences_declared_before_running", "explicit_non_authorizations",
):
    check("protocol[%r]" % key, lambda k=key: type(protocol[k]).__name__)

print()
print("== nested protocol keys ==")
check("carriage.must_appear_verbatim_in",
      lambda: len(protocol["adaptation_disclosure_carriage_requirement"]["must_appear_verbatim_in"]))
check("carriage.enforcement",
      lambda: len(protocol["adaptation_disclosure_carriage_requirement"]["enforcement"]))
check("carriage.encoding_note",
      lambda: len(protocol["adaptation_disclosure_carriage_requirement"]["encoding_note"]))
for key in ("universe_version", "universe_identity_sha256", "member_count", "members",
            "unchanged_from_attempt_1", "eligibility_recheck_convention", "excluded_symbols"):
    check("eligible_universe[%r]" % key,
          lambda k=key: type(protocol["eligible_universe"][k]).__name__)
for key in ("frozen_before_any_variant_is_run", "not_part_of_the_grid"):
    check("risk_architecture[%r]" % key, lambda k=key: protocol["risk_architecture"][k])
check("grid['axes']", lambda: type(protocol["grid"]["axes"]).__name__)
check("grid['size']", lambda: protocol["grid"]["size"])
check("runs_per_variant['total_runs']", lambda: protocol["runs_per_variant"]["total_runs"])
check("reproducibility_requirements['determinism']",
      lambda: type(protocol["reproducibility_requirements"]["determinism"]).__name__)
check("criteria['artifact_id']", lambda: criteria["artifact_id"])

print()
print("== sealed input paths exist ==")
for rel in (E.PROTOCOL_REL, E.CRITERIA_REL, E.COST_MODEL_REL, E.PARTITION_LOCK_REL,
            E.CHARTER_REL, E.GOVERNANCE_PROTOCOL_REL, E.GOVERNANCE_PROTOCOL_MD_REL):
    check(rel, lambda r=rel: (ROOT / r).exists() or (_ for _ in ()).throw(
        FileNotFoundError(r)))

print()
print("== carriage requirement accepts this module's output path ==")
check("EVIDENCE_REL in must_appear_verbatim_in",
      lambda: E.EVIDENCE_REL in protocol["adaptation_disclosure_carriage_requirement"][
          "must_appear_verbatim_in"])
carriage = check("carried_disclosure(protocol)", lambda: E.carried_disclosure(protocol)[1])
if carriage:
    print("       chars=%s sha256=%s" % (carriage["characters"], carriage["sha256_of_utf8"]))

print()
print("== window guard surface ==")
check("guard.stage_3_window().name", lambda: guard.stage_3_window().name)
check("guard.development_bound()", lambda: guard.development_bound().isoformat())
check("guard.WindowViolation", lambda: guard.WindowViolation.__name__)
check("load_risk_architecture(protocol).to_json() keys",
      lambda: sorted(load_risk_architecture(protocol).to_json()))

print()
print("== grid row shape, from the run already on disk ==")
rows = json.loads((OUT / "grid_results.json").read_text(encoding="utf-8"))
print("  rows on disk:", len(rows))
row_keys = set(rows[0])
needed = set(E.RUN_IDENTITY_FIELDS) | set(E._PER_RUN_COLUMNS) | {
    "variant_id", "label", "grid_index", "lookback_months", "top_k", "rebalance_frequency",
    "research_shutdown_events", "reconciliation_single_leg_compared",
    "reconciliation_mismatches", "reconciliation_vacuous",
}
missing = sorted(needed - row_keys)
if missing:
    failures.append("grid_report rows are missing: %r" % missing)
    print("  FAIL missing row keys:", missing)
else:
    print("  ok   all %d referenced row keys present" % len(needed))
print("  unused row keys (reported by grid_report, not lifted into the table):")
for key in sorted(row_keys - needed):
    print("     -", key)

print()
print("== reported_only_extras against two real runs ==")
# Two real runs, not the whole grid: enough to prove the extras path resolves before the six-minute
# build spends its time. The variant chosen is the first in grid order, not the representative.
series = R.load_grid_dataset()
variants = R.rotation_variants()
one = variants[0]
live = [R.run_one(one, label, series, protocol=protocol) for label in R.run_labels()]
print("  runs:", [run.run_id for run in live])
extras = check("reported_only_extras(runs, criteria)",
               lambda: E.reported_only_extras(live, criteria))
if extras:
    for run_id, payload in extras.items():
        btr = payload["best_trade_removed_return"]
        print("    %s btr=%s verdict=%s stop_exits=%d" % (
            run_id, btr["measured"], btr["verdict"], len(payload["stop_exits"])))
        if payload["stop_exits"]:
            print("      first stop exit keys:", sorted(payload["stop_exits"][0]))
    json.dumps(extras)  # must be JSON-native: the evidence dumps with no default=
    print("  ok   extras are JSON-native")

print()
print("== variant_table / _by_run_id / _run_digests against the real rows ==")
# The 36 rows on disk with synthetic extras of the right shape, so the coverage check is exercised
# over all eighteen variants rather than only the two just run.
shape = {col: None for col in E._PER_RUN_EXTRA_COLUMNS}
all_extras = {"%s%s" % (r["variant_id"], r["label"]): dict(shape) for r in rows}
all_extras.update(extras or {})
table = check("variant_table(rows, extras)", lambda: E.variant_table(rows, all_extras))
if table:
    print("       variants=%d columns=%d" % (len(table), len(table[0])))
    print("       shutdowns:", sorted({r["research_shutdown_events"] for r in table}))
    print("       first:", table[0]["variant_id"], table[0]["base_total_return"])
check("REPORTED_COVERAGE length matches the seal",
      lambda: (len(E.REPORTED_COVERAGE),
               len(protocol["reported_for_every_variant_but_not_gating"])))
sealed = list(protocol["reported_for_every_variant_but_not_gating"])
mismatch = [q for q, _ in E.REPORTED_COVERAGE if q not in sealed]
if mismatch:
    failures.append("REPORTED_COVERAGE quantities absent from the seal: %r" % mismatch)
    print("  FAIL coverage quantities not sealed verbatim:", mismatch)
else:
    print("  ok   all %d coverage quantities are the sealed strings verbatim" % len(sealed))
by_id = check("_by_run_id(rows)", lambda: len(E._by_run_id(rows)))
check("_run_digests(rows[0])", lambda: sorted(E._run_digests(rows[0])))

print()
print("== _combine_base_and_stress against the gate record on disk ==")
gate_record = json.loads((OUT / "gate_record.json").read_text(encoding="utf-8"))
scope = dict(gate_record["gate_inputs"])
scope["scope_resolution"] = scope.pop("scope_resolution")
combined = check(
    "_combine_base_and_stress(...)",
    lambda: E._combine_base_and_stress(
        gate_record["base_evaluation"], gate_record["stress_evaluation"], scope),
)
if combined:
    basis = combined["admission_basis"]
    print("       admitted:", combined["admitted"])
    print("       base not satisfied:", basis["base_conditions_not_satisfied"])
    print("       stress not satisfied:", basis["stress_conditions_not_satisfied"])
    print("       matches driver:",
          combined["admitted"] == gate_record["combined"]["admitted"])

print()
print("== selection record keys ==")
selection = json.loads((OUT / "selection_record.json").read_text(encoding="utf-8"))
for key in ("representative_exists", "representative_variant_id", "decided_at_step",
            "selection_note"):
    check("selection[%r]" % key, lambda k=key: selection[k])

print()
if failures:
    print("FAILURES (%d):" % len(failures))
    for line in failures:
        print("  -", line)
    raise SystemExit(1)
print("all key accesses resolved")
