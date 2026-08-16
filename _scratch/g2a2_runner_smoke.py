"""Smoke g2_runner_ra1 before anything imports it for real.

ASCII output only: the console is cp1252 and a single arrow character kills the sweep mid-run.

Sections
  1  import, and the AT-I field-tuple assertion that fires at import
  2  run_labels / scenario_for_label, including the refusals
  3  AT-H, the Attempt 1 module digests
  4  the dataset and the run-span recheck (three-way)
  5  sealed_steps against the seal
  6  select_representative: no-candidate, step 1, step 2, step 3
  7  selection_inputs refusals
  8  gate_inputs scope assertions and the neighbour label
  9  one real run end to end, plus grid_report over it
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

PASSED = 0
FAILED = 0
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print("  ok   %s" % name)
    else:
        FAILED += 1
        FAILURES.append(name)
        print("  FAIL %s %s" % (name, detail))


def refuses(name: str, fn, *exc) -> None:
    try:
        fn()
    except exc as error:  # noqa: PERF203
        check(name, True)
        print("       -> %s: %s" % (type(error).__name__, str(error).splitlines()[0][:150]))
    except Exception as error:  # noqa: BLE001
        check(name, False, "raised %s instead: %s" % (type(error).__name__, error))
    else:
        check(name, False, "did not refuse")


print("=" * 100)
print("SECTION 1  import")
print("=" * 100)

from stockedge100.backtest.errors import ConfigViolation, InvariantViolation  # noqa: E402
from stockedge100.strategies import g2_runner_ra1 as R  # noqa: E402
from stockedge100.strategies.g2_rotation_ra1 import (  # noqa: E402
    load_protocol,
    rotation_variants,
    variant_by_id,
)

check("module imports", True)
check(
    "SELECTION_FIELD_NAMES is the sealed four",
    R.SELECTION_FIELD_NAMES == ("variant_id", "shutdown_events", "fill_count", "per_run"),
    str(R.SELECTION_FIELD_NAMES),
)
actual = tuple(f.name for f in dataclasses.fields(R.SelectionInputRA1))
check("SelectionInputRA1 fields == SELECTION_FIELD_NAMES", actual == R.SELECTION_FIELD_NAMES, str(actual))
banned = {
    "total_return", "return", "cagr", "sharpe", "max_drawdown", "profit_factor", "equity",
    "pnl", "win_rate", "result", "measurement", "ladder", "lockout", "ladder_activations",
}
check(
    "no performance or risk-outcome field on the selection input",
    not (set(actual) & banned),
    str(sorted(set(actual) & banned)),
)
check("GATE_RUN_LABEL is #BASE", R.GATE_RUN_LABEL == "#BASE")
check("STRESS_RUN_LABEL is #STRESS", R.STRESS_RUN_LABEL == "#STRESS")

protocol = load_protocol()
variants = rotation_variants()
check("eighteen declared variants", len(variants) == 18, str(len(variants)))

print()
print("=" * 100)
print("SECTION 2  run labels and cost scenarios")
print("=" * 100)

labels = R.run_labels()
check("sealed labels", labels == ("#BASE", "#STRESS"), str(labels))
check("#BASE -> BASE", R.scenario_for_label("#BASE") == "BASE")
check("#STRESS -> STRESSED", R.scenario_for_label("#STRESS") == "STRESSED")
refuses("an undeclared label refuses", lambda: R.scenario_for_label("#BASELINE"), ConfigViolation)
refuses("a bare scenario name is not a label", lambda: R.scenario_for_label("BASE"), ConfigViolation)
refuses("the empty label refuses", lambda: R.scenario_for_label(""), ConfigViolation)

print()
print("=" * 100)
print("SECTION 3  AT-H, Attempt 1 is not touched")
print("=" * 100)

at_h = R.verify_attempt_1_modules()
check("AT-H passes", at_h["modules_that_moved"] == [], str(at_h["modules_that_moved"]))
check("nine modules verified", at_h["module_count"] == 9, str(at_h["module_count"]))
check(
    "every declared module was hashed",
    len(at_h["modules_verified"]) == at_h["module_count"],
    str(len(at_h["modules_verified"])),
)
check(
    "digest source names the governance seal",
    "SE100-GOV-2005" in at_h["digest_source"],
    at_h["digest_source"],
)
for path, digest in sorted(at_h["modules_verified"].items()):
    print("       %s  %s" % (digest[:16], path))

print()
print("=" * 100)
print("SECTION 4  dataset and run-span recheck")
print("=" * 100)

t0 = time.time()
series = R.load_grid_dataset()
print("       loaded %d symbols in %.1fs" % (len(series), time.time() - t0))
bound = dt.date(2021, 7, 31)
latest = max(s.sessions[-1] for s in series.values())
check("no loaded bar past the development bound", latest <= bound, latest.isoformat())

span = R.recheck_run_span(series, protocol=protocol)
check("run-span recheck passes", span["differences"] == [], str(span["differences"]))
m = span["measured"]
check("run_start 2008-07-28", m["run_start"] == "2008-07-28", m["run_start"])
check("run_end 2021-07-30", m["run_end"] == "2021-07-30", m["run_end"])
check("3276 run sessions", m["run_sessions"] == 3276, str(m["run_sessions"]))
check("157 monthly rebalances", m["monthly_rebalance_sessions"] == 157, str(m["monthly_rebalance_sessions"]))
check("53 quarterly rebalances", m["quarterly_rebalance_sessions"] == 53, str(m["quarterly_rebalance_sessions"]))
check("binding symbol VEA", m["binding_symbol"] == "VEA", str(m["binding_symbol"]))
check("7178 development union sessions", m["development_union_sessions"] == 7178, str(m["development_union_sessions"]))
check("session lists agree", m["session_lists_agree"] is True)
check(
    "the independent derivation was actually compared",
    len(span["independent_derivation_keys_compared"]) >= 15,
    str(len(span["independent_derivation_keys_compared"])),
)
print("       cross-checked keys: %s" % ", ".join(span["independent_derivation_keys_compared"]))

# A perturbed series must refuse. Truncating one symbol by one session moves the union.
victim = sorted(series)[0]
short = dict(series)
original = short[victim]
from stockedge100.backtest.dataset import PriceSeries  # noqa: E402

short[victim] = PriceSeries(
    symbol=victim,
    bars={d: b for d, b in original.bars.items() if d != original.sessions[-1]},
    sessions=original.sessions[:-1],
)
refuses(
    "a truncated member refuses the run-span recheck",
    lambda: R.recheck_run_span(short, protocol=protocol),
    InvariantViolation,
)

print()
print("=" * 100)
print("SECTION 5  the sealed selection steps")
print("=" * 100)

rule = protocol["representative_selection_rule"]
steps = R.sealed_steps(rule)
check("three steps", sorted(steps) == [1, 2, 3], str(sorted(steps)))
for order, criterion in R.EXPECTED_STEP_CRITERIA.items():
    check("step %d is %s" % (order, criterion), steps[order]["criterion"] == criterion, steps[order]["criterion"])
check("the seal calls the key 'criterion', not 'name'", "name" not in steps[1], str(sorted(steps[1])))
refuses(
    "a renamed step refuses",
    lambda: R.sealed_steps({"steps": [dict(steps[1], criterion="lowest_drawdown"), steps[2], steps[3]]}),
    ConfigViolation,
)
refuses(
    "a missing step refuses",
    lambda: R.sealed_steps({"steps": [steps[1], steps[2]]}),
    ConfigViolation,
)

print()
print("=" * 100)
print("SECTION 6  select_representative")
print("=" * 100)


def synth(variant_id: str, shutdowns: tuple[int, int], fills: tuple[int, int]) -> R.SelectionInputRA1:
    per_run = (("#BASE", shutdowns[0], fills[0]), ("#STRESS", shutdowns[1], fills[1]))
    return R.SelectionInputRA1(
        variant_id=variant_id,
        shutdown_events=sum(shutdowns),
        fill_count=sum(fills),
        per_run=per_run,
    )


ids = [v.variant_id for v in variants]

# (a) nothing survives step 1
all_shut = [synth(vid, (1, 1), (100, 100)) for vid in ids]
record = R.select_representative(all_shut, protocol=protocol)
check("no candidate -> representative_exists False", record["representative_exists"] is False)
check("no candidate -> id None", record["representative_variant_id"] is None)
check("no candidate -> decided_by no_candidate_path", record["decided_by"] == "no_candidate_path")
check("no candidate -> step_2 not reached", record["step_2"] is None)
check("no candidate carries the sealed path", bool(record["no_candidate_path"]))
check("eligible list empty", record["step_1"]["eligible"] == [])
check("all eighteen ineligible", len(record["step_1"]["ineligible"]) == 18)

# (b) a shutdown on the STRESS run alone still eliminates: step 1's scope is both runs
one_stress = [synth(vid, (1, 1), (100, 100)) for vid in ids]
one_stress[3] = synth(ids[3], (0, 1), (100, 100))
record = R.select_representative(one_stress, protocol=protocol)
check(
    "a stress-only shutdown does not survive step 1",
    record["representative_exists"] is False,
    str(record["representative_variant_id"]),
)

# (c) exactly one survivor -> step 1 decides
one_clean = [synth(vid, (1, 1), (100, 100)) for vid in ids]
one_clean[7] = synth(ids[7], (0, 0), (444, 444))
record = R.select_representative(one_clean, protocol=protocol)
check("step 1 decides", record["decided_at_step"] == 1, str(record["decided_at_step"]))
check("step 1 picks the clean variant", record["representative_variant_id"] == ids[7])
check("step 2 not reached", record["step_2"]["reached"] is False)
check("step 3 not reached", record["step_3"]["reached"] is False)

# (d) several survive, one lowest turnover -> step 2 decides
turnover = [synth(vid, (1, 1), (100, 100)) for vid in ids]
turnover[2] = synth(ids[2], (0, 0), (50, 60))
turnover[5] = synth(ids[5], (0, 0), (40, 45))   # 85, lowest
turnover[9] = synth(ids[9], (0, 0), (60, 70))
record = R.select_representative(turnover, protocol=protocol)
check("step 2 decides", record["decided_at_step"] == 2, str(record["decided_at_step"]))
check("step 2 picks the lowest fill count", record["representative_variant_id"] == ids[5])
check("lowest_fill_count is 85", record["step_2"]["lowest_fill_count"] == 85, str(record["step_2"]["lowest_fill_count"]))
check("step 3 not reached", record["step_3"]["reached"] is False)

# (e) a tie at the lowest -> step 3 decides lexicographically
tie = [synth(vid, (1, 1), (100, 100)) for vid in ids]
tie[4] = synth(ids[4], (0, 0), (40, 45))
tie[11] = synth(ids[11], (0, 0), (45, 40))
tie[1] = synth(ids[1], (0, 0), (41, 44))
record = R.select_representative(tie, protocol=protocol)
check("step 3 decides", record["decided_at_step"] == 3, str(record["decided_at_step"]))
expected = min(ids[4], ids[11], ids[1])
check("step 3 picks the lexicographic minimum", record["representative_variant_id"] == expected,
      "%s vs %s" % (record["representative_variant_id"], expected))
check("three tied at the lowest", len(record["step_2"]["tied_at_lowest"]) == 3)

# (f) return-blindness: the same shutdown/fill profile must decide identically no matter what
#     performance figures the underlying runs had. There is no field to vary, which is the point.
check(
    "the record states how return-blindness is enforced structurally",
    "SelectionInputRA1" in record["return_blind_enforcement"]
    and "asserted equal" in record["return_blind_enforcement"],
    record["return_blind_enforcement"][:80],
)

refuses(
    "a partial grid refuses",
    lambda: R.select_representative(one_clean[:5], protocol=protocol),
    ConfigViolation,
)
partial = R.select_representative(one_clean[:5], protocol=protocol, require_full_grid=False)
check("require_full_grid=False is available for tests", partial["variants_considered"] == 5)
refuses(
    "a duplicated variant refuses",
    lambda: R.select_representative(one_clean + [one_clean[0]], protocol=protocol),
    ConfigViolation,
)

print()
print("=" * 100)
print("SECTION 7  selection_inputs")
print("=" * 100)


class FakeResult:
    def __init__(self, fills: int, shutdown: dt.date | None) -> None:
        self.fills = [object()] * fills
        self.shutdown_session = shutdown


def fake_run(variant, label: str, fills: int, shutdown: dt.date | None = None) -> R.GridRunRA1:
    return R.GridRunRA1(
        variant=variant,
        label=label,
        scenario=R.scenario_for_label(label),
        result=FakeResult(fills, shutdown),
        measurement={},
        strategy_evidence={},
        clamps={},
        risk={},
        trades=[],
        ledger=None,
        reconciliation={},
    )


both = [fake_run(v, lbl, 10 + i) for i, v in enumerate(variants) for lbl in labels]
inputs = R.selection_inputs(both)
check("one input per variant", len(inputs) == 18, str(len(inputs)))
check("sorted by variant id", [i.variant_id for i in inputs] == sorted(ids))
check("fills summed across both runs", inputs[0].fill_count == sum(
    r.fill_count for r in both if r.variant.variant_id == inputs[0].variant_id))
check("per_run carries both labels", tuple(l for l, _, _ in inputs[0].per_run) == labels)

shut = list(both)
shut[1] = fake_run(variants[0], "#STRESS", 11, dt.date(2011, 8, 8))
inputs = R.selection_inputs(shut)
by_id = {i.variant_id: i for i in inputs}
check("a shutdown session counts as one event", by_id[variants[0].variant_id].shutdown_events == 1,
      str(by_id[variants[0].variant_id].shutdown_events))

refuses(
    "a variant missing its #STRESS run refuses",
    lambda: R.selection_inputs([r for r in both if not (r.variant.variant_id == ids[0] and r.label == "#STRESS")]),
    ConfigViolation,
)
refuses(
    "a duplicated run refuses",
    lambda: R.selection_inputs(both + [both[0]]),
    ConfigViolation,
)

print()
print("=" * 100)
print("SECTION 8  gate_inputs")
print("=" * 100)

gi = R.gate_inputs(both, ids[9])
check("primary is the #BASE run", gi["primary_run"].label == "#BASE")
check("stress is the #STRESS run", gi["stress_run"].label == "#STRESS")
check("neighbours are read on #BASE", gi["neighbour_run_label"] == "#BASE")
check("neighbours were derived", len(gi["neighbours"]) >= 2, str(len(gi["neighbours"])))
check("conflict is disclosed", gi["conflict_ref"] == "G2A2-CONFLICT-25")
check("scope sentence names both runs", "both of its runs" in gi["evaluated_on"], gi["evaluated_on"])
check("both_gate is carried", "only if both of its runs satisfy it" in gi["both_gate"])
check(
    "the resolution names the more restrictive reading",
    "all seven conditions on #BASE" in gi["scope_resolution"]
    and "S3-C1..S3-C6 also on #STRESS" in gi["scope_resolution"],
    gi["scope_resolution"][:90],
)
refuses(
    "an unknown representative refuses",
    lambda: R.gate_inputs(both, "SE100-G2-NOPE"),
    ConfigViolation,
)
refuses(
    "a missing neighbour run refuses",
    lambda: R.gate_inputs([r for r in both if r.label == "#BASE"][:3], ids[9]),
    ConfigViolation,
)

print()
print("=" * 100)
print("SECTION 9  one real run, end to end")
print("=" * 100)

target = variants[0]
print("       running %s#BASE over 3276 sessions ..." % target.variant_id)
t0 = time.time()
runs = R.run_grid(series, variants=(target,), labels=("#BASE",), verify=False)
print("       %.1fs" % (time.time() - t0))

run = runs[0]
check("one run returned", len(runs) == 1)
check("run id", run.run_id == target.variant_id + "#BASE", run.run_id)
check("scenario BASE", run.scenario == "BASE")
check("3276 equity points", len(run.result.equity_curve) == 3276, str(len(run.result.equity_curve)))
check("an episode ledger was built", run.ledger is not None)
check("a reconciliation was recorded", isinstance(run.reconciliation, dict) and "vacuous" in run.reconciliation)
check("risk summary present", "ladder" in run.risk and "lockout" in run.risk and "stops" in run.risk)
check("combined scalar mean is reported", run.risk["combined_scalar"]["mean"] is not None,
      str(run.risk["combined_scalar"]))
check("clamp summary present", "aggregate_ra2_ceiling" in run.clamps)
print("       fills=%d closed_trades=%s shutdown=%s" % (
    run.fill_count, run.measurement["closed_trades"], run.measurement["shutdown_session"]))
print("       ladder descents=%s deepest=%s lockout arms=%s stops filled=%s" % (
    run.risk["ladder"]["descents"], run.risk["ladder"]["deepest_band"],
    run.risk["lockout"]["arms"], run.risk["stops"]["filled"]))
print("       reconciliation: closed_episodes=%s closed_trades=%s single_leg=%s mismatches=%s vacuous=%s" % (
    run.reconciliation["closed_episodes"], run.reconciliation["closed_trades"],
    run.reconciliation["single_leg_compared"], run.reconciliation["mismatch_count"],
    run.reconciliation["vacuous"]))

rows = R.grid_report(runs)
check("one report row", len(rows) == 1, str(len(rows)))
row = rows[0]
required = [
    "grid_index", "variant_id", "lookback_months", "top_k", "rebalance_frequency", "label",
    "total_return", "max_drawdown", "profit_factor", "closed_trades",
    "research_shutdown_events", "shutdown_session", "fills",
    "ladder_descents", "ladder_ascents", "ladder_deepest_band", "ladder_sessions_in_band",
    "lockout_arms", "lockout_recoveries_blocked", "stops_triggered", "stops_filled",
    "throttle_legs_scheduled", "throttle_legs_below_min_notional",
    "max_gross_fraction_observed", "combined_scalar_minimum", "combined_scalar_mean",
    "combined_scalar_sessions_below_one", "trades_digest", "equity_digest", "ranking_digest",
    "risk_state_digest", "scheduled_rebalances", "executed_rebalances",
    "reconciliation_single_leg_compared", "reconciliation_mismatches",
]
absent = [key for key in required if key not in row]
check("every seal-required column is present", absent == [], str(absent))
check("no None where a count belongs", row["fills"] is not None and row["ladder_descents"] is not None)
check(
    "the two Attempt 2 counters are reported",
    isinstance(row["ladder_descents"], int) and isinstance(row["lockout_arms"], int),
    "%r %r" % (row["ladder_descents"], row["lockout_arms"]),
)
for key in sorted(row):
    value = row[key]
    if isinstance(value, dict):
        value = "{...%d keys}" % len(value)
    print("       %-42s %s" % (key, value))

print()
print("=" * 100)
print("PASSED: %d   FAILED: %d" % (PASSED, FAILED))
if FAILURES:
    for name in FAILURES:
        print("  - %s" % name)
print("=" * 100)
sys.exit(1 if FAILED else 0)
