"""Gate 3 for Generation 2 Attempt 2: two conditions imported, five measured on the episode ledger.

``config/generation_2/g2_gate_criteria_ra1.json`` (SE100-CFG-3104) names this module twice, in
S3-C5's ``implementation`` and in S3-C7's, and says of both that Generation 1's
``stockedge100.strategies.gate`` "and Attempt 1's ``stockedge100.strategies.g2_gate`` are not called
for Attempt 2 and neither is modified". That is the shape of this file. It *imports* Generation 1's
evaluator for the two conditions whose measurement basis Attempt 2 leaves alone, supplies its own
implementation for the five it does not, and imports nothing at all from Attempt 1's ``g2_gate``.

**Which conditions change and why.** The seal's ``relationship_to_attempt_1_criteria`` records
``measurement_basis_changed`` as S3-C3, S3-C4, S3-C5 and S3-C6, all four for one reason —
``G2A2-CONFLICT-18``, the episode ledger. Attempt 1's strategy could only ever sell a position
whole, so a ``Portfolio.Trade`` and a position's whole life were the same object. Attempt 2's
throttle and ladder trim positions, and the frozen recorder attributes a trim's proceeds to no trade
at all; the probe that established the conflict found a case where the dropped amount exceeded the
retained one and reversed its sign. Those four conditions therefore read
:func:`~stockedge100.backtest.g2_episodes_ra1.build_episode_ledger`, not ``result.trades``.

S3-C1 and S3-C2 read the engine's own equity curve, which is exact whether or not a position was
trimmed, so they are imported from Generation 1 unchanged. S3-C7 reads only the *sign* of each
neighbour's equity-curve total return and so inherits that exactness — but it is reimplemented here
anyway, because the seal forbids calling either earlier module and because its neighbour set is
built from Attempt 2's grid. The reimplementation is structurally identical to Attempt 1's by
design: an identical condition that computed a different answer would be the defect.

**S3-C5's ``j2``** is the largest P&L in signed currency terms — the biggest dollar winner — not the
largest ``abs(pnl)``. That reading was established by Generation 1's ``condition_5`` and its
docstring, the sealed wording is character-identical across all three criteria files, and the seal
here says the stricter both-removals reading is "carried over unchanged from Generation 1 and
Attempt 1". Removing a large *loss* would raise the remaining return, which is the opposite of the
stress the condition applies.

Every threshold, token, axis ordering and predicate below is read from the sealed criteria file. No
token string and no digest is written as a literal here.
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
from stockedge100.backtest.errors import ConfigViolation, DataIntegrityHalt, InvariantViolation
from stockedge100.backtest.metrics import profit_factor

from stockedge100.backtest.g2_episodes_ra1 import (
    CONFLICT_ID,
    LEDGER_ID,
    RECONCILED_FIELDS,
    EpisodeLedger,
    build_episode_ledger,
)

# Generation 1's evaluator, imported and never modified. ``condition_1`` and ``condition_2`` are the
# two the seal records as unchanged in measurement basis; the verdict vocabulary, ``_condition``,
# ``_threshold``, ``_sign``, ``CONCENTRATION_MAX`` and the seal check are reused rather than
# restated so the implementations cannot drift apart in a detail nobody is watching.
from stockedge100.strategies.gate import (
    CONCENTRATION_MAX,
    MET,
    NOT_APPLICABLE,
    NOT_EVALUABLE,
    NOT_MET,
    ConditionVerdict,
    _condition,
    _sign,
    _threshold,
    check_thresholds_against_seal,
    condition_1,
    condition_2,
)
from stockedge100.strategies.runner import contribution_by_symbol, trade_pnls

from stockedge100.backtest.g2_engine_ra1 import load_risk_architecture
from stockedge100.strategies.g2_rotation_ra1 import (
    STRATEGY_ID,
    RotationCandidateRA1,
    RotationVariantRA1,
    eligible_universe,
    load_protocol,
    rotation_variants,
)

__all__ = [
    "AXIS_NAMES",
    "CRITERIA_ID",
    "CRITERIA_PATH",
    "G2PlanRA1",
    "assert_reconciliation_non_vacuous",
    "attempt_1_tokens",
    "build_plan",
    "condition_3_ra1",
    "condition_4_ra1",
    "condition_5_ra1",
    "condition_6_ra1",
    "condition_7_ra1",
    "entry_equity_bases",
    "evaluate_representative_ra1",
    "expected_neighbour_count",
    "load_criteria",
    "neighbours_of",
    "stage_verdict_ra1",
]

CRITERIA_PATH = PROJECT_ROOT / "config" / "generation_2" / "g2_gate_criteria_ra1.json"
CRITERIA_ID = "SE100-CFG-3104"

#: The Attempt 1 criteria file this one declares itself a counterpart of. The path is asserted to
#: appear in the seal's own ``attempt_1_counterpart`` string rather than standing alone, and the
#: digest is read from the seal and recomputed — never written here. Attempt 1's criteria are read
#: (for its two verdict tokens, which Attempt 2 must refuse to emit) and never written.
ATTEMPT_1_COUNTERPART_REL = "config/generation_2/g2_gate_criteria.json"

#: Likewise for Generation 1's, whose digest this file also pins.
GENERATION_1_COUNTERPART_REL = "config/stage3_gate_criteria.json"

ONE = Decimal(1)

#: The three axes, in the sealed order. Used only to check that the criteria file and the protocol
#: file agree with each other; the values compared against come from those files, not from here.
AXIS_NAMES = ("lookback_months", "top_k", "rebalance_frequency")


# -- the seal ------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_criteria() -> dict[str, Any]:
    """The sealed Gate 3 criteria for Attempt 2, refusing to load anything that is not them.

    ``evaluation_integrity_rules`` §10: "The gate threshold seal check runs before any condition is
    evaluated: the five frozen thresholds, the S3-C6 predicate text and the S3-C4 exception flag are
    asserted unchanged against the constitution." Calling
    :func:`~stockedge100.strategies.gate.check_thresholds_against_seal` here is strictly earlier than
    that — the criteria cannot be *obtained* without those checks having passed, so there is no code
    path that reaches a condition with an unchecked seal.
    """

    criteria = json.loads(CRITERIA_PATH.read_text(encoding="utf-8"))
    if criteria.get("artifact_id") != CRITERIA_ID:
        raise ConfigViolation(
            f"{CRITERIA_PATH} carries artifact_id {criteria.get('artifact_id')!r}, not {CRITERIA_ID!r}"
        )
    if criteria.get("generation") != 2 or criteria.get("stage") != 3 or criteria.get("attempt") != 2:
        raise ConfigViolation(
            f"{CRITERIA_ID} is generation {criteria.get('generation')!r} stage "
            f"{criteria.get('stage')!r} attempt {criteria.get('attempt')!r}; this evaluator is "
            "Generation 2 Stage 3 Attempt 2 only"
        )
    if criteria.get("declared_before_any_strategy_code") is not True:
        raise ConfigViolation(
            f"{CRITERIA_ID} does not assert declared_before_any_strategy_code; a gate that was not "
            "declared before results is not a gate"
        )
    _check_counterpart(criteria, "attempt_1_counterpart", ATTEMPT_1_COUNTERPART_REL)
    _check_counterpart(criteria, "generation_1_counterpart", GENERATION_1_COUNTERPART_REL)
    check_thresholds_against_seal(criteria)
    _check_axes_agree(criteria)
    _check_tokens_are_attempt_2s_own(criteria)
    return criteria


def _check_counterpart(criteria: dict[str, Any], key: str, relative: str) -> None:
    """A counterpart named by the seal must exist at that path and hash to the pinned digest.

    Both counterparts are frozen — Generation 1's by its Stage 3 and Stage 4 checksum records,
    Attempt 1's by ``STAGE_3_G2_ROTATION_PROTOCOL.sha256`` — so a mismatch is something to report,
    never something to reconcile.
    """

    declared = criteria.get(key, "")
    if relative not in declared:
        raise ConfigViolation(
            f"{CRITERIA_ID} names {key} {declared!r}, which is not {relative!r}"
        )
    measured = sha256_file(PROJECT_ROOT / relative)
    pinned = criteria[f"{key}_sha256"]
    if measured != pinned:
        raise ConfigViolation(
            f"{relative} hashes to {measured}, but {CRITERIA_ID} pins {pinned}; that file is frozen, "
            "so report this rather than reconciling it"
        )


def _check_axes_agree(criteria: dict[str, Any]) -> None:
    """S3-C7's ``axis_orderings`` and the RA1 protocol's ``grid.axes`` must be the same three axes.

    They are sealed in two separate files. If they ever disagreed, the neighbour set would be derived
    from one grid and the runs from the other, and S3-C7 would silently be comparing the
    representative against variants that were never run.
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


@lru_cache(maxsize=1)
def attempt_1_tokens() -> tuple[str, str]:
    """Attempt 1's two verdict tokens, read from Attempt 1's own sealed criteria file.

    The Attempt 2 seal states in prose that "STAGE_3_G2_STRATEGY_ADMITTED_IN_DEVELOPMENT and
    STAGE_3_G2_NO_CANDIDATE belong to Attempt 1. No Attempt 2 artifact may emit either." Rather than
    restate those two strings here, they are read from the file that defines them — whose digest
    :func:`_check_counterpart` has already recomputed against the pin — and the prose is then checked
    to name both. Two files agreeing is evidence; one file quoting itself is not.
    """

    counterpart = json.loads(
        (PROJECT_ROOT / ATTEMPT_1_COUNTERPART_REL).read_text(encoding="utf-8")
    )
    derivation = counterpart["verdict_token_derivation"]
    return derivation["pass_token"], derivation["fail_token"]


def _check_tokens_are_attempt_2s_own(criteria: dict[str, Any]) -> None:
    """Attempt 2's two tokens must be Attempt 2's, and must not be Attempt 1's.

    A criteria file copied forward and edited incompletely would be caught nowhere else: every
    threshold, predicate and axis would check out, and the stage would emit a token belonging to an
    attempt that is closed.
    """

    derivation = criteria["verdict_token_derivation"]
    ours = (derivation["pass_token"], derivation["fail_token"])
    theirs = attempt_1_tokens()
    if set(ours) & set(theirs):
        raise ConfigViolation(
            f"{CRITERIA_ID} declares verdict tokens {ours} which collide with Attempt 1's {theirs}; "
            "Attempt 1 is closed and its tokens are not available here"
        )
    prose = derivation["attempt_1_tokens_are_not_available_here"]
    for token in theirs:
        if token not in prose:
            raise ConfigViolation(
                f"{CRITERIA_ID} does not name Attempt 1's token {token!r} in "
                "attempt_1_tokens_are_not_available_here, so the two seals do not agree about which "
                "tokens are withheld"
            )


# -- the plan the applicability of S3-C6 is decided from -----------------------------------------


@dataclass(frozen=True)
class G2PlanRA1:
    """What S3-C6 and the result header read off a plan.

    Carries the sealed span *recheck requirement* rather than a warmup session count. Attempt 2's
    lookback is a number of calendar months and the run start is derived from a month offset against
    the latest inception in the universe, so a session count would be a number invented to satisfy a
    constructor — which is exactly what an evidence field must never contain.
    """

    experiment_id: str
    family: str
    declared_universe: tuple[str, ...]
    run_start: dt.date
    run_end: dt.date
    binding_symbol: str
    sessions: int
    span_recheck_requirement: str
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
            "risk_architecture_id": self.risk_architecture_id,
        }


@lru_cache(maxsize=1)
def build_plan() -> G2PlanRA1:
    """The declared plan, entirely from the seals."""

    run = load_protocol()["run_span"]
    return G2PlanRA1(
        experiment_id=STRATEGY_ID,
        family=RotationCandidateRA1.family,
        declared_universe=eligible_universe(),
        run_start=dt.date.fromisoformat(run["run_start"]),
        run_end=dt.date.fromisoformat(run["run_end"]),
        binding_symbol=run["binding_symbol"],
        sessions=int(run["sessions"]),
        span_recheck_requirement=run["recheck_requirement"],
        risk_architecture_id=load_risk_architecture().architecture_id,
    )


# -- §9, the non-vacuity guard -------------------------------------------------------------------


def assert_reconciliation_non_vacuous(ledger: EpisodeLedger) -> dict[str, Any]:
    """``evaluation_integrity_rules`` §9, and the one case where it must not halt.

    §9: "That reconciliation must not be allowed to pass vacuously. The evaluator asserts that the
    number of single-leg episodes compared is greater than zero before asserting that they agree, and
    reports the compared count alongside the mismatch count. A run in which no episode closed would
    otherwise satisfy the reconciliation by having nothing to reconcile."

    The failure §9 exists to prevent is a reconciliation *reported as agreeing* having compared
    nothing. There are two ways to compare nothing, and they are not the same event:

    * **Closed episodes exist and not one of them is single-leg.** Then something was there to
      compare and nothing was compared, the reduction property of ``G2A2-CONFLICT-18`` was asserted
      about no case at all, and this halts.
    * **No episode closed.** Then there is nothing to reconcile in the first place. Halting here
      would replace a recorded FAIL with a crash: S3-C4 measures zero against a floor of thirty and
      is NOT_MET, S3-C3 is NOT_EVALUABLE and fails, so the stage already fails on evidence that the
      constitution requires to stay on disk. The vacuity is recorded in the returned record and in
      both conditions' evidence instead, and no pass can be manufactured from it.

    Returns the §9 report — compared count beside mismatch count — for the evidence blocks.
    """

    reconciliation = ledger.reconciliation
    report = {
        "rule": "evaluation_integrity_rules[9]",
        "ledger_id": LEDGER_ID,
        "conflict_id": CONFLICT_ID,
        "reconciled_fields": list(RECONCILED_FIELDS),
        "single_leg_compared": reconciliation.single_leg_compared,
        "mismatch_count": len(reconciliation.mismatches),
        "closed_episodes": reconciliation.closed_episodes,
        "closed_trades": reconciliation.closed_trades,
        "counts_agree": reconciliation.counts_agree,
        "vacuous": reconciliation.vacuous,
        "reconciled": reconciliation.reconciled,
        "nothing_closed": reconciliation.closed_episodes == 0,
        "total_trimmed_proceeds": f"{reconciliation.total_trimmed_proceeds:f}",
        "pnl_discrepancy": f"{reconciliation.pnl_discrepancy:f}",
    }
    if reconciliation.vacuous and reconciliation.closed_episodes > 0:
        raise DataIntegrityHalt(
            f"{CONFLICT_ID}: {reconciliation.closed_episodes} episode(s) closed and not one has a "
            "single sale leg, so the reduction property was asserted about nothing. "
            "evaluation_integrity_rules section 9 requires the compared count to exceed zero before "
            "agreement is asserted; evaluation halts."
        )
    return report


def _assert_counting_identity(result: BacktestResult, ledger: EpisodeLedger) -> None:
    """S3-C4's ``counting_identity``, "asserted equal at evaluation time rather than assumed".

    ``_reconcile`` already halts on a count difference, so reaching a disagreement here would mean
    the ledger handed to the gate is not the ledger built from this result. That is worth catching:
    the two arguments arrive separately and nothing else would notice them being mismatched.
    """

    episodes = len(ledger.closed_episodes)
    trades = len(result.trades)
    if episodes != trades:
        raise DataIntegrityHalt(
            f"S3-C4 counting_identity: {episodes} closed episode(s) against {trades} closed "
            f"trade(s) on run {result.label!r}/{result.scenario!r}. A closed episode and a closed "
            "Portfolio.Trade are the same event, so a difference means the ledger and the result are "
            "not describing the same run."
        )


# -- S3-C3, on the episode ledger ----------------------------------------------------------------


@exact
def condition_3_ra1(
    result: BacktestResult, ledger: EpisodeLedger, criteria: dict[str, Any]
) -> ConditionVerdict:
    """"profit factor is at least 1.10", over closed **episodes**.

    Both figures are reported, as the seal requires: profit factor over the episode ledger, which
    gates, and profit factor over ``Portfolio.trades``, which does not. The frozen
    :func:`~stockedge100.backtest.metrics.profit_factor` computes both — it is not modified and is
    still called for the reconciliation figure. Where the two differ, the difference is the trimmed
    proceeds the frozen recorder drops.

    The sealed undefined cases are distinguished by name. ``no_closed_episodes`` is NOT_EVALUABLE and
    the condition FAILS; ``no_losing_episodes`` with positive gross profit is MET with the raw null
    preserved in the evidence, "never as infinity".
    """

    spec = _condition(criteria, "S3-C3")
    minimum = _threshold(criteria["frozen_gate_json_companion_verbatim"]["thresholds"]["profit_factor_min"])

    pnls = list(ledger.pnls)
    gross_profit = sum((value for value in pnls if value > ZERO), ZERO)
    gross_loss = -sum((value for value in pnls if value < ZERO), ZERO)

    # The reconciliation figure. Reported, never compared against the threshold.
    frozen_pnls = trade_pnls(result)
    frozen_factor = profit_factor(frozen_pnls)

    evidence: dict[str, Any] = {
        "basis": spec["measurement"],
        "closed_episodes": len(pnls),
        "gross_profit": f"{gross_profit:f}",
        "gross_loss": f"{gross_loss:f}",
        "reconciliation": {
            "closed_trades": len(frozen_pnls),
            "profit_factor_over_portfolio_trades": (
                None if frozen_factor is None else f"{frozen_factor:f}"
            ),
            "total_trimmed_proceeds": f"{ledger.reconciliation.total_trimmed_proceeds:f}",
            "pnl_discrepancy": f"{ledger.reconciliation.pnl_discrepancy:f}",
            "single_leg_compared": ledger.reconciliation.single_leg_compared,
            "mismatch_count": len(ledger.reconciliation.mismatches),
            "note": spec["attempt_2_note"],
        },
    }

    if not pnls:
        evidence["vacuity"] = "no episode closed; nothing was available to reconcile (rule 9)"
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            measured=None, threshold=f">= {minimum:f}",
            note=spec["undefined_cases"]["no_closed_episodes"], evidence=evidence,
        )

    measured = profit_factor(pnls)
    if measured is None:
        # "the raw null preserved in the evidence rather than replaced by a number"
        evidence["profit_factor_raw"] = None
        if gross_profit > ZERO:
            return ConditionVerdict(
                spec["id"], spec["required_verbatim"], MET,
                measured=None, threshold=f">= {minimum:f}",
                note="UNDEFINED_NO_LOSSES_TREATED_AS_MET: " + spec["undefined_cases"]["no_losing_episodes"],
                evidence=evidence,
            )
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            measured=None, threshold=f">= {minimum:f}",
            note=(
                "profit factor is undefined with neither gross profit nor gross loss; the sealed "
                "no-losing-episodes allowance requires positive gross profit and does not reach "
                "this case"
            ),
            evidence=evidence,
        )

    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
        MET if measured >= minimum else NOT_MET,
        measured=f"{measured:f}", threshold=f">= {minimum:f}", evidence=evidence,
    )


# -- S3-C4, on the episode ledger ----------------------------------------------------------------


def condition_4_ra1(
    result: BacktestResult, ledger: EpisodeLedger, criteria: dict[str, Any]
) -> ConditionVerdict:
    """"at least 30 closed trades exist" — counted as closed **episodes**.

    The predicate is the only one whose string changed between the attempts, ``closed_trades >= 30``
    becoming ``closed_episodes >= 30``. The threshold and the relation are unchanged, and the seal
    records why the rename cannot change a verdict: the two counts are equal on every run, because a
    closed episode and a closed ``Portfolio.Trade`` are the same event. That equality is asserted
    here rather than assumed.

    There is no NOT_EVALUABLE path. A count is defined for every run and a run with no closed
    episodes has a count of zero, which is a measured value that fails the floor rather than absent
    evidence.
    """

    spec = _condition(criteria, "S3-C4")
    _assert_counting_identity(result, ledger)
    minimum = int(criteria["frozen_gate_json_companion_verbatim"]["thresholds"]["closed_trades_min"])
    measured = len(ledger.closed_episodes)
    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
        MET if measured >= minimum else NOT_MET,
        measured=str(measured), threshold=f">= {minimum}",
        note=spec["exception_note"],
        evidence={
            "basis": spec["measurement"],
            "exception_invoked": spec["exception_invoked"],
            "counting_identity": spec["counting_identity"],
            "closed_episodes": measured,
            "closed_trades": len(result.trades),
            "counts_agree": measured == len(result.trades),
            "open_episodes_at_end": len(ledger.open_episodes),
            "open_positions_at_end": len(result.open_positions),
            "trimmed_but_not_closed": sum(
                1 for episode in ledger.open_episodes if episode.sale_leg_count > 0
            ),
            "not_evaluable_treatment": spec["not_evaluable_treatment"],
        },
    )


# -- S3-C5, on the episode ledger and the engine's own curve -------------------------------------


def entry_equity_bases(result: BacktestResult, ledger: EpisodeLedger) -> list[Decimal]:
    """E_entry[i] for every closed episode, in closing order, by the sealed procedure.

    "For the i-th closed episode, E_entry[i] = account equity at the CLOSE of the session immediately
    preceding that episode's entry fill, read from the engine's own equity curve. If the entry fill
    is on the first session of the run, E_entry[i] = starting equity = 100.00."

    The curve has one point per session, so "the session immediately preceding" is the preceding
    *curve index*, not the preceding calendar day — a Tuesday entry after a Monday holiday is based
    on the previous Friday's close, which is the last close that existed. Where an episode was folded
    from several buys, ``entry_session`` is the first of them: the seal says "that episode's entry
    fill", and the episode's life begins at the fill that opened it.
    """

    index_by_session = {point.session: position for position, point in enumerate(result.equity_curve)}
    bases: list[Decimal] = []
    for episode in ledger.closed_episodes:
        position = index_by_session.get(episode.entry_session)
        if position is None:
            raise InvariantViolation(
                f"episode in {episode.symbol} entered {episode.entry_session.isoformat()}, which is "
                "not a session on the engine's own equity curve; the result is internally inconsistent"
            )
        bases.append(result.starting_equity if position == 0 else result.equity_curve[position - 1].equity)
    return bases


@exact
def condition_5_ra1(
    result: BacktestResult, ledger: EpisodeLedger, criteria: dict[str, Any]
) -> ConditionVerdict:
    """"removing the single best trade leaves total return above 0%", on closed episodes.

    Two removals, both of which must leave a positive return: ``j1`` the largest equity multiple,
    ``j2`` the largest signed-dollar P&L. Ties resolve to the earliest index through Generation 1's
    ``(value, -index)`` key, carried over so the removal is deterministic.

    The reconstruction is *not* expected to equal the equity-curve total return and no attempt is
    made to make it so. Concurrent positions mean the products do not telescope; dividends credited
    outside an episode and positions still open on the final session also contribute; and under
    Attempt 2 the exposure scalar changes within an episode's life. Both figures and their gap are
    reported side by side, as the sealed ``disclosure_requirement`` demands.
    """

    spec = _condition(criteria, "S3-C5")
    episodes = ledger.closed_episodes
    if len(episodes) < 2:
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            note=spec["not_evaluable_treatment"],
            evidence={"closed_episodes": len(episodes), "basis": spec["measurement"]["basis"]},
        )

    pnls = [episode.pnl for episode in episodes]
    bases = entry_equity_bases(result, ledger)
    first_session = result.equity_curve[0].session
    first_session_entries = sum(1 for episode in episodes if episode.entry_session == first_session)

    if any(base <= ZERO for base in bases):
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            note=(
                "at least one episode was entered against zero or negative account equity, so its "
                "per-episode equity multiple is not defined"
            ),
            evidence={"closed_episodes": len(episodes), "basis": spec["measurement"]["basis"]},
        )

    multiples = [ONE + pnl / base for pnl, base in zip(pnls, bases)]
    if any(multiple <= ZERO for multiple in multiples):
        return ConditionVerdict(
            spec["id"], spec["required_verbatim"], NOT_EVALUABLE,
            note=(
                "at least one episode lost more than the entire account equity that existed when it "
                "was entered, so the product of multiples is not a return"
            ),
            evidence={"closed_episodes": len(episodes), "basis": spec["measurement"]["basis"]},
        )

    def product_excluding(index: int | None) -> Decimal:
        total = ONE
        for position, multiple in enumerate(multiples):
            if position != index:
                total *= multiple
        return total - ONE

    reconstructed = product_excluding(None)
    equity_curve_return = result.total_return()

    j1 = max(range(len(multiples)), key=lambda i: (multiples[i], -i))
    j2 = max(range(len(pnls)), key=lambda i: (pnls[i], -i))

    removed_1 = product_excluding(j1)
    removed_2 = product_excluding(j2)
    both_positive = removed_1 > ZERO and removed_2 > ZERO

    def detail(index: int) -> dict[str, Any]:
        episode = episodes[index]
        return {
            "episode_index": index,
            "close_index": episode.close_index,
            "symbol": episode.symbol,
            "entry_session": episode.entry_session.isoformat(),
            "exit_session": None if episode.exit_session is None else episode.exit_session.isoformat(),
            "sale_legs": episode.sale_leg_count,
            "single_leg": episode.single_leg,
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
            "closed_episodes": len(episodes),
            "multi_leg_episodes": ledger.reconciliation.multi_leg_episodes,
            # The sealed disclosure_requirement: reconstruction, equity curve, and the gap, side by
            # side. The gap is expected to be non-zero and is not reconciled.
            "reconstructed_total_return": f"{reconstructed:f}",
            "equity_curve_total_return": f"{equity_curve_return:f}",
            "reconstruction_gap": f"{reconstructed - equity_curve_return:f}",
            "disclosure_requirement": spec["measurement"]["disclosure_requirement"],
            "which_trade_is_removed": spec["measurement"]["which_trade_is_removed"],
            "tie_handling": spec["measurement"]["tie_handling"],
            "j2_reading": (
                "largest P&L in signed currency terms, not largest abs(pnl); carried over from "
                "Generation 1's condition_5, whose docstring establishes the reading"
            ),
            "episodes_entered_on_first_session": first_session_entries,
            "distinct_entry_equity_bases": len({f"{base:f}" for base in bases}),
            "j1_largest_equity_multiple": detail(j1),
            "j2_largest_absolute_pnl": detail(j2),
            "j1_equals_j2": j1 == j2,
        },
    )


# -- S3-C6, on the episode ledger ----------------------------------------------------------------


@exact
def condition_6_ra1(
    result: BacktestResult, ledger: EpisodeLedger, plan: G2PlanRA1, criteria: dict[str, Any]
) -> ConditionVerdict:
    """"no single instrument contributes more than 50% of total strategy profit".

    Applicability is decided by the DECLARED universe, never by the realized symbol count. Attempt 2
    declares the full 34-member frozen list at every rebalance, so this condition applies
    unconditionally; the single-instrument branch is retained because the seal retains it, and is not
    reachable here.

    This is the condition ``G2A2-CONFLICT-18`` distorts most. Attribution is a ratio of one symbol's
    P&L to the total, so dropping a trim's proceeds corrupts both the numerator and the denominator.
    The gating figure is over closed episodes; the frozen-trade attribution is reported beside it, per
    symbol, so the size of the distortion is visible rather than asserted.
    """

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

    contributions = ledger.pnl_by_symbol()
    total = sum(contributions.values(), ZERO)
    frozen_contributions = contribution_by_symbol(result)
    frozen_total = sum(frozen_contributions.values(), ZERO)

    evidence: dict[str, Any] = {
        "basis": spec["measurement"],
        "applies_to": spec["scope_interpretation"]["applies_to"],
        "why_it_always_applies": spec["scope_interpretation"]["why_it_always_applies"],
        "declared_instrument_count": instruments,
        "declared_universe": list(plan.declared_universe),
        "distinct_symbols_traded": len(contributions),
        "total_closed_episode_pnl": f"{total:f}",
        "pnl_by_instrument": {symbol: f"{value:f}" for symbol, value in sorted(contributions.items())},
        "reconciliation": {
            "total_closed_trade_pnl": f"{frozen_total:f}",
            "pnl_by_instrument_over_portfolio_trades": {
                symbol: f"{value:f}" for symbol, value in sorted(frozen_contributions.items())
            },
            "per_instrument_difference": {
                symbol: f"{contributions.get(symbol, ZERO) - frozen_contributions.get(symbol, ZERO):f}"
                for symbol in sorted(set(contributions) | set(frozen_contributions))
            },
            "why_the_basis_matters_here": spec["why_the_basis_matters_here"],
        },
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
    evidence["attempt_2_significance"] = spec["scope_interpretation"]["attempt_2_significance"]
    return ConditionVerdict(
        spec["id"], spec["required_verbatim"],
        MET if largest <= CONCENTRATION_MAX else NOT_MET,
        measured=f"{largest:f}", threshold=f"<= {CONCENTRATION_MAX:f}", evidence=evidence,
    )


# -- S3-C7, on the Attempt 2 grid ----------------------------------------------------------------


def _axis_values(variant: RotationVariantRA1) -> dict[str, Any]:
    return {
        "lookback_months": variant.lookback_months,
        "top_k": variant.top_k,
        "rebalance_frequency": variant.frequency,
    }


def expected_neighbour_count(variant: RotationVariantRA1, criteria: dict[str, Any]) -> int:
    """The sealed count rule, computed independently of the neighbour construction.

    "3 when the representative is at an endpoint of both the lookback and the k axis; 5 when it is
    interior on both; 4 otherwise." One step on each side of an interior value, one step on the only
    side of an endpoint, and the two-valued frequency axis always contributes exactly one. Computing
    it from the axis orderings rather than from the constructed set is what makes the count a check
    on the construction instead of a restatement of it.
    """

    orderings = _condition(criteria, "S3-C7")["measurement"]["axis_orderings"]
    values = _axis_values(variant)
    total = 0
    for axis in AXIS_NAMES:
        ordering = list(orderings[axis])
        position = ordering.index(values[axis])
        total += (1 if position > 0 else 0) + (1 if position < len(ordering) - 1 else 0)
    return total


def neighbours_of(
    variant: RotationVariantRA1, criteria: dict[str, Any]
) -> tuple[RotationVariantRA1, ...]:
    """"Every variant in the eighteen-variant Attempt 2 grid that differs ... in exactly one axis by
    exactly one step."

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
    found: list[RotationVariantRA1] = []
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
                    "the eighteen-variant Attempt 2 grid"
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
def condition_7_ra1(
    primary: BacktestResult,
    neighbours: Sequence[tuple[RotationVariantRA1, BacktestResult | None]],
    criteria: dict[str, Any],
    *,
    variant: RotationVariantRA1,
) -> ConditionVerdict:
    """"reasonable neighboring parameter values do not reverse the sign of net return".

    "zero matches nothing", so a neighbour or a representative that lands exactly flat fails the
    condition rather than being counted as agreeing with everything. A neighbour that did not run is
    NOT_RUN, which the seal states is not a pass.

    The supplied neighbour set is checked against the set this representative's grid position
    requires — passing a hand-picked subset would turn a structural condition into a chosen one. Each
    neighbour is read for the sign of its base-run equity-curve total return and nothing else, and no
    neighbour is ever promoted to representative (``selection_prohibition``).

    The five RA1 risk constants are identical across all eighteen variants, so no neighbour differs
    from the representative in any risk parameter. Per ``G2A2-CONFLICT-22``, a MET verdict here says
    nothing whatever about the robustness of the risk architecture.
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
            "one_step_note": spec["measurement"]["one_step_note"],
            "representative_variant_id": variant.variant_id,
            "representative_grid_index": variant.index,
            "primary_total_return": f"{primary_return:f}",
            "primary_sign": primary_sign,
            "neighbours_not_run": not_run,
            "what_is_read": spec["measurement"]["what_is_read"],
            "no_new_runs": spec["measurement"]["no_new_runs"],
            "risk_constants_have_no_neighbours": spec["measurement"]["risk_constants_have_no_neighbours"],
            "neighbours": rows,
        },
    )


# -- combination ---------------------------------------------------------------------------------


def evaluate_representative_ra1(
    *,
    variant: RotationVariantRA1,
    primary: BacktestResult,
    neighbours: Sequence[tuple[RotationVariantRA1, BacktestResult | None]],
    criteria: dict[str, Any],
    ledger: EpisodeLedger | None = None,
    plan: G2PlanRA1 | None = None,
) -> dict[str, Any]:
    """All seven conditions for the one representative, combined conjunctively.

    Rule 6: "The representative is selected before any condition is evaluated, by the return-blind
    rule in SE100-CFG-3103. Condition evaluation cannot feed back into selection, because selection
    has already happened and is not repeated." Rule 7: "If the representative fails any condition,
    the stage fails. No other variant is evaluated against the gate." Nothing here inspects any
    variant other than the representative and its structural neighbours, and the neighbours are read
    for the sign of net return and nothing else.

    Order matters and is the sealed order: rule 10's threshold seal check, then rule 9's non-vacuity
    guard, then the conditions.
    """

    check_thresholds_against_seal(criteria)
    ledger = build_episode_ledger(primary) if ledger is None else ledger
    vacuity = assert_reconciliation_non_vacuous(ledger)
    plan = build_plan() if plan is None else plan

    verdicts = [
        condition_1(primary, criteria),
        condition_2(primary, criteria),
        condition_3_ra1(primary, ledger, criteria),
        condition_4_ra1(primary, ledger, criteria),
        condition_5_ra1(primary, ledger, criteria),
        condition_6_ra1(primary, ledger, plan, criteria),
        condition_7_ra1(primary, neighbours, criteria, variant=variant),
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
        "conditions_not_met": sorted(verdict.id for verdict in verdicts if verdict.verdict == NOT_MET),
        "conditions_not_evaluable": sorted(
            verdict.id for verdict in verdicts if verdict.verdict == NOT_EVALUABLE
        ),
        "conditions_not_applicable": sorted(
            verdict.id for verdict in verdicts if verdict.verdict == NOT_APPLICABLE
        ),
        "reconciliation": ledger.reconciliation.to_json(),
        "non_vacuity_check": vacuity,
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
    }


def stage_verdict_ra1(
    candidate_results: Sequence[dict[str, Any]],
    criteria: dict[str, Any],
    *,
    representative_exists: bool,
    selection_note: str,
) -> dict[str, Any]:
    """The stage verdict, with its token taken from the sealed derivation and never from a literal.

    Two distinct routes reach FAIL and the seal names both in one ``fail_condition``: "Either no
    representative exists, because every one of the eighteen variants recorded at least one
    research-shutdown event, or a representative exists and does not satisfy every hard condition."
    They are recorded separately because they mean different things about the hypothesis — the first
    says the grid never produced a candidate to test, the second says the candidate was tested and
    rejected — while producing the same token.

    Attempt 2 declares one live candidate, so the constitution's cross-candidate disjunction is over
    a set of size one; see ``G2-CONFLICT-15`` and ``G2A2-CONFLICT-24``. The token emitted is checked
    against Attempt 1's two, which are read from Attempt 1's own sealed file: Attempt 1 is closed and
    no Attempt 2 artifact may emit either.
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
    withheld = attempt_1_tokens()
    if token in withheld:
        raise ConfigViolation(
            f"verdict token {token!r} belongs to Attempt 1, which is closed; Attempt 2 may emit only "
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
        "attempt_1_tokens_withheld": list(withheld),
        "attempt_1_tokens_note": derivation["attempt_1_tokens_are_not_available_here"],
        "constitutional_fail_result_equivalent": derivation["constitutional_fail_result_equivalent"],
        "token_naming_note": derivation["token_naming_note"],
        "fail_is_a_deliverable": derivation["fail_is_a_deliverable"],
        "representative_exists": representative_exists,
        "selection_note": selection_note,
        "admitted_candidates": admitted,
        "candidates_evaluated": len(candidate_results),
        "combination_rule": derivation["conjunctive_note"],
    }
