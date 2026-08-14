"""Seal the Stage 1 pre-registration.

Run from ``stockedge100/``, **before** any market data is acquired::

    python -m stockedge100.reporting.stage1_preregistration

Writes:

* ``governance/STAGE_1_PREREGISTRATION.json``   — authoritative declaration timestamp and the digest
  of every pre-registered file
* ``governance/STAGE_1_PREREGISTRATION.sha256`` — checksum record over those files
* one reproducibility record under ``runs/``

The JSON deliberately carries **no** ``repo_state_id``: it lives in ``governance/`` and is therefore
one of the inputs to that digest, so any value written here would be stale the instant it was
written. The binding value is in the ``runs/`` record.

Refuses to run a second time. A pre-registration that can be regenerated after the data is visible
would prove nothing at all, which is the entire reason this file exists.
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
    verify_stage0_freeze,
)

PREREGISTERED = (
    "config/stage1_data_source.json",
    "config/stage1_universe_spec.json",
    "governance/STAGE_1_PREREGISTRATION.md",
)

RECORD_JSON = PROJECT_ROOT / "governance" / "STAGE_1_PREREGISTRATION.json"
RECORD_SHA = PROJECT_ROOT / "governance" / "STAGE_1_PREREGISTRATION.sha256"

RAW_DIR = PROJECT_ROOT / "data" / "raw"


def _acquired_files() -> list[Path]:
    return [p for p in RAW_DIR.rglob("*") if p.is_file() and p.suffix.lower() == ".csv"]


def build() -> int:
    if RECORD_JSON.exists() or RECORD_SHA.exists():
        print("REFUSED: a Stage 1 pre-registration record already exists.", file=sys.stderr)
        print("A pre-registration is sealed once. Regenerating it would destroy its meaning.", file=sys.stderr)
        return 2

    already = _acquired_files()
    if already:
        print(f"REFUSED: {len(already)} raw data file(s) already exist under data/raw/.", file=sys.stderr)
        print("The pre-registration must be sealed before any data is acquired.", file=sys.stderr)
        return 3

    freeze_ok, freeze_detail = verify_stage0_freeze()
    if not freeze_ok:
        print("REFUSED: the Stage 0 freeze does not verify. Stop and investigate.", file=sys.stderr)
        return 4

    missing = [name for name in PREREGISTERED if not (PROJECT_ROOT / name).is_file()]
    if missing:
        print(f"REFUSED: pre-registered file(s) missing: {missing}", file=sys.stderr)
        return 5

    timestamp = utc_now_iso()
    run_id = new_run_id(timestamp)
    digests = {name: sha256_file(PROJECT_ROOT / name) for name in PREREGISTERED}

    record = {
        "document_id": "SE100-GOV-0003",
        "project": "StockEdge100",
        "generation": 1,
        "stage": 1,
        "record_type": "PRE_REGISTRATION",
        "status": "SEALED",
        "declared_utc": timestamp,
        "run_id": run_id,
        "constitution_ref": "SE100-GOV-0001",
        "stage_0_freeze_verified": True,
        "stage_0_freeze_verification": freeze_detail,
        "sealed_before_any_data_acquired": True,
        "raw_data_files_present_at_seal_time": 0,
        "preregistered_files": {name: {"sha256": digest} for name, digest in digests.items()},
        "checksum_record": {
            "path": "governance/STAGE_1_PREREGISTRATION.sha256",
            "path_convention": "project-root-relative",
            "verify_from": "stockedge100/",
            "command": "cd stockedge100 && sha256sum -c governance/STAGE_1_PREREGISTRATION.sha256",
        },
        "repo_state_id_location": (
            "Deliberately omitted here. This file lives in governance/ and is one of the inputs to "
            "repo_state_id, so any value written into it would be stale on write. The binding value "
            f"is the repo_state_id field of runs/{run_id}.json."
        ),
        "binding_consequences": [
            "The provider, acquisition protocol, normalization spec, validation battery, universe "
            "candidate list, and eligibility rules are fixed as of this timestamp.",
            "No symbol may be added to or removed from the candidate list by judgement after data "
            "is visible; eligibility is applied mechanically.",
            "No eligibility or quality measurement may read validation-window or holdout-window data.",
            "live_trading_authorized remains false.",
        ],
        "live_trading_authorized": False,
    }
    RECORD_JSON.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # Written last so it covers the final bytes of the JSON above. It does not contain its own
    # digest; nothing hashes itself.
    covered = dict(digests)
    covered["governance/STAGE_1_PREREGISTRATION.json"] = sha256_file(RECORD_JSON)
    own_digest = write_sha256_record(covered, RECORD_SHA)

    code_hashes, repo_state_id = repo_state()
    RunRecord(
        run_id=run_id,
        stage="STAGE_1_PRE_REGISTRATION",
        command="python -m stockedge100.reporting.stage1_preregistration",
        timestamp_utc=timestamp,
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=digests["config/stage1_data_source.json"],
        dataset_hashes={},
        universe_version="SE100-CFG-1002@1.0.0",
        date_range=None,
        holdout_state="NOT_YET_COMPUTED",
        random_seed=None,
        dependency_versions=dependency_versions(TRACKED_DEPENDENCIES),
        exit_status="OK",
        output_artifact_hashes={
            "governance/STAGE_1_PREREGISTRATION.json": covered["governance/STAGE_1_PREREGISTRATION.json"],
            "governance/STAGE_1_PREREGISTRATION.sha256": own_digest,
        },
        notes=[
            "Pre-registration sealed before any market data was acquired.",
            "No credential access. No order. No strategy computation.",
        ],
    ).write(RUNS_DIR)

    print(f"run_id           {run_id}")
    print(f"declared_utc     {timestamp}")
    print(f"repo_state_id    {repo_state_id}")
    for name, digest in digests.items():
        print(f"  {digest}  {name}")
    print(f"sealed           governance/STAGE_1_PREREGISTRATION.json / .sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
