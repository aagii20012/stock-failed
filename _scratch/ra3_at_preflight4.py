"""Fourth preflight: AT-L's architecture surface and the two provenance checks, measured."""

import json
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest import g2_engine_ra3 as eng3
from stockedge100.backtest import g2_engine_ra1 as eng1

ARCH = eng3.load_risk_architecture_ra3()
ARCH2 = eng1.load_risk_architecture()


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


print("=" * 100)
print("L. RA3 architecture surface")
print("   type=%s" % type(ARCH).__name__)
print("   fields=%s" % sorted(k for k in dir(ARCH) if not k.startswith("_")))
print("   architecture_id=%r" % getattr(ARCH, "architecture_id", getattr(ARCH, "id", None)))
print("   bands:")
for b in ARCH.bands:
    print("      band=%d dd_from=%s dd_to_exclusive=%s scalar=%s"
          % (b.band, b.dd_from, b.dd_to_exclusive, b.scalar))
print("   RA2 bands:")
for b in ARCH2.bands:
    print("      band=%d dd_from=%s dd_to_exclusive=%s scalar=%s"
          % (b.band, b.dd_from, b.dd_to_exclusive, b.scalar))

for name in ("exposure_ceiling", "vol_target", "stop_fraction", "lockout_sessions",
             "vol_lookback", "trading_days", "scalar_decimals", "min_scalar"):
    print("   %-20s = %r" % (name, getattr(ARCH, name, "<absent>")))

print()
print("   effective caps per band (ceiling * scalar):")
for b in ARCH.bands:
    print("      band=%d cap=%s" % (b.band, (ARCH.exposure_ceiling * b.scalar)))

print()
print("   band_for / scalar_of across the deleted tier:")
for dd in ("0.00", "0.0499", "0.05", "0.06", "0.0799", "0.08", "0.0999", "0.10", "0.30"):
    d = Decimal(dd)
    print("      dd=%-7s RA3 band=%d scalar=%s | RA2 band=%d scalar=%s"
          % (dd, ARCH.band_for(d), ARCH.scalar_of(ARCH.band_for(d)),
             ARCH2.band_for(d), ARCH2.scalar_of(ARCH2.band_for(d))))

print()
print("=" * 100)
print("provenance checks")
prov = eng3.check_generation_1_provenance(ARCH)
print("   check_generation_1_provenance ->")
print(safe(json.dumps(prov, indent=6, default=str)))

diff = eng3.check_single_difference_from_ra2(ARCH)
print("   check_single_difference_from_ra2 ->")
print(safe(json.dumps(diff, indent=6, default=str)))

print()
print("=" * 100)
print("constants")
print("   RA3_BAND_COUNT=%r" % eng3.RA3_BAND_COUNT)
print("   RA3_SHALLOWEST_ENGAGEMENT=%r" % eng3.RA3_SHALLOWEST_ENGAGEMENT)
print("   DELETED_RA2_TIER=%r" % (eng3.DELETED_RA2_TIER,))
print("   RISK_DERIVED_ATTRIBUTES=%r" % (eng3.RISK_DERIVED_ATTRIBUTES,))
print("   PROTOCOL_ID=%r PROTOCOL_PATH=%s" % (eng3.PROTOCOL_ID, eng3.PROTOCOL_PATH.name))
print("   ATTEMPT_2_PROTOCOL_PATH=%s" % eng3.ATTEMPT_2_PROTOCOL_PATH.name)
print("   GENERATION_1_PROTOCOL_PATH=%s" % eng3.GENERATION_1_PROTOCOL_PATH.name)

print()
print("injection: a four-band ladder must not load")
proto = json.loads(eng3.PROTOCOL_PATH.read_text(encoding="utf-8"))
bands = proto["risk_architecture"]["components"]["RA3-1"]["bands"]
print("   component key list: %s" % sorted(proto["risk_architecture"]["components"]))
print("   sealed band rows: %s" % safe(json.dumps(bands)))
