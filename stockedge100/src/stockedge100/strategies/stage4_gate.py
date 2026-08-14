"""Gate 4: the seven sealed conditions, evaluated conjunctively against one representative.

This module imports no dataset loader, no market data and no broker surface. That is not tidiness —
it is the structural half of the claim that the gate cannot have been influenced by what it was
measuring. Everything here takes numbers that were already computed and compares them to thresholds
that were sealed before those numbers existed. The AST predicate the Stage 4 pre-registration seals
over ``stage4``-path modules is what turns "the gate reads no data" from a sentence in a report into
a fact a reader can recompute.

One transitive edge is worth stating plainly rather than leaving for a reader to find:
:mod:`stockedge100.strategies.gate` — which supplies :class:`ConditionVerdict`, the sealed four-value
verdict type whose ``satisfied`` property implements constitution section 9 — itself imports
``backtest.engine`` for its Gate 3 condition functions. So this module reaches the engine's *types*
transitively. It reaches no dataset, no loader and no price series, transitively or otherwise, which
is what the sealed predicate measures and what the claim above means. Re-declaring a private copy of
the verdict type to make the import graph look cleaner would trade a real invariant — one definition
of "satisfied" across both gates — for a cosmetic one.

Four rules from ``config/stage4_gate_criteria.json`` shape the whole file:

* **Thresholds come from two places and must agree.** Each condition's ``predicate`` carries a
  ``Decimal('…')`` literal; ``frozen_gate_json_companion_verbatim.thresholds`` carries a number for
  six of the seven. :func:`check_thresholds_against_seal` parses the first and compares it to the
  second, and refuses on any divergence. The protocol requires exactly this: *"a divergence between
  this file and that one fails rather than silently prefers this file."* Nothing in this module has
  a threshold typed into it.

* **Exact Decimals, no rounding before comparison.** ``evaluation_integrity_rules`` forbids floating
  point and forbids rounding before the comparison. Every measured value arrives as a ``Decimal`` or
  as ``None``; ``float`` never appears in a comparison.

* **NOT_EVALUABLE is never a pass.** Constitution section 9. Each condition's sealed
  ``not_evaluable_treatment`` names the exact circumstances, and each is implemented from that text
  rather than from a general "if something went wrong" branch — the two are not the same, and S4-C7
  is the case that proves it: its sealed treatment makes missing evidence ``NOT_MET``, not
  ``NOT_EVALUABLE``, because *"the absence of the evidence that would prove no change occurred is
  not neutral: it is the state the condition exists to forbid."*

* **The conjunction is the verdict.** ``verdict_token_derivation.conjunctive_note``: exactly one
  representative is evaluated, so there is no disjunction across candidates and no
  ``admissible_candidate_exists`` row. A Gate 4 conditions table that carried one would be claiming
  a degree of freedom this gate does not have.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Mapping, Sequence

from stockedge100.backtest.errors import ConfigViolation
from stockedge100.strategies.gate import (
    MET,
    NOT_APPLICABLE,
    NOT_EVALUABLE,
    NOT_MET,
    VERDICT_VALUES,
    ConditionVerdict,
)

CONDITION_IDS = ("S4-C1", "S4-C2", "S4-C3", "S4-C4", "S4-C5", "S4-C6", "S4-C7")

#: Maps each condition to the key its threshold carries in the JSON companion. S4-C7 has no entry:
#: the companion omits it entirely, which is S4-CONFLICT-1 and the reason the Markdown is
#: authoritative. Recording the omission as ``None`` rather than leaving the condition out of the
#: map keeps the cross-check total — a companion that grew a seventh threshold would fail here.
COMPANION_THRESHOLD_KEYS = {
    "S4-C1": "net_return_positive",
    "S4-C2": "sharpe_min",
    "S4-C3": "max_drawdown_pct",
    "S4-C4": "profit_factor_min",
    "S4-C5": "stressed_cost_return_positive",
    "S4-C6": "positive_walk_forward_folds_pct_min",
    "S4-C7": None,
}

_DECIMAL_LITERAL = re.compile(r"Decimal\('([-0-9.]+)'\)")


def condition(criteria: Mapping[str, Any], condition_id: str) -> dict[str, Any]:
    """One sealed condition, by id. The ``conditions`` block is a list, not a map."""

    for entry in criteria["conditions"]:
        if entry["id"] == condition_id:
            return dict(entry)
    raise ConfigViolation(f"no sealed Gate 4 condition with id {condition_id!r}")


def sealed_threshold(criteria: Mapping[str, Any], condition_id: str) -> Decimal | None:
    """The threshold, parsed out of the condition's own sealed ``predicate`` string.

    The conditions carry no numeric ``threshold`` field — the number lives inside the predicate
    text, so that the comparison a reader sees and the comparison the code makes are the same
    string. Parsing it keeps that property; restating it here would break it.

    S4-C7 returns ``None``, and that is a property of the sealed text rather than an oversight: its
    predicate is four conjoined equalities over digests, run records, run counts and parameters, and
    the only number in it is the declared run count of 2 written as a word-adjacent digit, not as a
    ``Decimal`` literal. The expected literal count is asserted per condition, so a future edit that
    added a threshold to S4-C7 — or removed one from any of the other six — would fail here instead
    of being silently absorbed.
    """

    predicate = str(condition(criteria, condition_id)["predicate"])
    found = _DECIMAL_LITERAL.findall(predicate)
    expected = 0 if condition_id == "S4-C7" else 1
    if len(found) != expected:
        raise ConfigViolation(
            f"{condition_id}: its sealed predicate carries {len(found)} Decimal literals "
            f"({found}); exactly {expected} was expected. Predicate: {predicate!r}"
        )
    return Decimal(found[0]) if found else None


def check_thresholds_against_seal(criteria: Mapping[str, Any]) -> dict[str, Any]:
    """Cross-check every predicate literal against the JSON companion, and refuse on divergence.

    The two representations differ in form and the comparison accounts for that rather than glossing
    it: the companion states the drawdown ceiling as ``15`` percent where the predicate states
    ``0.15`` as a fraction, and states the two positivity conditions as the boolean ``true`` where
    the predicates compare against ``0``. Both mappings are declared here explicitly, because an
    implicit "divide by a hundred if it looks big" rule is exactly the kind of silent preference the
    protocol forbids.
    """

    companion = criteria["frozen_gate_json_companion_verbatim"]["thresholds"]
    checked: dict[str, Any] = {}
    problems: list[str] = []

    for condition_id in CONDITION_IDS:
        key = COMPANION_THRESHOLD_KEYS[condition_id]
        literal = sealed_threshold(criteria, condition_id)
        if key is None or literal is None:
            if not (key is None and literal is None):
                problems.append(
                    f"{condition_id}: one of the two sealed homes carries a threshold and the other "
                    f"does not (companion key {key!r}, predicate literal {literal!r})"
                )
                continue
            checked[condition_id] = {
                "predicate_literal": None,
                "companion_key": None,
                "companion_value": None,
                "agrees": None,
                "note": (
                    "S4-CONFLICT-1: the JSON companion omits this condition, and its sealed "
                    "predicate is four equalities rather than a numeric threshold. The Markdown "
                    "gate text is authoritative for it."
                ),
            }
            continue
        if key not in companion:
            problems.append(f"{condition_id}: the companion carries no threshold {key!r}")
            continue
        raw = companion[key]
        if isinstance(raw, bool):
            # "net_return_positive": true means "the comparison is > 0", so the predicate literal
            # must be exactly zero. A true here with a non-zero literal would be a real divergence.
            agrees = raw is True and literal == Decimal(0)
            expected = "0"
        elif key == "max_drawdown_pct":
            agrees = Decimal(str(raw)) == literal * Decimal(100)
            expected = f"{literal * Decimal(100):f}"
        elif key == "positive_walk_forward_folds_pct_min":
            agrees = Decimal(str(raw)) == literal * Decimal(100)
            expected = f"{literal * Decimal(100):f}"
        else:
            agrees = Decimal(str(raw)) == literal
            expected = f"{literal:f}"
        checked[condition_id] = {
            "predicate_literal": f"{literal:f}",
            "companion_key": key,
            "companion_value": raw,
            "companion_as_compared": expected,
            "agrees": agrees,
        }
        if not agrees:
            problems.append(
                f"{condition_id}: predicate literal {literal} disagrees with companion "
                f"{key}={raw!r}"
            )

    unmapped = set(companion) - {
        key for key in COMPANION_THRESHOLD_KEYS.values() if key is not None
    }
    if unmapped:
        problems.append(f"the companion carries unmapped thresholds {sorted(unmapped)}")

    if problems:
        raise ConfigViolation(
            "the Gate 4 thresholds do not agree across their two sealed homes:\n  "
            + "\n  ".join(problems)
            + "\nSE100-CFG-4001 measurement_and_gate_criteria requires that a divergence fails "
            "rather than silently prefers one file."
        )
    return checked


def _verdict(
    criteria: Mapping[str, Any],
    condition_id: str,
    verdict: str,
    *,
    measured: Any = None,
    note: str | None = None,
    evidence: Mapping[str, Any] | None = None,
) -> ConditionVerdict:
    if verdict not in VERDICT_VALUES:
        raise ConfigViolation(f"{condition_id}: {verdict!r} is not one of {VERDICT_VALUES}")
    sealed = condition(criteria, condition_id)
    threshold = sealed_threshold(criteria, condition_id)
    # The threshold field carries the sealed predicate verbatim rather than a bare number. S4-C1 and
    # S4-C5 both carry the literal 0 but compare strictly, while S4-C2, S4-C4 and S4-C6 are
    # inclusive: a conditions table showing "0" for one row and "0.50" for another has lost the
    # direction of every comparison, and the direction is half of each rule. The parsed literal goes
    # into the evidence beside it, so a reader can still recompute the comparison arithmetically.
    body = dict(evidence or {})
    body["sealed_predicate_literal"] = None if threshold is None else f"{threshold:f}"
    return ConditionVerdict(
        id=condition_id,
        required_verbatim=str(sealed["required_verbatim"]),
        verdict=verdict,
        measured=None if measured is None else f"{measured:f}",
        threshold=str(sealed["predicate"]),
        note=note,
        evidence=body,
    )


# -- the seven conditions ---------------------------------------------------------------------


def condition_1(criteria: Mapping[str, Any], base: Mapping[str, Any]) -> ConditionVerdict:
    """S4-C1 — after-cost total return of the BASE run is positive. Strict; zero is not positive."""

    threshold = sealed_threshold(criteria, "S4-C1")
    if not base.get("reached_window_end") or base.get("equity_points", 0) < 2:
        return _verdict(
            criteria, "S4-C1", NOT_EVALUABLE,
            note=(
                "The sealed not_evaluable_treatment: an equity series with fewer than two points, "
                "or a run that did not reach 2024-07-31."
            ),
            evidence={
                "equity_points": base.get("equity_points"),
                "reached_window_end": base.get("reached_window_end"),
            },
        )
    measured = base["total_return"]
    return _verdict(
        criteria, "S4-C1", MET if measured > threshold else NOT_MET, measured=measured,
        note="Strict inequality. Exactly zero is NOT positive.",
        evidence={
            "starting_equity": base.get("starting_equity"),
            "final_equity": base.get("final_equity"),
            "scenario": base.get("scenario"),
        },
    )


def condition_2(criteria: Mapping[str, Any], base: Mapping[str, Any]) -> ConditionVerdict:
    """S4-C2 — Sharpe at the documented 0.00% cash rate is at least the frozen 0.50."""

    threshold = sealed_threshold(criteria, "S4-C2")
    sealed = condition(criteria, "S4-C2")
    measured = base.get("sharpe")
    if measured is None:
        return _verdict(
            criteria, "S4-C2", NOT_EVALUABLE,
            note=(
                "The sealed not_evaluable_treatment: fewer than two daily returns, or a zero "
                "standard deviation. Never as infinity and never as a large number."
            ),
            evidence={
                "daily_returns": base.get("daily_returns"),
                "documented_cash_rate": sealed["documented_cash_rate"],
            },
        )
    return _verdict(
        criteria, "S4-C2", MET if measured >= threshold else NOT_MET, measured=measured,
        note="Inclusive. The threshold is 0.50 and it is frozen.",
        evidence={
            "documented_cash_rate": sealed["documented_cash_rate"],
            "development_context": sealed["development_context_recorded"],
        },
    )


def condition_3(criteria: Mapping[str, Any], base: Mapping[str, Any]) -> ConditionVerdict:
    """S4-C3 — maximum drawdown no worse than 15%, inclusive.

    S4-CONFLICT-3 makes this the same number as the section 5.1 research shutdown on the same
    series, so the condition is met if and only if the shutdown never fired. Both quantities are
    recorded in the evidence, because a report that stated only one of them would be hiding the
    coincidence that makes the condition decidable.
    """

    threshold = sealed_threshold(criteria, "S4-C3")
    if not base.get("reached_window_end") or base.get("equity_points", 0) < 2:
        return _verdict(
            criteria, "S4-C3", NOT_EVALUABLE,
            note="The BASE run did not produce a scoreable equity series.",
            evidence={"equity_points": base.get("equity_points")},
        )
    measured = base["max_drawdown"]
    fired = bool(base.get("shutdown_session"))
    return _verdict(
        criteria, "S4-C3", MET if measured <= threshold else NOT_MET, measured=measured,
        note=(
            "Inclusive: exactly 15% is not worse than 15%. S4-CONFLICT-3 and S4-INTERP-4: this "
            "ceiling and the section 5.1 shutdown are the same 15% on the same series, so the "
            "condition is MET if and only if the shutdown never fired."
        ),
        evidence={
            "research_shutdown_fired": fired,
            "shutdown_session": base.get("shutdown_session"),
            "shutdown_fraction": base.get("shutdown_fraction"),
            "max_drawdown_basis": base.get("max_drawdown_basis"),
        },
    )


def condition_4(criteria: Mapping[str, Any], base: Mapping[str, Any]) -> ConditionVerdict:
    """S4-C4 — profit factor at least 1.15 over CLOSED round trips of the BASE run.

    Two distinct undefined cases, and the sealed text names both: no closed trades at all, and a
    zero gross loss. They are reported separately because they mean different things — one is an
    inactive strategy and the other is an unbeaten one — and conflating them would lose that.
    """

    threshold = sealed_threshold(criteria, "S4-C4")
    sealed = condition(criteria, "S4-C4")
    closed = base.get("closed_trades")
    measured = base.get("profit_factor")
    if closed == 0:
        return _verdict(
            criteria, "S4-C4", NOT_EVALUABLE,
            note="No closed round trips, so the ratio has no denominator and no numerator.",
            evidence={
                "closed_trades": closed,
                "undefined_cases": sealed["undefined_cases"],
                "no_closed_trade_floor_at_this_gate": sealed["no_closed_trade_floor_at_this_gate"],
            },
        )
    if measured is None:
        return _verdict(
            criteria, "S4-C4", NOT_EVALUABLE,
            note="Gross loss is zero, so the profit factor is undefined rather than infinite.",
            evidence={
                "closed_trades": closed,
                "gross_profit": base.get("gross_profit"),
                "gross_loss": base.get("gross_loss"),
                "undefined_cases": sealed["undefined_cases"],
            },
        )
    return _verdict(
        criteria, "S4-C4", MET if measured >= threshold else NOT_MET, measured=measured,
        note="Inclusive. Open positions at the window end are excluded from both sides of the ratio.",
        evidence={
            "closed_trades": closed,
            "gross_profit": base.get("gross_profit"),
            "gross_loss": base.get("gross_loss"),
            "no_closed_trade_floor_at_this_gate": sealed["no_closed_trade_floor_at_this_gate"],
        },
    )


def condition_5(criteria: Mapping[str, Any], stress: Mapping[str, Any]) -> ConditionVerdict:
    """S4-C5 — the STRESSED run's total return is positive. Gating at Gate 4.

    The sealed ``flag_semantics_superseded`` is the whole point of this condition: at Gate 3 a
    non-positive stressed return raised a ``STRESS_FRAGILE`` flag and the candidate could still
    pass. At Gate 4 it is NOT_MET. The base run's figures may not substitute for a missing stressed
    run, so an absent stressed result is NOT_EVALUABLE and never a silent fallback.
    """

    threshold = sealed_threshold(criteria, "S4-C5")
    sealed = condition(criteria, "S4-C5")
    if not stress or not stress.get("reached_window_end") or stress.get("equity_points", 0) < 2:
        return _verdict(
            criteria, "S4-C5", NOT_EVALUABLE,
            note=(
                "The stressed run did not reach 2024-07-31 or produced no scoreable series. The "
                "base run's figures may not substitute for a missing stressed run."
            ),
            evidence={
                "reached_window_end": stress.get("reached_window_end") if stress else None,
                "equity_points": stress.get("equity_points") if stress else None,
            },
        )
    measured = stress["total_return"]
    return _verdict(
        criteria, "S4-C5", MET if measured > threshold else NOT_MET, measured=measured,
        note=(
            "Strict. Gating at Gate 4: the Gate 3 STRESS_FRAGILE flag semantics are superseded, so "
            "a non-positive stressed return is NOT_MET rather than a flag."
        ),
        evidence={
            "scenario": stress.get("scenario"),
            "stress_multiplier": stress.get("stress_multiplier"),
            "shutdown_enforced": stress.get("shutdown_enforced"),
            "status_change_from_gate_3": sealed["status"],
        },
    )


def condition_6(
    criteria: Mapping[str, Any], folds: Sequence[Mapping[str, Any]]
) -> ConditionVerdict:
    """S4-C6 — at least 70% of COMPLETED folds have a positive after-cost return.

    The denominator is the count of COMPLETED folds, and a research shutdown cannot shrink it:
    S4-INTERP-5 makes every post-shutdown fold COMPLETED with a return of exactly 0, which is not
    positive. Fewer than twelve completed folds means the run did not reach the window end, which is
    NOT_EVALUABLE — not a smaller denominator scored proportionally.

    The ratio is compared as an exact Decimal quotient. With twelve folds the boundary is 8.4, so
    nine passes and eight fails and there is no tie to adjudicate; the quotient is used anyway,
    because the sealed predicate is a quotient and a count comparison would be a different rule that
    happens to agree at twelve.
    """

    threshold = sealed_threshold(criteria, "S4-C6")
    expected = int(
        criteria["walk_forward_fold_construction"]["completed_fold_definition"][
            "expected_completed_count"
        ]
    )
    completed = [fold for fold in folds if fold.get("completed")]
    positive = [fold for fold in completed if fold.get("positive")]
    evidence = {
        "declared_fold_count": expected,
        "folds_scored": len(folds),
        "completed_fold_count": len(completed),
        "positive_fold_count": len(positive),
        "positive_folds": [fold["fold"] for fold in positive],
        "non_positive_folds": [fold["fold"] for fold in completed if not fold.get("positive")],
        "incomplete_folds": [fold["fold"] for fold in folds if not fold.get("completed")],
        "smallest_passing_count_at_twelve_folds": 9,
    }
    if len(completed) < expected:
        return _verdict(
            criteria, "S4-C6", NOT_EVALUABLE,
            note=(
                f"{len(completed)} completed folds against the declared {expected}: the run did not "
                "reach the validation window end. The sealed rule re-runs in full rather than "
                "scoring partially."
            ),
            evidence=evidence,
        )
    if len(completed) == 0:
        return _verdict(
            criteria, "S4-C6", NOT_EVALUABLE, note="No completed folds.", evidence=evidence
        )
    ratio = Decimal(len(positive)) / Decimal(len(completed))
    return _verdict(
        criteria, "S4-C6", MET if ratio >= threshold else NOT_MET, measured=ratio,
        note=(
            "Inclusive. Denominator is COMPLETED folds; a research shutdown cannot shrink it, "
            "because post-shutdown folds are COMPLETED with a return of exactly 0."
        ),
        evidence=evidence,
    )


def condition_7(criteria: Mapping[str, Any], invariance: Mapping[str, Any]) -> ConditionVerdict:
    """S4-C7 — no material rule, feature, universe or parameter change in response to validation.

    Four conjoined clauses from the sealed predicate, each measured rather than asserted:

    1. every sealed digest recomputes to its sealed value;
    2. exactly one validation evaluation run record exists in ``runs/``;
    3. the number of validation-window engine runs equals the declared count of 2;
    4. no parameter recorded in the evaluation evidence differs from the sealed parameterisation.

    Clause 4 names ``config/stage4_representative_selection.json`` as the home of the sealed
    parameterisation, and that file carries none — the parameterisation lives in
    ``config/stage4_validation_protocol.json`` ``sealed_representative.parameters``. That is
    S4-CONFLICT-6, recorded in the decision package; the clause is measured against the file that
    actually carries the values, and both files are inside the thirteen-artifact digest set, so
    clause 1 already forbids either of them from changing.

    Missing evidence is NOT_MET here, not NOT_EVALUABLE. The sealed treatment is explicit about why:
    the absence of the evidence that would prove no change occurred is the state the condition
    exists to forbid.
    """

    sealed = condition(criteria, "S4-C7")
    declared_runs = int(invariance.get("declared_run_count", 0))
    clauses = {
        "every_sealed_digest_recomputes": bool(invariance.get("all_digests_equal")),
        "exactly_one_validation_evaluation_run_record": (
            int(invariance.get("validation_evaluation_run_records", -1)) == 1
        ),
        "validation_window_engine_runs_equals_declared": (
            int(invariance.get("validation_window_engine_runs", -1)) == declared_runs
            and declared_runs == 2
        ),
        "no_parameter_differs_from_the_seal": bool(invariance.get("parameters_unchanged")),
    }
    evidence = {
        "clauses": clauses,
        "digest_rows": invariance.get("digest_rows"),
        "digests_equal": invariance.get("digests_equal"),
        "digests_total": invariance.get("digests_total"),
        "validation_evaluation_run_records": invariance.get("validation_evaluation_run_records"),
        "validation_window_engine_runs": invariance.get("validation_window_engine_runs"),
        "declared_run_count": declared_runs,
        "parameter_comparison": invariance.get("parameter_comparison"),
        "strategy_invariance": invariance.get("strategy_invariance"),
        "conflict": invariance.get("conflict_note"),
        "boundary": sealed["boundary"],
        "scope_note": sealed["scope_note"],
    }
    failing = sorted(name for name, held in clauses.items() if not held)
    return _verdict(
        criteria, "S4-C7", MET if not failing else NOT_MET,
        note=(
            "All four sealed clauses hold; exact digest equality with no tolerance."
            if not failing
            else "Clauses not satisfied: " + ", ".join(failing) + ". The sealed "
            "not_evaluable_treatment makes missing or excess evidence NOT_MET rather than "
            "NOT_EVALUABLE."
        ),
        evidence=evidence,
    )


# -- the conjunction --------------------------------------------------------------------------


def evaluate_gate4(
    criteria: Mapping[str, Any],
    *,
    representative: str,
    base: Mapping[str, Any],
    stress: Mapping[str, Any],
    folds: Sequence[Mapping[str, Any]],
    invariance: Mapping[str, Any],
) -> dict[str, Any]:
    """Every condition, the conjunction, and the verdict token derived from the seal.

    The token is read out of ``verdict_token_derivation`` rather than written here, and the
    incoherent combinations the criteria file refuses are checked before the result is returned. A
    caller cannot obtain a PASS from this function without every condition being MET.
    """

    thresholds = check_thresholds_against_seal(criteria)

    verdicts = [
        condition_1(criteria, base),
        condition_2(criteria, base),
        condition_3(criteria, base),
        condition_4(criteria, base),
        condition_5(criteria, stress),
        condition_6(criteria, folds),
        condition_7(criteria, invariance),
    ]
    if tuple(v.id for v in verdicts) != CONDITION_IDS:
        raise ConfigViolation("the Gate 4 conditions were evaluated out of their sealed order")
    if len(criteria["conditions"]) != len(CONDITION_IDS):
        raise ConfigViolation(
            f"the seal carries {len(criteria['conditions'])} conditions; Gate 4 evaluates "
            f"{len(CONDITION_IDS)}. S4-CONFLICT-1 exists precisely because a condition can go "
            "missing between two representations."
        )

    tokens = criteria["verdict_token_derivation"]
    passed = all(v.verdict == MET for v in verdicts)
    satisfied = all(v.satisfied for v in verdicts)
    if passed != satisfied:
        # No Gate 4 condition is expected to be NOT_APPLICABLE, and the integrity rules say so.
        # If one ever were, "satisfied" and "MET" would diverge and the divergence must surface.
        raise ConfigViolation(
            "a Gate 4 condition returned NOT_APPLICABLE_BY_CONDITION_TEXT; the sealed integrity "
            "rules state that no Gate 4 condition is expected to be NOT_APPLICABLE, so this is a "
            "specification question and not something to aggregate over."
        )

    token = str(tokens["pass_token"] if passed else tokens["fail_token"])
    not_met = [v.id for v in verdicts if v.verdict == NOT_MET]
    not_evaluable = [v.id for v in verdicts if v.verdict == NOT_EVALUABLE]
    not_applicable = [v.id for v in verdicts if v.verdict == NOT_APPLICABLE]

    if passed and (not_met or not_evaluable):
        raise ConfigViolation("refused: a PASS with a condition that is not MET")
    if not passed and not (not_met or not_evaluable):
        raise ConfigViolation("refused: a FAIL with every condition MET")

    return {
        "gate_id": int(criteria["gate_id"]),
        "gate_name": str(criteria["gate_name"]),
        "representative": representative,
        "within_candidate": "CONJUNCTIVE",
        "across_candidates": "NOT_APPLICABLE_EXACTLY_ONE_REPRESENTATIVE",
        "conjunctive_note": str(tokens["conjunctive_note"]),
        "conditions": [v.to_json() for v in verdicts],
        "condition_count": len(verdicts),
        "met": [v.id for v in verdicts if v.verdict == MET],
        "not_met": not_met,
        "not_evaluable": not_evaluable,
        "not_applicable": not_applicable,
        "gate_passed": passed,
        "verdict_token": token,
        "verdict_token_source": (
            "config/stage4_gate_criteria.json verdict_token_derivation."
            + ("pass_token" if passed else "fail_token")
        ),
        "verdict": ("PASS — " if passed else "FAIL — ") + token,
        "thresholds_cross_checked": thresholds,
    }
