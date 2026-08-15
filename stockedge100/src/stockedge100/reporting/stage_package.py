"""Shared machinery for building a stage decision package.

Every governance stage produces the same six things: a Markdown report, a JSON decision record, a
``.sha256`` record, a test summary, an artifact manifest, and an append-only ``runs/`` record. The
parts that are identical across stages live here:

* locating the project root;
* verifying the Stage 0 freeze (every stage re-verifies it and stops if it fails);
* computing ``repo_state_id`` from :func:`hash_tree` / :func:`tree_digest`;
* the decision-JSON skeleton, the artifact manifest, the checksum record, and the ``RunRecord``.

A stage module supplies only what is genuinely its own: evidence, limitations, gate conditions, and
whatever stage-specific body belongs in the decision record.

``stage0_package.py`` is deliberately **not** refactored onto this module. Its artifacts are already
hashed and recorded; rewriting the generator would change bytes that other records attest to.

Nothing here writes to a frozen artifact. The governance files are opened read-only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
RUNS_DIR = PROJECT_ROOT / "runs"

# Files whose digests define the repository state id while this tree is not a git repository.
# Kept byte-identical to the Stage 0 definition on purpose: if the set of tracked patterns changed
# between stages, two repo_state_id values could not be compared with each other.
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

STAGE_0_FROZEN_INPUTS = (
    "governance/STAGE_0_CONSTITUTION.md",
    "governance/STAGE_0_CONSTITUTION.json",
    "governance/STAGE_0_FREEZE.sha256",
)

TRACKED_DEPENDENCIES = (
    "numpy", "pandas", "requests", "pytest", "yfinance", "exchange_calendars", "pyarrow", "scipy",
)


def new_run_id(timestamp: str) -> str:
    """``SE100-R-<compact UTC timestamp>``, matching the Stage 0 run-id shape."""
    return "SE100-R-" + timestamp.replace("-", "").replace(":", "")


def verify_stage0_freeze() -> tuple[bool, dict[str, dict[str, str]]]:
    """Recompute the frozen Stage 0 digests and compare them with the recorded freeze file.

    Every stage runs this. A mismatch means a frozen artifact was altered, which is a blocker for
    any stage, not just Stage 0. ``detail`` maps filename to recorded/computed digests so the
    failure is legible in the decision record rather than only in a traceback.
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


def repo_state() -> tuple[dict[str, str], str]:
    """``(file_hashes, repo_state_id)`` over :data:`REPO_STATE_PATTERNS`."""
    code_hashes = hash_tree(PROJECT_ROOT, REPO_STATE_PATTERNS)
    return code_hashes, tree_digest(code_hashes)


def verify_sha256_record(record_path: str | Path, root: str | Path = PROJECT_ROOT) -> dict[str, str]:
    """Check every entry of a checksum record, returning ``{path: "OK" | "FAILED" | "MISSING"}``.

    ``root`` is the working directory the record's paths are relative to. Getting that wrong is an
    operator error rather than an integrity failure, which is why it is an explicit argument.
    """
    base = Path(root)
    results: dict[str, str] = {}
    for line in Path(record_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        name = name.strip().lstrip("*")
        target = base / name
        if not target.is_file():
            results[name] = "MISSING"
        else:
            results[name] = "OK" if sha256_file(target) == digest.strip() else "FAILED"
    return results


@dataclass
class StageDecision:
    """Everything a stage must supply for its decision package.

    The fields below are the stage's own judgement. Everything else — hashes, digests, timestamps,
    run ids, manifests — is computed here so that no stage can accidentally hand-type one.
    """

    stage: str                      # e.g. "STAGE_1_DATA_FOUNDATION"
    stage_slug: str                 # e.g. "stage1"
    decision_basename: str          # e.g. "STAGE_1_DATA_READINESS"
    manifest_basename: str          # e.g. "STAGE_1_ARTIFACT_MANIFEST"
    gate_id: int
    gate_name: str
    verdict: str
    gate_passed: bool
    command: str

    # Which research generation this package belongs to. Generation 1 predates the field and every
    # record it wrote carries 1, so 1 is the default and those records stay byte-identical; a
    # Generation 2 stage passes 2 rather than letting its package claim Generation 1's lineage.
    generation: int = 1

    gate_conditions: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    conflicts_found: list[str] = field(default_factory=list)
    produced: list[str] = field(default_factory=list)
    frozen_inputs: list[str] = field(default_factory=lambda: list(STAGE_0_FROZEN_INPUTS))
    body: dict[str, Any] = field(default_factory=dict)
    tests: dict[str, int] = field(default_factory=dict)

    authorization_state: dict[str, str] = field(default_factory=dict)
    next_authorized_stage: str = ""

    dataset_hashes: dict[str, str] = field(default_factory=dict)
    universe_version: str | None = None
    date_range: list[str] | None = None
    holdout_state: str = "LOCKED"
    config_hash: str | None = None
    random_seed: int | None = None
    run_notes: list[str] = field(default_factory=list)


@dataclass
class BuildResult:
    run_id: str
    repo_state_id: str
    timestamp_utc: str
    freeze_ok: bool
    decision_path: Path
    manifest_path: Path
    checksum_path: Path
    checksum_digest: str
    run_record_path: Path


def build_stage_package(decision: StageDecision) -> BuildResult:
    """Write the decision record, artifact manifest, checksum record, and run record.

    Order matters. The checksum record is written last so it covers the final bytes of everything
    above it. The manifest excludes its own entry — a file cannot contain its own digest — and is
    covered by the checksum record instead. Neither file contains a tree digest, because
    ``repo_state_id`` covers ``governance/*.md`` and would be invalidated the moment it were
    written into one of them; it lives in the decision record and the run record only.
    """
    report_dir = PROJECT_ROOT / "reports" / decision.stage_slug
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = utc_now_iso()
    run_id = new_run_id(timestamp)
    freeze_ok, freeze_detail = verify_stage0_freeze()
    code_hashes, repo_state_id = repo_state()

    record: dict[str, Any] = {
        "project": "StockEdge100",
        "stage": decision.stage,
        "generation": decision.generation,
        "timestamp_utc": timestamp,
        "verdict": decision.verdict,
        "gate": {"constitution_gate_id": decision.gate_id, "name": decision.gate_name},
        "gate_passed": bool(decision.gate_passed),
        "constitution": {
            "document_id": "SE100-GOV-0001",
            "version": "1.0.0",
            "status": "FROZEN",
            "modified_by_this_stage": False,
            "freeze_verification_working_directory": "stockedge100/governance",
            "freeze_verified": bool(freeze_ok),
            "freeze_verification": freeze_detail,
        },
        **decision.body,
        "evidence": list(decision.evidence),
        "limitations": list(decision.limitations),
        "blockers": list(decision.blockers),
        "conflicts_found": list(decision.conflicts_found),
        "gate_conditions": dict(decision.gate_conditions),
        "artifacts": list(decision.produced),
        "frozen_inputs_read_only": list(decision.frozen_inputs),
        "tests": dict(decision.tests),
        "authorization_state": dict(decision.authorization_state),
        "next_authorized_stage": decision.next_authorized_stage,
        "live_trading_authorized": False,
        "reproducibility": {
            "run_id": run_id,
            "repo_state_id": repo_state_id,
            "package_version": __version__,
            "python": __import__("sys").version.split()[0],
            "dependency_versions": dependency_versions(TRACKED_DEPENDENCIES),
            "command": decision.command,
            "config_hash": decision.config_hash,
            "random_seed": decision.random_seed,
        },
    }

    decision_path = report_dir / f"{decision.decision_basename}.json"
    decision_path.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    manifest_rel = f"reports/{decision.stage_slug}/{decision.manifest_basename}.json"
    manifest = {
        "project": "StockEdge100",
        "stage": decision.stage,
        "generation": decision.generation,
        "timestamp_utc": timestamp,
        "repo_state_id": repo_state_id,
        "frozen_inputs": {
            name: {"sha256": sha256_file(PROJECT_ROOT / name), "disposition": "READ_ONLY_NOT_MODIFIED"}
            for name in decision.frozen_inputs
            if (PROJECT_ROOT / name).is_file()
        },
        # This manifest cannot hash itself without becoming non-deterministic, so its own entry is
        # excluded here and covered by the checksum record instead.
        "produced_artifacts": {
            name: {"sha256": sha256_file(PROJECT_ROOT / name)}
            for name in decision.produced
            if name != manifest_rel and (PROJECT_ROOT / name).is_file()
        },
        "dataset_hashes": dict(decision.dataset_hashes),
        "repo_state_files": code_hashes,
    }
    manifest_path = report_dir / f"{decision.manifest_basename}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    checksum_targets = {
        name: sha256_file(PROJECT_ROOT / name)
        for name in list(decision.frozen_inputs) + list(decision.produced)
        if (PROJECT_ROOT / name).is_file()
    }
    checksum_path = report_dir / f"{decision.decision_basename}.sha256"
    checksum_digest = write_sha256_record(checksum_targets, checksum_path)

    run_record = RunRecord(
        run_id=run_id,
        stage=decision.stage,
        command=decision.command,
        timestamp_utc=timestamp,
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=decision.config_hash,
        dataset_hashes=dict(decision.dataset_hashes),
        universe_version=decision.universe_version,
        date_range=decision.date_range,
        holdout_state=decision.holdout_state,
        strategy_id=None,
        random_seed=decision.random_seed,
        dependency_versions=dependency_versions(TRACKED_DEPENDENCIES),
        exit_status="OK" if decision.gate_passed else "GATE_NOT_PASSED",
        output_artifact_hashes={
            f"reports/{decision.stage_slug}/{decision.decision_basename}.json": sha256_file(decision_path),
            manifest_rel: sha256_file(manifest_path),
            f"reports/{decision.stage_slug}/{decision.decision_basename}.sha256": checksum_digest,
        },
        notes=list(decision.run_notes),
    )
    run_record_path = run_record.write(RUNS_DIR)

    return BuildResult(
        run_id=run_id,
        repo_state_id=repo_state_id,
        timestamp_utc=timestamp,
        freeze_ok=freeze_ok,
        decision_path=decision_path,
        manifest_path=manifest_path,
        checksum_path=checksum_path,
        checksum_digest=checksum_digest,
        run_record_path=run_record_path,
    )
