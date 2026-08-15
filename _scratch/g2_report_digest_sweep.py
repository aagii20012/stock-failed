"""Resolve every 64-hex string in the new Stage 3 G2 report and in README.md back to disk.

ASCII output only. A bare count proves nothing: what is forbidden is a *tree* digest (``repo_state_id``)
or the file's *own* digest, not any digest at all. So each hit is resolved to the artifact it belongs
to, and the two forbidden classes are checked explicitly.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
REPORT = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md"
README = ROOT / "README.md"
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def known_digests() -> dict[str, str]:
    """Every digest we can resolve, mapped digest -> what it is."""
    out: dict[str, str] = {}

    universe = json.loads((ROOT / "config/generation_2/g2_rotation_protocol.json").read_text(
        encoding="utf-8"))["eligible_universe"]
    for key, value in universe.items():
        if isinstance(value, str) and HEX64.fullmatch(value):
            out[value] = f"protocol eligible_universe.{key}"

    evidence_path = ROOT / "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    out[evidence["evidence_digest"]] = "evidence file self-digest (evidence_digest)"

    for rel in ("governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md",
                "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md",
                "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json",
                "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.md",
                "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json",
                "config/generation_2/g2_rotation_protocol.json",
                "config/generation_2/g2_gate_criteria.json",
                "config/generation_2/g2_cost_model.json",
                "governance/STAGE_0_CONSTITUTION.md",
                "governance/STAGE_0_CONSTITUTION.json"):
        out.setdefault(sha256_file(ROOT / rel), f"file digest of {rel}")

    return out


def sweep(path: Path, table: dict[str, str]) -> bool:
    text = path.read_text(encoding="utf-8")
    hits = sorted(set(HEX64.findall(text)))
    own = sha256_file(path)
    print(f"== {path.relative_to(ROOT)} ==")
    print(f"   bytes {path.stat().st_size}, 64-hex hits {len(hits)}")
    ok = True
    for h in hits:
        what = table.get(h, "*** UNRESOLVED ***")
        flag = "OK  "
        if h == own:
            what, flag, ok = "*** THIS FILE'S OWN DIGEST ***", "FAIL", False
        elif h not in table:
            ok = False
            flag = "FAIL"
        print(f"   {flag} {h[:16]}... {what}")
    print(f"   own digest appears in own text: {own in text}")
    print(f"   literal 'repo_state_id' value pattern: none expected; field name mentions "
          f"{text.count('repo_state_id')}")
    return ok


def main() -> int:
    table = known_digests()
    print(f"resolvable digests known: {len(table)}")
    print()
    ok_report = sweep(REPORT, table)
    print()
    ok_readme = sweep(README, table)
    print()
    print("RESULT " + ("OK" if ok_report and ok_readme else "FAILED"))
    return 0 if (ok_report and ok_readme) else 1


if __name__ == "__main__":
    sys.exit(main())
