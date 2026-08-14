"""Load the sealed Attempt 2 protocol and its gate binding, and refuse to run if either has moved.

This mirrors :mod:`stockedge100.strategies.config` deliberately, for the same reason that module
mirrors the Stage 2 loader: the whole evidentiary value of an adaptive second attempt rests on the
claim that every parameter was fixed before any Attempt 2 strategy code existed. A loader that
trusted the file on disk would make that claim unfalsifiable.

Three seals are recomputed here, not one.

* ``governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json`` carries ``preregistered_files`` for the
  Attempt 2 protocol (SE100-CFG-3003), the gate binding (SE100-CFG-3004), and the Markdown
  pre-registration. All three are recomputed.
* The binding adopts SE100-CFG-3002 *by digest rather than by copy* — "A copy could drift... A
  digest reference cannot drift, and the loader that reads it fails closed on any mismatch." This
  module is that loader. The criteria file is read from ``bound_artifact.path`` and its digest must
  equal both ``bound_artifact.sha256`` and the pre-registration's ``gate.criteria_sha256``.
* Every entry of the protocol's ``inputs_bound`` names its file and its digest inline in prose.
  Those digests are extracted and recomputed too, which is how the Attempt 1 protocol reaches this
  module: it is read-only input, cited "for shared rules and indicator definitions adopted
  unchanged", and the one number Attempt 2 needs from it — ``RSI.warmup_changes`` — is read from the
  verified file rather than restated here. A restated 100 would be a second copy of a sealed value,
  and the second copy is eventually the one that is wrong.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_file
from stockedge100.backtest.errors import ConfigViolation

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PREREGISTRATION_JSON = PROJECT_ROOT / "governance" / "STAGE_3_ATTEMPT_2_PREREGISTRATION.json"

PROTOCOL_REL = "config/stage3_attempt2_strategy_protocol.json"
BINDING_REL = "config/stage3_attempt2_gate_criteria_binding.json"
PREREGISTRATION_MD_REL = "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.md"

ATTEMPT_1_PROTOCOL_REL = "config/stage3_strategy_protocol.json"

#: ``inputs_bound`` key -> the repository-relative path its prose must name.
BOUND_INPUTS: dict[str, str] = {
    "universe": "governance/STAGE_1_UNIVERSE.json",
    "window_bounds_source": "governance/STAGE_1_HOLDOUT_LOCK.json",
    "cost_model": "config/stage2_cost_model.json",
    "gate_criteria": "config/stage3_gate_criteria.json",
    "attempt_1_protocol": ATTEMPT_1_PROTOCOL_REL,
}

_SHA256 = re.compile(r"\b[0-9a-f]{64}\b")

PROTOCOL_ARTIFACT_ID = "SE100-CFG-3003"
BINDING_ARTIFACT_ID = "SE100-CFG-3004"
CRITERIA_ARTIFACT_ID = "SE100-CFG-3002"


def bound_digest(inputs_bound: dict[str, Any], key: str) -> str:
    """Extract the sealed digest of one bound input from its prose entry.

    The sealed ``inputs_bound`` values are sentences, not sub-objects, so the digest has to be
    parsed out. Two guards make that parse fail closed rather than guess: the entry must name its
    own path, and it must carry exactly one 64-hex token. A sentence that mentioned two digests, or
    that named a different file, would otherwise be read as authorising whichever hash appeared
    first.
    """

    if key not in inputs_bound:
        raise ConfigViolation(f"sealed inputs_bound carries no {key!r} entry")
    text = str(inputs_bound[key])
    expected_path = BOUND_INPUTS[key]
    if expected_path not in text:
        raise ConfigViolation(
            f"sealed inputs_bound[{key!r}] does not name {expected_path}; it reads {text!r}"
        )
    found = _SHA256.findall(text)
    if len(found) != 1:
        raise ConfigViolation(
            f"sealed inputs_bound[{key!r}] carries {len(found)} sha256 tokens; exactly one is "
            "required to bind a digest unambiguously"
        )
    return found[0]


@dataclass(frozen=True)
class Attempt2Config:
    """The sealed Attempt 2 inputs, plus the digests recomputed to obtain them."""

    protocol: dict[str, Any]
    binding: dict[str, Any]
    criteria: dict[str, Any]
    attempt_1_protocol: dict[str, Any]
    preregistration: dict[str, Any]
    digests: dict[str, str]

    @property
    def experiments(self) -> list[dict[str, Any]]:
        return list(self.protocol["experiments"])

    @property
    def shared_rules(self) -> dict[str, Any]:
        return dict(self.protocol["shared_rules"])

    @property
    def shared_rule_texts(self) -> dict[str, str]:
        """The readable restatements. The sealed names live in ``shared_rules['adopted_unchanged']``."""

        return dict(self.protocol["shared_rules"]["adopted_text_restated_for_readability"])

    @property
    def indicator_definitions(self) -> dict[str, Any]:
        return dict(self.protocol["indicator_definitions"])

    @property
    def vol20(self) -> dict[str, Any]:
        """The one indicator Attempt 2 adds; it is nested under ``added``, not at the top level."""

        return dict(self.protocol["indicator_definitions"]["added"]["VOL20"])

    @property
    def rsi_warmup_changes(self) -> int:
        """Read from the verified Attempt 1 protocol, which Attempt 2 adopts unchanged.

        Attempt 2's own ``indicator_definitions`` restate the RSI procedure in prose and carry no
        number, precisely so that the number has one home.
        """

        adopted = self.indicator_definitions.get("adopted_unchanged", [])
        if "RSI" not in adopted:
            raise ConfigViolation(
                "the sealed Attempt 2 protocol does not adopt RSI unchanged, so its warm-up length "
                "may not be read from SE100-CFG-3001"
            )
        return int(self.attempt_1_protocol["indicator_definitions"]["RSI"]["warmup_changes"])

    @property
    def normalized_indicator_definitions(self) -> dict[str, Any]:
        """The shape the Attempt 1 planner helpers expect: ``{"RSI": {"warmup_changes": int}}``.

        ``strategies.runner.largest_lookback`` reads ``indicator_definitions["RSI"]["warmup_changes"]``
        at the top level. Attempt 2's file nests its RSI text elsewhere, so this adapter supplies the
        one field those helpers index, sourced from the digest-verified Attempt 1 protocol.
        """

        return {"RSI": {"warmup_changes": self.rsi_warmup_changes}}

    @property
    def risk_architecture(self) -> dict[str, Any]:
        return dict(self.protocol["risk_architecture"])

    @property
    def iteration_budget(self) -> dict[str, Any]:
        return dict(self.protocol["iteration_budget"])

    @property
    def excluded_symbols(self) -> dict[str, Any]:
        return dict(self.protocol.get("excluded_symbols", {}))

    @property
    def gate_conditions(self) -> list[dict[str, Any]]:
        return list(self.criteria["conditions"])

    @property
    def thresholds(self) -> dict[str, Any]:
        return dict(self.criteria["frozen_gate_json_companion_verbatim"]["thresholds"])

    @property
    def rederivations(self) -> list[dict[str, Any]]:
        return list(self.binding["rederivations"])

    def rederivation(self, rederivation_id: str) -> dict[str, Any]:
        for entry in self.rederivations:
            if entry["id"] == rederivation_id:
                return entry
        raise ConfigViolation(f"no sealed re-derivation with id {rederivation_id!r}")

    def experiment(self, experiment_id: str) -> dict[str, Any]:
        for entry in self.protocol["experiments"]:
            if entry["experiment_id"] == experiment_id:
                return entry
        raise ConfigViolation(f"no sealed Attempt 2 experiment with id {experiment_id!r}")

    @property
    def experiment_ids(self) -> tuple[str, ...]:
        return tuple(entry["experiment_id"] for entry in self.protocol["experiments"])


def _verify(rel: str, expected: str, digests: dict[str, str], drift: list[str]) -> None:
    path = PROJECT_ROOT / rel
    if not path.is_file():
        drift.append(f"{rel}: MISSING")
        return
    computed = sha256_file(path)
    previous = digests.get(rel)
    if previous is not None and previous != computed:
        # Cannot happen from one filesystem read, but a mismatch here would mean the file changed
        # mid-load, and a config that changes mid-load may not produce gate evidence.
        drift.append(f"{rel}: digest changed during load, {previous} then {computed}")
    digests[rel] = computed
    if computed != expected:
        drift.append(f"{rel}: sealed {expected} but found {computed}")


def load_attempt2_config() -> Attempt2Config:
    """Read the sealed Attempt 2 protocol, gate binding and bound inputs, verifying every digest.

    The seal is not optional here, and there is deliberately no keyword that makes it optional.
    The three Stage 0-2 loaders carry an unsealed path because each of them had to be able to read
    its own configuration *before* the sealing program had written the record; Attempt 2 inherits a
    seal that already exists, so nothing in this stage can legitimately need to bypass it. Giving
    this function a bypass would only create a way to produce Gate 3 evidence from parameters
    nobody committed to in advance.
    """

    protocol_path = PROJECT_ROOT / PROTOCOL_REL
    binding_path = PROJECT_ROOT / BINDING_REL
    for path in (protocol_path, binding_path):
        if not path.is_file():
            raise ConfigViolation(f"sealed Attempt 2 configuration is missing: {path}")

    if not PREREGISTRATION_JSON.is_file():
        raise ConfigViolation(
            f"Attempt 2 pre-registration record is missing: {PREREGISTRATION_JSON}. "
            "Strategy code may not run without the seal that fixes its parameters."
        )
    prereg = json.loads(PREREGISTRATION_JSON.read_text(encoding="utf-8"))
    sealed = prereg.get("preregistered_files", {})

    for rel in (PROTOCOL_REL, BINDING_REL, PREREGISTRATION_MD_REL):
        if rel not in sealed:
            raise ConfigViolation(
                f"{rel} is not listed in {PREREGISTRATION_JSON.name}. An unsealed parameter "
                "file cannot be used to produce Attempt 2 Gate 3 evidence."
            )

    digests: dict[str, str] = {}
    drift: list[str] = []
    for rel, entry in sorted(sealed.items()):
        _verify(rel, entry["sha256"], digests, drift)
    if drift:
        raise ConfigViolation(
            "Attempt 2 pre-registered configuration has changed since it was sealed:\n  "
            + "\n  ".join(drift)
            + "\nThis is a governance failure, not a bug to work around. Stop and report it."
        )

    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    if protocol.get("artifact_id") != PROTOCOL_ARTIFACT_ID:
        raise ConfigViolation(
            f"{PROTOCOL_REL} declares artifact_id {protocol.get('artifact_id')!r}, "
            f"not {PROTOCOL_ARTIFACT_ID}"
        )
    if binding.get("artifact_id") != BINDING_ARTIFACT_ID:
        raise ConfigViolation(
            f"{BINDING_REL} declares artifact_id {binding.get('artifact_id')!r}, "
            f"not {BINDING_ARTIFACT_ID}"
        )

    inputs_bound = dict(protocol["inputs_bound"])
    for key in sorted(BOUND_INPUTS):
        _verify(BOUND_INPUTS[key], bound_digest(inputs_bound, key), digests, drift)
    if drift:
        raise ConfigViolation(
            "an input bound by the sealed Attempt 2 protocol has changed since it was sealed:\n  "
            + "\n  ".join(drift)
            + "\nThis is a governance failure, not a bug to work around. Stop and report it."
        )

    bound = dict(binding["bound_artifact"])
    if bound.get("artifact_id") != CRITERIA_ARTIFACT_ID:
        raise ConfigViolation(
            f"the Attempt 2 binding binds {bound.get('artifact_id')!r}, not {CRITERIA_ARTIFACT_ID}"
        )
    if bound.get("adoption") != "ADOPTED_UNCHANGED":
        raise ConfigViolation(
            f"the Attempt 2 binding records adoption {bound.get('adoption')!r}; Gate 3 criteria may "
            "only be adopted unchanged by this attempt"
        )
    criteria_rel = str(bound["path"])
    if criteria_rel != BOUND_INPUTS["gate_criteria"]:
        raise ConfigViolation(
            f"the binding points at {criteria_rel} but the protocol binds "
            f"{BOUND_INPUTS['gate_criteria']}"
        )
    criteria_digest = digests[criteria_rel]
    for source, expected in (
        ("the Attempt 2 gate binding bound_artifact.sha256", str(bound["sha256"])),
        (
            "the Attempt 2 pre-registration gate.criteria_sha256",
            str(prereg.get("gate", {}).get("criteria_sha256", bound["sha256"])),
        ),
    ):
        if criteria_digest != expected:
            raise ConfigViolation(
                f"{criteria_rel} hashes to {criteria_digest} but {source} records {expected}. "
                "The Gate 3 criteria were adopted unchanged by digest; a mismatch means they "
                "changed. Stop and report it."
            )
    if prereg.get("gate", {}).get("criteria_changed_for_attempt_2") is not False:
        raise ConfigViolation(
            "the Attempt 2 pre-registration does not record criteria_changed_for_attempt_2 as false"
        )

    criteria = json.loads((PROJECT_ROOT / criteria_rel).read_text(encoding="utf-8"))
    attempt_1_protocol = json.loads(
        (PROJECT_ROOT / ATTEMPT_1_PROTOCOL_REL).read_text(encoding="utf-8")
    )

    return Attempt2Config(
        protocol=protocol,
        binding=binding,
        criteria=criteria,
        attempt_1_protocol=attempt_1_protocol,
        preregistration=prereg,
        digests=digests,
    )


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
