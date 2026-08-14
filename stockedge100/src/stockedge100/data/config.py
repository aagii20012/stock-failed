"""Load the pre-registered Stage 1 configuration, refusing to proceed if it has been altered.

Every module that acts on the Stage 1 rules loads them through here rather than reading the JSON
directly. The point is the integrity check in :func:`load_stage1_config`: if a configuration file no
longer matches the digest sealed in ``governance/STAGE_1_PREREGISTRATION.json``, the rules were
changed after they were declared, and no downstream result computed from them means anything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_file

PROJECT_ROOT = Path(__file__).resolve().parents[3]

PREREGISTRATION_JSON = PROJECT_ROOT / "governance" / "STAGE_1_PREREGISTRATION.json"
DATA_SOURCE_REL = "config/stage1_data_source.json"
UNIVERSE_SPEC_REL = "config/stage1_universe_spec.json"


class PreRegistrationViolation(RuntimeError):
    """Raised when the sealed Stage 1 rules do not match what is on disk."""


@dataclass(frozen=True)
class Stage1Config:
    data_source: dict[str, Any]
    universe_spec: dict[str, Any]
    preregistration: dict[str, Any]
    digests: dict[str, str]

    @property
    def declared_utc(self) -> str:
        return str(self.preregistration["declared_utc"])

    @property
    def config_hash(self) -> str:
        return self.digests[DATA_SOURCE_REL]

    @property
    def candidates(self) -> list[str]:
        return [entry["symbol"] for entry in self.universe_spec["candidates"]]

    @property
    def reference_symbols(self) -> list[str]:
        return [entry["symbol"] for entry in self.universe_spec["reference_symbols"]["symbols"]]

    @property
    def tolerances(self) -> dict[str, float]:
        return dict(self.data_source["validation_battery"]["tolerances"])


def load_stage1_config(*, require_seal: bool = True) -> Stage1Config:
    """Load the Stage 1 rules and verify them against the sealed pre-registration.

    ``require_seal=False`` exists only for the pre-registration generator itself, which must read
    the files before the seal exists. Nothing else may pass it.
    """
    data_source = json.loads((PROJECT_ROOT / DATA_SOURCE_REL).read_text(encoding="utf-8"))
    universe_spec = json.loads((PROJECT_ROOT / UNIVERSE_SPEC_REL).read_text(encoding="utf-8"))

    if not require_seal:
        return Stage1Config(data_source, universe_spec, {}, {})

    if not PREREGISTRATION_JSON.is_file():
        raise PreRegistrationViolation(
            "governance/STAGE_1_PREREGISTRATION.json is missing. The Stage 1 rules were never "
            "sealed, so nothing downstream of them can be trusted."
        )

    prereg = json.loads(PREREGISTRATION_JSON.read_text(encoding="utf-8"))
    sealed = prereg["preregistered_files"]

    digests: dict[str, str] = {}
    drift: list[str] = []
    for rel, entry in sealed.items():
        path = PROJECT_ROOT / rel
        if not path.is_file():
            drift.append(f"{rel}: MISSING")
            continue
        computed = sha256_file(path)
        digests[rel] = computed
        if computed != entry["sha256"]:
            drift.append(f"{rel}: sealed {entry['sha256']} but found {computed}")

    if drift:
        raise PreRegistrationViolation(
            "Stage 1 pre-registered configuration has changed since it was sealed:\n  "
            + "\n  ".join(drift)
            + "\nThis is a governance failure, not a bug to work around. Stop and report it."
        )

    return Stage1Config(data_source, universe_spec, prereg, digests)
