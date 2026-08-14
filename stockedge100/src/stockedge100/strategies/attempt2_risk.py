"""RA1 — the structural exposure and loss architecture every Attempt 2 candidate shares.

The sealed protocol declares RA1 once, identically for all three candidates, and says why:

    "Declaring one architecture once, identically across candidates, means its degrees of freedom
    are counted once rather than three times. If RA1 were tuned per candidate, three candidates
    would carry three independent sets of risk parameters and the search would be three times wider
    than it appears."

So RA1 is implemented once, here, in :class:`Ra1Candidate`, and the three candidate modules supply
only :meth:`Candidate.target` — the signal. No candidate may carry a private sizing, exit, or
lockout path, for exactly the reason the seal gives.

Every docstring below quotes its sealed rule before implementing it. Where the two disagree the seal
is the specification and the code is the defect.

Two structural points that are easy to get wrong, and that the engine settles rather than leaves to
interpretation:

*A "decision session" is a session on which* :meth:`decide` *is called.* The engine's run loop calls
it at the close of every session in ``sessions_between(start, end)`` except the final session and the
session on which the research shutdown first triggers. Every RA1 counter — the high-water-mark
series, ``sessions_held``, the lockout index, the ladder tally — advances once per ``decide`` call
and never on a session the candidate does not see.

*A pending entry has always resolved by the next decision session.* The loop runs ``_execute`` for
session ``t`` before it calls ``decide`` at session ``t``, so a BUY emitted at the close of ``t`` has
either filled at the open of ``t+1`` or been rejected by the time ``decide`` runs at ``t+1``. That is
what makes RA1-3's "A pending P_ref is discarded if the symbol is absent from context.open_symbols at
the next decision session" a single one-session test rather than a queue with a timeout.

The five ``NO_ENTRY_*`` reasons are candidate-side counters, not engine rejections.
:data:`stockedge100.backtest.orders.REASONS` is a closed ten-value set and none of the five is in it;
a blocked entry emits no order at all, so there is no order for the engine to reject. The counters
therefore live on the candidate object and are read out by the Attempt 2 measurement wrapper.
``EXIT_SHUTDOWN`` is deliberately *not* defined here: the engine force-schedules that liquidation
itself with ``forced=True`` and never calls ``decide`` on the triggering session, so a candidate can
never emit it and must not pretend to count it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Sequence

from stockedge100.backtest.costs import ZERO, exact
from stockedge100.backtest.engine import DecisionContext, OrderRequest
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.orders import BUY
from stockedge100.strategies.attempt2_config import dec
from stockedge100.strategies.attempt2_indicators import VOL20_BARS, vol20
from stockedge100.strategies.base import Candidate

ONE = Decimal(1)

# -- sealed reason codes -------------------------------------------------------------------------

EXIT_LOSS_CONTROL = "EXIT_LOSS_CONTROL"
EXIT_MAX_HOLD = "EXIT_MAX_HOLD"
EXIT_SIGNAL = "EXIT_SIGNAL"

#: ``exit_precedence.order``, verbatim and in order. "When more than one exit condition is true on
#: the same decision session, the position is closed once and the attributed reason is the
#: highest-precedence condition in the order above." The seal is explicit that this is "Reason
#: attribution only. The precedence changes no exit decision."
EXIT_PRECEDENCE: tuple[str, ...] = (EXIT_LOSS_CONTROL, EXIT_MAX_HOLD, EXIT_SIGNAL)

NO_ENTRY_ZERO_VOLATILITY = "NO_ENTRY_ZERO_VOLATILITY"
NO_ENTRY_VOLATILITY_FLOOR = "NO_ENTRY_VOLATILITY_FLOOR"
NO_ENTRY_SIZE_FLOOR = "NO_ENTRY_SIZE_FLOOR"
NO_ENTRY_LOCKOUT = "NO_ENTRY_LOCKOUT"
NO_ENTRY_INSUFFICIENT_HISTORY = "NO_ENTRY_INSUFFICIENT_HISTORY"

#: The sealed ``secondary_metrics`` enumeration of blocked-entry reasons, in its sealed order.
BLOCKED_ENTRY_REASONS: tuple[str, ...] = (
    NO_ENTRY_ZERO_VOLATILITY,
    NO_ENTRY_VOLATILITY_FLOOR,
    NO_ENTRY_SIZE_FLOOR,
    NO_ENTRY_LOCKOUT,
    NO_ENTRY_INSUFFICIENT_HISTORY,
)


# -- sealed parameters --------------------------------------------------------------------------


@dataclass(frozen=True)
class Ra1Parameters:
    """The RA1 constants of one variant, read from its sealed ``parameters`` block.

    Nothing here has a default. A default would be an implementation-supplied value capable of
    changing sealed behaviour when a parameter key is missing or misspelled, and the operating
    prompt requires proving that no such default exists. A missing key raises instead.
    """

    f_base: Decimal
    vol_target: Decimal
    vol_floor_fraction: Decimal
    loss_control: Decimal
    max_hold: int
    reentry_delay: int
    ladder_rungs: tuple[tuple[Decimal, Decimal], ...]

    @classmethod
    def from_parameters(cls, parameters: dict[str, Any]) -> "Ra1Parameters":
        required = (
            "f_base",
            "vol_target",
            "vol_floor_fraction",
            "loss_control",
            "max_hold",
            "reentry_delay",
            "ladder_rungs",
        )
        missing = [key for key in required if key not in parameters]
        if missing:
            raise ConfigViolation(
                f"sealed variant parameters are missing RA1 keys {missing}; RA1 has no defaults, "
                "because a default is an implementation value able to change sealed behaviour"
            )
        rungs: list[tuple[Decimal, Decimal]] = []
        for rung in parameters["ladder_rungs"]:
            if len(rung) != 2:
                raise ConfigViolation(
                    f"sealed ladder rung {rung!r} is not a (threshold, f_cap) pair"
                )
            rungs.append((dec(rung[0]), dec(rung[1])))
        thresholds = [threshold for threshold, _ in rungs]
        if thresholds != sorted(thresholds) or len(set(thresholds)) != len(thresholds):
            raise ConfigViolation(
                f"sealed ladder thresholds {thresholds} are not strictly ascending; the RA1-5 "
                "lookup reads them in order and would otherwise depend on file order"
            )
        return cls(
            f_base=dec(parameters["f_base"]),
            vol_target=dec(parameters["vol_target"]),
            vol_floor_fraction=dec(parameters["vol_floor_fraction"]),
            loss_control=dec(parameters["loss_control"]),
            max_hold=int(parameters["max_hold"]),
            reentry_delay=int(parameters["reentry_delay"]),
            ladder_rungs=tuple(rungs),
        )

    @property
    def ladder_bands(self) -> tuple[str, ...]:
        """Readable labels for the ladder tally, derived from the rungs rather than hand-written.

        For the sealed rungs ``[["0.08","0.25"], ["0.10","0.125"]]`` this is
        ``("dd<0.08", "0.08<=dd<0.10", "dd>=0.10")``, which is RA1-5's own three-line rule.
        """

        labels = [f"dd<{self.ladder_rungs[0][0]:f}"]
        for index, (threshold, _) in enumerate(self.ladder_rungs):
            if index + 1 < len(self.ladder_rungs):
                upper = self.ladder_rungs[index + 1][0]
                labels.append(f"{threshold:f}<=dd<{upper:f}")
            else:
                labels.append(f"dd>={threshold:f}")
        return tuple(labels)

    @exact
    def f_cap(self, drawdown: Decimal) -> Decimal:
        """RA1-5: the ladder value for a decision session whose account drawdown is ``drawdown``.

        Sealed rule, for the declared rungs: "dd < 0.08: f_cap = 0.50. 0.08 <= dd < 0.10:
        f_cap = 0.25. dd >= 0.10: f_cap = 0.125."

        Read generically: the base is RA1-1's ``f_base``, and each rung's ``f_cap`` takes effect at
        ``dd >= threshold``. The comparison is ``>=`` at every rung, which is what makes the bands
        half-open exactly as the sealed text writes them. No rounding precedes the comparison.
        """

        value = self.f_base
        for threshold, capped in self.ladder_rungs:
            if drawdown >= threshold:
                value = capped
        return value

    def band_of(self, drawdown: Decimal) -> str:
        """The ladder band label for a drawdown, for the non-gating rung tally."""

        index = 0
        for position, (threshold, _) in enumerate(self.ladder_rungs):
            if drawdown >= threshold:
                index = position + 1
        return self.ladder_bands[index]


# -- the shared candidate base ------------------------------------------------------------------


class Ra1Candidate(Candidate):
    """A Stage 3 Attempt 2 candidate: a signal plus RA1, sharing one implementation of RA1.

    Subclasses implement :meth:`Candidate.target` only. :meth:`decide` is final for Attempt 2 — the
    sealed ``why_shared`` is the reason, and RA1-8's all-or-nothing rule plus RA1-7's flat-first rule
    make a private order path unrepresentable anyway.
    """

    #: Set by subclasses; used only in evidence, never in a rule.
    family: str = ""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.ra1 = Ra1Parameters.from_parameters(self.parameters)

        # -- per-run RA1 state. One candidate instance serves exactly one run.
        self._decision_index: int = -1
        self._hwm: Decimal | None = None
        # -- ``(symbol, P_ref, f)``. ``P_ref`` is RA1-3's reference close; ``f`` is the RA1-2
        # -- fraction, carried only so the realised-exposure diagnostic can tell an entry that
        # -- filled from one the engine rejected. No rule reads it.
        self._pending_entry: tuple[str, Decimal, Decimal] | None = None
        self._position_ref: tuple[str, Decimal, Decimal] | None = None
        self._sessions_held: int = 0
        self._lockout_release: dict[str, int] = {}

        # -- non-gating diagnostics. The sealed secondary_metrics require each of these, and
        # -- "Extending the non-gating report cannot affect admission."
        self.blocked_entries: dict[str, int] = {reason: 0 for reason in BLOCKED_ENTRY_REASONS}
        self.exit_reasons: dict[str, int] = {reason: 0 for reason in EXIT_PRECEDENCE}
        self.ladder_sessions: dict[str, int] = {band: 0 for band in self.ra1.ladder_bands}
        self.entry_fractions: list[Decimal] = []
        self.entry_fractions_filled: list[Decimal] = []
        self.decision_sessions: int = 0
        self.decision_sessions_shutdown_active: int = 0

    # -- the order path, final for Attempt 2 -----------------------------------------------------

    def decide(self, view: MarketView, context: DecisionContext) -> list[OrderRequest]:
        """One decision per session, per the adopted ``one_decision_per_session`` rule.

        Bookkeeping runs before the shutdown gate on purpose. The sealed
        ``engine_shutdown_relationship.candidate_behaviour`` is "A candidate emits no order on any
        decision session where context.shutdown_active is true" — it suppresses *emission*, not the
        candidate's view of the run. Skipping the state update instead would make the high-water
        mark and the lockout index depend on the shutdown, and no RA1 rule may be conditioned on the
        shutdown state (``no_candidate_reads_the_ceiling``).
        """

        self._begin_session(context)

        if context.shutdown_active:
            self.decision_sessions_shutdown_active += 1
            return []

        held = context.open_symbols
        if held:
            return self._exit_decision(view, context, held[0])
        return self._entry_decision(view, context)

    def entry_order(self, symbol: str, context: DecisionContext) -> OrderRequest:
        """Refused. Attempt 1's sizing rule is exactly what Attempt 2 replaces.

        :meth:`Candidate.entry_order` requests ``max_gross_exposure_fraction`` — 95% — of equity.
        The sealed ``shared_rules.replaced.sizing_rule`` replaces that with RA1-1, RA1-2 and RA1-5,
        "Downward only". An inherited method able to request 95% is an implementation default capable
        of changing sealed behaviour, so it is removed rather than shadowed: any code path that
        reaches it is a defect and says so instead of silently sizing at Attempt 1's exposure.
        """

        raise InvariantViolation(
            "Ra1Candidate.entry_order must never be called: Attempt 2 sizes entries through RA1-2, "
            "not through the Attempt 1 95%-of-equity default this method implements"
        )

    # -- state ----------------------------------------------------------------------------------

    @exact
    def _begin_session(self, context: DecisionContext) -> None:
        """Advance the decision-session counters, then resolve last session's pending entry.

        RA1-5: "hwm is the running maximum of context.equity over the decision sessions of the run,
        seeded at the first decision session's equity and updated on every decision session whether
        the account is flat or not."

        RA1-4: "sessions_held counts the decision sessions on which the symbol has appeared in
        context.open_symbols, the current session included."

        RA1-3: "A pending P_ref is discarded if the symbol is absent from context.open_symbols at the
        next decision session, because the entry was not filled."

        ``context.open_symbols`` is the single authority for whether a position exists. The candidate
        never infers a fill from the fact that it emitted an order, which is why a rejected BUY
        needs no special handling here.
        """

        self._decision_index += 1
        self.decision_sessions += 1

        equity = context.equity
        if self._hwm is None or equity > self._hwm:
            self._hwm = equity
        self.ladder_sessions[self.ra1.band_of(self._drawdown(context))] += 1

        held = context.open_symbols
        if not held:
            self._pending_entry = None
            self._position_ref = None
            self._sessions_held = 0
            return

        symbol = held[0]
        if self._position_ref is not None and self._position_ref[0] == symbol:
            self._sessions_held += 1
            return
        if self._pending_entry is not None and self._pending_entry[0] == symbol:
            self._position_ref = self._pending_entry
            self.entry_fractions_filled.append(self._pending_entry[2])
            self._pending_entry = None
            self._sessions_held = 1
            return
        raise InvariantViolation(
            f"{self.variant_id}: holding {symbol} with no recorded entry reference. RA1-3 measures "
            "from the close of the decision session that scheduled the entry, so a position this "
            "candidate did not schedule cannot be loss-controlled and the run is not evaluable."
        )

    @exact
    def _drawdown(self, context: DecisionContext) -> Decimal:
        """RA1-5: "dd = (hwm - equity) / hwm at the decision close."

        ``hwm`` is never ``None`` here — :meth:`_begin_session` seeds it before any caller — and is
        never zero, because a zero high-water mark would mean a zero starting equity, which the
        sealed cost model forbids. ``ENGINE_CONTEXT`` traps the division rather than inventing an
        infinity if either ever became false.
        """

        hwm = self._hwm
        if hwm is None:
            raise InvariantViolation("RA1-5 drawdown read before the high-water mark was seeded")
        return (hwm - context.equity) / hwm

    # -- exits ----------------------------------------------------------------------------------

    def _exit_decision(
        self, view: MarketView, context: DecisionContext, symbol: str
    ) -> list[OrderRequest]:
        """Evaluate the three exit conditions in sealed precedence order and emit at most one exit.

        ``exit_precedence.rule``: "At most one exit is emitted per session because positions are
        all-or-nothing. When more than one exit condition is true on the same decision session, the
        position is closed once and the attributed reason is the highest-precedence condition."

        Testing in precedence order and returning on the first true condition yields precisely the
        highest-precedence true condition, so the short-circuit is the rule rather than an
        optimisation of it. RA1-8 forbids anything but a full exit, and :meth:`Candidate.exit_order`
        is inherited unchanged because a ``quantity`` of ``None`` already means the whole position.
        """

        if self._loss_control_triggered(view, context, symbol):
            return [self._exit(symbol, EXIT_LOSS_CONTROL)]
        if self._sessions_held >= self.ra1.max_hold:
            return [self._exit(symbol, EXIT_MAX_HOLD)]
        if self.target(view, context) != symbol:
            return [self._exit(symbol, EXIT_SIGNAL)]
        return []

    @exact
    def _loss_control_triggered(
        self, view: MarketView, context: DecisionContext, symbol: str
    ) -> bool:
        """RA1-3: "if close(symbol, t) <= P_ref * (1 - L), emit a full exit".

        ``close``, not ``adj_close``: the sealed rule writes ``close(symbol, t)`` and reserves
        ``adj_close`` for VOL20, where ``price_series_note`` states the reason it is used there.

        A symbol with no bar at ``t`` has no ``close(t)``, so the sealed predicate cannot be true and
        this returns ``False`` rather than guessing. That is not a discretionary reading of RA1-3:
        every candidate's ``signal_target_rule`` also needs a visible bar at ``t``, so the adopted
        ``insufficient_history_rule`` sends the session to cash and the position exits on the same
        session as ``EXIT_SIGNAL`` anyway. The predicate is skipped, never approximated from a stale
        price.
        """

        reference = self._position_ref
        if reference is None or reference[0] != symbol:
            raise InvariantViolation(
                f"{self.variant_id}: RA1-3 evaluated for {symbol} with no matching entry reference"
            )
        bars = self.bars_at(view, symbol, context.session, 1)
        if not bars:
            return False
        return bars[-1].close <= reference[1] * (ONE - self.ra1.loss_control)

    def _exit(self, symbol: str, reason: str) -> OrderRequest:
        """Record the attributed reason, arm the RA1-6 lockout if the exit was risk-driven.

        RA1-6: "After an exit with reason EXIT_LOSS_CONTROL or EXIT_MAX_HOLD, the candidate may not
        re-enter that same symbol for R = 5 decision sessions counted from the decision session that
        scheduled the exit. ... An exit with reason EXIT_SIGNAL creates no lockout."

        The five locked-out decision sessions are ``k+1 .. k+R`` for an exit scheduled at decision
        index ``k``, so the first permitted entry decision is ``k+R+1``. RA1-7 fixes that arithmetic
        rather than leaving it to be chosen: the exit fills at the open of ``k+1``, an entry decided
        at ``k+R+1`` fills at the open of ``k+R+2``, and the account is therefore out of the market
        for sessions ``k+1 .. k+R+1`` — six sessions at ``R = 5``, which is RA1-7's "a switch that
        follows a risk exit costs at least six sessions out of the market." Releasing at ``k+R``
        instead would yield five and contradict the seal.
        """

        self.exit_reasons[reason] += 1
        if reason in (EXIT_LOSS_CONTROL, EXIT_MAX_HOLD):
            self._lockout_release[symbol] = self._decision_index + self.ra1.reentry_delay + 1
        return self.exit_order(symbol)

    def locked_out(self, symbol: str) -> bool:
        """True while ``symbol`` is inside its RA1-6 lockout window."""

        release = self._lockout_release.get(symbol)
        return release is not None and self._decision_index < release

    # -- entries --------------------------------------------------------------------------------

    def _entry_decision(
        self, view: MarketView, context: DecisionContext
    ) -> list[OrderRequest]:
        """The signal chooses the symbol; RA1-1, RA1-2 and RA1-5 choose the size or refuse.

        Order matters and is fixed by what each rule is about. A ``target`` of ``None`` is not a
        blocked entry — the signal wanted cash — so it increments no counter. RA1-6's lockout is
        about a symbol and is tested before any sizing arithmetic is done on it. Only then does
        RA1-2 run, and each of its four refusals carries its own sealed reason.

        Every candidate's ``entry_rule`` begins "If the account is flat, no entry is pending, ...".
        Both clauses are structural rather than tested here: this method is reached only when
        ``context.open_symbols`` is empty, and :meth:`_begin_session` has already discarded any
        pending entry on a flat session because the engine resolves every scheduled order — filled or
        rejected — before the next ``decide``. The assertion states that so a future change to the
        engine's execution ordering cannot silently permit a second entry against a pending one.
        """

        if self._pending_entry is not None:
            raise InvariantViolation(
                f"{self.variant_id}: an entry in {self._pending_entry[0]} is still pending on a "
                "flat decision session. The sealed entry_rule requires that no entry be pending, "
                "and a pending order the candidate cannot see is not evaluable."
            )

        target = self.target(view, context)
        if target is None:
            return []
        if self.locked_out(target):
            self.blocked_entries[NO_ENTRY_LOCKOUT] += 1
            return []

        sized = self._entry_budget(view, context, target)
        if sized is None:
            return []
        fraction, budget = sized
        self._pending_entry = (target, self._decision_close(view, context, target), fraction)
        return [OrderRequest(symbol=target, side=BUY, budget=budget, tag=self.experiment_id)]

    @exact
    def _entry_budget(
        self, view: MarketView, context: DecisionContext, symbol: str
    ) -> tuple[Decimal, Decimal] | None:
        """RA1-2, verbatim, in order, with RA1-5 supplying ``f_cap`` and RA1-1 supplying its base.

            "sigma_target = 0.10, annualised.
             sigma = VOL20 of the symbol being entered, measured at the decision close.
             f_vol = sigma_target / sigma.
             f_cap = the RA1-5 ladder value for the decision session.
             f = min(f_cap, f_vol).
             If sigma == 0: no entry, reason NO_ENTRY_ZERO_VOLATILITY.
             If f < f_floor = 0.05: no entry that session, reason NO_ENTRY_VOLATILITY_FLOOR.
             budget = f * equity at the decision close.
             If budget < min_order_notional_usd = 1.00 from SE100-CFG-2001 sizing: no entry, reason
             NO_ENTRY_SIZE_FLOOR.
             Otherwise emit BUY with that budget."

        Two things the sealed text pins down that the code must not quietly improve on.

        ``sigma == 0`` is tested before ``f_vol`` is formed, because forming ``f_vol`` first would
        trap ``DivisionByZero`` under ``ENGINE_CONTEXT`` and turn a sealed no-entry into a failed
        run. ``f = min(f_cap, f_vol)`` is then bounded above by ``f_cap``, which is bounded above by
        RA1-1's ``f_base``; the assertion records that RA1-2 "can never raise it" as an executable
        invariant rather than a comment.

        The budget is not rounded. The global sealed arithmetic rule is "no rounding before a
        threshold comparison", and ``budget`` is compared against ``min_order_notional_usd``
        immediately below. The sealed rule also states what happens next: "The engine applies its own
        exposure cap, cash buffer, one-cent budget safety margin, and share rounding on top, and may
        reduce the executed notional further." Rounding here would pre-empt an engine step and
        Attempt 1's ``round_down_cent`` call is therefore deliberately absent.

        A VOL20 that cannot be computed is ``NO_ENTRY_INSUFFICIENT_HISTORY``: the signal wanted this
        symbol, so an entry was blocked, and ``insufficient_history_case`` plus the adopted
        ``insufficient_history_rule`` send the session to cash.

        Returns ``(f, budget)`` rather than the budget alone. ``f`` carries no rule weight — the
        engine is handed only the budget — but the sealed ``secondary_metrics`` ask for the
        "realised exposure fraction distribution", and *realised* excludes an ``f`` whose BUY the
        engine went on to reject. Returning it lets :meth:`_begin_session` record the filled subset
        at the moment ``context.open_symbols`` confirms the fill.
        """

        bars = self.bars_at(view, symbol, context.session, VOL20_BARS)
        sigma = vol20(bars) if bars else None
        if sigma is None:
            self.blocked_entries[NO_ENTRY_INSUFFICIENT_HISTORY] += 1
            return None
        if sigma == ZERO:
            self.blocked_entries[NO_ENTRY_ZERO_VOLATILITY] += 1
            return None

        f_cap = self.ra1.f_cap(self._drawdown(context))
        f_vol = self.ra1.vol_target / sigma
        fraction = min(f_cap, f_vol)
        if fraction > self.ra1.f_base:
            raise InvariantViolation(
                f"{self.variant_id}: RA1-2 produced f={fraction} above the RA1-1 ceiling "
                f"{self.ra1.f_base}; volatility targeting may only reduce exposure"
            )
        if fraction < self.ra1.vol_floor_fraction:
            self.blocked_entries[NO_ENTRY_VOLATILITY_FLOOR] += 1
            return None

        budget = fraction * context.equity
        if budget < self.costs.min_order_notional:
            self.blocked_entries[NO_ENTRY_SIZE_FLOOR] += 1
            return None

        self.entry_fractions.append(fraction)
        return fraction, budget

    def _decision_close(
        self, view: MarketView, context: DecisionContext, symbol: str
    ) -> Decimal:
        """RA1-3's ``P_ref``: "close of the DECISION session on which the entry order was scheduled".

        Reached only after :meth:`_entry_budget` has already required a visible bar at ``t`` for the
        same symbol, so the bar exists. ``why_decision_close_and_not_fill_price``: "The fill price is
        the next session's open and is not exposed to the candidate at decision time. Referencing the
        decision close keeps the rule computable from information the candidate is allowed to see,
        and structurally prevents a look-ahead read of the fill."
        """

        bars = self.bars_at(view, symbol, context.session, 1)
        if not bars:
            raise InvariantViolation(
                f"{self.variant_id}: no bar for {symbol} at {context.session.isoformat()} while "
                "recording the RA1-3 entry reference close"
            )
        return bars[-1].close

    # -- evidence -------------------------------------------------------------------------------

    def ra1_diagnostics(self) -> dict[str, Any]:
        """The RA1 half of the sealed ``secondary_metrics``, none of it gating.

        The sealed list requires the exit-reason counts, the blocked-entry counts, "realised exposure
        fraction distribution: the f actually used at each entry, so that RA1-2's effect is visible
        rather than assumed", and "number of decision sessions spent at each RA1-5 ladder rung".

        ``EXIT_SHUTDOWN`` is absent by construction and is derived from the engine's own forced fills
        by the measurement wrapper. The ladder tally is taken on every decision session, which is
        what "sessions spent at each rung" measures; RA1-5 itself is still *read* at entry only, in
        :meth:`_entry_budget`, and this tally feeds no rule.

        The exposure fractions are reported twice because the sealed word is *realised*.
        ``entry_fractions_at_order_emission`` is every ``f`` RA1-2 computed and sent to the engine;
        ``entry_fractions_realised`` is the subset whose BUY the engine actually filled, confirmed by
        the symbol appearing in ``context.open_symbols`` at the following decision session. The two
        differ exactly when the engine rejected or could not fill an entry, and the difference is
        visible rather than folded away.
        """

        return {
            "exits_by_reason": dict(self.exit_reasons),
            "blocked_entries_by_reason": dict(self.blocked_entries),
            "entry_fractions_at_order_emission": [f"{value:f}" for value in self.entry_fractions],
            "entry_fractions_realised": [f"{value:f}" for value in self.entry_fractions_filled],
            "entries_emitted": len(self.entry_fractions),
            "entries_filled": len(self.entry_fractions_filled),
            "ladder_sessions": dict(self.ladder_sessions),
            "decision_sessions": self.decision_sessions,
            "decision_sessions_shutdown_active": self.decision_sessions_shutdown_active,
        }

    def ra1_to_json(self) -> dict[str, Any]:
        """The RA1 constants actually in force for this variant, for the traceability evidence."""

        return {
            "f_base": f"{self.ra1.f_base:f}",
            "vol_target": f"{self.ra1.vol_target:f}",
            "vol_floor_fraction": f"{self.ra1.vol_floor_fraction:f}",
            "loss_control": f"{self.ra1.loss_control:f}",
            "max_hold": self.ra1.max_hold,
            "reentry_delay": self.ra1.reentry_delay,
            "ladder_rungs": [
                [f"{threshold:f}", f"{capped:f}"] for threshold, capped in self.ra1.ladder_rungs
            ],
            "ladder_bands": list(self.ra1.ladder_bands),
        }


def sealed_reason_codes(protocol_text: str, codes: Sequence[str]) -> list[str]:
    """The codes in ``codes`` that do not appear in ``protocol_text``.

    Used by the test that asserts every reason code this module defines is one the sealed protocol
    names, so a typo cannot introduce a reason the seal does not recognise.
    """

    return [code for code in codes if code not in protocol_text]
