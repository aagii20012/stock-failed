"""Pre-run the Attempt 3 sealer's seventeen-module immutability check.

The sealer will refuse if any prior-attempt module's digest on disk differs from the digest a prior
run record recorded for it.  A refusal is correct behaviour, but discovering it inside `build()`
means the diagnosis happens under a half-written seal.  Measure it here, where it costs nothing.

Stronger than the template's check in one way, deliberately: the digest is compared against EVERY
run record that names the module, not just one, so a module that changed between Attempt 1's run and
Attempt 2's run is visible as a disagreement between the records rather than hidden by whichever
record happened to be consulted.
"""

import hashlib
import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
P = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))

STAGES = ("STAGE_3_G2_ROTATION_DEVELOPMENT", "STAGE_3_G2_ATTEMPT_2_ROTATION_RA1_DEVELOPMENT")

records = {}
for path in sorted((ROOT / "runs").glob("*.json")):
    try:
        body = json.loads(path.read_text("utf-8"))
    except Exception:
        continue
    if body.get("stage") in STAGES:
        records.setdefault(body["stage"], []).append((path.name, body))

for stage in STAGES:
    got = records.get(stage, [])
    print("%-52s %d record(s) %s" % (stage, len(got), [n for n, _ in got]))
assert all(len(records.get(s, [])) == 1 for s in STAGES), "expected exactly one record per stage"

recorded = {}
for stage in STAGES:
    name, body = records[stage][0]
    for module, digest in (body.get("code_hashes") or {}).items():
        recorded.setdefault(module, {})[name] = digest

modules = (list(P["prior_attempt_modules_immutable"]["attempt_1_modules"])
           + list(P["prior_attempt_modules_immutable"]["attempt_2_modules"]))
print()
print("declared count: %d (config says %d)" % (len(modules), P["prior_attempt_modules_immutable"]["count"]))
print("duplicates: %s" % ([m for m in modules if modules.count(m) > 1] or "none"))

drift, unrecorded, disagree = [], [], []
for module in modules:
    path = ROOT / module
    if not path.exists():
        drift.append("%s: MISSING from disk" % module)
        continue
    measured = hashlib.sha256(path.read_bytes()).hexdigest()
    seen = recorded.get(module, {})
    if not seen:
        unrecorded.append(module)
        mark = "UNRECORDED"
    elif len(set(seen.values())) > 1:
        disagree.append("%s: records disagree %s" % (module, seen))
        mark = "RECORDS-DISAGREE"
    elif measured not in set(seen.values()):
        drift.append("%s: recorded %s, measured %s" % (module, sorted(set(seen.values()))[0], measured))
        mark = "DRIFT"
    else:
        mark = "ok in %d record(s)" % len(seen)
    print("  %-58s %s %s" % (module.replace("src/stockedge100/", ""), measured[:16], mark))

print()
print("drift:       %s" % (drift or "none"))
print("unrecorded:  %s" % (unrecorded or "none"))
print("disagree:    %s" % (disagree or "none"))

print()
print("-- pinned artifact digests in attempt_1_ref / attempt_2_ref " + "-" * 30)
bad = []
for ref in ("attempt_1_ref", "attempt_2_ref"):
    node = P[ref]
    n = 0
    for key, value in sorted(node.items()):
        if not key.endswith("_sha256") or not isinstance(value, str):
            continue
        relative = node.get(key[: -len("_sha256")])
        target = ROOT / relative
        if not target.exists():
            bad.append("%s.%s -> %s MISSING" % (ref, key, relative))
            continue
        got = hashlib.sha256(target.read_bytes()).hexdigest()
        n += 1
        if got != value:
            bad.append("%s.%s pinned %s measured %s" % (ref, key, value[:16], got[:16]))
    print("  %-16s %d pinned artifacts re-hashed" % (ref, n))

print()
print("-- top-level pinned digests " + "-" * 62)
TOP = {"constitution_md_sha256": "governance/STAGE_0_CONSTITUTION.md",
       "constitution_json_sha256": "governance/STAGE_0_CONSTITUTION.json",
       "charter_md_sha256": "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md",
       "partition_lock_md_sha256": "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md",
       "partition_lock_json_sha256": "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json",
       "cost_model_derivation_sha256": "config/generation_2/g2_cost_model.json"}
for key, relative in sorted(TOP.items()):
    target = ROOT / relative
    if not target.exists():
        bad.append("%s -> %s MISSING" % (key, relative))
        print("  %-34s MISSING %s" % (key, relative))
        continue
    got = hashlib.sha256(target.read_bytes()).hexdigest()
    ok = got == P[key]
    print("  %-34s %s %s" % (key, "OK  " if ok else "MISMATCH", relative))
    if not ok:
        bad.append("%s pinned %s measured %s" % (key, P[key][:16], got[:16]))

print()
print("=" * 90)
print("PROBLEMS: %s" % (bad or drift or unrecorded or disagree or "none"))
