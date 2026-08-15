"""Stage 3 Generation 2: the thirty-six declared development runs. ASCII output only.

Order is load-bearing and matches the seal:

  1. load the development dataset through the Generation 2 window guard (twice-checked);
  2. run all thirty-six declared runs unconditionally -- none is conditional on another's outcome;
  3. project them to the return-blind ``SelectionInput`` records;
  4. apply the frozen three-step selection rule;
  5. only then evaluate Gate 3 on the selected representative;
  6. only then produce the descriptive eighteen-variant table.

Steps 5 and 6 come after step 4 by construction, not by convention: the selection is decided from
records that carry no performance figure at all, so no return in this file can reach it.

The evidence lands in ``_scratch/`` -- outside ``stockedge100/``, so running this perturbs no
``repo_state_id`` pattern. The decision package reads it from there.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import g2_gate as gate  # noqa: E402
from stockedge100.strategies import g2_runner as runner  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402

OUT = Path(__file__).resolve().parent / "g2_stage3_evidence.json"


def main() -> int:
    started = time.time()

    print("== 1. dataset ==")
    window = guard.stage_3_window()
    print(f"   window {window.name}: {window.start} -> {window.end}")
    series = runner.load_grid_dataset()
    spans = {s: (one.sessions[0], one.sessions[-1]) for s, one in series.items()}
    latest = max(end for _, end in spans.values())
    print(f"   symbols={len(series)}  latest session anywhere={latest}")
    bound = guard.development_bound()
    assert latest <= bound, "a bar past the development bound survived the load"

    print()
    print("== 2. thirty-six runs ==")

    def progress(done, total, run):
        print(
            f"   [{done:2d}/{total}] {run.variant.variant_id}{run.label}"
            f"  fills={run.fill_count:4d}  shutdown={int(run.shutdown_fired)}"
            f"  ret={run.measurement['total_return']}"
        )

    runs = runner.run_grid(series, progress=progress)
    print(f"   completed {len(runs)} runs in {time.time() - started:.1f}s")

    print()
    print("== 3. return-blind projection ==")
    inputs = runner.selection_inputs(runs)
    for entry in inputs:
        print(
            f"   {entry.variant_id}  shutdowns={entry.shutdown_events}"
            f"  fills={entry.fill_count}"
        )

    print()
    print("== 4. frozen selection rule ==")
    selection = runner.select_representative(inputs)
    print(f"   representative_exists={selection['representative_exists']}")
    print(f"   representative={selection['representative_variant_id']}")
    print(f"   decided_at_step={selection['decided_at_step']} by {selection['decided_by']}")
    print(f"   eligible={selection['step_1']['eligible_count']} of {len(inputs)}")
    print(f"   note: {selection['selection_note']}")

    print()
    print("== 5. gate 3 on the representative ==")
    criteria = gate.load_criteria()
    candidate_results = []
    gate_scope = None
    if selection["representative_exists"]:
        chosen = selection["representative_variant_id"]
        scope = runner.gate_inputs(runs, chosen, criteria=criteria)
        gate_scope = {
            "evaluated_on": scope["evaluated_on"],
            "stress_run_treatment": scope["stress_run_treatment"],
            "not_a_disjunction": scope["not_a_disjunction"],
            "neighbours": [member.variant_id for member, _ in scope["neighbours"]],
        }
        evaluation = gate.evaluate_representative(
            variant=scope["variant"],
            primary=scope["primary"],
            neighbours=scope["neighbours"],
            criteria=criteria,
        )
        candidate_results.append(evaluation)
        print(f"   neighbours={gate_scope['neighbours']}")
        for condition in evaluation["conditions"]:
            print(
                f"   {condition['id']:8s} {condition['verdict']:16s} "
                f"{condition.get('observed', '')}"
            )
        print(f"   admitted={evaluation['admitted']}")
    else:
        print("   not evaluated: no representative was selected")

    print()
    print("== 6. stage verdict ==")
    verdict = gate.stage_verdict_g2(
        candidate_results,
        criteria,
        representative_exists=selection["representative_exists"],
        selection_note=selection["selection_note"],
    )
    print(f"   {verdict['verdict']} -- {verdict['verdict_token']}")
    print(f"   route={verdict['route']}")

    print()
    print("== 7. descriptive grid table ==")
    report = runner.grid_report(runs)
    print(f"   {len(report)} rows")

    payload = {
        "stage": "stage_3_generation_2_rotation_development",
        "window": {"name": window.name, "start": str(window.start), "end": str(window.end)},
        "development_bound": str(bound),
        "latest_session_loaded": str(latest),
        "symbols_loaded": len(series),
        "runs": [run.to_json() for run in runs],
        "selection_inputs": [entry.to_json() for entry in inputs],
        "selection": selection,
        "gate_scope": gate_scope,
        "candidate_results": candidate_results,
        "verdict": verdict,
        "grid_report": report,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=False, default=str), encoding="utf-8")
    print()
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
