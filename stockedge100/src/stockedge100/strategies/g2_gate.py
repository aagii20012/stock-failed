"""Gate 3 for Generation 2: five conditions reused from Generation 1, two redefined.

``config/generation_2/g2_gate_criteria.json`` (SE100-CFG-3102) names this module twice, once in
S3-C5's ``implementation`` and once in S3-C7's, and says of both that "Generation 1's
``stockedge100.strategies.gate`` ... is not called for Generation 2 and is not modified". That is
the whole shape of this file: it *imports* Generation 1's evaluator for the five conditions the seal
records as carried over unchanged, and supplies its own implementation for the two the seal records
as redefined. Nothing in ``gate.py`` is touched, subclassed, or monkeypatched — it is hashed by
Generation 1's frozen Stage 3 and Stage 4 checksum records.

Why the two are redefined:

**S3-C5.** Generation 1 reconstructed equity sequentially, ``E[i] = E[i-1] + pnl[i]`` over closed
trades in exit order. That was exact because at most one position could ever be open, so trades
never overlapped. Generation 2 holds up to three at once, and under the sequential reconstruction
two trades opened at the same rebalance would be charged against different equity bases purely
because of the order they happened to close in. The seal replaces the base with the equity that
actually existed at each trade's entry, read from the engine's own curve (G2-CONFLICT-6).

**S3-C7.** Generation 1's ``condition_7`` raises ``ConfigViolation`` unless exactly four neighbours
are supplied, because its grid had exactly four. Generation 2's neighbour set is structural — every
variant one step away on exactly one axis — and is 3, 4 or 5 depending on where in the 3x3x2 grid
the representative sits. The count is a function of the grid position and is never chosen
(G2-CONFLICT-7).

Every threshold, verdict token, axis ordering and predicate below is read from the sealed criteria
file. No token string and no digest is written as a literal here.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from typing import Any, Sequence

from stockedge100.audit import sha256_file
from stockedge100.backtest.config import PROJECT_ROOT
from stockedge100.backtest.costs import ZERO, exact
from stockedge100.backtest.engine import BacktestResult
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation

# Generation 1's evaluator, imported and never modified. The five carried-over conditions are used
# exactly as they are; ``_condition``, ``_sign`` and the verdict vocabulary are reused rather than
# restated so the two implementations cannot drift apart in a detail nobody is watching.
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
    condition_3,
    condition_4,
    condition_6,
)
from stockedge100.strategies.g2_rotation import (
    STRATEGY_ID,
    RotationCandidate,
    RotationVariant,
    eligible_universe,
    load_protocol,
    rotation_variants,
)

CRITERIA_PATH = PROJECT_ROOT / "config" / "generation_2" / "g2_gate_criteria.json"
CRITERIA_ID = "SE100-CFG-3102"

#: The Generation 1 criteria file this one declares itself a counterpart of. The path is asserted to
#: appear in the seal's own ``generation_1_counterpart`` string rather than standing alone, and the
#: digest is read from the seal and recomputed — never written here.
GENERATION_1_COUNTERPART_REL = "config/stage3_gate_criteria.json"

ONE = Decimal(1)

#: The three axes, in the sealed order. Used only to check that the criteria file and the protocol
#: file agree with each other; the values compared against come from those files, not from here.
AXIS_NAMES = ("lookback_months", "top_k", "rebalance_frequency")


@lru_cache(maxsize=1)
def load_criteria() -> dict[str, Any]:
    """The sealed Gate 3 criteria for Generation 2, refusing to load anything that is not them.

    The seal's own ``relationship_to_generation_1_criteria.seal_check`` says the Generation 2
    evaluator "calls the existing stockedge100.strategies.gate.check_thresholds_against_seal against
    this file ... before any condition is evaluated". Calling it here is strictly earlier than that:
    the criteria cannot be obtained at all without the five frozen thresholds, the S3-C6 predicate
    text and the S3-C4 exception flag having been checked against the constitution.
    """

    criteria = json.loads(CRITERIA_PATH.read_text(encoding="utf-8"))
    if criteria.get("artifact_id") != CRITERIA_ID:
        raise ConfigViolation(
            f"{CRITERIA_PATH} carries artifact_id {criteria.get('artifact_id')!r}, not {CRITERIA_ID!r}"
        )
    if criteria.get("generation") != 2 or criteria.get("stage") != 3:
        raise ConfigViolation(
            f"{CRITERIA_ID} is generation {criteria.get('generation')!r} stage "
            f"{criteria.get('stage')!r}; this evaluator is Generation 2 Stage 3 only"
        )
    if criteria.get("declared_before_any_strategy_code") is not True:
        raise ConfigViolation(
            f"{CRITERIA_ID} does not assert declared_before_any_strategy_code; a gate that was not "
            "declared before results is not a gate"
        )
    if GENERATION_1_COUNTERPART_REL not in criteria.get("generation_1_counterpart", ""):
        raise ConfigViolation(
            f"{CRITERIA_ID} names counterpart {criteria.get('generation_1_counterpart')!r}, which "
            f"is not {GENERATION_1_COUNTERPART_REL!r}"
        )
    counterpart = PROJECT_ROOT / GENERATION_1_COUNTERPART_REL
    measured = sha256_file(counterpart)
    if measured != criteria["generation_1_counterpart_sha256"]:
        raise ConfigViolation(
            f"{GENERATION_1_COUNTERPART_REL} hashes to {measured}, but {CRITERIA_ID} pins a "
            "different digest; the Generation 1 gate criteria are frozen, so report this rather "
            "than reconciling it"
        )
    check_thresholds_against_seal(criteria)
    _check_axes_agree(criteria)
    return criteria


def _check_axes_agree(criteria: dict[str, Any]) -> None:
    """S3-C7's ``axis_orderings`` and the protocol's ``grid.axes`` must be the same three axes.

    They are sealed in two separate files by two separate sessions. If they ever disagreed, the
    neighbour set would be derived from one grid and the runs from the other, and the condition
    would silently be comparing the representative against variants that were never run.
    """

    orderings = _condition(criteria, "S3-C7")["measurement"]["axis_orderings"]
    axes = load_protocol()["grid"]["axes"]
    if tuple(sorted(orderings)) != tuple(sorted(AXIS_NAMES)) or tuple(sorted(axes)) != tuple(sorted(AXIS_NAMES)):
        raise ConfigViolation(
            f"axis names differ: criteria {sorted(orderings)}, protocol {sorted(axes)}, "
            f"expected {sorted(AXIS_NAMES)}"
        )
    for axis in AXIS_NAMES:
        if list(orderings[axis]) != list(axes[axis]):
            raise ConfigViolation(
                f"axis {axis!r} is ordered {orderings[axis]!r} in {CRITERIA_ID} and {axes[axis]!r} "
                "in the sealed protocol; the two seals disagree"
            )


# -- the plan the reused condition_6 reads -------------------------------------------------------


@dataclass(frozen=True)
class G2Plan:
    """What Generation 1's ``condition_6`` and ``evaluate_candidate`` read off a plan.

    Deliberately *not* a ``CandidatePlan``. That dataclass carries ``warmup_sessions`` and
    ``effective_warmup`` as session counts, because Generation 1's lookback was a number of
    sessions. Generation 2's lookback is a number of calendar months, and the sealed ``run_span``
    derives the run start from a month offset against the latest inception in the universe, not
    from a session count. Filling those two fields would mean inventing a number to satisfy a
    constructor, which is exactly what an evidence field must never contain — so the plan carries
    the sealed derivation as prose and omits the counts that do not exist.

    ``condition_6`` reads one attribute, ``declared_universe``; ``evaluate_candidate``'s result
    header reads ``experiment_id`` and ``family``. All three are here and all three are real.
    """

    experiment_id: str
    family: str
    declared_universe: tuple[str, ...]
    run_start: dt.date
    run_end: dt.date
    binding_symbol: str
    warmup_derivation: str

    def to_json(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "family": self.family,
            "declared_universe": list(self.declared_universe),
            "declared_instrument_count": len(self.declared_universe),
            "run_start": self.run_start.isoformat(),
            "run_end": self.run_end.isoformat(),
            "binding_symbol": self.binding_symbol,
            "warmup_derivation": self.warmup_derivation,
        }


@lru_cache(maxsize=1)
def build_plan() -> G2Plan:
    """The declared plan, entirely from the seal."""

    run = load_protocol()["run_span"]
    return G2Plan(
        experiment_id=STRATEGY_ID,
        family=RotationCandidate.family,
        declared_universe=eligible_universe(),
        run_start=dt.date.fromisoformat(run["run_start"]),
        run_end=dt.date.fromisoformat(run["run_end"]),
        binding_symbol=run["binding_symbol"],
        warmup_derivation=run["derivation"],
    )


# -- S3-C5, redefined ----------------------------------------------------------------------------


def entry_equity_bases(result: BacktestResult) -> list[Decimal]:
    """E_entry[i] for every closed trade, by the sealed procedure.

    "For the i-th closed trade, E_entry[i] = account equity at the CLOSE of the session immediately
    preceding that trade's entry fill, read from the engine's own equity curve. If the entry fill is
    on the first session of the run, E_entry[i] = starting equity."

    The engine's curve has one point per session, so "the session immediately preceding" is the
    preceding *curve index*, not the preceding calendar day — a Tuesday entry after a Monday holiday
    is based on the previous Friday's close, which is the last close that existed.
    """

    index_by_session = {point.session: position for position, point in enumerate(result.equity_curve)}
    bases: list[Decimal] = []
    for trade in result.trades:
        position = index_by_session.get(trade.entry_session)
        if position is None:
            raise InvariantViolation(
                f"trade in {trade.symbol} entered {trade.entry_session.isoformat()}, which is not a "
                "session on the engine's own equity curve; the result is internally inconsistent"
            )
        bases.append(result.starting_equity if position == 0 else result.equity_curve[position - 1].equity)
    return bases


@exact
def condition_5_g2(result: BacktestResult, criteria: dict[str, Any]) -> ConditionVerdict:
    """"removing the single best trade leaves total return above 0%", on the entry-equity basis.

    ``j2`` is the largest P&L in signed currency terms — the biggest dollar winner — not the largest
    ``abs(pnl)``. The condition removes "the single best trade"; removing a large *loss* would raise
    the remaining return, which is the opposite of the stress this condition applies. That reading
    is carried over from Generation 1 unchanged, as the seal requires.
    """

    spec = _condition(criteria, "S3-C5")
    trades = list(result.trades)
    if len(trades) < 2:
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            note=spec["not_evaluable_treatment"],
            evidence={"closed_trades": len(trades)},
        )

    pnls = [trade.pnl for trade in trades]
    bases = entry_equity_bases(result)
    first_session_entries = sum(
        1 for trade in trades if trade.entry_session == result.equity_curve[0].session
    )

    if any(base <= ZERO for base in bases):
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            note=(
                "at least one trade was entered against zero or negative account equity, so its "
                "per-trade equity multiple is not defined"
            ),
            evidence={"closed_trades": len(trades)},
        )

    multiples = [ONE + pnl / base for pnl, base in zip(pnls, bases)]
    if any(multiple <= ZERO for multiple in multiples):
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            note=(
                "at least one trade lost more than the entire account equity that existed when it "
                "was entered, so the product of multiples is not a return"
            ),
            evidence={"closed_trades": len(trades)},
        )

    def product_excluding(index: int | None) -> Decimal:
        total = ONE
        for position, multiple in enumerate(multiples):
            if position != index:
                total *= multiple
        return total - ONE

    reconstructed = product_excluding(None)
    equity_curve_return = result.total_return()

    # "If several trades tie on the maximum, the earliest by index is removed." The (value, -index)
    # key is Generation 1's, carried over verbatim so the removal is deterministic.
    j1 = max(range(len(multiples)), key=lambda i: (multiples[i], -i))
    j2 = max(range(len(pnls)), key=lambda i: (pnls[i], -i))

    removed_1 = product_excluding(j1)
    removed_2 = product_excluding(j2)
    both_positive = removed_1 > ZERO and removed_2 > ZERO

    def detail(index: int) -> dict[str, Any]:
        return {
            "trade_index": index,
            "symbol": trades[index].symbol,
            "entry_session": trades[index].entry_session.isoformat(),
            "exit_session": trades[index].exit_session.isoformat(),
            "entry_equity_base": f"{bases[index]:f}",
            "multiple": f"{multiples[index]:f}",
            "pnl": f"{pnls[index]:f}",
            "removed_return": f"{product_excluding(index):f}",
        }

    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
        MET if both_positive else NOT_MET,
        measured=f"min({removed_1:f}, {removed_2:f})",
        threshold=spec["predicate"],
        note=spec["measurement"]["relation_to_headline_return"],
        evidence={
            "basis": spec["measurement"]["basis"],
            "closed_trades": len(trades),
            # The sealed disclosure_requirement: reconstruction, equity curve, and the gap, side by
            # side. The gap is expected to be non-zero and is not reconciled.
            "reconstructed_total_return": f"{reconstructed:f}",
            "equity_curve_total_return": f"{equity_curve_return:f}",
            "reconstruction_gap": f"{reconstructed - equity_curve_return:f}",
            "disclosure_requirement": spec["measurement"]["disclosure_requirement"],
            "trades_entered_on_first_session": first_session_entries,
            "distinct_entry_equity_bases": len({f"{base:f}" for base in bases}),
            "j1_largest_equity_multiple": detail(j1),
            "j2_largest_absolute_pnl": detail(j2),
            "j1_equals_j2": j1 == j2,
        },
    )


# -- S3-C7, redefined ----------------------------------------------------------------------------


def _axis_values(variant: RotationVariant) -> dict[str, Any]:
    return {
        "lookback_months": variant.lookback_months,
        "top_k": variant.top_k,
        "rebalance_frequency": variant.frequency,
    }


def expected_neighbour_count(variant: RotationVariant, criteria: dict[str, Any]) -> int:
    """The sealed count rule, computed independently of the neighbour construction.

    "3 when the representative is at an endpoint of both the lookback and the k axis; 5 when it is
    interior on both; 4 otherwise." One step on each side of an interior value, one step on the only
    side of an endpoint, and the two-valued frequency axis always contributes exactly one.
    """

    orderings = _condition(criteria, "S3-C7")["measurement"]["axis_orderings"]
    values = _axis_values(variant)
    total = 0
    for axis in AXIS_NAMES:
        ordering = list(orderings[axis])
        position = ordering.index(values[axis])
        total += (1 if position > 0 else 0) + (1 if position < len(ordering) - 1 else 0)
    return total


def neighbours_of(variant: RotationVariant, criteria: dict[str, Any]) -> tuple[RotationVariant, ...]:
    """"Every variant in the eighteen-variant grid that differs ... in exactly one axis by exactly
    one step."

    Constructed by stepping, then looked up in the grid — so a neighbour that is somehow not a
    declared variant is an error rather than a nineteenth run. The result is sorted by grid index,
    which makes the neighbour list a deterministic function of the representative alone.
    """

    orderings = _condition(criteria, "S3-C7")["measurement"]["axis_orderings"]
    grid = rotation_variants()
    by_axes = {
        (member.lookback_months, member.top_k, member.frequency): member for member in grid
    }
    values = _axis_values(variant)
    found: list[RotationVariant] = []
    for axis in AXIS_NAMES:
        ordering = list(orderings[axis])
        position = ordering.index(values[axis])
        for step in (-1, 1):
            neighbour_position = position + step
            if not 0 <= neighbour_position < len(ordering):
                continue
            shifted = dict(values)
            shifted[axis] = ordering[neighbour_position]
            key = (shifted["lookback_months"], shifted["top_k"], shifted["rebalance_frequency"])
            member = by_axes.get(key)
            if member is None:
                raise ConfigViolation(
                    f"one-step neighbour {key} of {variant.variant_id} is not a declared member of "
                    "the eighteen-variant grid"
                )
            found.append(member)

    expected = expected_neighbour_count(variant, criteria)
    if len(found) != expected or not 3 <= len(found) <= 5:
        raise ConfigViolation(
            f"{variant.variant_id} produced {len(found)} one-step neighbours; the sealed count rule "
            f"gives {expected}, and the grid admits only 3, 4 or 5"
        )
    if variant in found or len({member.variant_id for member in found}) != len(found):
        raise ConfigViolation(
            f"neighbour set of {variant.variant_id} is not a set of distinct other variants"
        )
    return tuple(sorted(found, key=lambda member: member.index))


@exact
def condition_7_g2(
    primary: BacktestResult,
    neighbours: Sequence[tuple[RotationVariant, BacktestResult | None]],
    criteria: dict[str, Any],
    *,
    variant: RotationVariant,
) -> ConditionVerdict:
    """"reasonable neighboring parameter values do not reverse the sign of net return".

    "zero matches nothing", so a neighbour or a representative that lands exactly flat fails the
    condition rather than being counted as agreeing with everything. A neighbour that did not run is
    NOT_RUN, which the seal states is not a pass.

    The neighbour set supplied is checked against the set this representative's grid position
    requires — passing a hand-picked subset would turn a structural condition into a chosen one.
    """

    spec = _condition(criteria, "S3-C7")
    required = neighbours_of(variant, criteria)
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
            row.update({"status": "NOT_RUN", "total_return": None, "sign": None, "matches_primary": False})
            not_run.append(member.variant_id)
            all_match = False
        else:
            neighbour_return = result.total_return()
            neighbour_sign = _sign(neighbour_return)
            matches = neighbour_sign == primary_sign and neighbour_sign != 0
            all_match = all_match and matches
            row.update({
                "status": "RUN",
                "total_return": f"{neighbour_return:f}",
                "sign": neighbour_sign,
                "matches_primary": matches,
            })
        rows.append(row)

    matched = sum(1 for row in rows if row["matches_primary"])
    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
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
            "representative_variant_id": variant.variant_id,
            "representative_grid_index": variant.index,
            "primary_total_return": f"{primary_return:f}",
            "primary_sign": primary_sign,
            "neighbours_not_run": not_run,
            "what_is_read": spec["measurement"]["what_is_read"],
            "neighbours": rows,
        },
    )


# -- combination ---------------------------------------------------------------------------------


def evaluate_representative(
    *,
    variant: RotationVariant,
    primary: BacktestResult,
    neighbours: Sequence[tuple[RotationVariant, BacktestResult | None]],
    criteria: dict[str, Any],
    plan: G2Plan | None = None,
) -> dict[str, Any]:
    """All seven conditions for the one representative, combined conjunctively.

    The seal's ``evaluation_integrity_rules``: "The representative is selected before any condition
    is evaluated, by the return-blind rule in SE100-CFG-3101. Condition evaluation cannot feed back
    into selection, because selection has already happened and is not repeated." Nothing here
    inspects any variant other than the representative and its structural neighbours, and the
    neighbours are read for the sign of net return and nothing else.
    """

    check_thresholds_against_seal(criteria)
    plan = build_plan() if plan is None else plan
    verdicts = [
        condition_1(primary, criteria),
        condition_2(primary, criteria),
        condition_3(primary, criteria),
        condition_4(primary, criteria),
        condition_5_g2(primary, criteria),
        condition_6(primary, plan, criteria),
        condition_7_g2(primary, neighbours, criteria, variant=variant),
    ]
    admitted = all(verdict.satisfied for verdict in verdicts)
    return {
        "experiment_id": plan.experiment_id,
        "family": plan.family,
        "variant_id": variant.variant_id,
        "variant": variant.to_json(),
        "plan": plan.to_json(),
        "admitted": admitted,
        "conditions": [verdict.to_json() for verdict in verdicts],
        "conditions_met": sum(1 for verdict in verdicts if verdict.verdict == MET),
        "conditions_not_met": sorted(verdict.id for verdict in verdicts if verdict.verdict == NOT_MET),
        "conditions_not_evaluable": sorted(
            verdict.id for verdict in verdicts if verdict.verdict == NOT_EVALUABLE
        ),
        "conditions_not_applicable": sorted(
            verdict.id for verdict in verdicts if verdict.verdict == NOT_APPLICABLE
        ),
        "redefined_for_generation_2": list(
            criteria["relationship_to_generation_1_criteria"]["redefined_for_generation_2"]
        ),
        "carried_over_unchanged": list(
            criteria["relationship_to_generation_1_criteria"]["carried_over_unchanged"]
        ),
    }


def stage_verdict_g2(
    candidate_results: Sequence[dict[str, Any]],
    criteria: dict[str, Any],
    *,
    representative_exists: bool,
    selection_note: str,
) -> dict[str, Any]:
    """The stage verdict, with its token taken from the sealed derivation and never from a literal.

    Two distinct routes reach FAIL, and the seal names both in one ``fail_condition``: "Either no
    representative exists, because every one of the eighteen variants recorded at least one
    research-shutdown event, or a representative exists and does not satisfy every hard condition."
    They are recorded separately here because they mean different things about the hypothesis — the
    first says the grid never produced a candidate to test, the second says the candidate was tested
    and rejected — while producing the same token.

    Generation 2 declares one candidate, so the constitution's cross-candidate disjunction is over a
    set of size one; see G2-CONFLICT-15.
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

    token = derivation["pass_token" if passed else "fail_token"]
    if token not in (derivation["pass_token"], derivation["fail_token"]):  # pragma: no cover
        raise ConfigViolation(f"verdict token {token!r} is not one of the two sealed tokens")

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
        "constitutional_fail_result_equivalent": derivation["constitutional_fail_result_equivalent"],
        "token_naming_note": derivation["token_naming_note"],
        "fail_is_a_deliverable": derivation["fail_is_a_deliverable"],
        "representative_exists": representative_exists,
        "selection_note": selection_note,
        "admitted_candidates": admitted,
        "candidates_evaluated": len(candidate_results),
        "combination_rule": derivation["conjunctive_note"],
    }
