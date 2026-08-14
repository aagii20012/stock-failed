"""Seal the Stage 3 Attempt 2 pre-registration.

Run from ``stockedge100/``, **before** any Attempt 2 strategy code is written::

    PYTHONPATH=src python -m stockedge100.reporting.stage3_attempt2_preregistration

Writes:

* ``governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json``   — authoritative declaration timestamp and
  the digest of every pre-registered file
* ``governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256`` — checksum record over those files
* one reproducibility record under ``runs/``

As in Stages 1, 2, and Attempt 1, the JSON carries **no** ``repo_state_id``: it lives in
``governance/`` and is one of the inputs to that digest, so any value written here would be stale on
write. The binding value is in the ``runs/`` record.

Why the contamination check is not Attempt 1's check
----------------------------------------------------

Attempt 1 sealed with ``src/stockedge100/strategies/`` empty and no result artifact anywhere, so it
could record two counts of zero over those literal paths. Both literal predicates are unavailable
now: that directory holds Attempt 1's nine modules and ``reports/stage3/`` holds Attempt 1's results,
and deleting either to restore a zero would destroy the evidence the constitution requires be kept.

Counting to zero over the same paths is therefore not the available test. Five Attempt-2-specific
predicates replace it, each narrow enough to be zero only if no Attempt 2 implementation or result
exists, and each carrying its own definition into the record so a reader can check what was counted
rather than trusting the count. Four must be zero; the fifth must verify.

The first predicate excludes ``reporting/`` because this module is itself
``src/stockedge100/reporting/stage3_attempt2_preregistration.py`` and would otherwise count itself.
That exclusion is a real narrowing of the check and is recorded as one: a sealing program is not a
strategy, but the exclusion is stated rather than left for a reader to discover.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from stockedge100.audit import (
    RunRecord,
    dependency_versions,
    sha256_file,
    utc_now_iso,
    write_sha256_record,
)
from stockedge100.reporting.stage_package import (
    PROJECT_ROOT,
    RUNS_DIR,
    TRACKED_DEPENDENCIES,
    new_run_id,
    repo_state,
    verify_sha256_record,
    verify_stage0_freeze,
)

PROTOCOL_REL = "config/stage3_attempt2_strategy_protocol.json"
BINDING_REL = "config/stage3_attempt2_gate_criteria_binding.json"
DOCUMENT_REL = "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.md"

PREREGISTERED = (PROTOCOL_REL, BINDING_REL, DOCUMENT_REL)

RECORD_JSON = PROJECT_ROOT / "governance" / "STAGE_3_ATTEMPT_2_PREREGISTRATION.json"
RECORD_SHA = PROJECT_ROOT / "governance" / "STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256"

SRC_DIR = PROJECT_ROOT / "src" / "stockedge100"
STRATEGY_DIR = SRC_DIR / "strategies"
REPORTS_DIR = PROJECT_ROOT / "reports"

STAGE_1_FREEZE = PROJECT_ROOT / "governance" / "STAGE_1_FREEZE.sha256"
STAGE_2_PREREG_SHA = PROJECT_ROOT / "governance" / "STAGE_2_PREREGISTRATION.sha256"
STAGE_2_DECISION_SHA = PROJECT_ROOT / "reports" / "stage2" / "STAGE_2_BACKTEST_ENGINE.sha256"
ATTEMPT_1_PREREG_SHA = PROJECT_ROOT / "governance" / "STAGE_3_PREREGISTRATION.sha256"
ATTEMPT_1_DECISION_SHA = PROJECT_ROOT / "reports" / "stage3" / "STAGE_3_STRATEGY_RESEARCH.sha256"

ATTEMPT_MARKER = "attempt2"
ATTEMPT_TOKEN = "ATTEMPT_2"

PREDICATE_DEFINITIONS = {
    "attempt_2_strategy_modules": (
        "Count of files under src/stockedge100/ with suffix .py whose path relative to the project "
        "root, lowercased with backslashes normalised to forward slashes, contains 'attempt2', "
        "EXCLUDING src/stockedge100/reporting/. The exclusion exists because the sealing program "
        "itself is src/stockedge100/reporting/stage3_attempt2_preregistration.py; it narrows the "
        "check and is recorded rather than hidden. Must be 0."
    ),
    "modules_naming_an_attempt_2_candidate": (
        "Count of files under src/stockedge100/strategies/ with suffix .py whose decoded text "
        "contains any candidate id declared in " + PROTOCOL_REL + ". Catches an Attempt 2 "
        "implementation added to an existing Attempt 1 module, which the path-based predicate above "
        "would miss. Must be 0."
    ),
    "attempt_2_report_artifacts": (
        "Count of files anywhere under reports/ whose project-root-relative path, lowercased and "
        "slash-normalised, contains 'attempt2'. Any Attempt 2 evidence, admissibility, or test "
        "artifact would appear here. Must be 0 at sealing."
    ),
    "attempt_2_run_records": (
        "Count of files under runs/ whose decoded text contains 'ATTEMPT_2' or any candidate id "
        "declared in " + PROTOCOL_REL + ". Measured BEFORE this seal writes its own run record, "
        "which carries stage STAGE_3_ATTEMPT_2_PRE_REGISTRATION and therefore contains the token by "
        "construction. A re-verification after sealing will legitimately count 1; the value recorded "
        "here is the count of records that existed before this run. Must be 0."
    ),
    "attempt_1_records_verify": (
        "Both governance/STAGE_3_PREREGISTRATION.sha256 and "
        "reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256 verify entry-for-entry from the project "
        "root. This is the Attempt 1 immutability check: it fails if any Attempt 1 pre-registered "
        "file or result artifact changed by a single byte. Must be true."
    ),
}


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _normalised_prose(text: str) -> str:
    """Strip Markdown presentation so a sentence can be compared across the two formats.

    The document quotes the research question as a wrapped blockquote, so the raw bytes carry ``> ``
    continuation markers and ``**`` emphasis that the JSON string does not. Removing blockquote
    prefixes, emphasis and code markers, then collapsing whitespace, compares the words rather than
    the layout. Both sides get the same treatment, so the test is symmetric.
    """
    lines = [line.lstrip().lstrip(">").strip() for line in text.splitlines()]
    stripped = " ".join(lines).replace("*", "").replace("`", "")
    return " ".join(stripped.split())


def _candidate_ids(protocol: dict) -> list[str]:
    return [experiment["experiment_id"] for experiment in protocol["experiments"]]


def _attempt_2_strategy_modules() -> list[str]:
    if not SRC_DIR.is_dir():
        return []
    reporting = (SRC_DIR / "reporting").resolve()
    hits = []
    for path in SRC_DIR.rglob("*.py"):
        if not path.is_file():
            continue
        if reporting in path.resolve().parents:
            continue
        if ATTEMPT_MARKER in _rel(path).lower():
            hits.append(_rel(path))
    return sorted(hits)


def _modules_naming_a_candidate(candidate_ids: list[str]) -> list[str]:
    if not STRATEGY_DIR.is_dir():
        return []
    hits = []
    for path in sorted(STRATEGY_DIR.rglob("*.py")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(candidate_id in text for candidate_id in candidate_ids):
            hits.append(_rel(path))
    return hits


def _attempt_2_report_artifacts() -> list[str]:
    if not REPORTS_DIR.is_dir():
        return []
    return sorted(
        _rel(path)
        for path in REPORTS_DIR.rglob("*")
        if path.is_file() and ATTEMPT_MARKER in _rel(path).lower()
    )


def _attempt_2_run_records(candidate_ids: list[str]) -> list[str]:
    if not RUNS_DIR.is_dir():
        return []
    hits = []
    for path in sorted(RUNS_DIR.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if ATTEMPT_TOKEN in text or any(candidate_id in text for candidate_id in candidate_ids):
            hits.append(_rel(path))
    return hits


def _check_record(label: str, path: Path, root: Path) -> list[str]:
    """Verify one checksum record and return the sorted names that did not come back ``OK``."""
    if not path.is_file():
        return [f"{label}: record missing at {path}"]
    results = verify_sha256_record(path, root=root)
    return sorted(f"{label}: {name} -> {result}" for name, result in results.items() if result != "OK")


def build() -> int:
    if RECORD_JSON.exists() or RECORD_SHA.exists():
        print("REFUSED: a Stage 3 Attempt 2 pre-registration record already exists.", file=sys.stderr)
        print("A pre-registration is sealed once. Regenerating it would destroy its meaning.", file=sys.stderr)
        return 2

    missing = [name for name in PREREGISTERED if not (PROJECT_ROOT / name).is_file()]
    if missing:
        print(f"REFUSED: pre-registered file(s) missing: {missing}", file=sys.stderr)
        return 5

    protocol = json.loads((PROJECT_ROOT / PROTOCOL_REL).read_text(encoding="utf-8"))
    binding = json.loads((PROJECT_ROOT / BINDING_REL).read_text(encoding="utf-8"))
    document = (PROJECT_ROOT / DOCUMENT_REL).read_text(encoding="utf-8")
    candidate_ids = _candidate_ids(protocol)

    # --- contamination, measured before anything is written ----------------------------------
    modules = _attempt_2_strategy_modules()
    naming = _modules_naming_a_candidate(candidate_ids)
    artifacts = _attempt_2_report_artifacts()
    records = _attempt_2_run_records(candidate_ids)

    contamination = {
        "attempt_2_strategy_modules": modules,
        "modules_naming_an_attempt_2_candidate": naming,
        "attempt_2_report_artifacts": artifacts,
        "attempt_2_run_records": records,
    }
    dirty = {name: hits for name, hits in contamination.items() if hits}
    if dirty:
        print("REFUSED: Attempt 2 implementation or result artifacts already exist.", file=sys.stderr)
        for name, hits in sorted(dirty.items()):
            print(f"  {name}: {len(hits)}", file=sys.stderr)
            for hit in hits:
                print(f"    {hit}", file=sys.stderr)
        print(
            "The design is not prospective with respect to those artifacts. Record the "
            "contamination and stop; do not seal.",
            file=sys.stderr,
        )
        return 3

    # --- upstream integrity ------------------------------------------------------------------
    freeze_ok, freeze_detail = verify_stage0_freeze()
    if not freeze_ok:
        print("REFUSED: the Stage 0 freeze does not verify. Stop and investigate.", file=sys.stderr)
        return 4

    # Freeze records store bare filenames, so they verify from the directory that holds them.
    # Every other record here uses project-root-relative paths. Each is checked with the root it
    # expects; passing the wrong one reports MISSING for every entry and looks like an integrity
    # failure when it is an operator error.
    stage1_freeze = verify_sha256_record(STAGE_1_FREEZE, root=STAGE_1_FREEZE.parent)
    problems = sorted(f"stage1_freeze: {n} -> {r}" for n, r in stage1_freeze.items() if r != "OK")
    problems += _check_record("stage2_prereg", STAGE_2_PREREG_SHA, PROJECT_ROOT)
    problems += _check_record("stage2_decision", STAGE_2_DECISION_SHA, PROJECT_ROOT)
    attempt_1_problems = _check_record("attempt1_prereg", ATTEMPT_1_PREREG_SHA, PROJECT_ROOT)
    attempt_1_problems += _check_record("attempt1_decision", ATTEMPT_1_DECISION_SHA, PROJECT_ROOT)
    problems += attempt_1_problems
    if problems:
        print("REFUSED: an upstream checksum record does not verify:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 4

    # --- the binding must still bind ----------------------------------------------------------
    bound = binding["bound_artifact"]
    bound_rel = bound["path"]
    bound_live = sha256_file(PROJECT_ROOT / bound_rel)
    if bound_live != bound["sha256"]:
        print("REFUSED: the bound Gate 3 criteria digest does not match the live file.", file=sys.stderr)
        print(f"  recorded {bound['sha256']}", file=sys.stderr)
        print(f"  live     {bound_live}", file=sys.stderr)
        print(
            "Attempt 2 adopts Gate 3 by reference, so a drifted digest means the criteria it "
            "claims to adopt are not the criteria on disk.",
            file=sys.stderr,
        )
        return 6

    # --- the document and the machine-readable specification must agree ----------------------
    disagreements = []
    for candidate_id in candidate_ids:
        if candidate_id not in document:
            disagreements.append(f"candidate {candidate_id} is not named in {DOCUMENT_REL}")
    if protocol["attempt_id"] not in document:
        disagreements.append(f"attempt_id {protocol['attempt_id']} is not named in {DOCUMENT_REL}")
    ceiling = binding["drawdown_ceiling_is_unchanged"]["value"]
    if ceiling != "0.15":
        disagreements.append(f"drawdown ceiling is {ceiling}, not the unchanged 0.15")
    if _normalised_prose(protocol["research_question"]) not in _normalised_prose(document):
        disagreements.append("the research question in the document does not match the protocol")
    if disagreements:
        print("REFUSED: the document and the machine-readable specification disagree:", file=sys.stderr)
        for line in disagreements:
            print(f"  {line}", file=sys.stderr)
        return 7

    timestamp = utc_now_iso()
    run_id = new_run_id(timestamp)
    digests = {name: sha256_file(PROJECT_ROOT / name) for name in PREREGISTERED}
    budget = protocol["iteration_budget"]
    cumulative = protocol["cumulative_experiment_count"]

    record = {
        "document_id": "SE100-GOV-0007",
        "project": "StockEdge100",
        "generation": 1,
        "stage": 3,
        "attempt": 2,
        "attempt_id": protocol["attempt_id"],
        "record_type": "PRE_REGISTRATION",
        "status": "SEALED",
        "declared_utc": timestamp,
        "run_id": run_id,
        "constitution_ref": "SE100-GOV-0001",
        "document_id_note": (
            "SE100-GOV-0004 is unused across the tree. This record takes 0007, the next number after "
            "the highest in use, rather than filling a gap whose reason is not recorded anywhere on "
            "disk."
        ),
        "supersedes": None,
        "relationship_to_attempt_1": (
            "None of Attempt 1 is modified, superseded, re-run, or repaired. SE100-GOV-0006 and its "
            "six candidates stand as sealed and as rejected. Attempt 2 is a new pre-registration "
            "declaring new candidates, which is the route constitution section 11 provides and the "
            "route the Attempt 1 research report names in its own closing section."
        ),
        "is_adaptive_second_attempt": True,
        "adaptation_disclosure_location": (
            PROTOCOL_REL + " adaptive_research_disclosure, and section 8 of " + DOCUMENT_REL
        ),
        "authorization_determination_location": PROTOCOL_REL + " authorization_determination",
        "gate": {
            "constitutional_gate": 3,
            "name": "development_admissibility",
            "criteria_source": bound_rel,
            "criteria_adoption": bound["adoption"],
            "criteria_sha256": bound_live,
            "criteria_changed_for_attempt_2": False,
            "conditions_evaluated": 7,
            "max_drawdown_ceiling": ceiling,
            "max_drawdown_ceiling_changed": False,
            "within_candidate": "CONJUNCTIVE",
            "across_candidates": "DISJUNCTIVE",
            "admissible_candidates_required": 1,
            "rederivations": [
                entry["id"] for entry in binding["rederivations"]
            ],
            "rederivation_note": (
                "Two enumerations in the sealed criteria name Attempt 1's candidates by id. Both are "
                "re-derived by applying the sealed RULE to Attempt 2's candidate set rather than "
                "carrying the sealed OUTPUT forward. No threshold, predicate, denominator, "
                "measurement procedure, or verdict token is changed. See " + BINDING_REL + "."
            ),
        },
        "stage_0_freeze_verified": True,
        "stage_0_freeze_verification": freeze_detail,
        "stage_1_freeze_verified": True,
        "stage_1_freeze_files": sorted(stage1_freeze),
        "stage_2_preregistration_verified": True,
        "stage_2_decision_record_verified": True,
        "attempt_1_preregistration_verified": True,
        "attempt_1_decision_record_verified": True,
        "sealed_before_any_attempt_2_strategy_code": True,
        "contamination_predicates": {
            "definitions": PREDICATE_DEFINITIONS,
            "attempt_2_strategy_modules": len(modules),
            "modules_naming_an_attempt_2_candidate": len(naming),
            "attempt_2_report_artifacts": len(artifacts),
            "attempt_2_run_records": len(records),
            "attempt_1_records_verify": True,
            "why_not_attempt_1_predicates": (
                "Attempt 1 recorded strategy_modules_present_at_seal_time 0 and "
                "strategy_output_files_present_at_seal_time 0 over src/stockedge100/strategies/ and "
                "reports/stage3/. Both directories are now legitimately non-empty with Attempt 1's "
                "own modules and results, which may not be deleted, so counting to zero over those "
                "paths is not the available test. Attempt 1 recorded its two counts as bare integers "
                "with no definition attached; each predicate here carries its definition."
            ),
        },
        "candidates_declared": budget["candidates"],
        "candidate_ids": candidate_ids,
        "families_retained": protocol["families_excluded"]["families_retained"],
        "families_excluded": [entry["family"] for entry in protocol["families_excluded"]["excluded"]],
        "shared_risk_architecture": protocol["risk_architecture"]["id"],
        "robustness_neighbours_per_candidate": 4,
        "max_variants_per_candidate": budget["max_variants_per_candidate"],
        "declared_gating_variants": budget["total_declared_gating_variants"],
        "declared_runs": budget["total_declared_runs"],
        "revisions_permitted": budget["revisions_permitted"],
        "cumulative_experiment_count": {
            "cumulative_candidates": cumulative["cumulative_candidates"],
            "cumulative_gating_variants": cumulative["cumulative_gating_variants"],
            "cumulative_total_runs": cumulative["cumulative_total_runs"],
            "binding_number_for_interpretation": cumulative["binding_number_for_interpretation"],
        },
        "preregistered_files": {name: {"sha256": digest} for name, digest in digests.items()},
        "checksum_record": {
            "path": "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256",
            "path_convention": "project-root-relative",
            "verify_from": "stockedge100/",
            "command": (
                "cd stockedge100 && sha256sum -c "
                "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256"
            ),
        },
        "repo_state_id_location": (
            "Deliberately omitted here. This file lives in governance/ and is one of the inputs to "
            "repo_state_id, so any value written into it would be stale on write. The binding value "
            f"is the repo_state_id field of runs/{run_id}.json."
        ),
        "binding_consequences": [
            "Every hypothesis, universe, exclusion, eligibility rule, signal timing, entry rule, "
            "exit rule, holding period, sizing rule, exposure cap, cash rule, loss control, "
            "de-risking ladder, re-entry delay, conflict rule, parameter value, permitted parameter "
            "grid, and warm-up length for all three candidates is fixed as of this timestamp and may "
            "not be revised because of a result it produces.",
            "The iteration budget is one primary run plus four declared neighbour runs per candidate "
            "and zero revisions. A candidate that fails is reported as failed. Under constitution "
            "section 11 a material change creates a new candidate that restarts at gate 3; it does "
            "not repair this one.",
            "The four robustness neighbours per candidate are read for the sign of net return only. "
            "No neighbour is ever promoted to primary or to representative of its candidate, and no "
            "parameterisation is selected from them.",
            "Gate 3 is adopted by digest, not by copy. The 15% maximum-drawdown ceiling, every other "
            "threshold, every measurement procedure, the NOT_EVALUABLE semantics, and the conjunction "
            "logic are unchanged.",
            "No machine learning, no fundamental or earnings data, no intraday data, and no "
            "combination of one candidate with another, per constitution section 8.",
            "Attempt 2 reads development-window data only. Validation stays LOCKED and holdout stays "
            "SEALED.",
            "This is an adaptive second attempt. The development window is no longer pristine, the "
            "cumulative experiment count is 9 candidates and 45 gating variants, and no Attempt 2 "
            "result may be described as independent confirmation because its code is new.",
            "Gate 3 is admissibility, not selection. No candidate is ranked, preferred, or named a "
            "winner, and no expected income, profit, or return is claimed for any period.",
            "AAPL is present on disk as a Stage 1 split fixture, is not a member of the frozen "
            "universe, and is excluded from every candidate.",
            "live_trading_authorized remains false.",
        ],
        "authorized_windows": ["development"],
        "validation_window_state": "LOCKED",
        "holdout_window_state": "SEALED",
        "strategy_research_authorized_for": (
            "Implementation and development-window evaluation of exactly the three candidates sealed "
            "here, in a later separately authorized session. Nothing else."
        ),
        "stage_4_authorized": False,
        "paper_trading_authorized": False,
        "shadow_live_authorized": False,
        "live_trading_authorized": False,
    }
    RECORD_JSON.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # Written last so it covers the final bytes of the JSON above. It does not contain its own
    # digest; nothing hashes itself.
    covered = dict(digests)
    covered["governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json"] = sha256_file(RECORD_JSON)
    own_digest = write_sha256_record(covered, RECORD_SHA)

    code_hashes, repo_state_id = repo_state()
    RunRecord(
        run_id=run_id,
        stage="STAGE_3_ATTEMPT_2_PRE_REGISTRATION",
        command="python -m stockedge100.reporting.stage3_attempt2_preregistration",
        timestamp_utc=timestamp,
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=digests[PROTOCOL_REL],
        dataset_hashes={},
        universe_version="SE100-CFG-1002@1.0.0",
        date_range=None,
        holdout_state="SEALED",
        strategy_id=None,
        random_seed=None,
        dependency_versions=dependency_versions(TRACKED_DEPENDENCIES),
        exit_status="OK",
        output_artifact_hashes={
            "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json": covered[
                "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json"
            ],
            "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256": own_digest,
        },
        notes=[
            "Three strategy specifications and the Gate 3 criteria binding sealed before any Attempt "
            "2 strategy code existed.",
            "Attempt 2 is an adaptive second attempt at Gate 3. Attempt 1's results are known; the "
            "disclosure is in the pre-registration rather than in a later interpretation.",
            "Contamination measured over four Attempt-2-specific predicates, all zero, each with its "
            "definition recorded in the sealed JSON. Attempt 1's literal predicates are unavailable "
            "because its own modules and results are legitimately on disk and may not be deleted.",
            "Attempt 1 immutability verified: governance/STAGE_3_PREREGISTRATION.sha256 and "
            "reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256 both verify entry-for-entry.",
            "Gate 3 adopted by digest. The 15% maximum-drawdown ceiling is unchanged.",
            "strategy_id is null because no candidate has been run and no candidate may be run in "
            "this session.",
            "No credential access. No order. No backtest, simulation, parameter sweep, or "
            "performance calculation. No validation or holdout read.",
        ],
    ).write(RUNS_DIR)

    print(f"run_id           {run_id}")
    print(f"declared_utc     {timestamp}")
    print(f"repo_state_id    {repo_state_id}")
    print(f"candidates       {len(candidate_ids)}  {', '.join(candidate_ids)}")
    print(f"gate criteria    {bound_rel} @ {bound_live}  (adopted unchanged)")
    print("contamination    " + ", ".join(
        f"{name}={len(hits)}" for name, hits in sorted(contamination.items())
    ))
    for name, digest in digests.items():
        print(f"  {digest}  {name}")
    print("sealed           governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json / .sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
