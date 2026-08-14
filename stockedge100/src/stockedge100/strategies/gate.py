"""Evaluate the seven Gate 3 conditions by program, from the engine's own outputs.

Sealed ``evaluation_integrity_rules``:

    "Conditions are evaluated by a program that reads the engine's own outputs. No condition verdict
    is typed by hand into a report."
    "Every condition verdict is one of MET, NOT_MET, NOT_EVALUABLE, or
    NOT_APPLICABLE_BY_CONDITION_TEXT. There is no fifth value and no borderline value."
    "Thresholds are compared as exact Decimals."

Constitution §9 supplies the combination rule: gates are conjunctive, and "NOT_RUN, UNKNOWN, or
missing evidence is not a pass". So within a candidate, every condition that applies must be MET;
NOT_EVALUABLE fails, and only NOT_APPLICABLE_BY_CONDITION_TEXT is satisfied without being met. The
sealed ``verdict_token_derivation`` supplies the other half: "Conjunction applies WITHIN a
candidate. Across candidates the stage verdict is a disjunction" — one admitted candidate passes the
stage.

Nothing here reads a threshold that is not in ``config/stage3_gate_criteria.json``, and
:func:`check_thresholds_against_seal` refuses to evaluate anything if a constant below has drifted
from the sealed value it is supposed to mirror.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Sequence

from stockedge100.backtest.costs import ZERO, exact
from stockedge100.backtest.engine import BacktestResult
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.metrics import max_drawdown, profit_factor
from stockedge100.strategies.runner import CandidatePlan, VariantSpec, contribution_by_symbol, trade_pnls

MET = "MET"
NOT_MET = "NOT_MET"
NOT_EVALUABLE = "NOT_EVALUABLE"
NOT_APPLICABLE = "NOT_APPLICABLE_BY_CONDITION_TEXT"
VERDICT_VALUES = (MET, NOT_MET, NOT_EVALUABLE, NOT_APPLICABLE)

ONE = Decimal(1)
HUNDRED = Decimal(100)

#: S3-C6's threshold lives only in the frozen gate prose, not in the numeric companion. It is
#: written here and then checked against the sealed predicate string, so it cannot drift silently.
CONCENTRATION_MAX = Decimal("0.50")


def _threshold(value: Any) -> Decimal:
    """A sealed JSON number as an exact Decimal.

    ``json.load`` hands back ``1.1`` as a binary double whose exact value is
    1.100000000000000088817841970012523233890533447265625. Routing through ``str`` uses Python's
    shortest round-tripping repr, so the Decimal is the 1.1 that was written in the file — which is
    the number the gate says it compares against.
    """

    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True)
class ConditionVerdict:
    id: str
    required_verbatim: str
    verdict: str
    measured: str | None = None
    threshold: str | None = None
    note: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.verdict not in VERDICT_VALUES:
            raise ConfigViolation(
                f"{self.id}: {self.verdict!r} is not one of the four sealed verdict values"
            )

    @property
    def satisfied(self) -> bool:
        """MET, or not applicable. NOT_EVALUABLE is not a pass — constitution §9."""

        return self.verdict in (MET, NOT_APPLICABLE)

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "required_verbatim": self.required_verbatim,
            "verdict": self.verdict,
            "satisfied": self.satisfied,
            "measured": self.measured,
            "threshold": self.threshold,
            "note": self.note,
            "evidence": self.evidence,
        }


def _condition(criteria: dict[str, Any], condition_id: str) -> dict[str, Any]:
    for entry in criteria["conditions"]:
        if entry["id"] == condition_id:
            return entry
    raise ConfigViolation(f"sealed criteria carry no condition {condition_id!r}")


def check_thresholds_against_seal(criteria: dict[str, Any]) -> None:
    """Refuse to evaluate if any constant here has drifted from the sealed criteria."""

    thresholds = criteria["frozen_gate_json_companion_verbatim"]["thresholds"]
    expected = {
        "net_return_positive": True,
        "max_drawdown_pct": 15,
        "profit_factor_min": Decimal("1.1"),
        "closed_trades_min": 30,
        "best_trade_removed_return_positive": True,
    }
    for key, want in expected.items():
        got = thresholds[key]
        got = _threshold(got) if isinstance(want, Decimal) else got
        if got != want:
            raise ConfigViolation(
                f"sealed threshold {key}={got!r} does not match the value this evaluator was "
                f"written against ({want!r}); the seal governs, so stop and report it"
            )
    predicate = _condition(criteria, "S3-C6")["predicate"]
    if f"<= {CONCENTRATION_MAX:f}" not in predicate:
        raise ConfigViolation(
            f"S3-C6 predicate {predicate!r} does not carry the concentration limit "
            f"{CONCENTRATION_MAX:f} this evaluator applies"
        )
    if _condition(criteria, "S3-C4")["exception_invoked"] is not False:
        raise ConfigViolation("S3-C4's lower-frequency exception is recorded as invoked; it is not")


# -- the seven conditions ------------------------------------------------------------------------


@exact
def condition_1(result: BacktestResult, criteria: dict[str, Any]) -> ConditionVerdict:
    """"total return is positive"."""

    spec = _condition(criteria, "S3-C1")
    if len(result.equity_curve) < 2:
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            note=spec["not_evaluable_treatment"],
            evidence={"equity_points": len(result.equity_curve)},
        )
    measured = result.total_return()
    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
        MET if measured > ZERO else NOT_MET,
        measured=f"{measured:f}", threshold="> 0",
        evidence={
            "starting_equity": f"{result.starting_equity:f}",
            "final_equity": f"{result.final_equity:f}",
        },
    )


@exact
def condition_2(result: BacktestResult, criteria: dict[str, Any]) -> ConditionVerdict:
    """"maximum drawdown is no worse than 15%" — inclusive at exactly 15%."""

    spec = _condition(criteria, "S3-C2")
    limit = _threshold(criteria["frozen_gate_json_companion_verbatim"]["thresholds"]["max_drawdown_pct"]) / HUNDRED
    measured = max_drawdown([point.equity for point in result.equity_curve])
    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
        MET if measured <= limit else NOT_MET,
        measured=f"{measured:f}", threshold=f"<= {limit:f}",
        note=spec["boundary"],
        evidence={
            "granularity": "session close",
            "research_shutdown_session": (
                None if result.shutdown_session is None else result.shutdown_session.isoformat()
            ),
        },
    )


@exact
def condition_3(result: BacktestResult, criteria: dict[str, Any]) -> ConditionVerdict:
    """"profit factor is at least 1.10", with both sealed undefined cases handled explicitly."""

    spec = _condition(criteria, "S3-C3")
    minimum = _threshold(criteria["frozen_gate_json_companion_verbatim"]["thresholds"]["profit_factor_min"])
    pnls = trade_pnls(result)
    gross_profit = sum((value for value in pnls if value > ZERO), ZERO)
    gross_loss = -sum((value for value in pnls if value < ZERO), ZERO)
    evidence = {
        "closed_trades": len(pnls),
        "gross_profit": f"{gross_profit:f}",
        "gross_loss": f"{gross_loss:f}",
    }
    if not pnls:
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            measured=None, threshold=f">= {minimum:f}",
            note=spec["undefined_cases"]["no_closed_trades"], evidence=evidence,
        )
    measured = profit_factor(pnls)
    if measured is None:
        if gross_profit > ZERO:
            return ConditionVerdict(
                spec["id"], spec["required_verbatim"], MET,
                measured=None, threshold=f">= {minimum:f}",
                note="UNDEFINED_NO_LOSSES_TREATED_AS_MET: " + spec["undefined_cases"]["no_losing_trades"],
                evidence=evidence,
            )
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            measured=None, threshold=f">= {minimum:f}",
            note=(
                "profit factor is undefined with neither gross profit nor gross loss; the sealed "
                "no-losing-trades allowance requires positive gross profit and does not reach this case"
            ),
            evidence=evidence,
        )
    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
        MET if measured >= minimum else NOT_MET,
        measured=f"{measured:f}", threshold=f">= {minimum:f}", evidence=evidence,
    )


def condition_4(result: BacktestResult, criteria: dict[str, Any]) -> ConditionVerdict:
    """"at least 30 closed trades exist" — the sealed lower-frequency exception is not invoked."""

    spec = _condition(criteria, "S3-C4")
    minimum = int(criteria["frozen_gate_json_companion_verbatim"]["thresholds"]["closed_trades_min"])
    measured = len(result.trades)
    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
        MET if measured >= minimum else NOT_MET,
        measured=str(measured), threshold=f">= {minimum}",
        note=spec["exception_note"],
        evidence={
            "exception_invoked": spec["exception_invoked"],
            "open_positions_at_end": len(result.open_positions),
        },
    )


@exact
def condition_5(result: BacktestResult, criteria: dict[str, Any]) -> ConditionVerdict:
    """"removing the single best trade leaves total return above 0%", by the sealed reconstruction.

    ``j2`` is read as the largest P&L *in absolute currency terms* — the biggest dollar winner —
    not the largest ``abs(pnl)``. The condition removes "the single best trade"; removing a large
    loss would raise the remaining return, which is the opposite of the stress this condition
    applies, and ``j1`` already supplies the relative-size reading that ``j2`` is contrasted with.
    """

    spec = _condition(criteria, "S3-C5")
    pnls = trade_pnls(result)
    if len(pnls) < 2:
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            note=spec["not_evaluable_treatment"], evidence={"closed_trades": len(pnls)},
        )

    equity = [result.starting_equity]
    for pnl in pnls:
        equity.append(equity[-1] + pnl)
    if any(value <= ZERO for value in equity):
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            note=(
                "the closed-trade reconstruction reaches zero or negative equity, so per-trade "
                "equity multiples are not defined over the whole sequence"
            ),
            evidence={"closed_trades": len(pnls)},
        )
    multiples = [equity[i + 1] / equity[i] for i in range(len(pnls))]

    realized = ONE
    for value in multiples:
        realized *= value
    realized -= ONE

    j1 = max(range(len(multiples)), key=lambda i: (multiples[i], -i))
    j2 = max(range(len(pnls)), key=lambda i: (pnls[i], -i))

    def removed(index: int) -> Decimal:
        product = ONE
        for position, value in enumerate(multiples):
            if position != index:
                product *= value
        return product - ONE

    removed_1 = removed(j1)
    removed_2 = removed(j2)
    both_positive = removed_1 > ZERO and removed_2 > ZERO
    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
        MET if both_positive else NOT_MET,
        measured=f"min({removed_1:f}, {removed_2:f})", threshold="> 0 for BOTH removals",
        note=spec["measurement"]["relation_to_headline_return"],
        evidence={
            "closed_trades": len(pnls),
            "reconstructed_total_return": f"{realized:f}",
            "equity_curve_total_return": f"{result.total_return():f}",
            "j1_largest_equity_multiple": {
                "trade_index": j1,
                "multiple": f"{multiples[j1]:f}",
                "pnl": f"{pnls[j1]:f}",
                "removed_return": f"{removed_1:f}",
            },
            "j2_largest_absolute_pnl": {
                "trade_index": j2,
                "multiple": f"{multiples[j2]:f}",
                "pnl": f"{pnls[j2]:f}",
                "removed_return": f"{removed_2:f}",
            },
            "j1_equals_j2": j1 == j2,
        },
    )


@exact
def condition_6(
    result: BacktestResult, plan: CandidatePlan, criteria: dict[str, Any]
) -> ConditionVerdict:
    """"no single instrument contributes more than 50% of total strategy profit for a
    multi-instrument strategy"."""

    spec = _condition(criteria, "S3-C6")
    instruments = len(plan.declared_universe)
    if instruments <= 1:
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_APPLICABLE,
            note=spec["scope_interpretation"]["rationale"],
            evidence={
                "declared_instrument_count": instruments,
                "declared_universe": list(plan.declared_universe),
                "treatment": spec["scope_interpretation"]["single_instrument_treatment"],
            },
        )

    contributions = contribution_by_symbol(result)
    total = sum(contributions.values(), ZERO)
    evidence: dict[str, Any] = {
        "declared_instrument_count": instruments,
        "declared_universe": list(plan.declared_universe),
        "total_closed_trade_pnl": f"{total:f}",
        "pnl_by_instrument": {symbol: f"{value:f}" for symbol, value in sorted(contributions.items())},
    }
    if total <= ZERO:
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            threshold=f"<= {CONCENTRATION_MAX:f}",
            note=spec["measurement"], evidence=evidence,
        )
    shares = {symbol: value / total for symbol, value in contributions.items()}
    evidence["share_by_instrument"] = {
        symbol: f"{value:f}" for symbol, value in sorted(shares.items())
    }
    largest_symbol = max(sorted(shares), key=lambda symbol: shares[symbol])
    largest = shares[largest_symbol]
    evidence["largest_contributor"] = largest_symbol
    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
        MET if largest <= CONCENTRATION_MAX else NOT_MET,
        measured=f"{largest:f}", threshold=f"<= {CONCENTRATION_MAX:f}", evidence=evidence,
    )


def _sign(value: Decimal) -> int:
    return (value > ZERO) - (value < ZERO)


@exact
def condition_7(
    primary: BacktestResult,
    neighbours: Sequence[tuple[VariantSpec, BacktestResult | None]],
    criteria: dict[str, Any],
) -> ConditionVerdict:
    """"reasonable neighboring parameter values do not reverse the sign of net return".

    "zero matches nothing", so a neighbour or primary that lands exactly flat fails the condition
    rather than being counted as agreeing with everything.
    """

    spec = _condition(criteria, "S3-C7")
    primary_return = primary.total_return()
    primary_sign = _sign(primary_return)
    rows: list[dict[str, Any]] = []
    all_match = True
    not_run: list[str] = []
    for variant, result in neighbours:
        if result is None:
            rows.append({
                "variant_id": variant.variant_id,
                "parameters": variant.to_json()["parameters"],
                "status": "NOT_RUN",
                "total_return": None,
                "sign": None,
                "matches_primary": False,
            })
            not_run.append(variant.variant_id)
            all_match = False
            continue
        neighbour_return = result.total_return()
        neighbour_sign = _sign(neighbour_return)
        matches = neighbour_sign == primary_sign and neighbour_sign != 0
        all_match = all_match and matches
        rows.append({
            "variant_id": variant.variant_id,
            "parameters": variant.to_json()["parameters"],
            "status": "RUN",
            "total_return": f"{neighbour_return:f}",
            "sign": neighbour_sign,
            "matches_primary": matches,
        })
    if len(rows) != 4:
        raise ConfigViolation(
            f"S3-C7 expects exactly four sealed neighbours; {len(rows)} were supplied"
        )
    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
        MET if all_match else NOT_MET,
        measured=f"{sum(1 for row in rows if row['matches_primary'])}/4 neighbours match",
        threshold="all four match, zero matches nothing",
        note=(
            spec["selection_prohibition"]
            if not not_run
            else spec["not_evaluable_treatment"] + " " + spec["selection_prohibition"]
        ),
        evidence={
            "primary_total_return": f"{primary_return:f}",
            "primary_sign": primary_sign,
            "neighbours_not_run": not_run,
            "neighbours": rows,
        },
    )


# -- combination ---------------------------------------------------------------------------------


def evaluate_candidate(
    *,
    plan: CandidatePlan,
    primary: BacktestResult,
    neighbours: Sequence[tuple[VariantSpec, BacktestResult | None]],
    criteria: dict[str, Any],
) -> dict[str, Any]:
    """All seven conditions for one candidate, combined conjunctively."""

    check_thresholds_against_seal(criteria)
    verdicts = [
        condition_1(primary, criteria),
        condition_2(primary, criteria),
        condition_3(primary, criteria),
        condition_4(primary, criteria),
        condition_5(primary, criteria),
        condition_6(primary, plan, criteria),
        condition_7(primary, neighbours, criteria),
    ]
    admitted = all(verdict.satisfied for verdict in verdicts)
    return {
        "experiment_id": plan.experiment_id,
        "family": plan.family,
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
    }


def stage_verdict(candidate_results: Sequence[dict[str, Any]], criteria: dict[str, Any]) -> dict[str, Any]:
    """Across candidates the stage verdict is a disjunction: one admitted candidate passes."""

    derivation = criteria["verdict_token_derivation"]
    admitted = [entry["experiment_id"] for entry in candidate_results if entry["admitted"]]
    passed = bool(admitted)
    return {
        "verdict": "PASS" if passed else "FAIL",
        "condition_token": derivation["pass_condition" if passed else "fail_condition"],
        "pass_token": derivation["pass_token"],
        "fail_token": derivation["fail_token"],
        "admitted_candidates": admitted,
        "candidates_evaluated": len(candidate_results),
        "combination_rule": derivation["conjunctive_note"],
    }
