"""Independently recompute the Attempt 2 evidence self-digest from the file on disk.

This deliberately does NOT import the evidence module. It reads the written JSON, follows the
file's own ``evidence_digest_covers`` sentence literally, and recomputes the digest with a local
canonical-JSON implementation. If this agreed with the writer only because it called the writer's
function, it would prove nothing.

ASCII output only (cp1252 console).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
EVIDENCE = ROOT / "reports" / "stage3_g2_attempt2" / "STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json"

raw = EVIDENCE.read_bytes()
body = json.loads(raw.decode("utf-8"))

print("file            reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json")
print("bytes           %d" % len(raw))
print("file sha256     %s" % hashlib.sha256(raw).hexdigest())
print("covers          %s" % body["evidence_digest_covers"])
print("recorded digest %s" % body["evidence_digest"])

# "every field of this file except generated_utc and evidence_digest, as canonical JSON"
covered = {k: v for k, v in body.items() if k not in ("generated_utc", "evidence_digest")}
payload = json.dumps(covered, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
print("recomputed      %s" % recomputed)
print("fields covered  %d of %d top-level" % (len(covered), len(body)))

assert recomputed == body["evidence_digest"], "EVIDENCE DIGEST MISMATCH: %s" % recomputed

# The two excluded fields must actually be excluded, not merely absent from the copy: removing a
# third field must change the digest, or the coverage sentence would be understating what it covers.
probe = dict(covered)
probe.pop("stage_verdict")
probe_digest = hashlib.sha256(
    json.dumps(probe, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
).hexdigest()
assert probe_digest != recomputed, "digest is insensitive to stage_verdict"
print("sensitivity     dropping stage_verdict changes the digest -> coverage is real")

print()
print("== findings the package builder will index ==")
sv = body["stage_verdict"]
print("  verdict            %s" % sv["verdict"])
print("  verdict_token      %s" % sv["verdict_token"])
print("  route              %s" % sv["route"])
print("  representative     %s" % sv["representative_exists"])
print("  candidates_eval    %s" % sv.get("candidates_evaluated"))
print("  admitted           %s" % sv.get("admitted_candidates"))
print("  determinism        %s (%d runs)" % (
    body["determinism"]["all_identical"], body["determinism"]["runs_compared"]))
print("  runs_executed      %s" % body["grid"]["runs_executed"])
print("  window latest      %s (bound %s)" % (
    body["window"]["latest_session_loaded"], body["window"]["development_bound"]))
print("  validation_read    %s" % body["window"]["validation_read"])
print("  g1 holdout read    %s" % body["window"]["generation_1_holdout_read"])
print("  g2 holdout read    %s" % body["window"]["generation_2_holdout_read"])
print("  disclosure chars   %s  sha256 %s" % (
    body["adaptation_disclosure_carriage"]["characters"],
    body["adaptation_disclosure_carriage"]["sha256_of_utf8"]))
print("  attempt1 modules   %s" % body["attempt_1_module_verification"].get("modules_verified"))
print("  attempt1 moved     %s" % body["attempt_1_module_verification"].get("moved"))

print()
print("== top-level keys, in emission order ==")
for i, key in enumerate(body):
    print("  %2d %s" % (i, key))

print()
print("OK: evidence digest reproduced independently")
