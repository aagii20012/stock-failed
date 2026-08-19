"""Seal the Generation 2 Stage 3 **Attempt 3** rotation pre-registration.

Writes ``governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json`` and the ``.sha256`` record
that covers it together with the hand-authored Markdown counterpart and the three Generation 2 config
artifacts this attempt reads. Run once:

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_rotation_ra3_preregistration

It is Attempt 2's sealer with five differences, four of them forced by the fact that two prior
attempts now exist on disk and one by what this attempt actually claims.

**Two prior attempts, not one.** The immutability check covers seventeen modules rather than nine,
and the recorded digests come from two development run records rather than one. Nine of the seventeen
are named by both records, and the check compares each module against *every* record that names it:
a module that changed between Attempt 1's run and Attempt 2's run is a refusal in its own right
(``prior_attempt_modules_that_disagree_between_records``) rather than something hidden by whichever
record happened to be consulted first.

**The Attempt 2 run record is located twice, by two independent routes**, and the routes must agree:
once by scanning ``runs/`` for the declared stage, once by the path the sealed config pins in
``attempt_2_ref.run_record``. Either alone would be a single point of transcription failure.

**The ladder's provenance is checked, not asserted.** This attempt's whole architectural claim is
that RA3-4 restores Generation 1's original RA1-5 ladder and that the single difference from RA2-4 is
the deletion of one tier. Both halves are recomputed here: RA1-5's prose rule is parsed into bands
and cross-checked against the three Generation 1 experiments' own ``ladder_rungs``, RA3's scalars are
converted to absolute ceilings through RA3-1 and required to equal RA1-5's ``f_cap`` values band for
band, and the RA2 to RA3 difference is required to be exactly one deleted tier plus the extension of
the band above it. A provenance claim that cannot survive that arithmetic is a refusal.

**The verdict tokens are checked for non-vacuous exclusion.** The sealed criteria file states that
the four prior-attempt tokens are unavailable here. That statement is worth nothing if no token can
be extracted from it, so the tokens are extracted by pattern, required to number at least four, and
required to share nothing with this attempt's own pair.

Carried unchanged from Attempt 2: the content-based contamination predicate (no ``.py`` file under
``src/stockedge100/`` or ``tests/`` names this attempt's candidate -- and this module is itself such a
file, so it loads the candidate id from the sealed config at run time rather than writing it as a
literal), the recomputation of the run span, both rebalance calendars, every target weight and the
whole eighteen-row grid, and the refusal to seal twice.

Like both prior sealers it reads dates, never prices: the only column parsed out of the acquired data
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
from .g2_rotation_ra1_preregistration import RECORD_SHA as ATTEMPT_2_SHA
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

RECORD_MD = G2_GOVERNANCE / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.md"
RECORD_JSON = G2_GOVERNANCE / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
RECORD_SHA = G2_GOVERNANCE / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256"

PROTOCOL_CONFIG = G2_CONFIG / "g2_rotation_ra3_protocol.json"
CRITERIA_CONFIG = G2_CONFIG / "g2_gate_criteria_ra3.json"
COST_CONFIG = G2_CONFIG / "g2_cost_model.json"

# The two ladder sources. Both are frozen and read-only; both are verified through a sealed .sha256
# record before a single value is parsed out of them.
ATTEMPT_2_PROTOCOL = G2_CONFIG / "g2_rotation_ra1_protocol.json"
GENERATION_1_PROTOCOL = PROJECT_ROOT / "config" / "stage3_attempt2_strategy_protocol.json"
GENERATION_1_SHA = PROJECT_ROOT / "governance" / "STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256"

DOCUMENT_ID = "SE100-GOV-2007"
PARTITION_LOCK_ID = "SE100-GOV-2002"
ATTEMPT_1_DOCUMENT_ID = "SE100-GOV-2003"
ATTEMPT_2_DOCUMENT_ID = "SE100-GOV-2005"

# The run records whose ``code_hashes`` are the recorded digests of the seventeen prior-attempt
# modules. Located by stage rather than by filename, and each required to be unique, so that a second
# record with the same stage is a refusal instead of a silent choice between two.
ATTEMPT_1_RUN_STAGE = "STAGE_3_G2_ROTATION_DEVELOPMENT"
ATTEMPT_2_RUN_STAGE = "STAGE_3_G2_ATTEMPT_2_ROTATION_RA1_DEVELOPMENT"
PRIOR_RUN_STAGES = (ATTEMPT_1_RUN_STAGE, ATTEMPT_2_RUN_STAGE)

# The directory this attempt writes its evidence into. It must be absent at seal time: a
# pre-registration written after its own results exist is not a pre-registration. The two prior
# attempts' report directories exist and are read-only; their presence is not a defect.
ATTEMPT_3_REPORT_DIR = PROJECT_ROOT / "reports" / "stage3_g2_attempt3"

# A value that looks like a repository-relative path rather than a sentence about one. Used to prove
# that every path a sealed ref names is pinned by a digest, with a declared and checked exception.
PATH_SHAPED = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:json|md|sha256|py|csv|yaml|txt)$")

# Generation 1's RA1-5 states its ladder as prose, in absolute f_cap terms, one rule per line. Each
# line is a sentence and ends in a full stop, so the numeric groups are spelled structurally rather
# than as [0-9.]+ -- a greedy character class swallows the terminating period and hands Decimal the
# string "0.50.", which raises ConversionSyntax rather than failing to match.
NUMBER = r"[0-9]+(?:\.[0-9]+)?"
LADDER_RULE = re.compile(
    rf"^(?:(?P<lo>{NUMBER})\s*<=\s*)?dd\s*(?P<op><|>=)\s*(?P<bound>{NUMBER})\s*:\s*"
    rf"f_cap\s*=\s*(?P<cap>{NUMBER})\s*\.?\s*$"
)

BINDING_RULES = (
    "The grid is complete at eighteen variants and is the same eighteen both prior attempts "
    "declared. No variant is added, removed, re-parameterised, or widened under any result.",
    "The five RA3 constants are frozen before any variant is run and are applied uniformly to all "
    "eighteen. None of them is an axis of the grid, and none is tuned after seeing a result.",
    "RA3 differs from RA2 in exactly one place: the de-risk ladder. Four of the five components are "
    "byte-identical to RA2's, and the ladder that replaces RA2-4 is Generation 1's own RA1-5, "
    "restored rather than invented. No new constant enters this architecture.",
    "The representative-selection rule SE100-G2-SEL-2 is applied exactly as sealed, on "
    "research-shutdown counts, fill counts, ladder-descent counts, lockout-arm counts, "
    "stops-filled counts, and variant ids alone. No return, drawdown, profit factor, or equity "
    "level is an input to it, and its scoring dataclass has no field that could carry one.",
    "Gate 3 is evaluated on the selected representative only, and both of its runs must satisfy "
    "every condition. The runner-up is never promoted.",
    "No parameter, threshold, symbol, weight, or rule may be chosen using any value inside the "
    "validation window or either holdout window.",
    "Every Generation 1 artifact and every Generation 2 Attempt 1 and Attempt 2 artifact is "
    "read-only. Both prior verdicts stand; nothing here reopens, re-runs, loosens, or supersedes "
    "either of them.",
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
    value = protocol.get("strategy_id")
    if not isinstance(value, str) or not value:
        raise RuntimeError("the sealed protocol config carries no strategy_id")
    return value


def exposure_ceiling(protocol: dict[str, Any]) -> Decimal:
    return Decimal(protocol["risk_architecture"]["components"]["RA3-1"]["value"])


def concentration_ceiling(protocol: dict[str, Any]) -> Decimal:
    return Decimal(protocol["concentration_ceiling"]["value"])


def target_weight(k: int, ceiling: Decimal, concentration: Decimal) -> Decimal:
    raw = min(ceiling / Decimal(k), concentration)
    return raw.quantize(WEIGHT_QUANTUM, rounding=ROUND_DOWN)


def enumerate_grid(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    """Rebuild all eighteen variants from the declared axes and the config's own id template."""
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


def prior_run_records() -> dict[str, tuple[Path, dict[str, Any]]]:
    """Locate exactly one development run record per prior attempt, by stage rather than filename."""
    found: dict[str, list[tuple[Path, dict[str, Any]]]] = {stage: [] for stage in PRIOR_RUN_STAGES}
    if RUNS_DIR.exists():
        for record in sorted(RUNS_DIR.glob("*.json")):
            try:
                body = json.loads(record.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            stage = body.get("stage")
            if stage in found:
                found[stage].append((record, body))
    located: dict[str, tuple[Path, dict[str, Any]]] = {}
    for stage in PRIOR_RUN_STAGES:
        matches = found[stage]
        if len(matches) != 1:
            raise RuntimeError(
                f"expected exactly one runs/ record with stage {stage}, found "
                f"{[p.name for p, _ in matches]}"
            )
        located[stage] = matches[0]
    return located


# --------------------------------------------------------------------------------------------- #
# Precondition: nothing on disk names this candidate, and nothing prior has moved
# --------------------------------------------------------------------------------------------- #

def measure_contamination(protocol: dict[str, Any]) -> dict[str, Any]:
    """Measure the content-based precondition, and both prior attempts' immutability alongside it."""
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

    records = prior_run_records()

    # Every recorded digest for every module, keyed by module then by the record that recorded it.
    # Merging rather than choosing is the point: a module named by both records with two different
    # digests is a finding, not a coin toss.
    recorded: dict[str, dict[str, str]] = {}
    for stage, (path, body) in records.items():
        for module, digest in (body.get("code_hashes") or {}).items():
            recorded.setdefault(module, {})[path.name] = digest

    immutable = protocol["prior_attempt_modules_immutable"]
    modules = list(immutable["attempt_1_modules"]) + list(immutable["attempt_2_modules"])
    module_digests: dict[str, str] = {}
    module_drift: list[str] = []
    module_unrecorded: list[str] = []
    module_disagreement: list[str] = []
    module_record_coverage: dict[str, int] = {}
    duplicates = sorted({m for m in modules if modules.count(m) > 1})
    for module in modules:
        path = PROJECT_ROOT / module
        if not path.exists():
            module_drift.append(f"{module}: MISSING from disk")
            continue
        digest = sha256_file(path)
        module_digests[module] = digest
        seen = recorded.get(module, {})
        module_record_coverage[module] = len(seen)
        if not seen:
            module_unrecorded.append(module)
        elif len(set(seen.values())) > 1:
            module_disagreement.append(f"{module}: prior run records disagree: {seen}")
        elif digest not in set(seen.values()):
            module_disagreement_free = sorted(set(seen.values()))[0]
            module_drift.append(
                f"{module}: recorded {module_disagreement_free}, measured {digest}"
            )

    # Every artifact either prior ref pins, re-hashed against its pin. The two refs are walked by the
    # same generic ``<name>``/``<name>_sha256`` loop, so a ref that gains a pin gains a check.
    artifact_digests: dict[str, str] = {}
    artifact_drift: list[str] = []
    pinned_counts: dict[str, int] = {}
    unpinned_paths: dict[str, list[str]] = {}
    for ref_name in ("attempt_1_ref", "attempt_2_ref"):
        ref = protocol[ref_name]
        pinned = 0
        for key, value in sorted(ref.items()):
            if not key.endswith("_sha256") or not isinstance(value, str):
                continue
            path_key = key[: -len("_sha256")]
            relative = ref.get(path_key)
            if not isinstance(relative, str):
                artifact_drift.append(
                    f"{ref_name}.{key} pins a digest but {path_key} names no path"
                )
                continue
            target = PROJECT_ROOT / relative
            if not target.exists():
                artifact_drift.append(f"{ref_name}: {relative} MISSING from disk")
                continue
            digest = sha256_file(target)
            artifact_digests[relative] = digest
            pinned += 1
            if digest != value:
                artifact_drift.append(f"{relative}: pinned {value}, measured {digest}")
        pinned_counts[ref_name] = pinned
        unpinned_paths[ref_name] = sorted(
            key
            for key, value in ref.items()
            if isinstance(value, str)
            and PATH_SHAPED.match(value)
            and f"{key}_sha256" not in ref
        )

    # The Attempt 2 run record, found a second way. The by-stage search above and the path the config
    # pins must name the same file, and that file must declare the stage the config says it does.
    attempt_2_path, attempt_2_body = records[ATTEMPT_2_RUN_STAGE]
    declared_run_record = protocol["attempt_2_ref"].get("run_record")
    run_record_routes_agree = (
        isinstance(declared_run_record, str)
        and (PROJECT_ROOT / declared_run_record).exists()
        and (PROJECT_ROOT / declared_run_record).resolve() == attempt_2_path.resolve()
        and attempt_2_body.get("stage") == protocol["attempt_2_ref"].get("run_record_stage")
    )

    report_artifacts = (
        sorted(p.relative_to(PROJECT_ROOT).as_posix() for p in ATTEMPT_3_REPORT_DIR.rglob("*"))
        if ATTEMPT_3_REPORT_DIR.exists()
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
            "This module loads strategy_id from config/generation_2/g2_rotation_ra3_protocol.json "
            "at run time. It is itself scanned by the predicate above and satisfies it."
        ),
        "prior_attempt_immutability_sources": {
            stage: path.relative_to(PROJECT_ROOT).as_posix() for stage, (path, _) in records.items()
        },
        "prior_attempt_module_count": len(modules),
        "prior_attempt_module_duplicates": duplicates,
        "prior_attempt_module_digests": module_digests,
        "prior_attempt_module_record_coverage": module_record_coverage,
        "prior_attempt_modules_that_moved": module_drift,
        "prior_attempt_modules_not_in_any_run_record": module_unrecorded,
        "prior_attempt_modules_that_disagree_between_records": module_disagreement,
        "prior_attempt_artifact_digests": artifact_digests,
        "prior_attempt_artifacts_that_moved": artifact_drift,
        "prior_attempt_pinned_artifact_counts": pinned_counts,
        "prior_attempt_path_shaped_values_without_a_pin": unpinned_paths,
        "attempt_2_run_record_located_by_stage": attempt_2_path.relative_to(
            PROJECT_ROOT
        ).as_posix(),
        "attempt_2_run_record_declared_in_the_config": declared_run_record,
        "attempt_2_run_record_routes_agree": run_record_routes_agree,
        "attempt_3_report_artifacts": report_artifacts,
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
    if measured["prior_attempt_module_count"] != 17:
        problems.append(
            f"prior_attempt_modules_immutable lists {measured['prior_attempt_module_count']} "
            "modules, not 17"
        )
    if measured["prior_attempt_module_duplicates"]:
        problems.append(
            "the immutable module list repeats an entry, so its count overstates its coverage: "
            f"{measured['prior_attempt_module_duplicates']}"
        )
    for label in (
        "prior_attempt_modules_that_moved",
        "prior_attempt_modules_that_disagree_between_records",
        "prior_attempt_artifacts_that_moved",
    ):
        if measured[label]:
            problems.append(f"{label}: {measured[label]}")
    if measured["prior_attempt_modules_not_in_any_run_record"]:
        problems.append(
            "no recorded digest exists for prior-attempt module(s): "
            f"{measured['prior_attempt_modules_not_in_any_run_record']}"
        )
    # Nine of the seventeen predate Attempt 2 and are named by both development run records. If none
    # were, the merge above would be doing nothing and the disagreement check would be vacuous.
    doubly_covered = sum(
        1 for count in measured["prior_attempt_module_record_coverage"].values() if count > 1
    )
    if doubly_covered == 0:
        problems.append(
            "no prior-attempt module is named by more than one run record, so the cross-record "
            "immutability comparison proved nothing"
        )
    for ref_name, expected in (("attempt_1_ref", 9), ("attempt_2_ref", 9)):
        got = measured["prior_attempt_pinned_artifact_counts"].get(ref_name, 0)
        if got != expected:
            problems.append(f"{ref_name} pins {got} artifact digests, expected {expected}")
    if measured["prior_attempt_path_shaped_values_without_a_pin"].get("attempt_1_ref"):
        problems.append(
            "attempt_1_ref names a path it does not pin: "
            f"{measured['prior_attempt_path_shaped_values_without_a_pin']['attempt_1_ref']}"
        )
    # The one declared exception: a runs/ record is append-only and carries its own repo_state_id, so
    # it is referenced by path and not pinned by digest. Any other unpinned path is a defect.
    unpinned_2 = measured["prior_attempt_path_shaped_values_without_a_pin"].get("attempt_2_ref", [])
    if unpinned_2 != ["run_record"]:
        problems.append(
            f"attempt_2_ref's unpinned path-shaped values are {unpinned_2}, expected ['run_record']"
        )
    if not measured["attempt_2_run_record_routes_agree"]:
        problems.append(
            "the Attempt 2 run record found by stage "
            f"({measured['attempt_2_run_record_located_by_stage']}) and the one the config names "
            f"({measured['attempt_2_run_record_declared_in_the_config']}) are not the same record "
            "declaring the same stage"
        )
    if measured["attempt_3_report_artifacts"]:
        problems.append(
            "this attempt's report directory already exists: "
            f"{measured['attempt_3_report_artifacts'][:5]}"
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
            problems.append(f"the k={k} aggregate target gross {gross:.9f} exceeds RA3-1 {ceiling}")

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

    # Three attempts now, so the cumulative figures are a three-term sum in both dimensions. Checking
    # only the variant sum would let a wrong run total through.
    multiplicity = config.get("multiple_comparisons_disclosure", {})
    for cumulative_field, terms in (
        (
            "cumulative_variants_this_hypothesis_family",
            ("variants_this_attempt", "variants_attempt_1", "variants_attempt_2"),
        ),
        (
            "cumulative_runs_this_hypothesis_family",
            ("runs_this_attempt", "runs_attempt_1", "runs_attempt_2"),
        ),
    ):
        parts = [multiplicity.get(term) for term in terms]
        if any(not isinstance(part, int) for part in parts):
            problems.append(f"{cumulative_field}: a term is missing or not an integer: {parts}")
        elif multiplicity.get(cumulative_field) != sum(parts):
            problems.append(
                f"{cumulative_field} is {multiplicity.get(cumulative_field)}, "
                f"recomputed {sum(parts)} from {list(zip(terms, parts))}"
            )

    risk = config.get("risk_architecture", {})
    if risk.get("frozen_before_any_variant_is_run") is not True:
        problems.append("risk_architecture is not marked frozen before any variant is run")
    if risk.get("not_part_of_the_grid") is not True:
        problems.append("risk_architecture is not marked outside the grid")
    components = risk.get("components", {})
    for name in ("RA3-1", "RA3-2", "RA3-3", "RA3-4", "RA3-5"):
        if name not in components:
            problems.append(f"risk_architecture.components is missing {name}")
    bands = components.get("RA3-4", {}).get("bands", [])
    if len(bands) != 3:
        problems.append(f"RA3-4 declares {len(bands)} bands, expected 3")
    else:
        previous = Decimal("0")
        for band in bands:
            if Decimal(band["dd_from"]) != previous:
                problems.append(f"RA3-4 band {band['band']} does not start where the previous ended")
            upper = band.get("dd_to_exclusive")
            previous = Decimal(upper) if upper is not None else previous
        deepest = Decimal(bands[-1]["dd_from"])
        if deepest >= Decimal("0.15"):
            problems.append(
                f"RA3-4's deepest rung at {deepest} is at or beyond the 15% research shutdown"
            )
        # The shallowest band must be full sizing and the descent must be strict. Stated
        # structurally rather than as literals: the thresholds themselves are checked against
        # Generation 1's sealed ladder in check_ladder_provenance, not asserted here.
        scalars = [Decimal(band["scalar"]) for band in bands]
        if scalars[0] != Decimal("1"):
            problems.append(
                f"RA3-4's shallowest band applies scalar {scalars[0]}, not full sizing. The whole "
                "of this attempt's architectural change is that the shallowest band is unthrottled."
            )
        if any(later >= earlier for earlier, later in zip(scalars, scalars[1:])):
            problems.append(f"RA3-4's scalars {scalars} do not strictly decrease with drawdown")
        if bands[-1].get("dd_to_exclusive") is not None:
            problems.append("RA3-4's deepest band is bounded above, so some drawdown has no band")

    if config.get("live_trading_authorized") is not False:
        problems.append("the protocol config does not carry live_trading_authorized false")
    if config.get("declared_before_any_strategy_code") is not True:
        problems.append("the protocol config does not claim declared_before_any_strategy_code")
    if config.get("attempt") != 3:
        problems.append(f"attempt is {config.get('attempt')}, expected 3")

    return problems


def check_criteria_agreement(criteria: dict[str, Any], protocol: dict[str, Any]) -> list[str]:
    """The two verdict tokens must already be sealed, as a pair, and belong to this attempt."""
    problems: list[str] = []
    derivation = criteria.get("verdict_token_derivation", {})
    pass_token = derivation.get("pass_token")
    fail_token = derivation.get("fail_token")
    for label, token in (("pass_token", pass_token), ("fail_token", fail_token)):
        if not isinstance(token, str) or "ATTEMPT_3" not in token:
            problems.append(f"gate criteria {label} is {token!r}, which does not name Attempt 3")
    if pass_token == fail_token:
        problems.append("the gate criteria pass and fail tokens are the same string")

    # The exclusion of the four prior-attempt tokens, checked rather than trusted. A sentence that
    # named no token at all would satisfy a substring test while proving nothing, so the tokens are
    # extracted by pattern first and the extraction is required to be non-empty.
    prose = derivation.get("prior_attempt_tokens_are_not_available_here")
    if not isinstance(prose, str) or not prose:
        problems.append("the gate criteria do not state that the prior attempts' tokens are unusable")
    else:
        excluded = sorted(set(re.findall(r"STAGE_3_G2_[A-Z0-9_]+", prose)))
        if len(excluded) < 4:
            problems.append(
                f"the prior-token exclusion names {len(excluded)} tokens, expected at least four "
                f"(two per closed attempt): {excluded}"
            )
        overlap = sorted({pass_token, fail_token} & set(excluded))
        if overlap:
            problems.append(
                f"this attempt's own verdict token(s) {overlap} appear in the list of tokens the "
                "criteria file declares unavailable"
            )

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
# Agreement: the ladder's stated provenance against the two configs it claims to come from
# --------------------------------------------------------------------------------------------- #

def parse_generation_1_ladder(node: dict[str, Any]) -> list[tuple[Decimal, Decimal | None, Decimal]]:
    """Parse RA1-5's prose rule lines into (lower, upper, absolute f_cap) triples."""
    bands: list[tuple[Decimal, Decimal | None, Decimal]] = []
    for line in node.get("rule", []):
        match = LADDER_RULE.match(str(line).strip())
        if match is None:
            continue
        bound = Decimal(match.group("bound"))
        cap = Decimal(match.group("cap"))
        if match.group("op") == "<":
            lower = Decimal(match.group("lo")) if match.group("lo") else Decimal("0")
            upper: Decimal | None = bound
        else:
            lower = bound
            upper = None
        bands.append((lower, upper, cap))
    return bands


def _band_triples(bands: list[dict[str, Any]]) -> list[tuple[Decimal, Decimal | None, Decimal]]:
    return [
        (
            Decimal(band["dd_from"]),
            None if band.get("dd_to_exclusive") is None else Decimal(band["dd_to_exclusive"]),
            Decimal(band["scalar"]),
        )
        for band in bands
    ]


def check_ladder_provenance(protocol: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    """Recompute the two provenance claims RA3-4 makes, from the files it names.

    Claim one: RA3-4 *is* Generation 1's sealed RA1-5 ladder, expressed as scalars on RA3-1's
    ceiling instead of as absolute caps. Claim two: the single difference from RA2-4 is the deletion
    of one tier, with the band above it extended to fill the gap.

    Neither is taken on trust. Generation 1's ladder is parsed out of its prose rule and
    cross-checked against the three Generation 1 experiments' own ``ladder_rungs``, which is a second
    statement of the same thing in a different shape; RA3's scalars are converted through RA3-1 and
    required to reproduce the absolute caps exactly; and the RA2 to RA3 difference is computed as a
    set difference rather than described.
    """
    problems: list[str] = []
    evidence: dict[str, Any] = {}

    generation_1 = json.loads(GENERATION_1_PROTOCOL.read_text(encoding="utf-8"))
    attempt_2 = json.loads(ATTEMPT_2_PROTOCOL.read_text(encoding="utf-8"))
    evidence["sources"] = {
        GENERATION_1_PROTOCOL.relative_to(PROJECT_ROOT).as_posix(): sha256_file(
            GENERATION_1_PROTOCOL
        ),
        ATTEMPT_2_PROTOCOL.relative_to(PROJECT_ROOT).as_posix(): sha256_file(ATTEMPT_2_PROTOCOL),
    }

    # Generation 1's risk architecture puts its components at the top of ``risk_architecture`` and
    # leaves ``components`` empty; Generation 2's puts them under ``components``. Read the shape that
    # is actually there rather than the one the later generation uses.
    g1_risk = generation_1.get("risk_architecture", {})
    ladder_node = g1_risk.get("RA1-5")
    ceiling_node = g1_risk.get("RA1-1")
    if not isinstance(ladder_node, dict) or not isinstance(ceiling_node, dict):
        problems.append(
            "Generation 1's protocol does not carry risk_architecture.RA1-5 and RA1-1, so the "
            "ladder this attempt claims to restore cannot be read"
        )
        return problems, evidence

    g1_bands = parse_generation_1_ladder(ladder_node)
    evidence["generation_1_ladder"] = [
        [str(lower), None if upper is None else str(upper), str(cap)]
        for lower, upper, cap in g1_bands
    ]
    if len(g1_bands) != 3:
        problems.append(
            f"parsed {len(g1_bands)} bands out of Generation 1's RA1-5 rule, expected 3. The rule "
            "wording changed shape, so nothing below can be trusted."
        )
        return problems, evidence

    # Second, independent statement of the same ladder: every Generation 1 experiment declares the
    # rungs as parameters. All of them must agree with each other and with the prose.
    rungs = {
        experiment.get("experiment_id"): experiment.get("primary_parameters", {}).get(
            "ladder_rungs"
        )
        for experiment in generation_1.get("experiments", [])
    }
    evidence["generation_1_experiment_rungs"] = rungs
    if len(rungs) < 3 or any(not value for value in rungs.values()):
        problems.append(
            f"expected at least three Generation 1 experiments each declaring ladder_rungs, got "
            f"{rungs}"
        )
    else:
        distinct = {json.dumps(value, sort_keys=True) for value in rungs.values()}
        if len(distinct) != 1:
            problems.append(
                f"Generation 1's experiments do not agree on ladder_rungs: {sorted(distinct)}"
            )
        else:
            declared = [[Decimal(str(a)), Decimal(str(b))] for a, b in next(iter(rungs.values()))]
            from_prose = [[lower, cap] for lower, _, cap in g1_bands[1:]]
            if declared != from_prose:
                problems.append(
                    f"Generation 1's ladder_rungs {declared} do not match the rungs its RA1-5 prose "
                    f"states {from_prose}"
                )

    # RA1-1 states f_base as prose. RA3-1 states the same ceiling as a value. If they differ, the
    # scalar-to-absolute conversion below is comparing two different architectures.
    f_base_match = re.search(rf"f_base\s*=\s*({NUMBER})", str(ceiling_node.get("rule", "")))
    ceiling = exposure_ceiling(protocol)
    if f_base_match is None:
        problems.append("Generation 1's RA1-1 rule does not state f_base, so no conversion is safe")
        return problems, evidence
    g1_f_base = Decimal(f_base_match.group(1))
    evidence["generation_1_f_base"] = str(g1_f_base)
    evidence["ra3_exposure_ceiling"] = str(ceiling)
    if g1_f_base != ceiling:
        problems.append(
            f"Generation 1's f_base is {g1_f_base} but RA3-1's ceiling is {ceiling}; RA3-4's "
            "scalars cannot reproduce RA1-5's absolute caps under a different base"
        )

    ra3_bands = protocol["risk_architecture"]["components"]["RA3-4"]["bands"]
    ra3_triples = _band_triples(ra3_bands)
    ra3_absolute = [
        (lower, upper, (ceiling * scalar).quantize(WEIGHT_QUANTUM, rounding=ROUND_DOWN))
        for lower, upper, scalar in ra3_triples
    ]
    evidence["ra3_absolute_ceilings"] = [
        [str(lower), None if upper is None else str(upper), f"{cap:.9f}"]
        for lower, upper, cap in ra3_absolute
    ]
    if len(ra3_absolute) != len(g1_bands):
        problems.append(
            f"RA3-4 has {len(ra3_absolute)} bands against Generation 1's {len(g1_bands)}"
        )
    else:
        for index, (got, want) in enumerate(zip(ra3_absolute, g1_bands)):
            if got[0] != want[0] or got[1] != want[1] or got[2] != want[2]:
                problems.append(
                    f"RA3-4 band {index} is [{got[0]}, {got[1]}) at absolute ceiling {got[2]}, "
                    f"Generation 1's RA1-5 band {index} is [{want[0]}, {want[1]}) at {want[2]}"
                )

    # The RA2 to RA3 difference, computed rather than described.
    ra2_components = attempt_2.get("risk_architecture", {}).get("components", {})
    ra2_ceiling = Decimal(ra2_components.get("RA2-1", {}).get("value", "-1"))
    if ra2_ceiling != ceiling:
        problems.append(
            f"RA2-1's ceiling {ra2_ceiling} differs from RA3-1's {ceiling}, so the two ladders' "
            "scalars are not directly comparable and 'one change' is not a checkable claim"
        )
    ra2_triples = _band_triples(ra2_components.get("RA2-4", {}).get("bands", []))
    evidence["ra2_bands"] = [
        [str(lower), None if upper is None else str(upper), str(scalar)]
        for lower, upper, scalar in ra2_triples
    ]
    removed = [triple for triple in ra2_triples if triple not in ra3_triples]
    added = [triple for triple in ra3_triples if triple not in ra2_triples]
    evidence["bands_removed_from_ra2"] = [
        [str(lower), None if upper is None else str(upper), str(scalar)]
        for lower, upper, scalar in removed
    ]
    evidence["bands_added_by_ra3"] = [
        [str(lower), None if upper is None else str(upper), str(scalar)]
        for lower, upper, scalar in added
    ]
    if len(ra2_triples) != 4:
        problems.append(f"RA2-4 has {len(ra2_triples)} bands, expected 4")
    elif len(removed) != 2 or len(added) != 1:
        problems.append(
            f"the RA2 to RA3 ladder difference is {len(removed)} bands removed and {len(added)} "
            "added, not the declared single deleted tier plus the extension of the band above it"
        )
    else:
        deleted = removed[1]
        widened = added[0]
        expected_widened = (ra2_triples[0][0], deleted[1], ra2_triples[0][2])
        if removed[0] != ra2_triples[0] or deleted != ra2_triples[1]:
            problems.append(
                "the two RA2 bands that RA3 does not carry are not its two shallowest, so the "
                "change is not the deletion of one tier at the shallow end"
            )
        if widened != expected_widened:
            problems.append(
                f"RA3's replacement shallow band {widened} is not RA2's shallowest band extended "
                f"over the deleted tier, which would be {expected_widened}"
            )
        deep_ra2 = [triple for triple in ra2_triples if triple[0] >= deleted[1]]
        deep_ra3 = [triple for triple in ra3_triples if triple[0] >= deleted[1]]
        evidence["bands_at_or_below_the_deleted_tier_unchanged"] = deep_ra2 == deep_ra3
        if not deep_ra2 or deep_ra2 != deep_ra3:
            problems.append(
                f"the bands at or beyond {deleted[1]} differ between RA2 and RA3: {deep_ra2} "
                f"against {deep_ra3}. Only the shallow tier may change."
            )
        evidence["deleted_tier"] = [str(deleted[0]), str(deleted[1]), str(deleted[2])]

    return problems, evidence


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
    row cannot survive -- a variant id is written inside code ticks and the ticks are part of the
    cell. Prose is checked against the stripped form, table rows and backticked identifiers against a
    whitespace-collapsed copy of the raw document. The Markdown is hard-wrapped at 100 columns, so
    neither can be checked against the document line by line.
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
        "attempt 2 document id": ATTEMPT_2_DOCUMENT_ID,
        "generation id": generation_identity()["generation_id"],
        "strategy id": candidate_id(protocol),
        "family": protocol["family"],
        "risk architecture id": protocol["risk_architecture"]["id"],
        "selection rule id": protocol["representative_selection_rule"]["id"],
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
        "attempt 2 verdict": protocol["attempt_2_ref"]["verdict"].replace(" - ", " — "),
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

    # All seventeen immutable prior-attempt modules, named individually, so a sweep of strategies/
    # alone is visibly insufficient. Three of the seventeen live under backtest/.
    immutable = protocol["prior_attempt_modules_immutable"]
    for module in list(immutable["attempt_1_modules"]) + list(immutable["attempt_2_modules"]):
        if f"`{module}`" not in raw:
            problems.append(f"the Markdown does not name the immutable prior-attempt module {module}")

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
        print("REFUSED: this pre-registration is already sealed.")
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
        ATTEMPT_2_SHA,
        GENERATION_1_SHA,
        GENERATION_1_PROTOCOL,
        ATTEMPT_2_PROTOCOL,
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

    # All three closed pre-registrations this attempt reads from, under one exit code. Attempt 2's
    # numbering is kept so a failure here means the same thing it meant in the two prior sessions;
    # which record failed is printed rather than encoded in the code.
    prior_freezes = {
        "generation_1_stage_3_attempt_2": (
            GENERATION_1_SHA,
            verify_sha256_record(GENERATION_1_SHA, root=PROJECT_ROOT),
        ),
        "generation_2_attempt_1": (
            ATTEMPT_1_SHA,
            verify_sha256_record(ATTEMPT_1_SHA, root=PROJECT_ROOT),
        ),
        "generation_2_attempt_2": (
            ATTEMPT_2_SHA,
            verify_sha256_record(ATTEMPT_2_SHA, root=PROJECT_ROOT),
        ),
    }
    failed = {
        label: (path, results)
        for label, (path, results) in prior_freezes.items()
        if not results or any(state != "OK" for state in results.values())
    }
    if failed:
        print("REFUSED: a closed pre-registration this attempt depends on does not verify.")
        for label, (path, results) in sorted(failed.items()):
            print(f"  {label}: {path.relative_to(PROJECT_ROOT).as_posix()}")
            for name, state in sorted(results.items()):
                if state != "OK":
                    print(f"    {name}: {state}")
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

    # Runs before the document check but numbered after it: exit codes 2 through 11 keep the meanings
    # Attempt 2's sealer gave them, and this check is new to Attempt 3.
    problems, ladder_provenance = check_ladder_provenance(protocol)
    if problems:
        print("REFUSED: RA3-4's stated provenance does not survive recomputation.")
        for problem in problems:
            print(f"  - {problem}")
        return 12

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
        "config/generation_2/g2_rotation_ra3_protocol.json": sha256_file(PROTOCOL_CONFIG),
        "config/generation_2/g2_gate_criteria_ra3.json": sha256_file(CRITERIA_CONFIG),
        "config/generation_2/g2_cost_model.json": sha256_file(COST_CONFIG),
        "config/generation_2/g2_rotation_ra1_protocol.json": sha256_file(ATTEMPT_2_PROTOCOL),
        "config/stage3_attempt2_strategy_protocol.json": sha256_file(GENERATION_1_PROTOCOL),
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
            "Generation 2 Stage 3 Attempt 3 cross-sectional rotation pre-registration under risk "
            "architecture RA3 and representative-selection rule SE100-G2-SEL-2"
        ),
        "status": "SEALED",
        "project": "StockEdge100",
        "generation": 2,
        "generation_id": identity["generation_id"],
        "stage": 3,
        "gate_id": 3,
        "attempt": 3,
        "sealed_utc": timestamp,
        "run_id": run_id,
        "charter_ref": f"governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md ({CHARTER_ID})",
        "partition_lock_ref": (
            f"governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md ({PARTITION_LOCK_ID})"
        ),
        "constitution_ref": protocol["constitution_ref"],
        "markdown_counterpart": "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md",
        "source_of_record": "config/generation_2/g2_rotation_ra3_protocol.json",
        "attempt_1_ref": {
            "artifact_id": ATTEMPT_1_DOCUMENT_ID,
            "strategy_id": protocol["attempt_1_ref"]["strategy_id"],
            "verdict": protocol["attempt_1_ref"]["verdict"],
            "disposition": protocol["attempt_1_ref"]["disposition"],
            "record_verified_here": ATTEMPT_1_SHA.relative_to(PROJECT_ROOT).as_posix(),
            "record_verification": prior_freezes["generation_2_attempt_1"][1],
        },
        "attempt_2_ref": {
            "artifact_id": ATTEMPT_2_DOCUMENT_ID,
            "strategy_id": protocol["attempt_2_ref"]["strategy_id"],
            "verdict": protocol["attempt_2_ref"]["verdict"],
            "fail_route": protocol["attempt_2_ref"]["fail_route"],
            "disposition": protocol["attempt_2_ref"]["disposition"],
            "record_verified_here": ATTEMPT_2_SHA.relative_to(PROJECT_ROOT).as_posix(),
            "record_verification": prior_freezes["generation_2_attempt_2"][1],
            "run_record_located_by_stage": contamination[
                "attempt_2_run_record_located_by_stage"
            ],
            "run_record_declared_in_the_config": contamination[
                "attempt_2_run_record_declared_in_the_config"
            ],
            "run_record_routes_agree": contamination["attempt_2_run_record_routes_agree"],
        },
        "generation_1_ref": {
            "protocol": GENERATION_1_PROTOCOL.relative_to(PROJECT_ROOT).as_posix(),
            "record_verified_here": GENERATION_1_SHA.relative_to(PROJECT_ROOT).as_posix(),
            "record_verification": prior_freezes["generation_1_stage_3_attempt_2"][1],
            "read_for": (
                "The RA1-5 de-risk ladder and the RA1-1 exposure ceiling only. Generation 1 is "
                "closed; nothing here reopens, re-runs, or supersedes any part of it."
            ),
        },
        "pinned_artifact_digests_reverified": contamination["prior_attempt_artifact_digests"],
        "sealed_before_any_strategy_code": True,
        "sealed_before_any_variant_is_run": True,
        "sealed_before_any_result_was_seen": False,
        "sealed_before_any_result_was_seen_note": (
            "False, and stated as such. This pre-registration was designed after both Attempt 1's "
            "and Attempt 2's development results were known. It is the third disclosed adaptation "
            "on the same hypothesis family. See adaptation_disclosure."
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
            "derived_from": protocol["risk_architecture"]["derived_from"],
            "single_difference_from_ra2": protocol["risk_architecture"]["single_difference_from_ra2"],
            "components": {
                name: {
                    "name": body.get("name"),
                    "value": body.get("value"),
                    "unit": body.get("unit"),
                }
                for name, body in protocol["risk_architecture"]["components"].items()
            },
            "ladder_bands": protocol["risk_architecture"]["components"]["RA3-4"]["bands"],
            "combined_scalar": protocol["risk_architecture"]["combined_scalar"]["formula"],
            "provenance_recomputed_here": ladder_provenance,
            "recomputed_here": (
                "The per-position weights below are derived from RA3-1's ceiling by this program, "
                "not copied from the config, so a change to the ceiling that was not carried into "
                "the weight table would refuse the seal. The ladder itself is checked against the "
                "two configs it claims to come from rather than described: Generation 1's RA1-5 "
                "prose and experiment parameters, and Attempt 2's RA2-4 band table."
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
            "unchanged_from_attempt_2": True,
            "recomputed_here": (
                "Every field above is recomputed by this program from the declared axes, the "
                "config's own variant id template, and decimal arithmetic, then compared field by "
                "field against the sealed config and row by row against the Markdown."
            ),
        },
        "run_span_measured_from_disk": span,
        "representative_selection_rule": protocol["representative_selection_rule"],
        "gate": {
            "criteria_file": "config/generation_2/g2_gate_criteria_ra3.json",
            "criteria_sha256": sealed_inputs["config/generation_2/g2_gate_criteria_ra3.json"],
            "evaluated_on": protocol["gate_evaluation_scope"]["evaluated_on"],
            "conjunctive_within_candidate": True,
            "thresholds_changed_from_attempt_1": (
                protocol["gate_evaluation_scope"]["thresholds_changed_from_attempt_1"]
            ),
            "thresholds_changed_from_attempt_2": (
                protocol["gate_evaluation_scope"]["thresholds_changed_from_attempt_2"]
            ),
            "pass_token": derivation["pass_token"],
            "fail_token": derivation["fail_token"],
            "tokens_taken_from": "config/generation_2/g2_gate_criteria_ra3.json",
            "prior_attempt_tokens_are_not_available_here": (
                derivation["prior_attempt_tokens_are_not_available_here"]
            ),
            "prior_attempt_tokens_extracted_and_excluded": sorted(
                set(
                    re.findall(
                        r"STAGE_3_G2_[A-Z0-9_]+",
                        derivation["prior_attempt_tokens_are_not_available_here"],
                    )
                )
            ),
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
        "conflicts_declared_in_the_gate_criteria": (
            protocol["conflicts_declared_in_the_gate_criteria"]
        ),
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
            "Stage 3 Attempt 3 reads it."
        ),
        "binding_rules": list(BINDING_RULES),
        "explicit_non_authorizations": protocol["explicit_non_authorizations"],
        "repo_state_id_location": (
            "Deliberately omitted here. governance/generation_2/ is not reached by the "
            "repo_state_id patterns (governance/*.md is single-level), so this file is covered by "
            "STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256 instead. The binding repo_state_id for this "
            f"seal is the repo_state_id field of runs/{run_id}.json. Recorded as G2A3-CONFLICT-30."
        ),
        "stage_3_authorized": True,
        "stage_4_authorized": False,
        "holdout_read_authorized": False,
        "live_trading_authorized": False,
    }

    # The three prior sealed governance JSONs under generation_2/ are CRLF, because write_text
    # translated on Windows. Matching them is a decision here rather than a platform accident: the
    # payload is built explicitly, the invariant is asserted on the bytes *before* anything is
    # written, and the write is byte-exact on any platform.
    body = json.dumps(record, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
    if "\r" in body:
        print("REFUSED: the assembled record contains a carriage return before serialisation.")
        return 13
    payload = body.replace("\n", "\r\n").encode("utf-8")
    lone_feeds = payload.count(b"\n")
    pairs = payload.count(b"\r\n")
    if lone_feeds != pairs or pairs == 0:
        print("REFUSED: the serialised record is not uniformly CRLF; nothing was written.")
        print(f"  LF {lone_feeds}  CRLF {pairs}")
        return 13
    RECORD_JSON.parent.mkdir(parents=True, exist_ok=True)
    RECORD_JSON.write_bytes(payload)

    # Written last so it covers the final bytes of the JSON above. It does not contain its own
    # digest; nothing hashes itself.
    covered = {
        "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md": sha256_file(RECORD_MD),
        "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json": sha256_file(RECORD_JSON),
        "config/generation_2/g2_rotation_ra3_protocol.json": sha256_file(PROTOCOL_CONFIG),
        "config/generation_2/g2_gate_criteria_ra3.json": sha256_file(CRITERIA_CONFIG),
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
        stage="stage_3_generation_2_rotation_attempt_3_preregistration",
        command="python -m stockedge100.reporting.g2_rotation_ra3_preregistration",
        timestamp_utc=timestamp,
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=sealed_inputs["config/generation_2/g2_rotation_ra3_protocol.json"],
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
            "STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256": own_digest,
        },
        notes=[
            "Attempt 3 of Generation 2 Stage 3. Attempt 1 closed FAIL - STAGE_3_G2_NO_CANDIDATE and "
            "Attempt 2 closed FAIL - STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE; both are read-only. This "
            "seal verified both .sha256 records and re-hashed all seventeen prior-attempt modules "
            "and eighteen pinned artifacts against their recorded digests before writing anything. "
            "Nine of the seventeen are named by both development run records and were compared "
            "against each, so a module that changed between the two prior runs would refuse here.",
            "This pre-registration was designed after both Attempt 1's and Attempt 2's development "
            "results were known, and is the third disclosed adaptation on the same hypothesis "
            "family. The development window is not pristine for it. The mandated disclosure is "
            "carried verbatim in the sealed JSON and in the Markdown.",
            f"Eighteen variants declared in full before any is run; "
            f"{record['grid']['total_runs']} runs total across the base and stress cost "
            "assumptions. The grid is the grid both prior attempts used, not widened. Cumulative "
            "across the family: "
            f"{protocol['multiple_comparisons_disclosure']['cumulative_variants_this_hypothesis_family']}"
            " variants and "
            f"{protocol['multiple_comparisons_disclosure']['cumulative_runs_this_hypothesis_family']}"
            " runs, with no multiplicity correction applied.",
            f"Run span {span['run_start']} to {span['run_end']}, {span['run_sessions']} sessions, "
            f"common to all eighteen variants; binding symbol {span['binding_symbol']} with "
            f"inception {span['binding_symbol_inception']}.",
            "Risk architecture RA3: five constants frozen before any variant is run, applied "
            "uniformly to all eighteen, none of them an axis of the grid. Four are RA2's unchanged. "
            "The fifth, the de-risk ladder, is Generation 1's own RA1-5 restored; its provenance "
            "was recomputed here from Generation 1's prose rule, from its three experiments' "
            "declared rungs, and from Attempt 2's band table, and the RA2 to RA3 difference was "
            "computed as a set difference rather than described.",
            "Representative selection is SE100-G2-SEL-2, which replaces Attempt 2's "
            "lowest-turnover rule with a neighbourhood-stability score over non-return "
            "risk-behaviour statistics. It remains return-blind by construction, and the structural "
            "enforcement of that is declared here before the selection module exists.",
            "Contamination measured before writing, content-based: "
            f"{contamination['python_files_scanned']} Python files scanned under src/ and tests/, "
            "zero naming this candidate. This sealer loads the candidate id from the config at run "
            "time so it satisfies its own predicate. Recorded as G2A3-CONFLICT-34.",
            "governance/generation_2/ is outside REPO_STATE_PATTERNS; the .sha256 record and this "
            "run record are what cover those files. config/generation_2/*.json is inside them and "
            "is additionally covered by the .sha256 record. Recorded as G2A3-CONFLICT-30.",
            "Measurement read the session date column and the exchange calendar only. No price, "
            "volume, or dividend field was parsed by this program in any window. No data at or "
            "after the development end date was read, and neither holdout window was opened.",
            "Stage 4 validation is not authorized by this seal.",
        ],
    ).write(RUNS_DIR)

    print("Generation 2 Stage 3 Attempt 3 pre-registration SEALED")
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
    print(f"  risk arch      RA3, ceiling {ceiling}, "
          f"{len(record['risk_architecture']['ladder_bands'])} ladder bands, not gridded")
    print(f"  ladder         Generation 1 RA1-5 restored; deleted RA2 tier "
          f"{ladder_provenance.get('deleted_tier')}; "
          f"absolute ceilings {[row[2] for row in ladder_provenance['ra3_absolute_ceilings']]}")
    print(f"  selection      {protocol['representative_selection_rule']['id']}, return_blind="
          f"{protocol['representative_selection_rule']['return_blind']}")
    print(f"  contamination  {contamination['python_files_scanned']} .py files scanned, "
          f"{contamination['modules_naming_this_candidate_count']} in src/ and "
          f"{contamination['tests_naming_this_candidate_count']} in tests/ name this candidate")
    print(f"  prior attempts {contamination['prior_attempt_module_count']} modules and "
          f"{len(contamination['prior_attempt_artifact_digests'])} artifacts re-hashed, all "
          "unchanged")
    print(f"  tokens         {derivation['pass_token']} / {derivation['fail_token']}")
    print(f"  excluded       {record['gate']['prior_attempt_tokens_extracted_and_excluded']}")
    for name, digest in sorted(covered.items()):
        print(f"  {digest}  {name}")
    print(f"  record digest  {own_digest}")
    return 0


if __name__ == "__main__":
    sys.exit(build())
