"""Key paths only (no values) for CFG-3105 and CFG-3106, so the Markdown
generator can be written against real key names rather than remembered ones."""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")


def walk(node, prefix="", depth=0, maxdepth=3):
    lines = []
    if isinstance(node, dict):
        for k, v in node.items():
            path = "%s.%s" % (prefix, k) if prefix else k
            if isinstance(v, dict):
                lines.append("%s  {%d}" % (path, len(v)))
                if depth < maxdepth:
                    lines.extend(walk(v, path, depth + 1, maxdepth))
            elif isinstance(v, list):
                kinds = sorted({type(x).__name__ for x in v})
                lines.append("%s  [%d] of %s" % (path, len(v), ",".join(kinds)))
                if v and isinstance(v[0], dict) and depth < maxdepth:
                    lines.append("%s[*] keys: %s" % (path, list(v[0].keys())))
            else:
                lines.append("%s  <%s>" % (path, type(v).__name__))
    return lines


for name in ("g2_rotation_ra3_protocol.json", "g2_gate_criteria_ra3.json"):
    obj = json.loads((ROOT / "config/generation_2" / name).read_text(encoding="utf-8"))
    print("=" * 78)
    print("### %s" % name)
    print("=" * 78)
    for line in walk(obj):
        print(line)
    print()
