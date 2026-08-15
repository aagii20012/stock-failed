"""After a research shutdown, did the engine really stop buying? ASCII output only.

The stage verdict rests entirely on the shutdown count, so the shutdown's *effect* is worth
confirming from the fill stream rather than from the engine's own rejection counters. For a spread
of variants -- an early firing, a late one, and one of each breadth -- this prints every fill at or
after the shutdown session and asserts none of them is a BUY.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import g2_rotation as rot  # noqa: E402
from stockedge100.strategies import g2_runner as runner  # noqa: E402

PROBES = (
    "SE100-G2-S3-C1-ROTATION-L03-K3-MONTHLY",    # earliest firing, 2008-10-24
    "SE100-G2-S3-C1-ROTATION-L06-K1-MONTHLY",    # latest firing, 2020-03-12
    "SE100-G2-S3-C1-ROTATION-L03-K1-MONTHLY",    # highest turnover
    "SE100-G2-S3-C1-ROTATION-L12-K2-QUARTERLY",  # lowest turnover
)


def main() -> int:
    series = runner.load_grid_dataset()
    failures = 0
    for variant_id in PROBES:
        variant = rot.variant_by_id(variant_id)
        run = runner.run_one(variant, "#BASE", series)
        result = run.result
        fired = result.shutdown_session
        after = [r for r in result.fills if r.session >= fired] if fired else []
        buys_after = [r for r in after if r.fill.side == "BUY"]
        last = result.fills[-1].session if result.fills else None
        print(f"{variant_id}")
        print(f"   shutdown={fired}  fills={len(result.fills)}  last fill={last}")
        print(f"   fills at/after the shutdown session: {len(after)}")
        for one in after:
            print(f"      {one.session} {one.fill.side:4s} {one.fill.symbol}  ({one.order_id})")
        if buys_after:
            failures += 1
            print(f"   *** {len(buys_after)} BUY fills after the shutdown -- entries were NOT blocked")
        else:
            print("   OK: no BUY fill at or after the shutdown session")
        print()
    print(f"probes={len(PROBES)}  failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
