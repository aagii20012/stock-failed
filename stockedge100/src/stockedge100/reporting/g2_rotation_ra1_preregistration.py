"""Seal the Generation 2 Stage 3 **Attempt 2** rotation pre-registration.

Writes ``governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json`` and the ``.sha256`` record
that covers it together with the hand-authored Markdown counterpart and the three Generation 2
config artifacts this attempt reads. Run once:

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_rotation_ra1_preregistration

It is Attempt 1's sealer with four differences, each of them forced by the fact that Attempt 1 now
exists on disk.

**The contamination predicate is content-based, not path-based.** Attempt 1 refused to seal if any
module basename under ``strategies/`` or ``backtest/`` contained ``g2_``. That predicate was true
when ``strategies/`` held no Generation 2 code; it is now unsatisfiable, because Attempt 1's own six
modules live there and are supposed to. Loosening it until it passed would have left a check that
tests nothing. The honest form is that no ``.py`` file under ``src/stockedge100/`` or ``tests/``
names this attempt's candidate — and this module is itself such a file, so it loads the candidate id
from the sealed config at run time rather than writing it as a literal. The indirection is disclosed
in the config (``sealer_indirection_note``) and in section 13 of the Markdown, because a predicate
satisfied by an indirection the reader cannot see is worth no more than one that is simply false.

**A content predicate is paired with an immutability check.** On its own it would pass while an
Attempt 1 module was being quietly rewritten. Every module in ``attempt_1_modules_immutable`` is
re-hashed here and must equal the digest Attempt 1's own development run record recorded, and every
Attempt 1 artifact pinned in ``attempt_1_ref`` must still match its pinned digest. A difference is a
refusal, not a value to update.

**It measures rather than restates.** The run span, both rebalance calendars, every target weight and
the whole eighteen-row grid are recomputed here — the weights from the *sealed* RA2-1 ceiling rather
than from a literal — then compared against the config field by field and against the Markdown row by
row. A disagreement is a refusal.

**It seals once.** If either output already exists the program refuses and changes nothing.

Like Attempt 1's sealer it reads dates, never prices: the only column parsed out of the acquired data
is ``session``, and the measurement is reused from Attempt 1's module rather than reimplemented.
"""

from __future__ import annotations

import json
import re
import sys
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
)
from .g2_partition_lock import RECORD_JSON as PARTITION_LOCK_JSON
from .g2_partition_lock import RECORD_MD as PARTITION_LOCK_MD
from .g2_partition_lock import RECORD_SHA as PARTITION_LOCK_SHA
from .g2_rotation_preregistration import (
    FREQUENCIES,
    LOOKBACKS,
    POSITION_COUNTS,
    WEIGHT_QUANTUM,
    measure_span,
)
from .g2_rotation_preregistration import RECORD_SHA as ATTEMPT_1_SHA
from .stage_package import (
    PROJECT_ROOT,
    RUNS_DIR,
    TRACKED_DEPENDENCIES,
    new_run_id,
    repo_state,
    verify_sha256_record,
    verify_stage0_freeze,
)

G2_GOVERNANCE = PROJECT_ROOT / "governance" / "generation_2"
G2_CONFIG = PROJECT_ROOT / "config" / "generation_2"

RECORD_MD = G2_GOVERNANCE / "STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"
RECORD_JSON = G2_GOVERNANCE / "STAGE_3_G2_ROTATION_RA1_PROTOCOL.json"
RECORD_SHA = G2_GOVERNANCE / "STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256"

PROTOCOL_CONFIG = G2_CONFIG / "g2_rotation_ra1_protocol.json"
CRITERIA_CONFIG = G2_CONFIG / "g2_gate_criteria_ra1.json"
COST_CONFIG = G2_CONFIG / "g2_cost_model.json"

DOCUMENT_ID = "SE100-GOV-2005"
PARTITION_LOCK_ID = "SE100-GOV-2002"
ATTEMPT_1_DOCUMENT_ID = "SE100-GOV-2003"

# The run record whose ``code_hashes`` are the recorded digests of Attempt 1's nine modules. Located
# by stage rather than by filename, and required to be unique, so that a second record with the same
# stage is a refusal instead of a silent choice between two.
ATTEMPT_1_RUN_STAGE = "STAGE_3_G2_ROTATION_DEVELOPMENT"

# Directories this attempt writes into. Both must be absent at seal time: a pre-registration written
# after its own results exist is not a pre-registration.
ATTEMPT_2_REPORT_DIR = PROJECT_ROOT / "reports" / "stage3_g2_attempt2"

BINDING_RULES = (
    "The grid is complete at eighteen variants and is the same eighteen Attempt 1 declared. No "
    "variant is added, removed, re-parameterised, or widened under any result.",
    "The five RA2 constants are frozen before any variant is run and are applied uniformly to all "
    "eighteen. None of them is an axis of the grid, and none is tuned after seeing a result.",
    "The representative-selection rule is applied exactly as sealed, on research-shutdown counts, "
    "fill counts, and variant ids alone. No return, drawdown, profit factor, or equity level is an "
    "input to it.",
    "Gate 3 is evaluated on the selected representative only, and both of its runs must satisfy "
    "every condition. The runner-up is never promoted.",
    "No parameter, threshold, symbol, weight, or rule may be chosen using any value inside the "
    "validation window or either holdout window.",
    "Every Generation 1 artifact and every Generation 2 Attempt 1 artifact is read-only. Attempt "
    "1's verdict stands; nothing here reopens, re-runs, loosens, or supersedes it.",
    "A defect discovered after this seal is reported and its effect disclosed. This artifact is "
    "superseded by a new id if it is wrong; it is never edited in place.",
    "Stage 4 validation for Generation 2 requires a separate, explicitly authorized session. "
    "Nothing sealed here, and no result produced under it, authorizes one.",
    "live_trading_authorized remains false. This artifact authorizes no order, no broker "
    "connection, no credential read, and no scheduling of either.",
)


# --------------------------------------------------------------------------------------------- #
# Values derived from the sealed config rather than restated here
# --------------------------------------------------------------------------------------------- #

def candidate_id(protocol: dict[str, Any]) -> str:
    """This attempt's candidate id, loaded, never written as a literal. See the module docstring."""
    value = protocol.get("strategy_id")
    if not isinstance(value, str) or not value:
        raise RuntimeError("the sealed protocol config carries no strategy_id")
    return value


def exposure_ceiling(protocol: dict[str, Any]) -> Decimal:
    """RA2-1's aggregate exposure ceiling, read from the sealed risk architecture."""
    return Decimal(protocol["risk_architecture"]["components"]["RA2-1"]["value"])


def concentration_ceiling(protocol: dict[str, Any]) -> Decimal:
    return Decimal(protocol["concentration_ceiling"]["value"])


def target_weight(k: int, ceiling: Decimal, concentration: Decimal) -> Decimal:
    """``w(k) = min(ceiling / k, concentration)`` quantized to nine decimals, ROUND_DOWN.

    ROUND_DOWN rather than the engine's ROUND_HALF_EVEN for the reason Attempt 1 gave: at k=3 the
    half-even value times three exceeds the ceiling in a far decimal place, which would make the
    aggregate clamp bind on the third buy of every rebalance for a pure representation reason. Under
    Attempt 2 that clamp is RA2-1's, so the same ulp would look like a risk-architecture event.
    """
    raw = min(ceiling / Decimal(k), concentration)
    return raw.quantize(WEIGHT_QUANTUM, rounding=ROUND_DOWN)


def enumerate_grid(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    """The eighteen variants, in the declared order: lookback outer, k, frequency inner.

    Variant ids are produced from the config's own ``variant_id_format`` template, which is the same
    indirection the candidate id uses.
    """
    template = protocol["grid"]["variant_id_format"]
    strategy = candidate_id(protocol)
    if not template.startswith(strategy):
        raise RuntimeError(f"grid.variant_id_format does not begin with the strategy_id: {template}")
    ceiling = exposure_ceiling(protocol)
    concentration = concentration_ceiling(protocol)

    rows: list[dict[str, Any]] = []
    for lookback in LOOKBACKS:
        for k in POSITION_COUNTS:
            weight = target_weight(k, ceiling, concentration)
            for frequency in FREQUENCIES:
                rows.append(
                    {
                        "index": len(rows) + 1,
                        "variant_id": template.format(lookback=lookback, k=k, FREQUENCY=frequency),
                        "lookback_months": lookback,
                        "top_k": k,
                        "rebalance_frequency": frequency,
                        "target_weight_per_position": f"{weight:.9f}",
                    }
                )
    return rows


# --------------------------------------------------------------------------------------------- #
# Precondition: no Attempt 2 code, results, or run records yet, and Attempt 1 untouched
# --------------------------------------------------------------------------------------------- #

def attempt_1_run_record() -> tuple[Path, dict[str, Any]]:
    """Locate the single Attempt 1 development run record that recorded the module digests."""
    matches: list[tuple[Path, dict[str, Any]]] = []
    if RUNS_DIR.exists():
        for record in sorted(RUNS_DIR.glob("*.json")):
            try:
                body = json.loads(record.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if body.get("stage") == ATTEMPT_1_RUN_STAGE:
                matches.append((record, body))
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one runs/ record with stage {ATTEMPT_1_RUN_STAGE}, found "
            f"{[p.name for p, _ in matches]}"
        )
    return matches[0]


def measure_contamination(protocol: dict[str, Any]) -> dict[str, Any]:
    """Measure the content-based precondition, and Attempt 1's immutability alongside it."""
    strategy = candidate_id(protocol)
    src = PROJECT_ROOT / "src" / "stockedge100"
    tests = PROJECT_ROOT / "tests"

    def naming(root: Path) -> list[str]:
        if not root.exists():
            return []
        found = []
        for path in sorted(root.rglob("*.py")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if strategy in text:
                found.append(path.relative_to(PROJECT_ROOT).as_posix())
        return found

    src_naming = naming(src)
    tests_naming = naming(tests)
    scanned = sum(1 for _ in src.rglob("*.py")) + sum(1 for _ in tests.rglob("*.py"))

    record_path, record = attempt_1_run_record()
    recorded = record.get("code_hashes", {})
    modules = list(protocol["attempt_1_modules_immutable"]["modules"])
    module_digests: dict[str, str] = {}
    module_drift: list[str] = []
    module_unrecorded: list[str] = []
    for module in modules:
        path = PROJECT_ROOT / module
        if not path.exists():
            module_drift.append(f"{module}: MISSING from disk")
            continue
        digest = sha256_file(path)
        module_digests[module] = digest
        if module not in recorded:
            module_unrecorded.append(module)
        elif recorded[module] != digest:
            module_drift.append(f"{module}: recorded {recorded[module]}, measured {digest}")

    pinned = protocol["attempt_1_ref"]
    artifact_drift: list[str] = []
    artifact_digests: dict[str, str] = {}
    for key, value in sorted(pinned.items()):
        if not key.endswith("_sha256") or not isinstance(value, str):
            continue
        path_key = key[: -len("_sha256")]
        relative = pinned.get(path_key)
        if not isinstance(relative, str):
            artifact_drift.append(f"{key} pins a digest but {path_key} names no path")
            continue
        target = PROJECT_ROOT / relative
        if not target.exists():
            artifact_drift.append(f"{relative}: MISSING from disk")
            continue
        digest = sha256_file(target)
        artifact_digests[relative] = digest
        if digest != value:
            artifact_drift.append(f"{relative}: pinned {value}, measured {digest}")

    report_artifacts = (
        sorted(p.relative_to(PROJECT_ROOT).as_posix() for p in ATTEMPT_2_REPORT_DIR.rglob("*"))
        if ATTEMPT_2_REPORT_DIR.exists()
        else []
    )

    foreign_runs: list[str] = []
    if RUNS_DIR.exists():
        for path in sorted(RUNS_DIR.glob("*.json")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if strategy in text:
                foreign_runs.append(path.name)

    return {
        "contamination_predicate": "CONTENT_BASED",
        "predicate": protocol["declared_before_any_strategy_code_measurement"]["predicate"],
        "python_files_scanned": scanned,
        "modules_naming_this_candidate": src_naming,
        "tests_naming_this_candidate": tests_naming,
        "modules_naming_this_candidate_count": len(src_naming),
        "tests_naming_this_candidate_count": len(tests_naming),
        "sealer_names_the_candidate": False,
        "sealer_indirection": (
            "This module loads strategy_id from config/generation_2/g2_rotation_ra1_protocol.json "
            "at run time. It is itself scanned by the predicate above and satisfies it."
        ),
        "attempt_1_immutability_source": record_path.relative_to(PROJECT_ROOT).as_posix(),
        "attempt_1_module_count": len(modules),
        "attempt_1_module_digests": module_digests,
        "attempt_1_modules_that_moved": module_drift,
        "attempt_1_modules_not_in_the_run_record": module_unrecorded,
        "attempt_1_artifact_digests": artifact_digests,
        "attempt_1_artifacts_that_moved": artifact_drift,
        "attempt_2_report_artifacts": report_artifacts,
        "run_records_naming_this_candidate": foreign_runs,
    }


def contamination_problems(measured: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if measured["modules_naming_this_candidate"]:
        problems.append(
            "module(s) under src/stockedge100 already name this candidate: "
            f"{measured['modules_naming_this_candidate']}"
        )
    if measured["tests_naming_this_candidate"]:
        problems.append(
            f"test module(s) already name this candidate: {measured['tests_naming_this_candidate']}"
        )
    if measured["python_files_scanned"] == 0:
        problems.append("the contamination scan read zero Python files, so it proved nothing")
    if measured["attempt_1_module_count"] != 9:
        problems.append(
            f"attempt_1_modules_immutable lists {measured['attempt_1_module_count']} modules, not 9"
        )
    for label in ("attempt_1_modules_that_moved", "attempt_1_artifacts_that_moved"):
        if measured[label]:
            problems.append(f"{label}: {measured[label]}")
    if measured["attempt_1_modules_not_in_the_run_record"]:
        problems.append(
            "no recorded digest exists for Attempt 1 module(s): "
            f"{measured['attempt_1_modules_not_in_the_run_record']}"
        )
    if measured["attempt_2_report_artifacts"]:
        problems.append(
            f"an Attempt 2 report directory already exists: {measured['attempt_2_report_artifacts'][:5]}"
        )
    if measured["run_records_naming_this_candidate"]:
        problems.append(
            "a runs/ record already names this candidate: "
            f"{measured['run_records_naming_this_candidate']}"
        )
    return problems


# --------------------------------------------------------------------------------------------- #
# Agreement: sealed config JSON against the measurement
# --------------------------------------------------------------------------------------------- #

def check_config_agreement(config: dict[str, Any], span: dict[str, Any]) -> list[str]:
    """Every claim the sealed config makes that this module can independently recompute."""
    problems: list[str] = []
    expected = enumerate_grid(config)
    ceiling = exposure_ceiling(config)
    concentration = concentration_ceiling(config)

    grid = config.get("grid", {})
    if grid.get("size") != len(expected):
        problems.append(f"grid.size is {grid.get('size')}, recomputed {len(expected)}")
    axes = grid.get("axes", {})
    if tuple(axes.get("lookback_months", ())) != LOOKBACKS:
        problems.append(f"grid.axes.lookback_months is {axes.get('lookback_months')}")
    if tuple(axes.get("top_k", ())) != POSITION_COUNTS:
        problems.append(f"grid.axes.top_k is {axes.get('top_k')}")
    if tuple(axes.get("rebalance_frequency", ())) != FREQUENCIES:
        problems.append(f"grid.axes.rebalance_frequency is {axes.get('rebalance_frequency')}")

    declared = grid.get("variants", [])
    if len(declared) != len(expected):
        problems.append(f"grid.variants has {len(declared)} entries, recomputed {len(expected)}")
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
        ("sessions", span["run_sessions"]),
        ("binding_symbol", span["binding_symbol"]),
        ("binding_symbol_inception", span["binding_symbol_inception"]),
        ("members_missing_a_bar_at_run_start", span["members_missing_a_bar_at_run_start"]),
        ("symbols_ending_before_run_end", span["symbols_ending_before_run_end"]),
        ("development_union_sessions", span["development_union_sessions"]),
    ):
        if run_span.get(field) != value:
            problems.append(f"run_span.{field} is {run_span.get(field)!r}, measured {value!r}")

    measured_counts = config.get("rebalance", {}).get("measured_counts", {})
    for field, value in (
        ("monthly", span["monthly_rebalance_sessions"]),
        ("quarterly", span["quarterly_rebalance_sessions"]),
        ("monthly_first_three", span["monthly_first_three"]),
        ("quarterly_first_three", span["quarterly_first_three"]),
        ("monthly_last", span["monthly_last_two"][-1]),
        ("quarterly_last", span["quarterly_last_two"][-1]),
    ):
        if measured_counts.get(field) != value:
            problems.append(
                f"rebalance.measured_counts.{field} is {measured_counts.get(field)!r}, "
                f"measured {value!r}"
            )

    sizing = config.get("position_sizing", {})
    for k in POSITION_COUNTS:
        weight = target_weight(k, ceiling, concentration)
        gross = (weight * k).quantize(WEIGHT_QUANTUM)
        if sizing.get("target_weights", {}).get(str(k)) != f"{weight:.9f}":
            problems.append(f"position_sizing.target_weights['{k}'] disagrees with {weight:.9f}")
        if sizing.get("target_gross_exposure", {}).get(str(k)) != f"{gross:.9f}":
            problems.append(
                f"position_sizing.target_gross_exposure['{k}'] disagrees with {gross:.9f}"
            )
        if gross > ceiling:
            problems.append(f"the k={k} aggregate target gross {gross:.9f} exceeds RA2-1 {ceiling}")

    window = config.get("window", {})
    development = window.get("development", {})
    if development.get("from") != DEVELOPMENT_START or development.get("to") != DEVELOPMENT_END:
        problems.append("window.development disagrees with the sealed partition lock")
    if development.get("last_session") != span["run_end"]:
        problems.append(
            f"window.development.last_session is {development.get('last_session')!r}, "
            f"measured {span['run_end']!r}"
        )
    prohibited = {
        (entry.get("from"), entry.get("to")) for entry in window.get("prohibited", [])
    }
    for pair in (
        (VALIDATION_START, VALIDATION_END),
        (GENERATION_1_HOLDOUT_START, GENERATION_1_HOLDOUT_END),
        (HOLDOUT_START, HOLDOUT_END),
    ):
        if pair not in prohibited:
            problems.append(f"window.prohibited does not list {pair}")

    universe = config.get("eligible_universe", {})
    if tuple(universe.get("members", ())) != tuple(UNIVERSE):
        problems.append("eligible_universe.members is not the sealed Generation 1 universe")
    if universe.get("member_count") != len(UNIVERSE):
        problems.append(f"eligible_universe.member_count is {universe.get('member_count')}")
    if universe.get("universe_version") != UNIVERSE_VERSION:
        problems.append(f"eligible_universe.universe_version is {universe.get('universe_version')}")

    runs = config.get("runs_per_variant", {})
    if runs.get("total_runs") != len(expected) * runs.get("count", 0):
        problems.append("runs_per_variant.total_runs is not count times the grid size")

    multiplicity = config.get("multiple_comparisons_disclosure", {})
    cumulative = multiplicity.get("cumulative_variants_this_hypothesis_family")
    if cumulative != multiplicity.get("variants_this_attempt", 0) + multiplicity.get(
        "variants_attempt_1", 0
    ):
        problems.append(f"cumulative_variants_this_hypothesis_family is {cumulative}")

    risk = config.get("risk_architecture", {})
    if risk.get("frozen_before_any_variant_is_run") is not True:
        problems.append("risk_architecture is not marked frozen before any variant is run")
    if risk.get("not_part_of_the_grid") is not True:
        problems.append("risk_architecture is not marked outside the grid")
    components = risk.get("components", {})
    for name in ("RA2-1", "RA2-2", "RA2-3", "RA2-4", "RA2-5"):
        if name not in components:
            problems.append(f"risk_architecture.components is missing {name}")
    bands = components.get("RA2-4", {}).get("bands", [])
    if len(bands) != 4:
        problems.append(f"RA2-4 declares {len(bands)} bands, expected 4")
    else:
        previous = Decimal("0")
        for band in bands:
            if Decimal(band["dd_from"]) != previous:
                problems.append(f"RA2-4 band {band['band']} does not start where the previous ended")
            upper = band.get("dd_to_exclusive")
            previous = Decimal(upper) if upper is not None else previous
        deepest = Decimal(bands[-1]["dd_from"])
        if deepest >= Decimal("0.15"):
            problems.append(
                f"RA2-4's deepest rung at {deepest} is at or beyond the 15% research shutdown"
            )

    if config.get("live_trading_authorized") is not False:
        problems.append("the protocol config does not carry live_trading_authorized false")
    if config.get("declared_before_any_strategy_code") is not True:
        problems.append("the protocol config does not claim declared_before_any_strategy_code")
    if config.get("attempt") != 2:
        problems.append(f"attempt is {config.get('attempt')}, expected 2")

    return problems


def check_criteria_agreement(criteria: dict[str, Any], protocol: dict[str, Any]) -> list[str]:
    """The two verdict tokens must already be sealed, as a pair, and belong to this attempt."""
    problems: list[str] = []
    derivation = criteria.get("verdict_token_derivation", {})
    pass_token = derivation.get("pass_token")
    fail_token = derivation.get("fail_token")
    for label, token in (("pass_token", pass_token), ("fail_token", fail_token)):
        if not isinstance(token, str) or "ATTEMPT_2" not in token:
            problems.append(f"gate criteria {label} is {token!r}, which does not name Attempt 2")
    if pass_token == fail_token:
        problems.append("the gate criteria pass and fail tokens are the same string")
    if criteria.get("live_trading_authorized") is not False:
        problems.append("gate criteria do not carry live_trading_authorized false")
    if criteria.get("attempt") != protocol.get("attempt"):
        problems.append(
            f"gate criteria attempt is {criteria.get('attempt')!r}, protocol says "
            f"{protocol.get('attempt')!r}"
        )
    if protocol.get("gate_criteria_ref") != CRITERIA_CONFIG.relative_to(PROJECT_ROOT).as_posix():
        problems.append(
            f"the protocol's gate_criteria_ref is {protocol.get('gate_criteria_ref')!r}"
        )
    return problems


# --------------------------------------------------------------------------------------------- #
# Agreement: Markdown against the measurement
# --------------------------------------------------------------------------------------------- #

def _norm_predicate(text: str) -> str:
    """Strip the Markdown's code ticks and its trailing path slashes, collapse whitespace.

    The Markdown writes the scanned roots as paths -- ``src/stockedge100/`` and ``tests/`` -- while
    the sealed predicate names them without the trailing slash. That is presentation, not a
    difference in what is claimed, so it is normalised away on both sides rather than tolerated as a
    substring match on one.
    """
    collapsed = re.sub(r"\s+", " ", text.replace("`", "").replace("/ ", " "))
    return collapsed.strip().rstrip(".")


def check_document_agreement(
    document: str, protocol: dict[str, Any], span: dict[str, Any]
) -> list[str]:
    """Every claim the Markdown makes that this module can independently check.

    Two normalisations, because the two kinds of claim survive different damage. ``normalised_prose``
    strips backticks and blockquote markers, which is what a quoted paragraph needs and what a table
    row cannot survive -- a variant id is written ```SE100-...``` and the ticks are part of
    the cell. Prose is checked against the stripped form, table rows and backticked identifiers
    against a whitespace-collapsed copy of the raw document. The Markdown is hard-wrapped at 100
    columns, so neither can be checked against the document line by line.
    """
    flat = normalised_prose(document)
    raw = re.sub(r"\s+", " ", document)
    problems: list[str] = []
    ceiling = exposure_ceiling(protocol)
    concentration = concentration_ceiling(protocol)

    disclosure = protocol["adaptation_disclosure_verbatim"]
    if normalised_prose(disclosure) not in flat:
        problems.append(
            "the mandated adaptation disclosure is missing from the Markdown or was altered"
        )
    if normalised_prose(VALIDATION_REUSE_DISCLOSURE) not in flat:
        problems.append(
            "the mandated validation-reuse disclosure is missing from the Markdown or was altered"
        )

    criteria = json.loads(CRITERIA_CONFIG.read_text(encoding="utf-8"))
    derivation = criteria.get("verdict_token_derivation", {})
    required = {
        "document id": DOCUMENT_ID,
        "charter id": CHARTER_ID,
        "partition lock id": PARTITION_LOCK_ID,
        "attempt 1 document id": ATTEMPT_1_DOCUMENT_ID,
        "generation id": generation_identity()["generation_id"],
        "strategy id": candidate_id(protocol),
        "family": protocol["family"],
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
        "pass token": derivation.get("pass_token", ""),
        "fail token": derivation.get("fail_token", ""),
        "attempt 1 verdict": protocol["attempt_1_ref"]["verdict"].replace(" - ", " — "),
    }
    for label, value in required.items():
        if not value or value not in flat:
            problems.append(f"the Markdown does not state the measured {label} ({value})")

    if span["binding_symbol"] and span["binding_symbol"] not in flat:
        problems.append(f"the Markdown does not name the binding symbol {span['binding_symbol']}")

    # The grid table, row by row, rebuilt from the recomputed grid and the measured calendars.
    counts = {
        "MONTHLY": span["monthly_rebalance_sessions"],
        "QUARTERLY": span["quarterly_rebalance_sessions"],
    }
    for row in enumerate_grid(protocol):
        gross = (
            Decimal(row["target_weight_per_position"]) * row["top_k"]
        ).quantize(WEIGHT_QUANTUM)
        expected = (
            f"| {row['index']} | `{row['variant_id']}` | {row['lookback_months']} | {row['top_k']} "
            f"| {row['rebalance_frequency']} | {row['target_weight_per_position']} "
            f"| {gross:.9f} | {counts[row['rebalance_frequency']]} |"
        )
        if expected not in raw:
            problems.append(f"the Markdown grid table does not carry the row for {row['variant_id']}")

    # The weight table, rebuilt from the same arithmetic the engine will use.
    for k in POSITION_COUNTS:
        weight = target_weight(k, ceiling, concentration)
        gross = (weight * k).quantize(WEIGHT_QUANTUM)
        if f"| {k} | {weight:.9f} | {gross:.9f} |" not in raw:
            problems.append(f"the Markdown weight table does not carry the row for k={k}")

    # The rebalance calendar, measured here rather than read from the config.
    for frequency, count, first_three, last in (
        (
            "MONTHLY",
            span["monthly_rebalance_sessions"],
            span["monthly_first_three"],
            span["monthly_last_two"][-1],
        ),
        (
            "QUARTERLY",
            span["quarterly_rebalance_sessions"],
            span["quarterly_first_three"],
            span["quarterly_last_two"][-1],
        ),
    ):
        if f"| `{frequency}` | {count} |" not in raw:
            problems.append(f"the Markdown does not carry the measured {frequency} rebalance count")
        if ", ".join(first_three) not in raw:
            problems.append(f"the Markdown does not carry the first three {frequency} rebalances")
        if last not in raw:
            problems.append(f"the Markdown does not carry the last {frequency} rebalance {last}")

    # Attempt 1's immutable modules, named individually, so a sweep of strategies/ alone is visibly
    # insufficient. Two of the nine live under backtest/.
    for module in protocol["attempt_1_modules_immutable"]["modules"]:
        if f"`{module}`" not in raw:
            problems.append(f"the Markdown does not name the immutable Attempt 1 module {module}")

    # The contamination predicate, quoted rather than paraphrased. Compared as an equality after the
    # same normalisation is applied to both sides, so a paraphrase that happens to contain the
    # sealed wording as a substring is not accepted in place of the quotation.
    predicate = protocol["declared_before_any_strategy_code_measurement"]["predicate"]
    quoted = re.search(r"\n((?:> .*\n)+)", document[document.index("## 13.") :])
    if quoted is None:
        problems.append("section 13 of the Markdown carries no blockquote")
    else:
        got = " ".join(line[2:].strip() for line in quoted.group(1).strip().splitlines())
        if _norm_predicate(got) != _norm_predicate(predicate):
            problems.append(
                "the Markdown's quoted contamination predicate is not the sealed predicate:\n"
                f"      markdown: {_norm_predicate(got)}\n"
                f"      sealed:   {_norm_predicate(predicate)}"
            )

    # Every conflict the config found, and no conflict id the config does not carry.
    declared = {entry["id"] for entry in protocol.get("conflicts_found", [])}
    for identifier in sorted(declared):
        if identifier not in flat:
            problems.append(f"the Markdown does not carry {identifier}")

    # A pre-registration must not carry a tree digest or its own digest; it may pin frozen inputs.
    own = sha256_file(RECORD_MD)
    if own in document:
        problems.append("the Markdown contains its own SHA-256, which cannot be true of a sealed file")

    return problems


# --------------------------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------------------------- #

def build() -> int:
    if RECORD_JSON.exists() or RECORD_SHA.exists():
        print("REFUSED: the Attempt 2 pre-registration is already sealed.")
        print(f"  {RECORD_JSON.relative_to(PROJECT_ROOT).as_posix()}: {RECORD_JSON.exists()}")
        print(f"  {RECORD_SHA.relative_to(PROJECT_ROOT).as_posix()}: {RECORD_SHA.exists()}")
        print("A pre-registration is sealed once. Regenerating it would destroy its meaning.")
        return 2

    prerequisites = (
        CHARTER_MD,
        PARTITION_LOCK_MD,
        PARTITION_LOCK_JSON,
        PARTITION_LOCK_SHA,
        ATTEMPT_1_SHA,
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

    partition_freeze = verify_sha256_record(PARTITION_LOCK_SHA, root=PROJECT_ROOT)
    if any(state != "OK" for state in partition_freeze.values()):
        print("REFUSED: the Generation 2 partition lock record does not verify.")
        for name, state in sorted(partition_freeze.items()):
            print(f"  {name}: {state}")
        return 6

    attempt_1_freeze = verify_sha256_record(ATTEMPT_1_SHA, root=PROJECT_ROOT)
    if any(state != "OK" for state in attempt_1_freeze.values()):
        print("REFUSED: Attempt 1's sealed pre-registration record does not verify.")
        for name, state in sorted(attempt_1_freeze.items()):
            print(f"  {name}: {state}")
        return 7

    protocol = json.loads(PROTOCOL_CONFIG.read_text(encoding="utf-8"))
    criteria = json.loads(CRITERIA_CONFIG.read_text(encoding="utf-8"))

    contamination = measure_contamination(protocol)
    problems = contamination_problems(contamination)
    if problems:
        print("REFUSED: the precondition this pre-registration claims does not hold.")
        for problem in problems:
            print(f"  - {problem}")
        return 8

    span = measure_span()
    if not span["session_lists_agree"]:
        print("REFUSED: the exchange calendar and the union of member bars disagree over the run.")
        print(f"  union sessions    {span['run_sessions']}")
        print(f"  calendar sessions {span['exchange_calendar_sessions']}")
        return 9

    problems = check_config_agreement(protocol, span) + check_criteria_agreement(criteria, protocol)
    if problems:
        print("REFUSED: the sealed configuration and the measured data disagree.")
        for problem in problems:
            print(f"  - {problem}")
        return 10

    problems = check_document_agreement(RECORD_MD.read_text(encoding="utf-8"), protocol, span)
    if problems:
        print("REFUSED: the Markdown protocol and the measured data disagree.")
        for problem in problems:
            print(f"  - {problem}")
        return 11

    identity = generation_identity()
    timestamp = utc_now_iso()
    run_id = new_run_id(timestamp)
    strategy = candidate_id(protocol)
    derivation = criteria["verdict_token_derivation"]

    sealed_inputs = {
        "config/generation_2/g2_rotation_ra1_protocol.json": sha256_file(PROTOCOL_CONFIG),
        "config/generation_2/g2_gate_criteria_ra1.json": sha256_file(CRITERIA_CONFIG),
        "config/generation_2/g2_cost_model.json": sha256_file(COST_CONFIG),
        "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md": sha256_file(CHARTER_MD),
        "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md": sha256_file(PARTITION_LOCK_MD),
        "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json": sha256_file(PARTITION_LOCK_JSON),
    }

    grid = enumerate_grid(protocol)
    ceiling = exposure_ceiling(protocol)
    concentration = concentration_ceiling(protocol)
    record: dict[str, Any] = {
        "artifact_id": DOCUMENT_ID,
        "title": (
            "Generation 2 Stage 3 Attempt 2 cross-sectional rotation pre-registration under risk "
            "architecture RA2"
        ),
        "status": "SEALED",
        "project": "StockEdge100",
        "generation": 2,
        "generation_id": identity["generation_id"],
        "stage": 3,
        "gate_id": 3,
        "attempt": 2,
        "sealed_utc": timestamp,
        "run_id": run_id,
        "charter_ref": f"governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md ({CHARTER_ID})",
        "partition_lock_ref": (
            f"governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md ({PARTITION_LOCK_ID})"
        ),
        "constitution_ref": protocol["constitution_ref"],
        "markdown_counterpart": "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md",
        "source_of_record": "config/generation_2/g2_rotation_ra1_protocol.json",
        "attempt_1_ref": {
            "artifact_id": ATTEMPT_1_DOCUMENT_ID,
            "strategy_id": protocol["attempt_1_ref"]["strategy_id"],
            "verdict": protocol["attempt_1_ref"]["verdict"],
            "disposition": protocol["attempt_1_ref"]["disposition"],
            "record_verified_here": ATTEMPT_1_SHA.relative_to(PROJECT_ROOT).as_posix(),
            "record_verification": attempt_1_freeze,
            "pinned_artifact_digests_reverified": contamination["attempt_1_artifact_digests"],
        },
        "sealed_before_any_strategy_code": True,
        "sealed_before_any_variant_is_run": True,
        "sealed_before_any_result_was_seen": False,
        "sealed_before_any_result_was_seen_note": (
            "False, and stated as such. This pre-registration was designed after Attempt 1's "
            "development results were known. See adaptation_disclosure."
        ),
        "contamination_measurement": contamination,
        "sealed_inputs": sealed_inputs,
        "strategy": {
            "strategy_id": strategy,
            "candidate_index": protocol["candidate_index"],
            "family": protocol["family"],
            "hypothesis": protocol["hypothesis"],
            "candidate_count": 1,
            "universe_version": UNIVERSE_VERSION,
            "member_count": len(UNIVERSE),
            "members": list(UNIVERSE),
        },
        "risk_architecture": {
            "id": protocol["risk_architecture"]["id"],
            "frozen_before_any_variant_is_run": True,
            "not_part_of_the_grid": True,
            "components": {
                name: {
                    "name": body.get("name"),
                    "value": body.get("value"),
                    "unit": body.get("unit"),
                }
                for name, body in protocol["risk_architecture"]["components"].items()
            },
            "ladder_bands": protocol["risk_architecture"]["components"]["RA2-4"]["bands"],
            "combined_scalar": protocol["risk_architecture"]["combined_scalar"]["formula"],
            "recomputed_here": (
                "The per-position weights below are derived from RA2-1's ceiling by this program, "
                "not copied from the config, so a change to the ceiling that was not carried into "
                "the weight table would refuse the seal."
            ),
        },
        "position_sizing": {
            "formula": protocol["position_sizing"]["target_weight_formula"],
            "aggregate_ceiling": f"{ceiling:.9f}",
            "concentration_ceiling": f"{concentration:.9f}",
            "target_weights": {
                str(k): f"{target_weight(k, ceiling, concentration):.9f}" for k in POSITION_COUNTS
            },
            "target_gross_exposure": {
                str(k): (
                    f"{(target_weight(k, ceiling, concentration) * k).quantize(WEIGHT_QUANTUM):.9f}"
                )
                for k in POSITION_COUNTS
            },
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
            "unchanged_from_attempt_1": True,
            "recomputed_here": (
                "Every field above is recomputed by this program from the declared axes, the "
                "config's own variant id template, and decimal arithmetic, then compared field by "
                "field against the sealed config and row by row against the Markdown."
            ),
        },
        "run_span_measured_from_disk": span,
        "representative_selection_rule": protocol["representative_selection_rule"],
        "gate": {
            "criteria_file": "config/generation_2/g2_gate_criteria_ra1.json",
            "criteria_sha256": sealed_inputs["config/generation_2/g2_gate_criteria_ra1.json"],
            "evaluated_on": protocol["gate_evaluation_scope"]["evaluated_on"],
            "conjunctive_within_candidate": True,
            "thresholds_changed_from_attempt_1": (
                protocol["gate_evaluation_scope"]["thresholds_changed_from_attempt_1"]
            ),
            "pass_token": derivation["pass_token"],
            "fail_token": derivation["fail_token"],
            "tokens_taken_from": "config/generation_2/g2_gate_criteria_ra1.json",
        },
        "multiple_comparisons_disclosure": protocol["multiple_comparisons_disclosure"],
        "adaptation_disclosure": protocol["adaptation_disclosure_verbatim"],
        "adaptation_disclosure_carriage_requirement": (
            protocol["adaptation_disclosure_carriage_requirement"]
        ),
        "structural_consequences_declared_before_running": (
            protocol["structural_consequences_declared_before_running"]
        ),
        "adversarial_test_requirements": protocol["adversarial_test_requirements"],
        "reproducibility_requirements": protocol["reproducibility_requirements"],
        "conflicts_found": protocol["conflicts_found"],
        "post_seal_defect_rule": protocol["post_seal_defect_rule"],
        "windows": {
            "authorized": ["development"],
            "development": [DEVELOPMENT_START, DEVELOPMENT_END],
            "validation": [VALIDATION_START, VALIDATION_END],
            "generation_1_holdout": [GENERATION_1_HOLDOUT_START, GENERATION_1_HOLDOUT_END],
            "generation_2_holdout": [HOLDOUT_START, HOLDOUT_END],
            "enforcement": protocol["window"]["enforcement"],
        },
        "validation_reuse_disclosure": VALIDATION_REUSE_DISCLOSURE,
        "validation_reuse_disclosure_note": (
            "Reproduced verbatim because this artifact names the validation window. Nothing in "
            "Stage 3 Attempt 2 reads it."
        ),
        "binding_rules": list(BINDING_RULES),
        "explicit_non_authorizations": protocol["explicit_non_authorizations"],
        "repo_state_id_location": (
            "Deliberately omitted here. governance/generation_2/ is not reached by the "
            "repo_state_id patterns (governance/*.md is single-level), so this file is covered by "
            "STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256 instead. The binding repo_state_id for this "
            f"seal is the repo_state_id field of runs/{run_id}.json. Recorded as G2A2-CONFLICT-10."
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
        "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md": sha256_file(RECORD_MD),
        "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json": sha256_file(RECORD_JSON),
        "config/generation_2/g2_rotation_ra1_protocol.json": sha256_file(PROTOCOL_CONFIG),
        "config/generation_2/g2_gate_criteria_ra1.json": sha256_file(CRITERIA_CONFIG),
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
        stage="stage_3_generation_2_rotation_attempt_2_preregistration",
        command="python -m stockedge100.reporting.g2_rotation_ra1_preregistration",
        timestamp_utc=timestamp,
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=sealed_inputs["config/generation_2/g2_rotation_ra1_protocol.json"],
        dataset_hashes=dataset_hashes,
        universe_version=UNIVERSE_VERSION,
        date_range=[DEVELOPMENT_START, DEVELOPMENT_END],
        holdout_state="SEALED",
        strategy_id=strategy,
        random_seed=None,
        dependency_versions=dependency_versions(TRACKED_DEPENDENCIES),
        exit_status="SEALED",
        output_artifact_hashes={
            **covered,
            "STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256": own_digest,
        },
        notes=[
            "Attempt 2 of Generation 2 Stage 3. Attempt 1 closed FAIL - STAGE_3_G2_NO_CANDIDATE and "
            "is read-only; this seal verified its .sha256 record and re-hashed its nine modules and "
            "nine pinned artifacts against their recorded digests before writing anything.",
            "This pre-registration was designed after Attempt 1's development results were known. "
            "The development window is no longer pristine for this hypothesis family. The mandated "
            "disclosure is carried verbatim in the sealed JSON and in the Markdown.",
            f"Eighteen variants declared in full before any is run; "
            f"{record['grid']['total_runs']} runs total across the base and stress cost "
            "assumptions. The grid is Attempt 1's grid, not widened.",
            f"Run span {span['run_start']} to {span['run_end']}, {span['run_sessions']} sessions, "
            f"common to all eighteen variants; binding symbol {span['binding_symbol']} with "
            f"inception {span['binding_symbol_inception']}.",
            "Risk architecture RA2: five constants frozen before any variant is run, applied "
            "uniformly to all eighteen, none of them an axis of the grid. The per-position weights "
            "were rederived here from RA2-1's ceiling rather than copied from the config.",
            "Contamination measured before writing, content-based: "
            f"{contamination['python_files_scanned']} Python files scanned under src/ and tests/, "
            "zero naming this candidate. This sealer loads the candidate id from the config at run "
            "time so it satisfies its own predicate. Recorded as G2A2-CONFLICT-3.",
            "governance/generation_2/ is outside REPO_STATE_PATTERNS; the .sha256 record and this "
            "run record are what cover those files. config/generation_2/*.json is inside them and "
            "is additionally covered by the .sha256 record. Recorded as G2A2-CONFLICT-10.",
            "Measurement read the session date column and the exchange calendar only. No price, "
            "volume, or dividend field was parsed by this program in any window.",
            "Stage 4 validation is not authorized by this seal.",
        ],
    ).write(RUNS_DIR)

    print("Generation 2 Stage 3 Attempt 2 pre-registration SEALED")
    print(f"  generation_id  {identity['generation_id']}")
    print(f"  strategy_id    {strategy}")
    print(f"  run_id         {run_id}")
    print(f"  sealed_utc     {timestamp}")
    print(f"  repo_state_id  {repo_state_id}")
    print(f"  grid           {len(grid)} variants x {record['grid']['runs_per_variant']} runs "
          f"= {record['grid']['total_runs']} runs")
    print(f"  run span       {span['run_start']} -> {span['run_end']} "
          f"({span['run_sessions']} sessions)")
    print(f"  rebalances     monthly {span['monthly_rebalance_sessions']}, "
          f"quarterly {span['quarterly_rebalance_sessions']}")
    print(f"  risk arch      RA2, ceiling {ceiling}, "
          f"{len(record['risk_architecture']['ladder_bands'])} ladder bands, not gridded")
    print(f"  contamination  {contamination['python_files_scanned']} .py files scanned, "
          f"{contamination['modules_naming_this_candidate_count']} in src/ and "
          f"{contamination['tests_naming_this_candidate_count']} in tests/ name this candidate")
    print(f"  attempt 1      {contamination['attempt_1_module_count']} modules and "
          f"{len(contamination['attempt_1_artifact_digests'])} artifacts re-hashed, all unchanged")
    print(f"  tokens         {derivation['pass_token']} / {derivation['fail_token']}")
    for name, digest in sorted(covered.items()):
        print(f"  {digest}  {name}")
    print(f"  record digest  {own_digest}")
    return 0


if __name__ == "__main__":
    sys.exit(build())
