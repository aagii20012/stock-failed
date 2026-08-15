"""Dry-run the Generation 2 partition lock sealer. ASCII output only.

The real sealer refuses to run twice, so any defect found after it writes is unrepairable without
destroying the seal. This redirects every output path into _scratch/ and prints what would have been
written, leaving the governed tree untouched.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent / "g2_partition_lock_dryrun_out"
ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.reporting import g2_partition_lock as mod  # noqa: E402


def main() -> int:
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    (SCRATCH / "runs").mkdir(parents=True)

    identity = mod.generation_identity()
    print("generation_id   :", identity["generation_id"])
    print("identity_sha256 :", identity["identity_sha256"])
    print()

    coverage = mod.measure_coverage()
    for key in (
        "member_count",
        "development_sessions",
        "development_first_session",
        "development_last_session",
        "earliest_inception",
        "earliest_inception_symbols",
        "latest_inception",
        "latest_inception_symbols",
        "dataset_last_session",
        "sealed_generation_2_session_count_on_disk",
        "sealed_generation_2_sessions_present_on_disk",
    ):
        print(f"{key:<45} {coverage[key]}")
    print()

    spans = {
        "development_years": mod.span_years(mod.DEVELOPMENT_START, mod.DEVELOPMENT_END),
        "validation_months": mod.span_months(mod.VALIDATION_START, mod.VALIDATION_END),
        "holdout_months": mod.span_months(mod.HOLDOUT_START, mod.HOLDOUT_END),
        "minimum_development_years": 5,
    }
    print("spans:", spans)
    print()

    problems = mod.check_document_agreement(
        mod.RECORD_MD.read_text(encoding="utf-8"), coverage, spans
    )
    if problems:
        print("DOCUMENT AGREEMENT PROBLEMS:")
        for problem in problems:
            print("  -", problem)
    else:
        print("DOCUMENT AGREEMENT: clean")
    print()

    ok, _ = mod.verify_stage0_freeze()
    print("stage 0 freeze verifies:", ok)
    stage1 = mod.verify_sha256_record(
        mod.PROJECT_ROOT / "governance" / "STAGE_1_FREEZE.sha256",
        root=mod.PROJECT_ROOT / "governance",
    )
    print("stage 1 freeze:", stage1)
    print()

    # Redirect every write target, then run the real build.
    mod.RECORD_JSON = SCRATCH / "STAGE_1_G2_PARTITION_LOCK.json"
    mod.RECORD_SHA = SCRATCH / "STAGE_1_G2_PARTITION_LOCK.sha256"
    mod.RUNS_DIR = SCRATCH / "runs"
    code = mod.build()
    print()
    print("build() exit code:", code)
    if code != 0:
        return code

    record = json.loads(mod.RECORD_JSON.read_text(encoding="utf-8"))
    print()
    print("top-level keys:", list(record.keys()))
    print()
    print("--- sha256 record ---")
    print(mod.RECORD_SHA.read_text(encoding="utf-8"), end="")
    runs = sorted((SCRATCH / "runs").glob("*.json"))
    print("--- run record ---", runs[0].name)
    run = json.loads(runs[0].read_text(encoding="utf-8"))
    for key in ("stage", "repo_state_id", "config_hash", "date_range", "holdout_state",
                "universe_version", "exit_status"):
        print(f"  {key:<18} {run[key]}")
    print(f"  dataset_hashes     {len(run['dataset_hashes'])} entries")
    print(f"  code_hashes        {len(run['code_hashes'])} entries")
    for note in run["notes"]:
        print("  note:", note.encode("ascii", "replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
