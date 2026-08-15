"""Enumerate the built Stage 3 G2 package's real shape before writing predicates against it.

ASCII only. The Stage 4 verifier's own comments record that guessing where the shared builder puts a
field produced confident FAIL lines about a package that was fine.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
DEC = ROOT / "reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json"
MAN = ROOT / "reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json"


def show(s) -> str:
    return str(s).encode("ascii", "backslashreplace").decode("ascii")


def outline(node, name: str, depth: int = 0, maxdepth: int = 2) -> None:
    pad = "  " * depth
    if isinstance(node, dict):
        print(f"{pad}{name}: dict({len(node)}) {show(list(node.keys()))}")
        if depth < maxdepth:
            for k, v in node.items():
                if isinstance(v, (dict, list)):
                    outline(v, k, depth + 1, maxdepth)
    elif isinstance(node, list):
        kind = type(node[0]).__name__ if node else "empty"
        print(f"{pad}{name}: list({len(node)}) of {kind}")
        if node and isinstance(node[0], dict) and depth < maxdepth:
            print(f"{pad}  element keys: {show(list(node[0].keys()))}")
    else:
        print(f"{pad}{name}: {type(node).__name__} = {show(node)[:110]}")


def main() -> None:
    dec = json.loads(DEC.read_text(encoding="utf-8"))
    man = json.loads(MAN.read_text(encoding="utf-8"))

    print("=========== DECISION RECORD ===========")
    outline(dec, "<root>", 0, 1)

    print()
    print("=========== gate_conditions ===========")
    for k, v in dec.get("gate_conditions", {}).items():
        vd = v.get("verdict") if isinstance(v, dict) else v
        print(f"   {k:44s} {show(vd)}")

    print()
    print("=========== reproducibility ===========")
    for k, v in dec.get("reproducibility", {}).items():
        print(f"   {k:34s} {show(v)[:90]}")

    print()
    print("=========== MANIFEST ===========")
    outline(man, "<root>", 0, 1)

    run_id = dec["reproducibility"]["run_id"]
    run = json.loads((ROOT / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))
    print()
    print("=========== RUN RECORD ===========")
    outline(run, "<root>", 0, 1)


if __name__ == "__main__":
    main()
