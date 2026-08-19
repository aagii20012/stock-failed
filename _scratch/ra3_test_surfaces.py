"""Every surface the AT-A..AT-M test module will touch, dumped before a line of it is written.

The RA1 test module (44 tests) is the template, but it names `RotationEngineRA1`,
`load_risk_architecture`, `SelectionInputRA1`, `SELECTION_FIELD_NAMES`, `variant_by_id` on
`g2_rotation_ra1`, and `verify_attempt_1_modules`. RA3 renamed most of those. AT-I and AT-J in
particular need *verbatim source text* (the injection re-execs the dataclass body with one field
added, so the body must be matched exactly) and the real neighbour function name.

Prints laundered to ASCII: cp1252 kills the process on U+2014.
"""

import dataclasses
import inspect
import json
import pathlib
import re
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def wrap(text, indent=6, width=110):
    text = safe(text)
    while text:
        print("%s%s" % (" " * indent, text[:width]))
        text = text[width:]


print("=" * 100)
print("1. g2_selection_v2 -- the whole public surface")
from stockedge100.strategies import g2_selection_v2 as S

print("   __all__ %s" % getattr(S, "__all__", None))
for name in sorted(n for n in dir(S) if not n.startswith("__")):
    obj = getattr(S, name)
    if dataclasses.is_dataclass(obj):
        print("   dataclass %-26s frozen=%s fields=%s"
              % (name, obj.__dataclass_params__.frozen,
                 [f.name for f in dataclasses.fields(obj)]))
    elif inspect.isfunction(obj):
        print("   def       %-26s %s" % (name, inspect.signature(obj)))
    elif isinstance(obj, (tuple, list, dict, str, int)):
        print("   const     %-26s %s" % (name, safe(repr(obj))[:96]))

print()
print("   --- SelectionInputV2 dataclass body, VERBATIM (AT-I's injection must match it) ---")
sel_src = pathlib.Path(S.__file__).read_text("utf-8")
m = re.search(r"class SelectionInputV2.*?\n\n", sel_src, re.S)
print("".join("   |%s\n" % safe(line) for line in (m.group(0) if m else "<none>").splitlines()))

print("   --- the import-time assertion, verbatim ---")
for line in sel_src.splitlines():
    if "SELECTION_V2_FIELD_NAMES" in line and ("assert" in line or "==" in line):
        print("   |%s" % safe(line))

print("   --- neighbour-related names in the module ---")
for m in re.finditer(r"^(?:def|class) ([A-Za-z_0-9]+)", sel_src, re.M):
    if "neigh" in m.group(1).lower() or "score" in m.group(1).lower():
        print("   %s" % m.group(1))

print()
print("=" * 100)
print("2. g2_engine_ra3")
from stockedge100.backtest import g2_engine_ra3 as E

print("   __all__ %s" % getattr(E, "__all__", None))
for name in sorted(n for n in dir(E) if not n.startswith("_")):
    obj = getattr(E, name)
    if inspect.isclass(obj):
        print("   class %-32s bases=%s" % (name, [b.__name__ for b in obj.__bases__]))
    elif inspect.isfunction(obj):
        print("   def   %-32s %s" % (name, inspect.signature(obj)))

print("   --- RotationEngineRA3 methods defined here (not inherited) ---")
eng_src = pathlib.Path(E.__file__).read_text("utf-8")
for m in re.finditer(r"^    def ([A-Za-z_0-9]+)\(", eng_src, re.M):
    print("      %s" % m.group(1))

print()
print("   --- the RA3 architecture object as loaded ---")
arch = E.load_risk_architecture_ra3()
print("   type=%s" % type(arch).__name__)
print("   fields=%s" % [f.name for f in dataclasses.fields(arch)])
print("   bands:")
for b in arch.bands:
    print("      band=%s dd_from=%s dd_to_exclusive=%s scalar=%s"
          % (b.band, b.dd_from, b.dd_to_exclusive, b.scalar))
print("   exposure_ceiling=%s stop_fraction=%s lockout_sessions=%s"
      % (arch.exposure_ceiling, arch.stop_fraction, arch.lockout_sessions))
for d in ("0.00", "0.0499999999", "0.05", "0.06", "0.0799999999", "0.08",
          "0.0999999999", "0.10", "0.30"):
    from decimal import Decimal
    print("      band_for(%-14s) = %s   scalar=%s"
          % (d, arch.band_for(Decimal(d)), arch.scalar_of(arch.band_for(Decimal(d)))))

print()
print("=" * 100)
print("3. g2_rotation_ra3 -- variant ids and candidate surface")
from stockedge100.strategies import g2_rotation_ra3 as R

print("   __all__ %s" % getattr(R, "__all__", None))
for name in sorted(n for n in dir(R) if not n.startswith("_")):
    obj = getattr(R, name)
    if inspect.isfunction(obj):
        print("   def   %-32s %s" % (name, inspect.signature(obj)))
    elif dataclasses.is_dataclass(obj):
        print("   dc    %-32s %s" % (name, [f.name for f in dataclasses.fields(obj)]))
variants = R.rotation_variants()
print("   %d variants; first three ids:" % len(variants))
for v in variants[:3]:
    print("      %s" % v.variant_id)
print("   last id: %s" % variants[-1].variant_id)

print()
print("=" * 100)
print("4. g2_gate_ra3 -- the three internals the extra tests target")
from stockedge100.strategies import g2_gate_ra3 as G

for name in ("PROSE_ALIASES", "_check_prose_renames_are_as_declared",
             "_pointers_dropped_since_attempt_2", "_keys_the_frozen_evaluators_read"):
    obj = getattr(G, name, "<ABSENT>")
    if callable(obj):
        print("   %-40s %s" % (name, inspect.signature(obj)))
    else:
        print("   %-40s %s" % (name, safe(repr(obj))[:110]))

print()
print("=" * 100)
print("5. prior_attempt_modules_immutable -- names, and where the digests live")
node = P3["prior_attempt_modules_immutable"]
print("   keys: %s" % list(node))
mods = node.get("modules", [])
print("   %d modules:" % len(mods))
for mod in mods:
    print("      %s" % mod)
for key in node:
    if key != "modules":
        print("   %s:" % key)
        wrap(json.dumps(node[key], ensure_ascii=False) if not isinstance(node[key], str)
             else node[key])

gov = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
print("   governance seal exists: %s" % gov.is_file())
if gov.is_file():
    payload = json.loads(gov.read_text("utf-8"))
    print("   top-level keys: %s" % sorted(payload))
    for key in sorted(payload):
        if isinstance(payload[key], dict) and any("digest" in k for k in payload[key]):
            print("   %s -> %s" % (key, sorted(payload[key])))

print()
print("=" * 100)
print("6. risk_architecture section of CFG-3105 (AT-L reads the sealed band table)")
node = P3["risk_architecture"]
for key, value in node.items():
    if isinstance(value, (dict, list)):
        print("   %s:" % key)
        wrap(json.dumps(value, ensure_ascii=False), indent=8)
    else:
        print("   %-40s %s" % (key, safe(value)[:100]))

print()
print("=" * 100)
print("7. runner entry points the tests call")
from stockedge100.strategies import g2_runner_ra3 as RUN

for name in ("verify_prior_attempt_modules", "load_grid_dataset", "selection_inputs",
             "select_representative_ra3", "GATE_RUN_LABEL", "STRESS_RUN_LABEL"):
    obj = getattr(RUN, name, "<ABSENT>")
    if callable(obj):
        print("   %-34s %s" % (name, inspect.signature(obj)))
    else:
        print("   %-34s %s" % (name, safe(repr(obj))))
