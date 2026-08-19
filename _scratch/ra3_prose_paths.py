"""Dump every string-valued path in the Attempt 3 protocol config and the partition lock.

The report template carries 62 bare ``@@NAME@@`` tokens whose values are sealed prose. Each must be
resolved to a dotted path that exists, not to a paraphrase. This prints the whole tree so the
renderer's PROSE map can be written against measured paths rather than guessed ones.

ASCII only: values are backslash-escaped before printing, because the console is cp1252 and the
sealed disclosure contains U+2212.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "stockedge100"


def ascii_(text: str) -> str:
    return str(text).encode("ascii", "backslashreplace").decode("ascii")


def walk(node, prefix=""):
    if isinstance(node, dict):
        for key, value in node.items():
            walk(value, f"{prefix}.{key}" if prefix else key)
    elif isinstance(node, list):
        if node and all(isinstance(x, str) for x in node):
            print("  %-72s list[str] %d  %s" % (prefix, len(node), ascii_(node[0])[:60]))
        else:
            for i, value in enumerate(node):
                walk(value, f"{prefix}[{i}]")
    elif isinstance(node, str):
        print("  %-72s str %5d  %s" % (prefix, len(node), ascii_(node)[:90]))
    else:
        print("  %-72s %s  %s" % (prefix, type(node).__name__, ascii_(node)[:40]))


which = sys.argv[1]
paths = {
    "protocol": "config/generation_2/g2_rotation_ra3_protocol.json",
    "criteria": "config/generation_2/g2_gate_criteria_ra3.json",
    "lock": "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json",
}
rel = paths[which]
print("=== %s ===" % rel)
walk(json.loads((ROOT / rel).read_text(encoding="utf-8")))
