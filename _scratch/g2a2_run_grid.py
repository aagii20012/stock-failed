"""Generation 2 Stage 3 Attempt 2: drive the full 18-variant grid and the sealed evaluation.

Writes only into ``stockedge100/reports/stage3_g2_attempt2/``, which is outside every
``repo_state_id`` pattern, so running this perturbs no digest. ASCII output only (cp1252 console).

Order is the sealed one and nothing here reorders it:

  1. verify Attempt 1's nine modules are byte-unmoved (AT-H), and recheck the run span three ways;
  2. run all thirty-six declared runs;
  3. project to the return-blind selection inputs and apply the frozen three-step rule;
  4. only then assemble the gate inputs and evaluate the representative;
  5. emit the stage verdict, with its token read from the sealed derivation.

Step 3 precedes step 4 in code as well as in prose: no performance figure is computed into a
variable the selection can see before the selection has already happened.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies.g2_gate_ra1 import (  # noqa: E402
    evaluate_representative_ra1,
    load_criteria,
    stage_verdict_ra1,
)
from stockedge100.strategies.g2_rotation_ra1 import load_protocol  # noqa: E402
from stockedge100.strategies import g2_runner_ra1 as R  # noqa: E402

OUT = ROOT / "reports" / "stage3_g2_attempt2"
OUT.mkdir(parents=True, exist_ok=True)


def dump(name: str, payload) -> None:
    path = OUT / name
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print("  wrote %-34s %8d bytes" % (name, path.stat().st_size), flush=True)


started = time.time()
print("== 1. pre-run verification ==", flush=True)
protocol = load_protocol()
criteria = load_criteria()

modules = R.verify_attempt_1_modules()
print("  attempt 1 modules verified:", modules["module_count"],
      " moved:", modules["modules_that_moved"], flush=True)

series = R.load_grid_dataset()
span = R.recheck_run_span(series, protocol=protocol)
m = span["measured"]
print("  run span: %s -> %s  sessions=%s monthly=%s quarterly=%s binding=%s" % (
    m["run_start"], m["run_end"], m["run_sessions"], m["monthly_rebalance_sessions"],
    m["quarterly_rebalance_sessions"], m["binding_symbol"]), flush=True)
print("  differences:", span["differences"], flush=True)

# The seal's own list, read rather than remembered: max_gross_fraction_observed must be a
# reported-not-gating quantity, not something the gate or the selection may read.
reported = list(protocol["reported_for_every_variant_but_not_gating"])
print("  reported_but_not_gating entries:", len(reported), flush=True)
for entry in reported:
    print("     -", entry, flush=True)

dump("attempt_1_module_verification.json", modules)
dump("run_span_recheck.json", span)

print(flush=True)
print("== 2. the grid: 36 runs ==", flush=True)


def progress(done: int, total: int, run) -> None:
    metrics = run.measurement
    print("  [%2d/%2d] %-52s ret=%9s dd=%8s pf=%7s trades=%4s eps=%4s shutdown=%s  %.1fs" % (
        done, total, run.run_id, metrics["total_return"], metrics["max_drawdown"],
        metrics["profit_factor"], metrics["closed_trades"], len(run.ledger.closed_episodes),
        metrics["shutdown_session"], time.time() - started), flush=True)


runs = R.run_grid(series, progress=progress, verify=True)
print("  runs completed:", len(runs), flush=True)

rows = R.grid_report(runs)
dump("grid_results.json", rows)

print(flush=True)
print("== 3. the return-blind selection ==", flush=True)
inputs = R.selection_inputs(runs)
for entry in inputs:
    print("  %-46s shutdowns=%d fills=%5d  per_run=%s" % (
        entry.variant_id, entry.shutdown_events, entry.fill_count,
        [(lab, ev, fl) for lab, ev, fl in entry.per_run]), flush=True)

selection = R.select_representative(inputs)
dump("selection_inputs.json", [entry.to_json() for entry in inputs])
dump("selection_record.json", selection)
print("  representative:", selection["representative_variant_id"], flush=True)
print("  note:", selection["selection_note"], flush=True)

representative = selection["representative_variant_id"]
candidate_results: list[dict] = []
gate_payload = None

if representative:
    print(flush=True)
    print("== 4. the gate, under the G2A2-CONFLICT-25 restrictive resolution ==", flush=True)
    gi = R.gate_inputs(runs, representative, criteria=criteria)

    base_eval = evaluate_representative_ra1(
        variant=gi["variant"],
        primary=gi["primary"],
        neighbours=gi["neighbours"],
        criteria=criteria,
        ledger=gi["primary_run"].ledger,
    )
    stress_eval = evaluate_representative_ra1(
        variant=gi["variant"],
        primary=gi["stress"],
        neighbours=gi["neighbours"],
        criteria=criteria,
        ledger=gi["stress_run"].ledger,
    )

    # S3-C7 is evaluated once, on base runs. The stress evaluation computes it too -- the function
    # evaluates all seven -- but its stress-side answer compares a stress-run return against
    # base-run neighbours, a mixed basis the seal gives no authority for. It is recorded and not
    # used. Everything else on the stress side gates.
    stress_gating = [c for c in stress_eval["conditions"] if c["id"] != "S3-C7"]
    stress_reported_only = [c for c in stress_eval["conditions"] if c["id"] == "S3-C7"]
    assert len(stress_gating) == 6 and len(stress_reported_only) == 1, "condition ids moved"

    base_ok = base_eval["admitted"]
    stress_ok = all(c["satisfied"] for c in stress_gating)
    admitted = base_ok and stress_ok

    combined = dict(base_eval)
    combined["admitted"] = admitted
    combined["admission_basis"] = {
        "conflict_ref": gi["conflict_ref"],
        "resolution": gi["scope_resolution"],
        "evaluated_on": gi["evaluated_on"],
        "both_gate": gi["both_gate"],
        "base_all_seven_satisfied": base_ok,
        "stress_first_six_satisfied": stress_ok,
        "stress_conditions_not_satisfied": sorted(
            c["id"] for c in stress_gating if not c["satisfied"]
        ),
        "base_conditions_not_satisfied": sorted(
            c["id"] for c in base_eval["conditions"] if not c["satisfied"]
        ),
        "s3_c7_stress_side_reported_not_gating": stress_reported_only[0],
        "permissive_base_only_reading_would_give": base_ok,
    }
    combined["stress_evaluation"] = stress_eval
    candidate_results = [combined]
    gate_payload = {
        "gate_inputs": {
            key: gi[key]
            for key in ("evaluated_on", "conjunctive", "both_gate", "criteria_source",
                        "conflict_ref", "scope_resolution", "neighbour_run_label")
        },
        "representative_variant_id": representative,
        "neighbour_variant_ids": [v.variant_id for v, _ in gi["neighbours"]],
        "base_evaluation": base_eval,
        "stress_evaluation": stress_eval,
        "combined": combined,
    }
    dump("gate_record.json", gate_payload)

    for entry in base_eval["conditions"]:
        print("  BASE   %-8s %-22s satisfied=%s" % (
            entry["id"], entry["verdict"], entry["satisfied"]), flush=True)
    for entry in stress_eval["conditions"]:
        used = "gating" if entry["id"] != "S3-C7" else "reported-only"
        print("  STRESS %-8s %-22s satisfied=%s  (%s)" % (
            entry["id"], entry["verdict"], entry["satisfied"], used), flush=True)
    print("  admitted:", admitted, flush=True)
else:
    print(flush=True)
    print("== 4. no representative: the gate is not reached ==", flush=True)

print(flush=True)
print("== 5. the stage verdict ==", flush=True)
verdict = stage_verdict_ra1(
    candidate_results,
    criteria,
    representative_exists=bool(representative),
    selection_note=selection["selection_note"],
)
dump("stage_verdict.json", verdict)
print("  %s -- %s" % (verdict["verdict"], verdict["verdict_token"]), flush=True)
print("  route:", verdict["route"], flush=True)
print("  condition_token:", verdict["condition_token"], flush=True)
print(flush=True)
print("done in %.1fs" % (time.time() - started), flush=True)
