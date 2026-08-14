"""Load the sealed Stage 3 protocol, and refuse to run if it has moved.

This mirrors :mod:`stockedge100.backtest.config` deliberately. The Stage 2 loader recomputes the
digest of every pre-registered file on every load and raises rather than continue; the same
discipline applies here, because the whole evidentiary value of Stage 3 rests on the claim that the
parameters were fixed before the code existed. A loader that trusted the file on disk would make
that claim unfalsifiable.

The seal of record is ``governance/STAGE_3_PREREGISTRATION.json``. Its ``preregistered_files`` map
carries the digest of the Markdown pre-registration and of both configuration files. All three are
recomputed here; drift in any one of them is a governance failure, not a bug to work around.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_file
from stockedge100.backtest.errors import ConfigViolation

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PREREGISTRATION_JSON = PROJECT_ROOT / "governance" / "STAGE_3_PREREGISTRATION.json"

PROTOCOL_REL = "config/stage3_strategy_protocol.json"
CRITERIA_REL = "config/stage3_gate_criteria.json"


@dataclass(frozen=True)
class Stage3Config:
    """The sealed Stage 3 inputs, plus the digests that were recomputed to obtain them."""

    protocol: dict[str, Any]
    criteria: dict[str, Any]
    preregistration: dict[str, Any]
    digests: dict[str, str]

    @property
    def experiments(self) -> list[dict[str, Any]]:
        return list(self.protocol["experiments"])

    @property
    def shared_rules(self) -> dict[str, str]:
        return dict(self.protocol["shared_rules"])

    @property
    def indicator_definitions(self) -> dict[str, Any]:
        return dict(self.protocol["indicator_definitions"])

    @property
    def gate_conditions(self) -> list[dict[str, Any]]:
        return list(self.criteria["conditions"])

    @property
    def thresholds(self) -> dict[str, Any]:
        return dict(self.criteria["frozen_gate_json_companion_verbatim"]["thresholds"])

    def experiment(self, experiment_id: str) -> dict[str, Any]:
        for entry in self.protocol["experiments"]:
            if entry["experiment_id"] == experiment_id:
                return entry
        raise ConfigViolation(f"no sealed experiment with id {experiment_id!r}")


def load_stage3_config(*, require_seal: bool = True) -> Stage3Config:
    """Read the sealed protocol and criteria, verifying both against the pre-registration.

    ``require_seal=False`` exists only for the failure-path test that has to observe what happens
    when the seal is absent. It does not skip the digest check on files that *are* sealed.
    """

    protocol_path = PROJECT_ROOT / PROTOCOL_REL
    criteria_path = PROJECT_ROOT / CRITERIA_REL
    for path in (protocol_path, criteria_path):
        if not path.is_file():
            raise ConfigViolation(f"sealed Stage 3 configuration is missing: {path}")

    if not PREREGISTRATION_JSON.is_file():
        if require_seal:
            raise ConfigViolation(
                f"Stage 3 pre-registration record is missing: {PREREGISTRATION_JSON}. "
                "Strategy code may not run without the seal that fixes its parameters."
            )
        prereg: dict[str, Any] = {}
        sealed: dict[str, Any] = {}
    else:
        prereg = json.loads(PREREGISTRATION_JSON.read_text(encoding="utf-8"))
        sealed = prereg.get("preregistered_files", {})

    if require_seal:
        for rel in (PROTOCOL_REL, CRITERIA_REL):
            if rel not in sealed:
                raise ConfigViolation(
                    f"{rel} is not listed in {PREREGISTRATION_JSON.name}. An unsealed parameter "
                    "file cannot be used to produce Gate 3 evidence."
                )

    digests: dict[str, str] = {}
    drift: list[str] = []
    for rel, entry in sorted(sealed.items()):
        path = PROJECT_ROOT / rel
        if not path.is_file():
            drift.append(f"{rel}: MISSING")
            continue
        computed = sha256_file(path)
        digests[rel] = computed
        if computed != entry["sha256"]:
            drift.append(f"{rel}: sealed {entry['sha256']} but found {computed}")
    if drift:
        raise ConfigViolation(
            "Stage 3 pre-registered configuration has changed since it was sealed:\n  "
            + "\n  ".join(drift)
            + "\nThis is a governance failure, not a bug to work around. Stop and report it."
        )

    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    criteria = json.loads(criteria_path.read_text(encoding="utf-8"))
    if not digests:
        digests = {
            PROTOCOL_REL: sha256_file(protocol_path),
            CRITERIA_REL: sha256_file(criteria_path),
        }
    return Stage3Config(protocol=protocol, criteria=criteria, preregistration=prereg, digests=digests)


def dec(value: Any) -> Decimal:
    """Sealed JSON numbers become Decimals through their string form, never through ``float``."""

    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        raise ConfigViolation(
            f"refusing to build a Decimal from the float {value!r}; a sealed numeric value must "
            "reach the engine through its exact decimal text"
        )
    return Decimal(str(value))
