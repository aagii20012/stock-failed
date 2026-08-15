"""Dry-run the Generation 2 Stage 3 pre-registration sealer. ASCII output only.

The real sealer refuses to run twice, and a pre-registration that is regenerated after a defect is
found is no longer a pre-registration. So every write target is redirected into _scratch/ here and
the real build() is called, leaving the governed tree untouched.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent / "g2_rotation_preregistration_dryrun_out"
ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.reporting import g2_rotation_preregistration as mod  # noqa: E402


def main() -> int:
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    (SCRATCH / "runs").mkdir(parents=True)

    print("=== contamination ===")
    contamination = mod.measure_contamination()
    for key in (
        "strategies_count",
        "backtest_count",
        "elsewhere_in_src_count",
        "tests_count",
        "reporting_count",
    ):
        print(f"  {key:<26} {contamination[key]}")
    print(f"  reporting                  {contamination['reporting']}")
    print(f"  generation_2 reports       {contamination['generation_2_report_artifacts']}")
    print(f"  foreign runs               "
          f"{contamination['generation_2_run_records_other_than_the_partition_lock']}")
    problems = mod.contamination_problems(contamination)
    print("  problems:", problems or "none")
    print()

    print("=== measured span ===")
    span = mod.measure_span()
    for key in (
        "run_start",
        "run_start_weekday",
        "run_start_lookback_reference",
        "session_before_run_start",
        "session_before_run_start_lookback_reference",
        "run_end",
        "run_sessions",
        "exchange_calendar_sessions",
        "session_lists_agree",
        "binding_symbol",
        "binding_symbols",
        "binding_symbol_inception",
        "earliest_inception",
        "earliest_inception_symbols",
        "members_missing_a_bar_at_run_start",
        "symbols_ending_before_run_end",
        "development_union_sessions",
        "development_union_span",
        "monthly_rebalance_sessions",
        "quarterly_rebalance_sessions",
        "monthly_first_three",
        "monthly_last_two",
        "quarterly_first_three",
        "quarterly_last_two",
    ):
        print(f"  {key:<45} {span[key]}")
    print()

    print("=== recomputed grid ===")
    for row in mod.enumerate_grid():
        print(f"  {row['index']:>2}  {row['variant_id']:<44} "
              f"w={row['target_weight_per_position']}  gross={row['target_gross_exposure']}")
    print()

    print("=== config agreement ===")
    protocol = json.loads(mod.PROTOCOL_CONFIG.read_text(encoding="utf-8"))
    criteria = json.loads(mod.CRITERIA_CONFIG.read_text(encoding="utf-8"))
    problems = mod.check_config_agreement(protocol, span) + mod.check_criteria_agreement(criteria)
    if problems:
        for problem in problems:
            print("  -", problem.encode("ascii", "replace").decode("ascii"))
    else:
        print("  clean")
    print()

    print("=== document agreement ===")
    problems = mod.check_document_agreement(
        mod.RECORD_MD.read_text(encoding="utf-8"), span, contamination
    )
    if problems:
        for problem in problems:
            print("  -", problem.encode("ascii", "replace").decode("ascii"))
    else:
        print("  clean")
    print()

    print("=== freeze records ===")
    ok, _ = mod.verify_stage0_freeze()
    print("  stage 0 freeze verifies:", ok)
    print("  stage 1 freeze:", mod.verify_sha256_record(
        mod.PROJECT_ROOT / "governance" / "STAGE_1_FREEZE.sha256",
        root=mod.PROJECT_ROOT / "governance",
    ))
    print("  g2 partition lock:", mod.verify_sha256_record(
        mod.PARTITION_LOCK_SHA, root=mod.PROJECT_ROOT
    ))
    print()

    # Redirect every write target, then run the real build.
    mod.RECORD_JSON = SCRATCH / "STAGE_3_G2_ROTATION_PROTOCOL.json"
    mod.RECORD_SHA = SCRATCH / "STAGE_3_G2_ROTATION_PROTOCOL.sha256"
    mod.RUNS_DIR = SCRATCH / "runs"
    code = mod.build()
    print()
    print("build() exit code:", code)
    if code != 0:
        return code

    record = json.loads(mod.RECORD_JSON.read_text(encoding="utf-8"))
    print()
    print("top-level keys:", list(record.keys()))
    print("grid keys      :", list(record["grid"].keys()))
    print("variants       :", len(record["grid"]["variants"]))
    print("sealed_inputs  :", len(record["sealed_inputs"]))
    print()
    print("--- sha256 record ---")
    print(mod.RECORD_SHA.read_text(encoding="utf-8"), end="")
    runs = sorted((SCRATCH / "runs").glob("*.json"))
    print("--- run record ---", runs[0].name)
    run = json.loads(runs[0].read_text(encoding="utf-8"))
    for key in ("stage", "repo_state_id", "config_hash", "strategy_id", "date_range",
                "holdout_state", "universe_version", "exit_status"):
        print(f"  {key:<18} {run[key]}")
    print(f"  dataset_hashes     {len(run['dataset_hashes'])} entries")
    print(f"  code_hashes        {len(run['code_hashes'])} entries")
    for note in run["notes"]:
        print("  note:", note.encode("ascii", "replace").decode("ascii"))

    # The governance JSON must carry no tree digest and no digest of itself.
    text = mod.RECORD_JSON.read_text(encoding="utf-8")
    print()
    print("repo_state_id value present in the JSON:", run["repo_state_id"] in text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
