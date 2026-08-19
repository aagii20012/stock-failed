"""Seventh pass: the last literals the AT module pins, after pass 6 died on `rebalance_frequency`.

The variant field is `frequency`. Needed here: the eighteen ids, dissimilarity's source and quantum,
the neighbour literals AT-J writes out by hand, load_selection_rule's keys, check_seal_agreement's
shape, and the two gate helpers the extra tests assert.
"""

import inspect
import json
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def show(title, text):
    print("   --- %s ---" % title)
    for line in safe(text).splitlines():
        print("   |%s" % line)


print("=" * 100)
print("1. the eighteen variants")
from stockedge100.strategies import g2_rotation_ra3 as R

for v in R.rotation_variants():
    print("   %-2d %-46s L%-2s K%s %-9s w=%s"
          % (v.index, v.variant_id, v.lookback_months, v.top_k, v.frequency, v.target_weight))

print()
print("=" * 100)
print("2. g2_selection_v2 numerics")
from stockedge100.strategies import g2_selection_v2 as S

print("   SCORE_DECIMALS=%s SCORE_QUANTUM=%s" % (S.SCORE_DECIMALS, getattr(S, "SCORE_QUANTUM", "<absent>")))
print("   QUANTITIES=%s" % (S.QUANTITIES,))
print("   EXPECTED_STEP_CRITERIA=%s" % (S.EXPECTED_STEP_CRITERIA,))
print("   uppercase names: %s" % [n for n in dir(S) if n.isupper()])
show("dissimilarity", inspect.getsource(S.dissimilarity))
print("   d(3,7)=%s d(0,0)=%s d(0,5)=%s d(5,5)=%s"
      % (S.dissimilarity(3, 7), S.dissimilarity(0, 0), S.dissimilarity(0, 5), S.dissimilarity(5, 5)))
print()
show("neighbours_of", inspect.getsource(S.neighbours_of))
print()
print("   load_selection_rule() keys: %s" % sorted(S.load_selection_rule()))
print("   check_seal_agreement() ->")
for k, v in S.check_seal_agreement().items():
    print("      %-34s %s" % (k, safe(json.dumps(v, ensure_ascii=False, default=str))[:170]))

print()
print("=" * 100)
print("3. AT-J neighbour literals, computed")
struct = S.check_neighbourhood_structure()
for vid in sorted(struct["neighbours"]):
    print("   %-46s (%d) %s"
          % (vid, len(struct["neighbours"][vid]),
             [n.rsplit("RA3-", 1)[-1] for n in struct["neighbours"][vid]]))
print("   partition=%s symmetric=%s pairs=%s"
      % (struct["partition"], struct["symmetric"], struct["total_directed_pairs"]))

print()
print("=" * 100)
print("4. g2_gate_ra3 helpers the two extra tests assert")
from stockedge100.strategies import g2_gate_ra3 as G

dropped = G._pointers_dropped_since_attempt_2()
read = G._keys_the_frozen_evaluators_read()
print("   _pointers_dropped_since_attempt_2() -> %d" % len(dropped))
for entry in sorted(dropped):
    print("      %s" % safe(repr(entry)))
print("   _keys_the_frozen_evaluators_read() -> %d (first 12)" % len(read))
for entry in sorted(read)[:12]:
    print("      %s" % safe(repr(entry)))
print("   has _derived_alias_pointers: %s" % hasattr(G, "_derived_alias_pointers"))
if hasattr(G, "_derived_alias_pointers"):
    show("_derived_alias_pointers", inspect.getsource(G._derived_alias_pointers))

print()
print("=" * 100)
print("5. window guard")
from stockedge100.strategies import g2_window_guard as guard

print("   development_bound() = %s" % guard.development_bound())
print("   prohibited_windows() = %s" % (guard.prohibited_windows(),))
print("   public names: %s" % [n for n in dir(guard) if not n.startswith("_")])
