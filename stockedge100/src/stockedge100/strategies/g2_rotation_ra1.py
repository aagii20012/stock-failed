"""``SE100-G2-S3-C2-ROTATION-RA1`` — Attempt 2's candidate: Attempt 1's signal, plus RA2.

Everything here was fixed in ``config/generation_2/g2_rotation_ra1_protocol.json``
(``SE100-CFG-3103``) and its Markdown counterpart before any Attempt 2 strategy code existed, so this
module reads the seal rather than restating it. Where a value can be *derived* from something sealed
it is derived and then checked against the declaration: a restated constant can drift, and a derived
one that disagrees with its declaration raises.

**What is reused, and how literally.** The seal's own words are that
``stockedge100.strategies.g2_rotation.total_return`` "is imported and called unmodified", because
"reimplementing a sealed formula for a second attempt would create two definitions of one signal and a
place for them to diverge". The same reasoning applies past the signal: the rebalance calendar, the
ranking sort, the exclusion accounting and the whole ``decide`` flow are unchanged from Attempt 1, so
:class:`RotationCandidateRA1` **inherits** them from :class:`~stockedge100.strategies.g2_rotation.
RotationCandidate` rather than copying them. Attempt 1's module is imported and read; it is never
written, and nothing here modifies its behaviour for Attempt 1's own callers.

**Why ``__init__`` is nonetheless reimplemented.** Attempt 1's constructor derives
``w(k) = min(0.95 / k, 0.50)`` and refuses a variant whose declared weight differs — which every
Attempt 2 variant with ``k > 1`` does. So this class initialises its own state and calls
:class:`~stockedge100.strategies.base.Candidate` directly. That is the one place where inherited
methods could reach an attribute this constructor forgot to set, so the attribute set Attempt 1's
constructor produces is read out of Attempt 1's *source* and required to be covered. See
:func:`_attempt1_init_state`.

**Three things worth reading before the code.**

*The weight is derived from the ceiling that actually binds.* Attempt 1 sized against the
constitutional 95% gross ceiling. RA2-1 caps aggregate exposure at 50% of equity, so ``0.95 / k`` each
would demand 95% gross and be clamped to 50% on every rebalance — "the strategy would be defined by
its clamp rather than by its weights". The sealed formula is ``w(k) = min(A / k, C)`` with ``A = 0.50``
from RA2-1 and ``C = 0.50`` the per-position concentration ceiling, so ``A`` is read from the risk
architecture and never written here. ROUND_DOWN is load-bearing for the same representation reason it
was in Attempt 1: at ``prec=34`` and ROUND_HALF_EVEN, ``0.50 / 3`` rounds up and three such weights
exceed the ceiling by one ulp.

*This candidate still issues orders only on scheduled rebalances.* The stop, the throttle and the
ladder run at every session close, but all three are the engine's
(:class:`~stockedge100.backtest.g2_engine_ra1.RotationEngineRA1`), not the candidate's. Attempt 2's
departure from Attempt 1's "between scheduled rebalances the strategy issues no orders at all" is
recorded as ``G2A2-CONFLICT-1`` and lives entirely on the engine side. The check that keeps that
division honest is :func:`_verify_order_kinds`, which requires the seal to still say the two tags this
module emits fire on "scheduled rebalance only".

*An EXIT leg carries no quantity.* The engine's throttle excludes an exiting symbol from the projected
book on the basis that the whole position is going, and refuses a sized EXIT for that reason. The
inherited :meth:`~stockedge100.strategies.base.Candidate.exit_order` already leaves quantity ``None``;
it is overridden here only to carry the sealed ``EXIT`` tag.
"""

from __future__ import annotations

import ast
import datetime as dt
import hashlib
import inspect
import json
import pathlib
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from functools import lru_cache
from typing import Any, Sequence

from stockedge100.audit import sha256_file
from stockedge100.backtest.config import PROJECT_ROOT, dec
from stockedge100.backtest.costs import BASE, CostModel, exact, round_down_cent
from stockedge100.backtest.engine import DecisionContext, OrderRequest
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation
from stockedge100.backtest.g2_costs import concentration_ceiling, rotation_cost_model
from stockedge100.backtest.g2_engine_ra1 import (
    PROTOCOL_ID,
    PROTOCOL_PATH,
    SCALAR_DECIMALS,
    SCALAR_QUANTUM,
    SPELLED_DECIMALS,
    STRATEGY_ID,
    load_ra1_protocol,
    load_risk_architecture,
)
from stockedge100.backtest.orders import BUY, SELL
from stockedge100.strategies import g2_rotation as attempt_1
from stockedge100.strategies.base import Candidate
from stockedge100.strategies.g2_rotation import RotationCandidate, total_return

__all__ = [
    "ENTRY_TAG",
    "EXIT_TAG",
    "FAMILY",
    "PROTOCOL_ID",
    "PROTOCOL_PATH",
    "STRATEGY_ID",
    "RotationCandidateRA1",
    "RotationVariantRA1",
    "attempt_1_grid_agreement",
    "attempt_1_weight_comparison",
    "eligible_universe",
    "load_protocol",
    "rotation_variants",
    "target_weight",
    "variant_by_id",
]

UNIVERSE_REL = "governance/STAGE_1_UNIVERSE.json"

#: The two order tags this candidate may emit. STOP and THROTTLE are the engine's; SHUTDOWN is
#: Generation 1's engine's. All five are declared in the seal and checked in :func:`_verify_order_kinds`.
ENTRY_TAG = "ENTRY"
EXIT_TAG = "EXIT"

#: Attempt 1's family with the architecture appended. Checked against the seal, never assumed.
FAMILY = "CROSS_SECTIONAL_RELATIVE_STRENGTH_RISK_ARCHITECTURE"

_ENGINE_ISSUED_TAGS = ("STOP", "THROTTLE", "SHUTDOWN")


# -- the seal ------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_protocol() -> dict[str, Any]:
    """The sealed Attempt 2 protocol, with the checks this module needs on top of the engine's.

    Identity, generation, stage, attempt, ``declared_before_any_strategy_code`` and
    ``live_trading_authorized`` are already
    :func:`~stockedge100.backtest.g2_engine_ra1.load_ra1_protocol`'s. What is added here is everything
    a *strategy* has to believe before it ranks anything: the universe, the family, the order kinds
    and the rebalance months.
    """
    protocol = load_ra1_protocol()
    _verify_universe(protocol)
    _verify_family(protocol)
    _verify_order_kinds(protocol)
    _verify_rebalance(protocol)
    return protocol


def _verify_universe(protocol: dict[str, Any]) -> None:
    """The 34 members are Stage 1's, and the seal is checked against the frozen artifact itself.

    ``universe_identity_sha256`` is *not* recomputed here — its derivation belongs to Stage 1, and a
    reimplementation of it would be a second definition of the thing it identifies. It is read out of
    the frozen artifact and required to match, which is the same evidence without the second
    definition.
    """
    universe = protocol["eligible_universe"]
    source = PROJECT_ROOT / UNIVERSE_REL
    on_disk = sha256_file(source)
    if on_disk != universe["source_sha256"]:
        raise ConfigViolation(
            f"the protocol pins {UNIVERSE_REL} at {universe['source_sha256']} but the file on disk "
            f"is {on_disk}. The Stage 1 universe is frozen; a difference is a governance failure, "
            "not a value to update."
        )
    sealed = json.loads(source.read_text(encoding="utf-8"))
    if sorted(sealed["members"]) != sorted(universe["members"]):
        raise ConfigViolation(
            f"the protocol's member list does not match {UNIVERSE_REL}. Generation 2 re-checks "
            "eligibility on development data; it never adds, drops or substitutes a symbol."
        )
    if len(sealed["members"]) != universe["member_count"]:
        raise ConfigViolation(
            f"the protocol declares {universe['member_count']} members against "
            f"{len(sealed['members'])} in {UNIVERSE_REL}"
        )
    for field in ("universe_version", "universe_identity_sha256"):
        if sealed.get(field) != universe.get(field):
            raise ConfigViolation(
                f"the protocol declares {field}={universe.get(field)!r} against "
                f"{sealed.get(field)!r} in the frozen {UNIVERSE_REL}"
            )
    if universe.get("unchanged_from_attempt_1") is not True:
        raise ConfigViolation(
            "the protocol no longer claims the universe is unchanged from Attempt 1. Holding the "
            "universe fixed is what makes any Attempt 2 difference attributable to RA2."
        )


def _verify_family(protocol: dict[str, Any]) -> None:
    if protocol["family"] != FAMILY:
        raise ConfigViolation(
            f"the protocol declares family {protocol['family']!r}; this module implements {FAMILY!r}"
        )


def _verify_order_kinds(protocol: dict[str, Any]) -> None:
    """The candidate's two tags, and the division of labour with the engine.

    The load-bearing predicate is the last one. Attempt 2's whole departure from Attempt 1 is that
    *the engine* may act between rebalances; if the seal ever let the candidate do so, this module
    would be the wrong implementation of it.
    """
    declared = protocol["execution"]["order_kinds_this_attempt_may_issue"]
    kinds = {entry["tag"]: entry for entry in declared}
    if len(kinds) != len(declared):
        raise ConfigViolation("the sealed order-kind table names a tag twice")
    expected = {ENTRY_TAG, EXIT_TAG, *_ENGINE_ISSUED_TAGS}
    if set(kinds) != expected:
        raise ConfigViolation(
            f"the sealed order kinds are {sorted(kinds)}; this attempt implements {sorted(expected)}"
        )
    if kinds[ENTRY_TAG]["side"] != BUY or kinds[EXIT_TAG]["side"] != SELL:
        raise ConfigViolation(
            f"the seal gives {ENTRY_TAG} side {kinds[ENTRY_TAG]['side']!r} and {EXIT_TAG} side "
            f"{kinds[EXIT_TAG]['side']!r}"
        )
    if kinds[EXIT_TAG]["quantity"] != "the whole position":
        raise ConfigViolation(
            f"the seal sizes an {EXIT_TAG} leg as {kinds[EXIT_TAG]['quantity']!r}. The engine's "
            "throttle excludes an exiting symbol from the projected book on the basis that the whole "
            "position is going, and refuses a sized EXIT for that reason."
        )
    if "issued_by" not in kinds["SHUTDOWN"]:
        raise ConfigViolation(
            "the seal no longer records the SHUTDOWN leg as issued by the engine. The constitutional "
            "research shutdown is Generation 1's and is not this attempt's to issue."
        )
    for tag in (ENTRY_TAG, EXIT_TAG):
        if "scheduled rebalance only" not in kinds[tag]["when"]:
            raise ConfigViolation(
                f"the seal now fires {tag} on {kinds[tag]['when']!r}. This candidate issues orders "
                "only on scheduled rebalances; every between-rebalance leg in this attempt is the "
                "engine's (G2A2-CONFLICT-1)."
            )


def _verify_rebalance(protocol: dict[str, Any]) -> None:
    """Attempt 1's calendar, reused by inheritance, so the sealed rule must still be Attempt 1's."""
    rebalance = protocol["rebalance"]
    if rebalance.get("unchanged_from_attempt_1") is not True:
        raise ConfigViolation(
            "the protocol no longer claims the rebalance calendar is unchanged from Attempt 1, but "
            "this module inherits Attempt 1's is_scheduled_rebalance unmodified"
        )
    if tuple(rebalance["values"]) != (attempt_1.MONTHLY, attempt_1.QUARTERLY):
        raise ConfigViolation(
            f"the sealed rebalance values {rebalance['values']} are not the two frequencies "
            f"{(attempt_1.MONTHLY, attempt_1.QUARTERLY)} the inherited calendar implements"
        )
    rule = rebalance["rule"]
    for month in ("January", "April", "July", "October"):
        if month not in rule:
            raise ConfigViolation(
                f"the sealed rebalance rule does not name {month}, which the inherited quarterly "
                f"calendar rebalances in. Rule as sealed: {rule!r}"
            )


def eligible_universe() -> tuple[str, ...]:
    """The 34 frozen members, sorted. Ranked in full at every scheduled rebalance."""
    return tuple(sorted(load_protocol()["eligible_universe"]["members"]))


# -- sizing --------------------------------------------------------------------------------------


@exact
def target_weight(k: int, costs: CostModel) -> Decimal:
    """``w(k) = min(A / k, C)`` at nine decimal places, ROUND_DOWN, with ``A`` RA2-1's ceiling.

    Both fractions come off disk — ``A`` from the risk architecture, ``C`` from the sealed
    concentration ceiling — and the result is checked against the protocol's own declared weight
    *and* its declared gross exposure. Checking the gross separately is not redundant: the k=3 weight
    is one ulp short of a third by design, and the declared ``0.499999998`` is the only place that
    deliberate shortfall is written down.
    """
    if k <= 0:
        raise ConfigViolation(f"k={k!r} is not a position count")
    if costs.share_quantum != SCALAR_QUANTUM:
        raise ConfigViolation(
            f"the cost model quantizes shares at {costs.share_quantum} but the seal quantizes the "
            f"weight at {SCALAR_QUANTUM}"
        )

    ceiling = load_risk_architecture().exposure_ceiling
    weight = min(ceiling / k, concentration_ceiling())
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
            "module sizes against RA2-1's ceiling rather than the constitutional one"
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
            f"{k} * w({k}) = {gross} exceeds RA2-1's aggregate exposure ceiling {ceiling}"
        )
    return weight


@exact
def attempt_1_weight_comparison() -> dict[str, Any]:
    """Evidence, not a runtime dependency: how far Attempt 2's weights sit below Attempt 1's.

    Deliberately not called by :func:`target_weight`. Attempt 2's sizing must not depend on Attempt
    1's protocol still loading — that file's immutability is a gate condition, checked where gate
    conditions are checked, and coupling the two would turn one failure into two.
    """
    rows = []
    for k in (1, 2, 3):
        costs = rotation_cost_model(k, BASE)
        mine = target_weight(k, costs)
        theirs = attempt_1.target_weight(k, costs)
        if theirs < mine:
            raise InvariantViolation(
                f"Attempt 1 sized k={k} at {theirs}, below Attempt 2's {mine}. Attempt 2 sizes "
                "against a strictly tighter ceiling and can never size larger."
            )
        rows.append(
            {
                "top_k": k,
                "attempt_1_weight": f"{theirs:f}",
                "attempt_2_weight": f"{mine:f}",
                "attempt_1_gross": f"{theirs * k:f}",
                "attempt_2_gross": f"{mine * k:f}",
                "identical": theirs == mine,
            }
        )
    return {
        "attempt_1_formula": load_protocol()["position_sizing"]["attempt_1_formula"],
        "attempt_2_formula": load_protocol()["position_sizing"]["target_weight_formula"],
        "rows": rows,
        "coincident_at": [row["top_k"] for row in rows if row["identical"]],
    }


# -- the grid ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RotationVariantRA1:
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
    """The sealed id format, used as a format string rather than paraphrased into an f-string.

    Interpolating a template read from a file is only safe because the file is hash-verified before
    it is believed; the zero-padding check below is what makes the reuse worth it, since a template
    that lost its ``:02d`` would sort ``L12`` before ``L3`` in the representative tiebreak.
    """
    template = load_protocol()["grid"]["variant_id_format"]
    if not template.startswith(f"{STRATEGY_ID}-"):
        raise ConfigViolation(
            f"the sealed variant id format {template!r} does not begin with the strategy id "
            f"{STRATEGY_ID!r}"
        )
    if "{lookback:02d}" not in template:
        raise ConfigViolation(
            f"the sealed variant id format {template!r} does not zero-pad the lookback. The final "
            "tiebreak of the representative-selection rule is lexicographic, and an unpadded L12 "
            "would sort before L3."
        )
    return template


def _variant_id(lookback: int, k: int, frequency: str) -> str:
    variant_id = _variant_id_template().format(lookback=lookback, k=k, FREQUENCY=frequency)
    if f"-L{lookback:02d}-" not in variant_id:
        raise ConfigViolation(f"{variant_id!r} did not zero-pad lookback {lookback}")
    return variant_id


@lru_cache(maxsize=1)
def rotation_variants() -> tuple[RotationVariantRA1, ...]:
    """All eighteen, in the sealed order, rebuilt from the axes and checked against the seal.

    Rebuilding from ``grid.axes`` rather than reading ``grid.variants`` straight through means the
    declared list is *verified* rather than trusted, exactly as in Attempt 1: a variant silently added
    to or removed from the seal shows up as a length or id mismatch here instead of quietly becoming a
    nineteenth run.
    """
    protocol = load_protocol()
    grid = protocol["grid"]
    axes = grid["axes"]
    declared = {entry["variant_id"]: entry for entry in grid["variants"]}
    built: list[RotationVariantRA1] = []
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
                    RotationVariantRA1(
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


def variant_by_id(variant_id: str) -> RotationVariantRA1:
    for variant in rotation_variants():
        if variant.variant_id == variant_id:
            return variant
    raise ConfigViolation(f"{variant_id!r} is not one of the eighteen declared variants")


def attempt_1_grid_agreement() -> dict[str, Any]:
    """Evidence for the seal's ``grid.unchanged_from_attempt_1``: the axes really are the same.

    Compares axes and per-variant parameters against Attempt 1's protocol, ignoring the ids — those
    differ by construction, because Attempt 2's candidate id is different. As with
    :func:`attempt_1_weight_comparison` this is reporting, not a runtime dependency.
    """
    mine = load_protocol()["grid"]
    theirs = attempt_1.load_protocol()["grid"]
    axes_agree = {
        axis: list(mine["axes"][axis]) == list(theirs["axes"][axis]) for axis in sorted(mine["axes"])
    }
    key = ("lookback_months", "top_k", "rebalance_frequency", "scheduled_rebalance_sessions")
    mine_rows = [tuple(entry[field] for field in key) for entry in mine["variants"]]
    theirs_rows = [tuple(entry[field] for field in key) for entry in theirs["variants"]]
    return {
        "declared_unchanged": mine.get("unchanged_from_attempt_1") is True,
        "axes_agree": axes_agree,
        "all_axes_agree": all(axes_agree.values()),
        "size_agrees": mine["size"] == theirs["size"] == 18,
        "parameter_rows_agree": mine_rows == theirs_rows,
        "compared_fields": list(key),
        "ids_differ_by_construction": {
            "attempt_1": theirs["variants"][0]["variant_id"],
            "attempt_2": mine["variants"][0]["variant_id"],
        },
    }


# -- the candidate -------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _attempt1_init_state() -> frozenset[str]:
    """The instance attributes Attempt 1's ``__init__`` sets, read out of Attempt 1's own source.

    :class:`RotationCandidateRA1` inherits ``rank``, ``decide`` and ``evidence`` from Attempt 1 but
    cannot call Attempt 1's constructor, so every attribute those methods touch has to be set here
    instead. Listing them by hand would be a copy that silently rots; reading them off the source
    turns "I mirrored the state" from a claim into a check. Attempt 1 is parsed, never modified.
    """
    source_file = inspect.getsourcefile(RotationCandidate)
    if source_file is None:  # pragma: no cover - a source-less import is not a supported layout
        raise ConfigViolation("Attempt 1's candidate has no source file to read its state from")
    tree = ast.parse(pathlib.Path(source_file).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != RotationCandidate.__name__:
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or item.name != "__init__":
                continue
            names: set[str] = set()
            for statement in ast.walk(item):
                if isinstance(statement, ast.Assign):
                    targets = list(statement.targets)
                elif isinstance(statement, (ast.AnnAssign, ast.AugAssign)):
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
                    "Attempt 1's candidate constructor assigns no instance attributes; the mirror "
                    "check would pass vacuously"
                )
            return frozenset(names)
    raise ConfigViolation(
        f"no {RotationCandidate.__name__}.__init__ found in {source_file}; the state this class "
        "mirrors cannot be located"
    )


class RotationCandidateRA1(Candidate):
    """Attempt 1's cross-sectional rotation, sized under RA2.

    Inherits :meth:`~stockedge100.strategies.g2_rotation.RotationCandidate.rank`, ``decide``,
    ``target`` and ``evidence`` from Attempt 1 — the signal, the calendar, the sort key, the
    exclusion accounting and the ranking digest are all unchanged, which is the only reason a second
    attempt on a contaminated window is worth running. What changes is the weight, the two order
    tags, and the presence of an engine that acts between rebalances.
    """

    family = FAMILY

    # Attempt 1's decision logic, reused rather than copied. Bound explicitly so that the reuse is
    # visible at the class body rather than hidden in an MRO: this class descends from Candidate, not
    # from RotationCandidate, precisely because Attempt 1's constructor would refuse these variants.
    rank = RotationCandidate.rank
    decide = RotationCandidate.decide
    target = RotationCandidate.target
    ranking_digest = RotationCandidate.ranking_digest
    _base_evidence = RotationCandidate.evidence

    def __init__(
        self,
        variant: RotationVariantRA1,
        costs: CostModel,
        *,
        universe: Sequence[str] | None = None,
    ) -> None:
        risk = load_risk_architecture()
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

        self._previous_session: dt.date | None = None
        self._ranking_hash = hashlib.sha256()

        # Evidence, not bookkeeping: every one of these is reported for all eighteen variants.
        self.scheduled_rebalances = 0
        self.executed_rebalances = 0
        self.rebalances_blocked_by_shutdown = 0
        self.exclusions: dict[str, int] = {}
        self.selection_log: list[dict[str, Any]] = []

        missing = sorted(_attempt1_init_state() - set(vars(self)))
        if missing:
            raise InvariantViolation(
                f"this constructor mirrors Attempt 1's but does not set {missing}, which Attempt 1's "
                "constructor does. The inherited decide()/rank()/evidence() would reach it at "
                "runtime."
            )

    # -- orders ------------------------------------------------------------------------------------

    def entry_order(self, symbol: str, context: DecisionContext) -> OrderRequest:
        """``w(k) · equity`` at the decision close, tagged ``ENTRY``.

        The engine re-evaluates ``w(k) · f(t) · equity`` at the fill session's open, where ``f(t)`` is
        the combined risk scalar measured at *this* close. A frozen ``Order`` has nowhere to carry a
        weight or a scalar, so this budget is the record of the intent rather than the number that
        sizes the fill — Attempt 1's G2-CONFLICT-16, carried forward and widened by the scalar.
        """
        budget = round_down_cent(self.weight * context.equity)
        return OrderRequest(symbol=symbol, side=BUY, budget=budget, tag=ENTRY_TAG)

    def exit_order(self, symbol: str) -> OrderRequest:
        """The whole position, tagged ``EXIT``. Quantity stays ``None``; see the module docstring."""
        return OrderRequest(symbol=symbol, side=SELL, tag=EXIT_TAG)

    # -- evidence ----------------------------------------------------------------------------------

    def evidence(self) -> dict[str, Any]:
        payload = dict(self._base_evidence())
        payload["risk_architecture"] = self.risk.to_json()
        payload["target_weight_per_position"] = f"{self.weight:f}"
        payload["order_tags_issued"] = [ENTRY_TAG, EXIT_TAG]
        return payload


def build_candidate(
    variant: RotationVariantRA1 | str,
    scenario: str = BASE,
    *,
    universe: Sequence[str] | None = None,
) -> RotationCandidateRA1:
    """The one construction path the runner uses, so the cost model is never chosen by hand."""
    resolved = variant_by_id(variant) if isinstance(variant, str) else variant
    costs = rotation_cost_model(resolved.top_k, scenario)
    return RotationCandidateRA1(resolved, costs, universe=universe)


# ``total_return`` is re-exported so that a reader of this module can see the signal it ranks on
# without being told to go and find it. It is Attempt 1's function object, not a copy of it.
assert total_return is attempt_1.total_return
