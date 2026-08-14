# How do you choose between two surviving strategies without looking at their returns?

**Platform:** Reddit — r/algotrading (crosspost candidate: r/quant)
**Status:** DRAFT — not posted
**Contains no strategy logic, no equity curves, no absolute performance figures, no credentials.** Two
development-window facts appear only as positions relative to sealed thresholds. The strategy has not
touched the validation window, so there is nothing to report about it and nothing to leak.

---

My development gate admitted two candidates and ranked neither. Both cleared the same six conditions;
the criteria were sealed months earlier and say nothing about what to do when two things pass. Only one
gets to see the validation window, because the window is a one-shot resource — every extra look at it
is a free parameter I don't have to declare.

So: pick one. And the obvious way to pick is the one way I'm not allowed to use, because "pick the
better-looking one" is a selection made on results I've already seen, which prices the validation
result at whatever the selection was worth. Eyeballing the two equity curves and choosing is exactly
the move the whole apparatus exists to prevent.

What I did instead was write a **return-blind** rule: a predicate that reads no return, no Sharpe, no
drawdown depth, no profit factor — only whether each candidate ever tripped the *research shutdown
threshold* during its declared development runs. That threshold is a risk-control tripwire fixed in the
project constitution, not a performance metric, and every candidate had already declared its full set
of runs including the cost-stress variants. One candidate had tripped it in two of its six declared
runs. The other, never. Survivor count: one. No tiebreak needed, no human coin flip.

The property I care about: **reverse the sign of every return in my development evidence and the rule
returns the same answer.** That's a mechanical check, not a vibe — the rule literally never reads the
fields that changed. Tests assert it by reading `reads_no_return` and `reads_no_risk_adjusted_metric`
off the sealed artifact and by re-deriving the trip counts from the raw declared-run list rather than
from the summary they're supposed to verify.

**The part I can't launder, and didn't try to.**

The rule's *output* is independent of returns. The *choice of predicate* is not. I picked "count
shutdown trips" while sitting on full knowledge of both candidates' development results, and a
different researcher with the same evidence would have picked a different blind rule. There is no
correction for that freedom, so the pre-registration says so in those words, in a section that exists
specifically to record what the mitigation does *not* cover. Three things constrain it and none of them
launders it: the rule was fixed and hashed before the window opened, it reduces to one number per
candidate with no tunable, and the survivor keeps its original identifier so it's traceable back to the
run that produced it.

The other thing I made myself write down first: the expected outcome is **failure**. Neither admitted
candidate reached the sealed Sharpe floor on *development* data, and the survivor's worst
non-breaching neighbour sat a fraction of a percent under the same drawdown ceiling the next gate
applies — headroom that isn't headroom. So
the honest prediction, recorded before the read, is that this thing gets rejected. Writing that down in
advance is most of the value — it's the difference between a failed test and a disappointment I get to
reinterpret.

**One implementation note that might be the most useful thing here.**

The seal has to prove that no evaluator existed when it was written — otherwise "pre-registered" means
nothing. My first instinct was to grep the source tree for the marker. That doesn't work, and the
failure is funny: a text search for the forbidden pattern matches *the file defining the search*, and
matches every governance document that discusses the prohibition. So the predicate parses the syntax
tree instead and asks structural questions — is there an import of the data layer, a call to a loader, a
network or broker import, an environment-variable read, a string constant containing a URL scheme — and
includes its own file in the scope it checks. It reads empty over the sealing program and over the
package builder, which is what makes "this code cannot reach the restricted window" a fact about the
AST rather than a promise in a comment.

Related: the first dry run of the sealing program failed its own predicate, because the marker table
contained a literal `"https://"`. The table is now composed from schemes at import time. A rule strict
enough to catch you is strict enough to catch itself, and that's the good outcome.

## What I don't know

Whether the survivor works. It hasn't been run on the validation window and it won't be until a
separate session does exactly two declared runs, once, with no re-run permitted afterwards. I also
don't know whether the shutdown-trip predicate is a *good* selection rule in any general sense — I only
claim it's a defensible one that couldn't have been reverse-engineered from the answer I wanted.

The part I'd most like attacked: is a return-blind rule chosen by a return-aware researcher actually
worth anything, or is it just a more elaborate way of choosing the one I liked? I think the reversal
property makes it more than theatre, but I'd rather hear the argument that it doesn't.
