"""Generation 2's cost model, derived from Generation 1's sealed one rather than copied.

The operating instruction for Generation 2 puts the cost model out of scope: it must not be revised.
A second copy of the numbers would be a second place they could drift, so Generation 2 holds none.
``config/generation_2/g2_cost_model.json`` (``SE100-CFG-2101``) is not a cost model at all — it is
the declaration of a *derivation*, and this module executes it:

1. load ``config/stage2_cost_model.json`` through Generation 1's own seal check, which raises if the
   file has moved by one byte;
2. apply exactly the declared override, ``/account/max_open_risky_positions`` set to the variant's
   ``k``;
3. walk both mappings and refuse to construct a :class:`CostModel` unless the difference set is
   exactly that one pointer.

Step 3 is the part that matters. Steps 1 and 2 describe what the code intends to do; step 3 is what
makes the claim checkable by something other than reading the code.

The 50% single-position concentration ceiling is declared here too, because the sealed Generation 1
cost model has no field for it — a one-position portfolio cannot breach a concentration limit the
gross-exposure cap does not already cover — and that file is frozen. It is enforced in
:mod:`stockedge100.backtest.g2_engine`.
"""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from functools import lru_cache
from typing import Any

from stockedge100.audit import sha256_file
from stockedge100.backtest.config import PROJECT_ROOT, dec, load_stage2_config
from stockedge100.backtest.costs import BASE, SCENARIOS, CostModel
from stockedge100.backtest.errors import ConfigViolation

__all__ = [
    "DECLARATION_PATH",
    "DECLARATION_ID",
    "OVERRIDE_POINTER",
    "SEALED_COST_MODEL_REL",
    "load_declaration",
    "permitted_position_counts",
    "concentration_ceiling",
    "flatten_pointers",
    "difference_set",
    "derive_mapping",
    "rotation_cost_model",
    "derivation_evidence",
]

DECLARATION_PATH = PROJECT_ROOT / "config" / "generation_2" / "g2_cost_model.json"
DECLARATION_ID = "SE100-CFG-2101"
OVERRIDE_POINTER = "/account/max_open_risky_positions"
SEALED_COST_MODEL_REL = "config/stage2_cost_model.json"


def _escape(token: str) -> str:
    """RFC 6901 pointer escaping. No sealed key needs it today; relying on that would be luck."""
    return token.replace("~", "~0").replace("/", "~1")


def flatten_pointers(node: Any, prefix: str = "") -> dict[str, Any]:
    """Every leaf of ``node``, keyed by JSON pointer.

    Containers are flattened rather than compared whole, so a difference reports the path that
    differs instead of "the frictions block changed".
    """
    if isinstance(node, dict):
        flat: dict[str, Any] = {}
        for key, value in node.items():
            flat.update(flatten_pointers(value, f"{prefix}/{_escape(str(key))}"))
        return flat
    if isinstance(node, list):
        flat = {}
        for index, value in enumerate(node):
            flat.update(flatten_pointers(value, f"{prefix}/{index}"))
        return flat
    return {prefix: node}


def difference_set(sealed: dict[str, Any], derived: dict[str, Any]) -> list[str]:
    """Sorted JSON pointers at which the two mappings differ, including additions and removals."""
    left = flatten_pointers(sealed)
    right = flatten_pointers(derived)
    pointers = set(left) | set(right)
    return sorted(
        pointer
        for pointer in pointers
        if pointer not in left
        or pointer not in right
        or left[pointer] != right[pointer]
        or type(left[pointer]) is not type(right[pointer])
    )


@lru_cache(maxsize=1)
def load_declaration() -> dict[str, Any]:
    """The Generation 2 derivation declaration, checked for identity and self-consistency."""
    if not DECLARATION_PATH.is_file():
        raise ConfigViolation(f"the Generation 2 cost derivation is missing at {DECLARATION_PATH}")
    declaration = json.loads(DECLARATION_PATH.read_text(encoding="utf-8"))

    if declaration.get("artifact_id") != DECLARATION_ID:
        raise ConfigViolation(
            f"{DECLARATION_PATH.name} declares artifact_id {declaration.get('artifact_id')!r}; "
            f"expected {DECLARATION_ID!r}"
        )
    if declaration.get("generation") != 2:
        raise ConfigViolation(f"{DECLARATION_PATH.name} is not a Generation 2 artifact")
    if declaration.get("no_other_field_may_differ") is not True:
        raise ConfigViolation(
            f"{DECLARATION_PATH.name} no longer asserts no_other_field_may_differ; this module "
            "implements a derivation that permits exactly one difference and nothing else"
        )
    if declaration.get("live_trading_authorized") is not False:
        raise ConfigViolation(f"{DECLARATION_PATH.name} no longer records live_trading_authorized as false")

    overrides = declaration["overrides"]
    if len(overrides) != 1 or overrides[0]["json_pointer"] != OVERRIDE_POINTER:
        raise ConfigViolation(
            f"{DECLARATION_PATH.name} declares overrides "
            f"{[entry.get('json_pointer') for entry in overrides]!r}; this module implements exactly "
            f"[{OVERRIDE_POINTER!r}]"
        )
    if declaration.get("difference_set_expected_size") != len(overrides):
        raise ConfigViolation(
            f"{DECLARATION_PATH.name} expects a difference set of "
            f"{declaration.get('difference_set_expected_size')!r} but declares {len(overrides)} override(s)"
        )

    source = declaration["derived_from"]
    if source["path"] != SEALED_COST_MODEL_REL:
        raise ConfigViolation(
            f"{DECLARATION_PATH.name} derives from {source['path']!r}, not {SEALED_COST_MODEL_REL!r}"
        )
    on_disk = sha256_file(PROJECT_ROOT / SEALED_COST_MODEL_REL)
    if on_disk != source["sha256"]:
        raise ConfigViolation(
            f"the Generation 2 derivation names {SEALED_COST_MODEL_REL} at {source['sha256']} but the "
            f"file on disk is {on_disk}. Generation 1's cost model is frozen; a difference here is a "
            "governance failure, not a value to update."
        )
    return declaration


def permitted_position_counts() -> tuple[int, ...]:
    """The values ``k`` may take, read from the declaration rather than from the grid."""
    return tuple(int(value) for value in load_declaration()["overrides"][0]["permitted_values"])


def concentration_ceiling() -> Decimal:
    """The 50% single-position ceiling, as a fraction of account equity."""
    return dec(load_declaration()["concentration_ceiling"]["value"])


def derive_mapping(k: int) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Return ``(sealed, derived, differences)`` for position count ``k``.

    The sealed mapping is loaded through :func:`load_stage2_config` with the seal check on, so a
    drifted Generation 1 cost model stops Generation 2 before any override is applied.
    """
    declaration = load_declaration()
    override = declaration["overrides"][0]
    permitted = permitted_position_counts()
    if k not in permitted:
        raise ConfigViolation(
            f"k={k!r} is not one of the declared position counts {list(permitted)}; the grid is "
            "complete at eighteen variants and no other breadth is authorized"
        )

    sealed = load_stage2_config().cost_model
    account = sealed["account"]
    if account["max_open_risky_positions"] != override["sealed_value"]:
        raise ConfigViolation(
            f"the sealed cost model holds max_open_risky_positions="
            f"{account['max_open_risky_positions']!r}; the derivation was declared against "
            f"{override['sealed_value']!r}"
        )

    derived = copy.deepcopy(sealed)
    derived["account"]["max_open_risky_positions"] = k

    differences = difference_set(sealed, derived)
    expected = [OVERRIDE_POINTER] if k != override["sealed_value"] else []
    if differences != expected:
        raise ConfigViolation(
            f"the Generation 2 cost derivation for k={k} differs from the sealed model at "
            f"{differences!r}; the declaration permits exactly {expected!r}. Refusing to build a "
            "cost model that is not the sealed one plus its single declared override."
        )
    return sealed, derived, differences


def rotation_cost_model(k: int, scenario: str = BASE) -> CostModel:
    """The sealed Generation 1 cost model with breadth raised to ``k``, and nothing else changed."""
    if scenario not in SCENARIOS:
        raise ConfigViolation(f"unknown cost scenario {scenario!r}; declared: {SCENARIOS}")
    _, derived, _ = derive_mapping(k)
    costs = CostModel(derived, scenario)
    if costs.max_open_risky_positions != k:
        raise ConfigViolation(
            f"the derived cost model reports max_open_risky_positions="
            f"{costs.max_open_risky_positions}, not the requested {k}"
        )
    return costs


def derivation_evidence(k: int) -> dict[str, Any]:
    """What the derivation actually did, for a report that must show it rather than assert it."""
    declaration = load_declaration()
    sealed, derived, differences = derive_mapping(k)
    return {
        "declaration": DECLARATION_PATH.name,
        "declaration_artifact_id": declaration["artifact_id"],
        "derived_from": SEALED_COST_MODEL_REL,
        "derived_from_sha256": declaration["derived_from"]["sha256"],
        "loader": "stockedge100.backtest.config.load_stage2_config(require_seal=True)",
        "sealed_leaf_count": len(flatten_pointers(sealed)),
        "derived_leaf_count": len(flatten_pointers(derived)),
        "difference_set": differences,
        "difference_set_size": len(differences),
        "override_pointer": OVERRIDE_POINTER,
        "sealed_value": declaration["overrides"][0]["sealed_value"],
        "generation_2_value": k,
        "concentration_ceiling": f"{concentration_ceiling():f}",
    }
