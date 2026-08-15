"""Compute the Generation 2 identity digest, ASCII output only.

The id is derived from artifacts that already exist on disk before any Generation 2 file is
written, so it can be recomputed by anyone and it cannot contain a digest of itself. The same
derivation is implemented in stockedge100.reporting.g2_partition_lock and is asserted by test.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def main() -> None:
    inputs = {
        "project": "StockEdge100",
        "generation": 2,
        "constitution_ref": "SE100-GOV-0001",
        "constitution_sha256": sha256_file(ROOT / "governance" / "STAGE_0_CONSTITUTION.md"),
        "universe_version": "SE100-U1-d4917c2f7f1cd834",
        "universe_sha256": sha256_file(ROOT / "governance" / "STAGE_1_UNIVERSE.json"),
        "cost_model_sha256": sha256_file(ROOT / "config" / "stage2_cost_model.json"),
        "generation_1_terminal_verdict": "FAIL - STAGE_4_STRATEGY_REJECTED_IN_VALIDATION",
        "single_variable_changed": "PORTFOLIO_BREADTH_AND_CROSS_SECTIONAL_SELECTION",
        "development_window": ["1993-01-29", "2021-07-31"],
        "validation_window": ["2021-08-01", "2024-07-31"],
        "holdout_window": ["2026-08-01", "2028-07-31"],
    }
    full = canonical(inputs)
    print("identity_inputs:")
    for key, value in inputs.items():
        print(f"  {key} = {value}")
    print()
    print(f"identity_sha256 = {full}")
    print(f"generation_id   = SE100-GEN2-{full[:16]}")


if __name__ == "__main__":
    main()
