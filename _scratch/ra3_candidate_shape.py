"""Sixteenth pass: the candidate_results[0] shape the gate_conditions() port depends on."""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


EV = json.loads(
    (ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
    .read_text(encoding="utf-8")
)

cand = EV["candidate_results"][0]
print("candidate_results len: %d" % len(EV["candidate_results"]))
print("candidate keys: %s" % safe(sorted(cand)))
print("-" * 100)
basis = cand["admission_basis"]
print("admission_basis keys: %s" % safe(sorted(basis)))
print(safe(json.dumps(basis, indent=1, default=str))[:3000])
print("-" * 100)
print("stress_evaluation keys: %s" % safe(sorted(cand["stress_evaluation"])))
print(safe(json.dumps({k: v for k, v in cand["stress_evaluation"].items()
                       if k != "conditions"}, indent=1, default=str))[:1800])
print("-" * 100)
for key in ("variant_id", "candidate_id", "strategy_id", "admitted", "verdict",
            "conditions_not_satisfied", "gate_verdict"):
    print("cand.%-30s %s" % (key, safe(json.dumps(cand.get(key, "<absent>"), default=str))[:200]))
print("-" * 100)
print("base row ids:   %s" % safe([r["id"] for r in cand["conditions"]]))
print("stress row ids: %s" % safe([r["id"] for r in cand["stress_evaluation"]["conditions"]]))
print("-" * 100)
print("EV.gate_scope:")
print(safe(json.dumps(EV["gate_scope"], indent=1, default=str))[:2200])
print("-" * 100)
print("EV.gate_evaluation_scope:")
print(safe(json.dumps(EV["gate_evaluation_scope"], indent=1, default=str))[:2200])
