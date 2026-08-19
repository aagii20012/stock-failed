"""Third and last surface pass: the handful of names the AT-A..AT-M module calls that passes one
and two did not pin down.

Specifically: how RA3's candidate/cost-model is built (AT-A..AT-F all need an engine), where the
seventeen immutable digests actually live and what `verify_prior_attempt_modules` returns (AT-H),
the runner's label helpers (AT-I's end-to-end projection), `check_seal_agreement`'s shape, and
whichever Attempt 2 test already used the AST mechanism AT-M must reuse.
"""

import dataclasses
import inspect
import json
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
print("1. g2_rotation_ra3: how AT-A..AT-F must build a candidate")
from stockedge100.strategies import g2_rotation_ra3 as R

for name in sorted(n for n in dir(R) if not n.startswith("_")):
    obj = getattr(R, name)
    if inspect.isfunction(obj):
        print("   def   %-30s %s" % (name, inspect.signature(obj)))
    elif dataclasses.is_dataclass(obj):
        print("   dc    %-30s frozen=%s %s"
              % (name, obj.__dataclass_params__.frozen,
                 [f.name for f in dataclasses.fields(obj)]))
print()
show("build_candidate", inspect.getsource(R.build_candidate))
print()
print("   RotationCandidateRA3 __init__ / bases: %s"
      % [b.__name__ for b in R.RotationCandidateRA3.__bases__])
try:
    print("   RotationCandidateRA3 signature: %s" % inspect.signature(R.RotationCandidateRA3))
except Exception as exc:                                    # noqa: BLE001
    print("   RotationCandidateRA3 signature unavailable: %s" % exc)
print("   methods: %s" % [n for n in dir(R.RotationCandidateRA3) if not n.startswith("_")])

print()
print("=" * 100)
print("2. g2_runner_ra3: engine construction, labels, scenario helper, selection surface")
from stockedge100.strategies import g2_runner_ra3 as RUN

for name in sorted(n for n in dir(RUN) if not n.startswith("__")):
    obj = getattr(RUN, name)
    if inspect.isfunction(obj):
        print("   def   %-30s %s" % (name, inspect.signature(obj)))
    elif isinstance(obj, (str, int, tuple)) and not name.islower():
        print("   const %-30s %s" % (name, safe(repr(obj))[:100]))
print()
show("run_one", inspect.getsource(RUN.run_one))
print()
show("_assert_selection_surface", inspect.getsource(RUN._assert_selection_surface))
print()
show("selection_inputs", inspect.getsource(RUN.selection_inputs))
print()
show("verify_prior_attempt_modules", inspect.getsource(RUN.verify_prior_attempt_modules))

print()
print("=" * 100)
print("3. AT-H: where the seventeen digests live")
gov = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
seal = json.loads(gov.read_text("utf-8"))
for key in sorted(seal):
    value = seal[key]
    if isinstance(value, dict):
        inner = [k for k in value if "digest" in k or "module" in k]
        if inner:
            print("   seal[%r] -> subkeys with digest/module: %s" % (key, inner))
cfg = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
node = cfg["prior_attempt_modules_immutable"]
print("   config prior_attempt_modules_immutable keys: %s" % list(node))
print("   config module count: %d" % len(node.get("modules", [])))
for key in sorted(seal):
    value = seal[key]
    if isinstance(value, dict) and any(
        isinstance(v, dict) and v and all(isinstance(x, str) and len(x) == 64 for x in v.values())
        for v in value.values()
    ):
        for sub, v in value.items():
            if isinstance(v, dict) and v and all(len(x) == 64 for x in v.values() if isinstance(x, str)):
                print("   DIGEST MAP: seal[%r][%r] -> %d entries" % (key, sub, len(v)))
                for path in sorted(v)[:20]:
                    print("      %s" % path)

print()
print("=" * 100)
print("4. g2_selection_v2.check_seal_agreement and load_selection_rule")
from stockedge100.strategies import g2_selection_v2 as S

print("   check_seal_agreement() ->")
for k, v in S.check_seal_agreement().items():
    print("      %-34s %s" % (k, safe(json.dumps(v, ensure_ascii=False, default=str))[:170]))
print("   load_selection_rule() keys -> %s" % sorted(S.load_selection_rule()))
print()
show("dissimilarity", inspect.getsource(S.dissimilarity))
print()
show("select_representative_v2", inspect.getsource(S.select_representative_v2))

print()
print("=" * 100)
print("5. whichever existing test already uses attributes_derived_from_risk (AT-M's precedent)")
for path in sorted((ROOT / "tests").rglob("*.py")):
    text = path.read_text("utf-8")
    if "attributes_derived_from_risk" in text or "RISK_DERIVED_ATTRIBUTES" in text:
        print("   %s" % path.relative_to(ROOT))
        for m in re.finditer(r"^def (test_[A-Za-z_0-9]*)", text, re.M):
            if "derive" in m.group(1) or "risk" in m.group(1):
                print("      %s" % m.group(1))
        m = re.search(
            r"def test_[A-Za-z_0-9]*(?:derive|re_derive)[A-Za-z_0-9]*\(.*?(?=\n\ndef |\n\n@|\Z)",
            text, re.S)
        if m:
            show("precedent test", m.group(0))

print()
print("=" * 100)
print("6. counts: current suite size and the adversarial directory")
adv = sorted((ROOT / "tests/adversarial").glob("*.py"))
for path in adv:
    text = path.read_text("utf-8")
    print("   %-52s %4d lines %3d tests"
          % (path.name, text.count("\n"), len(re.findall(r"^def test_", text, re.M))))
