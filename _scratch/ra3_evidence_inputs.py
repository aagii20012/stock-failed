"""Everything g2_stage3_attempt3_evidence.py must read, dumped before a line of it is written.

Attempt 2's evidence module subscripts CFG-3103 in twenty-odd places and calls seven functions on
`g2_gate_ra1` / `g2_runner_ra1`. CFG-3105 renamed sections already (`attempt_1_modules_immutable` ->
`prior_attempt_modules_immutable`, the three-step rule -> SEL-2), and `select_representative_ra3`
takes runs where Attempt 2's took projected inputs. A KeyError discovered after seventy-two backtests
-- the grid plus the determinism replay -- would cost the whole session.

Also resolves which report artifacts belong to the evidence module and which to the package builder,
because Attempt 2's report directory holds thirteen files and this module writes one of them.
"""

import inspect
import json
import pathlib
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
P2 = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text("utf-8"))
C3 = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def wrap(text, indent=6, width=112):
    text = safe(text)
    while text:
        print("%s%s" % (" " * indent, text[:width]))
        text = text[width:]


print("=" * 100)
print("1. every key Attempt 2's evidence module subscripts on its protocol -- present in CFG-3105?")
SUBSCRIPTED = [
    "generation_id", "attempt", "strategy_id", "candidate_index", "family", "hypothesis",
    "what_this_attempt_adds_over_attempt_1", "adaptation_disclosure_verbatim",
    "adaptation_disclosure_carriage_requirement", "attempt_1_ref", "declared_before_any_strategy_code",
    "declared_before_any_strategy_code_measurement", "run_span", "eligible_universe",
    "risk_architecture", "grid", "runs_per_variant", "reproducibility_requirements",
    "reported_for_every_variant_but_not_gating", "multiple_comparisons_disclosure",
    "representative_selection_rule", "gate_evaluation_scope",
    "structural_consequences_declared_before_running", "explicit_non_authorizations",
]
for key in SUBSCRIPTED:
    print("   %-52s RA3=%-5s Att2=%s" % (key, key in P3, key in P2))
print()
print("   only-RA3 top-level : %s" % sorted(set(P3) - set(P2)))
print("   only-Att2 top-level: %s" % sorted(set(P2) - set(P3)))

print()
print("=" * 100)
print("2. adaptation_disclosure_carriage_requirement.must_appear_verbatim_in")
req = P3["adaptation_disclosure_carriage_requirement"]
print("   keys: %s" % list(req))
for path in req["must_appear_verbatim_in"]:
    print("      %s" % path)
print("   enforcement:")
wrap(req["enforcement"])
print("   encoding_note:")
wrap(req.get("encoding_note", "<absent>"))
text = P3["adaptation_disclosure_verbatim"]
import hashlib
print("   disclosure chars=%d sha256=%s" % (len(text), hashlib.sha256(text.encode("utf-8")).hexdigest()))

print()
print("=" * 100)
print("3. reported_for_every_variant_but_not_gating -- how many, and what")
node = P3.get("reported_for_every_variant_but_not_gating")
if node is None:
    print("   *** ABSENT -- look for a renamed section ***")
    for key in sorted(P3):
        if "report" in key:
            print("   candidate: %s" % key)
else:
    print("   count=%d" % len(node))
    for i, item in enumerate(node):
        print("   [%2d] %s" % (i, safe(json.dumps(item, ensure_ascii=False))[:130]))

print()
print("=" * 100)
print("4. reproducibility_requirements")
node = P3["reproducibility_requirements"]
for key, value in node.items():
    print("   %s:" % key)
    wrap(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)

print()
print("=" * 100)
print("5. attempt lineage keys")
for key in sorted(P3):
    if "attempt" in key and key not in ("prior_attempt_modules_immutable",):
        value = P3[key]
        if isinstance(value, str):
            print("   %s:" % key)
            wrap(value)
        else:
            print("   %-46s %s" % (key, safe(json.dumps(value, ensure_ascii=False))[:110]))

print()
print("=" * 100)
print("6. g2_gate_ra3 public surface")
from stockedge100.strategies import g2_gate_ra3 as G
print("   __all__ %s" % getattr(G, "__all__", None))
for name in sorted(n for n in dir(G) if not n.startswith("_")):
    obj = getattr(G, name)
    if callable(obj):
        try:
            print("   %-38s %s" % (name, inspect.signature(obj)))
        except Exception:
            print("   %-38s <class>" % name)

print()
print("=" * 100)
print("7. g2_runner_ra3 selection + gate entry points")
from stockedge100.strategies import g2_runner_ra3 as RUN
for name in ("selection_inputs", "select_representative_ra3", "gate_inputs", "run_grid",
             "grid_report", "ladder_engagement_comparison", "verify_prior_attempt_modules",
             "recheck_run_span", "write_run_span_recheck", "attempt_2_counterparts"):
    print("   %-34s %s" % (name, inspect.signature(getattr(RUN, name))))

print()
print("=" * 100)
print("8. which module writes the other twelve files in reports/stage3_g2_attempt2/")
pkg = ROOT / "src/stockedge100/reporting/g2_stage3_attempt2_package.py"
srctext = pkg.read_text("utf-8")
import re
for m in re.finditer(r'"([A-Za-z0-9_./]+\.(?:json|md|txt|sha256))"', srctext):
    print("   pkg literal: %s" % m.group(1))
print("   --- package module public functions ---")
for m in re.finditer(r"^def ([a-z_0-9]+)\((.*)$", srctext, re.M):
    print("   def %s(%s" % (m.group(1), m.group(2)[:90]))

print()
print("=" * 100)
print("9. existing SE100-EVID ids on disk")
import subprocess
for base in ("config", "governance", "src", "reports"):
    for path in sorted((ROOT / base).rglob("*")):
        if path.is_file() and path.suffix in (".json", ".py", ".md"):
            try:
                blob = path.read_text("utf-8", errors="ignore")
            except Exception:
                continue
            for m in set(re.findall(r"SE100-EVID-\d+", blob)):
                print("   %-14s %s" % (m, path.relative_to(ROOT)))
