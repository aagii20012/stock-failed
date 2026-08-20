"""Record two conventions the LEAN cross-check earned, missing from the rules file.

1. The 10bps-per-unit-turnover cost default is ~6.7x too harsh for these
   instruments. Measured, not guessed: LEAN's InteractiveBrokersFeeModel charged
   $4,248 on $28,304,842 of traded notional over 19.6 years = 1.50 bps.

2. The bracket technique. Running the harness at 0bps AND 10bps turns the cost
   model into an interval rather than a point, and the question "does the other
   implementation land inside it?" is answerable at a glance. Its real value is
   the contrapositive: a metric OUTSIDE the bracket cannot be a cost artifact,
   which is what pointed max drawdown at fill timing instead.

Inserted before the "Never report a single-config backtest" bullet, which is the
other convention about not trusting one number.
"""

import io
import os

RULES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                     ".claude", "rules", "faber-lean.md"))

ANCHOR = "- **Never report a single-config backtest.**"

NEW = """- **Do not charge 10 bps per unit of turnover.** That was a placeholder and it is
  ~6.7x too harsh for nine large SPDR ETFs traded monthly. LEAN's IB fee model charged
  $4,248 on $28,304,842 of traded notional over 19.6 years -- **1.50 bps of notional** --
  against $73,306 of terminal wealth removed by the 10 bps model. Quote ~2 bps as the
  realistic figure and say "conservative floor" out loud if quoting 10 bps. Note LEAN
  runs *no* slippage model, so it is the optimistic bound, not the truth.
- **Bracket a comparison instead of point-matching it.** Run the harness at 0 bps and at
  the cost assumption, and ask whether the other implementation's metric lands inside the
  interval. CAGR 9.32% between 9.64% and 8.91% is instantly interpretable where "off by
  0.37 pp" is not. The contrapositive is what earns its place: a metric landing *outside*
  the bracket cannot be a cost-model artifact, so it points at a different mechanism --
  that is how max drawdown was traced to fill timing rather than fees.
"""


def main():
    with io.open(RULES, encoding="utf-8") as fh:
        body = fh.read()
    if "1.50 bps of notional" in body:
        print("  already recorded")
        return
    n = body.count(ANCHOR)
    if n != 1:
        raise SystemExit("anchor matched %d times, expected 1" % n)
    with io.open(RULES, "w", encoding="utf-8", newline="") as fh:
        fh.write(body.replace(ANCHOR, NEW + ANCHOR))
    print("  patched (%d -> %d chars)" % (len(body), len(body) + len(NEW)))


if __name__ == "__main__":
    print("=== recording cost calibration + bracket technique ===")
    main()
