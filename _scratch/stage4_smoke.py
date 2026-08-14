"""Import-test the two Stage 4 modules and drive the gate with synthetic evidence only.

No dataset is loaded and no validation observation is read: every number below is invented, which is
the point. This is the §6 "test pass and fail token derivations using synthetic evidence" check in
throwaway form, before the real tests are written.

ASCII-only output: the console is cp1252.
"""
import json
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.errors import ConfigViolation  # noqa: E402
from stockedge100.strategies import stage4_evaluation as ev  # noqa: E402
from stockedge100.strategies import stage4_gate as g  # noqa: E402


def out(text):
    sys.stdout.write(str(text).encode("ascii", "backslashreplace").decode("ascii") + "\n")


CRIT = json.loads((ROOT / "config/stage4_gate_criteria.json").read_text(encoding="utf-8"))

out("both modules imported")
out("")

out("== threshold cross-check (predicate literal vs JSON companion) ==")
checked = g.check_thresholds_against_seal(CRIT)
for cid in g.CONDITION_IDS:
    row = checked[cid]
    out("  %-7s literal=%-6s companion %-36s agrees=%s" % (
        cid, row["predicate_literal"], "%s=%s" % (row["companion_key"], row["companion_value"]),
        row["agrees"]))
out("")


def base(**kw):
    d = dict(
        scenario="BASE", equity_points=755, reached_window_end=True,
        starting_equity="100.00", final_equity="130.00",
        total_return=Decimal("0.30"), sharpe=Decimal("0.60"),
        max_drawdown=Decimal("0.10"), shutdown_session=None, shutdown_fraction=None,
        max_drawdown_basis="session close", daily_returns=754,
        closed_trades=40, profit_factor=Decimal("1.20"),
        gross_profit="60.00", gross_loss="50.00",
    )
    d.update(kw)
    return d


def stress(**kw):
    d = dict(scenario="STRESSED", equity_points=755, reached_window_end=True,
             total_return=Decimal("0.10"), stress_multiplier="2.0", shutdown_enforced=True)
    d.update(kw)
    return d


def folds(positive=12, completed=12):
    rows = []
    for i in range(1, 13):
        rows.append({"fold": i, "completed": i <= completed, "positive": i <= positive})
    return rows


def invariance(**kw):
    d = dict(all_digests_equal=True, digests_equal=13, digests_total=13, digest_rows=[],
             validation_evaluation_run_records=1, validation_window_engine_runs=2,
             declared_run_count=2, parameters_unchanged=True, parameter_comparison={},
             strategy_invariance={}, conflict_note="S4-CONFLICT-6")
    d.update(kw)
    return d


def run(tag, **kw):
    args = dict(representative="SE100-S3A2-C2-MEANREV-RA1", base=base(), stress=stress(),
                folds=folds(), invariance=invariance())
    args.update(kw)
    try:
        r = g.evaluate_gate4(CRIT, **args)
    except ConfigViolation as exc:
        out("  %-46s REFUSED  %s" % (tag, str(exc).splitlines()[0][:70]))
        return
    rows = " ".join("%s=%s" % (c["id"], c["verdict"][:4]) for c in r["conditions"])
    out("  %-46s %-5s %s" % (tag, "PASS" if r["gate_passed"] else "FAIL", r["verdict_token"]))
    out("       %s" % rows)


out("== synthetic evidence -> verdict token ==")
run("all seven MET")
run("C1 return exactly zero (strict)", base=base(total_return=Decimal("0")))
run("C2 sharpe exactly 0.50 (inclusive)", base=base(sharpe=Decimal("0.50")))
run("C2 sharpe 0.4999...", base=base(sharpe=Decimal("0.4999999999999999")))
run("C3 drawdown exactly 0.15 (inclusive)", base=base(max_drawdown=Decimal("0.15")))
run("C3 drawdown 0.150000000000001", base=base(max_drawdown=Decimal("0.150000000000001")))
run("C4 pf exactly 1.15 (inclusive)", base=base(profit_factor=Decimal("1.15")))
run("C4 pf 1.1499999", base=base(profit_factor=Decimal("1.1499999")))
run("C4 zero closed trades", base=base(closed_trades=0))
run("C4 zero gross loss -> undefined", base=base(profit_factor=None, gross_loss="0.00"))
run("C5 stressed return exactly zero", stress=stress(total_return=Decimal("0")))
run("C5 stressed run missing", stress={})
run("C6 nine of twelve positive (8.4 boundary)", folds=folds(positive=9))
run("C6 eight of twelve positive", folds=folds(positive=8))
run("C6 eleven completed -> NOT_EVALUABLE", folds=folds(positive=11, completed=11))
run("C2 sharpe undefined", base=base(sharpe=None))
run("C1 did not reach window end", base=base(reached_window_end=False))
run("C7 a digest changed", invariance=invariance(all_digests_equal=False))
run("C7 two validation run records", invariance=invariance(validation_evaluation_run_records=2))
run("C7 three engine runs", invariance=invariance(validation_window_engine_runs=3))
run("C7 a parameter differs", invariance=invariance(parameters_unchanged=False))
out("")

out("== sealed config load (no dataset) ==")
cfg = ev.load_stage4_config()
out("  representative        %s" % cfg.sealed_representative["experiment_id"])
out("  declared universe     %s" % list(cfg.declared_universe))
out("  warmup sessions       %s" % cfg.warmup_sessions)
out("  declared run count    %s" % cfg.declared_run_count)
out("  run labels            %s" % list(cfg.run_labels))
out("  digests verified      %d" % len(cfg.digests))
out("  strategy module (13th) %s" % cfg.strategy_module_rel)
out("  stress multiplier     %s" % cfg.stress_multiplier)
out("  verdict tokens        %s / %s" % (cfg.verdict_tokens["pass_token"],
                                         cfg.verdict_tokens["fail_token"]))
out("")

out("== 13-artifact recheck ==")
rows = ev.recheck_table(cfg)
out("  rows=%d  all equal=%s" % (len(rows), all(r["equal"] for r in rows)))
for r in rows:
    if not r["equal"]:
        out("    MISMATCH %s" % r["artifact"])
out("")

out("== strategy invariance vs Gate 3 ==")
inv = ev.strategy_invariance(cfg)
for k, v in inv.items():
    if k in ("parameters_json", "gate_3_parameters_json"):
        continue
    out("  %-34s %s" % (k, json.dumps(v)[:90]))
out("")

out("== sealed folds ==")
fs = ev.sealed_folds(cfg)
out("  count=%d  first=%s..%s  last=%s..%s" % (
    len(fs), fs[0].start, fs[0].end, fs[-1].start, fs[-1].end))
out("")

out("== windows ==")
out("  validation %s" % (ev.validation_window(),))
out("  holdout    %s" % (ev.holdout_window(),))
