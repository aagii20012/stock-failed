"""Pull the per-candidate Gate 3 numbers out of the written evidence.

Nothing here is part of the repository state.
"""

import json
from pathlib import Path

ROOT = Path(r"d:\Product\stock-trade-alpaca\stockedge100")
EVIDENCE = ROOT / "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json"
body = json.loads(EVIDENCE.read_text(encoding="utf-8"))

FIELDS = (
    "total_return", "max_drawdown", "profit_factor", "closed_trades", "shutdown_session",
    "final_equity", "cagr", "sharpe", "exposure_fraction", "win_rate", "fills", "rejections",
    "stale_marks", "longest_flat_streak_sessions", "deepest_drawdown_4dp",
)

for cand in body["candidates"]:
    plan = cand["plan"]
    print("=" * 90)
    print(plan["experiment_id"], "|", plan["family"], "| universe", plan["declared_universe"])
    print("  run", plan["run_start"], "->", plan["run_end"],
          "| warmup", plan["declared_warmup_sessions"],
          "| lookback", plan["largest_lookback_across_primary_and_neighbours"],
          "| binding", plan["run_start_binding_symbol"])
    print("  admitted:", cand["gate"]["admitted"])
    print("\n  -- variant metrics --")
    for vid, run in cand["runs"].items():
        short = vid.split("#", 1)[1]
        print(f"    {short:<12} {run['role']:<9} gating={run['gating']} "
              f"ret={run['total_return']:<12} dd={run['deepest_drawdown_4dp']:<8} "
              f"pf={str(run['profit_factor'])[:8]:<8} trades={run['closed_trades']:<5} "
              f"shutdown={run['shutdown_session']}")
    primary = cand["runs"][f"{plan['experiment_id']}#PRIMARY"]
    print("\n  -- primary detail --")
    for f in FIELDS:
        print(f"    {f}: {primary[f]}")
    print("    ra1_diagnostics:", json.dumps(primary["ra1_diagnostics"]))
    print("\n  -- conditions --")
    for cond in cand["gate"]["conditions"]:
        print(f"    {cond['id']}  {cond['verdict']}  satisfied={cond.get('satisfied')}")
        for k in ("measured", "threshold", "comparison", "boundary"):
            if k in cond:
                print(f"        {k}: {cond[k]}")
        print(f"        evidence: {str(cond.get('evidence',''))[:500]}")
    print("\n  -- stressed cost run (non-gating) --")
    s = cand["stressed_cost_run"]
    for k in ("stress_multiplier", "base_total_return", "stressed_total_return",
              "base_max_drawdown", "stressed_max_drawdown", "base_closed_trades",
              "stressed_closed_trades", "base_shutdown_session", "stressed_shutdown_session",
              "flags"):
        print(f"    {k}: {s[k]}")
    print("\n  -- benchmarks (non-gating) --")
    for k, v in cand["benchmarks"].items():
        if k not in ("note", "gating", "window"):
            print(f"    {k}: {json.dumps(v)[:220]}")
    print("  benchmark_comparison:", json.dumps(cand["benchmark_comparison"])[:600])
    print()
