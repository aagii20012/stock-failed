"""Cash, positions, and the invariants that make them trustworthy.

The portfolio keeps a **ledger**: every cash movement is appended with its reason, and the running
balance is reconciled against the sum of the ledger after every single event. That is more machinery
than a running float needs, and it is the point — a backtest that loses a cent somewhere usually
loses it in a way that flatters the result, and a balance that is only ever incremented has no way
to notice.

Cash is always a whole number of cents. Marks are never rounded, because a mark is not a cash
movement; rounding it would be inventing precision loss that never happened.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from stockedge100.backtest.costs import CENT, ZERO, Fill, exact
from stockedge100.backtest.errors import InvariantViolation

BUY = "BUY"
SELL = "SELL"


@dataclass(frozen=True)
class LedgerEntry:
    session: dt.date
    reason: str
    amount: Decimal
    symbol: str = ""

    def to_json(self) -> dict[str, str]:
        return {
            "session": self.session.isoformat(),
            "reason": self.reason,
            "amount": f"{self.amount:f}",
            "symbol": self.symbol,
        }


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: Decimal
    cost_basis: Decimal          # total cash paid to acquire the current quantity
    opened_session: dt.date

    def to_json(self) -> dict[str, str]:
        return {
            "symbol": self.symbol,
            "quantity": f"{self.quantity:f}",
            "cost_basis": f"{self.cost_basis:f}",
            "opened_session": self.opened_session.isoformat(),
        }


@dataclass
class Trade:
    """A closed round trip. Costs on both legs are attributed to it, per the sealed definition."""

    symbol: str
    entry_session: dt.date
    exit_session: dt.date
    quantity: Decimal
    entry_cash: Decimal          # cash paid on entry, positive
    exit_cash: Decimal           # cash received on exit, positive
    dividends: Decimal
    entry_costs: Decimal
    exit_costs: Decimal

    @property
    def pnl(self) -> Decimal:
        return self.exit_cash + self.dividends - self.entry_cash

    def to_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "entry_session": self.entry_session.isoformat(),
            "exit_session": self.exit_session.isoformat(),
            "quantity": f"{self.quantity:f}",
            "entry_cash": f"{self.entry_cash:f}",
            "exit_cash": f"{self.exit_cash:f}",
            "dividends": f"{self.dividends:f}",
            "entry_costs": f"{self.entry_costs:f}",
            "exit_costs": f"{self.exit_costs:f}",
            "pnl": f"{self.pnl:f}",
        }


class Portfolio:
    """A long-only cash account with a reconciled ledger."""

    def __init__(self, starting_cash: Decimal, *, max_positions: int = 1) -> None:
        if starting_cash <= ZERO:
            raise InvariantViolation(f"starting cash must be positive, got {starting_cash}")
        self._require_cents(starting_cash, "starting cash")
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.max_positions = max_positions
        self.positions: dict[str, Position] = {}
        self.ledger: list[LedgerEntry] = []
        self.trades: list[Trade] = []
        self._dividends_by_symbol: dict[str, Decimal] = {}

    # -- invariants ------------------------------------------------------------------------------

    @staticmethod
    def _require_cents(amount: Decimal, what: str) -> None:
        if amount != amount.quantize(CENT):
            raise InvariantViolation(
                f"CASH_IS_WHOLE_CENTS: {what} is {amount}, which is not a whole number of cents"
            )

    def check_invariants(self, where: str) -> None:
        if self.cash < ZERO:
            raise InvariantViolation(
                f"CASH_NON_NEGATIVE violated at {where}: cash is {self.cash}. A cash account cannot "
                "go negative; this is leverage arriving by accident."
            )
        self._require_cents(self.cash, f"cash at {where}")

        reconciled = self.starting_cash + sum((e.amount for e in self.ledger), ZERO)
        if reconciled != self.cash:
            raise InvariantViolation(
                f"CASH_CONSERVATION violated at {where}: balance is {self.cash} but the ledger sums "
                f"to {reconciled}. A cash movement happened without being recorded."
            )
        for symbol, position in self.positions.items():
            if position.quantity <= ZERO:
                raise InvariantViolation(
                    f"LONG_ONLY violated at {where}: {symbol} holds {position.quantity}"
                )
        if len(self.positions) > self.max_positions:
            raise InvariantViolation(
                f"MAX_POSITIONS violated at {where}: {len(self.positions)} open positions exceeds "
                f"the sealed limit of {self.max_positions}"
            )

    # -- cash ------------------------------------------------------------------------------------

    def _move(self, session: dt.date, reason: str, amount: Decimal, symbol: str = "") -> None:
        self._require_cents(amount, f"{reason} amount")
        self.cash = self.cash + amount
        self.ledger.append(LedgerEntry(session=session, reason=reason, amount=amount, symbol=symbol))
        self.check_invariants(f"{session.isoformat()} {reason}")

    def credit(self, session: dt.date, reason: str, amount: Decimal, symbol: str = "") -> None:
        if amount < ZERO:
            raise InvariantViolation(f"credit must be non-negative, got {amount}")
        self._move(session, reason, amount, symbol)

    def debit(self, session: dt.date, reason: str, amount: Decimal, symbol: str = "") -> None:
        if amount < ZERO:
            raise InvariantViolation(f"debit must be non-negative, got {amount}")
        self._move(session, reason, -amount, symbol)

    # -- positions -------------------------------------------------------------------------------

    def quantity_of(self, symbol: str) -> Decimal:
        position = self.positions.get(symbol)
        return ZERO if position is None else position.quantity

    def open_symbols(self) -> tuple[str, ...]:
        return tuple(sorted(self.positions))

    @exact
    def apply_fill(self, session: dt.date, fill: Fill) -> None:
        """Settle a fill: move the cash, move the shares, and reconcile.

        Cash moves *before* the position changes so that a fill which would overdraw the account
        raises on the cash invariant rather than leaving a phantom position behind.
        """
        if fill.side == BUY:
            debit = -fill.cash_delta
            if debit > self.cash:
                raise InvariantViolation(
                    f"CASH_NON_NEGATIVE: buying {fill.symbol} needs {debit} but only {self.cash} is "
                    "available. Sizing should have prevented this order from being admitted."
                )
            self.debit(session, "BUY", debit, fill.symbol)
            existing = self.positions.get(fill.symbol)
            if existing is None:
                if len(self.positions) >= self.max_positions:
                    raise InvariantViolation(
                        f"MAX_POSITIONS: opening {fill.symbol} would exceed the sealed limit"
                    )
                self.positions[fill.symbol] = Position(
                    symbol=fill.symbol,
                    quantity=fill.quantity,
                    cost_basis=debit,
                    opened_session=session,
                )
            else:
                self.positions[fill.symbol] = Position(
                    symbol=fill.symbol,
                    quantity=existing.quantity + fill.quantity,
                    cost_basis=existing.cost_basis + debit,
                    opened_session=existing.opened_session,
                )
        else:
            existing = self.positions.get(fill.symbol)
            held = ZERO if existing is None else existing.quantity
            if fill.quantity > held:
                raise InvariantViolation(
                    f"INSUFFICIENT_POSITION: selling {fill.quantity} of {fill.symbol} while holding "
                    f"{held}. Long-only means a sale cannot exceed the position."
                )
            self.credit(session, "SELL", fill.cash_delta, fill.symbol)
            remaining = held - fill.quantity
            assert existing is not None  # guarded by the quantity check above
            if remaining == ZERO:
                entry_cash = existing.cost_basis
                self.trades.append(
                    Trade(
                        symbol=fill.symbol,
                        entry_session=existing.opened_session,
                        exit_session=session,
                        quantity=fill.quantity,
                        entry_cash=entry_cash,
                        exit_cash=fill.cash_delta,
                        dividends=self._dividends_by_symbol.pop(fill.symbol, ZERO),
                        entry_costs=ZERO,
                        exit_costs=fill.commission + fill.sec_fee + fill.taf_fee,
                    )
                )
                del self.positions[fill.symbol]
            else:
                share = existing.cost_basis * (remaining / held)
                self.positions[fill.symbol] = Position(
                    symbol=fill.symbol,
                    quantity=remaining,
                    cost_basis=share,
                    opened_session=existing.opened_session,
                )
        self.check_invariants(f"{session.isoformat()} {fill.side} {fill.symbol}")

    def record_dividend(self, session: dt.date, symbol: str, amount: Decimal) -> None:
        self.credit(session, "DIVIDEND", amount, symbol)
        self._dividends_by_symbol[symbol] = self._dividends_by_symbol.get(symbol, ZERO) + amount

    # -- valuation -------------------------------------------------------------------------------

    @exact
    def equity(self, marks: dict[str, Decimal]) -> Decimal:
        """Cash plus marked positions, at full precision and never rounded."""
        total = self.cash
        for symbol in sorted(self.positions):
            mark = marks.get(symbol)
            if mark is None:
                raise InvariantViolation(
                    f"no mark supplied for open position {symbol}; equity cannot be computed by "
                    "leaving a holding out of the sum"
                )
            total += self.positions[symbol].quantity * mark
        return total

    def snapshot(self) -> dict[str, Any]:
        return {
            "cash": f"{self.cash:f}",
            "positions": [self.positions[s].to_json() for s in sorted(self.positions)],
        }
