"""Seal the Generation 2 Stage 3 rotation pre-registration.

Writes ``governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json`` and the ``.sha256`` record that
covers it together with the hand-authored Markdown counterpart and the three Generation 2 config
artifacts. Run once:

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_rotation_preregistration

Four properties this module is responsible for.

**It seals once.** A pre-registration that can be regenerated after a variant has been run is not a
pre-registration. If either output already exists the program refuses and changes nothing.

**It proves the precondition it claims.** The sealed config asserts that it was written before any
Generation 2 strategy code existed. That is measured here — Generation 2 modules under
``strategies/``, ``backtest/``, elsewhere in ``src/``, and under ``tests/`` must all be zero, no
Generation 2 report directory may exist, and no Generation 2 ``runs/`` record other than the Stage 1
partition lock may exist. The two sealing programs under ``reporting/`` are a real narrowing of the
predicate and are named rather than quietly excluded.

**It measures rather than restates.** The run span, the rebalance calendars, the universe coverage
and every target weight are recomputed here from the acquired session dates and from decimal
arithmetic, then compared against the sealed config JSON row by row and against the Markdown row by
row. A disagreement is a refusal, not a warning.

**It reads dates, never prices.** Like the Stage 1 sealer, the only column this module parses out of
the acquired data is ``session``. No price, volume, or dividend field is read in any window.

The generation identity, the universe, the window constants and the mandated validation-reuse
disclosure are imported from the Stage 1 sealer rather than retyped, so there is exactly one copy of
each in the tree.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from calendar import monthrange
from decimal import ROUND_DOWN, Decimal
from pathlib import Path
from typing import Any

from ..audit import (
    RunRecord,
    dependency_versions,
    sha256_file,
    utc_now_iso,
    write_sha256_record,
)
from ..data.calendar import sessions_between
from .stage_package import (
    PROJECT_ROOT,
    RUNS_DIR,
    TRACKED_DEPENDENCIES,
    new_run_id,
    repo_state,
    verify_sha256_record,
    verify_stage0_freeze,
)
from .g2_partition_lock import (
    CHARTER_ID,
    CHARTER_MD,
    DAILY,
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    GENERATION_1_HOLDOUT_END,
    GENERATION_1_HOLDOUT_START,
    HOLDOUT_END,
    HOLDOUT_START,
    UNIVERSE,
    UNIVERSE_VERSION,
    VALIDATION_END,
    VALIDATION_REUSE_DISCLOSURE,
    VALIDATION_START,
    generation_identity,
    normalised_prose,
    sessions_only,
)
from .g2_partition_lock import RECORD_JSON as PARTITION_LOCK_JSON
from .g2_partition_lock import RECORD_MD as PARTITION_LOCK_MD
from .g2_partition_lock import RECORD_SHA as PARTITION_LOCK_SHA

G2_GOVERNANCE = PROJECT_ROOT / "governance" / "generation_2"
G2_CONFIG = PROJECT_ROOT / "config" / "generation_2"

RECORD_MD = G2_GOVERNANCE / "STAGE_3_G2_ROTATION_PROTOCOL.md"
RECORD_JSON = G2_GOVERNANCE / "STAGE_3_G2_ROTATION_PROTOCOL.json"
RECORD_SHA = G2_GOVERNANCE / "STAGE_3_G2_ROTATION_PROTOCOL.sha256"

PROTOCOL_CONFIG = G2_CONFIG / "g2_rotation_protocol.json"
CRITERIA_CONFIG = G2_CONFIG / "g2_gate_criteria.json"
COST_CONFIG = G2_CONFIG / "g2_cost_model.json"

DOCUMENT_ID = "SE100-GOV-2003"
PARTITION_LOCK_ID = "SE100-GOV-2002"

STRATEGY_ID = "SE100-G2-S3-C1-ROTATION"
LOOKBACKS = (3, 6, 12)
POSITION_COUNTS = (1, 2, 3)
FREQUENCIES = ("MONTHLY", "QUARTERLY")
QUARTER_MONTHS = (1, 4, 7, 10)

MAX_GROSS = Decimal("0.95")
CONCENTRATION_CEILING = Decimal("0.50")
WEIGHT_QUANTUM = Decimal("1E-9")

PASS_TOKEN = "STAGE_3_G2_STRATEGY_ADMITTED_IN_DEVELOPMENT"
FAIL_TOKEN = "STAGE_3_G2_NO_CANDIDATE"

# Generation 2 modules that are allowed to exist when this seal is taken. Both are sealing programs:
# they read session dates and governance artifacts, run no strategy, and produce no result. Naming
# them is the honest form of the precondition; "zero Generation 2 modules" would simply be false.
PERMITTED_GENERATION_2_MODULES = (
    "src/stockedge100/reporting/g2_partition_lock.py",
    "src/stockedge100/reporting/g2_rotation_preregistration.py",
)
PERMITTED_GENERATION_2_RUN_STAGES = ("stage_1_generation_2_partition_lock",)

BINDING_RULES = (
    "The grid is complete at eighteen variants. No variant is added, removed, or re-parameterised "
    "under any result.",
    "The representative-selection rule is applied exactly as sealed, on research-shutdown counts, "
    "fill counts, and variant ids alone. No return, drawdown, profit factor, or equity level is an "
    "input to it.",
    "Gate 3 is evaluated on the selected representative's base run only. No other variant is "
    "evaluated against the gate, and the runner-up is never promoted.",
    "No parameter, threshold, symbol, weight, or rule may be chosen using any value inside the "
    "validation window or either holdout window.",
    "A defect discovered after this seal is reported and its effect disclosed. This artifact is "
    "superseded by a new id if it is wrong; it is never edited in place.",
    "Stage 4 validation for Generation 2 requires a separate, explicitly authorized session. "
    "Nothing sealed here, and no result produced under it, authorizes one.",
    "live_trading_authorized remains false. This artifact authorizes no order, no broker "
    "connection, no credential read, and no scheduling of either.",
)


# --------------------------------------------------------------------------------------------- #
# Calendar arithmetic
# --------------------------------------------------------------------------------------------- #

def month_offset(day: dt.date, months: int) -> dt.date:
    """Shift ``day`` by ``months`` calendar months, clamping the day to the target month's length.

    Pure calendar arithmetic. It reads no market data, which is why the lookback interval can be
    established before any bar is loaded.
    """
    total = (day.year * 12 + day.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    return dt.date(year, month, min(day.day, monthrange(year, month)[1]))


def target_weight(k: int) -> Decimal:
    """``w(k) = min(0.95 / k, 0.50)`` quantized to nine decimals, ROUND_DOWN.

    ROUND_DOWN rather than the engine's ROUND_HALF_EVEN: at k=3 the half-even value times three
    exceeds 0.95 in the thirty-fourth decimal place, which would make the aggregate exposure clamp
    bind on the third buy of every rebalance for a pure representation reason.
    """
    raw = min(MAX_GROSS / Decimal(k), CONCENTRATION_CEILING)
    return raw.quantize(WEIGHT_QUANTUM, rounding=ROUND_DOWN)


def variant_id(lookback: int, k: int, frequency: str) -> str:
    return f"{STRATEGY_ID}-L{lookback:02d}-K{k}-{frequency}"


def enumerate_grid() -> list[dict[str, Any]]:
    """The eighteen variants, in the declared order: lookback outer, k, frequency inner."""
    rows: list[dict[str, Any]] = []
    for lookback in LOOKBACKS:
        for k in POSITION_COUNTS:
            weight = target_weight(k)
            gross = (weight * k).quantize(WEIGHT_QUANTUM)
            for frequency in FREQUENCIES:
                rows.append(
                    {
                        "index": len(rows) + 1,
                        "variant_id": variant_id(lookback, k, frequency),
                        "lookback_months": lookback,
                        "top_k": k,
                        "rebalance_frequency": frequency,
                        "target_weight_per_position": f"{weight:.9f}",
                        "target_gross_exposure": f"{gross:.9f}",
                    }
                )
    return rows


# --------------------------------------------------------------------------------------------- #
# Date-only measurement
# --------------------------------------------------------------------------------------------- #

def measure_span() -> dict[str, Any]:
    """Recompute the run span and both rebalance calendars from the acquired session dates.

    Two independent session lists are built — the union of the members' own bars, and the exchange
    calendar — and required to agree over the run span. If the strategy's session loop and the
    calendar disagreed anywhere, every rebalance count sealed here would be arguable.
    """
    first: dict[str, str] = {}
    last: dict[str, str] = {}
    development_union: set[str] = set()
    member_sessions: dict[str, set[str]] = {}

    for symbol in UNIVERSE:
        sessions = sessions_only(symbol)
        inside = [s for s in sessions if DEVELOPMENT_START <= s <= DEVELOPMENT_END]
        member_sessions[symbol] = set(inside)
        development_union.update(inside)
        first[symbol] = inside[0]
        last[symbol] = inside[-1]

    union = sorted(development_union)
    latest_inception = max(first.values())
    latest_symbols = sorted(s for s in UNIVERSE if first[s] == latest_inception)
    earliest_inception = min(first.values())
    earliest_symbols = sorted(s for s in UNIVERSE if first[s] == earliest_inception)

    run_end = max(last.values())
    ends_early = sorted(s for s in UNIVERSE if last[s] != run_end)

    # The first session whose twelve-month lookback reference lands at or after the latest inception
    # in the universe, so the longest lookback in the grid has a bar for every member from the first
    # rebalance onward. Common to all eighteen variants by declaration.
    run_start = None
    previous_session = None
    for session in union:
        if month_offset(dt.date.fromisoformat(session), -12).isoformat() >= latest_inception:
            run_start = session
            break
        previous_session = session
    if run_start is None:
        raise RuntimeError("no development session satisfies the twelve-month lookback requirement")

    run_sessions = [s for s in union if run_start <= s <= run_end]
    calendar_sessions = [
        d.isoformat()
        for d in sessions_between(
            dt.date.fromisoformat(run_start), dt.date.fromisoformat(run_end)
        )
    ]

    monthly = [run_sessions[0]]
    quarterly = [run_sessions[0]]
    for previous, session in zip(run_sessions, run_sessions[1:]):
        if session[5:7] != previous[5:7]:
            monthly.append(session)
            if int(session[5:7]) in QUARTER_MONTHS:
                quarterly.append(session)

    missing_at_start = sorted(s for s in UNIVERSE if run_start not in member_sessions[s])

    return {
        "member_count": len(UNIVERSE),
        "run_start": run_start,
        "run_start_weekday": dt.date.fromisoformat(run_start).strftime("%A"),
        "run_start_lookback_reference": month_offset(
            dt.date.fromisoformat(run_start), -12
        ).isoformat(),
        "session_before_run_start": previous_session,
        "session_before_run_start_lookback_reference": (
            month_offset(dt.date.fromisoformat(previous_session), -12).isoformat()
            if previous_session
            else None
        ),
        "run_end": run_end,
        "run_sessions": len(run_sessions),
        "exchange_calendar_sessions": len(calendar_sessions),
        "session_lists_agree": calendar_sessions == run_sessions,
        "binding_symbol": latest_symbols[0] if len(latest_symbols) == 1 else None,
        "binding_symbols": latest_symbols,
        "binding_symbol_inception": latest_inception,
        "earliest_inception": earliest_inception,
        "earliest_inception_symbols": earliest_symbols,
        "members_missing_a_bar_at_run_start": missing_at_start,
        "symbols_ending_before_run_end": ends_early,
        "development_union_sessions": len(union),
        "development_union_span": [union[0], union[-1]],
        "monthly_rebalance_sessions": len(monthly),
        "quarterly_rebalance_sessions": len(quarterly),
        "monthly_first_three": monthly[:3],
        "monthly_last_two": monthly[-2:],
        "quarterly_first_three": quarterly[:3],
        "quarterly_last_two": quarterly[-2:],
        "measurement_basis": (
            "Date column only, plus the exchange calendar. This module parses no price, volume, or "
            "dividend field in any window, so nothing it measures is an observation of a market."
        ),
    }


# --------------------------------------------------------------------------------------------- #
# Precondition: no Generation 2 strategy code, results, or run records yet
# --------------------------------------------------------------------------------------------- #

def measure_contamination() -> dict[str, Any]:
    """Count Generation 2 modules, reports, and run records that exist at seal time.

    The predicate is a basename containing ``g2_``. Two sealing programs under ``reporting/`` are
    permitted and named; everything else must be absent for the pre-registration's central claim to
    be true.
    """
    src = PROJECT_ROOT / "src" / "stockedge100"
    tests = PROJECT_ROOT / "tests"

    def matches(root: Path) -> list[str]:
        if not root.exists():
            return []
        return sorted(
            p.relative_to(PROJECT_ROOT).as_posix()
            for p in root.rglob("*.py")
            if "g2_" in p.name
        )

    strategies = matches(src / "strategies")
    backtest = matches(src / "backtest")
    reporting = matches(src / "reporting")
    src_all = matches(src)
    elsewhere = sorted(set(src_all) - set(strategies) - set(backtest) - set(reporting))
    test_modules = matches(tests)

    reports_dir = PROJECT_ROOT / "reports" / "generation_2"
    generation_2_reports = (
        sorted(p.relative_to(PROJECT_ROOT).as_posix() for p in reports_dir.rglob("*"))
        if reports_dir.exists()
        else []
    )

    foreign_runs: list[str] = []
    if RUNS_DIR.exists():
        for record in sorted(RUNS_DIR.glob("*.json")):
            try:
                stage = json.loads(record.read_text(encoding="utf-8")).get("stage", "")
            except (json.JSONDecodeError, OSError):
                continue
            if "generation_2" in stage and stage not in PERMITTED_GENERATION_2_RUN_STAGES:
                foreign_runs.append(record.name)

    return {
        "predicate": "a Python file under src/stockedge100/ or tests/ whose basename contains 'g2_'",
        "strategies": strategies,
        "backtest": backtest,
        "elsewhere_in_src": elsewhere,
        "tests": test_modules,
        "reporting": reporting,
        "strategies_count": len(strategies),
        "backtest_count": len(backtest),
        "elsewhere_in_src_count": len(elsewhere),
        "tests_count": len(test_modules),
        "reporting_count": len(reporting),
        "generation_2_report_artifacts": generation_2_reports,
        "generation_2_run_records_other_than_the_partition_lock": foreign_runs,
        "permitted_reporting_modules": list(PERMITTED_GENERATION_2_MODULES),
        "narrowing_note": (
            "The two permitted modules are sealing programs, not strategies. Recording them as a "
            "narrowing of the predicate rather than excluding them silently is the same treatment "
            "Generation 1 gave its own reporting modules."
        ),
    }


def contamination_problems(measured: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for label in ("strategies", "backtest", "elsewhere_in_src", "tests"):
        found = measured[label]
        if found:
            problems.append(f"Generation 2 module(s) already exist under {label}: {found}")
    if sorted(measured["reporting"]) != sorted(PERMITTED_GENERATION_2_MODULES):
        problems.append(
            "the Generation 2 modules under reporting/ are not exactly the two permitted sealing "
            f"programs: {measured['reporting']}"
        )
    if measured["generation_2_report_artifacts"]:
        problems.append(
            "a Generation 2 report directory already exists: "
            f"{measured['generation_2_report_artifacts'][:5]}"
        )
    if measured["generation_2_run_records_other_than_the_partition_lock"]:
        problems.append(
            "a Generation 2 run record other than the partition lock already exists: "
            f"{measured['generation_2_run_records_other_than_the_partition_lock']}"
        )
    return problems


# --------------------------------------------------------------------------------------------- #
# Agreement: sealed config JSON against the measurement
# --------------------------------------------------------------------------------------------- #

def check_config_agreement(config: dict[str, Any], span: dict[str, Any]) -> list[str]:
    """Every claim the sealed config makes that this module can independently recompute."""
    problems: list[str] = []
    expected = enumerate_grid()

    grid = config.get("grid", {})
    if grid.get("size") != len(expected):
        problems.append(f"grid.size is {grid.get('size')}, measured {len(expected)}")
    axes = grid.get("axes", {})
    if tuple(axes.get("lookback_months", ())) != LOOKBACKS:
        problems.append(f"grid.axes.lookback_months is {axes.get('lookback_months')}")
    if tuple(axes.get("top_k", ())) != POSITION_COUNTS:
        problems.append(f"grid.axes.top_k is {axes.get('top_k')}")
    if tuple(axes.get("rebalance_frequency", ())) != FREQUENCIES:
        problems.append(f"grid.axes.rebalance_frequency is {axes.get('rebalance_frequency')}")

    declared = grid.get("variants", [])
    if len(declared) != len(expected):
        problems.append(f"grid.variants has {len(declared)} entries, measured {len(expected)}")
    else:
        counts = {
            "MONTHLY": span["monthly_rebalance_sessions"],
            "QUARTERLY": span["quarterly_rebalance_sessions"],
        }
        for want, got in zip(expected, declared):
            for field, value in want.items():
                if got.get(field) != value:
                    problems.append(
                        f"variant {want['variant_id']}: {field} is {got.get(field)!r}, "
                        f"recomputed {value!r}"
                    )
            rebalances = counts[want["rebalance_frequency"]]
            if got.get("scheduled_rebalance_sessions") != rebalances:
                problems.append(
                    f"variant {want['variant_id']}: scheduled_rebalance_sessions is "
                    f"{got.get('scheduled_rebalance_sessions')}, measured {rebalances}"
                )

    run_span = config.get("run_span", {})
    for field, value in (
        ("run_start", span["run_start"]),
        ("run_start_weekday", span["run_start_weekday"]),
        ("run_end", span["run_end"]),
        ("run_sessions", span["run_sessions"]),
        ("binding_symbol", span["binding_symbol"]),
        ("binding_symbol_inception", span["binding_symbol_inception"]),
        ("earliest_inception_in_universe", span["earliest_inception"]),
        ("earliest_inception_symbols", span["earliest_inception_symbols"]),
        ("members_missing_a_bar_at_run_start", span["members_missing_a_bar_at_run_start"]),
        ("symbols_ending_before_run_end", span["symbols_ending_before_run_end"]),
        ("development_union_sessions", span["development_union_sessions"]),
        ("development_union_span", span["development_union_span"]),
    ):
        if run_span.get(field) != value:
            problems.append(f"run_span.{field} is {run_span.get(field)!r}, measured {value!r}")

    measured_counts = config.get("rebalance", {}).get("measured_counts", {})
    for field in (
        "monthly_rebalance_sessions",
        "quarterly_rebalance_sessions",
        "monthly_first_three",
        "monthly_last_two",
        "quarterly_first_three",
        "quarterly_last_two",
    ):
        if measured_counts.get(field) != span[field]:
            problems.append(
                f"rebalance.measured_counts.{field} is {measured_counts.get(field)!r}, "
                f"measured {span[field]!r}"
            )

    sizing = config.get("position_sizing", {})
    for k in POSITION_COUNTS:
        weight = f"{target_weight(k):.9f}"
        gross = f"{(target_weight(k) * k).quantize(WEIGHT_QUANTUM):.9f}"
        if sizing.get("target_weights", {}).get(str(k)) != weight:
            problems.append(f"position_sizing.target_weights['{k}'] disagrees with {weight}")
        if sizing.get("target_gross_exposure", {}).get(str(k)) != gross:
            problems.append(f"position_sizing.target_gross_exposure['{k}'] disagrees with {gross}")

    window = config.get("window", {})
    if window.get("start") != DEVELOPMENT_START or window.get("end") != DEVELOPMENT_END:
        problems.append("window.start/window.end disagree with the sealed partition lock")
    prohibited = {tuple(entry.get("window", [])) for entry in window.get("prohibited", [])}
    for pair in (
        (VALIDATION_START, VALIDATION_END),
        (GENERATION_1_HOLDOUT_START, GENERATION_1_HOLDOUT_END),
        (HOLDOUT_START, HOLDOUT_END),
    ):
        if pair not in prohibited:
            problems.append(f"window.prohibited does not list {pair}")

    if config.get("strategy_id") != STRATEGY_ID:
        problems.append(f"strategy_id is {config.get('strategy_id')!r}")
    runs = config.get("runs_per_variant", {})
    if runs.get("total_runs") != len(expected) * runs.get("count", 0):
        problems.append("runs_per_variant.total_runs is not count times the grid size")

    return problems


def check_criteria_agreement(criteria: dict[str, Any]) -> list[str]:
    """The two verdict tokens must already be sealed, and must be sealed as a pair."""
    problems: list[str] = []
    derivation = criteria.get("verdict_token_derivation", {})
    if derivation.get("pass_token") != PASS_TOKEN:
        problems.append(f"gate criteria pass_token is {derivation.get('pass_token')!r}")
    if derivation.get("fail_token") != FAIL_TOKEN:
        problems.append(f"gate criteria fail_token is {derivation.get('fail_token')!r}")
    if criteria.get("live_trading_authorized") is not False:
        problems.append("gate criteria do not carry live_trading_authorized false")
    return problems


# --------------------------------------------------------------------------------------------- #
# Agreement: Markdown against the measurement
# --------------------------------------------------------------------------------------------- #

def check_document_agreement(
    document: str, span: dict[str, Any], contamination: dict[str, Any]
) -> list[str]:
    """Every claim the Markdown makes that this module can independently check."""
    flat = normalised_prose(document)
    problems: list[str] = []

    if normalised_prose(VALIDATION_REUSE_DISCLOSURE) not in flat:
        problems.append(
            "the mandated validation-reuse disclosure is missing from the Markdown or was altered"
        )

    required = {
        "document id": DOCUMENT_ID,
        "charter id": CHARTER_ID,
        "partition lock id": PARTITION_LOCK_ID,
        "generation id": generation_identity()["generation_id"],
        "strategy id": STRATEGY_ID,
        "development start": DEVELOPMENT_START,
        "development end": DEVELOPMENT_END,
        "validation start": VALIDATION_START,
        "validation end": VALIDATION_END,
        "generation 1 holdout start": GENERATION_1_HOLDOUT_START,
        "generation 1 holdout end": GENERATION_1_HOLDOUT_END,
        "holdout start": HOLDOUT_START,
        "holdout end": HOLDOUT_END,
        "universe version": UNIVERSE_VERSION,
        "run start": span["run_start"],
        "run start weekday": span["run_start_weekday"],
        "run end": span["run_end"],
        "run session count": str(span["run_sessions"]),
        "binding symbol inception": span["binding_symbol_inception"],
        "development union session count": str(span["development_union_sessions"]),
        "pass token": PASS_TOKEN,
        "fail token": FAIL_TOKEN,
    }
    for label, value in required.items():
        if value not in flat:
            problems.append(f"the Markdown does not state the measured {label} ({value})")

    if span["binding_symbol"] and span["binding_symbol"] not in flat:
        problems.append(f"the Markdown does not name the binding symbol {span['binding_symbol']}")

    # The grid table, row by row, rebuilt from the recomputed grid and the measured calendars.
    counts = {
        "MONTHLY": span["monthly_rebalance_sessions"],
        "QUARTERLY": span["quarterly_rebalance_sessions"],
    }
    for row in enumerate_grid():
        expected = (
            f"| {row['index']} | {row['variant_id']} | {row['lookback_months']} | {row['top_k']} "
            f"| {row['rebalance_frequency']} | {row['target_weight_per_position']} "
            f"| {row['target_gross_exposure']} | {counts[row['rebalance_frequency']]} |"
        )
        if expected not in flat:
            problems.append(f"the Markdown grid table does not carry the row for {row['variant_id']}")

    # The weight table, rebuilt from the same arithmetic the engine will use.
    for k in POSITION_COUNTS:
        weight = target_weight(k)
        gross = (weight * k).quantize(WEIGHT_QUANTUM)
        expected = f"| {k} | {weight:.9f} | {gross:.9f} |"
        if expected not in flat:
            problems.append(f"the Markdown weight table does not carry the row for k={k}")

    # The rebalance calendar table.
    for frequency, count, first_three, last_two in (
        (
            "MONTHLY",
            span["monthly_rebalance_sessions"],
            span["monthly_first_three"],
            span["monthly_last_two"],
        ),
        (
            "QUARTERLY",
            span["quarterly_rebalance_sessions"],
            span["quarterly_first_three"],
            span["quarterly_last_two"],
        ),
    ):
        expected = (
            f"| {frequency} | {count} | {', '.join(first_three)} | {', '.join(last_two)} |"
        )
        if expected not in flat:
            problems.append(f"the Markdown does not carry the measured {frequency} rebalance row")

    # The contamination table, so the document cannot claim a cleaner precondition than was measured.
    for label, count in (
        ("src/stockedge100/strategies/", contamination["strategies_count"]),
        ("src/stockedge100/backtest/", contamination["backtest_count"]),
        ("src/stockedge100/reporting/", contamination["reporting_count"]),
    ):
        expected = f"| Generation 2 modules under {label} | {count} |"
        if expected not in flat:
            problems.append(f"the Markdown does not state the measured module count for {label}")
    expected_tests = f"| Generation 2 test modules under tests/ | {contamination['tests_count']} |"
    if expected_tests not in flat:
        problems.append("the Markdown does not state the measured Generation 2 test module count")
    for module in PERMITTED_GENERATION_2_MODULES:
        if module not in flat:
            problems.append(f"the Markdown does not name the permitted sealing program {module}")

    return problems


# --------------------------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------------------------- #

def build() -> int:
    if RECORD_JSON.exists() or RECORD_SHA.exists():
        print("REFUSED: the Generation 2 Stage 3 pre-registration is already sealed.")
        print(f"  {RECORD_JSON.relative_to(PROJECT_ROOT).as_posix()}: {RECORD_JSON.exists()}")
        print(f"  {RECORD_SHA.relative_to(PROJECT_ROOT).as_posix()}: {RECORD_SHA.exists()}")
        print("A pre-registration is sealed once. Regenerating it would destroy its meaning.")
        return 2

    prerequisites = (
        CHARTER_MD,
        PARTITION_LOCK_MD,
        PARTITION_LOCK_JSON,
        PARTITION_LOCK_SHA,
        RECORD_MD,
        PROTOCOL_CONFIG,
        CRITERIA_CONFIG,
        COST_CONFIG,
    )
    for required in prerequisites:
        if not required.exists():
            print(f"REFUSED: missing prerequisite {required.relative_to(PROJECT_ROOT).as_posix()}")
            return 3

    frozen_ok, frozen_detail = verify_stage0_freeze()
    if not frozen_ok:
        print("REFUSED: the Stage 0 freeze does not verify.")
        for name, detail in sorted(frozen_detail.items()):
            if detail.get("recorded") != detail.get("computed"):
                print(f"  {name}: {detail}")
        return 4

    # Bare-filename record: verified from the directory that holds it, not from the project root.
    stage1_freeze = verify_sha256_record(
        PROJECT_ROOT / "governance" / "STAGE_1_FREEZE.sha256",
        root=PROJECT_ROOT / "governance",
    )
    if any(state != "OK" for state in stage1_freeze.values()):
        print("REFUSED: governance/STAGE_1_FREEZE.sha256 does not verify.")
        for name, state in sorted(stage1_freeze.items()):
            print(f"  {name}: {state}")
        return 5

    # Project-root-relative record, written by the Stage 1 Generation 2 sealer.
    partition_freeze = verify_sha256_record(PARTITION_LOCK_SHA, root=PROJECT_ROOT)
    if any(state != "OK" for state in partition_freeze.values()):
        print("REFUSED: the Generation 2 partition lock record does not verify.")
        for name, state in sorted(partition_freeze.items()):
            print(f"  {name}: {state}")
        return 6

    contamination = measure_contamination()
    problems = contamination_problems(contamination)
    if problems:
        print("REFUSED: Generation 2 work already exists, so this is not a pre-registration.")
        for problem in problems:
            print(f"  - {problem}")
        return 7

    span = measure_span()
    if not span["session_lists_agree"]:
        print("REFUSED: the exchange calendar and the union of member bars disagree over the run.")
        print(f"  union sessions    {span['run_sessions']}")
        print(f"  calendar sessions {span['exchange_calendar_sessions']}")
        return 8

    protocol = json.loads(PROTOCOL_CONFIG.read_text(encoding="utf-8"))
    criteria = json.loads(CRITERIA_CONFIG.read_text(encoding="utf-8"))
    problems = check_config_agreement(protocol, span) + check_criteria_agreement(criteria)
    if problems:
        print("REFUSED: the sealed configuration and the measured data disagree.")
        for problem in problems:
            print(f"  - {problem}")
        return 9

    problems = check_document_agreement(
        RECORD_MD.read_text(encoding="utf-8"), span, contamination
    )
    if problems:
        print("REFUSED: the Markdown protocol and the measured data disagree.")
        for problem in problems:
            print(f"  - {problem}")
        return 10

    identity = generation_identity()
    timestamp = utc_now_iso()
    run_id = new_run_id(timestamp)

    sealed_inputs = {
        "config/generation_2/g2_rotation_protocol.json": sha256_file(PROTOCOL_CONFIG),
        "config/generation_2/g2_gate_criteria.json": sha256_file(CRITERIA_CONFIG),
        "config/generation_2/g2_cost_model.json": sha256_file(COST_CONFIG),
        "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md": sha256_file(CHARTER_MD),
        "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md": sha256_file(PARTITION_LOCK_MD),
        "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json": sha256_file(PARTITION_LOCK_JSON),
    }

    grid = enumerate_grid()
    record: dict[str, Any] = {
        "artifact_id": DOCUMENT_ID,
        "title": "Generation 2 Stage 3 cross-sectional rotation pre-registration",
        "status": "SEALED",
        "project": "StockEdge100",
        "generation": 2,
        "generation_id": identity["generation_id"],
        "stage": 3,
        "gate_id": 3,
        "sealed_utc": timestamp,
        "run_id": run_id,
        "charter_ref": f"governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md ({CHARTER_ID})",
        "partition_lock_ref": (
            f"governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md ({PARTITION_LOCK_ID})"
        ),
        "constitution_ref": "SE100-GOV-0001 sections 3, 4, 5.1, 6.1, 9 gate 3, 11",
        "markdown_counterpart": "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.md",
        "sealed_before_any_strategy_code": True,
        "sealed_before_any_variant_is_run": True,
        "contamination_measurement": contamination,
        "sealed_inputs": sealed_inputs,
        "strategy": {
            "strategy_id": STRATEGY_ID,
            "family": protocol["family"],
            "hypothesis": protocol["hypothesis"],
            "candidate_count": 1,
            "universe_version": UNIVERSE_VERSION,
            "member_count": len(UNIVERSE),
            "members": list(UNIVERSE),
        },
        "grid": {
            "size": len(grid),
            "axes": {
                "lookback_months": list(LOOKBACKS),
                "top_k": list(POSITION_COUNTS),
                "rebalance_frequency": list(FREQUENCIES),
            },
            "variant_id_format": protocol["grid"]["variant_id_format"],
            "variants": grid,
            "runs_per_variant": protocol["runs_per_variant"]["count"],
            "run_labels": protocol["runs_per_variant"]["labels"],
            "total_runs": protocol["runs_per_variant"]["total_runs"],
            "recomputed_here": (
                "Every field above is recomputed by this program from the declared axes and from "
                "decimal arithmetic, then compared field by field against the sealed config and "
                "row by row against the Markdown. It is not copied from either."
            ),
        },
        "run_span_measured_from_disk": span,
        "representative_selection_rule": {
            "return_blind": True,
            "steps": [
                "zero research-shutdown events across both the base and the stress run",
                "lowest turnover, measured as total executed fills across both runs",
                "lexicographically smallest variant id",
            ],
            "inputs": ["research_shutdown_events", "fill_count", "variant_id"],
            "prohibited_inputs": [
                "total return",
                "maximum drawdown",
                "profit factor",
                "Sharpe ratio",
                "equity level",
                "per-trade profit and loss",
            ],
            "no_candidate_path": FAIL_TOKEN,
            "representative_fails_gate_path": FAIL_TOKEN,
            "runner_up_promotion": False,
            "conflict_refs": ["G2-CONFLICT-11", "G2-CONFLICT-13"],
        },
        "gate": {
            "criteria_file": "config/generation_2/g2_gate_criteria.json",
            "criteria_sha256": sealed_inputs["config/generation_2/g2_gate_criteria.json"],
            "evaluated_on": "the selected representative's #BASE run only",
            "condition_count": len(criteria["conditions"]),
            "conjunctive_within_candidate": True,
            "pass_token": PASS_TOKEN,
            "fail_token": FAIL_TOKEN,
            "not_a_disjunction_over_variants": (
                "The eighteen variants are parameterisations of one candidate, not eighteen "
                "candidates. Recorded as G2-CONFLICT-15."
            ),
        },
        "adversarial_test_requirements": {
            "required": list(protocol["adversarial_test_requirements"]["required"]),
            "additional": list(protocol["adversarial_test_requirements"]["additional"]),
            "total": (
                len(protocol["adversarial_test_requirements"]["required"])
                + len(protocol["adversarial_test_requirements"]["additional"])
            ),
        },
        "windows": {
            "authorized": ["development"],
            "development": [DEVELOPMENT_START, DEVELOPMENT_END],
            "validation": [VALIDATION_START, VALIDATION_END],
            "generation_1_holdout": [GENERATION_1_HOLDOUT_START, GENERATION_1_HOLDOUT_END],
            "generation_2_holdout": [HOLDOUT_START, HOLDOUT_END],
            "enforcement": (
                "stockedge100.strategies.g2_window_guard, implementing the three checks sealed in "
                "STAGE_1_G2_PARTITION_LOCK.md section 4, on top of ResearchWindow and MarketView."
            ),
        },
        "validation_reuse_disclosure": VALIDATION_REUSE_DISCLOSURE,
        "validation_reuse_disclosure_note": (
            "Reproduced verbatim because this artifact names the validation window. Nothing in "
            "Stage 3 reads it."
        ),
        "binding_rules": list(BINDING_RULES),
        "repo_state_id_location": (
            "Deliberately omitted here. governance/generation_2/ is not reached by the "
            "repo_state_id patterns (governance/*.md is single-level), so this file is covered by "
            "STAGE_3_G2_ROTATION_PROTOCOL.sha256 instead. The binding repo_state_id for this seal "
            f"is the repo_state_id field of runs/{run_id}.json."
        ),
        "stage_3_authorized": True,
        "stage_4_authorized": False,
        "holdout_read_authorized": False,
        "live_trading_authorized": False,
    }

    RECORD_JSON.parent.mkdir(parents=True, exist_ok=True)
    RECORD_JSON.write_text(
        json.dumps(record, indent=2, sort_keys=False, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Written last so it covers the final bytes of the JSON above. It does not contain its own
    # digest; nothing hashes itself.
    covered = {
        "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.md": sha256_file(RECORD_MD),
        "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json": sha256_file(RECORD_JSON),
        "config/generation_2/g2_rotation_protocol.json": sha256_file(PROTOCOL_CONFIG),
        "config/generation_2/g2_gate_criteria.json": sha256_file(CRITERIA_CONFIG),
        "config/generation_2/g2_cost_model.json": sha256_file(COST_CONFIG),
    }
    own_digest = write_sha256_record(covered, RECORD_SHA)

    code_hashes, repo_state_id = repo_state()
    dataset_hashes = {
        f"data/normalized/daily/{symbol}.csv": sha256_file(DAILY / f"{symbol}.csv")
        for symbol in UNIVERSE
    }

    RunRecord(
        run_id=run_id,
        stage="stage_3_generation_2_rotation_preregistration",
        command="python -m stockedge100.reporting.g2_rotation_preregistration",
        timestamp_utc=timestamp,
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=sealed_inputs["config/generation_2/g2_rotation_protocol.json"],
        dataset_hashes=dataset_hashes,
        universe_version=UNIVERSE_VERSION,
        date_range=[DEVELOPMENT_START, DEVELOPMENT_END],
        holdout_state="SEALED",
        strategy_id=STRATEGY_ID,
        random_seed=None,
        dependency_versions=dependency_versions(TRACKED_DEPENDENCIES),
        exit_status="SEALED",
        output_artifact_hashes={
            **covered,
            "STAGE_3_G2_ROTATION_PROTOCOL.sha256": own_digest,
        },
        notes=[
            f"Eighteen variants declared in full before any is run; {record['grid']['total_runs']} "
            "runs total across the base and stress cost assumptions.",
            f"Run span {span['run_start']} to {span['run_end']}, {span['run_sessions']} sessions, "
            f"common to all eighteen variants; binding symbol {span['binding_symbol']} with "
            f"inception {span['binding_symbol_inception']}.",
            "Grid rows, target weights, and both rebalance calendars were recomputed here and "
            "compared field by field against the sealed config and row by row against the Markdown.",
            "Contamination measured before writing: zero Generation 2 modules under strategies/, "
            "backtest/, elsewhere in src/, and tests/. The two sealing programs under reporting/ "
            "are a recorded narrowing of the predicate, not an exclusion.",
            "governance/generation_2/ is outside REPO_STATE_PATTERNS; the .sha256 record and this "
            "run record are what cover those files. config/generation_2/*.json is inside them and "
            "is additionally covered by the .sha256 record. Recorded as G2-CONFLICT-4.",
            "Measurement read the session date column and the exchange calendar only. No price, "
            "volume, or dividend field was parsed by this program in any window.",
            "Stage 4 validation is not authorized by this seal.",
        ],
    ).write(RUNS_DIR)

    print("Generation 2 Stage 3 pre-registration SEALED")
    print(f"  generation_id  {identity['generation_id']}")
    print(f"  strategy_id    {STRATEGY_ID}")
    print(f"  run_id         {run_id}")
    print(f"  sealed_utc     {timestamp}")
    print(f"  repo_state_id  {repo_state_id}")
    print(f"  grid           {len(grid)} variants x {record['grid']['runs_per_variant']} runs "
          f"= {record['grid']['total_runs']} runs")
    print(f"  run span       {span['run_start']} -> {span['run_end']} "
          f"({span['run_sessions']} sessions)")
    print(f"  rebalances     monthly {span['monthly_rebalance_sessions']}, "
          f"quarterly {span['quarterly_rebalance_sessions']}")
    print(f"  contamination  strategies {contamination['strategies_count']}, "
          f"backtest {contamination['backtest_count']}, tests {contamination['tests_count']}, "
          f"reporting {contamination['reporting_count']} (permitted sealers)")
    print(f"  tokens         {PASS_TOKEN} / {FAIL_TOKEN}")
    for name, digest in sorted(covered.items()):
        print(f"  {digest}  {name}")
    print(f"  record digest  {own_digest}")
    return 0


if __name__ == "__main__":
    sys.exit(build())
