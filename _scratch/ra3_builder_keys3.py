"""Ninth pass: the last gaps before g2_stage3_attempt3_package.py can be written.

Specifically: the disclosure carriage nodes on both sides, which carriers currently carry the
1507-char text byte-exact and which need prose normalisation, the full stage_verdict, the
criteria condition rows as the gate_conditions() function will read them, and the four .sha256
records the guard chain re-verifies.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.reporting.g2_partition_lock import normalised_prose  # noqa: E402
from stockedge100.reporting.stage_package import verify_sha256_record  # noqa: E402


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def dump(label, node, limit=2600):
    print("=" * 100)
    print(label)
    print(safe(json.dumps(node, indent=1, default=str))[:limit])


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


EV = load("reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
PROT = load("config/generation_2/g2_rotation_ra3_protocol.json")
CRIT = load("config/generation_2/g2_gate_criteria_ra3.json")

dump("PROT.adaptation_disclosure_carriage_requirement",
     PROT["adaptation_disclosure_carriage_requirement"], 3000)
dump("EV.adaptation_disclosure_carriage", EV["adaptation_disclosure_carriage"], 3000)

sealed = PROT["adaptation_disclosure_verbatim"]
print("=" * 100)
print("sealed disclosure: chars=%d" % len(sealed))
import hashlib  # noqa: E402
print("sealed disclosure: sha256=%s" % hashlib.sha256(sealed.encode("utf-8")).hexdigest())

print("=" * 100)
print("carrier state right now:")
for rel in PROT["adaptation_disclosure_carriage_requirement"]["must_appear_verbatim_in"]:
    path = ROOT / rel
    if not path.is_file():
        print("   %-72s MISSING" % rel)
        continue
    text = path.read_text(encoding="utf-8")
    byte_exact = sealed in text
    if rel.endswith(".json"):
        embedded = json.dumps(json.loads(text), ensure_ascii=False)
        verbatim = json.dumps(sealed, ensure_ascii=False)[1:-1] in embedded or byte_exact
    else:
        verbatim = normalised_prose(sealed) in normalised_prose(text)
    print("   %-72s byte_exact=%-5s verbatim=%s" % (rel, byte_exact, verbatim))

dump("EV.stage_verdict", EV["stage_verdict"], 3600)
dump("EV.refs_reverified", EV["refs_reverified"], 2200)
dump("EV.selection_determinism", EV["selection_determinism"], 2000)
dump("EV.selection.steps", EV["selection"]["steps"], 2400)
dump("EV.selection.selection_input_fields + scored_quantities",
     {k: EV["selection"][k] for k in ("selection_input_fields", "scored_quantities")}, 900)

print("=" * 100)
print("CRIT.conditions as gate_conditions() reads them:")
for cond in CRIT["conditions"]:
    print("   id=%s" % cond["id"])
    print("      required_verbatim: %s" % safe(cond["required_verbatim"])[:150])
    print("      predicate        : %s" % safe(cond.get("predicate", cond.get("threshold")))[:150])

print("=" * 100)
print("candidate_results[0] scalars:")
c = EV["candidate_results"][0]
for k in ("variant_id", "experiment_id", "admitted", "scenario", "family",
          "conditions_met", "conditions_not_met", "conditions_not_applicable",
          "conditions_not_evaluable"):
    print("   %-28s %s" % (k, safe(json.dumps(c[k], default=str))[:200]))
print("   stress_evaluation keys: %s" % sorted(c["stress_evaluation"]))
print("   non_vacuity_check: %s" % safe(json.dumps(c["non_vacuity_check"], default=str))[:400])

print("=" * 100)
print("sha256 record re-verification:")
for rel in ("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.sha256",
            "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256",
            "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.sha256",
            "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256"):
    try:
        res = verify_sha256_record(ROOT / rel, ROOT)
        print("   %-60s %s" % (rel, sorted(set(res.values()))))
        for p, s in sorted(res.items()):
            if s != "OK":
                print("        %s -> %s" % (p, s))
    except Exception as exc:  # noqa: BLE001
        print("   %-60s RAISED %s: %s" % (rel, type(exc).__name__, safe(exc)))

print("=" * 100)
print("evidence digest recomputation:")
excluded = ("generated_utc", "evidence_digest")
covered = {k: v for k, v in EV.items() if k not in excluded}
blob = json.dumps(covered, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
print("   recomputed = %s" % hashlib.sha256(blob.encode("utf-8")).hexdigest())
print("   recorded   = %s" % EV["evidence_digest"])
print("   covers     = %s" % safe(json.dumps(EV["evidence_digest_covers"], default=str))[:400])
print("   command    = %s" % safe(EV["command"]))
