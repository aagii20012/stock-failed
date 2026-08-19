"""Gate 3 for Generation 2 Attempt 3: five evaluators reused verbatim, two adapted, one rebuilt.

``config/generation_2/g2_gate_criteria_ra3.json`` (SE100-CFG-3106) states in
``relationship_to_attempt_2_criteria`` that ``thresholds_changed`` is "none", ``predicates_changed``
is "none. All seven predicate strings are character-identical to SE100-CFG-3104's", and
``measurement_basis_changed`` is the empty list. Attempt 3 changes the risk architecture and the
selection rule; it changes nothing about how a condition is measured. This file is the shape of that
claim: it computes as little as possible of its own.

**On importing from the closed attempts.** The operating instruction closes Attempt 1's and Attempt
2's modules to editing, deletion and rerunning. It cannot mean "never call a function defined in
them", because the same instruction's §4.1 requires RA3 to "reuse RA2's exposure/vol-target/stop/
lockout code paths unchanged", which is reachable only by importing them, and CFG-3106's
``episode_ledger_inherited`` requires ``stockedge100.backtest.g2_episodes_ra1`` to be *imported*
rather than copied or subclassed. What is closed is those attempts' experiments and verdicts, not
their vocabulary. Nothing here writes to, reruns, or reopens either attempt; every symbol taken from
``g2_gate_ra1`` is read-only and unmodified, exactly as ``g2_gate_ra1`` itself imports Generation 1's
``gate``.

**What is reused, measured rather than assumed.** ``_scratch/ra3_gate_reuse.py`` walked every
evaluator's AST, resolved the condition each binds ``spec`` to, and checked every dereferenced key
against CFG-3106. Five evaluators — ``condition_1``, ``condition_2``, ``condition_4_ra1``,
``condition_5_ra1`` and ``condition_7``'s count rule — resolve completely against the Attempt 3 seal
and are called with the sealed criteria object itself, unmodified.

**What is adapted, and why an adapter rather than a copy.** CFG-3106 renames two *prose* fields that
two frozen evaluators dereference by literal name:

===============================================  ==========================  ====================
sealed pointer in CFG-3104                       renamed in CFG-3106 to      read at
===============================================  ==========================  ====================
``S3-C3.attempt_2_note``                         ``attempt_3_note``          ``g2_gate_ra1.py:432``
``S3-C6.scope_interpretation.``                  ``attempt_3_significance``  ``g2_gate_ra1.py:738``
``attempt_2_significance``
===============================================  ==========================  ====================

Neither participates in a predicate, a threshold or a verdict — both are evidence prose. Copying
``condition_3_ra1`` and ``condition_6_ra1`` forward to change two string literals would put two
implementations of a *gating* predicate in the tree, differing in nothing that gates, which is the
failure ``g2_gate_ra1``'s own docstring warns about: reused "so the implementations cannot drift
apart in a detail nobody is watching". So the evaluators are called unmodified against a view of the
criteria that binds the old names to the new values, and
:func:`check_prose_alias_adapter` proves the view differs from the seal in exactly those two
pointers, that both aliases carry byte-identical values to their RA3 originals, and that the sealed
object itself is unmutated. ``G2A3-CONFLICT-40``.

**What is rebuilt.** ``condition_7``'s neighbour *set* — Attempt 2's ``neighbours_of`` resolves
against ``g2_rotation_ra1``'s grid, so an RA3 representative would be compared against Attempt 2's
variant ids and raise. CFG-3106's S3-C7 ``measurement.shared_with_selection`` says of the neighbour
relation that "one implementation serves both", so the set comes from
:func:`~stockedge100.strategies.g2_selection_v2.neighbours_of` — the same function SE100-G2-SEL-2
averages its stability score over — while the *count* rule is still Attempt 2's
``expected_neighbour_count``, which reads only CFG-3106's ``axis_orderings`` and the variant's own
axis values and is therefore grid-independent. The set is derived from CFG-3105 and the count from
CFG-3106; requiring them to agree is a check across two seals rather than a restatement of one.

``build_plan`` and ``stage_verdict`` are rebuilt because they read Attempt 2's protocol, Attempt 2's
risk architecture, and a ``verdict_token_derivation`` key CFG-3106 renames — see
:func:`build_plan_ra3` and :func:`stage_verdict_ra3`.

Every threshold, token, axis ordering, digest and predicate below is read from a sealed file. No
token string and no digest is written as a literal here.
"""

from __future__ import annotations

import ast
import copy
import datetime as dt
import json
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any, Sequence

from stockedge100.audit import sha256_bytes, sha256_file
from stockedge100.backtest.config import PROJECT_ROOT
from stockedge100.backtest.costs import exact
from stockedge100.backtest.engine import BacktestResult
from stockedge100.backtest.errors import ConfigViolation

# Imported, never copied and never subclassed — CFG-3106's ``episode_ledger_inherited``.
from stockedge100.backtest.g2_episodes_ra1 import EpisodeLedger, build_episode_ledger

# Generation 1's evaluator, through the same door Attempt 2 used. ``condition_1`` and ``condition_2``
# read the engine's own equity curve, which is exact whether or not a position was trimmed, so the
# episode ledger does not reach them and CFG-3106 records both as unchanged in measurement basis.
from stockedge100.strategies.gate import (
    MET,
    NOT_APPLICABLE,
    NOT_EVALUABLE,
    NOT_MET,
    ConditionVerdict,
    _condition,
    _sign,
    check_thresholds_against_seal,
    condition_1,
    condition_2,
)

# Attempt 2's evaluator. Read-only: nothing below assigns to any of these, and none of them is
# rerun in Attempt 2's own configuration — each is called with Attempt 3's sealed criteria.
from stockedge100.strategies.g2_gate_ra1 import (
    AXIS_NAMES,
    assert_reconciliation_non_vacuous,
    condition_3_ra1,
    condition_4_ra1,
    condition_5_ra1,
    condition_6_ra1,
    expected_neighbour_count,
)

from stockedge100.backtest.g2_engine_ra3 import load_risk_architecture_ra3
from stockedge100.strategies import g2_selection_v2
from stockedge100.strategies.g2_rotation_ra3 import (
    STRATEGY_ID,
    RotationCandidateRA3,
    RotationVariantRA3,
    _flatten,
    eligible_universe,
    load_protocol,
    variant_by_id,
)

__all__ = [
    "ATTEMPT_1_COUNTERPART_REL",
    "ATTEMPT_2_COUNTERPART_REL",
    "CRITERIA_ID",
    "CRITERIA_PATH",
    "GENERATION_1_COUNTERPART_REL",
    "PROSE_ALIASES",
    "G2PlanRA3",
    "adapted_criteria_for_frozen_prose",
    "build_plan_ra3",
    "check_prose_alias_adapter",
    "condition_3_ra3",
    "condition_6_ra3",
    "condition_7_ra3",
    "evaluate_representative_ra3",
    "load_criteria_ra3",
    "neighbours_of_ra3",
    "prior_attempt_tokens",
    "stage_verdict_ra3",
]

CRITERIA_PATH = PROJECT_ROOT / "config" / "generation_2" / "g2_gate_criteria_ra3.json"
CRITERIA_ID = "SE100-CFG-3106"

#: The three closed criteria files CFG-3106 pins by digest. Attempt 3 has *two* closed predecessors
#: where Attempt 2 had one, so there are three counterparts to recompute and four tokens to withhold.
#: Every path is read; none is written.
GENERATION_1_COUNTERPART_REL = "config/stage3_gate_criteria.json"
ATTEMPT_1_COUNTERPART_REL = "config/generation_2/g2_gate_criteria.json"
ATTEMPT_2_COUNTERPART_REL = "config/generation_2/g2_gate_criteria_ra1.json"

#: ``(condition id, pointer within the condition, name CFG-3104 used, name CFG-3106 uses)``.
#: The two prose fields renamed between the seals, and the whole of ``G2A3-CONFLICT-40``. Both are
#: evidence text; neither is read by any predicate. Verified exhaustive by
#: :func:`check_prose_alias_adapter`, which rejects any *other* difference between the sealed
#: criteria and the adapted view.
PROSE_ALIASES = (
    ("S3-C3", (), "attempt_2_note", "attempt_3_note"),
    ("S3-C6", ("scope_interpretation",), "attempt_2_significance", "attempt_3_significance"),
)

CONFLICT_PROSE_RENAME = "G2A3-CONFLICT-40"
CONFLICT_NEIGHBOUR_COUNT = "G2A3-CONFLICT-27"


# -- the seal ------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_criteria_ra3() -> dict[str, Any]:
    """The sealed Gate 3 criteria for Attempt 3, refusing to load anything that is not them.

    Same ordering discipline as Attempt 2's loader: the threshold seal check runs *inside* the
    loader, so the criteria cannot be obtained without it having passed and there is no code path
    that reaches a condition with an unchecked seal. Three counterpart digests are recomputed rather
    than two, because Attempt 3 stands behind two closed attempts.
    """

    criteria = json.loads(CRITERIA_PATH.read_text(encoding="utf-8"))
    if criteria.get("artifact_id") != CRITERIA_ID:
        raise ConfigViolation(
            f"{CRITERIA_PATH} carries artifact_id {criteria.get('artifact_id')!r}, not {CRITERIA_ID!r}"
        )
    if criteria.get("generation") != 2 or criteria.get("stage") != 3 or criteria.get("attempt") != 3:
        raise ConfigViolation(
            f"{CRITERIA_ID} is generation {criteria.get('generation')!r} stage "
            f"{criteria.get('stage')!r} attempt {criteria.get('attempt')!r}; this evaluator is "
            "Generation 2 Stage 3 Attempt 3 only"
        )
    if criteria.get("declared_before_any_strategy_code") is not True:
        raise ConfigViolation(
            f"{CRITERIA_ID} does not assert declared_before_any_strategy_code; a gate that was not "
            "declared before results is not a gate"
        )
    _check_counterpart(criteria, "generation_1_counterpart", GENERATION_1_COUNTERPART_REL)
    _check_counterpart(criteria, "attempt_1_counterpart", ATTEMPT_1_COUNTERPART_REL)
    _check_counterpart(criteria, "attempt_2_counterpart", ATTEMPT_2_COUNTERPART_REL)
    check_thresholds_against_seal(criteria)
    _check_axes_agree(criteria)
    _check_tokens_are_attempt_3s_own(criteria)
    _check_prose_renames_are_as_declared(criteria)
    return criteria


def _check_counterpart(criteria: dict[str, Any], key: str, relative: str) -> None:
    """A counterpart named by the seal must exist at that path and hash to the pinned digest.

    All three counterparts are frozen — Generation 1's by its Stage 3 and Stage 4 checksum records,
    Attempt 1's and Attempt 2's by their own governance records — so a mismatch is something to
    report as a blocker, never something to reconcile.
    """

    declared = criteria.get(key, "")
    if relative not in declared:
        raise ConfigViolation(f"{CRITERIA_ID} names {key} {declared!r}, which is not {relative!r}")
    measured = sha256_file(PROJECT_ROOT / relative)
    pinned = criteria[f"{key}_sha256"]
    if measured != pinned:
        raise ConfigViolation(
            f"{relative} hashes to {measured}, but {CRITERIA_ID} pins {pinned}; that file is frozen, "
            "so report this rather than reconciling it"
        )


def _check_axes_agree(criteria: dict[str, Any]) -> None:
    """S3-C7's ``axis_orderings`` and CFG-3105's ``grid.axes`` must be the same three axes.

    Attempt 3 leans on this harder than Attempt 2 did. The neighbour set now comes from CFG-3105 via
    :mod:`~stockedge100.strategies.g2_selection_v2` and the neighbour count from CFG-3106; if the two
    files' axis orderings disagreed, the selection rule and the gate would be reasoning about
    different grids and the disagreement would surface as an arithmetic error rather than a seal
    conflict.
    """

    orderings = _condition(criteria, "S3-C7")["measurement"]["axis_orderings"]
    axes = load_protocol()["grid"]["axes"]
    if tuple(sorted(orderings)) != tuple(sorted(AXIS_NAMES)) or tuple(sorted(axes)) != tuple(
        sorted(AXIS_NAMES)
    ):
        raise ConfigViolation(
            f"axis names differ: criteria {sorted(orderings)}, protocol {sorted(axes)}, "
            f"expected {sorted(AXIS_NAMES)}"
        )
    for axis in AXIS_NAMES:
        if list(orderings[axis]) != list(axes[axis]):
            raise ConfigViolation(
                f"axis {axis!r} is ordered {orderings[axis]!r} in {CRITERIA_ID} and {axes[axis]!r} "
                "in CFG-3105; the two seals disagree"
            )


@lru_cache(maxsize=1)
def prior_attempt_tokens() -> tuple[str, ...]:
    """The four verdict tokens belonging to the two closed attempts, read from their own files.

    CFG-3106's prose names all four. Rather than restate them here, they are read from the two files
    that *define* them — whose digests :func:`_check_counterpart` has already recomputed against the
    pins — and the prose is then checked to name every one. Two files agreeing is evidence; one file
    quoting itself is not.

    Order is Attempt 1's pair then Attempt 2's, which is the order the prose states them in.
    """

    tokens: list[str] = []
    for relative in (ATTEMPT_1_COUNTERPART_REL, ATTEMPT_2_COUNTERPART_REL):
        derivation = json.loads((PROJECT_ROOT / relative).read_text(encoding="utf-8"))[
            "verdict_token_derivation"
        ]
        tokens += [derivation["pass_token"], derivation["fail_token"]]
    if len(set(tokens)) != 4:
        raise ConfigViolation(
            f"the two closed attempts declare {sorted(set(tokens))}, which is not four distinct "
            "tokens; two attempts sharing a token would make a verdict unattributable"
        )
    return tuple(tokens)


def _check_tokens_are_attempt_3s_own(criteria: dict[str, Any]) -> None:
    """Attempt 3's two tokens must be Attempt 3's, and must not be either closed attempt's.

    A criteria file copied forward and edited incompletely would be caught nowhere else: every
    threshold, predicate and axis would check out, and the stage would emit a token belonging to an
    attempt that is closed. CFG-3106 renames Attempt 2's ``attempt_1_tokens_are_not_available_here``
    to ``prior_attempt_tokens_are_not_available_here`` precisely because there are now two prior
    attempts to name, which is why ``stage_verdict_ra1`` cannot be reused.
    """

    derivation = criteria["verdict_token_derivation"]
    ours = (derivation["pass_token"], derivation["fail_token"])
    if ours[0] == ours[1]:
        raise ConfigViolation(f"{CRITERIA_ID} declares the same token {ours[0]!r} for pass and fail")
    theirs = prior_attempt_tokens()
    collisions = sorted(set(ours) & set(theirs))
    if collisions:
        raise ConfigViolation(
            f"{CRITERIA_ID} declares verdict tokens {ours} which collide with {collisions} belonging "
            "to a closed attempt; Attempts 1 and 2 are closed and their tokens are not available here"
        )
    prose = derivation["prior_attempt_tokens_are_not_available_here"]
    for token in theirs:
        if token not in prose:
            raise ConfigViolation(
                f"{CRITERIA_ID} does not name the closed token {token!r} in "
                "prior_attempt_tokens_are_not_available_here, so the seals do not agree about which "
                "tokens are withheld"
            )


def _check_prose_renames_are_as_declared(criteria: dict[str, Any]) -> None:
    """Every pointer in :data:`PROSE_ALIASES` must be absent under its old name and present under
    the new one.

    The adapter below binds the old names to the new values. If CFG-3106 ever carried *both* names,
    the adapter would silently overwrite a sealed field instead of supplying a missing one, and the
    evaluator would read a value the seal did not intend. Checking for the old name's absence is
    what makes the alias an alias rather than an override.
    """

    for condition_id, path, old, new in PROSE_ALIASES:
        node = _condition(criteria, condition_id)
        for part in path:
            node = node[part]
        where = f"{condition_id}{''.join('.' + p for p in path)}"
        if new not in node:
            raise ConfigViolation(
                f"{CRITERIA_ID} {where} does not carry {new!r}; the Attempt 3 evaluator supplies "
                f"{old!r} from it and has nothing to supply it from"
            )
        if old in node:
            raise ConfigViolation(
                f"{CRITERIA_ID} {where} carries both {old!r} and {new!r}; aliasing the former onto "
                "the latter would overwrite a sealed field rather than supply a missing one"
            )
        if not isinstance(node[new], str) or not node[new].strip():
            raise ConfigViolation(f"{CRITERIA_ID} {where}.{new} is not non-empty prose")

    declared = frozenset((cid, tuple(path) + (old,)) for cid, path, old, _ in PROSE_ALIASES)
    derived = _derived_alias_pointers()
    if declared != derived:
        raise ConfigViolation(
            f"PROSE_ALIASES declares {sorted(declared)} but the two sealed files and the frozen "
            f"evaluator's own source derive {sorted(derived)}; {CONFLICT_PROSE_RENAME} covers exactly "
            "the renamed fields the frozen evaluators dereference, and this table may not be widened "
            "by hand"
        )


def _subscript_chain(node: ast.AST) -> list[str] | None:
    """``['spec', 'scope_interpretation', 'attempt_2_significance']`` for a chain of literal keys."""

    parts: list[str] = []
    while isinstance(node, ast.Subscript):
        key = node.slice
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            return None
        parts.append(key.value)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    return [node.id] + list(reversed(parts))


@lru_cache(maxsize=1)
def _keys_the_frozen_evaluators_read() -> frozenset[tuple[str, tuple[str, ...]]]:
    """``(condition id, key path)`` for every sealed field Attempt 2's evaluators dereference.

    Read out of ``g2_gate_ra1.py``'s AST rather than listed here. Each evaluator binds ``spec`` from
    one ``_condition(criteria, "S3-CN")`` call, which is what attributes a read to a condition; a
    flat scan of the file conflates the seven and cannot say which condition a key belongs to.

    The file is frozen, so this cannot drift — but deriving it is what makes
    :data:`PROSE_ALIASES` a measurement rather than an assertion.
    """

    source = PROJECT_ROOT / "src" / "stockedge100" / "strategies" / "g2_gate_ra1.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    reads: set[tuple[str, tuple[str, ...]]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        condition_id = None
        for call in [n for n in ast.walk(node) if isinstance(n, ast.Call)]:
            if (
                isinstance(call.func, ast.Name)
                and call.func.id == "_condition"
                and len(call.args) == 2
                and isinstance(call.args[1], ast.Constant)
                and isinstance(call.args[1].value, str)
            ):
                condition_id = call.args[1].value
        if condition_id is None:
            continue
        for sub in [n for n in ast.walk(node) if isinstance(n, ast.Subscript)]:
            chain = _subscript_chain(sub)
            if chain and chain[0] == "spec" and len(chain) > 1:
                reads.add((condition_id, tuple(chain[1:])))
    if not reads:
        raise ConfigViolation(
            "no sealed key reads were recovered from g2_gate_ra1.py; a predicate that compares "
            "against an empty set passes vacuously and would make the alias table unchecked"
        )
    return frozenset(reads)


@lru_cache(maxsize=1)
def _pointers_dropped_since_attempt_2() -> frozenset[tuple[str, tuple[str, ...]]]:
    """``(condition id, key path)`` present in CFG-3104's conditions and absent from CFG-3106's.

    Both files are read straight from disk rather than through :func:`load_criteria_ra3`, which calls
    this — and reading independently is the point anyway: the expectation for the alias diff must not
    come from the same object the adapter is built from.
    """

    def by_condition(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            condition["id"]: _flatten(condition)
            for condition in document["conditions"]
        }

    old = by_condition(
        json.loads((PROJECT_ROOT / ATTEMPT_2_COUNTERPART_REL).read_text(encoding="utf-8"))
    )
    new = by_condition(json.loads(CRITERIA_PATH.read_text(encoding="utf-8")))
    dropped: set[tuple[str, tuple[str, ...]]] = set()
    for condition_id, pointers in old.items():
        for pointer in set(pointers) - set(new.get(condition_id, {})):
            dropped.add((condition_id, tuple(pointer.lstrip("/").split("/"))))
    if not dropped:
        raise ConfigViolation(
            "CFG-3104 and CFG-3106 differ in no condition-level key, so the rename this adapter "
            "exists for is not in the files; that predicate would pass vacuously"
        )
    return frozenset(dropped)


@lru_cache(maxsize=1)
def _derived_alias_pointers() -> frozenset[tuple[str, tuple[str, ...]]]:
    """The alias set, derived: renamed between the seals **and** read by a frozen evaluator.

    CFG-3106 renames nine condition-level fields; seven of them (the ``attempt_2_status`` family) no
    evaluator dereferences, so aliasing them would be dead work that widened the adapter's reach for
    nothing. The intersection is what :data:`PROSE_ALIASES` must equal.
    """

    return _pointers_dropped_since_attempt_2() & _keys_the_frozen_evaluators_read()


# -- G2A3-CONFLICT-40, the prose alias adapter ---------------------------------------------------


def adapted_criteria_for_frozen_prose(criteria: dict[str, Any]) -> dict[str, Any]:
    """A deep copy of the sealed criteria with the two renamed prose fields bound to both names.

    Used only by :func:`condition_3_ra3` and :func:`condition_6_ra3`. The other five evaluators are
    called with the sealed object itself — narrowing the adapter's blast radius to the two conditions
    that need it is most of what makes it safe, and :func:`check_prose_alias_adapter` measures the
    rest.

    A deep copy, not a shallow one: ``load_criteria_ra3`` is ``lru_cache``d, so every caller in the
    process shares one object, and a shallow copy would reach the same nested condition dicts and
    mutate the seal in memory for everyone.
    """

    adapted = copy.deepcopy(criteria)
    for condition_id, path, old, new in PROSE_ALIASES:
        node = _condition(adapted, condition_id)
        for part in path:
            node = node[part]
        node[old] = node[new]
    return adapted


def check_prose_alias_adapter(criteria: dict[str, Any] | None = None) -> dict[str, Any]:
    """Prove the adapted view differs from the seal in exactly the declared pointers, and nowhere else.

    Three claims, each measured rather than argued:

    1. the adapted view *adds* exactly the two aliased pointers and changes or removes nothing;
    2. each alias carries a value identical to the RA3 field it was taken from — the adapter invents
       no prose, and in particular does not carry Attempt 2's wording forward into Attempt 3;
    3. the sealed object is byte-identical after the adaptation, so nothing else in the process sees
       a mutated seal.

    An adapter that only ever adds keys is still not self-evidently safe; the diff is what makes it
    checkable rather than argued.
    """

    criteria = load_criteria_ra3() if criteria is None else criteria
    before = json.dumps(criteria, sort_keys=True, ensure_ascii=False)
    adapted = adapted_criteria_for_frozen_prose(criteria)
    after = json.dumps(criteria, sort_keys=True, ensure_ascii=False)
    if before != after:
        raise ConfigViolation(
            "adapting the criteria mutated the sealed object; the copy is not deep enough"
        )

    flat_sealed = _flatten(criteria)
    flat_adapted = _flatten(adapted)
    added = sorted(set(flat_adapted) - set(flat_sealed))
    removed = sorted(set(flat_sealed) - set(flat_adapted))
    changed = sorted(
        pointer
        for pointer in set(flat_sealed) & set(flat_adapted)
        if flat_sealed[pointer] != flat_adapted[pointer]
    )

    # The diff assertion runs before any evidence is assembled. Assembling first would let an
    # incidental KeyError inside the evidence rows raise on exactly the inputs the diff exists to
    # reject, and a guard that is shadowed by an accident is not a guard.
    located: list[tuple[str, tuple[str, ...], str, str, int, str]] = []
    for index, condition in enumerate(criteria["conditions"]):
        for condition_id, path, old, new in PROSE_ALIASES:
            if condition["id"] != condition_id:
                continue
            stem = f"/conditions[{index}]" + "".join(f"/{part}" for part in path)
            located.append((condition_id, tuple(path), old, new, index, f"{stem}/{old}"))
    expected_added = [entry[5] for entry in located]

    if added != sorted(expected_added):
        raise ConfigViolation(
            f"the adapted criteria added {added}, not the declared {sorted(expected_added)}; "
            f"{CONFLICT_PROSE_RENAME} declares exactly two aliased pointers"
        )
    if removed or changed:
        raise ConfigViolation(
            f"the adapted criteria removed {removed} and changed {changed}; an alias adapter may "
            "only add"
        )

    aliases: list[dict[str, Any]] = []
    for condition_id, path, old, new, index, pointer in located:
        node = criteria["conditions"][index]
        for part in path:
            node = node[part]
        aliases.append(
            {
                "condition": condition_id,
                "sealed_field": new,
                "alias_supplied": old,
                "pointer": pointer,
                "values_identical": _alias_value(adapted, index, path, old) == node[new],
                "value_sha256_prefix": sha256_bytes(node[new].encode("utf-8"))[:16],
                "read_by": _READ_SITES.get(condition_id, "<no read site recorded>"),
            }
        )
    for alias in aliases:
        if alias["values_identical"] is not True:
            raise ConfigViolation(
                f"alias {alias['pointer']} does not carry the value of {alias['sealed_field']}; the "
                "adapter is inventing prose"
            )

    return {
        "conflict_id": CONFLICT_PROSE_RENAME,
        "criteria_id": CRITERIA_ID,
        "pointers_added": added,
        "pointers_changed": changed,
        "pointers_removed": removed,
        "sealed_object_unmutated": True,
        "conditions_using_the_adapter": sorted({alias["condition"] for alias in aliases}),
        "conditions_using_the_seal_directly": sorted(
            condition["id"]
            for condition in criteria["conditions"]
            if condition["id"] not in {alias["condition"] for alias in aliases}
        ),
        "aliases": aliases,
        "affects_a_predicate": False,
        "affects_a_threshold": False,
        "affects_a_verdict": False,
    }


_READ_SITES = {
    "S3-C3": "g2_gate_ra1.py:432, inside condition_3_ra1's evidence['reconciliation']['note']",
    "S3-C6": "g2_gate_ra1.py:738, inside condition_6_ra1's evidence['attempt_2_significance']",
}


def _alias_value(adapted: dict[str, Any], index: int, path: Sequence[str], old: str) -> Any:
    node = adapted["conditions"][index]
    for part in path:
        node = node[part]
    return node[old]


# -- the plan S3-C6's applicability is decided from ----------------------------------------------


@dataclass(frozen=True)
class G2PlanRA3:
    """What S3-C6 and the result header read off a plan.

    Structurally Attempt 2's ``G2PlanRA1`` with one field added. ``condition_6_ra1`` reads exactly
    one attribute of the plan it is handed — ``declared_universe`` — so this is duck-compatible with
    it by measurement rather than by inheritance; subclassing Attempt 2's plan would have coupled
    Attempt 3's header to a frozen dataclass for no gain.

    The added field is CFG-3105's ``run_span.reverification_required``, which is new in Attempt 3 and
    says the carried span "must not be assumed". Carrying it on the plan is what makes the
    requirement travel with the object the runner and the report both read.
    """

    experiment_id: str
    family: str
    declared_universe: tuple[str, ...]
    run_start: dt.date
    run_end: dt.date
    binding_symbol: str
    sessions: int
    span_recheck_requirement: str
    span_reverification_requirement: str
    risk_architecture_id: str

    def to_json(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "family": self.family,
            "declared_universe": list(self.declared_universe),
            "declared_instrument_count": len(self.declared_universe),
            "run_start": self.run_start.isoformat(),
            "run_end": self.run_end.isoformat(),
            "binding_symbol": self.binding_symbol,
            "sessions": self.sessions,
            "span_recheck_requirement": self.span_recheck_requirement,
            "span_reverification_requirement": self.span_reverification_requirement,
            "risk_architecture_id": self.risk_architecture_id,
        }


@lru_cache(maxsize=1)
def build_plan_ra3() -> G2PlanRA3:
    """The declared plan, entirely from CFG-3105 and the RA3 risk architecture.

    Not reused from Attempt 2: ``build_plan`` reads Attempt 2's protocol and calls Attempt 2's
    ``load_risk_architecture``, so it would build a plan claiming ``RA2`` for an Attempt 3 run.

    The span here is the *declared* one. It is carried from Attempt 2 and CFG-3105 states it must not
    be assumed — the runner recomputes it from the loaded data and asserts equality against these
    values before the first variant runs. This function is therefore the claim, not the check.
    """

    run = load_protocol()["run_span"]
    architecture = load_risk_architecture_ra3()
    if architecture.architecture_id != "RA3":
        raise ConfigViolation(
            f"the plan resolved risk architecture {architecture.architecture_id!r}, not 'RA3'; "
            "Attempt 3 evaluates RA3 and nothing else"
        )
    return G2PlanRA3(
        experiment_id=STRATEGY_ID,
        family=RotationCandidateRA3.family,
        declared_universe=eligible_universe(),
        run_start=dt.date.fromisoformat(run["run_start"]),
        run_end=dt.date.fromisoformat(run["run_end"]),
        binding_symbol=run["binding_symbol"],
        sessions=int(run["sessions"]),
        span_recheck_requirement=run["recheck_requirement"],
        span_reverification_requirement=run["reverification_required"],
        risk_architecture_id=architecture.architecture_id,
    )


# -- the two adapted conditions ------------------------------------------------------------------


def condition_3_ra3(
    result: BacktestResult, ledger: EpisodeLedger, criteria: dict[str, Any]
) -> ConditionVerdict:
    """S3-C3 by Attempt 2's evaluator, against Attempt 3's seal.

    The only difference from calling ``condition_3_ra1`` directly is the prose alias — the evaluator
    writes ``spec["attempt_2_note"]`` into ``evidence["reconciliation"]["note"]``, and under
    CFG-3106 that field is ``attempt_3_note``. The evidence key is ``note``, so no Attempt 2 name
    reaches the output; only the *lookup* is aliased. The source field is recorded beside the prose
    so a reader of the decision record does not have to work out which sealed field it came from.
    """

    verdict = condition_3_ra1(result, ledger, adapted_criteria_for_frozen_prose(criteria))
    evidence = dict(verdict.evidence)
    reconciliation = dict(evidence.get("reconciliation", {}))
    reconciliation["note_source_key"] = "attempt_3_note"
    reconciliation["note_source_conflict"] = CONFLICT_PROSE_RENAME
    evidence["reconciliation"] = reconciliation
    return replace(verdict, evidence=evidence)


def condition_6_ra3(
    result: BacktestResult, ledger: EpisodeLedger, plan: G2PlanRA3, criteria: dict[str, Any]
) -> ConditionVerdict:
    """S3-C6 by Attempt 2's evaluator, against Attempt 3's seal, with one evidence key relabelled.

    Unlike S3-C3, here the Attempt 2 name reaches the *output*: the evaluator writes
    ``evidence["attempt_2_significance"]``. Left alone, Attempt 3's decision record would carry
    CFG-3106's own prose — which is about Attempt 3, and says so — under a key naming Attempt 2. So
    the key is renamed on the way out.

    The relabel is conditional because the write is: ``condition_6_ra1`` returns NOT_EVALUABLE before
    reaching that line when total P&L is non-positive, and a relabel that assumed the key was present
    would turn a legitimate NOT_EVALUABLE into a ``KeyError``.
    """

    verdict = condition_6_ra1(result, ledger, plan, adapted_criteria_for_frozen_prose(criteria))
    if "attempt_2_significance" not in verdict.evidence:
        return verdict
    evidence = dict(verdict.evidence)
    evidence["attempt_3_significance"] = evidence.pop("attempt_2_significance")
    evidence["significance_key_conflict"] = CONFLICT_PROSE_RENAME
    return replace(verdict, evidence=evidence)


# -- S3-C7, on the Attempt 3 grid, sharing SEL-2's neighbour relation ----------------------------


def neighbours_of_ra3(
    variant: RotationVariantRA3, criteria: dict[str, Any]
) -> tuple[RotationVariantRA3, ...]:
    """The representative's one-step neighbours, from the same function SEL-2 scores over.

    CFG-3106's S3-C7 ``measurement.shared_with_selection``: "SE100-G2-SEL-2 averages its stability
    score over this same neighbour set, computed by this same rule from these same axis_orderings.
    One implementation serves both". So the set is
    :func:`~stockedge100.strategies.g2_selection_v2.neighbours_of` and not a second enumeration —
    two enumerations of one sealed relation is the arrangement in which the gate and the selection
    rule can quietly disagree about what a neighbourhood is.

    The *count* is still checked by Attempt 2's ``expected_neighbour_count``, which derives it from
    CFG-3106's ``axis_orderings`` and the variant's own axis values and never touches a grid. The set
    therefore comes from CFG-3105 and the count from CFG-3106, and they are required to agree.

    ``G2A3-CONFLICT-27``: the Attempt 3 operating instruction states 2, 3 and 4 for the corner, edge
    and interior cases. Those counts omit the rebalance-frequency axis, which contributes exactly one
    neighbour to every variant. The sealed counts — 3, 4 and 5 — govern, and are what is asserted.
    """

    found = tuple(variant_by_id(member) for member in g2_selection_v2.neighbours_of(variant.variant_id))
    expected = expected_neighbour_count(variant, criteria)
    if len(found) != expected or not 3 <= len(found) <= 5:
        raise ConfigViolation(
            f"{variant.variant_id} has {len(found)} one-step neighbours by CFG-3105's relation, but "
            f"CFG-3106's count rule gives {expected}; the two seals disagree about the neighbourhood"
        )
    if variant in found or len({member.variant_id for member in found}) != len(found):
        raise ConfigViolation(
            f"neighbour set of {variant.variant_id} is not a set of distinct other variants"
        )
    return tuple(sorted(found, key=lambda member: member.index))


def _axis_values(variant: RotationVariantRA3) -> dict[str, Any]:
    return {
        "lookback_months": variant.lookback_months,
        "top_k": variant.top_k,
        "rebalance_frequency": variant.frequency,
    }


@exact
def condition_7_ra3(
    primary: BacktestResult,
    neighbours: Sequence[tuple[RotationVariantRA3, BacktestResult | None]],
    criteria: dict[str, Any],
    *,
    variant: RotationVariantRA3,
) -> ConditionVerdict:
    """"reasonable neighboring parameter values do not reverse the sign of net return".

    Structurally identical to Attempt 2's ``condition_7_ra1`` — an identical condition computing a
    different answer would be the defect — differing only in where the neighbour set comes from.

    "zero matches nothing", so a neighbour or a representative that lands exactly flat fails the
    condition rather than being counted as agreeing with everything. A neighbour that did not run is
    NOT_RUN, which the seal states is not a pass.

    The supplied neighbour set is checked against the set this representative's grid position
    requires — passing a hand-picked subset would turn a structural condition into a chosen one. Each
    neighbour is read for the sign of its base-run equity-curve total return and nothing else, and no
    neighbour is ever promoted to representative (``selection_prohibition``).

    Per ``G2A3-CONFLICT-22`` and the seal's ``risk_constants_have_no_neighbours``, the five RA3
    constants are identical across all eighteen variants and are not gridded. A MET verdict here says
    nothing whatever about the robustness of the risk architecture — which, for an attempt whose
    entire disclosed change is to that architecture, is the single most important thing this
    condition does not establish.
    """

    spec = _condition(criteria, "S3-C7")
    required = neighbours_of_ra3(variant, criteria)
    supplied = tuple(sorted(member.variant_id for member, _ in neighbours))
    if supplied != tuple(sorted(member.variant_id for member in required)):
        raise ConfigViolation(
            f"S3-C7 was given neighbours {list(supplied)} for {variant.variant_id}, but its grid "
            f"position requires {[member.variant_id for member in required]}"
        )

    primary_return = primary.total_return()
    primary_sign = _sign(primary_return)
    rows: list[dict[str, Any]] = []
    not_run: list[str] = []
    all_match = True
    for member, result in sorted(neighbours, key=lambda pair: pair[0].index):
        row: dict[str, Any] = {
            "variant_id": member.variant_id,
            "grid_index": member.index,
            "parameters": _axis_values(member),
        }
        if result is None:
            row.update(
                {"status": "NOT_RUN", "total_return": None, "sign": None, "matches_primary": False}
            )
            not_run.append(member.variant_id)
            all_match = False
        else:
            neighbour_return = result.total_return()
            neighbour_sign = _sign(neighbour_return)
            matches = neighbour_sign == primary_sign and neighbour_sign != 0
            all_match = all_match and matches
            row.update(
                {
                    "status": "RUN",
                    "total_return": f"{neighbour_return:f}",
                    "sign": neighbour_sign,
                    "matches_primary": matches,
                }
            )
        rows.append(row)

    matched = sum(1 for row in rows if row["matches_primary"])
    return ConditionVerdict(
        spec["id"],
        spec["required_verbatim"],
        MET if all_match else NOT_MET,
        measured=f"{matched}/{len(rows)} neighbours match",
        threshold=f"all {len(rows)} match, zero matches nothing",
        note=(
            spec["selection_prohibition"]
            if not not_run
            else spec["not_evaluable_treatment"] + " " + spec["selection_prohibition"]
        ),
        evidence={
            "neighbour_definition": spec["measurement"]["neighbour_definition"],
            "neighbour_count": len(rows),
            "neighbour_count_rule": spec["measurement"]["neighbour_count"],
            "neighbour_count_conflict": spec["measurement"]["neighbour_count_conflict"],
            "neighbour_count_conflict_id": CONFLICT_NEIGHBOUR_COUNT,
            "shared_with_selection": spec["measurement"]["shared_with_selection"],
            "neighbour_set_source": "stockedge100.strategies.g2_selection_v2.neighbours_of",
            "neighbour_count_source": "stockedge100.strategies.g2_gate_ra1.expected_neighbour_count",
            "one_step_note": spec["measurement"]["one_step_note"],
            "representative_variant_id": variant.variant_id,
            "representative_grid_index": variant.index,
            "primary_total_return": f"{primary_return:f}",
            "primary_sign": primary_sign,
            "neighbours_not_run": not_run,
            "what_is_read": spec["measurement"]["what_is_read"],
            "no_new_runs": spec["measurement"]["no_new_runs"],
            "risk_constants_have_no_neighbours": spec["measurement"][
                "risk_constants_have_no_neighbours"
            ],
            "neighbours": rows,
        },
    )


# -- combination ---------------------------------------------------------------------------------


def evaluate_representative_ra3(
    *,
    variant: RotationVariantRA3,
    primary: BacktestResult,
    neighbours: Sequence[tuple[RotationVariantRA3, BacktestResult | None]],
    criteria: dict[str, Any],
    ledger: EpisodeLedger | None = None,
    plan: G2PlanRA3 | None = None,
) -> dict[str, Any]:
    """All seven conditions for the one representative, combined conjunctively.

    Rule 6: the representative is selected before any condition is evaluated, by the return-blind
    rule — SE100-G2-SEL-2 for Attempt 3. Condition evaluation cannot feed back into selection,
    because selection has already happened and is not repeated. Rule 7: if the representative fails
    any condition, the stage fails, and no other variant is evaluated against the gate. Nothing here
    inspects any variant other than the representative and its structural neighbours, and the
    neighbours are read for the sign of net return and nothing else.

    Order matters and is the sealed order: rule 10's threshold seal check, then rule 9's non-vacuity
    guard, then the conditions. The adapter check runs first of all, because two of the seven
    conditions are evaluated against an adapted view and a report that did not establish the view was
    faithful would be reporting an unverified gate.
    """

    adapter_evidence = check_prose_alias_adapter(criteria)
    check_thresholds_against_seal(criteria)
    ledger = build_episode_ledger(primary) if ledger is None else ledger
    vacuity = assert_reconciliation_non_vacuous(ledger)
    plan = build_plan_ra3() if plan is None else plan

    verdicts = [
        condition_1(primary, criteria),
        condition_2(primary, criteria),
        condition_3_ra3(primary, ledger, criteria),
        condition_4_ra1(primary, ledger, criteria),
        condition_5_ra1(primary, ledger, criteria),
        condition_6_ra3(primary, ledger, plan, criteria),
        condition_7_ra3(primary, neighbours, criteria, variant=variant),
    ]
    admitted = all(verdict.satisfied for verdict in verdicts)
    return {
        "experiment_id": plan.experiment_id,
        "family": plan.family,
        "variant_id": variant.variant_id,
        "variant": variant.to_json(),
        "plan": plan.to_json(),
        "scenario": primary.scenario,
        "admitted": admitted,
        "conditions": [verdict.to_json() for verdict in verdicts],
        "conditions_met": sum(1 for verdict in verdicts if verdict.verdict == MET),
        "conditions_not_met": sorted(
            verdict.id for verdict in verdicts if verdict.verdict == NOT_MET
        ),
        "conditions_not_evaluable": sorted(
            verdict.id for verdict in verdicts if verdict.verdict == NOT_EVALUABLE
        ),
        "conditions_not_applicable": sorted(
            verdict.id for verdict in verdicts if verdict.verdict == NOT_APPLICABLE
        ),
        "reconciliation": ledger.reconciliation.to_json(),
        "non_vacuity_check": vacuity,
        "prose_alias_adapter": adapter_evidence,
        "redefined_for_generation_2": list(
            criteria["relationship_to_generation_1_criteria"]["redefined_for_generation_2"]
        ),
        "carried_over_unchanged": list(
            criteria["relationship_to_generation_1_criteria"]["carried_over_unchanged"]
        ),
        "measurement_basis_changed_from_attempt_1": list(
            criteria["relationship_to_attempt_1_criteria"]["measurement_basis_changed"]
        ),
        "measurement_basis_unchanged_from_attempt_1": list(
            criteria["relationship_to_attempt_1_criteria"]["measurement_basis_unchanged"]
        ),
        "measurement_basis_changed_from_attempt_2": list(
            criteria["relationship_to_attempt_2_criteria"]["measurement_basis_changed"]
        ),
        "measurement_basis_unchanged_from_attempt_2": list(
            criteria["relationship_to_attempt_2_criteria"]["measurement_basis_unchanged"]
        ),
        "episode_ledger_inherited": criteria["relationship_to_attempt_2_criteria"][
            "episode_ledger_inherited"
        ],
    }


def stage_verdict_ra3(
    candidate_results: Sequence[dict[str, Any]],
    criteria: dict[str, Any],
    *,
    representative_exists: bool,
    selection_note: str,
) -> dict[str, Any]:
    """The stage verdict, with its token taken from the sealed derivation and never from a literal.

    Not reused from Attempt 2: ``stage_verdict_ra1`` reads
    ``derivation["attempt_1_tokens_are_not_available_here"]`` and withholds two tokens. Attempt 3 has
    two closed predecessors, CFG-3106 renames that key to
    ``prior_attempt_tokens_are_not_available_here``, and four tokens are withheld.

    Two distinct routes reach FAIL and the seal names both in one ``fail_condition``: either no
    representative exists, because every one of the eighteen variants recorded at least one
    research-shutdown event, or a representative exists and does not satisfy every hard condition.
    They are recorded separately because they mean different things about the hypothesis — the first
    says the grid never produced a candidate to test, the second says the candidate was tested and
    rejected — while producing the same token. Attempt 1 failed by the first route and Attempt 2 by
    the second, so which route Attempt 3 takes is itself a result.
    """

    derivation = criteria["verdict_token_derivation"]
    admitted = [entry["variant_id"] for entry in candidate_results if entry["admitted"]]
    passed = bool(admitted)
    if passed and not representative_exists:
        raise ConfigViolation(
            "a candidate is recorded as admitted while no representative was selected; the two "
            "cannot both be true"
        )
    if representative_exists and not candidate_results:
        raise ConfigViolation(
            "a representative was selected but no candidate result was evaluated against the gate"
        )
    if len(candidate_results) > 1:
        raise ConfigViolation(
            f"{len(candidate_results)} candidates were evaluated against Gate 3; "
            "evaluation_integrity_rules section 7 admits exactly one, the representative"
        )

    token = derivation["pass_token" if passed else "fail_token"]
    if token not in (derivation["pass_token"], derivation["fail_token"]):  # pragma: no cover
        raise ConfigViolation(f"verdict token {token!r} is not one of the two sealed tokens")
    withheld = prior_attempt_tokens()
    if token in withheld:
        raise ConfigViolation(
            f"verdict token {token!r} belongs to a closed attempt; Attempt 3 may emit only "
            f"{derivation['pass_token']!r} or {derivation['fail_token']!r}"
        )

    if passed:
        route = "REPRESENTATIVE_SATISFIED_EVERY_CONDITION"
    elif not representative_exists:
        route = "NO_REPRESENTATIVE_EXISTS"
    else:
        route = "REPRESENTATIVE_FAILED_AT_LEAST_ONE_CONDITION"

    return {
        "verdict": "PASS" if passed else "FAIL",
        "verdict_token": token,
        "condition_token": derivation["pass_condition" if passed else "fail_condition"],
        "fail_route": None if passed else route,
        "route": route,
        "pass_token": derivation["pass_token"],
        "fail_token": derivation["fail_token"],
        "prior_attempt_tokens_withheld": list(withheld),
        "prior_attempt_tokens_note": derivation["prior_attempt_tokens_are_not_available_here"],
        "constitutional_fail_result_equivalent": derivation["constitutional_fail_result_equivalent"],
        "token_naming_note": derivation["token_naming_note"],
        "fail_is_a_deliverable": derivation["fail_is_a_deliverable"],
        "representative_exists": representative_exists,
        "selection_rule_id": g2_selection_v2.SELECTION_RULE_ID,
        "selection_note": selection_note,
        "admitted_candidates": admitted,
        "candidates_evaluated": len(candidate_results),
        "combination_rule": derivation["conjunctive_note"],
    }
