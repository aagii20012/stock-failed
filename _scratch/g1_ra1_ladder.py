"""Locate Generation 1's sealed RA1-5 de-risk ladder inside its own protocol
config, so the Attempt 3 Markdown's provenance table quotes the file rather than
restating a value from memory.  Also dumps the RA3-4 scalar-level fields and the
risk_architecture top-level scalars the generator needs verbatim."""

import hashlib
import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
G1 = ROOT / "config/stage3_attempt2_strategy_protocol.json"
PROTO = ROOT / "config/generation_2/g2_rotation_ra3_protocol.json"


def a(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False).encode(
        "ascii", "backslashreplace").decode("ascii")


print("g1 path exists   : %s" % G1.exists())
raw = G1.read_bytes()
print("g1 sha256        : %s" % hashlib.sha256(raw).hexdigest())
print("g1 expected      : 77f1451c20e37640bd2843ff86d69eb54cbc0ebb592a696972fbdea6e05b5433")
g1 = json.loads(raw.decode("utf-8"))

print("\n--- g1 top-level keys (%d)" % len(g1))
for k in g1:
    print("   %s" % k)


def find(node, path=""):
    """Every path whose key or string value mentions RA1-5 or a ladder."""
    hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = "%s.%s" % (path, k) if path else k
            if "RA1-5" in str(k) or "ladder" in str(k).lower():
                hits.append((p, v))
            hits.extend(find(v, p))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits.extend(find(v, "%s[%d]" % (path, i)))
    return hits


print("\n--- ladder / RA1-5 key hits in the Generation 1 config")
for p, v in find(g1):
    print("\n===== %s" % p)
    print(a(v))

proto = json.loads(PROTO.read_text(encoding="utf-8"))
ra = proto["risk_architecture"]
print("\n\n--- risk_architecture scalar fields")
for k, v in ra.items():
    if k in ("components", "combined_scalar", "state_ownership"):
        continue
    print("   %-34s %s" % (k, a(v)))

print("\n--- risk_architecture.combined_scalar")
print(a(ra["combined_scalar"]))
print("\n--- risk_architecture.state_ownership")
print(a(ra["state_ownership"]))

print("\n--- RA3-4 scalar fields")
for k, v in ra["components"]["RA3-4"].items():
    if k in ("bands", "provenance", "relationship_to_the_shutdown_threshold"):
        continue
    print("   %-34s %s" % (k, a(v)))
