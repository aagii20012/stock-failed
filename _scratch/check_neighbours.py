"""Compute the SE100-G2-SEL-2 neighbour partition over the 18-variant grid from the sealed
Attempt 2 grid block, rather than asserting it by hand."""

import collections
import json
import pathlib

d = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra1_protocol.json").read_text(encoding="utf-8")
)
g = d["grid"]
print("axes:", json.dumps(g["axes"]))

vs = g["variants"]
LB = [3, 6, 12]
K = [1, 2, 3]
FREQ = ["MONTHLY", "QUARTERLY"]


def key(v):
    return (v["lookback_months"], v["top_k"], v["rebalance_frequency"])


index = {key(v): v for v in vs}
assert len(index) == 18


def neighbours(v):
    lb, k, f = key(v)
    out = []
    i = LB.index(lb)
    for j in (i - 1, i + 1):
        if 0 <= j < len(LB):
            out.append((LB[j], k, f))
    i = K.index(k)
    for j in (i - 1, i + 1):
        if 0 <= j < len(K):
            out.append((lb, K[j], f))
    out.append((lb, k, FREQ[1 - FREQ.index(f)]))
    return out


counts = collections.Counter()
nb = {}
for v in vs:
    n = neighbours(v)
    assert len(set(n)) == len(n)
    for t in n:
        assert t in index, t
    nb[key(v)] = set(n)
    counts[len(n)] += 1

print("partition (n_neighbours -> n_variants):", dict(sorted(counts.items())))
print("total variants:", sum(counts.values()))

# symmetry
for a, ns in nb.items():
    for b in ns:
        assert a in nb[b], (a, b)
print("symmetry: OK")

# hand-verifiable examples, one of each class
for want in (3, 4, 5):
    for v in vs:
        if len(nb[key(v)]) == want:
            print("\n%d-neighbour example: %s" % (want, v["variant_id"]))
            for t in sorted(nb[key(v)]):
                print("   ", index[t]["variant_id"])
            break

# edge classes spelled out
ends_lb = [v for v in vs if v["lookback_months"] in (3, 12)]
ends_k = [v for v in vs if v["top_k"] in (1, 3)]
print("\nvariants at an end of the lookback axis:", len(ends_lb))
print("variants at an end of the k axis:", len(ends_k))
print("both ends (=> 3 neighbours):",
      len([v for v in vs if v["lookback_months"] in (3, 12) and v["top_k"] in (1, 3)]))
print("neither end (=> 5 neighbours):",
      len([v for v in vs if v["lookback_months"] == 6 and v["top_k"] == 2]))
