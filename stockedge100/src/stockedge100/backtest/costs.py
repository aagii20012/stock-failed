"""The sealed cost constitution, implemented.

Constitution §7 lists what a backtest must charge. This module is the only place any of it is
computed, so there is exactly one answer to "what did this fill cost" and it can be read off in one
screen.

Two properties are load-bearing and are asserted rather than assumed:

* **Every price friction is adverse.** A buy fills above its reference, a sell below it. Never the
  reverse, in any scenario, at any multiplier.
* **Every rounding step is adverse.** Quantity rounds down; a buy's notional and every regulatory
  fee round up; sale proceeds and dividend credits round down. Rounding in a backtest is either a
  small cost or a small free lunch, and which one it is depends entirely on the direction chosen.

All arithmetic runs in :data:`ENGINE_CONTEXT`, a fixed 34-digit decimal context. Pinning it means a
value computed inside :meth:`Engine.run` and the same value computed by a test are produced under
identical rules, which is what makes the sealed hand-calculated fixtures checkable at all.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from decimal import (
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    localcontext,
)
from typing import Any, Callable, TypeVar

from stockedge100.backtest.config import dec
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation

ENGINE_CONTEXT = Context(
    prec=34,
    rounding=ROUND_HALF_EVEN,
    traps=[InvalidOperation, DivisionByZero, Overflow],
)

CENT = Decimal("0.01")
ZERO = Decimal("0")
BPS = Decimal("10000")

BASE = "BASE"
STRESSED = "STRESSED"
SCENARIOS = (BASE, STRESSED)

F = TypeVar("F", bound=Callable[..., Any])


def exact(fn: F) -> F:
    """Run ``fn`` under :data:`ENGINE_CONTEXT` regardless of the caller's decimal context.

    Without this, a caller that had adjusted the global context could change a fill price without
    touching a line of engine code.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with localcontext(ENGINE_CONTEXT):
            return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def _non_negative(value: Decimal, what: str) -> Decimal:
    if value < ZERO:
        raise InvariantViolation(f"{what} must be non-negative, got {value}")
    return value


def round_up_cent(value: Decimal) -> Decimal:
    """Round a non-negative money amount up to the whole cent."""
    return _non_negative(value, "amount").quantize(CENT, rounding=ROUND_CEILING)


def round_down_cent(value: Decimal) -> Decimal:
    """Round a non-negative money amount down to the whole cent."""
    return _non_negative(value, "amount").quantize(CENT, rounding=ROUND_FLOOR)


def assert_adverse_price(side: str, reference: Decimal, effective: Decimal, friction_bps: Decimal) -> None:
    """The adverse-price invariant, checked on the *result* rather than inside the arithmetic.

    :meth:`CostModel.effective_buy_price` already refuses to return a favourable price, but that
    check lives in the same expression as the price it guards: replace the method and the guard
    leaves with it. This one is called again by every fill, from a different function, on a value it
    did not compute — so a mutated price function is still caught before it can move any cash.

    Equality is permitted only when the friction assumption is genuinely zero.
    """
    if side == "BUY":
        ok = effective > reference if friction_bps > ZERO else effective == reference
    else:
        ok = effective < reference if friction_bps > ZERO else effective == reference
    if not ok:
        raise InvariantViolation(
            f"ADVERSE_PRICE: a {side} fill at reference {reference} priced at {effective} under a "
            f"friction of {friction_bps} bps per side, which is not adverse to the account"
        )


@dataclass(frozen=True)
class Fill:
    """One executed order leg, with every cost component kept separate.

    The components are not collapsed into a single number because a test that can only see the
    total cannot tell a missing regulatory fee from a mis-signed slippage charge.
    """

    symbol: str
    side: str                    # "BUY" or "SELL"
    quantity: Decimal
    reference_price: Decimal
    effective_price: Decimal
    gross_notional: Decimal      # rounded, adverse direction
    commission: Decimal
    sec_fee: Decimal
    taf_fee: Decimal
    cash_delta: Decimal          # negative for a buy, positive for a sell

    @property
    def total_cost(self) -> Decimal:
        """Everything the account paid beyond the reference-price value of the shares."""
        friction = (self.effective_price - self.reference_price) * self.quantity
        if self.side == "SELL":
            friction = -friction
        rounding = self.gross_notional - self.effective_price * self.quantity
        if self.side == "SELL":
            rounding = -rounding
        return friction + rounding + self.commission + self.sec_fee + self.taf_fee

    def to_json(self) -> dict[str, str]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": f"{self.quantity:f}",
            "reference_price": f"{self.reference_price:f}",
            "effective_price": f"{self.effective_price:f}",
            "gross_notional": f"{self.gross_notional:f}",
            "commission": f"{self.commission:f}",
            "sec_fee": f"{self.sec_fee:f}",
            "taf_fee": f"{self.taf_fee:f}",
            "cash_delta": f"{self.cash_delta:f}",
        }


class CostModel:
    """The sealed frictions, at one of the two declared scenarios.

    ``STRESSED`` multiplies the **complete** friction assumption by the sealed multiplier, including
    the TAF cap. Doubling a per-share rate while leaving its cap alone would quietly make the
    stressed run cheaper than 2× for large orders, which is the opposite of a stress test.
    """

    def __init__(self, cost_model: dict[str, Any], scenario: str = BASE) -> None:
        if scenario not in SCENARIOS:
            raise ConfigViolation(f"unknown cost scenario {scenario!r}; declared: {SCENARIOS}")
        self.scenario = scenario
        self.raw = cost_model

        frictions = cost_model["frictions"]
        regulatory = frictions["regulatory"]
        sizing = cost_model["sizing"]
        account = cost_model["account"]

        mult = dec(frictions["stress_multiplier"]) if scenario == STRESSED else Decimal("1")
        self.stress_multiplier = mult

        stressed = set(frictions["stress_applies_to"])
        for name in (
            "commission_per_order_usd", "half_spread_bps", "slippage_bps",
            "sec_section_31_fee_rate", "finra_taf_per_share_usd", "finra_taf_cap_usd",
        ):
            if name not in stressed:
                raise ConfigViolation(
                    f"the sealed stress_applies_to list omits {name!r}; a stressed run that leaves "
                    "a friction component unscaled is not a 2x stress of the complete assumption"
                )

        # Money-valued parameters are quantized to the cent after stressing; rate-valued ones are
        # not. A broker cannot charge a fraction of a cent, and leaving a stressed commission at
        # 0.000 would carry that exponent into every cash balance it touched, so the ledger would
        # print 119.220 for a figure that is a whole number of cents. Both quantizations round *up*,
        # the adverse direction, in the case where the multiplier does create a fraction.
        self.commission = round_up_cent(dec(frictions["commission_per_order_usd"]) * mult)
        self.half_spread_bps = dec(frictions["half_spread_bps"]) * mult
        self.slippage_bps = dec(frictions["slippage_bps"]) * mult
        self.sec_rate = dec(regulatory["sec_section_31_fee_rate"]) * mult
        self.taf_per_share = dec(regulatory["finra_taf_per_share_usd"]) * mult
        self.taf_cap = round_up_cent(dec(regulatory["finra_taf_cap_usd"]) * mult)

        self.share_decimals = int(sizing["share_decimals"])
        self.share_quantum = Decimal(1).scaleb(-self.share_decimals)
        self.min_order_notional = dec(sizing["min_order_notional_usd"])
        self.min_order_shares = dec(sizing["min_order_shares"])
        self.budget_safety_margin = dec(sizing["budget_safety_margin_usd"])

        self.starting_equity = dec(account["starting_equity_usd"])
        self.max_gross_exposure_fraction = dec(account["max_gross_exposure_fraction"])
        self.min_cash_buffer_fraction = dec(account["min_cash_buffer_fraction"])
        self.max_open_risky_positions = int(account["max_open_risky_positions"])

        self.research_shutdown_drawdown = dec(cost_model["risk"]["research_shutdown_drawdown_fraction"])
        self.max_consecutive_stale = int(cost_model["data_integrity"]["max_consecutive_stale_sessions"])
        self.max_stale_sessions_for_fill = int(cost_model["data_integrity"]["max_stale_sessions_for_fill"])

    # -- prices ----------------------------------------------------------------------------------

    @property
    def price_friction_bps(self) -> Decimal:
        return self.half_spread_bps + self.slippage_bps

    @exact
    def effective_buy_price(self, reference: Decimal) -> Decimal:
        """The reference price marked up by the half spread plus slippage. Always higher."""
        price = reference * (Decimal(1) + self.price_friction_bps / BPS)
        assert_adverse_price("BUY", reference, price, self.price_friction_bps)
        return price

    @exact
    def effective_sell_price(self, reference: Decimal) -> Decimal:
        """The reference price marked down by the half spread plus slippage. Always lower."""
        price = reference * (Decimal(1) - self.price_friction_bps / BPS)
        assert_adverse_price("SELL", reference, price, self.price_friction_bps)
        if price <= ZERO:
            raise InvariantViolation(f"a sell at reference {reference} produced a non-positive price")
        return price

    # -- sizing ----------------------------------------------------------------------------------

    @exact
    def round_quantity(self, quantity: Decimal) -> Decimal:
        """Round a share quantity **down** to the sealed precision."""
        return _non_negative(quantity, "quantity").quantize(self.share_quantum, rounding=ROUND_FLOOR)

    @exact
    def solve_buy_quantity(self, budget: Decimal, effective_price: Decimal) -> Decimal:
        """The largest quantity whose charged notional still fits inside ``budget``.

        The sealed safety margin is withheld *before* the division, so that rounding the resulting
        notional up to the cent afterwards can never push the charge back over the budget — and
        therefore can never breach the exposure cap or the cash buffer by a cent.
        """
        if effective_price <= ZERO:
            raise InvariantViolation(f"cannot size an order at a non-positive price {effective_price}")
        usable = budget - self.commission - self.budget_safety_margin
        if usable <= ZERO:
            return ZERO
        return self.round_quantity(usable / effective_price)

    # -- charges ---------------------------------------------------------------------------------

    @exact
    def buy_fill(self, symbol: str, quantity: Decimal, reference: Decimal) -> Fill:
        """Cost a purchase. The notional rounds **up**: the account pays the extra fraction of a cent."""
        effective = self.effective_buy_price(reference)
        assert_adverse_price("BUY", reference, effective, self.price_friction_bps)
        gross = round_up_cent(quantity * effective)
        cash_delta = -(gross + self.commission)
        return Fill(
            symbol=symbol, side="BUY", quantity=quantity,
            reference_price=reference, effective_price=effective,
            gross_notional=gross, commission=self.commission,
            sec_fee=ZERO, taf_fee=ZERO, cash_delta=cash_delta,
        )

    @exact
    def sell_fill(self, symbol: str, quantity: Decimal, reference: Decimal) -> Fill:
        """Cost a sale, including the two sell-side regulatory fees.

        Both fees are charged on the **rounded** gross notional and both round up to the cent, per
        the sealed model. On a USD 100 account they round to a cent from a fraction of one, which
        over-charges — the conservative direction, and recorded as a limitation rather than tuned
        away.
        """
        effective = self.effective_sell_price(reference)
        assert_adverse_price("SELL", reference, effective, self.price_friction_bps)
        gross = round_down_cent(quantity * effective)
        sec = round_up_cent(gross * self.sec_rate) if self.sec_rate > ZERO else ZERO
        taf_raw = min(quantity * self.taf_per_share, self.taf_cap)
        taf = round_up_cent(taf_raw) if self.taf_per_share > ZERO else ZERO
        net = gross - self.commission - sec - taf
        return Fill(
            symbol=symbol, side="SELL", quantity=quantity,
            reference_price=reference, effective_price=effective,
            gross_notional=gross, commission=self.commission,
            sec_fee=sec, taf_fee=taf, cash_delta=net,
        )

    @exact
    def dividend_cash(self, quantity: Decimal, amount_per_share: Decimal) -> Decimal:
        """Cash credited for a dividend, rounded **down** to the cent like every other credit."""
        return round_down_cent(quantity * amount_per_share)

    # -- reporting -------------------------------------------------------------------------------

    def to_json(self) -> dict[str, str]:
        return {
            "scenario": self.scenario,
            "stress_multiplier": f"{self.stress_multiplier:f}",
            "commission_per_order_usd": f"{self.commission:f}",
            "half_spread_bps": f"{self.half_spread_bps:f}",
            "slippage_bps": f"{self.slippage_bps:f}",
            "price_friction_bps_per_side": f"{self.price_friction_bps:f}",
            "sec_section_31_fee_rate": f"{self.sec_rate:f}",
            "finra_taf_per_share_usd": f"{self.taf_per_share:f}",
            "finra_taf_cap_usd": f"{self.taf_cap:f}",
        }
