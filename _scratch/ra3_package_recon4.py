"""Fourth reconnaissance pass: the RA3 protocol config the builder reads for its body/limitations,
and the exact evidence nodes the Attempt 2 template pulls from its own protocol.

Every key the Attempt 3 builder will touch is printed here from disk, so the module is written
against measured structure. Nothing is inferred from Attempt 2's spellings.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def keys(label, node):
    print("-- %s" % label)
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, dict):
                print("   %-46s dict[%d] %s" % (key, len(value), sorted(value))[:400])
            elif isinstance(value, list):
                print("   %-46s list[%d] %s"
                      % (key, len(value), safe(json.dumps(value, default=str))[:200]))
            else:
                print("   %-46s %s" % (key, safe(repr(value))[:200]))
    else:
        print("   %s" % safe(json.dumps(node, default=str))[:400])


PROT = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json")
                  .read_text(encoding="utf-8"))

print("=" * 100)
print("PROTOCOL top-level keys (%d):" % len(PROT))
for key, value in PROT.items():
    kind = ("dict[%d]" % len(value) if isinstance(value, dict)
            else "list[%d]" % len(value) if isinstance(value, list) else type(value).__name__)
    print("   %-52s %s" % (key, kind))

for name in ("adaptation_disclosure_carriage_requirement", "runs_per_variant", "run_span",
             "eligible_universe", "attempt_1_ref", "attempt_2_ref", "multiple_comparisons_disclosure",
             "risk_architecture", "selection_rule", "structural_consequences_declared_before_running"):
    print("=" * 100)
    keys("PROTOCOL.%s" % name, PROT.get(name, "<ABSENT>"))

print("=" * 100)
print("PROTOCOL scalars:")
for key in sorted(PROT):
    if not isinstance(PROT[key], (dict, list)):
        print("   %-52s = %s" % (key, safe(repr(PROT[key]))[:180]))

print("=" * 100)
print("PROTOCOL.explicit_non_authorizations:")
for item in PROT.get("explicit_non_authorizations", []):
    print("   - %s" % safe(item)[:160])

EV = json.loads((ROOT / "reports/stage3_g2_attempt3/"
                 "STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))

for name in ("gate_scope", "attempt_1_ref", "attempt_2_ref", "refs_reverified",
             "prior_attempt_module_verification", "ladder_engagement_comparison",
             "adaptation_disclosure_carriage", "risk_architecture", "sealed_inputs",
             "window", "grid", "selection_determinism", "run_span_recheck"):
    print("=" * 100)
    node = EV.get(name, "<ABSENT>")
    if isinstance(node, dict):
        node = {k: ("<elided %d>" % len(v) if k in ("modules_verified", "per_run", "inputs")
                    else v) for k, v in node.items()}
    keys("EVIDENCE.%s" % name, node)

print("=" * 100)
print("EVIDENCE.selection (short):")
sel = EV["selection"]
for key, value in sel.items():
    if key in ("inputs", "neighbour_scores"):
        print("   %-38s <elided, %d entries>" % (key, len(value)))
    else:
        print("   %-38s %s" % (key, safe(json.dumps(value, default=str))[:400]))
