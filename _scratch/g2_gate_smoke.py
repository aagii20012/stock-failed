"""Smoke-test the Generation 2 Gate 3 evaluator. ASCII output only.

Runs one variant plus its structural neighbours and evaluates all seven conditions. The figures
printed are machinery verification, not a result: the representative is chosen by the frozen
return-blind rule in a later step, and nothing here may influence it.
"""

from __future__ import annotations

import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import BASE  # noqa: E402
from stockedge100.backtest.g2_costs import rotation_cost_model  # noqa: E402
from stockedge100.backtest.g2_engine import RotationEngine  # noqa: E402
from stockedge100.strategies import g2_gate as gate  # noqa: E402
from stockedge100.strategies import g2_rotation as rot  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402

PRIMARY = sys.argv[1] if len(sys.argv) > 1 else "SE100-G2-S3-C1-ROTATION-L06-K2-MONTHLY"

_SERIES = None


def series():
    global _SERIES
    if _SERIES is None:
        loaded = guard.load_stage_3_dataset(rot.eligible_universe())
        guard.assert_series_within_bound(loaded)
        _SERIES = loaded
    return _SERIES


def run(variant):
    costs = rotation_cost_model(variant.top_k, BASE)
    candidate = rot.RotationCandidate(variant, costs)
    span = rot.load_protocol()["run_span"]
    engine = RotationEngine(
        series(),
        costs,
        guard.stage_3_window(),
        candidate,
        start=dt.date.fromisoformat(span["run_start"]),
        end=dt.date.fromisoformat(span["run_end"]),
        label=f"{variant.variant_id}#BASE",
        budget_weight=candidate.weight,
    )
    return engine.run()


def main() -> int:
    criteria = gate.load_criteria()
    print("criteria:", criteria["artifact_id"], "| gate:", criteria["gate_id"], criteria["gate_name"])
    print("carried over:", criteria["relationship_to_generation_1_criteria"]["carried_over_unchanged"])
    print("redefined   :", criteria["relationship_to_generation_1_criteria"]["redefined_for_generation_2"])

    plan = gate.build_plan()
    print()
    print("plan:", plan.experiment_id, "|", plan.family, "|", len(plan.declared_universe), "instruments",
          "|", plan.run_start, "->", plan.run_end, "| binding", plan.binding_symbol)

    print()
    print("=== neighbour sets, structural, for every grid position ===")
    counts = {}
    for variant in rot.rotation_variants():
        found = gate.neighbours_of(variant, criteria)
        expected = gate.expected_neighbour_count(variant, criteria)
        assert len(found) == expected, (variant.variant_id, len(found), expected)
        counts[len(found)] = counts.get(len(found), 0) + 1
        # symmetry: if B is a neighbour of A, A must be a neighbour of B
        for member in found:
            back = {m.variant_id for m in gate.neighbours_of(member, criteria)}
            assert variant.variant_id in back, (variant.variant_id, member.variant_id)
    print("  count histogram:", dict(sorted(counts.items())), "total edges/2:",
          sum(k * v for k, v in counts.items()) // 2)

    primary_variant = rot.variant_by_id(PRIMARY)
    neighbour_variants = gate.neighbours_of(primary_variant, criteria)
    print()
    print("  representative:", primary_variant.variant_id, "index", primary_variant.index)
    for member in neighbour_variants:
        print("    neighbour", member.index, member.variant_id)

    print()
    print("=== runs ===")
    primary = run(primary_variant)
    print(f"  {primary_variant.variant_id:48s} trades {len(primary.trades):3d} "
          f"return {primary.total_return():.6f}")
    neighbours = []
    for member in neighbour_variants:
        result = run(member)
        neighbours.append((member, result))
        print(f"  {member.variant_id:48s} trades {len(result.trades):3d} "
              f"return {result.total_return():.6f}")

    print()
    print("=== the seven conditions ===")
    evaluation = gate.evaluate_representative(
        variant=primary_variant, primary=primary, neighbours=neighbours, criteria=criteria
    )
    for entry in evaluation["conditions"]:
        print(f"  {entry['id']} {entry['verdict']:32s} measured={entry['measured']} "
              f"threshold={entry['threshold']}")
    print("  admitted:", evaluation["admitted"])
    print("  not met :", evaluation["conditions_not_met"])

    c5 = [e for e in evaluation["conditions"] if e["id"] == "S3-C5"][0]["evidence"]
    if "reconstructed_total_return" in c5:
        print()
        print("=== S3-C5 disclosure (sealed requirement) ===")
        print("  reconstructed      ", c5["reconstructed_total_return"])
        print("  equity-curve       ", c5["equity_curve_total_return"])
        print("  gap                ", c5["reconstruction_gap"])
        print("  distinct bases     ", c5["distinct_entry_equity_bases"], "over", c5["closed_trades"], "trades")
        print("  j1", c5["j1_largest_equity_multiple"]["symbol"],
              c5["j1_largest_equity_multiple"]["entry_session"],
              "mult", c5["j1_largest_equity_multiple"]["multiple"],
              "-> removed", c5["j1_largest_equity_multiple"]["removed_return"])
        print("  j2", c5["j2_largest_absolute_pnl"]["symbol"],
              c5["j2_largest_absolute_pnl"]["entry_session"],
              "pnl", c5["j2_largest_absolute_pnl"]["pnl"],
              "-> removed", c5["j2_largest_absolute_pnl"]["removed_return"])
        print("  j1 == j2:", c5["j1_equals_j2"])

    c6 = [e for e in evaluation["conditions"] if e["id"] == "S3-C6"][0]
    print()
    print("=== S3-C6 concentration ===")
    print("  largest contributor:", c6["evidence"].get("largest_contributor"), c6["measured"])

    print()
    print("=== stage verdict, both routes ===")
    for exists, results in ((True, [evaluation]), (False, [])):
        verdict = gate.stage_verdict_g2(
            results, criteria, representative_exists=exists,
            selection_note="smoke test" if exists else "no variant had zero shutdowns",
        )
        print(f"  representative_exists={exists}: {verdict['verdict']} - {verdict['verdict_token']} "
              f"(route {verdict['route']})")

    print()
    print("=== refusals ===")
    try:
        gate.condition_7_g2(primary, neighbours[:2], criteria, variant=primary_variant)
    except Exception as exc:
        print("  hand-picked neighbour subset:", type(exc).__name__, str(exc)[:90])
    try:
        gate.stage_verdict_g2([evaluation], criteria, representative_exists=False, selection_note="x")
    except Exception as exc:
        print("  admitted with no representative:", type(exc).__name__, str(exc)[:90])
    return 0


if __name__ == "__main__":
    sys.exit(main())
