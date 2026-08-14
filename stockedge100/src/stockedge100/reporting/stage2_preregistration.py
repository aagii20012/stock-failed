"""Seal the Stage 2 pre-registration.

Run from ``stockedge100/``, **before** any backtest engine code is written::

    PYTHONPATH=src python -m stockedge100.reporting.stage2_preregistration

Writes:

* ``governance/STAGE_2_PREREGISTRATION.json``   — authoritative declaration timestamp and the digest
  of every pre-registered file
* ``governance/STAGE_2_PREREGISTRATION.sha256`` — checksum record over those files
* one reproducibility record under ``runs/``

As with Stage 1, the JSON carries **no** ``repo_state_id``: it lives in ``governance/`` and is one of
the inputs to that digest, so any value written here would be stale on write. The binding value is in
the ``runs/`` record.

Refuses to run if a record already exists, or if any file exists under ``src/stockedge100/backtest/``
or any Stage 2 engine output exists under ``reports/stage2/``. A cost model sealed after the engine
could produce a number is a cost model that may have been chosen because of that number.
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
    "config/stage2_cost_model.json",
    "config/stage2_engine_spec.json",
    "governance/STAGE_2_PREREGISTRATION.md",
)

RECORD_JSON = PROJECT_ROOT / "governance" / "STAGE_2_PREREGISTRATION.json"
RECORD_SHA = PROJECT_ROOT / "governance" / "STAGE_2_PREREGISTRATION.sha256"

ENGINE_DIR = PROJECT_ROOT / "src" / "stockedge100" / "backtest"
STAGE_2_REPORTS_DIR = PROJECT_ROOT / "reports" / "stage2"

STAGE_1_FREEZE = PROJECT_ROOT / "governance" / "STAGE_1_FREEZE.sha256"


def _engine_files() -> list[Path]:
    if not ENGINE_DIR.is_dir():
        return []
    return [p for p in ENGINE_DIR.rglob("*") if p.is_file() and p.suffix == ".py"]


def _engine_output_files() -> list[Path]:
    if not STAGE_2_REPORTS_DIR.is_dir():
        return []
    return [p for p in STAGE_2_REPORTS_DIR.rglob("*") if p.is_file()]


def build() -> int:
    if RECORD_JSON.exists() or RECORD_SHA.exists():
        print("REFUSED: a Stage 2 pre-registration record already exists.", file=sys.stderr)
        print("A pre-registration is sealed once. Regenerating it would destroy its meaning.", file=sys.stderr)
        return 2

    engine = _engine_files()
    if engine:
        print(f"REFUSED: {len(engine)} engine module(s) already exist under src/stockedge100/backtest/.", file=sys.stderr)
        print("The cost model and acceptance spec must be sealed before any engine code exists.", file=sys.stderr)
        return 3

    output = _engine_output_files()
    if output:
        print(f"REFUSED: {len(output)} Stage 2 output file(s) already exist under reports/stage2/.", file=sys.stderr)
        print("No engine output may exist when the acceptance criteria are sealed.", file=sys.stderr)
        return 3

    freeze_ok, freeze_detail = verify_stage0_freeze()
    if not freeze_ok:
        print("REFUSED: the Stage 0 freeze does not verify. Stop and investigate.", file=sys.stderr)
        return 4

    # Freeze records store bare filenames, so they verify from the directory that holds them.
    # Passing PROJECT_ROOT here would report MISSING for every entry — an operator error dressed up
    # as an integrity failure.
    stage1_freeze = verify_sha256_record(STAGE_1_FREEZE, root=STAGE_1_FREEZE.parent)
    bad = sorted(name for name, result in stage1_freeze.items() if result != "OK")
    if bad:
        print(f"REFUSED: the Stage 1 freeze does not verify: {bad}", file=sys.stderr)
        return 4

    missing = [name for name in PREREGISTERED if not (PROJECT_ROOT / name).is_file()]
    if missing:
        print(f"REFUSED: pre-registered file(s) missing: {missing}", file=sys.stderr)
        return 5

    timestamp = utc_now_iso()
    run_id = new_run_id(timestamp)
    digests = {name: sha256_file(PROJECT_ROOT / name) for name in PREREGISTERED}

    record = {
        "document_id": "SE100-GOV-0005",
        "project": "StockEdge100",
        "generation": 1,
        "stage": 2,
        "record_type": "PRE_REGISTRATION",
        "status": "SEALED",
        "declared_utc": timestamp,
        "run_id": run_id,
        "constitution_ref": "SE100-GOV-0001",
        "gate": {
            "constitutional_gate": 2,
            "name": "Backtest engine validity",
            "pass_conditions": [
                "deterministic reruns produce identical trades and equity curves",
                "tests detect look-ahead, same-close fill, split/dividend, delisting, stale-price, "
                "cash, rounding, fee, slippage, rejected-order, and duplicate-order errors",
                "independent hand-calculated fixtures match engine output",
                "benchmark calculations reconcile",
            ],
            "fail_result": "BACKTEST_ENGINE_NOT_VALIDATED",
        },
        "stage_0_freeze_verified": True,
        "stage_0_freeze_verification": freeze_detail,
        "stage_1_freeze_verified": True,
        "stage_1_freeze_files": sorted(stage1_freeze),
        "sealed_before_any_engine_code": True,
        "engine_modules_present_at_seal_time": 0,
        "engine_output_files_present_at_seal_time": 0,
        "preregistered_files": {name: {"sha256": digest} for name, digest in digests.items()},
        "checksum_record": {
            "path": "governance/STAGE_2_PREREGISTRATION.sha256",
            "path_convention": "project-root-relative",
            "verify_from": "stockedge100/",
            "command": "cd stockedge100 && sha256sum -c governance/STAGE_2_PREREGISTRATION.sha256",
        },
        "repo_state_id_location": (
            "Deliberately omitted here. This file lives in governance/ and is one of the inputs to "
            "repo_state_id, so any value written into it would be stale on write. The binding value "
            f"is the repo_state_id field of runs/{run_id}.json."
        ),
        "binding_consequences": [
            "Every cost, fee, spread, slippage, rounding direction, and corporate-action convention "
            "the engine applies is fixed as of this timestamp and may not be revised because of a "
            "result it produced.",
            "The hand-calculated fixture values in config/stage2_engine_spec.json are the reference. "
            "If engine output disagrees, the discrepancy is reported; the sealed value is not edited "
            "to match the engine.",
            "Each of the twelve declared defect classes requires an injected-defect test that proves "
            "its detector fires.",
            "Stage 2 reads development-window data only. Validation stays LOCKED and holdout stays "
            "SEALED.",
            "No probe in Stage 2 is a strategy: no signal, no parameter, no fitting, no selection, "
            "and no performance claim.",
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
    covered["governance/STAGE_2_PREREGISTRATION.json"] = sha256_file(RECORD_JSON)
    own_digest = write_sha256_record(covered, RECORD_SHA)

    code_hashes, repo_state_id = repo_state()
    RunRecord(
        run_id=run_id,
        stage="STAGE_2_PRE_REGISTRATION",
        command="python -m stockedge100.reporting.stage2_preregistration",
        timestamp_utc=timestamp,
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=digests["config/stage2_cost_model.json"],
        dataset_hashes={},
        universe_version="SE100-CFG-1002@1.0.0",
        date_range=None,
        holdout_state="SEALED",
        random_seed=None,
        dependency_versions=dependency_versions(TRACKED_DEPENDENCIES),
        exit_status="OK",
        output_artifact_hashes={
            "governance/STAGE_2_PREREGISTRATION.json": covered["governance/STAGE_2_PREREGISTRATION.json"],
            "governance/STAGE_2_PREREGISTRATION.sha256": own_digest,
        },
        notes=[
            "Cost model and engine acceptance criteria sealed before any backtest engine code existed.",
            "src/stockedge100/backtest/ contained no Python module at seal time; reports/stage2/ did not exist.",
            "No credential access. No order. No strategy computation. No backtest run.",
        ],
    ).write(RUNS_DIR)

    print(f"run_id           {run_id}")
    print(f"declared_utc     {timestamp}")
    print(f"repo_state_id    {repo_state_id}")
    for name, digest in digests.items():
        print(f"  {digest}  {name}")
    print("sealed           governance/STAGE_2_PREREGISTRATION.json / .sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
