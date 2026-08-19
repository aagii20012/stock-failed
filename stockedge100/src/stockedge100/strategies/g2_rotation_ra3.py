"""``SE100-G2-S3-C3-ROTATION-RA3`` — Attempt 3's candidate: Attempt 2's candidate, sized under RA3.

Everything here was fixed in ``config/generation_2/g2_rotation_ra3_protocol.json``
(``SE100-CFG-3105``) and its Markdown counterpart before any Attempt 3 strategy code existed, so this
module reads the seal rather than restating it — the same discipline
:mod:`stockedge100.strategies.g2_rotation_ra1` applied to ``SE100-CFG-3103``.

**What is reused, and how literally.** Attempt 3 changes two things: the de-risk ladder (RA3 removes
the −5% tier RA2 had added beyond Generation 1's original architecture) and the representative
selection rule. Neither is a strategy-level change, so the strategy level is reused rather than
retyped:

* the four seal verifiers ``_verify_universe``, ``_verify_family``, ``_verify_order_kinds`` and
  ``_verify_rebalance`` are **imported from Attempt 2's module and called unmodified**. Every key
  each of them dereferences was measured present in CFG-3105 before this module relied on it. A
  retyped verifier would be a second definition of the same check and a place for the two to diverge;
  importing Attempt 2's makes "Attempt 3's universe, family, order kinds and calendar pass exactly
  the checks Attempt 2's passed" true by construction rather than by inspection.
* ``ENTRY_TAG``, ``EXIT_TAG`` and ``FAMILY`` are imported for the same reason. There is one
  definition of each in the tree.
* :class:`RotationCandidateRA3` binds ``rank``, ``decide``, ``target``, ``ranking_digest``,
  ``entry_order``, ``exit_order`` and ``evidence`` from :class:`~stockedge100.strategies.
  g2_rotation_ra1.RotationCandidateRA1`, which in turn bound the first four from Attempt 1. The chain
  back to Attempt 1 is asserted at the end of this module rather than described.

Attempt 1's and Attempt 2's modules are imported and read; neither is written, and nothing here
changes their behaviour for their own callers.

**Why ``target_weight`` is nonetheless re-derived.** Attempt 2's ``target_weight`` reads ``A`` off
:func:`~stockedge100.backtest.g2_engine_ra1.load_risk_architecture` — RA2's — and checks the result
against CFG-3103's ``position_sizing``. Calling it here would make Attempt 3's sizing depend on
Attempt 2's protocol file still loading, and would take the aggregate exposure ceiling from the
architecture this attempt exists to replace. So ``A`` is read from RA3-1 and the result is checked
against CFG-3105's own ``position_sizing`` block. That the two derivations agree is *evidence*
(:func:`attempt_2_weight_agreement`), deliberately not a runtime dependency, exactly as Attempt 2
kept :func:`~stockedge100.strategies.g2_rotation_ra1.attempt_1_weight_comparison` off its own sizing
path.

The sealed formula names ``A = 0.50`` as "the Attempt 2 aggregate exposure ceiling (RA2-1)" while
this module derives ``A`` from RA3-1. :func:`target_weight` therefore parses both constants out of
the sealed sentence and requires them to equal the two ceilings it actually used, so that a prose
sentence describing one architecture and a derivation running on another cannot silently disagree.

**``G2A3-CONFLICT-39`` — the carried-unchanged claim is narrower than its wording.**
``mechanics_carried_unchanged.method`` states "Only ``grid.variant_id_format`` and
``grid.variants[].variant_id`` differ". Compared pointer by pointer against CFG-3103, four further
pointers differ across the thirteen named blocks: three are purely additive provenance notes
(``run_span.reverification_required``, ``grid.unchanged_from_attempt_2``,
``grid.variant_id_change_note``, ``gate_evaluation_scope.thresholds_changed_from_attempt_2``) and one
is a changed pointer that could not have been otherwise
(``gate_evaluation_scope.criteria_source``, which must name Attempt 3's own criteria file). None is a
mechanic. The seal is not edited; :func:`check_mechanics_carried_unchanged` implements the true
predicate — no pointer removed, no pointer changed outside a declared list, no addition outside a
declared list — and reports the unused entries of both allow-lists so that a list which only ever
widens shows up as evidence rather than passing quietly.
"""

from __future__ import annotations

import ast
import datetime as dt
import hashlib
import inspect
import json
import pathlib
import re
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from functools import lru_cache
from typing import Any, Sequence

from stockedge100.backtest.config import dec
from stockedge100.backtest.costs import BASE, CostModel, exact
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation
from stockedge100.backtest.g2_costs import concentration_ceiling, rotation_cost_model
from stockedge100.backtest.g2_engine_ra1 import (
    SCALAR_DECIMALS,
    SCALAR_QUANTUM,
    SPELLED_DECIMALS,
)
from stockedge100.backtest.g2_engine_ra3 import (
    ATTEMPT_2_PROTOCOL_PATH,
    PROTOCOL_ID,
    PROTOCOL_PATH,
    STRATEGY_ID,
    load_ra3_protocol,
    load_risk_architecture_ra3,
)
from stockedge100.strategies import g2_rotation as attempt_1
from stockedge100.strategies import g2_rotation_ra1 as attempt_2
from stockedge100.strategies.base import Candidate
from stockedge100.strategies.g2_rotation import RotationCandidate, total_return
from stockedge100.strategies.g2_rotation_ra1 import (
    ENTRY_TAG,
    EXIT_TAG,
    FAMILY,
    RotationCandidateRA1,
    _verify_family,
    _verify_order_kinds,
    _verify_rebalance,
    _verify_universe,
)

__all__ = [
    "ENTRY_TAG",
    "EXIT_TAG",
    "FAMILY",
    "PROTOCOL_ID",
    "PROTOCOL_PATH",
    "STRATEGY_ID",
    "RotationCandidateRA3",
    "RotationVariantRA3",
    "attempt_2_grid_agreement",
    "attempt_2_weight_agreement",
    "build_candidate",
    "check_mechanics_carried_unchanged",
    "eligible_universe",
    "load_protocol",
    "rotation_variants",
    "target_weight",
    "variant_by_id",
]

#: The thirteen blocks ``mechanics_carried_unchanged`` declares copied from CFG-3103. Read off the
#: seal at check time rather than restated here; this tuple only records what the module expects to
#: find, so that a seal which quietly dropped a block is a mismatch instead of a shorter loop.
EXPECTED_CARRIED_BLOCKS = (
    "eligible_universe",
    "ranking_signal",
    "ranking_rule",
    "position_count",
    "rebalance",
    "execution",
    "position_sizing",
    "concentration_ceiling",
    "window",
    "run_span",
    "grid",
    "runs_per_variant",
    "gate_evaluation_scope",
)

#: Pointers that legitimately hold a *different value* in CFG-3105 than in CFG-3103. The eighteen
#: variant ids are generated rather than listed; see :func:`check_mechanics_carried_unchanged`.
PERMITTED_CHANGED_POINTERS = (
    "/grid/variant_id_format",
    "/gate_evaluation_scope/criteria_source",
)

#: Pointers CFG-3105 *adds*. All four are provenance notes about Attempt 3 that could not have
#: existed in Attempt 2's file; none names a mechanic.
PERMITTED_ADDED_POINTERS = (
    "/run_span/reverification_required",
    "/grid/unchanged_from_attempt_2",
    "/grid/variant_id_change_note",
    "/gate_evaluation_scope/thresholds_changed_from_attempt_2",
)


# -- the seal ------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_protocol() -> dict[str, Any]:
    """The sealed Attempt 3 protocol, with the strategy-level checks on top of the engine's.

    Identity, generation, stage, attempt, ``declared_before_any_strategy_code`` and
    ``live_trading_authorized`` are already
    :func:`~stockedge100.backtest.g2_engine_ra3.load_ra3_protocol`'s. The four verifiers added here
    are Attempt 2's function objects, called on Attempt 3's protocol — see the module docstring. The
    fifth is Attempt 3's own and has no Attempt 2 counterpart: it is the check that the two declared
    changes really are the only two.
    """
    protocol = load_ra3_protocol()
    _verify_universe(protocol)
    _verify_family(protocol)
    _verify_order_kinds(protocol)
    _verify_rebalance(protocol)
    check_mechanics_carried_unchanged(protocol)
    return protocol


def _flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    """Every leaf of a JSON subtree, keyed by JSON-pointer-ish path.

    Whole-block equality answers "did anything change"; it cannot answer "did anything change that
    matters", which is the question ``mechanics_carried_unchanged`` actually poses.
    """
    flat: dict[str, Any] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            flat.update(_flatten(value, f"{prefix}/{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            flat.update(_flatten(value, f"{prefix}[{index}]"))
    else:
        flat[prefix] = node
    return flat


def check_mechanics_carried_unchanged(protocol: dict[str, Any] | None = None) -> dict[str, Any]:
    """The thirteen carried blocks, compared pointer by pointer against CFG-3103.

    The seal's own reasoning is that "any third difference, including an accidental one in a constant
    nobody re-read, would make the result uninterpretable". That is a measurable claim and this is the
    measurement. Three predicates, in order of how badly a failure would hurt:

    1. **Nothing was removed.** A pointer present in CFG-3103 and absent from CFG-3105 is a mechanic
       that stopped being declared. This is the dangerous direction and it is checked first.
    2. **Nothing changed outside the declared list.** The eighteen variant ids and the id format
       change by construction; ``gate_evaluation_scope.criteria_source`` must name this attempt's own
       criteria file.
    3. **Nothing was added outside the declared list.**

    The two allow-lists are reported back with their *unused* entries, because an allow-list that
    only ever widens is not a check. The eighteen id pointers are additionally required to be present
    in the changed set: if they were not, Attempt 3 would be running Attempt 2's variant ids, and a
    predicate that merely permits a difference would have passed on their absence.
    """
    protocol = load_ra3_protocol() if protocol is None else protocol
    node = protocol["mechanics_carried_unchanged"]
    blocks = tuple(node["blocks"])
    if blocks != EXPECTED_CARRIED_BLOCKS:
        raise ConfigViolation(
            f"the seal declares {len(blocks)} carried blocks {list(blocks)}; this module checks "
            f"{list(EXPECTED_CARRIED_BLOCKS)}. A block added to or dropped from that list changes "
            "what 'carried unchanged' covers."
        )

    attempt_2_protocol = json.loads(ATTEMPT_2_PROTOCOL_PATH.read_text(encoding="utf-8"))
    id_pointers = tuple(
        f"/grid/variants[{index}]/variant_id"
        for index in range(len(protocol["grid"]["variants"]))
    )
    permitted_changed = set(PERMITTED_CHANGED_POINTERS) | set(id_pointers)
    permitted_added = set(PERMITTED_ADDED_POINTERS)

    removed: list[str] = []
    changed: list[str] = []
    added: list[str] = []
    for block in blocks:
        if block not in attempt_2_protocol:
            raise ConfigViolation(
                f"{block!r} is declared copied from SE100-CFG-3103 but that file has no such block"
            )
        mine = _flatten(protocol[block], f"/{block}")
        theirs = _flatten(attempt_2_protocol[block], f"/{block}")
        removed.extend(sorted(set(theirs) - set(mine)))
        added.extend(sorted(set(mine) - set(theirs)))
        changed.extend(sorted(p for p in set(mine) & set(theirs) if mine[p] != theirs[p]))

    if removed:
        raise ConfigViolation(
            f"CFG-3105 drops {len(removed)} pointer(s) CFG-3103 declares, first {removed[:5]}. A "
            "carried block that lost a field is a mechanic that stopped being declared, which is the "
            "one direction 'copied programmatically' cannot produce."
        )
    unexpected_changed = sorted(set(changed) - permitted_changed)
    if unexpected_changed:
        raise ConfigViolation(
            f"CFG-3105 changes {len(unexpected_changed)} carried pointer(s) outside the declared "
            f"two changes, first {unexpected_changed[:5]}. Attempt 3 changes the ladder and the "
            "selection rule; a third difference makes the result uninterpretable."
        )
    unexpected_added = sorted(set(added) - permitted_added)
    if unexpected_added:
        raise ConfigViolation(
            f"CFG-3105 adds {len(unexpected_added)} carried pointer(s) outside the declared "
            f"provenance notes, first {unexpected_added[:5]}"
        )
    missing_ids = sorted(set(id_pointers) - set(changed))
    if missing_ids:
        raise ConfigViolation(
            f"{len(missing_ids)} variant id(s) are byte-identical to Attempt 2's, first "
            f"{missing_ids[:3]}. Attempt 3's ids encode candidate index C3 and architecture RA3; an "
            "id that did not change would run this attempt under Attempt 2's identity."
        )

    return {
        "blocks_compared": list(blocks),
        "compared_against": str(ATTEMPT_2_PROTOCOL_PATH.name),
        "pointers_removed": removed,
        "pointers_changed": sorted(changed),
        "pointers_added": sorted(added),
        "variant_id_pointers_changed": len(id_pointers),
        "permitted_changed_unused": sorted(permitted_changed - set(changed)),
        "permitted_added_unused": sorted(permitted_added - set(added)),
        "method_as_sealed": node["method"],
        # The measured overstatement, reported rather than raised: every pointer that differs and is
        # not one of the two the sealed sentence names. See G2A3-CONFLICT-39 in the module docstring.
        "method_understates_by": sorted(
            (set(changed) - set(id_pointers) - {"/grid/variant_id_format"}) | set(added)
        ),
        "conflict_ref": "G2A3-CONFLICT-39",
    }


def eligible_universe() -> tuple[str, ...]:
    """The 34 frozen members, sorted. Ranked in full at every scheduled rebalance."""
    return tuple(sorted(load_protocol()["eligible_universe"]["members"]))


# -- sizing --------------------------------------------------------------------------------------

_A_PATTERN = re.compile(r"\bA\s*=\s*([0-9]+(?:\.[0-9]+)?)")
_C_PATTERN = re.compile(r"\bC\s*=\s*([0-9]+(?:\.[0-9]+)?)")


@exact
def target_weight(k: int, costs: CostModel) -> Decimal:
    """``w(k) = min(A / k, C)`` at nine decimal places, ROUND_DOWN, with ``A`` **RA3-1's** ceiling.

    Both fractions come off disk — ``A`` from Attempt 3's risk architecture, ``C`` from the sealed
    concentration ceiling — and the result is checked against CFG-3105's own declared weight *and* its
    declared gross exposure. Checking the gross separately is not redundant: the k=3 weight is one ulp
    short of a third by design, and the declared ``0.499999998`` is the only place that deliberate
    shortfall is written down.

    The sealed sentence names ``A`` as RA2-1's ceiling because ``position_sizing`` is one of the
    thirteen blocks copied from CFG-3103 verbatim. Both constants are parsed back out of it and
    required to equal the two ceilings actually used, so the copied prose cannot describe one
    architecture while the derivation runs on another.
    """
    if k <= 0:
        raise ConfigViolation(f"k={k!r} is not a position count")
    if costs.share_quantum != SCALAR_QUANTUM:
        raise ConfigViolation(
            f"the cost model quantizes shares at {costs.share_quantum} but the seal quantizes the "
            f"weight at {SCALAR_QUANTUM}"
        )

    ceiling = load_risk_architecture_ra3().exposure_ceiling
    per_position = concentration_ceiling()
    weight = min(ceiling / k, per_position)
    weight = weight.quantize(costs.share_quantum, rounding=ROUND_DOWN)

    sizing = load_protocol()["position_sizing"]
    formula = sizing["target_weight_formula"]
    spelled = SPELLED_DECIMALS[SCALAR_DECIMALS]
    if f"{spelled} decimal places" not in formula or "ROUND_DOWN" not in formula:
        raise ConfigViolation(
            f"the sealed weight formula does not quantize to {spelled} decimal places with "
            f"ROUND_DOWN: {formula!r}"
        )
    if sizing.get("changed_from_attempt_1") is not True:
        raise ConfigViolation(
            "the protocol no longer records the sizing rule as changed from Attempt 1, but this "
            "module sizes against RA3-1's ceiling rather than the constitutional one"
        )
    for label, pattern, used in (("A", _A_PATTERN, ceiling), ("C", _C_PATTERN, per_position)):
        match = pattern.search(formula)
        if match is None:
            raise ConfigViolation(
                f"the sealed weight formula does not state a value for {label}: {formula!r}"
            )
        if dec(match.group(1)) != used:
            raise ConfigViolation(
                f"the sealed weight formula states {label} = {match.group(1)} but this derivation "
                f"used {used}. The sentence is CFG-3103's, copied into CFG-3105; RA3-1's ceiling "
                "must equal the one it describes or the copy has stopped being true."
            )

    declared = sizing["target_weights"].get(str(k))
    if declared is None:
        raise ConfigViolation(f"the protocol declares no target weight for k={k}")
    if weight != dec(declared):
        raise ConfigViolation(
            f"w({k}) derives to {weight} from the sealed ceilings but the protocol declares "
            f"{declared}. Refusing to size a position against a weight that disagrees with its own "
            "pre-registration."
        )
    gross = k * weight
    declared_gross = sizing["target_gross_exposure"].get(str(k))
    if declared_gross is None or gross != dec(declared_gross):
        raise ConfigViolation(
            f"{k} * w({k}) = {gross} but the protocol declares target gross {declared_gross!r}"
        )
    if gross > ceiling:
        raise ConfigViolation(
            f"{k} * w({k}) = {gross} exceeds RA3-1's aggregate exposure ceiling {ceiling}"
        )
    return weight


@exact
def attempt_2_weight_agreement() -> dict[str, Any]:
    """Evidence, not a runtime dependency: Attempt 3's weights against Attempt 2's.

    RA3 changes only the de-risk ladder, so the aggregate exposure ceiling — and therefore every
    target weight — should be identical to Attempt 2's. Deliberately not called by
    :func:`target_weight`: Attempt 3's sizing must not depend on Attempt 2's protocol still loading.
    A difference here is reported rather than raised at load time, because the finding would be about
    the seal rather than about this run.
    """
    rows = []
    for k in (1, 2, 3):
        costs = rotation_cost_model(k, BASE)
        mine = target_weight(k, costs)
        theirs = attempt_2.target_weight(k, costs)
        rows.append(
            {
                "top_k": k,
                "attempt_2_weight": f"{theirs:f}",
                "attempt_3_weight": f"{mine:f}",
                "attempt_2_gross": f"{theirs * k:f}",
                "attempt_3_gross": f"{mine * k:f}",
                "identical": theirs == mine,
            }
        )
    return {
        "attempt_3_exposure_ceiling": f"{load_risk_architecture_ra3().exposure_ceiling:f}",
        "rows": rows,
        "all_identical": all(row["identical"] for row in rows),
        "why_identical_is_expected": (
            "RA3 differs from RA2 only in the de-risk ladder. The aggregate exposure ceiling RA3-1 "
            "is RA2-1's value, so w(k) = min(A/k, C) cannot move. A difference here would mean the "
            "single-change claim is false at the sizing level."
        ),
    }


# -- the grid ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RotationVariantRA3:
    """One of the eighteen declared parameterisations. Constructed only from the seal."""

    index: int
    variant_id: str
    lookback_months: int
    top_k: int
    frequency: str
    target_weight: Decimal
    scheduled_rebalance_sessions: int

    def to_json(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "variant_id": self.variant_id,
            "lookback_months": self.lookback_months,
            "top_k": self.top_k,
            "rebalance_frequency": self.frequency,
            "target_weight_per_position": f"{self.target_weight:f}",
            "scheduled_rebalance_sessions": self.scheduled_rebalance_sessions,
        }


@lru_cache(maxsize=1)
def _variant_id_template() -> str:
    """The sealed id format, used as a format string rather than paraphrased into an f-string."""
    template = load_protocol()["grid"]["variant_id_format"]
    if not template.startswith(f"{STRATEGY_ID}-"):
        raise ConfigViolation(
            f"the sealed variant id format {template!r} does not begin with the strategy id "
            f"{STRATEGY_ID!r}"
        )
    if "{lookback:02d}" not in template:
        raise ConfigViolation(
            f"the sealed variant id format {template!r} does not zero-pad the lookback. The final "
            "tiebreak of SE100-G2-SEL-2 is lexicographic, and an unpadded L12 would sort before L3."
        )
    return template


def _variant_id(lookback: int, k: int, frequency: str) -> str:
    variant_id = _variant_id_template().format(lookback=lookback, k=k, FREQUENCY=frequency)
    if f"-L{lookback:02d}-" not in variant_id:
        raise ConfigViolation(f"{variant_id!r} did not zero-pad lookback {lookback}")
    return variant_id


@lru_cache(maxsize=1)
def rotation_variants() -> tuple[RotationVariantRA3, ...]:
    """All eighteen, in the sealed order, rebuilt from the axes and checked against the seal.

    Rebuilding from ``grid.axes`` rather than reading ``grid.variants`` straight through means the
    declared list is *verified* rather than trusted: a variant silently added to or removed from the
    seal shows up as a length or id mismatch here instead of quietly becoming a nineteenth run.
    """
    protocol = load_protocol()
    grid = protocol["grid"]
    axes = grid["axes"]
    declared = {entry["variant_id"]: entry for entry in grid["variants"]}
    built: list[RotationVariantRA3] = []
    index = 0
    for lookback in axes["lookback_months"]:
        for k in axes["top_k"]:
            for frequency in axes["rebalance_frequency"]:
                index += 1
                variant_id = _variant_id(int(lookback), int(k), str(frequency))
                entry = declared.get(variant_id)
                if entry is None:
                    raise ConfigViolation(
                        f"the axes generate {variant_id} but the sealed variant list does not "
                        "contain it"
                    )
                if entry["index"] != index:
                    raise ConfigViolation(
                        f"{variant_id} is declared at index {entry['index']} but the axes place it "
                        f"at {index}; the enumeration order is part of the seal"
                    )
                weight = target_weight(int(k), rotation_cost_model(int(k), BASE))
                if weight != dec(entry["target_weight_per_position"]):
                    raise ConfigViolation(
                        f"{variant_id} declares weight {entry['target_weight_per_position']} but "
                        f"w({k}) is {weight}"
                    )
                built.append(
                    RotationVariantRA3(
                        index=index,
                        variant_id=variant_id,
                        lookback_months=int(lookback),
                        top_k=int(k),
                        frequency=str(frequency),
                        target_weight=weight,
                        scheduled_rebalance_sessions=int(entry["scheduled_rebalance_sessions"]),
                    )
                )

    if len(built) != grid["size"] or len(built) != len(declared):
        raise ConfigViolation(
            f"the axes generate {len(built)} variants against a declared size of {grid['size']} and "
            f"{len(declared)} declared entries. The grid is complete at eighteen and may not be "
            "widened, narrowed, or re-centred."
        )
    return tuple(built)


def variant_by_id(variant_id: str) -> RotationVariantRA3:
    for variant in rotation_variants():
        if variant.variant_id == variant_id:
            return variant
    raise ConfigViolation(f"{variant_id!r} is not one of the eighteen declared variants")


def attempt_2_grid_agreement() -> dict[str, Any]:
    """Evidence for ``grid.unchanged_from_attempt_2``: the axes and parameters really are the same.

    Compares axes and per-variant parameters against Attempt 2's protocol, ignoring the ids — those
    differ by construction. Reporting, not a runtime dependency; the structural version of this claim
    is :func:`check_mechanics_carried_unchanged`, which does raise.
    """
    mine = load_protocol()["grid"]
    theirs = attempt_2.load_protocol()["grid"]
    axes_agree = {
        axis: list(mine["axes"][axis]) == list(theirs["axes"][axis]) for axis in sorted(mine["axes"])
    }
    key = ("index", "lookback_months", "top_k", "rebalance_frequency", "scheduled_rebalance_sessions")
    mine_rows = [tuple(entry[field] for field in key) for entry in mine["variants"]]
    theirs_rows = [tuple(entry[field] for field in key) for entry in theirs["variants"]]
    return {
        "declared_unchanged_from_attempt_2": mine.get("unchanged_from_attempt_2") is True,
        "declared_unchanged_from_attempt_1": mine.get("unchanged_from_attempt_1") is True,
        "axes_agree": axes_agree,
        "all_axes_agree": all(axes_agree.values()),
        "size_agrees": mine["size"] == theirs["size"] == 18,
        "parameter_rows_agree": mine_rows == theirs_rows,
        "compared_fields": list(key),
        "ids_differ_by_construction": {
            "attempt_2": theirs["variants"][0]["variant_id"],
            "attempt_3": mine["variants"][0]["variant_id"],
        },
    }


# -- the candidate -------------------------------------------------------------------------------


def _constructor_assignments(cls: type) -> frozenset[str]:
    """The instance attributes ``cls.__init__`` assigns, read out of that class's own source.

    ``ast.AnnAssign`` is walked as well as ``ast.Assign``: Attempt 2's constructor annotates three of
    its ten assignments, and a walker that saw only plain assignments would under-report the state to
    be mirrored and pass vacuously on exactly the attributes most likely to be forgotten.
    """
    source_file = inspect.getsourcefile(cls)
    if source_file is None:  # pragma: no cover - a source-less import is not a supported layout
        raise ConfigViolation(f"{cls.__name__} has no source file to read its state from")
    tree = ast.parse(pathlib.Path(source_file).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != cls.__name__:
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or item.name != "__init__":
                continue
            names: set[str] = set()
            for statement in ast.walk(item):
                if isinstance(statement, ast.Assign):
                    targets: list[ast.expr] = list(statement.targets)
                elif isinstance(statement, (ast.AnnAssign, ast.AugAssign)):
                    if getattr(statement, "value", None) is None:
                        continue
                    targets = [statement.target]
                else:
                    continue
                for target in targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        names.add(target.attr)
            if not names:
                raise ConfigViolation(
                    f"{cls.__name__}'s constructor assigns no instance attributes; the mirror check "
                    "would pass vacuously"
                )
            return frozenset(names)
    raise ConfigViolation(
        f"no {cls.__name__}.__init__ found in {source_file}; the state this class mirrors cannot be "
        "located"
    )


@lru_cache(maxsize=1)
def _inherited_init_state() -> frozenset[str]:
    """The union of the state Attempt 1's and Attempt 2's constructors set.

    Attempt 2 checked itself against Attempt 1's constructor only. That is not sufficient here:
    Attempt 2's constructor sets attributes Attempt 1's does not (``variant``, ``risk``, ``weight``),
    and this class binds Attempt 2's ``entry_order``, ``exit_order`` and ``evidence``, which reach
    them. Taking the union makes the requirement strictly stronger than either check alone, and
    neither source file is modified to obtain it.
    """
    return _constructor_assignments(RotationCandidate) | _constructor_assignments(
        RotationCandidateRA1
    )


class RotationCandidateRA3(Candidate):
    """Attempt 1's cross-sectional rotation, sized under RA3.

    Every decision method is Attempt 2's function object, which for the first four is Attempt 1's.
    What changes is the risk architecture the engine runs and the id this candidate carries — not one
    line of the signal, the calendar, the sort, the exclusion accounting or the order legs. That is
    the only reason a third attempt on the same window is interpretable at all.
    """

    family = FAMILY

    # Bound explicitly so the reuse is visible at the class body rather than hidden in an MRO. This
    # class descends from Candidate, not from RotationCandidateRA1, because Attempt 2's constructor
    # would load RA2's architecture and stamp its id into the parameters of an RA3 run.
    rank = RotationCandidateRA1.rank
    decide = RotationCandidateRA1.decide
    target = RotationCandidateRA1.target
    ranking_digest = RotationCandidateRA1.ranking_digest
    _base_evidence = RotationCandidateRA1._base_evidence
    entry_order = RotationCandidateRA1.entry_order
    exit_order = RotationCandidateRA1.exit_order
    evidence = RotationCandidateRA1.evidence

    def __init__(
        self,
        variant: RotationVariantRA3,
        costs: CostModel,
        *,
        universe: Sequence[str] | None = None,
    ) -> None:
        risk = load_risk_architecture_ra3()
        super().__init__(
            experiment_id=STRATEGY_ID,
            variant_id=variant.variant_id,
            universe=eligible_universe() if universe is None else universe,
            parameters={
                "lookback_months": variant.lookback_months,
                "top_k": variant.top_k,
                "rebalance_frequency": variant.frequency,
                "target_weight": variant.target_weight,
                "risk_architecture_id": risk.architecture_id,
            },
            costs=costs,
        )
        self.variant = variant
        self.risk = risk
        self.weight = target_weight(variant.top_k, costs)
        if self.weight != variant.target_weight:
            raise ConfigViolation(
                f"{variant.variant_id}: the candidate derived w={self.weight} against the variant's "
                f"{variant.target_weight}"
            )
        if costs.max_open_risky_positions != variant.top_k:
            raise ConfigViolation(
                f"{variant.variant_id}: k={variant.top_k} but the cost model admits "
                f"{costs.max_open_risky_positions} open positions. The weight check above cannot "
                "catch this — neither ceiling in w(k) varies with the cost model's breadth, so a "
                "k=3 variant handed a k=1 model would size every leg correctly and then have its "
                "second and third rejected by the engine's breadth cap, trading a strategy nobody "
                "declared."
            )
        if risk.architecture_id != "RA3":
            raise ConfigViolation(
                f"{variant.variant_id}: the loaded architecture identifies as "
                f"{risk.architecture_id!r}. This candidate is Attempt 3's and runs under RA3."
            )

        self._previous_session: dt.date | None = None
        self._ranking_hash = hashlib.sha256()

        # Evidence, not bookkeeping: every one of these is reported for all eighteen variants.
        self.scheduled_rebalances = 0
        self.executed_rebalances = 0
        self.rebalances_blocked_by_shutdown = 0
        self.exclusions: dict[str, int] = {}
        self.selection_log: list[dict[str, Any]] = []

        missing = sorted(_inherited_init_state() - set(vars(self)))
        if missing:
            raise InvariantViolation(
                f"this constructor mirrors Attempt 1's and Attempt 2's but does not set {missing}, "
                "which one of their constructors does. The bound decide()/rank()/evidence() would "
                "reach it at runtime."
            )


def build_candidate(
    variant: RotationVariantRA3 | str,
    scenario: str = BASE,
    *,
    universe: Sequence[str] | None = None,
) -> RotationCandidateRA3:
    """The one construction path the runner uses, so the cost model is never chosen by hand."""
    resolved = variant_by_id(variant) if isinstance(variant, str) else variant
    costs = rotation_cost_model(resolved.top_k, scenario)
    return RotationCandidateRA3(resolved, costs, universe=universe)


# The reuse chain, asserted rather than described: Attempt 3's decision methods are Attempt 2's
# function objects, and the four Attempt 2 inherited from Attempt 1 are still Attempt 1's. A refactor
# that quietly reimplemented one of them in either module fails here at import.
assert total_return is attempt_1.total_return
assert RotationCandidateRA3.rank is RotationCandidate.rank
assert RotationCandidateRA3.decide is RotationCandidate.decide
assert RotationCandidateRA3.target is RotationCandidate.target
assert RotationCandidateRA3.ranking_digest is RotationCandidate.ranking_digest
assert RotationCandidateRA3._base_evidence is RotationCandidate.evidence
assert RotationCandidateRA3.entry_order is RotationCandidateRA1.entry_order
assert RotationCandidateRA3.exit_order is RotationCandidateRA1.exit_order
assert RotationCandidateRA3.evidence is RotationCandidateRA1.evidence
