"""Enumerate the real shape of the Stage 3 G2 evidence file. ASCII only.

Written because a predicate guessed ``grid["size"]`` and raised KeyError. Locate evidence structures
by what they actually carry, not by a guess at their shape.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
EVIDENCE = ROOT / "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json"


def describe(value, depth: int = 0, name: str = "") -> None:
    pad = "  " * depth
    if isinstance(value, dict):
        print(f"{pad}{name} : dict({len(value)}) keys={list(value.keys())}")
        if depth < 1:
            for k, v in value.items():
                if isinstance(v, (dict, list)):
                    describe(v, depth + 1, k)
    elif isinstance(value, list):
        kind = type(value[0]).__name__ if value else "empty"
        print(f"{pad}{name} : list({len(value)}) of {kind}")
        if value and isinstance(value[0], dict):
            print(f"{pad}  element keys={list(value[0].keys())}")
    else:
        print(f"{pad}{name} : {type(value).__name__} = {value!r}")


def main() -> None:
    ev = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    print(f"top-level fields: {len(ev)}")
    for k, v in ev.items():
        describe(v, 0, k)


if __name__ == "__main__":
    main()
