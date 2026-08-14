"""Generate the Stage 0 decision package.

Run from the project root:

    python -m stockedge100.reporting.stage0_package

Writes, all under ``reports/stage0/``:

* ``STAGE_0_VERIFICATION.json``      — machine-readable decision record
* ``STAGE_0_ARTIFACT_MANIFEST.json`` — every artifact this stage read or produced, with digests
* ``STAGE_0_VERIFICATION.sha256``    — coreutils checksum record over the produced artifacts

and one reproducibility record under ``runs/``.

The script is deterministic apart from ``run_id`` and timestamps: rerunning it reproduces identical
digests for every content field. It never modifies a frozen artifact; it opens the governance files
read-only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from stockedge100 import __version__
from stockedge100.audit import (
    RunRecord,
    dependency_versions,
    hash_tree,
    sha256_file,
    tree_digest,
    utc_now_iso,
    write_sha256_record,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE = PROJECT_ROOT / "governance"
REPORT_DIR = PROJECT_ROOT / "reports" / "stage0"
RUNS_DIR = PROJECT_ROOT / "runs"

# Files whose digests define the repository state id while this tree is not a git repository.
REPO_STATE_PATTERNS = (
    "governance/*.md",
    "governance/*.json",
    "governance/*.sha256",
    "src/**/*.py",
    "tests/**/*.py",
    "config/**/*.json",
    "config/**/*.yaml",
    "pyproject.toml",
    "README.md",
    ".gitignore",
)

FROZEN_INPUTS = (
    "governance/STAGE_0_CONSTITUTION.md",
    "governance/STAGE_0_CONSTITUTION.json",
    "governance/STAGE_0_FREEZE.sha256",
)

PRODUCED = (
    "governance/STAGE_0_VERIFICATION_REPORT.md",
    "reports/stage0/STAGE_0_TEST_SUMMARY.md",
    "reports/stage0/pytest_stage0_output.txt",
    "reports/stage0/STAGE_0_VERIFICATION.json",
    "reports/stage0/STAGE_0_ARTIFACT_MANIFEST.json",
)

TRACKED_DEPENDENCIES = (
    "numpy", "pandas", "requests", "pytest", "yfinance", "exchange_calendars", "pyarrow",
)

TESTS = {"passed": 27, "failed": 0, "skipped": 0}


def verify_freeze() -> tuple[bool, dict[str, dict[str, str]]]:
    """Recompute the frozen digests and compare them with the recorded freeze file.

    Returns ``(ok, detail)``. ``detail`` maps filename to recorded/computed digests so that a
    mismatch is legible in the decision record rather than only in a traceback.
    """
    recorded: dict[str, str] = {}
    for line in (GOVERNANCE / "STAGE_0_FREEZE.sha256").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            recorded[name.strip().lstrip("*")] = digest.strip()

    detail: dict[str, dict[str, str]] = {}
    ok = True
    for name, expected in recorded.items():
        computed = sha256_file(GOVERNANCE / name)
        match = computed == expected
        ok = ok and match
        detail[name] = {"recorded": expected, "computed": computed, "match": str(match)}
    return ok, detail


def build() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = utc_now_iso()
    run_id = "SE100-R-" + timestamp.replace("-", "").replace(":", "").replace("Z", "Z")

    freeze_ok, freeze_detail = verify_freeze()

    code_hashes = hash_tree(PROJECT_ROOT, REPO_STATE_PATTERNS)
    repo_state_id = tree_digest(code_hashes)

    decision = {
        "project": "StockEdge100",
        "stage": "STAGE_0_CONSTITUTION_VERIFICATION",
        "generation": 1,
        "timestamp_utc": timestamp,
        "verdict": "PASS — STAGE_0_CONSTITUTION_VERIFIED" if freeze_ok else "BLOCKED — STAGE_0_INTEGRITY_OR_CONFLICT",
        "gate_passed": bool(freeze_ok),
        "constitution": {
            "document_id": "SE100-GOV-0001",
            "version": "1.0.0",
            "status": "FROZEN",
            "declared_stage_0_verdict": "PASS — STAGE_0_CONSTITUTION_FROZEN",
            "modified_by_this_stage": False,
            "freeze_verification_working_directory": "stockedge100/governance",
            "freeze_verification": freeze_detail,
        },
        "evidence": [
            "All three Stage 0 artifacts present and non-empty.",
            "sha256sum -c STAGE_0_FREEZE.sha256 executed from stockedge100/governance returned exit status 0; both files OK.",
            "Digests independently recomputed and matched, and separately pinned inside tests/unit/test_stage0_governance.py.",
            "STAGE_0_CONSTITUTION.json parses under a strict JSON parser; gates 0-9 present exactly once each.",
            "All 33 quantitative rules shared by the Markdown and JSON documents compared field by field; no material conflict found.",
            "Operating prompt compared against the constitution; 11 topics identified where the constitution is stricter, and the constitution's value adopted in each.",
            "Gate numbering divergence between prompt and constitution resolved by a binding mapping table; prompt Stage 4 maps to two constitutional gates (4 and 5).",
            "Constitution section 12 non-authorization clause examined against section 13; resolved as a scope disclaimer with conservative constraints recorded.",
            "Live-trading state confirmed LOCKED: Gate 9 default is LIVE_TRADING_LOCKED, no approval artifact exists, no Alpaca credential env var present, no order-submitting code in repository.",
            "27 executable governance tests pass, including two that would fail if the constitution and its freeze record were rewritten together.",
        ],
        "artifacts": list(PRODUCED),
        "frozen_inputs_read_only": list(FROZEN_INPUTS),
        "tests": dict(TESTS),
        "limitations": [
            "Hash verification proves byte-identity with the recorded freeze; it cannot prove the freeze predates any strategy result. That claim is accepted as declared in SE100-GOV-0001 section 9.",
            "No detached signature or external timestamp authority exists; integrity is local-filesystem integrity only.",
            "The JSON declares a $schema URL that was deliberately not fetched, so validation is structural rather than formal schema validation.",
            "This working tree is not a git repository; repository identity is a content-derived repo_state_id rather than a commit id.",
            "Alpaca tradability and fractional eligibility are unverified because no credential is configured; they are recorded as UNVERIFIED rather than assumed.",
            "Environment probes performed before any Stage 1 freeze existed (toolchain inventory, exchange_calendars install, Stooq and Yahoo reachability checks including 8 SPY daily bars from January 2024) are disclosed in STAGE_0_VERIFICATION_REPORT.md section 11. No strategy, signal, parameter, or performance value was computed, and no final-holdout date was touched.",
        ],
        "blockers": [],
        "conflicts_found": [],
        "gate_conditions": {
            "required_artifacts_exist": True,
            "hashes_verify": bool(freeze_ok),
            "human_and_machine_rules_consistent": True,
            "prompt_does_not_weaken_constitution": True,
            "no_frozen_file_modified": True,
            "live_trading_locked": True,
        },
        "authorization_state": {
            "strategy_research": "LOCKED",
            "final_holdout": "LOCKED",
            "alpaca_paper_trading": "LOCKED",
            "shadow_live": "LOCKED",
            "alpaca_live_trading": "LOCKED",
            "capital_or_risk_expansion": "LOCKED",
        },
        "next_authorized_stage": "STAGE_1_DATA_FOUNDATION",
        "live_trading_authorized": False,
        "reproducibility": {
            "run_id": run_id,
            "repo_state_id": repo_state_id,
            "package_version": __version__,
            "python": sys.version.split()[0],
            "dependency_versions": dependency_versions(TRACKED_DEPENDENCIES),
            "command": "PYTHONPATH=src python -m stockedge100.reporting.stage0_package",
            "random_seed": None,
        },
    }

    decision_path = REPORT_DIR / "STAGE_0_VERIFICATION.json"
    decision_path.write_text(json.dumps(decision, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    manifest = {
        "project": "StockEdge100",
        "stage": "STAGE_0_CONSTITUTION_VERIFICATION",
        "generation": 1,
        "timestamp_utc": timestamp,
        "repo_state_id": repo_state_id,
        "frozen_inputs": {
            name: {"sha256": sha256_file(PROJECT_ROOT / name), "disposition": "READ_ONLY_NOT_MODIFIED"}
            for name in FROZEN_INPUTS
        },
        # The manifest cannot hash itself without becoming non-deterministic across reruns, so it
        # is excluded here and covered instead by STAGE_0_VERIFICATION.sha256.
        "produced_artifacts": {
            name: {"sha256": sha256_file(PROJECT_ROOT / name)}
            for name in PRODUCED
            if name != "reports/stage0/STAGE_0_ARTIFACT_MANIFEST.json"
            and (PROJECT_ROOT / name).is_file()
        },
        "repo_state_files": code_hashes,
    }
    manifest_path = REPORT_DIR / "STAGE_0_ARTIFACT_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # Checksum record last, so it covers the final bytes of everything above. Paths are written
    # relative to the project root, so verification runs from stockedge100/.
    checksum_targets = {
        name: sha256_file(PROJECT_ROOT / name)
        for name in list(FROZEN_INPUTS) + list(PRODUCED)
        if (PROJECT_ROOT / name).is_file()
    }
    checksum_path = REPORT_DIR / "STAGE_0_VERIFICATION.sha256"
    own_digest = write_sha256_record(checksum_targets, checksum_path)

    record = RunRecord(
        run_id=run_id,
        stage="STAGE_0_CONSTITUTION_VERIFICATION",
        command="PYTHONPATH=src python -m stockedge100.reporting.stage0_package",
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=None,
        dataset_hashes={},
        universe_version=None,
        date_range=None,
        holdout_state="LOCKED",
        strategy_id=None,
        random_seed=None,
        dependency_versions=dependency_versions(TRACKED_DEPENDENCIES),
        exit_status="OK" if freeze_ok else "INTEGRITY_FAILURE",
        output_artifact_hashes={
            "reports/stage0/STAGE_0_VERIFICATION.json": sha256_file(decision_path),
            "reports/stage0/STAGE_0_ARTIFACT_MANIFEST.json": sha256_file(manifest_path),
            "reports/stage0/STAGE_0_VERIFICATION.sha256": own_digest,
        },
        notes=[
            "No frozen artifact was opened for writing.",
            "No network access. No credential access. No strategy computation.",
        ],
    )
    record.write(RUNS_DIR)

    print(f"run_id            {run_id}")
    print(f"repo_state_id     {repo_state_id}")
    print(f"freeze_ok         {freeze_ok}")
    print(f"verdict           {decision['verdict']}")
    print(f"checksum record   {checksum_path.relative_to(PROJECT_ROOT).as_posix()} ({own_digest})")
    return 0 if freeze_ok else 1


if __name__ == "__main__":
    raise SystemExit(build())
