"""Smoke the RA2 engine module before anything imports it for real.

The module lives in src/, which is a repo_state_id pattern, so a defect found after the decision
package is built cannot be repaired without invalidating the digest that package recorded. Every
piece of arithmetic that does not need a price series is exercised here first, against the sealed
protocol as it actually sits on disk.

Three things this proves that reading the file cannot:
  - load_risk_architecture() parses the seal and every structural predicate passes against it;
  - the validators are not vacuous -- each one is shown to reject a perturbed architecture;
  - the ladder, lockout and volatility arithmetic reproduce the sealed tables by hand.
"""
from __future__ import annotations

import json
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.errors import ConfigViolation, InvariantViolation  # noqa: E402
import stockedge100.backtest.g2_engine_ra1 as E  # noqa: E402

FAILED = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global FAILED
    if not ok:
        FAILED += 1
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", label, ("  <- " + detail) if detail else ""))


def rejects(label: str, mutate) -> None:
    """The validator must refuse a perturbed protocol. A validator that accepts everything is not one."""
    protocol = json.loads(E.PROTOCOL_PATH.read_text(encoding="utf-8"))
    mutate(protocol)
    try:
        E.load_risk_architecture(protocol)
    except (ConfigViolation, InvariantViolation, KeyError) as exc:
        check("rejects: %s" % label, True, type(exc).__name__)
        return
    check("rejects: %s" % label, False, "accepted a protocol it should have refused")


print("=== 1. the module imports and names Attempt 1 without touching it ===")
check("PROTOCOL_PATH exists", E.PROTOCOL_PATH.is_file(), str(E.PROTOCOL_PATH))
check("clamp names are the sealed five", E.CLAMP_NAMES_RA2 ==
      ("REQUESTED_BUDGET", "AGGREGATE_RA2", "AGGREGATE", "CASH_FLOOR", "CONCENTRATION"))
from stockedge100.backtest.g2_engine import CLAMP_NAMES, RotationEngine  # noqa: E402
check("Attempt 1's four clamps all survive", set(CLAMP_NAMES) < set(E.CLAMP_NAMES_RA2),
      "added %s" % (set(E.CLAMP_NAMES_RA2) - set(CLAMP_NAMES)))
check("the engine subclasses Attempt 1's", issubclass(E.RotationEngineRA1, RotationEngine))
check("precedence is STOP > EXIT > THROTTLE > ENTRY",
      E.ORDER_KIND_PRECEDENCE == ("STOP", "EXIT", "THROTTLE", "ENTRY"))

print()
print("=== 2. the seal parses ===")
protocol = E.load_ra1_protocol()
ra = E.load_risk_architecture(protocol)
check("architecture id RA2", ra.architecture_id == "RA2")
check("exposure ceiling 0.50", ra.exposure_ceiling == Decimal("0.50"), str(ra.exposure_ceiling))
check("volatility target 0.10", ra.volatility_target == Decimal("0.10"), str(ra.volatility_target))
check("stop 0.08", ra.stop_fraction == Decimal("0.08"), str(ra.stop_fraction))
check("lockout 10 sessions", ra.lockout_sessions == 10, str(ra.lockout_sessions))
check("four bands", len(ra.bands) == 4, str(len(ra.bands)))
for band in ra.bands:
    print("       band %d  [%s, %s)  scalar %s  absolute ceiling %s"
          % (band.band, band.dd_from,
             "inf" if band.dd_to_exclusive is None else band.dd_to_exclusive,
             band.scalar, (ra.exposure_ceiling * band.scalar).quantize(Decimal("0.000000001"))))

print()
print("=== 3. the sealed band table reproduces Generation 1's RA1-5 f_cap values ===")
# The seal's provenance claim: bands 0, 2 and 3 as absolute ceilings equal Gen 1 RA1-5 exactly, and
# only band 1 is new. Recompute rather than trust the sentence.
absolute = {b.band: (ra.exposure_ceiling * b.scalar).quantize(Decimal("0.000000001")) for b in ra.bands}
for band, expected in ((0, "0.500000000"), (1, "0.375000000"), (2, "0.250000000"), (3, "0.125000000")):
    check("band %d absolute ceiling %s" % (band, expected),
          absolute[band] == Decimal(expected), str(absolute[band]))

print()
print("=== 4. band lookup honours the closed-lower / open-upper convention ===")
cases = [("0.00", 0), ("0.049999999", 0), ("0.05", 1), ("0.079999999", 1),
         ("0.08", 2), ("0.099999999", 2), ("0.10", 3), ("0.9999", 3), ("1.00", 3)]
for dd, expected in cases:
    got = ra.band_for(Decimal(dd))
    check("dd %-12s -> band %d" % (dd, expected), got == expected, "got %d" % got)

print()
print("=== 5. the structural validators are not vacuous ===")


def _bands(protocol):
    return protocol["risk_architecture"]["components"]["RA2-4"]["bands"]


rejects("architecture id is not RA2", lambda p: p["risk_architecture"].__setitem__("id", "RA9"))
rejects("no longer frozen before any variant ran",
        lambda p: p["risk_architecture"].__setitem__("frozen_before_any_variant_is_run", False))
rejects("constants became a grid axis",
        lambda p: p["risk_architecture"].__setitem__("not_part_of_the_grid", False))
rejects("combined scalar became a min()",
        lambda p: p["risk_architecture"]["combined_scalar"].__setitem__(
            "formula", "f(t) = min(f_vol(t), f_ladder(t)), quantized to nine decimal places, ROUND_DOWN."))
rejects("combined scalar stopped exempting the shutdown",
        lambda p: p["risk_architecture"]["combined_scalar"].__setitem__("does_not_apply_to", []))
rejects("a clamp was dropped",
        lambda p: p["risk_architecture"]["components"]["RA2-1"]["enforcement"]["part_a_entry_clamp"]
        .__setitem__("clamp_names", ["REQUESTED_BUDGET", "AGGREGATE_RA2"]))
rejects("volatility moved off the equity curve",
        lambda p: p["risk_architecture"]["components"]["RA2-2"].__setitem__("measured_on", "A_PRICE_SERIES"))
rejects("the stop reference became the raw entry price",
        lambda p: p["risk_architecture"]["components"]["RA2-3"].__setitem__("reference_price", "entry_price"))
rejects("bands are no longer contiguous",
        lambda p: _bands(p)[1].__setitem__("dd_from", "0.06"))
rejects("the deepest band gained an upper bound",
        lambda p: _bands(p)[3].__setitem__("dd_to_exclusive", "0.15"))
rejects("a deeper band sizes above a shallower one",
        lambda p: _bands(p)[2].__setitem__("scalar", "0.90"))
rejects("the shallowest band no longer starts at zero",
        lambda p: _bands(p)[0].__setitem__("dd_from", "0.01"))
rejects("the shallowest band no longer sizes at full weight",
        lambda p: _bands(p)[0].__setitem__("scalar", "0.90"))
rejects("a band scalar left (0, 1]",
        lambda p: _bands(p)[3].__setitem__("scalar", "0.00"))
rejects("the ceiling left (0, 1]",
        lambda p: p["risk_architecture"]["components"]["RA2-1"].__setitem__("value", "1.50"))
rejects("the stop left (0, 1)",
        lambda p: p["risk_architecture"]["components"]["RA2-3"].__setitem__("value", "1.00"))
rejects("the lockout became negative",
        lambda p: p["risk_architecture"]["components"]["RA2-5"].__setitem__("value", -1))
rejects("the lockout became a float",
        lambda p: p["risk_architecture"]["components"]["RA2-5"].__setitem__("value", 10.0))
rejects("the lockout moved to calendar days",
        lambda p: p["risk_architecture"]["components"]["RA2-5"].__setitem__(
            "counted_in_sessions_not_days", "Calendar days from the transition."))
print()
print("=== 5b. the identity and authorization checks are not vacuous either ===")
# These three predicates live in load_ra1_protocol(), which reads the file, not in
# load_risk_architecture(), which takes the parsed dict. Routing them through rejects() above
# exercised the wrong function and reported three false failures. Stub the path instead, so the
# real loader does its real read and reaches its real checks.


class StubProtocolPath:
    """Just enough of pathlib.Path for load_ra1_protocol(). The file on disk is never touched."""

    name = "g2_rotation_ra1_protocol.json"

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def is_file(self) -> bool:
        return True

    def read_text(self, encoding: str | None = None) -> str:
        return json.dumps(self.payload)


def rejects_identity(label: str, mutate) -> None:
    real_path = E.PROTOCOL_PATH
    payload = json.loads(real_path.read_text(encoding="utf-8"))
    mutate(payload)
    E.PROTOCOL_PATH = StubProtocolPath(payload)
    try:
        E.load_ra1_protocol()
    except (ConfigViolation, InvariantViolation, KeyError) as exc:
        check("rejects: %s" % label, True, type(exc).__name__)
        return
    else:
        check("rejects: %s" % label, False, "accepted a protocol it should have refused")
    finally:
        E.PROTOCOL_PATH = real_path


rejects_identity("the protocol stopped predating the strategy code",
                 lambda p: p.__setitem__("declared_before_any_strategy_code", False))
rejects_identity("the protocol is a different artifact",
                 lambda p: p.__setitem__("artifact_id", "SE100-CFG-9999"))
rejects_identity("live trading was authorized",
                 lambda p: p.__setitem__("live_trading_authorized", True))
# and the stub is a probe, not a state change: the module must still point at the real file.
check("PROTOCOL_PATH restored to the real file", E.PROTOCOL_PATH.is_file() and
      isinstance(E.PROTOCOL_PATH, pathlib.Path), str(E.PROTOCOL_PATH))
check("the unperturbed protocol still loads", E.load_ra1_protocol()["artifact_id"] == E.PROTOCOL_ID)

print()
print("=== 6. quantize_scalar rounds toward less exposure, never more ===")
for raw, expected in (("1", "1.000000000"), ("0.9999999999", "0.999999999"),
                      ("0.1234567891", "0.123456789"), ("0.25", "0.250000000")):
    got = E.quantize_scalar(Decimal(raw))
    check("quantize(%s) = %s" % (raw, expected), got == Decimal(expected), str(got))
check("ROUND_DOWN never rounds up",
      all(E.quantize_scalar(Decimal(v)) <= Decimal(v)
          for v in ("0.9999999999", "0.5000000005", "0.3333333339")))

print()
print("=== 7. the ladder state machine, on a hand-built drawdown and recovery ===")


class LadderProbe:
    """The transition rule alone, driven by a scripted drawdown path.

    Reimplements nothing: it calls the engine's own _advance_ladder against a stub carrying only the
    attributes that method touches. A separate reimplementation here would be testing itself.
    """

    def __init__(self):
        self.risk = ra
        self._band = 0
        self._lockout_until_index = None
        self._high_water = Decimal(100)
        self.ladder_descents = 0
        self.ladder_ascents = 0
        self.lockout_arms = 0
        self.recoveries_blocked = 0
        self.deepest_band = 0
        self.sessions_in_band = {b.band: 0 for b in ra.bands}

    step = E.RotationEngineRA1._advance_ladder
    remaining = E.RotationEngineRA1._lockout_remaining


probe = LadderProbe()
# equity path: flat, then a fast fall to a 12% drawdown, then a full recovery to the high-water mark.
path = [Decimal(100)] * 2 + [Decimal(94), Decimal(91), Decimal(88)] + [Decimal(100)] * 40
trace = []
for index, equity in enumerate(path):
    probe.step(index, equity)
    trace.append((index, equity, probe._band, probe.remaining(index)))

check("descends to band 1 on the first 6% drawdown", trace[2][2] == 1, "band %d" % trace[2][2])
check("descends to band 2 on the 9% drawdown", trace[3][2] == 2, "band %d" % trace[3][2])
check("descends to band 3 on the 12% drawdown", trace[4][2] == 3, "band %d" % trace[4][2])
check("three descents counted", probe.ladder_descents == 3, str(probe.ladder_descents))
check("the lockout armed on every descent", probe.lockout_arms == 3, str(probe.lockout_arms))
check("deepest band recorded as 3", probe.deepest_band == 3, str(probe.deepest_band))

# RA2-5: "The lockout expires 10 trading sessions after the session on which the transition
# occurred." The last descent is at index 4, so expiry is 4 + 10 = 14 and recovery is blocked while
# index < 14. Band 3 therefore spans indices 4..13 -- ten sessions, counting the descent itself --
# and exactly nine recovery attempts (indices 5..13) are computed and refused. An earlier draft of
# this check sliced 5..14 and expected ten; the slice was wrong, not the ladder.
held = [i for i, _, b, _ in trace if b == 3]
check("band 3 spans indices 4..13, ten sessions", held == list(range(4, 14)),
      "%d sessions, %s..%s" % (len(held), held[0], held[-1]))
check("sessions_in_band agrees with the trace", probe.sessions_in_band[3] == len(held),
      str(probe.sessions_in_band[3]))
check("the lockout expiry index is 4 + 10", probe._lockout_until_index == 14,
      str(probe._lockout_until_index))
check("lockout remaining is 10 at the descent, 1 at index 13, 0 at index 14",
      (trace[4][3], trace[13][3], trace[14][3]) == (10, 1, 0),
      str((trace[4][3], trace[13][3], trace[14][3])))
check("nine recoveries were computed and blocked", probe.recoveries_blocked == 9,
      str(probe.recoveries_blocked))
check("the first ascent lands at index 14", trace[14][2] == 2, "band %d at 14" % trace[14][2])
check("no ascent before index 14", all(b == 3 for _, _, b, _ in trace[5:14]))

# each ascent re-arms nothing, so recovery is one band per session from here: 2 at 14, 1 at 15, 0 at 16.
check("band 1 at index 15", trace[15][2] == 1, "band %d" % trace[15][2])
check("band 0 at index 16", trace[16][2] == 0, "band %d" % trace[16][2])
check("never climbs more than one band per session",
      all(trace[i][2] - trace[i + 1][2] <= 1 for i in range(len(trace) - 1)))
check("three ascents counted", probe.ladder_ascents == 3, str(probe.ladder_ascents))
check("an upward transition does not re-arm the lockout", probe.lockout_arms == 3,
      str(probe.lockout_arms))
check("sessions in band sum to the path length",
      sum(probe.sessions_in_band.values()) == len(path), str(probe.sessions_in_band))
print("       sessions per band: %s" % probe.sessions_in_band)

print()
print("=== 8. descent is immediate and to the full band, with no smoothing ===")
fast = LadderProbe()
for index, equity in enumerate([Decimal(100), Decimal(80)]):
    fast.step(index, equity)
check("a 20% one-session fall lands in band 3 directly", fast._band == 3, "band %d" % fast._band)
check("one descent, not three", fast.ladder_descents == 1, str(fast.ladder_descents))

print()
print("=== 9. a later descent extends the lockout rather than shortening it ===")
ext = LadderProbe()
script = [Decimal(100), Decimal(94)] + [Decimal(94)] * 4 + [Decimal(88)] + [Decimal(100)] * 20
for index, equity in enumerate(script):
    ext.step(index, equity)
    if index == 6:
        check("the second descent re-armed to index 16", ext._lockout_until_index == 16,
              str(ext._lockout_until_index))
check("the extended lockout still blocks at index 15",
      ext.recoveries_blocked >= 9, "%d blocked" % ext.recoveries_blocked)
check("recovery begins only after the later arm expires", ext.ladder_ascents > 0)

print()
print("=== 10. the combined scalar is the product, not the minimum ===")
for vol, band, expected in (("1.00", 0, "1.000000000"), ("1.00", 3, "0.250000000"),
                            ("0.50", 3, "0.125000000"), ("0.50", 1, "0.375000000")):
    got = E.quantize_scalar(Decimal(vol) * ra.scalar_of(band))
    check("f_vol %s x band %d = %s" % (vol, band, expected), got == Decimal(expected), str(got))
check("a product is strictly below the minimum when both terms bite",
      E.quantize_scalar(Decimal("0.50") * ra.scalar_of(3)) < min(Decimal("0.50"), ra.scalar_of(3)))

print()
print("=" * 96)
print("SMOKE %s -- %d failed" % ("CLEAN" if FAILED == 0 else "HAS PROBLEMS", FAILED))
sys.exit(1 if FAILED else 0)
