"""Fourth pass: the last five unknowns.

  1. score_neighbourhood's source (AT-J/AT-K assert its component breakdown)
  2. GridRunRA3's derived properties (shutdown_fired, fill_count) that selection_inputs reads
  3. whether g2_engine_ra1 carries the AST precedent AT-M is told to reuse
  4. RiskArchitecture: is it frozen / replaceable, and what does scalar_of do
  5. the RA3 engine's inherited attribute names AT-D/AT-E drive (_advance_ladder etc.)
"""

import dataclasses
import inspect
import pathlib
import re
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def show(title, text):
    print("   --- %s ---" % title)
    for line in safe(text).splitlines():
        print("   |%s" % line)


print("=" * 100)
print("1. score_neighbourhood")
from stockedge100.strategies import g2_selection_v2 as S

show("score_neighbourhood", inspect.getsource(S.score_neighbourhood))

print()
print("=" * 100)
print("2. GridRunRA3 properties")
from stockedge100.strategies import g2_runner_ra3 as RUN

print("   fields: %s" % [f.name for f in dataclasses.fields(RUN.GridRunRA3)])
print("   frozen: %s" % RUN.GridRunRA3.__dataclass_params__.frozen)
for name in sorted(n for n in dir(RUN.GridRunRA3) if not n.startswith("_")):
    obj = getattr(RUN.GridRunRA3, name)
    kind = "property" if isinstance(obj, property) else type(obj).__name__
    print("   %-24s %s" % (name, kind))
for name in ("shutdown_fired", "fill_count"):
    obj = getattr(RUN.GridRunRA3, name, None)
    if isinstance(obj, property):
        show(name, inspect.getsource(obj.fget))

print()
print("=" * 100)
print("3. AST precedent in g2_engine_ra1 (AT-M says Attempt 2 used one against Attempt 1)")
ra1 = pathlib.Path(
    ROOT / "src/stockedge100/backtest/g2_engine_ra1.py").read_text("utf-8")
print("   'ast' imported in g2_engine_ra1: %s" % ("import ast" in ra1))
for m in re.finditer(r"^def ([A-Za-z_0-9]+)\(", ra1, re.M):
    print("      def %s" % m.group(1))
for m in re.finditer(r"^(?:\s*)(?:RISK_DERIVED|ATTRIBUTES)[A-Z_]*\s*=", ra1, re.M):
    print("      const line: %s" % safe(m.group(0)))

print()
print("=" * 100)
print("4. RiskArchitecture")
from stockedge100.backtest import g2_engine_ra1 as E1
from stockedge100.backtest import g2_engine_ra3 as E3

arch = E3.load_risk_architecture_ra3()
cls = type(arch)
print("   class %s from %s" % (cls.__name__, cls.__module__))
print("   frozen=%s fields=%s"
      % (cls.__dataclass_params__.frozen, [f.name for f in dataclasses.fields(cls)]))
band_cls = type(arch.bands[0])
print("   band class %s frozen=%s fields=%s"
      % (band_cls.__name__, band_cls.__dataclass_params__.frozen,
         [f.name for f in dataclasses.fields(band_cls)]))
for name in sorted(n for n in dir(cls) if not n.startswith("_")):
    obj = getattr(cls, name)
    if inspect.isfunction(obj):
        print("   def %-22s %s" % (name, inspect.signature(obj)))
print("   scalar_of(0..2) = %s" % [str(arch.scalar_of(b)) for b in range(3)])
print("   replace works: %s"
      % (dataclasses.replace(arch, exposure_ceiling=arch.exposure_ceiling) is not arch))

print()
print("=" * 100)
print("5. names AT-D/AT-E drive on the engine")
for name in ("_advance_ladder", "_lockout_remaining", "_volatility_scalar", "_band",
             "_high_water", "_lockout_until_index", "deepest_band", "ladder_descents",
             "ladder_ascents", "lockout_arms", "recoveries_blocked", "sessions_in_band",
             "risk_state_payload", "risk_state_digest", "clamp_summary", "risk_summary",
             "binding_clamp_counts", "stop_events", "stop_preempted_signal_exit",
             "suppressed_legs", "vol_scalar_min", "vol_scalar_sessions_below_one",
             "vol_scalar_undefined_sessions"):
    on3 = hasattr(E3.RotationEngineRA3, name)
    print("   %-32s on RotationEngineRA3 class: %s" % (name, on3))
print("   module constants on g2_engine_ra1: SCALAR_DECIMALS=%s ORDER_KIND_PRECEDENCE=%s"
      % (getattr(E1, "SCALAR_DECIMALS", "<absent>"),
         getattr(E1, "ORDER_KIND_PRECEDENCE", "<absent>")))
print("   quantize_scalar present: %s" % hasattr(E1, "quantize_scalar"))
print("   RA3 __all__ has check_single_difference_from_ra2: %s"
      % ("check_single_difference_from_ra2" in dir(E3)))
