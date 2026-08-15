"""Smoke-test the Generation 2 grid runner and the return-blind selection. ASCII output only.

The selection logic is exercised on synthetic SelectionInput records, which is the point: the
chooser cannot see a return, so it does not need a real run to be tested. Two real runs go through
run_one to check the plumbing and to time the grid.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import g2_runner as runner  # noqa: E402
from stockedge100.strategies import g2_rotation as rot  # noqa: E402

SI = runner.SelectionInput


def synthetic(variant_id, base=(0, 10), stress=(0, 10)):
    per_run = (("#BASE", base[0], base[1]), ("#STRESS", stress[0], stress[1]))
    return SI(
        variant_id=variant_id,
        shutdown_events=base[0] + stress[0],
        fill_count=base[1] + stress[1],
        per_run=per_run,
    )


def show(title, inputs):
    record = runner.select_representative(inputs, require_full_grid=False)
    print(f"  {title}")
    print(f"    representative : {record['representative_variant_id']}")
    print(f"    decided_at_step: {record['decided_at_step']} ({record['decided_by']})")
    print(f"    note           : {record['selection_note'][:110]}")
    return record


def main() -> int:
    print("=== sealed run labels ===")
    labels = runner.run_labels()
    print("  labels:", labels)
    for label in labels:
        print(f"  {label:8s} -> cost scenario {runner.scenario_for_label(label)}")
    print("  gate label:", runner.GATE_RUN_LABEL)
    print("  return-blind fields:", runner.SELECTION_FIELD_NAMES)

    print()
    print("=== the sealed rule, on synthetic return-blind inputs ===")
    ids = [f"V{i:02d}" for i in range(1, 6)]

    # step 1 decides: exactly one variant clean
    show("step 1", [
        synthetic(ids[0], (0, 40), (0, 40)),
        synthetic(ids[1], (1, 10), (0, 10)),
        synthetic(ids[2], (0, 5), (1, 5)),
        synthetic(ids[3], (1, 2), (1, 2)),
    ])

    # step 2 decides: three clean, one strictly lowest fill count
    show("step 2", [
        synthetic(ids[0], (0, 40), (0, 40)),
        synthetic(ids[1], (0, 12), (0, 11)),
        synthetic(ids[2], (0, 30), (0, 30)),
        synthetic(ids[3], (1, 1), (0, 1)),
    ])

    # step 3 decides: two clean and tied on fills
    record = show("step 3", [
        synthetic(ids[2], (0, 9), (0, 9)),
        synthetic(ids[1], (0, 9), (0, 9)),
        synthetic(ids[0], (0, 50), (0, 50)),
    ])
    print("    tied           :", record["step_2"]["tied_at_lowest"])

    # no candidate: every variant shut down at least once
    record = show("no candidate", [
        synthetic(ids[0], (1, 4), (0, 4)),
        synthetic(ids[1], (0, 4), (1, 4)),
        synthetic(ids[2], (1, 4), (1, 4)),
    ])
    print("    verdict on the sealed path:", record["no_candidate_path"]["verdict"])
    print("    prohibition:", record["no_candidate_path"]["prohibition"][:100])

    print()
    print("=== the screen really does span BOTH runs ===")
    # clean base, dirty stress -> ineligible. A base-only screen would admit it.
    record = runner.select_representative(
        [synthetic(ids[0], (0, 2), (1, 2)), synthetic(ids[1], (0, 80), (0, 80))],
        require_full_grid=False,
    )
    print("  clean-base/dirty-stress variant eligible:",
          ids[0] in record["step_1"]["eligible"], "(must be False)")
    print("  representative:", record["representative_variant_id"], "(the higher-turnover clean one)")

    print()
    print("=== refusals ===")
    try:
        runner.select_representative([synthetic("V01")], require_full_grid=True)
    except Exception as exc:
        print("  partial grid            :", type(exc).__name__, str(exc)[:80])
    try:
        runner.select_representative(
            [synthetic("V01"), synthetic("V01")], require_full_grid=False
        )
    except Exception as exc:
        print("  duplicate variant       :", type(exc).__name__, str(exc)[:80])
    try:
        runner.run_one(rot.rotation_variants()[0], "#PAPER", {})
    except Exception as exc:
        print("  undeclared run label    :", type(exc).__name__, str(exc)[:80])
    try:
        runner.scenario_for_label("#S")
    except Exception as exc:
        print("  ambiguous label         :", type(exc).__name__, str(exc)[:80])

    print()
    print("=== two real runs, for plumbing and timing ===")
    series = runner.load_grid_dataset()
    variant = rot.rotation_variants()[0]
    runs = []
    for label in labels:
        started = time.time()
        run = runner.run_one(variant, label, series)
        elapsed = time.time() - started
        runs.append(run)
        print(f"  {run.run_id:56s} {elapsed:5.1f}s fills {run.fill_count:4d} "
              f"trades {run.measurement['closed_trades']:3d} shutdown {run.shutdown_fired}")
    per_run = sum(1 for _ in runs)
    print(f"  -> 36 runs at this rate ~ {36 * (time.time() - started) / 60:.0f} min (rough)")

    inputs = runner.selection_inputs(runs)
    print("  projection:", inputs[0].to_json())

    print()
    print("=== missing-run refusal (the screen needs both) ===")
    try:
        runner.selection_inputs(runs[:1])
    except Exception as exc:
        print("  one run only            :", type(exc).__name__, str(exc)[:100])

    print()
    print("=== gate_inputs refuses when the neighbours were not run ===")
    try:
        runner.gate_inputs(runs, variant.variant_id)
    except Exception as exc:
        print("  neighbours absent       :", type(exc).__name__, str(exc)[:80])

    print()
    print("=== grid_report row shape ===")
    row = runner.grid_report(runs)[0]
    print("  keys:", len(row))
    for key in ("variant_id", "label", "total_return", "max_drawdown", "profit_factor",
                "closed_trades", "research_shutdown_events", "fills", "distinct_symbols_traded"):
        print(f"    {key:26s} {row[key]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
