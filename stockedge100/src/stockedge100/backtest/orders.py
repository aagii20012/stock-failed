"""Orders, the order book, and the reasons an order does not become a fill.

Two rules live here and nowhere else.

**A fill is never on the decision session.** An order decided at the close of session *t* fills at
the open of the next exchange session. The order book computes that session itself from the
independent XNYS calendar and refuses any other, so "fill at the same close" is not a bug that can be
introduced by a careless caller — it is a rejected construction.

**A rejection is an event, not an absence.** Every order that does not fill is recorded with a reason
code and asserted to have changed nothing. An order that quietly disappears is indistinguishable, in
the equity curve, from one that was never generated, and those are very different facts.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from stockedge100.data.calendar import sessions_between
from stockedge100.backtest.errors import DuplicateOrderError, FillTimingError

BUY = "BUY"
SELL = "SELL"
SIDES = (BUY, SELL)

# Every reason an order can fail to become a fill. Closed set: the engine may not invent one at
# runtime, because a reason nobody declared is a reason nobody tested.
REASONS = (
    "MIN_NOTIONAL",
    "INSUFFICIENT_CASH",
    "INSUFFICIENT_POSITION",
    "DUPLICATE_ORDER",
    "STALE_PRICE",
    "MAX_POSITIONS",
    "RESEARCH_SHUTDOWN",
    "NO_ELIGIBLE_SESSION",
    "ZERO_QUANTITY",
    "DELISTED",
)


@dataclass(frozen=True)
class Order:
    """One intent, decided at the close of ``decision_session``.

    A buy carries a cash ``budget`` rather than a share count: at USD 100 with fractional shares, the
    quantity is a consequence of the budget and the price, and letting a caller name both would let
    it name a quantity the budget cannot pay for.
    """

    order_id: str
    symbol: str
    side: str
    decision_session: dt.date
    fill_session: dt.date
    budget: Decimal | None = None       # BUY only
    quantity: Decimal | None = None     # SELL only; None means "the whole position"
    tag: str = ""

    def __post_init__(self) -> None:
        if self.side not in SIDES:
            raise ValueError(f"unknown side {self.side!r}")
        if self.fill_session <= self.decision_session:
            raise FillTimingError(
                f"{self.order_id}: fill session {self.fill_session.isoformat()} is not strictly "
                f"after decision session {self.decision_session.isoformat()}. An order decided at a "
                "close cannot execute at that same close."
            )
        if self.side == BUY and self.budget is None:
            raise ValueError(f"{self.order_id}: a buy needs a budget")
        if self.side == SELL and self.budget is not None:
            raise ValueError(f"{self.order_id}: a sell does not take a budget")

    def to_json(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "decision_session": self.decision_session.isoformat(),
            "fill_session": self.fill_session.isoformat(),
            "budget": None if self.budget is None else f"{self.budget:f}",
            "quantity": None if self.quantity is None else f"{self.quantity:f}",
            "tag": self.tag,
        }


@dataclass(frozen=True)
class Rejection:
    order: Order
    reason: str
    detail: str = ""

    def to_json(self) -> dict[str, Any]:
        return {"order": self.order.to_json(), "reason": self.reason, "detail": self.detail}


def next_session_after(session: dt.date, *, lookahead_days: int = 30) -> dt.date | None:
    """The next XNYS session strictly after ``session``.

    Uses the independent exchange calendar, not the provider's data. Asking the price file "what is
    the next row" would make a missing bar look like a holiday, and a missing bar is exactly the
    stale-price condition the engine must refuse to fill on.
    """
    horizon = session + dt.timedelta(days=lookahead_days)
    for day in sessions_between(session + dt.timedelta(days=1), horizon):
        return day
    return None


@dataclass
class OrderBook:
    """Orders admitted for one decision session.

    A fresh book per session is what makes the duplicate check meaningful: within a session, an
    order id may appear once and a symbol may have one live order, full stop.
    """

    decision_session: dt.date
    orders: list[Order] = field(default_factory=list)
    _ids: set[str] = field(default_factory=set, repr=False)
    _symbols: set[str] = field(default_factory=set, repr=False)

    def submit(self, order: Order) -> Order:
        if order.decision_session != self.decision_session:
            raise FillTimingError(
                f"{order.order_id}: decided on {order.decision_session.isoformat()} but submitted to "
                f"the book for {self.decision_session.isoformat()}"
            )
        if order.order_id in self._ids:
            raise DuplicateOrderError(
                f"order id {order.order_id!r} was already admitted for "
                f"{self.decision_session.isoformat()}"
            )
        if order.symbol in self._symbols:
            raise DuplicateOrderError(
                f"{order.symbol} already has a live order on {self.decision_session.isoformat()}; "
                "two orders in one symbol on one session is a duplicate, whatever the sides are"
            )
        self._ids.add(order.order_id)
        self._symbols.add(order.symbol)
        self.orders.append(order)
        return order

    def scheduled(self) -> list[Order]:
        """Admitted orders in a deterministic order: symbol, then side, then id."""
        return sorted(self.orders, key=lambda o: (o.symbol, o.side, o.order_id))

    def __len__(self) -> int:
        return len(self.orders)


def make_order_id(decision_session: dt.date, symbol: str, side: str, tag: str = "") -> str:
    """A deterministic id built only from the order's own facts.

    No counter, no timestamp, no object address — so two runs of the same probe produce the same ids,
    and a genuinely duplicated order produces a genuinely duplicated id rather than a fresh one that
    slips past the check.
    """
    suffix = f"-{tag}" if tag else ""
    return f"{decision_session.isoformat()}-{symbol}-{side}{suffix}"
