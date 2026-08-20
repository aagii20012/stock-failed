"""Wrap-up edits: close the LEAN cross-check item in CLAUDE.local.md and add the
duplicated-algorithm-copy rule to .claude/rules/faber-lean.md."""

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL = os.path.join(ROOT, "CLAUDE.local.md")
RULES = os.path.join(ROOT, ".claude", "rules", "faber-lean.md")

LOCAL_OLD = """## Unfinished

- **LEAN cross-check: DONE and fully reconciled 2026-08-20.**"""

LOCAL_NEW = """## Baseline

Tag **`baseline-v1-faber-verified`** (commit `71eecee`, pushed 2026-08-20) is the
locked known-good state. Diff any future change against it:
`git diff baseline-v1-faber-verified -- faber-lean/`. The annotated tag message
carries the verified metrics, so read it with `git show baseline-v1-faber-verified`
rather than re-deriving them.

Confirmed at that tag: CAGR 9.32%, Sharpe vs SHY 0.537, max drawdown **-24.75%**
(LEAN fill timing -- quote this, not the harness's -22.58%), realistic cost 1.50 bps
of notional. Signal logic exactly reproduced across both implementations.

The one open finding it does *not* resolve: the momentum ranking shows no selection
skill (48-config sweep -- CAGR flattens at top-N=3 while Sharpe and drawdown improve
monotonically with N; 0 of 48 beat SPY's 11.02%). That sweep ran at the 10 bps cost
model now known to be ~6.7x too harsh, so its absolute CAGRs are understated -- the
gradient stands (every config paid the same) but re-run it at ~1.5 bps before
concluding anything about the SPY comparison.

## Unfinished

- **LEAN cross-check: DONE, reconciled, and committed 2026-08-20.**"""

RULES_OLD = """- Generated data (`data/`, `prices.csv`) is gitignored and reproducible from
  `fetch_reference_data.py` + `make_lean_data.py`. Do not commit vendor price data."""

RULES_NEW = """- Generated data (`data/`, `prices.csv`) is gitignored and reproducible from
  `fetch_reference_data.py` + `make_lean_data.py`. Do not commit vendor price data.
- **The algorithm exists in two byte-identical copies** -- `faber_sector_rotation.py`
  (readable) and `FaberSectorRotation/main.py` (LEAN entry point). Patch both in the
  same edit and `diff` them afterwards to prove they still match. Fixing only the
  readable copy feels like fixing the thing and does not change what LEAN runs.
- **Retract in code, not just in prose.** A claim disproved by the order events
  ("fills ~30 min after the open") survived two rounds of README correction inside
  the schedule comment of both copies, because the greps were scoped to `*.md`.
  Sweep source and config for the claim's distinctive tokens too."""


def patch(path, old, new):
    with io.open(path, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    if new in text:
        print("SKIP already patched: %s" % os.path.basename(path))
        return 0
    if text.count(old) != 1:
        print("FAIL block missing or not unique in %s (count=%d)"
              % (os.path.basename(path), text.count(old)))
        sys.exit(1)
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace(old, new))
    print("PATCHED %s" % os.path.basename(path))
    return 1


n = patch(LOCAL, LOCAL_OLD, LOCAL_NEW) + patch(RULES, RULES_OLD, RULES_NEW)
print("files changed: %d" % n)
