"""Second preflight: the AT-G / AT-H / AT-L / extra-gate-test literals, measured before assertion."""

import hashlib
import inspect
import json
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

print("=" * 100)
print("G. window guard surface")
from stockedge100.strategies import g2_window_guard as guard

print("   public: %s" % [n for n in dir(guard) if not n.startswith("_")])
for n in ("assert_series_within_bound", "generation_2_window", "development_bound",
          "prohibited_windows"):
    obj = getattr(guard, n, None)
    print("   def %-30s %s" % (n, inspect.signature(obj) if obj else "<ABSENT>"))
print("   module file: %s" % pathlib.Path(guard.__file__).name)

from stockedge100.strategies import g2_runner_ra3 as runner

print("   runner.load_grid_dataset sig %s" % inspect.signature(runner.load_grid_dataset))
src = inspect.getsource(runner.load_grid_dataset)
print("   loader mentions the guard module: %s" % ("g2_window_guard" in src or "guard." in src))
for line in src.splitlines():
    print("   |%s" % line)

print()
print("=" * 100)
print("H. the seventeen immutable modules")
cfg = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
node = cfg["prior_attempt_modules_immutable"]
print("   node keys: %s" % sorted(node))
print("   count=%s a1=%d a2=%d" % (node["count"], len(node["attempt_1_modules"]),
                                   len(node["attempt_2_modules"])))
for k in ("attempt_1_modules", "attempt_2_modules"):
    for m in node[k]:
        print("      %-14s %s" % (k[:10], m))
print("   excluded key present: %s" % [k for k in node if "exclu" in k])
for k in node:
    if k not in ("attempt_1_modules", "attempt_2_modules"):
        print("      %-28s %s" % (k, str(node[k])[:150]))

seal = json.loads((ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json")
                  .read_text("utf-8"))
digests = seal["contamination_measurement"]["prior_attempt_module_digests"]
print("   seal digest entries=%d  sets agree=%s"
      % (len(digests),
         sorted(digests) == sorted(node["attempt_1_modules"] + node["attempt_2_modules"])))
moved = [r for r, d in digests.items()
         if hashlib.sha256((ROOT / r).read_bytes()).hexdigest() != d]
print("   modules that moved right now: %s" % moved)

rep = runner.verify_prior_attempt_modules()
print("   runner report: count=%s a1=%s a2=%s moved=%s"
      % (rep["module_count"], rep["attempt_1_module_count"], rep["attempt_2_module_count"],
         rep["modules_that_moved"]))
print("   verified == seal digests: %s" % (rep["modules_verified"] == digests))
print("   excluded_and_why: %s" % str(rep["excluded_and_why"])[:400])
print("   list sources: %s | %s" % (rep["attempt_1_list_source"], rep["attempt_2_list_source"]))

print()
print("   attempt 3's own modules, which must NOT be in the immutable set:")
A3 = [
    "src/stockedge100/strategies/g2_rotation_ra3.py",
    "src/stockedge100/strategies/g2_gate_ra3.py",
    "src/stockedge100/strategies/g2_runner_ra3.py",
    "src/stockedge100/strategies/g2_selection_v2.py",
    "src/stockedge100/backtest/g2_engine_ra3.py",
    "src/stockedge100/reporting/g2_stage3_attempt3_evidence.py",
]
for r in A3:
    print("      exists=%s immutable=%s  %s" % ((ROOT / r).is_file(), r in digests, r))

print()
print("=" * 100)
print("L. the band table as absolute caps")
from stockedge100.backtest.g2_engine_ra3 import (RA3_BAND_COUNT, RA3_SHALLOWEST_ENGAGEMENT,
                                                 DELETED_RA2_TIER, load_risk_architecture_ra3)

arch = load_risk_architecture_ra3()
print("   RA3_BAND_COUNT=%s SHALLOWEST=%s DELETED_RA2_TIER=%s"
      % (RA3_BAND_COUNT, RA3_SHALLOWEST_ENGAGEMENT, DELETED_RA2_TIER))
print("   band count=%d" % len(arch.bands))
print("   absolute caps: %s"
      % [str((arch.exposure_ceiling * b.scalar).quantize(Decimal("0.000000001")))
         for b in arch.bands])
print("   band fields: %s" % [f for f in dir(arch.bands[0]) if not f.startswith("_")])
print("   arch fields: %s" % [f for f in dir(arch) if not f.startswith("_")])
print("   vol target lives where: %s"
      % [(n, getattr(arch, n)) for n in dir(arch) if "vol" in n.lower()])

print()
print("=" * 100)
print("X. the two extra gate tests")
from stockedge100.strategies import g2_gate_ra3 as G
from stockedge100.backtest.errors import ConfigViolation

crit = G.load_criteria_ra3()
print("   criteria id=%s conditions=%d" % (crit.get("id"), len(crit["conditions"])))
print("   _check_prose_renames_are_as_declared sig %s"
      % inspect.signature(G._check_prose_renames_are_as_declared))
saved = G.PROSE_ALIASES
try:
    G.PROSE_ALIASES = saved + (("S3-C1", (), "attempt_2_status", "attempt_3_status"),)
    G._check_prose_renames_are_as_declared(G.load_criteria_ra3())
    print("   widened table -> NO RAISE (bad)")
except ConfigViolation as exc:
    print("   widened table -> ConfigViolation: %s" % str(exc)[:220])
except Exception as exc:                                             # noqa: BLE001
    print("   widened table -> %s: %s" % (type(exc).__name__, str(exc)[:200]))
finally:
    G.PROSE_ALIASES = saved

try:
    G.PROSE_ALIASES = saved[:1]
    G._check_prose_renames_are_as_declared(G.load_criteria_ra3())
    print("   narrowed table -> NO RAISE (bad)")
except ConfigViolation as exc:
    print("   narrowed table -> ConfigViolation: %s" % str(exc)[:200])
finally:
    G.PROSE_ALIASES = saved

print("   clean table -> %s" % (G._check_prose_renames_are_as_declared(G.load_criteria_ra3()),))
print("   dropped=%d read=%d" % (len(G._pointers_dropped_since_attempt_2()),
                                 len(G._keys_the_frozen_evaluators_read())))
inter = set(G._pointers_dropped_since_attempt_2()) & set(G._keys_the_frozen_evaluators_read())
print("   intersection (the ones the adapter must supply): %s" % sorted(inter))
