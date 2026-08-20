"""Replay the tagged decision log through faber_signal.decide().

``rebalance_log.csv`` is the per-month decision record produced by the verified
baseline (tag ``baseline-v1-faber-verified``): 236 rebalances whose picks and
skips LEAN reproduced exactly. This test asserts the live signal module makes
the same call on every one of them.

Needs ``faber-lean/prices.csv``, which is gitignored (derived vendor data), so
it is skipped in CI and must be run locally:

    cd faber-lean/paper && python -m pytest test_signal_parity.py -q
    cd faber-lean/paper && python test_signal_parity.py      # same, with a report

Regenerate the inputs with ``python local_backtest.py`` from ``faber-lean/``.
"""

from __future__ import annotations

import ast
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faber_signal import DEFENSIVE, SECTORS, TOP_N, decide  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PRICES = os.path.join(HERE, os.pardir, "prices.csv")
LOG = os.path.join(HERE, os.pardir, "rebalance_log.csv")

MISSING = not (os.path.exists(PRICES) and os.path.exists(LOG))
SKIP_REASON = (
    "needs faber-lean/prices.csv + rebalance_log.csv (gitignored/derived); "
    "run `python local_backtest.py` in faber-lean/ first"
)


def load_fixtures():
    prices = pd.read_csv(PRICES, index_col=0, parse_dates=True)
    log = pd.read_csv(LOG)
    log["ranked"] = log["ranked"].apply(ast.literal_eval)
    log["skipped"] = log["skipped"].apply(ast.literal_eval)
    return prices, log


def replay(prices: pd.DataFrame, log: pd.DataFrame):
    """Yield (row, decision, asof) for every logged rebalance."""
    periods = prices.index.to_period("M")
    for row in log.itertuples():
        hold = pd.Period(row.hold_month, freq="M")
        # The rebalance runs on the first trading day of the hold month, which
        # is when LEAN's month_start rule fires.
        days = prices.index[periods == hold]
        if len(days) == 0:
            continue
        asof = days[0]
        yield row, decide(prices.loc[prices.index <= asof], asof), asof


@pytest.mark.skipif(MISSING, reason=SKIP_REASON)
def test_picks_and_skips_match_tagged_log():
    prices, log = load_fixtures()
    replayed = 0
    for row, d, asof in replay(prices, log):
        replayed += 1
        assert d.signal_month == row.signal_month, f"{asof.date()}: signal month"
        assert d.ranked == list(row.ranked), (
            f"{asof.date()}: ranked {d.ranked} != logged {list(row.ranked)}"
        )
        assert sorted(d.skipped) == sorted(row.skipped), (
            f"{asof.date()}: skipped {d.skipped} != logged {list(row.skipped)}"
        )
    assert replayed >= 236, f"only replayed {replayed} rebalances, expected 236+"


@pytest.mark.skipif(MISSING, reason=SKIP_REASON)
def test_weights_are_wellformed():
    prices, log = load_fixtures()
    for row, d, asof in replay(prices, log):
        assert abs(sum(d.weights.values()) - 1.0) < 1e-9, f"{asof.date()}: weights"
        assert all(w > 0 for w in d.weights.values())
        assert set(d.weights) <= set(SECTORS + [DEFENSIVE])
        # Every slot lands somewhere: a held sector or the defensive bucket.
        held = [s for s in d.ranked if s not in d.skipped]
        assert len(held) + len(d.skipped) == TOP_N
        for s in held:
            assert d.weights[s] >= 1.0 / TOP_N - 1e-9
        if d.skipped:
            expected = len(d.skipped) / TOP_N
            assert abs(d.weights[DEFENSIVE] - expected) < 1e-9


def test_insufficient_history_is_a_no_trade():
    """Short history must produce an empty decision, never a partial one."""
    idx = pd.date_range("2025-01-01", periods=120, freq="B")
    short = pd.DataFrame(
        {t: range(1, len(idx) + 1) for t in SECTORS + [DEFENSIVE]}, index=idx
    ).astype(float)
    d = decide(short, idx[-1])
    assert d.weights == {}
    assert "completed monthly closes" in d.reason


def test_trend_filter_routes_every_slot_to_defensive():
    """A universe in freefall must go 100% defensive, not partially invested."""
    idx = pd.date_range("2023-01-02", periods=700, freq="B")
    falling = pd.Series(range(len(idx), 0, -1), index=idx).astype(float)
    flat = pd.Series(100.0, index=idx)
    df = pd.DataFrame({t: falling for t in SECTORS})
    df[DEFENSIVE] = flat
    d = decide(df, idx[-1])
    assert d.skipped == d.ranked
    assert d.fully_defensive
    assert d.weights == {DEFENSIVE: 1.0}


if __name__ == "__main__":
    if MISSING:
        sys.exit("SKIP: " + SKIP_REASON)
    prices, log = load_fixtures()
    rows = list(replay(prices, log))
    bad = [
        (str(r.hold_month), d.ranked, list(r.ranked), d.skipped, list(r.skipped))
        for r, d, _ in rows
        if d.ranked != list(r.ranked) or sorted(d.skipped) != sorted(r.skipped)
    ]
    slots = len(rows) * TOP_N
    skips = sum(len(d.skipped) for _, d, _ in rows)
    print(f"replayed         : {len(rows)} rebalances")
    print(f"slots            : {slots}")
    print(f"skips            : {skips} ({100.0 * skips / slots:.1f}%)")
    print(f"fully defensive  : {sum(1 for _, d, _ in rows if d.fully_defensive)}")
    print(f"mismatches       : {len(bad)}")
    for b in bad[:10]:
        print("  ", b)
    sys.exit(1 if bad else 0)
