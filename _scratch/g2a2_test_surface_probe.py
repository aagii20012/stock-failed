"""Verify every name the new adversarial test file reaches for, before running pytest.

A test that fails on an AttributeError tells you nothing about the engine. ASCII output only.
"""

from __future__ import annotations

import dataclasses
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))


def probe(label, fn):
    try:
        print("OK   %-52s %s" % (label, fn()))
    except Exception as exc:  # noqa: BLE001
        print("FAIL %-52s %s: %s" % (label, type(exc).__name__, exc))


import stockedge100.backtest.config as cfg  # noqa: E402
import stockedge100.backtest.costs as costs_mod  # noqa: E402
import stockedge100.backtest.dataset as ds  # noqa: E402
import stockedge100.backtest.engine as eng  # noqa: E402
import stockedge100.backtest.errors as errs  # noqa: E402
import stockedge100.backtest.orders as orders  # noqa: E402
import stockedge100.data.calendar as cal  # noqa: E402
from stockedge100.backtest import g2_engine_ra1 as E  # noqa: E402
from stockedge100.strategies import g2_rotation_ra1 as rot  # noqa: E402
from stockedge100.strategies import g2_runner_ra1 as R  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402

print("== module-level names ==")
probe("config.PROJECT_ROOT", lambda: cfg.PROJECT_ROOT)
probe("costs.BASE", lambda: costs_mod.BASE)
probe("costs.ZERO", lambda: costs_mod.ZERO)
probe("dataset.PriceSeries", lambda: ds.PriceSeries)
probe("dataset.series_from_rows sig", lambda: inspect.signature(ds.series_from_rows))
probe("engine.EquityPoint fields", lambda: [f.name for f in dataclasses.fields(eng.EquityPoint)])
probe("errors.ConfigViolation", lambda: errs.ConfigViolation)
probe("errors.InvariantViolation", lambda: errs.InvariantViolation)
probe("errors.WindowViolation", lambda: errs.WindowViolation)
probe("orders.BUY", lambda: orders.BUY)
probe("calendar.sessions_between sig", lambda: inspect.signature(cal.sessions_between))

print()
print("== g2_engine_ra1 ==")
probe("ORDER_KIND_PRECEDENCE", lambda: E.ORDER_KIND_PRECEDENCE)
probe("SCALAR_DECIMALS", lambda: E.SCALAR_DECIMALS)
probe("load_risk_architecture", lambda: type(E.load_risk_architecture()).__name__)
probe("quantize_scalar", lambda: E.quantize_scalar)
arch = E.load_risk_architecture()
probe("arch fields", lambda: [f.name for f in dataclasses.fields(arch)])
probe("band fields", lambda: [f.name for f in dataclasses.fields(arch.bands[0])])
probe("arch.band_for(0.06)", lambda: arch.band_for(__import__("decimal").Decimal("0.06")))
probe("arch.scalar_of(2)", lambda: arch.scalar_of(2))
probe("RotationEngineRA1.__init__ sig", lambda: inspect.signature(E.RotationEngineRA1.__init__))

print()
print("== engine instance attributes (from __init__ source) ==")
src = inspect.getsource(E.RotationEngineRA1.__init__)
for line in src.splitlines():
    stripped = line.strip()
    if stripped.startswith("self.") and "=" in stripped:
        print("   " + stripped.split("=")[0].strip())

print()
print("== engine methods of interest ==")
for name in ("_advance_ladder", "_lockout_remaining", "_volatility_scalar", "risk_state_payload",
             "risk_state_digest", "risk_summary", "clamp_summary", "_close_marked_values", "run"):
    probe(name, lambda n=name: inspect.signature(getattr(E.RotationEngineRA1, n)))

print()
print("== g2_rotation_ra1 ==")
probe("variant_by_id", lambda: inspect.signature(rot.variant_by_id))
probe("RotationCandidateRA1 sig", lambda: inspect.signature(rot.RotationCandidateRA1.__init__))
probe("rotation_cost_model", lambda: inspect.signature(rot.rotation_cost_model))
probe("variant ids (first 3)", lambda: [v.variant_id for v in rot.rotation_variants()[:3]])
probe("variant fields", lambda: [f.name for f in dataclasses.fields(rot.rotation_variants()[0])])

print()
print("== g2_runner_ra1 ==")
probe("SELECTION_FIELD_NAMES", lambda: R.SELECTION_FIELD_NAMES)
probe("SelectionInputRA1 fields",
      lambda: [f.name for f in dataclasses.fields(R.SelectionInputRA1)])
probe("SelectionInputRA1.to_json", lambda: inspect.signature(R.SelectionInputRA1.to_json))
probe("selection_inputs", lambda: inspect.signature(R.selection_inputs))
probe("GridRunRA1 fields", lambda: [f.name for f in dataclasses.fields(R.GridRunRA1)])
probe("verify_attempt_1_modules", lambda: inspect.signature(R.verify_attempt_1_modules))
probe("load_grid_dataset", lambda: inspect.signature(R.load_grid_dataset))

print()
print("== g2_window_guard ==")
probe("development_bound", lambda: guard.development_bound())
probe("prohibited_windows", lambda: guard.prohibited_windows())
probe("generation_2_window sig", lambda: inspect.signature(guard.generation_2_window))
probe("assert_series_within_bound sig", lambda: inspect.signature(guard.assert_series_within_bound))

print()
print("== RunResult surface ==")
probe("result fields", lambda: [f.name for f in dataclasses.fields(eng.RunResult)]
      if hasattr(eng, "RunResult") else "no RunResult in backtest.engine")
for name in dir(E):
    if name.endswith("Result"):
        print("   engine_ra1 exports:", name)
