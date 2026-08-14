"""Audit primitives shared by every stage: content hashing, manifests, and run records.

Design rules enforced here:

* Hashing is byte-exact and never normalises line endings. A file that changes by one byte changes
  its digest.
* Nothing in this module writes to, renames, or deletes an existing file. Callers do that.
* Timestamps are UTC and ISO-8601 with an explicit ``Z``.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

CHUNK = 1 << 20


def utc_now_iso() -> str:
    """Current UTC time as ISO-8601 with a trailing ``Z`` and second resolution."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    """SHA-256 of a file read in binary mode."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(CHUNK)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def sha256_text_canonical_json(obj: Any) -> str:
    """SHA-256 of an object serialised as canonical JSON.

    Canonical means sorted keys, compact separators, and UTF-8. Two logically identical objects
    hash identically regardless of how they were constructed, which is what configuration hashing
    requires.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(payload.encode("utf-8"))


def iter_files(root: str | os.PathLike[str], patterns: Sequence[str]) -> list[Path]:
    """Deterministically ordered file list for the given glob patterns under ``root``."""
    base = Path(root)
    found: set[Path] = set()
    for pattern in patterns:
        for path in base.glob(pattern):
            if path.is_file():
                found.add(path)
    return sorted(found, key=lambda p: p.relative_to(base).as_posix())


def hash_tree(root: str | os.PathLike[str], patterns: Sequence[str]) -> dict[str, str]:
    """Map of ``relative/posix/path -> sha256`` for every matching file, in sorted order."""
    base = Path(root)
    return {
        path.relative_to(base).as_posix(): sha256_file(path)
        for path in iter_files(base, patterns)
    }


def tree_digest(file_hashes: dict[str, str]) -> str:
    """A single digest summarising a whole set of files.

    This is the project's substitute for a git commit id while the working tree is not a git
    repository. It is order independent because ``hash_tree`` returns sorted keys.
    """
    return sha256_text_canonical_json(file_hashes)


def write_sha256_record(
    lines: dict[str, str],
    out_path: str | os.PathLike[str],
) -> str:
    """Write a coreutils-compatible ``sha256sum`` record and return its own digest.

    ``lines`` maps a path *as it should appear in the record* to a digest. The record is written
    with LF endings and a trailing newline so that ``sha256sum -c`` accepts it on any platform.
    """
    body = "".join(f"{digest}  {name}\n" for name, digest in sorted(lines.items()))
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body.encode("utf-8"))
    return sha256_bytes(body.encode("utf-8"))


def dependency_versions(modules: Iterable[str]) -> dict[str, str]:
    """Installed version for each named module, or ``"MISSING"``.

    Recorded in every run record so a rerun that produces different numbers can be attributed.
    """
    import importlib

    versions: dict[str, str] = {}
    for name in modules:
        try:
            module = importlib.import_module(name)
        except Exception:
            versions[name] = "MISSING"
        else:
            versions[name] = str(getattr(module, "__version__", "UNKNOWN"))
    return versions


@dataclass
class RunRecord:
    """Reproducibility record required by every material run.

    Fields left at their defaults must be filled by the caller before the record is written; a
    reviewer should be able to reconstruct the run from this object alone.
    """

    run_id: str
    stage: str
    command: str
    timestamp_utc: str = field(default_factory=utc_now_iso)
    repo_state_id: str | None = None
    code_hashes: dict[str, str] = field(default_factory=dict)
    config_hash: str | None = None
    dataset_hashes: dict[str, str] = field(default_factory=dict)
    universe_version: str | None = None
    date_range: list[str] | None = None
    holdout_state: str = "LOCKED"
    strategy_id: str | None = None
    random_seed: int | None = None
    dependency_versions: dict[str, str] = field(default_factory=dict)
    python_version: str = field(default_factory=lambda: sys.version.split()[0])
    platform: str = field(default_factory=platform.platform)
    exit_status: str | None = None
    output_artifact_hashes: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    def write(self, runs_dir: str | os.PathLike[str]) -> Path:
        target = Path(runs_dir) / f"{self.run_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return target
