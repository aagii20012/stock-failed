"""Smoke-test the Generation 2 cost derivation. ASCII output only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest import g2_costs  # noqa: E402
from stockedge100.backtest.costs import BASE, STRESSED  # noqa: E402
from stockedge100.backtest.errors import ConfigViolation  # noqa: E402


def main() -> int:
    print("permitted k:", g2_costs.permitted_position_counts())
    print("concentration ceiling:", g2_costs.concentration_ceiling())
    print()

    for k in g2_costs.permitted_position_counts():
        evidence = g2_costs.derivation_evidence(k)
        print(f"k={k}: leaves {evidence['sealed_leaf_count']} -> {evidence['derived_leaf_count']}, "
              f"diff {evidence['difference_set']}")

    print()
    for scenario in (BASE, STRESSED):
        costs = g2_costs.rotation_cost_model(3, scenario)
        print(scenario, json.dumps(costs.to_json()))
        print("   max_open_risky_positions:", costs.max_open_risky_positions,
              " starting_equity:", costs.starting_equity,
              " gross:", costs.max_gross_exposure_fraction,
              " cash floor:", costs.min_cash_buffer_fraction,
              " shutdown:", costs.research_shutdown_drawdown)

    print()
    for bad in (0, 4, "3"):
        try:
            g2_costs.rotation_cost_model(bad)
        except ConfigViolation as exc:
            print(f"  OK   k={bad!r} refused: {str(exc).splitlines()[0][:90]}")
        else:
            print(f"  FAIL k={bad!r} accepted")

    # A second difference must be refused, not absorbed.
    sealed = g2_costs.load_stage2_config().cost_model
    tampered = json.loads(json.dumps(sealed))
    tampered["account"]["max_open_risky_positions"] = 3
    tampered["frictions"]["half_spread_bps"] = "3.5"
    print("  tampered difference set:", g2_costs.difference_set(sealed, tampered))
    return 0


if __name__ == "__main__":
    sys.exit(main())
