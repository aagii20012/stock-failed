"""Load the sealed Stage 2 cost model and acceptance spec, refusing anything that has drifted.

Same shape as :mod:`stockedge100.data.config`, and for the same reason: a cost assumption that can
be edited after a result exists is not an assumption, it is a knob. Every module that needs a cost,
a rounding direction, or a fixture value loads it through here.
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

PREREGISTRATION_JSON = PROJECT_ROOT / "governance" / "STAGE_2_PREREGISTRATION.json"
HOLDOUT_LOCK_JSON = PROJECT_ROOT / "governance" / "STAGE_1_HOLDOUT_LOCK.json"

COST_MODEL_REL = "config/stage2_cost_model.json"
ENGINE_SPEC_REL = "config/stage2_engine_spec.json"


@dataclass(frozen=True)
class Stage2Config:
    cost_model: dict[str, Any]
    engine_spec: dict[str, Any]
    preregistration: dict[str, Any]
    digests: dict[str, str]

    @property
    def declared_utc(self) -> str:
        return str(self.preregistration["declared_utc"])

    @property
    def config_hash(self) -> str:
        return self.digests[COST_MODEL_REL]

    @property
    def fixtures(self) -> dict[str, Any]:
        return self.engine_spec["hand_calculated_fixtures"]

    def defect_class_ids(self) -> list[str]:
        return [entry["id"] for entry in self.engine_spec["defect_classes"]["classes"]]


def load_stage2_config(*, require_seal: bool = True) -> Stage2Config:
    """Load the Stage 2 rules and verify them against the sealed pre-registration.

    ``require_seal=False`` exists only for the sealing program itself, which must read the files
    before the seal exists. Nothing else may pass it.
    """
    cost_model = json.loads((PROJECT_ROOT / COST_MODEL_REL).read_text(encoding="utf-8"))
    engine_spec = json.loads((PROJECT_ROOT / ENGINE_SPEC_REL).read_text(encoding="utf-8"))

    if not require_seal:
        return Stage2Config(cost_model, engine_spec, {}, {})

    if not PREREGISTRATION_JSON.is_file():
        raise ConfigViolation(
            "governance/STAGE_2_PREREGISTRATION.json is missing. The Stage 2 cost model was never "
            "sealed, so no engine result computed with it can be trusted."
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
        raise ConfigViolation(
            "Stage 2 pre-registered configuration has changed since it was sealed:\n  "
            + "\n  ".join(drift)
            + "\nThis is a governance failure, not a bug to work around. Stop and report it."
        )

    return Stage2Config(cost_model, engine_spec, prereg, digests)


def load_partition_bounds() -> dict[str, str]:
    """The locked window boundaries, read from the Stage 1 holdout lock rather than restated.

    Restating them here would create a second copy that could disagree with the locked one, and the
    copy that disagrees is always the one an engine ends up trusting.
    """
    lock = json.loads(HOLDOUT_LOCK_JSON.read_text(encoding="utf-8"))
    if lock.get("holdout_state") != "SEALED":
        raise ConfigViolation(
            f"the Stage 1 holdout lock reports holdout_state={lock.get('holdout_state')!r}; "
            "Stage 2 will not run against an unsealed partition"
        )
    return dict(lock["partition"])


def dec(value: Any) -> Decimal:
    """Parse a sealed configuration value into a :class:`~decimal.Decimal`.

    Sealed money and rate values are stored in JSON as **strings** precisely so they survive the
    round trip exactly. A float would already have lost the value before this function saw it, so a
    float argument is refused rather than converted.
    """
    if isinstance(value, float):
        raise ConfigViolation(
            f"refusing to build a Decimal from the float {value!r}: a sealed money or rate value "
            "must be stored as a string so it round-trips exactly"
        )
    return Decimal(str(value))
