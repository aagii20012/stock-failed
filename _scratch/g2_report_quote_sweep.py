"""Resolve every blockquote in the Stage 3 G2 report back to a sealed string on disk. ASCII only.

Written after the selection note was found to carry markdown backticks I had added inside a
quotation introduced as "verbatim". One instance of that defect implies the class must be swept, not
the instance patched: any block the report presents as a quotation should be byte-identical to
something sealed.

Blocks that are the report's own commentary rather than a quotation are reported as such and are not
failures -- but they are listed, so "unresolved" is a decision rather than an omission.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
REPORT = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md"

SOURCES = [
    "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json",
    "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json",
    "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md",
    "config/generation_2/g2_rotation_protocol.json",
    "config/generation_2/g2_gate_criteria.json",
    "config/generation_2/g2_cost_model.json",
    "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json",
    "governance/STAGE_0_CONSTITUTION.json",
    "governance/STAGE_0_CONSTITUTION.md",
]


def ascii_(s: str) -> str:
    return s.encode("ascii", "backslashreplace").decode("ascii")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def walk_strings(node, path: str, out: list[tuple[str, str]]) -> None:
    if isinstance(node, str):
        if len(node) >= 40:
            out.append((path, node))
    elif isinstance(node, dict):
        for k, v in node.items():
            walk_strings(v, f"{path}.{k}" if path else k, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_strings(v, f"{path}[{i}]", out)


def load_sealed() -> list[tuple[str, str, str]]:
    """(file, json pointer-ish path, string value) for every sealed string worth matching."""
    sealed: list[tuple[str, str, str]] = []
    for rel in SOURCES:
        path = ROOT / rel
        if not path.exists():
            print(f"   (missing source, skipped: {rel})")
            continue
        if path.suffix == ".json":
            found: list[tuple[str, str]] = []
            walk_strings(json.loads(path.read_text(encoding="utf-8")), "", found)
            sealed.extend((rel, p, v) for p, v in found)
        else:
            text = path.read_text(encoding="utf-8")
            for para in re.split(r"\n\s*\n", text):
                if len(para.strip()) >= 40:
                    sealed.append((rel, "<paragraph>", para.strip()))
    return sealed


def main() -> int:
    text = REPORT.read_text(encoding="utf-8")
    print("loading sealed strings...")
    sealed = load_sealed()
    exact = {v: (f, p) for f, p, v in sealed}
    normalised = {norm(v): (f, p) for f, p, v in sealed}
    print(f"sealed strings available: {len(sealed)}")
    print()

    blocks = [m.group(0) for m in re.finditer(r"(?:^> ?.*\n)+", text, re.MULTILINE)]
    print(f"blockquote blocks in report: {len(blocks)}")
    print()

    unresolved = 0
    for i, raw in enumerate(blocks, 1):
        body = "\n".join(line[2:] if line.startswith("> ") else line[1:]
                         for line in raw.rstrip("\n").split("\n"))
        one_line = norm(body)
        head = ascii_(one_line[:72])
        if body in exact:
            f, p = exact[body]
            print(f"{i:2d}. EXACT     {len(body):4d}ch  {f} :: {p}")
        elif one_line in normalised:
            f, p = normalised[one_line]
            print(f"{i:2d}. REWRAPPED {len(body):4d}ch  {f} :: {p}")
            print(f"       (matches only after whitespace normalisation)")
        else:
            unresolved += 1
            print(f"{i:2d}. OWN TEXT  {len(body):4d}ch  \"{head}...\"")

    print()
    print(f"exact-or-rewrapped quotations: {len(blocks) - unresolved}")
    print(f"report's own prose blocks    : {unresolved}")
    print()
    print("Note: 'OWN TEXT' is only a defect if the surrounding sentence calls it a quotation.")
    print("Grep the introducing line for each before concluding.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
