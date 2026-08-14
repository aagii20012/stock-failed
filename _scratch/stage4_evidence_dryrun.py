"""Drive stage4_evidence end to end against synthetic bars, writing nothing into the tree.

CLAUDE.md: "dry-run it before it writes anything." This module is the one piece that must be right
on first execution, because a crash cannot authorize a rerun -- the sealed remedy allows a
crash-and-restart inside one session on one load, but only because no result was extracted, and it
is far cheaper to find the defect here.

Every real path is exercised: the sealed config load, the thirteen-artifact recheck, the strategy
invariance comparison, the window arithmetic, both registered runs, the twelve folds, the runs/
record, the S4-C7 record count, the seven conditions and the digest seal. Only two things are
replaced: the dataset load, patched to synthetic bars carrying real session dates and invented
prices, and the two output directories, redirected under _scratch.

Two price scenarios, because they exercise different halves of the evidence layer:

  RISING       a monotonic ramp. The mean-reversion entry never fires, so the account never trades
               and the run exercises the zero-trade branches: profit factor undefined, Sharpe
               undefined on a constant equity series, twelve completed folds all returning zero.
  OSCILLATING  a sawtooth deep enough to cross the sealed entry band repeatedly, so trades close,
               gross profit and gross loss are non-zero, equity moves between folds and the fold
               baseline chaining is exercised on a series that is not flat.

The prices are invented, so the numbers printed below are meaningless as evidence and are not
evidence. What is being checked is that the plumbing produces a shaped, sealed, JSON-serialisable
artifact and a coherent gate, and that the refusal paths refuse.

ASCII-only output: the console is cp1252.
"""
import datetime as dt
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
SCRATCH = pathlib.Path(r"D:\Product\stock-trade-alpaca\_scratch\stage4_dryrun")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.dataset import series_from_rows  # noqa: E402
from stockedge100.data.calendar import sessions_between  # noqa: E402
from stockedge100.reporting import stage4_evidence as evmod  # noqa: E402
from stockedge100.strategies import stage4_evaluation as harness  # noqa: E402


def out(text):
    sys.stdout.write(str(text).encode("ascii", "backslashreplace").decode("ascii") + "\n")


FIRST = dt.date(2021, 1, 4)
LAST = dt.date(2024, 7, 31)
SESSIONS = sessions_between(FIRST, LAST)


def rising(index):
    return 100 + index


def oscillating(index):
    # A 40-session sawtooth with an 18 percent amplitude: deep enough to cross a mean-reversion
    # band in both directions many times over three and a half years, and drifting upward slowly so
    # the fold returns are not all the same sign.
    phase = index % 40
    swing = phase if phase < 20 else 40 - phase
    return 100 + index * 0.01 + swing * 0.9


def make_series(symbol, price_of):
    rows = []
    for index, session in enumerate(SESSIONS):
        close = round(price_of(index), 4)
        rows.append({
            "session": session.isoformat(), "open": str(close), "high": str(close),
            "low": str(close), "close": str(close), "adj_close": str(close),
            "volume": "1000000", "dividend": "0", "split_ratio": "1",
        })
    return series_from_rows(symbol, rows)


def reset():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    runs = SCRATCH / "runs"
    runs.mkdir(parents=True)
    harness.RUNS_DIR = runs
    evmod.RUNS_DIR = runs
    evmod.EVIDENCE_REL = "../_scratch/stage4_dryrun/EVIDENCE.json"
    return runs


def loader_for(price_of):
    def load(config):
        return {symbol: make_series(symbol, price_of)
                for symbol in sorted(set(config.declared_universe))}
    return load


# -- refusal paths ---------------------------------------------------------------------------------

runs = reset()
evmod.load_validation_series = loader_for(rising)

out("== refusal: a validation evaluation record already on disk ==")
(runs / "SE100-R-FAKE.json").write_text(
    json.dumps({"strategy_id": harness.REPRESENTATIVE}), encoding="utf-8")
out("  build() -> %s" % evmod.build())
out("  records now: %s" % sorted(p.name for p in runs.glob("*.json")))
out("")

runs = reset()
out("== refusal: the evidence file already exists ==")
target = pathlib.Path(evmod.PROJECT_ROOT / evmod.EVIDENCE_REL)
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text("{}", encoding="utf-8")
out("  build() -> %s" % evmod.build())
out("")

out("== run id collision cannot overwrite an append-only record ==")
first = evmod.unique_run_id()[0]
(runs / ("%s.json" % first)).write_text("{}", encoding="utf-8")
second = evmod.unique_run_id()[0]
out("  first=%s second=%s distinct=%s" % (first, second, first != second))
out("")


# -- the two scenarios -----------------------------------------------------------------------------


def scenario(name, price_of):
    runs = reset()
    evmod.load_validation_series = loader_for(price_of)
    target = pathlib.Path(evmod.PROJECT_ROOT / evmod.EVIDENCE_REL)

    out("=" * 90)
    out("== scenario %s ==" % name)
    code = evmod.build()
    out("  build() -> %s" % code)

    body = json.loads(target.read_text(encoding="utf-8"))
    out("")
    out("  top-level keys (%d)" % len(body))
    out("  digest recomputes     %s" % (evmod.evidence_digest(body) == body["evidence_digest"]))
    out("  serialises            %s" % isinstance(json.dumps(body), str))
    out("  records written       %s" % sorted(p.name for p in runs.glob("*.json")))

    record = json.loads(sorted(runs.glob("*.json"))[0].read_text(encoding="utf-8"))
    out("")
    out("  -- runs/ record --")
    for key in ("stage", "strategy_id", "holdout_state", "universe_version", "date_range",
                "exit_status", "random_seed"):
        out("    %-18s %s" % (key, json.dumps(record[key])[:80]))
    out("    %-18s %d entries" % ("code_hashes", len(record["code_hashes"])))
    out("    %-18s %s" % ("dataset_hashes", list(record["dataset_hashes"])))
    out("    %-18s %s" % ("output_artifacts", record["output_artifact_hashes"]))

    out("")
    out("  -- runs --")
    for entry in body["runs"]:
        m = entry["measure"]
        out("    %-46s" % entry["run_label"])
        out("      return=%s sharpe=%s dd=%s pf=%s trades=%s" % (
            m["total_return"], m["sharpe"], m["max_drawdown"], m["profit_factor"],
            m["closed_trades"]))
        out("      trades_digest=%s equity_digest=%s" % (
            m["trades_digest"][:16], m["equity_digest"][:16]))

    base = body["gate_evidence"]["base"]
    out("")
    out("  -- base evidence --")
    for key in ("equity_points", "reached_window_end", "starting_equity", "final_equity",
                "closed_trades", "gross_profit", "gross_loss", "profit_factor",
                "shutdown_session", "max_drawdown_basis", "daily_returns"):
        out("    %-22s %s" % (key, json.dumps(base[key])[:70]))

    out("")
    out("  -- folds (completed=%s positive=%s) --" % (
        body["folds"]["completed"], body["folds"]["positive"]))
    for row in body["folds"]["rows"]:
        out("    %2d %s..%s sess=%-4s done=%-5s base=%-14s eq=%-14s ret=%s" % (
            row["fold"], row["start"], row["end"], row["run_sessions"], row["completed"],
            row["baseline_equity"], row["equity_at_last_session"], row["fold_return"]))

    out("")
    out("  -- gate --")
    for entry in body["gate"]["conditions"]:
        out("    %-7s %-14s sat=%-5s measured=%s" % (
            entry["id"], entry["verdict"], entry["satisfied"], entry["measured"]))
    out("    gate_passed  %s" % body["gate"]["gate_passed"])
    out("    token        %s" % body["gate"]["verdict_token"])

    inv = body["gate_evidence"]["invariance"]
    out("")
    out("  -- S4-C7 clauses --")
    for key in ("all_digests_equal", "digests_equal", "digests_total",
                "validation_evaluation_run_records", "validation_window_engine_runs",
                "declared_run_count", "parameters_unchanged"):
        out("    %-36s %s" % (key, json.dumps(inv[key])))

    out("")
    out("  -- second call is refused --")
    out("    build() -> %s" % evmod.build())
    out("    records now: %d" % len(list(runs.glob("*.json"))))
    out("")


scenario("RISING (no trades)", rising)
scenario("OSCILLATING (trades close)", oscillating)
