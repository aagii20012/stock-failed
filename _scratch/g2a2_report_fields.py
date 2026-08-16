"""Resolve every non-table placeholder the report template needs, before wiring the renderer.

The template quotes digests, dates, counts and sealed prose. CLAUDE.md forbids hand-typing any of
them, so each must resolve to a real key path on disk first. This prints the resolved value for each
and names the ones that do not resolve, rather than raising on the first. ASCII output only; long
sealed prose is measured, not printed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
MISSING = object()


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


protocol = load("config/generation_2/g2_rotation_ra1_protocol.json")
ev = load("reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json")

problems = []


def probe(label, obj, *path):
    cur = obj
    for key in path:
        cur = cur.get(key, MISSING) if isinstance(cur, dict) else MISSING
        if cur is MISSING:
            break
    trail = "%s[%s]" % (label, "][".join(repr(p) for p in path))
    if cur is MISSING:
        problems.append(trail)
        print("  MISSING  %s" % trail)
        return MISSING
    if isinstance(cur, (dict, list)):
        shown = "%s(%d) %s" % (type(cur).__name__, len(cur),
                               sorted(cur) if isinstance(cur, dict) else "")
    else:
        shown = str(cur).replace("\n", " ")
        shown = ("%s ... [%d chars]" % (shown[:90], len(str(cur)))) if len(shown) > 90 else shown
    print("  ok       %-62s %s" % (trail, shown.encode("ascii", "backslashreplace").decode("ascii")))
    return cur


print("== identity ==")
probe("protocol", protocol, "generation_id")
probe("protocol", protocol, "strategy_id")
probe("ev", ev, "generation_id")
probe("ev", ev, "strategy_id")

print()
print("== sealed prose ==")
probe("protocol", protocol, "what_this_attempt_adds_over_attempt_1")
probe("protocol", protocol, "declared_before_any_strategy_code")
probe("protocol", protocol, "declared_before_any_strategy_code_measurement")
probe("ev", ev, "sealed_inputs", "declared_before_any_strategy_code")
probe("ev", ev, "sealed_inputs", "declared_before_any_strategy_code_measurement")

print()
print("== sealed digests (evidence sealed_inputs) ==")
for key in ("protocol_sha256", "criteria_sha256", "governance_protocol_md_sha256",
            "governance_protocol_json_sha256", "cost_model_sha256", "partition_lock_sha256",
            "charter_sha256", "protocol", "criteria", "governance_protocol_md",
            "governance_protocol_json", "cost_model", "partition_lock", "charter"):
    probe("ev", ev, "sealed_inputs", key)

print()
print("== window ==")
for key in ("development_bound", "run_start", "run_end", "sessions", "latest_session_loaded",
            "start", "end", "binding_symbol"):
    probe("ev", ev, "window", key)

print()
print("== universe ==")
print("  universe keys:", sorted(ev.get("universe", {})))
for key in ("universe_version", "identity_sha256", "identity", "universe_identity_sha256",
            "declared_members", "loaded_members", "unchanged_from_attempt_1"):
    probe("ev", ev, "universe", key)

print()
print("== selection / evidence provenance ==")
probe("ev", ev, "selection", "representative_variant_id")
probe("ev", ev, "generated_utc")
probe("ev", ev, "evidence_digest")
probe("ev", ev, "artifact_id")
p = ROOT / "reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json"
print("  evidence bytes  %d" % p.stat().st_size)
print("  evidence sha256 %s" % hashlib.sha256(p.read_bytes()).hexdigest())

print()
print("== seal run record ==")
seal = None
for path in sorted((ROOT / "runs").glob("SE100-R-*.json")):
    rec = json.loads(path.read_text(encoding="utf-8"))
    if "attempt_2_preregistration" in str(rec.get("stage", "")):
        seal = (path, rec)
print("  file:", seal[0].name if seal else "NOT FOUND")
if seal is None:
    problems.append("seal run record")
else:
    for key in ("run_id", "timestamp_utc", "repo_state_id", "stage"):
        probe("seal", seal[1], key)

print()
print("== file digests recomputed from disk ==")
for rel in ("governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md",
            "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json",
            "config/generation_2/g2_rotation_ra1_protocol.json",
            "config/generation_2/g2_gate_criteria_ra1.json",
            "config/generation_2/g2_cost_model.json",
            "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json",
            "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md"):
    f = ROOT / rel
    print("  %-46s %s" % (rel.split("/")[-1],
                          hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else "NO SUCH FILE"))
    if not f.exists():
        problems.append(rel)

print()
print(("PROBLEMS (%d): %s" % (len(problems), problems)) if problems else "OK: everything resolved")
