"""Stage 4 sealed-validation-execution decision package — a gate 4 determination.

This module records what the single authorized validation-reading session produced. Unlike
:mod:`stockedge100.reporting.stage4_package`, which sealed a *design*, this one carries a real gate
determination reached from a real evidence file. Everything mechanical — timestamp, run id,
``repo_state_id``, manifest, checksum record, run record — comes from
:mod:`stockedge100.reporting.stage_package`.

Four things are worth knowing before reading further.

**The verdict is a FAIL, and a FAIL is a deliverable.** ``stage2_package.py`` refuses to write unless
every condition is met. Copying that guard here would suppress the one artifact the constitution most
wants on disk: a negative result. The guard in :func:`build` is the portable one from
``stage3_package.py`` and ``stage3_attempt2_package.py`` — it asserts that the verdict written into
the package is the verdict the evidence reached, derives both tokens from the sealed
``verdict_token_derivation`` rather than restating them as literals, and refuses the incoherent
combinations enumerated in ``config/stage4_gate_criteria.json`` ``incoherent_combinations_refused``.

**The conditions are re-derived here, not copied.** Every one of the seven is recomputed from the raw
measurements in ``reports/stage4/STAGE_4_VALIDATION_EVIDENCE.json`` using thresholds parsed out of the
sealed predicate strings, and the result is required to agree with the verdict the evaluator recorded.
Two independent implementations reaching the same seven verdicts is the check; a single implementation
agreeing with itself is not.

**There is no ``admissible_candidate_exists`` row and there must not be one.** Constitution section 9
makes gates conjunctive within a candidate and disjunctive across candidates, but Gate 4 evaluates
exactly one sealed representative, so the across-candidate disjunction is degenerate. The decisive row
is ``gate_4_representative_admitted_in_validation``, which carries the conjunction itself so that the
seven-row table cannot be read as though some rollup were still outstanding.

**Nothing is predicted.** Contamination predicates, checksum records, the sealed thirteen-artifact
recheck and the repository-state delta are all measured here, at build time, before
``build_stage_package`` writes anything. Where this package's own writes will move a count, the
package records the *mechanism* — which files, and whether the directory is overwritten or appended —
and never a number nobody has computed yet.

``gate_passed`` is ``False``, so the shared builder derives ``exit_status`` ``GATE_NOT_PASSED`` for the
``runs/`` record. That is correct and is recorded in the run notes.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage4_evaluation_package
"""

from __future__ import annotations

import ast
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_file, sha256_text_canonical_json
from stockedge100.reporting import stage4_preregistration
from stockedge100.reporting.stage_package import (
    GOVERNANCE,
    PROJECT_ROOT,
    RUNS_DIR,
    STAGE_0_FROZEN_INPUTS,
    StageDecision,
    build_stage_package,
    repo_state,
    verify_sha256_record,
    verify_stage0_freeze,
)

COMMAND = (
    "cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage4_evaluation_package"
)

REPRESENTATIVE = "SE100-S3A2-C2-MEANREV-RA1"

EVIDENCE_REL = "reports/stage4/STAGE_4_VALIDATION_EVIDENCE.json"
SEAL = "governance/STAGE_4_PREREGISTRATION.json"
PREREG_MD = "governance/STAGE_4_PREREGISTRATION.md"
PREREG_RECORD = "governance/STAGE_4_PREREGISTRATION.sha256"
PROTOCOL = "config/stage4_validation_protocol.json"
CRITERIA = "config/stage4_gate_criteria.json"
SELECTION = "config/stage4_representative_selection.json"
PREREG_REPORT = "governance/STAGE_4_VALIDATION_PREREGISTRATION_REPORT.md"
VALIDATION_REPORT = "governance/STAGE_4_VALIDATION_REPORT.md"
HOLDOUT_LOCK = "governance/STAGE_1_HOLDOUT_LOCK.json"
UNIVERSE = "governance/STAGE_1_UNIVERSE.json"

SEALING_RUN = "runs/SE100-R-20260813T140121Z.json"
PREREG_PACKAGE_RUN = "runs/SE100-R-20260814T111459Z.json"

# (record, working directory the record's paths are relative to, entry count expected). Recording
# expected against actual makes a drift in either the record or this module visible, instead of
# silently agreeing with whichever was written last. The two Stage 0/1 freeze records carry bare
# filenames and verify from governance/; every other record carries project-root-relative paths.
CHECKSUM_RECORDS = (
    ("governance/STAGE_0_FREEZE.sha256", "governance", 2),
    ("governance/STAGE_1_FREEZE.sha256", "governance", 2),
    ("governance/STAGE_1_PREREGISTRATION.sha256", "root", 4),
    ("governance/STAGE_2_PREREGISTRATION.sha256", "root", 4),
    ("governance/STAGE_3_PREREGISTRATION.sha256", "root", 4),
    ("governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256", "root", 4),
    (PREREG_RECORD, "root", 5),
    ("reports/stage0/STAGE_0_VERIFICATION.sha256", "root", 8),
    ("reports/stage1/STAGE_1_DATA_READINESS.sha256", "root", 19),
    ("reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256", "root", 20),
    ("reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256", "root", 26),
    ("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256", "root", 31),
    ("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256", "root", 37),
    ("reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.sha256", "root", 26),
)

STAGE_1_FROZEN_INPUTS = (
    "governance/STAGE_1_DATA_FOUNDATION_REPORT.md",
    UNIVERSE,
    HOLDOUT_LOCK,
    "governance/STAGE_1_FREEZE.sha256",
    "governance/STAGE_1_PREREGISTRATION.json",
    "governance/STAGE_1_PREREGISTRATION.sha256",
)

STAGE_2_FROZEN_INPUTS = (
    "governance/STAGE_2_BACKTEST_ENGINE_REPORT.md",
    "governance/STAGE_2_PREREGISTRATION.json",
    "governance/STAGE_2_PREREGISTRATION.sha256",
    "config/stage2_cost_model.json",
    "config/stage2_engine_spec.json",
)

STAGE_3_FROZEN_INPUTS = (
    "governance/STAGE_3_PREREGISTRATION.json",
    "governance/STAGE_3_PREREGISTRATION.sha256",
    "governance/STAGE_3_STRATEGY_RESEARCH_REPORT.md",
    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json",
    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256",
    "governance/STAGE_3_ATTEMPT_2_DESIGN_REPORT.md",
    "governance/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH_REPORT.md",
    "config/stage3_gate_criteria.json",
    "config/stage3_attempt2_strategy_protocol.json",
    "config/stage3_attempt2_gate_criteria_binding.json",
    "src/stockedge100/strategies/attempt2_candidates.py",
)

STAGE_4_SEALED_INPUTS = (
    PREREG_MD,
    SEAL,
    PREREG_RECORD,
    PREREG_REPORT,
    PROTOCOL,
    CRITERIA,
    SELECTION,
)

PRODUCED = (
    VALIDATION_REPORT,
    EVIDENCE_REL,
    "reports/stage4/STAGE_4_VALIDATION.json",
    "reports/stage4/STAGE_4_VALIDATION_ARTIFACT_MANIFEST.json",
    "reports/stage4/STAGE_4_VALIDATION_TEST_SUMMARY.md",
    "reports/stage4/pytest_stage4_evaluation_output.txt",
    "src/stockedge100/strategies/stage4_evaluation.py",
    "src/stockedge100/strategies/stage4_gate.py",
    "src/stockedge100/reporting/stage4_evidence.py",
    "src/stockedge100/reporting/stage4_evaluation_package.py",
    "tests/unit/test_stage4_evaluation.py",
    "tests/unit/test_stage4_evidence.py",
)

VERDICT_SEMANTICS = (
    "MET means the sealed predicate evaluated true on the measured value. NOT_MET means it evaluated "
    "false. NOT_EVALUABLE, NOT_RUN, UNKNOWN and missing evidence are never a pass. "
    "NOT_APPLICABLE_BY_CONDITION_TEXT would be satisfied without being met; no condition reached it."
)

HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
DECIMAL_LITERAL = re.compile(r"Decimal\('([^']+)'\)")

# The AST markers of the sealed P5 predicate: an import of the data-access layer, a call to a dataset
# loader, an import of a network or broker package, an attribute access used to read an environment
# variable or open a connection, or a string constant containing a URL scheme.
DATA_MODULES = ("stockedge100.backtest.dataset", "stockedge100.data")
LOADER_CALLS = ("load_dataset", "load_series", "read_csv", "series_from_rows", "load_validation_series")
NETWORK_MODULES = ("requests", "urllib", "http", "socket", "alpaca", "alpaca_trade_api", "yfinance")
ENV_ATTRS = ("environ", "getenv", "urlopen", "connect", "Session", "Client")
# Composed, not written out, and composed the same way the sealer composes URL_MARKERS. This module is
# itself a stage4-named module under src/, so the sealed P5 predicate walks it; a literal "http" +
# "://" here would be a string constant containing a URL scheme inside a file the predicate scans. The
# pre-registration session hit exactly this on its first dry-run and settled it with the composed form
# plus test_the_url_marker_table_is_composed_so_the_predicate_does_not_flag_itself, which asserts no
# string constant in the scanning module contains a marker. Following that precedent rather than
# inventing a second convention for the same problem one stage later.
URL_SCHEMES = tuple(scheme + "://" for scheme in ("http", "https", "ftp", "ws", "wss"))


def load(rel: str) -> Any:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def read_text(rel: str) -> str:
    return (PROJECT_ROOT / rel).read_text(encoding="utf-8")


def _condition(condition_id: str, verdict: str, required: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "required": required,
        "verdict": verdict,
        "satisfied": verdict in ("MET", "NOT_APPLICABLE_BY_CONDITION_TEXT"),
        "verdict_semantics": VERDICT_SEMANTICS,
        "evidence": evidence,
    }


def _threshold_of(predicate: str) -> str | None:
    """The Decimal literal inside a sealed predicate string, or None if it carries no number."""
    found = DECIMAL_LITERAL.search(predicate)
    return found.group(1) if found else None


# -- independent re-derivation of the seven conditions ---------------------------------------------


def _rederive(evidence: dict[str, Any], criteria: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Recompute each sealed predicate from the raw measurements, in a second implementation.

    The evaluator that produced the evidence already recorded a verdict per condition. Trusting it
    here would make this package a copy rather than a check, so every comparison is redone from the
    numbers in ``gate_evidence`` and ``folds`` against thresholds parsed out of the sealed predicate
    strings. Decimal throughout, and no rounding before comparison: the sealed criteria require the
    comparison to be exact and one fold return differs from zero in its fifth significant figure.
    """
    base = evidence["gate_evidence"]["base"]
    stress = evidence["gate_evidence"]["stress"]
    folds = evidence["folds"]
    invariance = evidence["gate_evidence"]["invariance"]
    by_id = {c["id"]: c for c in criteria["conditions"]}

    def threshold(condition_id: str) -> Decimal:
        literal = _threshold_of(by_id[condition_id]["predicate"])
        if literal is None:
            raise ValueError(f"{condition_id} carries no Decimal literal in its sealed predicate")
        return Decimal(literal)

    out: dict[str, dict[str, Any]] = {}

    total_return = Decimal(base["total_return"])
    out["S4-C1"] = {
        "measured": str(total_return),
        "threshold": str(threshold("S4-C1")),
        "comparison": "total_return > threshold",
        "met": total_return > threshold("S4-C1"),
    }

    sharpe = Decimal(base["sharpe"])
    out["S4-C2"] = {
        "measured": str(sharpe),
        "threshold": str(threshold("S4-C2")),
        "comparison": "sharpe >= threshold",
        "met": sharpe >= threshold("S4-C2"),
    }

    drawdown = Decimal(base["max_drawdown"])
    out["S4-C3"] = {
        "measured": str(drawdown),
        "threshold": str(threshold("S4-C3")),
        "comparison": "max_drawdown <= threshold",
        "met": drawdown <= threshold("S4-C3"),
    }

    profit_factor = Decimal(base["profit_factor"])
    out["S4-C4"] = {
        "measured": str(profit_factor),
        "threshold": str(threshold("S4-C4")),
        "comparison": "profit_factor >= threshold",
        "met": profit_factor >= threshold("S4-C4"),
    }

    stressed = Decimal(stress["total_return"])
    out["S4-C5"] = {
        "measured": str(stressed),
        "threshold": str(threshold("S4-C5")),
        "comparison": "stressed_total_return > threshold",
        "met": stressed > threshold("S4-C5"),
    }

    completed = int(folds["completed"])
    positive = int(folds["positive"])
    ratio = Decimal(positive) / Decimal(completed) if completed else None
    out["S4-C6"] = {
        "measured": str(ratio) if ratio is not None else None,
        "threshold": str(threshold("S4-C6")),
        "comparison": "positive_fold_count / completed_fold_count >= threshold",
        "positive_fold_count": positive,
        "completed_fold_count": completed,
        "met": bool(ratio is not None and ratio >= threshold("S4-C6")),
    }

    # S4-C7 carries no Decimal literal: it is the conjunction of three mechanical clauses.
    out["S4-C7"] = {
        "measured": None,
        "threshold": "exact equality of every sealed digest; no tolerance",
        "comparison": (
            "all sealed digests equal AND exactly one validation evaluation run record AND "
            "engine runs == declared runs"
        ),
        "all_digests_equal": bool(invariance["all_digests_equal"]),
        "digests_equal": invariance["digests_equal"],
        "digests_total": invariance["digests_total"],
        "validation_evaluation_run_records": invariance["validation_evaluation_run_records"],
        "validation_window_engine_runs": invariance["validation_window_engine_runs"],
        "declared_run_count": invariance["declared_run_count"],
        "met": bool(
            invariance["all_digests_equal"]
            and invariance["digests_equal"] == invariance["digests_total"]
            and invariance["validation_evaluation_run_records"] == 1
            and invariance["validation_window_engine_runs"] == invariance["declared_run_count"]
        ),
    }
    return out


# -- build-time integrity measurements --------------------------------------------------------------


def _verify_records() -> tuple[bool, dict[str, Any]]:
    freeze_ok, freeze_detail = verify_stage0_freeze()
    records: dict[str, Any] = {}
    all_ok = freeze_ok
    for rel, where, expected_entries in CHECKSUM_RECORDS:
        root = GOVERNANCE if where == "governance" else PROJECT_ROOT
        results = verify_sha256_record(PROJECT_ROOT / rel, root)
        statuses = sorted(set(results.values()))
        ok = statuses == ["OK"] and len(results) == expected_entries
        all_ok = all_ok and ok
        records[rel] = {
            "verify_from": "stockedge100/governance" if where == "governance" else "stockedge100",
            "entries": len(results),
            "entries_expected": expected_entries,
            "statuses": statuses,
            "all_ok": ok,
        }
    return all_ok, {
        "stage_0_freeze_verified": bool(freeze_ok),
        "stage_0_freeze_detail": freeze_detail,
        "records": records,
        "records_verified": len(records),
        "all_ok": bool(all_ok),
        "working_directory_note": (
            "Two conventions are in use. STAGE_0_FREEZE.sha256 and STAGE_1_FREEZE.sha256 carry bare "
            "filenames and verify from stockedge100/governance; every other record carries "
            "project-root-relative paths and verifies from stockedge100. A failure from the wrong "
            "working directory would be an operator error, not an integrity failure."
        ),
    }


def _recheck_sealed_digests() -> tuple[bool, dict[str, Any]]:
    """The thirteen-artifact S4-C7 recheck set, recomputed here from disk a second time."""
    seal = load(SEAL)
    sealed = dict(seal["sealed_digests_for_s4_c7"]["entries"])
    entries: dict[str, Any] = {}
    all_equal = True
    for rel, expected in sorted(sealed.items()):
        computed = sha256_file(PROJECT_ROOT / rel)
        equal = computed == expected
        all_equal = all_equal and equal
        entries[rel] = {"sealed": expected, "recomputed": computed, "equal": equal}

    # The thirteenth entry is the seal record itself, which cannot carry its own digest. Its value
    # lives in governance/STAGE_4_PREREGISTRATION.sha256 instead.
    own = seal["sealed_digests_for_s4_c7"]["own_digest_excluded"]
    record_entries = verify_sha256_record(PROJECT_ROOT / PREREG_RECORD, PROJECT_ROOT)
    own_ok = record_entries.get(own) == "OK"
    all_equal = all_equal and own_ok
    entries[own] = {
        "sealed": "carried by " + PREREG_RECORD,
        "recomputed": "verified via the checksum record",
        "equal": own_ok,
        "note": seal["sealed_digests_for_s4_c7"]["own_digest_location"],
    }
    return all_equal, {
        "declared_set_size": seal["sealed_digests_for_s4_c7"]["declared_set_size"],
        "rechecked": len(entries),
        "all_equal": bool(all_equal),
        "entries": entries,
        "recheck_rule": seal["sealed_digests_for_s4_c7"]["recheck_rule"],
    }


def _repo_state_delta(code_hashes: dict[str, str]) -> dict[str, Any]:
    """Diff the tree against the seal and against the evaluation, computed rather than asserted.

    Four states matter and they are all different on purpose. The seal fixes the tree at the moment
    the protocol was sealed; the pre-registration package fixes it three artifacts later, and *that*
    is the "sealed ending repo_state_id" the operating prompt names, so it is the baseline the Stage 4
    report reconciles against; the evaluation fixes it after the evaluator was written but before this
    report and this builder were; now is now. What must hold across all four is that nothing under
    ``governance/`` or ``config/`` changed and nothing was removed.

    Both the sealing run and the pre-registration package run are carried because quoting only one
    invites the reader to mistake it for the other -- they differ by three entries and by a digest.
    """
    sealed_map = load(SEALING_RUN)["code_hashes"]
    prereg_map = load(PREREG_PACKAGE_RUN)["code_hashes"]
    evaluated_map = load("runs/" + _evaluation_run_id() + ".json")["code_hashes"]

    def diff(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
        protected = sorted(
            k for k in changed + removed
            if k.startswith("governance/") or k.startswith("config/")
        )
        return {
            "entries_before": len(before),
            "entries_after": len(after),
            "added": added,
            "changed": changed,
            "removed": removed,
            "added_count": len(added),
            "changed_count": len(changed),
            "removed_count": len(removed),
            "protected_paths_changed_or_removed": protected,
            "no_frozen_or_sealed_path_moved": not protected,
        }

    return {
        "baselines": {
            "sealing_run": SEALING_RUN,
            "preregistration_package_run": PREREG_PACKAGE_RUN,
            "validation_evaluation_run": "runs/" + _evaluation_run_id() + ".json",
            "which_one_the_report_reconciles": PREREG_PACKAGE_RUN,
        },
        "seal_to_preregistration_package": diff(sealed_map, prereg_map),
        "preregistration_package_to_evaluation": diff(prereg_map, evaluated_map),
        "evaluation_to_package_build": diff(evaluated_map, code_hashes),
        "seal_to_package_build": diff(sealed_map, code_hashes),
        "why_they_differ": (
            "The seal predates the pre-registration package that closed Stage 4's design session; "
            "both predate the evaluator they authorized; the evaluation predates this report and this "
            "builder. Equality across the four is neither expected nor required. What is required is "
            "that nothing under governance/ or config/ changed and nothing was removed, which is "
            "measured above rather than asserted."
        ),
        "identifiers_recorded_where": (
            "The three repo_state_id values live in runs/ and in this decision record. None is "
            "written into a governance Markdown file, because repo_state_id covers governance/*.md "
            "and a tree digest recorded inside its own tree invalidates itself on write."
        ),
    }


def _evaluation_run_id() -> str:
    """The run id of the one validation evaluation, found by strategy_id rather than by name."""
    matches = sorted(
        path.stem for path in RUNS_DIR.glob("*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("strategy_id") == REPRESENTATIVE
    )
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one validation evaluation run record for {REPRESENTATIVE}, "
            f"found {len(matches)}: {matches}"
        )
    return matches[0]


def _ast_markers(path: Path) -> list[str]:
    """The sealed P5 markers present in one module's parsed syntax tree.

    An AST question, not a text search: the sealed definition says so explicitly, because a text
    search would match the words of the definition itself.
    """
    found: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if any(node.module.startswith(m) for m in DATA_MODULES):
                found.append(f"from {node.module}")
            if any(node.module.split(".")[0] == m for m in NETWORK_MODULES):
                found.append(f"network import {node.module}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if any(alias.name.startswith(m) for m in DATA_MODULES):
                    found.append(f"import {alias.name}")
                if alias.name.split(".")[0] in NETWORK_MODULES:
                    found.append(f"network import {alias.name}")
        elif isinstance(node, ast.Call):
            target = node.func
            name = target.id if isinstance(target, ast.Name) else (
                target.attr if isinstance(target, ast.Attribute) else None
            )
            if name in LOADER_CALLS:
                found.append(f"call {name}")
        elif isinstance(node, ast.Attribute):
            if node.attr in ENV_ATTRS:
                found.append(f"attribute {node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if any(scheme in node.value for scheme in URL_SCHEMES):
                found.append("url scheme constant")
    return sorted(set(found))


def _contamination() -> dict[str, Any]:
    """The six sealed predicates, measured now, before this package writes anything."""
    seal = load(SEAL)
    protocol = load(PROTOCOL)
    declared = seal["contamination_predicates"]
    labels = [run["run_label"] for run in protocol["runs_declared"]["runs"]]

    src = PROJECT_ROOT / "src" / "stockedge100"
    excluded = "src/stockedge100/reporting/stage4_preregistration.py"
    stage4_modules = sorted(
        path for path in src.rglob("*.py")
        if "stage4" in path.relative_to(PROJECT_ROOT).as_posix().lower()
    )

    p1 = [
        path.relative_to(PROJECT_ROOT).as_posix() for path in stage4_modules
        if path.relative_to(PROJECT_ROOT).as_posix() != excluded
    ]
    p2 = [
        path.relative_to(PROJECT_ROOT).as_posix() for path in src.rglob("*.py")
        if any(label in path.read_text(encoding="utf-8") for label in labels)
    ]
    p3 = sorted(
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "reports").rglob("*")
        if path.is_file() and "stage4" in path.relative_to(PROJECT_ROOT).as_posix().lower()
    )
    p4 = sorted(
        path.name for path in RUNS_DIR.glob("*.json")
        if "STAGE_4" in path.read_text(encoding="utf-8")
        or any(label in path.read_text(encoding="utf-8") for label in labels)
    )

    # The sealer's own predicate is the reference implementation of P5: it is the code the seal was
    # written against and the code the marker test asserts on. It is called here rather than
    # restated, so this package and that failing test cannot report different numbers for the same
    # predicate. The sweep below is a second, wider reading of the same sealed prose and is reported
    # alongside it, never in place of it -- see p5["two_implementations_disagree"].
    reference_hits = stage4_preregistration._stage_4_modules_touching_restricted_data()
    reference_files = sorted(hit.split(":", 1)[0] for hit in reference_hits)

    p5_data: dict[str, list[str]] = {}
    p5_broker: dict[str, list[str]] = {}
    for path in stage4_modules:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        markers = _ast_markers(path)
        data_half = [m for m in markers if m.startswith(("from ", "import ", "call "))]
        broker_half = [m for m in markers if not m.startswith(("from ", "import ", "call "))
                       or m.startswith("network import")]
        if data_half:
            p5_data[rel] = data_half
        if broker_half:
            p5_broker[rel] = broker_half

    # Every hit is resolved back to a named cause. The frozen-artifact rules require exactly this of
    # any broad sweep -- "resolve every hit back to a file on disk ... a bare count proves nothing" --
    # and it is the only way a nonzero P5 can be read as anything other than a breach. A hit that no
    # rule below explains stays UNRESOLVED and the guard refuses the package.
    p5_resolution: dict[str, str] = {}
    unresolved: list[str] = []
    for rel, markers in sorted({**p5_data, **p5_broker}.items()):
        if all(
            m.startswith("call ") or m.startswith("from ") or m.startswith("import ")
            for m in markers
        ) and not any(m.startswith("network import") for m in markers):
            p5_resolution[rel] = (
                "AUTHORIZED_EVALUATION_PATH: dataset-loader and data-layer markers only "
                "(" + ", ".join(markers) + "). These are the reads the seal authorized this session "
                "to perform. No network, broker, environment-variable or URL marker is present."
            )
        else:
            p5_resolution[rel] = "UNRESOLVED"
            unresolved.append(rel)

    gate3_records = {
        rel: sorted(set(verify_sha256_record(PROJECT_ROOT / rel, PROJECT_ROOT).values()))
        for rel in (
            "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256",
            "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256",
        )
    }
    p6 = all(statuses == ["OK"] for statuses in gate3_records.values())

    return {
        "measured_before_this_package_wrote_anything": True,
        "sealed_values_at_sealing": {
            key: declared[key] for key in (
                "stage_4_evaluator_or_result_modules",
                "modules_naming_a_stage_4_run_label",
                "stage_4_report_artifacts",
                "stage_4_run_records",
                "stage_4_modules_touching_restricted_data_or_a_broker",
                "gate_3_attempt_2_records_verify",
            )
        },
        "stage_4_evaluator_or_result_modules": {
            "count": len(p1), "files": p1, "sealed_value": 0,
            "expected_to_move": True,
            "why": (
                "The seal recorded 0 because no Stage 4 module existed. This session wrote the "
                "evaluator the seal authorized, and the pre-registration session wrote its own "
                "decision-package builder after the seal. Both legitimately count. The one file the "
                "predicate excludes by name, " + excluded + ", is the sealing program itself."
            ),
        },
        "modules_naming_a_stage_4_run_label": {
            "count": len(p2), "files": p2, "sealed_value": 0,
            "labels_searched": labels,
            "note": (
                "Still 0. The run labels are read from the sealed protocol at run time and are not "
                "restated as literals anywhere in src/."
            ),
        },
        "stage_4_report_artifacts": {
            "count": len(p3), "files": p3, "sealed_value": 0,
            "expected_to_move": True,
            "mechanism": (
                "reports/stage4/ gains this package's decision record, artifact manifest and "
                "checksum record, which are written after this measurement is taken. reports/ is "
                "overwritten in place per basename, not appended, so a re-measurement counts files "
                "present rather than writes performed."
            ),
        },
        "stage_4_run_records": {
            "count": len(p4), "files": p4, "sealed_value": 0,
            "expected_to_move": True,
            "mechanism": (
                "runs/ is append-only and gains exactly one record per session that writes one: the "
                "seal's, the pre-registration package's, the validation evaluation's, and this "
                "package's, the last of which is written after this measurement is taken."
            ),
        },
        "stage_4_modules_touching_restricted_data_or_a_broker": {
            "reference_implementation": {
                "source": "src/stockedge100/reporting/stage4_preregistration.py"
                          "::_stage_4_modules_touching_restricted_data",
                "count": len(reference_hits),
                "files": reference_files,
                "hits": sorted(reference_hits),
                "status": (
                    "FROZEN. This is the function the seal was written against and the function "
                    "tests/unit/test_stage4_preregistration.py::"
                    "test_no_stage_4_module_can_reach_restricted_data_or_a_broker asserts on, so its "
                    "count is the one that appears in the failing-test line of the test summary."
                ),
            },
            "data_access_half": {"count": len(p5_data), "files": p5_data},
            "broker_network_env_url_half": {"count": len(p5_broker), "files": p5_broker},
            "modules_matching_either_half": len({**p5_data, **p5_broker}),
            "resolution": p5_resolution,
            "unresolved": unresolved,
            "sealed_value": 0,
            "conflict": "S4-CONFLICT-7",
            "two_implementations_disagree": {
                "reference_count": len(reference_hits),
                "this_package_count": len({**p5_data, **p5_broker}),
                "seen_only_by_this_package": sorted(
                    set({**p5_data, **p5_broker}) - set(reference_files)
                ),
                "seen_only_by_the_reference": sorted(
                    set(reference_files) - set({**p5_data, **p5_broker})
                ),
                "cause": (
                    "The sealed prose says 'a call to a dataset loader'; it does not enumerate the "
                    "loaders. The frozen implementation enumerates them in a literal frozenset, "
                    "LOADER_CALLS = " + ", ".join(sorted(stage4_preregistration.LOADER_CALLS))
                    + ", which was written before the evaluator existed and therefore cannot name "
                    "load_validation_series. Its data-layer tuple, DATA_LAYER_MODULES = "
                    + ", ".join(stage4_preregistration.DATA_LAYER_MODULES) + ", is narrower than "
                    "this module's for the same reason. Both counts are correct for what they "
                    "measure: the reference measures the seal's frozen implementation, this package "
                    "measures the seal's prose."
                ),
                "resolution_rule": (
                    "Neither is edited to agree with the other. The frozen implementation may not be "
                    "changed, and widening it after a validation read would be exactly the "
                    "post-seal edit post_seal_defect_rule forbids; narrowing this package's sweep to "
                    "match would suppress a real loader call the sealed prose covers. The wider "
                    "count is reported as the measurement and the frozen count as the reference, "
                    "and the divergence is disclosed here and as part of S4-CONFLICT-7. Neither "
                    "reading is zero, so the conflict's substance -- that the predicate cannot "
                    "survive authorizing the work it gates -- is unaffected by which is used."
                ),
            },
            "why_the_data_half_cannot_be_zero": (
                "The sealed predicate's stated purpose is the fail-closed proof that the "
                "PRE-REGISTRATION path cannot read a restricted observation or reach a broker. Its "
                "mechanical scope is every stage4-named module under src/. Once the evaluation the "
                "pre-registration authorized exists, the evaluator must call a dataset loader, so "
                "the predicate necessarily reads at least 1 and can never read 0 again. Reported, "
                "not repaired: renaming the evaluator out of the stage4 path would hide a real load "
                "from a predicate written to find it and would corrupt the first predicate too, "
                "weakening or deleting the marker test is forbidden, and editing the seal after a "
                "validation read is forbidden by post_seal_defect_rule regardless of intent."
            ),
            "why_the_broker_half_is_still_zero": (
                "It reads " + str(len(p5_broker)) + ". No stage4 module imports a network or broker "
                "package, reads an environment variable, opens a connection, or carries a URL scheme "
                "constant, so this half of the predicate survives the authorization intact and "
                "remains the fail-closed proof it was written to be. This module's own URL_SCHEMES "
                "marker table is composed at import time rather than written out, following the "
                "convention the sealer established for the same problem and the test that pins it: a "
                "scanning module must not trip its own scan. Every hit on either half is resolved by "
                "name above, and the guard refuses this package if any hit is UNRESOLVED."
            ),
            "no_network_or_broker_import_anywhere": not any(
                m.startswith("network import") or m.startswith("attribute ")
                for markers in p5_broker.values() for m in markers
            ),
        },
        "gate_3_attempt_2_records_verify": {
            "value": bool(p6), "sealed_value": True, "records": gate3_records,
            "why_it_matters": declared["definitions"]["gate_3_attempt_2_records_verify"],
        },
    }


# -- the package ------------------------------------------------------------------------------------


def build() -> int:
    evidence = load(EVIDENCE_REL)
    criteria = load(CRITERIA)
    protocol = load(PROTOCOL)
    seal = load(SEAL)
    selection = load(SELECTION)
    lock = load(HOLDOUT_LOCK)
    universe = load(UNIVERSE)

    derivation = criteria["verdict_token_derivation"]
    pass_token = derivation["pass_token"]
    fail_token = derivation["fail_token"]

    records_ok, records_detail = _verify_records()
    digests_ok, digests_detail = _recheck_sealed_digests()
    code_hashes, repo_state_id = repo_state()
    delta = _repo_state_delta(code_hashes)
    contamination = _contamination()

    evaluation_run_id = _evaluation_run_id()
    evaluation_run = load("runs/" + evaluation_run_id + ".json")

    # The evidence file is this package's input, so its self-digest is re-verified rather than
    # trusted, following the file's own coverage description literally: every field except
    # generated_utc and evidence_digest, in the project's canonical JSON form. Recomputing it with a
    # hand-rolled serialisation instead of the shared one is how a false mismatch gets reported, so
    # the shared function is used here and the excluded keys come from the file's own description.
    excluded = ("generated_utc", "evidence_digest")
    for key in excluded:
        if key not in evidence["evidence_digest_covers"]:
            raise ValueError(
                f"the evidence file's coverage description does not name {key!r}; the exclusion set "
                "must follow the description on disk, not this module's assumption"
            )
    evidence_digest = sha256_text_canonical_json(
        {k: v for k, v in evidence.items() if k not in excluded}
    )
    evidence_digest_ok = evidence_digest == evidence["evidence_digest"]

    rederived = _rederive(evidence, criteria)
    recorded = {c["id"]: c for c in evidence["gate"]["conditions"]}
    agreement = {
        cid: {
            "recorded_verdict": recorded[cid]["verdict"],
            "rederived_met": rederived[cid]["met"],
            "agrees": (recorded[cid]["verdict"] == "MET") == rederived[cid]["met"],
        }
        for cid in sorted(recorded)
    }
    all_agree = all(entry["agrees"] for entry in agreement.values())

    conditions: dict[str, Any] = {}
    for cid in sorted(recorded):
        sealed = next(c for c in criteria["conditions"] if c["id"] == cid)
        conditions[cid] = _condition(
            cid,
            recorded[cid]["verdict"],
            sealed["required_verbatim"],
            {
                "sealed_predicate": sealed["predicate"],
                "sealed_boundary": sealed["boundary"],
                "sealed_measurement": sealed["measurement"],
                "measured": recorded[cid]["measured"],
                "independent_rederivation": rederived[cid],
                "agrees_with_the_evaluator": agreement[cid]["agrees"],
                "condition_evidence": recorded[cid]["evidence"],
                "source": EVIDENCE_REL + " gate.conditions",
            },
        )

    met = sorted(cid for cid, c in conditions.items() if c["verdict"] == "MET")
    not_met = sorted(cid for cid, c in conditions.items() if c["verdict"] == "NOT_MET")
    not_evaluable = sorted(cid for cid, c in conditions.items() if c["verdict"] == "NOT_EVALUABLE")
    not_applicable = sorted(
        cid for cid, c in conditions.items() if c["verdict"] == "NOT_APPLICABLE_BY_CONDITION_TEXT"
    )
    conjunction = bool(conditions) and all(c["satisfied"] for c in conditions.values())

    # The decisive row. Gate 4 evaluates one sealed representative, so the across-candidate
    # disjunction of constitution section 9 is degenerate and there is no admissible_candidate_exists
    # to compute. Carrying the conjunction as its own row stops the seven-row table being read as
    # though a rollup were still outstanding.
    conditions["gate_4_representative_admitted_in_validation"] = _condition(
        "gate_4_representative_admitted_in_validation",
        "MET" if conjunction else "NOT_MET",
        (
            "The single sealed representative satisfies every hard condition of gate 4. Conjunctive "
            "within the candidate; the across-candidate disjunction of constitution section 9 is "
            "degenerate because exactly one representative was sealed."
        ),
        {
            "representative": REPRESENTATIVE,
            "condition_count": len(met) + len(not_met) + len(not_evaluable) + len(not_applicable),
            "met": met,
            "not_met": not_met,
            "not_evaluable": not_evaluable,
            "not_applicable_by_condition_text": not_applicable,
            "within_candidate": "CONJUNCTIVE",
            "across_candidates": "NOT_APPLICABLE_EXACTLY_ONE_REPRESENTATIVE",
            "conjunction": conjunction,
            "no_admissible_candidate_exists_row": (
                "Deliberate. That row belongs to a stage that ranks candidates across a disjunction. "
                "Gate 4 has one representative and takes no disjunction, so the row would be "
                "meaningless rather than merely unevaluated."
            ),
        },
    )

    gate_passed = conjunction
    verdict_token = pass_token if gate_passed else fail_token
    verdict = ("PASS — " if gate_passed else "FAIL — ") + verdict_token

    # -- the portable guard ------------------------------------------------------------------------
    # Not stage2_package.py's guard, which refuses to write unless every condition is met: copying
    # that here would suppress a legitimate FAIL, and the constitution keeps negative results on
    # disk. What this refuses is a package that disagrees with its own evidence.
    if not evidence_digest_ok:
        print(
            "EVIDENCE DIGEST DID NOT RECOMPUTE — no package written\n"
            f"  recorded   {evidence['evidence_digest']}\n"
            f"  recomputed {evidence_digest}",
            flush=True,
        )
        return 3
    if not all_agree:
        disagreeing = sorted(cid for cid, e in agreement.items() if not e["agrees"])
        print(
            f"INDEPENDENT RE-DERIVATION DISAGREES WITH THE EVALUATOR ON {disagreeing} — "
            "no package written",
            flush=True,
        )
        return 3
    if gate_passed != bool(evidence["gate"]["gate_passed"]):
        print(
            f"CONJUNCTION DISAGREES WITH THE EVIDENCE: {gate_passed} vs "
            f"{evidence['gate']['gate_passed']} — no package written",
            flush=True,
        )
        return 3
    if verdict_token != evidence["gate"]["verdict_token"]:
        print(
            f"VERDICT TOKEN DISAGREES WITH THE EVIDENCE: {verdict_token!r} vs "
            f"{evidence['gate']['verdict_token']!r} — no package written",
            flush=True,
        )
        return 3
    if gate_passed and not_met:
        print(f"A PASS WITH {not_met} NOT MET IS INCOHERENT — no package written", flush=True)
        return 3
    if gate_passed and (not_evaluable or any(
        c["verdict"] in ("NOT_RUN", "UNKNOWN") for c in conditions.values()
    )):
        print("A PASS REACHED THROUGH NOT_EVALUABLE/NOT_RUN/UNKNOWN — no package written", flush=True)
        return 3
    if "ELIGIBLE_FOR_PAPER_TRADING" in verdict_token:
        print("GATE 4 MAY NOT EMIT GATE 5'S TOKEN — no package written", flush=True)
        return 3
    if not (records_ok and digests_ok):
        print(
            "INTEGRITY VERIFICATION FAILED BEFORE THE BUILD — no package written. A checksum record "
            "or a sealed digest did not verify, which is a blocker for a human to resolve, not a "
            "state this builder may write a verdict over.",
            flush=True,
        )
        return 3
    # A nonzero P5 is expected once the authorized evaluator exists, but only for causes that have
    # been named. An unexplained marker -- or any network/broker/environment marker at all -- is the
    # breach the predicate was sealed to catch, and it stops the package here.
    p5 = contamination["stage_4_modules_touching_restricted_data_or_a_broker"]
    if p5["unresolved"]:
        print(
            f"UNRESOLVED CONTAMINATION MARKER IN {p5['unresolved']} — no package written. Every P5 "
            "hit must resolve to a named cause before a verdict may be written over it.",
            flush=True,
        )
        return 3
    if not p5["no_network_or_broker_import_anywhere"]:
        print(
            "A NETWORK, BROKER OR ENVIRONMENT MARKER IS PRESENT IN A STAGE 4 MODULE — no package "
            "written. This is the fail-closed half of the sealed predicate and it is a blocker.",
            flush=True,
        )
        return 3
    # Nothing may embed a tree digest inside the tree it covers. The validation report is a
    # governance Markdown file and is therefore inside repo_state_id's own patterns, so a digest
    # written into it would invalidate itself on write.
    report_text = read_text(VALIDATION_REPORT)
    for tree_digest_value in (
        repo_state_id,
        load(SEALING_RUN)["repo_state_id"],
        load(PREREG_PACKAGE_RUN)["repo_state_id"],
        evaluation_run["repo_state_id"],
    ):
        if tree_digest_value in report_text:
            print(
                f"A TREE DIGEST APPEARS IN {VALIDATION_REPORT} — no package written. repo_state_id "
                "covers governance/*.md and would invalidate itself on write.",
                flush=True,
            )
            return 3

    base = evidence["gate_evidence"]["base"]
    stress = evidence["gate_evidence"]["stress"]
    read_footprint = evidence["single_validation_read"]

    decision = StageDecision(
        stage="STAGE_4_VALIDATION",
        stage_slug="stage4",
        decision_basename="STAGE_4_VALIDATION",
        manifest_basename="STAGE_4_VALIDATION_ARTIFACT_MANIFEST",
        gate_id=4,
        gate_name="validation_robustness",
        verdict=verdict,
        gate_passed=gate_passed,
        command=COMMAND,
        gate_conditions=conditions,
        evidence=[
            f"Representative {REPRESENTATIVE}, selected by {selection['artifact_id']} rule "
            f"{selection['selection_rule']['id']} ({selection['selection_rule']['name']}), "
            f"evaluated once on the locked validation window "
            f"{read_footprint['validation_partition']['start']}.."
            f"{read_footprint['validation_partition']['end']}.",
            f"Evidence file {EVIDENCE_REL} ({evidence['artifact_id']}), self-digest "
            f"{evidence['evidence_digest']}, recomputed from the written file by this builder and "
            f"equal.",
            f"Validation dataset loads {read_footprint['validation_dataset_loads']}; validation "
            f"reading sessions {read_footprint['validation_reading_sessions']}; validation-window "
            f"engine runs {read_footprint['validation_window_engine_runs']}; declared run count "
            f"{protocol['runs_declared']['count']}, recorded as a hard limit. Run record "
            f"{read_footprint['run_record']}.",
            f"Base-cost run: total return {base['total_return']}, Sharpe {base['sharpe']} at a "
            f"documented cash rate of {base['sharpe_risk_free_annual']}, maximum drawdown "
            f"{base['max_drawdown']}, profit factor {base['profit_factor']}, "
            f"{base['closed_trades']} closed trades, section 5.1 shutdown session "
            f"{base['shutdown_session']}.",
            f"Stressed-cost run at the sealed multiplier {stress['stress_multiplier']}: total "
            f"return {stress['total_return']}, shutdown enforced "
            f"{stress['shutdown_enforced']}, shutdown session {stress['shutdown_session']}.",
            f"Folds: {evidence['folds']['declared_test_folds']} declared test folds, "
            f"{evidence['folds']['declared_train_folds']} training folds, "
            f"{evidence['folds']['completed']} completed, {evidence['folds']['positive']} positive. "
            f"Smallest passing count at twelve completed folds is 9.",
            f"S4-C7 invariance: {digests_detail['rechecked']} of "
            f"{digests_detail['declared_set_size']} sealed digests recomputed here and all equal; "
            f"exactly one validation evaluation run record ({evaluation_run_id}); engine runs equal "
            f"the declared count.",
            f"Every one of the seven sealed conditions was re-derived by this builder from the raw "
            f"measurements against thresholds parsed out of the sealed predicate strings, in Decimal "
            f"with no rounding before comparison, and all seven agree with the evaluator.",
            f"{records_detail['records_verified']} checksum records plus the Stage 0 freeze verified, "
            f"each from the working directory its own convention requires; every entry OK.",
            f"Repository-state delta measured at build time rather than predicted: see "
            f"repo_state_delta in this record for the seal-to-evaluation, evaluation-to-build and "
            f"seal-to-build diffs and for the protected-path check.",
            f"Holdout {lock['partition']['holdout_start']}..{lock['partition']['holdout_end']} "
            f"state {read_footprint['holdout_partition']['state']}, sessions read "
            f"{read_footprint['holdout_partition']['sessions_read']}. Unreachability is proved "
            f"mechanically in the evidence file, not asserted.",
        ],
        limitations=[
            "The verdict is a fail. The five met conditions are met on a very small equity "
            "amplitude: 2.15% total return over three years on 41 closed trades. S4-C3 is met at "
            "3.16% against a 15% ceiling because the curve barely moved, not because a drawdown was "
            "survived, and S4-C5 is met by 15 basis points.",
            "The universe is one symbol, SPY. Every figure is a single-instrument result and "
            "carries no cross-sectional evidence.",
            "One representative, one window, one read, one parameterisation. The gate says nothing "
            "about SE100-S3A2-C1-PULLBACK-RA1 and nothing about this candidate on any other period.",
            "The documented cash rate is 0.00%, sealed and labelled conservative. Any positive cash "
            "rate would lower the measured Sharpe further, never raise it.",
            "S4-CONFLICT-5 stands: 'walk-forward' degenerates to twelve contiguous out-of-sample "
            "quarters with no re-estimation, because the representative estimates nothing. The fold "
            "stability measurement is weaker than the constitutional phrase suggests.",
            "The validation window is now spent. It has been read once, which is all the design "
            "permits, and it cannot be read again.",
            "No test can cover this decision package: tests/**/*.py is one of the repo_state_id "
            "patterns, so a test asserting this package's repo_state_id would invalidate the value "
            "it asserts. The package is verified by re-running the recomputation.",
            "The full suite ends 1 failed. That failure is the S4-CONFLICT-7 marker test and is "
            "left failing deliberately; it is a disclosure, not a defect. No test was weakened, "
            "skipped, xfailed or deleted to reach any verdict here.",
        ],
        blockers=[],
        conflicts_found=[
            "S4-CONFLICT-1 through S4-CONFLICT-5 were found and resolved prospectively by the "
            "pre-registration and are recorded in config/stage4_gate_criteria.json conflicts_found. "
            "All five were applied here exactly as sealed and none was reopened.",
            "S4-CONFLICT-6: the sealed invariance clause names config/stage4_representative_"
            "selection.json as the home of the representative's parameterisation; that file carries "
            "no parameter values and they are in config/stage4_validation_protocol.json "
            "sealed_representative. Both files are inside the thirteen-artifact digest set and both "
            "recompute equal, so the clause's purpose is satisfied whichever is read. Reported, not "
            "repaired. Nothing in the verdict turns on it.",
            "S4-CONFLICT-7: the sealed P5 contamination predicate states its purpose as the "
            "fail-closed proof that the PRE-REGISTRATION path cannot reach restricted data or a "
            "broker, but its mechanical scope is every stage4-named module under src/. The "
            "evaluator the pre-registration authorized must call a dataset loader, so the "
            "data-access half can never read 0 again; it measures "
            f"{p5['data_access_half']['count']} here. The seal's own frozen implementation of the "
            f"same predicate measures {p5['reference_implementation']['count']}, because its "
            "literal LOADER_CALLS frozenset was written before the evaluator existed and cannot "
            "name load_validation_series. Both are reported and neither is edited to match the "
            "other; see contamination_predicates.stage_4_modules_touching_restricted_data_or_a_"
            "broker.two_implementations_disagree. Neither reading is 0, so nothing about this "
            "conflict turns on the choice. The broker, network, environment-variable and "
            f"URL half measures {p5['broker_network_env_url_half']['count']} and remains the "
            "fail-closed proof it was written to be. Every hit on either half is resolved to a named "
            "cause in contamination_predicates.resolution, none is a network or broker reach, and the "
            "builder refuses to write if any hit is unresolved. Reported, not repaired: renaming the evaluator out of the "
            "stage4 path would hide a real dataset load from a predicate written to find it and "
            "would corrupt predicate P1 as well; weakening, skipping, xfailing or deleting the "
            "marker test is forbidden; and editing the seal after a validation read is forbidden by "
            "post_seal_defect_rule regardless of intent. The marker test is left failing as the "
            "disclosure mechanism.",
        ],
        produced=list(PRODUCED),
        frozen_inputs=list(STAGE_0_FROZEN_INPUTS)
        + list(STAGE_1_FROZEN_INPUTS)
        + list(STAGE_2_FROZEN_INPUTS)
        + list(STAGE_3_FROZEN_INPUTS)
        + list(STAGE_4_SEALED_INPUTS),
        body={
            "session_type": "SEALED_VALIDATION_EXECUTION_AND_GATE_4_DECISION",
            "gate_4_evaluated": True,
            "gate_4_passed": gate_passed,
            "representative": evidence["representative"],
            "protocol": {
                "protocol_id": protocol["artifact_id"],
                "criteria_id": criteria["artifact_id"],
                "selection_id": selection["artifact_id"],
                "selection_rule_id": selection["selection_rule"]["id"],
                "selection_rule_name": selection["selection_rule"]["name"],
                "prohibited_after_the_selection_seal": selection["prohibited_after_this_seal"],
                "seal_document_id": seal["document_id"],
                "sealed_utc": seal["declared_utc"],
                "sealing_run": SEALING_RUN,
                "preregistration_package_run": PREREG_PACKAGE_RUN,
                "validation_evaluation_run": "runs/" + evaluation_run_id + ".json",
                "authorized_for": seal["validation_evaluation_authorized_for"],
            },
            "verdict_derivation": {
                "pass_token": pass_token,
                "fail_token": fail_token,
                "source": CRITERIA + " verdict_token_derivation",
                "fail_condition": derivation["fail_condition"],
                "token_emitted": verdict_token,
                "token_taken_from_disk_not_from_a_prompt": True,
                "within_candidate": "CONJUNCTIVE",
                "across_candidates": "NOT_APPLICABLE_EXACTLY_ONE_REPRESENTATIVE",
                "conjunction": conjunction,
            },
            "independent_rederivation": {
                "why": (
                    "The evaluator that produced the evidence recorded a verdict per condition. "
                    "Trusting it here would make this package a copy rather than a check, so every "
                    "comparison was redone from the raw measurements against thresholds parsed out "
                    "of the sealed predicate strings, in Decimal, with no rounding before "
                    "comparison."
                ),
                "all_seven_agree": all_agree,
                "per_condition": agreement,
                "rederived": rederived,
            },
            "single_validation_read": read_footprint,
            "run_evidence": {
                "declared_run_count": protocol["runs_declared"]["count"],
                "count_is_a_hard_limit": protocol["runs_declared"]["count_is_a_hard_limit"],
                "single_validation_read_rule": protocol["single_validation_read_rule"],
                "partial_or_failed_run_rule": protocol["partial_or_failed_run_rule"],
                "runs": evidence["runs"],
                "base": base,
                "stress": stress,
                "failed_or_partial_runs": 0,
                "unregistered_runs": 0,
                "repeated_runs": 0,
                "rerun_policy_applied": (
                    "No run failed and no run was partial, so the sealed failed-run rule was not "
                    "invoked. Both registered runs completed inside the single authorized load and "
                    "reached the window end. After a valid completed run no rerun is permitted, and "
                    "none was performed."
                ),
            },
            "folds": evidence["folds"],
            "strategy_invariance": {
                "evaluator_measurement": evidence["strategy_invariance"],
                "package_recheck": digests_detail,
                "conflict_note": evidence["gate_evidence"]["invariance"].get("conflict_note"),
                "no_tolerance_rule": (
                    "Exact equality of every digest. There is no tolerance and no immaterial change. "
                    "The set was rechecked before the validation load, again by the evaluator, and "
                    "a third time here."
                ),
                "representative_not_modified_after_performance_was_observed": True,
            },
            "integrity_verification": {
                "checksum_records": records_detail,
                "evidence_digest": {
                    "recorded": evidence["evidence_digest"],
                    "recomputed": evidence_digest,
                    "equal": evidence_digest_ok,
                    "covers": evidence["evidence_digest_covers"],
                },
                "repo_state_delta": delta,
                "frozen_artifacts_modified": False,
                "sealed_artifacts_modified": False,
                "self_reference_policy": (
                    "The manifest excludes its own entry and is covered by the checksum record. No "
                    "repo_state_id is written into any governance Markdown; the validation report is "
                    "searched for all three tree digests before this package is written, and the "
                    "build refuses if one is present."
                ),
                "package_not_covered_by_tests": (
                    "tests/**/*.py is one of the repo_state_id patterns, so a test asserting this "
                    "package's repo_state_id would invalidate the value it asserts. The package is "
                    "verified by re-running the recomputation."
                ),
            },
            "contamination_predicates": contamination,
            "holdout": {
                "lock_artifact": lock["artifact_id"],
                "lock_status": lock["status"],
                "start": lock["partition"]["holdout_start"],
                "end": lock["partition"]["holdout_end"],
                "state": read_footprint["holdout_partition"]["state"],
                "sessions_read": read_footprint["holdout_partition"]["sessions_read"],
                "access_authorized": False,
                "unreachability_proof": evidence["holdout_unreachability_proof"],
                "unchanged_by_this_stage": True,
            },
            "defects_found_and_corrected": {
                "rule": protocol["post_seal_defect_rule"],
                "all_corrected_before_the_validation_load": True,
                "none_corrected_after_performance_was_visible": True,
                "items": [
                    {
                        "defect": "unique_run_id: two records generated inside the same second "
                                  "would have overwritten an append-only runs/ record",
                        "correction": "re-read the clock and raise rather than overwrite",
                        "validation_loaded_at_the_time": False,
                        "performance_visible_at_the_time": False,
                    },
                    {
                        "defect": "label_suffix_for failed OPEN on an unrecognised scenario, "
                                  "returning a usable run label instead of refusing",
                        "correction": "raise; covered in both directions",
                        "validation_loaded_at_the_time": False,
                        "performance_visible_at_the_time": False,
                    },
                    {
                        "defect": "fold_construction emitted without its sealed method key",
                        "correction": "key added from the sealed construction record",
                        "validation_loaded_at_the_time": False,
                        "performance_visible_at_the_time": False,
                    },
                    {
                        "defect": "ConditionVerdict.to_json() omitted its summary key",
                        "correction": "key added",
                        "validation_loaded_at_the_time": False,
                        "performance_visible_at_the_time": False,
                    },
                    {
                        "defect": "Decimal values were not JSON-serialisable",
                        "correction": "_jsonable conversion preserving full precision as strings",
                        "validation_loaded_at_the_time": False,
                        "performance_visible_at_the_time": False,
                    },
                    {
                        "defect": "threshold_cross_check duplicated in the emitted gate block",
                        "correction": "de-duplicated",
                        "validation_loaded_at_the_time": False,
                        "performance_visible_at_the_time": False,
                    },
                ],
                "how_they_were_found": (
                    "An out-of-tree dry run under _scratch/ drove the evidence writer end to end "
                    "against synthetic bars in two price scenarios, with the dataset loader and both "
                    "output directories patched, before any real validation observation was loaded."
                ),
                "no_sealed_specification_was_altered": True,
            },
            "terminal_consequence": {
                "applies": not gate_passed,
                "binding_consequence": seal["binding_consequences"][7],
                "what_a_fail_does_not_authorize": protocol["no_retuning_rule"][
                    "what_a_fail_does_not_authorize"
                ],
                "what_a_fail_does_authorize": protocol["no_retuning_rule"][
                    "what_a_fail_does_authorize"
                ],
                "there_is_no_attempt_2_at_gate_4": True,
            },
            "scope": {
                "candidates_evaluated": 1,
                "candidates_evaluated_ids": [REPRESENTATIVE],
                "other_gate_3_candidate_reconsidered": False,
                "neighbours_promoted": 0,
                "parameterisations_evaluated": 1,
                "validation_dataset_loads": read_footprint["validation_dataset_loads"],
                "validation_reading_sessions": read_footprint["validation_reading_sessions"],
                "validation_window_engine_runs": read_footprint["validation_window_engine_runs"],
                "training_folds": evidence["folds"]["declared_train_folds"],
                "refits_on_validation_data": 0,
                "retunes": 0,
                "threshold_changes": 0,
                "fold_boundary_changes": 0,
                "cost_benchmark_or_metric_changes": 0,
                "sensitivity_checks_run": 0,
                "debugging_performance_runs": 0,
                "alternative_metrics_computed": 0,
                "external_data_acquired": "none",
                "holdout_sessions_read": 0,
                "stage_5_work_performed": "none",
                "broker_connections": 0,
                "credentials_used": "none",
                "orders_generated": 0,
                "money_spent_usd": 0,
                "stage_5_remains_prohibited_conditions": protocol[
                    "stage_5_remains_prohibited_conditions"
                ],
                "explicit_non_authorizations": protocol["explicit_non_authorizations"],
            },
            "trade_readiness_statement": (
                "StockEdge100 is not trade-ready and is not described as trade-ready anywhere in "
                "this package. Gate 4 was not passed; even a pass would have conferred only the "
                "right to a separately authorized holdout gate, never ELIGIBLE_FOR_PAPER_TRADING, "
                "which is gate 5's token and which gate 4 may not emit."
            ),
        },
        tests={},  # filled below from the captured summary
        authorization_state={
            "final_holdout": "SEALED",
            "holdout_access": "NOT_AUTHORIZED",
            "validation_window": "READ_ONCE_AND_SPENT",
            "further_validation_reads": "NOT_AUTHORIZED",
            "stage_5_paper_trading": "NOT_AUTHORIZED",
            "constitutional_gate_5_holdout": "LOCKED_GATE_4_NOT_PASSED",
            "alpaca_paper_trading": "LOCKED",
            "shadow_live": "LOCKED",
            "alpaca_live_trading": "LOCKED",
            "capital_or_risk_expansion": "LOCKED",
            "retune_or_substitute_the_representative": "PROHIBITED_BY_THE_SEALED_TERMINAL_CONSEQUENCE",
        },
        next_authorized_stage=(
            "None within this design. Gate 4 was not passed, so it authorizes no further stage: not "
            "the constitutional holdout gate, not Stage 5, not a retune, not a substitution of "
            "SE100-S3A2-C1-PULLBACK-RA1, and not a second validation read. "
            "config/stage4_validation_protocol.json no_retuning_rule states what a fail does "
            "authorize in one sentence: recording the fail as a deliverable, and stopping. Any "
            "subsequent strategy work is a new candidate restarting at constitutional gate 3, "
            "disclosed as adaptive, with the validation window's information now known to the "
            "researcher and therefore permanently compromised for that candidate."
        ),
        dataset_hashes=dict(evidence["datasets"]["digests"]),
        universe_version=universe["universe_version"],
        date_range=[
            read_footprint["run_bounds"]["start"],
            read_footprint["run_bounds"]["end"],
        ],
        holdout_state=read_footprint["holdout_partition"]["state"],
        config_hash=sha256_file(PROJECT_ROOT / PROTOCOL),
        random_seed=None,
        run_notes=[
            "Gate 4 was evaluated and not passed. gate_passed is false, so the shared builder "
            "derives exit_status GATE_NOT_PASSED. That is the correct status for this package: the "
            "build succeeded and the gate did not.",
            "This package's own runs/ record carries strategy_id null, so it does not count as a "
            "validation evaluation run record under S4-C7. The one record that does is "
            + evaluation_run_id + ", identified by strategy_id rather than by filename.",
            "The single authorized validation read is complete and irreversible. One dataset load, "
            "two registered runs in the declared order, both reaching the window end. No rerun is "
            "permitted and none was performed.",
            "random_seed is null because the representative uses no randomness. Recording null "
            "rather than an unused integer keeps the field honest.",
            "All seven sealed conditions were re-derived independently by this builder and agree "
            "with the evaluator. The verdict token was taken from the sealed verdict_token_"
            "derivation on disk, not from any prompt.",
            "S4-CONFLICT-6 and S4-CONFLICT-7 are reported, not repaired. No frozen or sealed "
            "artifact was edited at any point in this session.",
            "The holdout was not read, no broker was contacted, no credential was accessed, and no "
            "order of any kind was generated. live_trading_authorized remains false.",
        ],
    )

    summary = read_text("reports/stage4/STAGE_4_VALIDATION_TEST_SUMMARY.md")
    decision.tests = _parse_test_counts(summary)

    result = build_stage_package(decision)
    if not result.freeze_ok:
        print("STAGE 0 FREEZE VERIFICATION FAILED — see the decision record", flush=True)
        return 2

    if result.repo_state_id != repo_state_id:
        print(
            f"repo_state_id MOVED DURING THE BUILD: {repo_state_id} -> {result.repo_state_id}",
            flush=True,
        )

    print(f"run_id        {result.run_id}")
    print(f"timestamp_utc {result.timestamp_utc}")
    print(f"repo_state_id {result.repo_state_id}")
    print(f"verdict       {verdict}")
    for path in (
        result.decision_path,
        result.manifest_path,
        result.checksum_path,
        result.run_record_path,
    ):
        print(f"wrote         {Path(path).relative_to(PROJECT_ROOT)}")
    return 0


def _parse_test_counts(summary: str) -> dict[str, int]:
    """Read the four counts out of the written test summary rather than hand-typing them here.

    A count typed into this module could drift from the pytest capture the summary quotes. Reading
    it back means the two cannot disagree without the parse failing loudly.
    """
    counts: dict[str, int] = {}
    for key in ("passed", "failed", "skipped", "collected"):
        found = re.search(rf"^\|\s*{key}\s*\|\s*(\d+)\s*\|", summary, re.MULTILINE | re.IGNORECASE)
        if found is None:
            raise ValueError(f"test summary carries no '{key}' row for the package to read")
        counts[key] = int(found.group(1))
    return counts


if __name__ == "__main__":
    raise SystemExit(build())
