"""Exercise g2_engine_ra3's loader and its two provenance recomputations, without running a variant.

The engine class itself needs data, a cost model and a window; that comes later.  What can be checked
now is everything that happens before a session runs: the module imports (so the import-time AST
assertion fired and passed), the ladder loads, the loader's three RA3-only predicates hold, and the
two provenance checks agree with the sealed files rather than with this script's expectations.

Nothing is written.  ASCII only: the console is cp1252.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100/src")))

import json  # noqa: E402

from stockedge100.backtest.errors import ConfigViolation  # noqa: E402
from stockedge100.backtest import g2_engine_ra3 as m  # noqa: E402

problems = []


def check(label, ok, detail=""):
    print("  %-62s %s %s" % (label, "OK  " if ok else "FAIL", detail))
    if not ok:
        problems.append(label)


print("=" * 100)
print("1. the import-time AST assertion (G2A3-CONFLICT-31)")
print("     module imported, so the assertion passed")
measured = m.attributes_derived_from_risk()
check("measured derived set", measured == m.RISK_DERIVED_ATTRIBUTES, str(sorted(measured)))
check("it is exactly two attributes", len(measured) == 2)
# An AST walker that finds nothing also "agrees" with a declaration of nothing; prove it finds the
# annotated assignment specifically, since that is the one a naive walker drops.
check("it found the ANNOTATED assignment", "sessions_in_band" in measured)
check("it found the plain assignment", "risk" in measured)

print()
print("=" * 100)
print("2. the protocol loads and is Attempt 3's")
protocol = m.load_ra3_protocol()
check("artifact_id", protocol["artifact_id"] == m.PROTOCOL_ID, protocol["artifact_id"])
check("attempt is 3", protocol["attempt"] == 3, str(protocol["attempt"]))
check("strategy_id", protocol["strategy_id"] == m.STRATEGY_ID, protocol["strategy_id"])

print()
print("=" * 100)
print("3. the RA3 architecture parses and validates")
risk = m.load_risk_architecture_ra3(protocol)
check("architecture_id is RA3", risk.architecture_id == "RA3", risk.architecture_id)
check("exposure ceiling 0.50", str(risk.exposure_ceiling) == "0.50", str(risk.exposure_ceiling))
check("volatility target 0.10", str(risk.volatility_target) == "0.10", str(risk.volatility_target))
check("stop fraction 0.08", str(risk.stop_fraction) == "0.08", str(risk.stop_fraction))
check("lockout 10 sessions", risk.lockout_sessions == 10, str(risk.lockout_sessions))
check("exactly 3 bands", len(risk.bands) == m.RA3_BAND_COUNT, str(len(risk.bands)))
for band in risk.bands:
    print("     band %d  [%s, %s)  scalar %s"
          % (band.band, band.dd_from, band.dd_to_exclusive, band.scalar))

print()
print("  the sentence the attempt is defined by: nothing engages below 8%")
from decimal import Decimal  # noqa: E402

# Every drawdown RA2's deleted rung would have throttled must now be full sizing.  0.05 and 0.0501
# are the two that matter: under RA2 they sat in the [0.05, 0.08) tier at scalar 0.75.
for dd in ("0.00", "0.0499", "0.05", "0.0501", "0.07", "0.079999999"):
    b = risk.band_for(Decimal(dd))
    s = risk.scalar_of(b)
    check("dd=%-12s -> band %d scalar %s (RA2 threw 0.75 here)" % (dd, b, s),
          b == 0 and s == Decimal("1.00"))
for dd, want_band, want_scalar in (
    ("0.08", 1, "0.50"), ("0.099999", 1, "0.50"),
    ("0.10", 2, "0.25"), ("0.5", 2, "0.25"), ("0.99", 2, "0.25"),
):
    b = risk.band_for(Decimal(dd))
    s = risk.scalar_of(b)
    check("dd=%-12s -> band %d scalar %s" % (dd, b, s),
          b == want_band and s == Decimal(want_scalar))

print()
print("=" * 100)
print("4. Generation 1 provenance, recomputed from that generation's own sealed file")
prov = m.check_generation_1_provenance(risk)
print(json.dumps(prov, indent=2))
check("G1 states its ladder twice and they agree",
      prov["generation_1_states_it_twice_and_they_agree"] is True)
check("3 experiments cross-checked", len(prov["generation_1_ladder_rungs_per_experiment"]) == 3)
check("RA3 caps equal G1 prose caps",
      prov["ra3_bands_as_absolute_caps"] == prov["generation_1_ladder_from_ra1_5_prose"])
caps = [c for _, _, c in prov["ra3_bands_as_absolute_caps"]]
check("caps are 0.5 / 0.25 / 0.125", caps == ["0.5", "0.25", "0.125"], str(caps))
edges = [(a, b) for a, b, _ in prov["ra3_bands_as_absolute_caps"]]
check("bands are [0,0.08) [0.08,0.1) [0.1,inf)",
      edges == [("0", "0.08"), ("0.08", "0.1"), ("0.1", None)], str(edges))
# The experiments state only the two engaged tiers; the prose states all three.  That the two
# statements were cross-checked is the point -- assert the shapes really do differ, or "they agree"
# could be true of two readings of the same list.
per_exp = list(prov["generation_1_ladder_rungs_per_experiment"].values())[0]
check("experiments state 2 tiers, prose states 3",
      len(per_exp) == 2 and len(prov["generation_1_ladder_from_ra1_5_prose"]) == 3)

print()
print("=" * 100)
print("5. single difference from RA2, recomputed from Attempt 2's own sealed file")
diff = m.check_single_difference_from_ra2(risk)
print(json.dumps(diff, indent=2))
check("deleted tier is [0.05, 0.08) at 0.75",
      diff["deleted_tier"] == ["0.05", "0.08", "0.75"], str(diff["deleted_tier"]))
check("RA2 had 4 bands", len(diff["ra2_bands"]) == 4, str(len(diff["ra2_bands"])))
check("RA3 has 3", len(diff["ra3_bands"]) == 3, str(len(diff["ra3_bands"])))
check("exactly one band added", len(diff["bands_added_by_ra3"]) == 1)
check("the added band is [0.00, 0.08) at 1.00",
      diff["bands_added_by_ra3"][0] == ["0.00", "0.08", "1.00"],
      str(diff["bands_added_by_ra3"][0]))

print()
print("=" * 100)
print("6. the loader refuses a ladder that is not RA3's")
mutations = [
    ("RA2's own four-band ladder", lambda a: _swap_bands(a, [
        {"band": 0, "dd_from": "0.00", "dd_to_exclusive": "0.05", "scalar": "1.00"},
        {"band": 1, "dd_from": "0.05", "dd_to_exclusive": "0.08", "scalar": "0.75"},
        {"band": 2, "dd_from": "0.08", "dd_to_exclusive": "0.10", "scalar": "0.50"},
        {"band": 3, "dd_from": "0.10", "dd_to_exclusive": None, "scalar": "0.25"}])),
    ("a shallow rung at 0.06", lambda a: _swap_bands(a, [
        {"band": 0, "dd_from": "0.00", "dd_to_exclusive": "0.06", "scalar": "1.00"},
        {"band": 1, "dd_from": "0.06", "dd_to_exclusive": "0.10", "scalar": "0.50"},
        {"band": 2, "dd_from": "0.10", "dd_to_exclusive": None, "scalar": "0.25"}])),
    ("two bands only", lambda a: _swap_bands(a, [
        {"band": 0, "dd_from": "0.00", "dd_to_exclusive": "0.08", "scalar": "1.00"},
        {"band": 1, "dd_from": "0.08", "dd_to_exclusive": None, "scalar": "0.50"}])),
    ("architecture id RA2", lambda a: a.__setitem__("id", "RA2")),
]


def _swap_bands(architecture, bands):
    architecture["components"]["RA3-4"]["bands"] = bands


for label, mutate in mutations:
    hostile = json.loads(json.dumps(protocol))
    mutate(hostile["risk_architecture"])
    try:
        m.load_risk_architecture_ra3(hostile)
        check("refuses %s" % label, False, "LOADED IT")
    except (ConfigViolation, AssertionError, Exception) as exc:
        check("refuses %s" % label, True, type(exc).__name__ + ": " + str(exc)[:60])

print()
print("=" * 100)
print("PROBLEMS: %s" % (problems or "none"))
