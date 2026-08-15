"""Is the universal shutdown real, or is the trigger defective? ASCII output only.

Thirty-six runs out of thirty-six fired a research shutdown, and that verdict is the whole of the
stage. A rate that uniform is exactly what a defective trigger looks like -- so this checks the
claim from outside the engine:

  1. when did each run's shutdown fire, and where in the run span is that;
  2. what was the drawdown at that session, recomputed from the equity curve rather than read from
     the engine's own high-water mark;
  3. did the engine keep buying afterwards (it must not: the sealed action blocks entries);
  4. what does the same 15% rule do to plain buy-and-hold on the run span, for scale.

Item 4 is the control. If buy-and-hold also breaches 15% early in the span, a long-only equity
strategy firing the same trigger is a property of the window, not a bug.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import g2_runner as runner  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402

EVIDENCE = Path(__file__).resolve().parent / "g2_stage3_evidence.json"
THRESHOLD = Decimal("0.15")


def drawdown_path(curve):
    """Running peak-to-current drawdown, recomputed from the curve alone."""
    peak = None
    out = []
    for session, equity in curve:
        value = Decimal(str(equity))
        peak = value if peak is None or value > peak else peak
        out.append((session, value, (peak - value) / peak))
    return out


def main() -> int:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    span = payload["runs"][0]["variant"]
    print(f"run span sessions = {len(payload['runs'])} runs")

    print()
    print("== 1. when each shutdown fired ==")
    sessions_fired = {}
    for run in payload["runs"]:
        fired = run["shutdown_session"]
        sessions_fired.setdefault(fired, []).append(run["run_id"])
    for fired in sorted(sessions_fired, key=lambda s: (s is None, s)):
        ids = sessions_fired[fired]
        print(f"   {fired}  x{len(ids)}")
        for one in ids:
            print(f"      {one}")

    print()
    print("== 2. buy-and-hold control on the same span ==")
    series = runner.load_grid_dataset()
    start = dt.date.fromisoformat(payload["runs"][0]["variant"]["run_start"]) \
        if "run_start" in span else None
    protocol = runner.load_protocol()
    start = dt.date.fromisoformat(protocol["run_span"]["run_start"])
    end = dt.date.fromisoformat(protocol["run_span"]["run_end"])
    print(f"   span {start} -> {end}")
    for symbol in ("SPY", "IVV", "AGG", "TLT", "SHY"):
        one = series[symbol]
        rows = [(d, one.bars[d].close) for d in one.sessions if start <= d <= end]
        if not rows:
            print(f"   {symbol}: no bars in span")
            continue
        path = drawdown_path(rows)
        first_breach = next((s for s, _, dd in path if dd >= THRESHOLD), None)
        worst = max(dd for _, _, dd in path)
        print(
            f"   {symbol}: bars={len(rows)}  first 15% breach={first_breach}"
            f"  worst drawdown={worst:.4f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
