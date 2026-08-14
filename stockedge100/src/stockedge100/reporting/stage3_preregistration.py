"""Seal the Stage 3 pre-registration.

Run from ``stockedge100/``, **before** any strategy code is written::

    PYTHONPATH=src python -m stockedge100.reporting.stage3_preregistration

Writes:

* ``governance/STAGE_3_PREREGISTRATION.json``   — authoritative declaration timestamp and the digest
  of every pre-registered file
* ``governance/STAGE_3_PREREGISTRATION.sha256`` — checksum record over those files
* one reproducibility record under ``runs/``

As with Stages 1 and 2, the JSON carries **no** ``repo_state_id``: it lives in ``governance/`` and is
one of the inputs to that digest, so any value written here would be stale on write. The binding
value is in the ``runs/`` record.

Refuses to run if a record already exists, if any Python module exists under
``src/stockedge100/strategies/``, or if any Stage 3 output exists under ``reports/stage3/``.

Stage 2's refusal existed because a cost model sealed after the engine could produce a number may
have been chosen because of that number. Here the exposure is larger, not smaller. A strategy is a
collection of free parameters, and every one of them — lookback, threshold, universe member,
rebalance date, warm-up length — can be nudged after a disappointing result and nudged back after a
good one, leaving no trace in the output. The ordering check is the only thing that distinguishes a
rule that was specified from a rule that was found.
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

PREREGISTERED = (
    "config/stage3_strategy_protocol.json",
    "config/stage3_gate_criteria.json",
    "governance/STAGE_3_PREREGISTRATION.md",
)

RECORD_JSON = PROJECT_ROOT / "governance" / "STAGE_3_PREREGISTRATION.json"
RECORD_SHA = PROJECT_ROOT / "governance" / "STAGE_3_PREREGISTRATION.sha256"

STRATEGY_DIR = PROJECT_ROOT / "src" / "stockedge100" / "strategies"
STAGE_3_REPORTS_DIR = PROJECT_ROOT / "reports" / "stage3"

STAGE_1_FREEZE = PROJECT_ROOT / "governance" / "STAGE_1_FREEZE.sha256"
STAGE_2_PREREG_SHA = PROJECT_ROOT / "governance" / "STAGE_2_PREREGISTRATION.sha256"
STAGE_2_DECISION_SHA = PROJECT_ROOT / "reports" / "stage2" / "STAGE_2_BACKTEST_ENGINE.sha256"


def _strategy_files() -> list[Path]:
    if not STRATEGY_DIR.is_dir():
        return []
    return [p for p in STRATEGY_DIR.rglob("*") if p.is_file() and p.suffix == ".py"]


def _strategy_output_files() -> list[Path]:
    if not STAGE_3_REPORTS_DIR.is_dir():
        return []
    return [p for p in STAGE_3_REPORTS_DIR.rglob("*") if p.is_file()]


def _check_record(label: str, path: Path, root: Path) -> list[str]:
    """Verify one checksum record and return the sorted names that did not come back ``OK``."""
    if not path.is_file():
        return [f"{label}: record missing at {path}"]
    results = verify_sha256_record(path, root=root)
    return sorted(f"{label}: {name} -> {result}" for name, result in results.items() if result != "OK")


def build() -> int:
    if RECORD_JSON.exists() or RECORD_SHA.exists():
        print("REFUSED: a Stage 3 pre-registration record already exists.", file=sys.stderr)
        print("A pre-registration is sealed once. Regenerating it would destroy its meaning.", file=sys.stderr)
        return 2

    strategies = _strategy_files()
    if strategies:
        print(f"REFUSED: {len(strategies)} strategy module(s) already exist under src/stockedge100/strategies/.", file=sys.stderr)
        print("The strategy specifications and gate criteria must be sealed before any strategy code exists.", file=sys.stderr)
        return 3

    output = _strategy_output_files()
    if output:
        print(f"REFUSED: {len(output)} Stage 3 output file(s) already exist under reports/stage3/.", file=sys.stderr)
        print("No strategy result may exist when the specifications are sealed.", file=sys.stderr)
        return 3

    freeze_ok, freeze_detail = verify_stage0_freeze()
    if not freeze_ok:
        print("REFUSED: the Stage 0 freeze does not verify. Stop and investigate.", file=sys.stderr)
        return 4

    # Freeze records store bare filenames, so they verify from the directory that holds them.
    # Passing PROJECT_ROOT here would report MISSING for every entry — an operator error dressed up
    # as an integrity failure. The Stage 2 records use project-root-relative paths instead, so they
    # verify from PROJECT_ROOT; the two conventions are checked with the root each one expects.
    stage1_freeze = verify_sha256_record(STAGE_1_FREEZE, root=STAGE_1_FREEZE.parent)
    problems = sorted(f"stage1_freeze: {n} -> {r}" for n, r in stage1_freeze.items() if r != "OK")
    problems += _check_record("stage2_prereg", STAGE_2_PREREG_SHA, PROJECT_ROOT)
    problems += _check_record("stage2_decision", STAGE_2_DECISION_SHA, PROJECT_ROOT)
    if problems:
        print("REFUSED: an upstream checksum record does not verify:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 4

    missing = [name for name in PREREGISTERED if not (PROJECT_ROOT / name).is_file()]
    if missing:
        print(f"REFUSED: pre-registered file(s) missing: {missing}", file=sys.stderr)
        return 5

    timestamp = utc_now_iso()
    run_id = new_run_id(timestamp)
    digests = {name: sha256_file(PROJECT_ROOT / name) for name in PREREGISTERED}

    record = {
        "document_id": "SE100-GOV-0006",
        "project": "StockEdge100",
        "generation": 1,
        "stage": 3,
        "record_type": "PRE_REGISTRATION",
        "status": "SEALED",
        "declared_utc": timestamp,
        "run_id": run_id,
        "constitution_ref": "SE100-GOV-0001",
        "gate": {
            "constitutional_gate": 3,
            "name": "development_admissibility",
            "pass_conditions": [
                "total return is positive",
                "maximum drawdown is no worse than 15%",
                "profit factor is at least 1.10",
                "at least 30 closed trades exist, unless a lower-frequency protocol predeclared a "
                "longer evidence requirement before results",
                "performance is not dependent on one trade: removing the single best trade leaves "
                "total return above 0%",
                "no single instrument contributes more than 50% of total strategy profit for a "
                "multi-instrument strategy",
                "reasonable neighboring parameter values do not reverse the sign of net return",
            ],
            "fail_result": "STRATEGY_REJECTED_IN_DEVELOPMENT",
            "pass_result_source": (
                "Not stated in the frozen artifact. Derived by negation of fail_result and fixed "
                "before any result: STRATEGY_ADMITTED_IN_DEVELOPMENT. See "
                "config/stage3_gate_criteria.json verdict_token_derivation."
            ),
            "conditions_in_frozen_json_companion": 5,
            "conditions_in_frozen_markdown": 7,
            "conditions_evaluated": 7,
            "condition_count_note": (
                "The frozen Markdown is authoritative and more restrictive than its JSON companion, "
                "which omits the profit-concentration and neighboring-parameter conditions. All "
                "seven are evaluated. Reported, not repaired; the frozen artifact is not edited."
            ),
        },
        "stage_0_freeze_verified": True,
        "stage_0_freeze_verification": freeze_detail,
        "stage_1_freeze_verified": True,
        "stage_1_freeze_files": sorted(stage1_freeze),
        "stage_2_preregistration_verified": True,
        "stage_2_decision_record_verified": True,
        "sealed_before_any_strategy_code": True,
        "strategy_modules_present_at_seal_time": 0,
        "strategy_output_files_present_at_seal_time": 0,
        "candidates_declared": 6,
        "candidate_ids": [
            "SE100-S3-F1-TREND-SMA200",
            "SE100-S3-F2-PULLBACK-SMA200-SMA10",
            "SE100-S3-F3-MEANREV-RSI2",
            "SE100-S3-F4-BREAKOUT-DONCHIAN-50-25",
            "SE100-S3-F5-ROTATION-DUALMOM",
            "SE100-S3-F6-DEFENSIVE-SMA200-SHY",
        ],
        "robustness_neighbours_per_candidate": 4,
        "declared_runs": 30,
        "revisions_permitted": 0,
        "preregistered_files": {name: {"sha256": digest} for name, digest in digests.items()},
        "checksum_record": {
            "path": "governance/STAGE_3_PREREGISTRATION.sha256",
            "path_convention": "project-root-relative",
            "verify_from": "stockedge100/",
            "command": "cd stockedge100 && sha256sum -c governance/STAGE_3_PREREGISTRATION.sha256",
        },
        "repo_state_id_location": (
            "Deliberately omitted here. This file lives in governance/ and is one of the inputs to "
            "repo_state_id, so any value written into it would be stale on write. The binding value "
            f"is the repo_state_id field of runs/{run_id}.json."
        ),
        "binding_consequences": [
            "Every hypothesis, universe, exclusion, lookback, threshold, entry rule, exit rule, "
            "sizing rule, ranking rule, conflict rule, rebalance date, warm-up length, and run-start "
            "rule for all six candidates is fixed as of this timestamp and may not be revised "
            "because of a result it produced.",
            "The iteration budget is one primary run per candidate and zero revisions. A candidate "
            "that fails is reported as failed. Under constitution section 11 a material change "
            "creates a new candidate that restarts at gate 3; it does not repair this one.",
            "The four robustness neighbours per candidate are read for the sign of net return only. "
            "No neighbour is ever promoted to primary and no parameterisation is selected from them.",
            "How each of the seven gate conditions is measured — not merely its threshold — is fixed "
            "in config/stage3_gate_criteria.json, including the undefined and not-evaluable "
            "treatments and the scope of the multi-instrument concentration condition.",
            "No machine learning of any kind is used, per constitution section 8. No candidate is "
            "combined with any other candidate.",
            "Stage 3 reads development-window data only. Validation stays LOCKED and holdout stays "
            "SEALED.",
            "Gate 3 is admissibility, not selection. No candidate is ranked, preferred, or named a "
            "winner, and no expected income, profit, or return is claimed for any period.",
            "AAPL is present on disk as a Stage 1 split fixture, is not a member of the frozen "
            "universe, and is excluded from every candidate.",
            "live_trading_authorized remains false.",
        ],
        "authorized_windows": ["development"],
        "validation_window_state": "LOCKED",
        "holdout_window_state": "SEALED",
        "live_trading_authorized": False,
    }
    RECORD_JSON.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # Written last so it covers the final bytes of the JSON above. It does not contain its own
    # digest; nothing hashes itself.
    covered = dict(digests)
    covered["governance/STAGE_3_PREREGISTRATION.json"] = sha256_file(RECORD_JSON)
    own_digest = write_sha256_record(covered, RECORD_SHA)

    code_hashes, repo_state_id = repo_state()
    RunRecord(
        run_id=run_id,
        stage="STAGE_3_PRE_REGISTRATION",
        command="python -m stockedge100.reporting.stage3_preregistration",
        timestamp_utc=timestamp,
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=digests["config/stage3_strategy_protocol.json"],
        dataset_hashes={},
        universe_version="SE100-CFG-1002@1.0.0",
        date_range=None,
        holdout_state="SEALED",
        strategy_id=None,
        random_seed=None,
        dependency_versions=dependency_versions(TRACKED_DEPENDENCIES),
        exit_status="OK",
        output_artifact_hashes={
            "governance/STAGE_3_PREREGISTRATION.json": covered["governance/STAGE_3_PREREGISTRATION.json"],
            "governance/STAGE_3_PREREGISTRATION.sha256": own_digest,
        },
        notes=[
            "Six strategy specifications and the gate 3 evaluation methods sealed before any strategy "
            "code existed.",
            "src/stockedge100/strategies/ contained no Python module at seal time; reports/stage3/ "
            "did not exist.",
            "strategy_id is null because no candidate has been run. The field is populated by the "
            "evidence and decision runs that follow.",
            "No credential access. No order. No backtest run. No strategy result of any kind.",
        ],
    ).write(RUNS_DIR)

    print(f"run_id           {run_id}")
    print(f"declared_utc     {timestamp}")
    print(f"repo_state_id    {repo_state_id}")
    for name, digest in digests.items():
        print(f"  {digest}  {name}")
    print("sealed           governance/STAGE_3_PREREGISTRATION.json / .sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
