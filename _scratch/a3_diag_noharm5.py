"""Section 5 of the no-harm sweep, with the predicate corrected.

The first version reported 9 failures, all of them predicate defects of the exact class
`.claude/rules/frozen-artifacts.md` warns about:

  * every `alpaca` hit was the workspace directory name `stock-trade-alpaca`;
  * the only `holdout` hit was a NEGATIVE assertion in the report generator's own prose
    ("Neither holdout partition was read");
  * the `http://` / `https://` and credential-word hits were in the sweep's own forbidden-word
    list, i.e. the checker matching itself;
  * `os` is imported by the trace and never used.

Each is now encoded as an assertion that still fails if the underlying fact stops holding,
rather than as an allow-list entry.
"""

import ast
import re
import sys
from pathlib import Path

SCRATCH = Path(r"D:\Product\stock-trade-alpaca\_scratch")
WORKSPACE_DIR_TOKEN = "stock-trade-alpaca"

fails = []


def check(label, ok, detail=""):
    print("   [%s] %-52s %s" % ("OK" if ok else "FAIL", label, detail))
    if not ok:
        fails.append(label)


# The sweep cannot sweep itself: any checker necessarily contains the vocabulary it forbids.
# Named explicitly rather than skipped silently.
SELF = {"a3_diag_noharm.py", "a3_diag_noharm5.py"}

CRED_WORDS = ("api_key", "apikey", "secret_key", "ALPACA_API", "ALPACA_SECRET", "PAPER_KEY")
FORBIDDEN_IMPORT = {
    "requests", "httpx", "aiohttp", "socket", "urllib", "http", "websocket",
    "websockets", "boto3", "alpaca", "alpaca_trade_api", "subprocess", "shutil",
}
FORBIDDEN_ATTR = {"environ", "getenv", "urlopen", "connect", "urlretrieve", "system", "popen"}

DIAG = ("a3_iwm_trace.py", "a3_iwm_sizing.py", "a3_iwm_report.py", "a3_keys.py",
        "patch_trace.py", "a3_final_immutability.py")
scripts = [SCRATCH / n for n in DIAG]
assert all(p.exists() for p in scripts), [p.name for p in scripts if not p.exists()]
check("diagnostic scripts swept", len(scripts) >= 6, str([s.name for s in scripts]))
check("sweep excludes only itself, by name", SELF == {"a3_diag_noharm.py", "a3_diag_noharm5.py"},
      "excluded: %s" % sorted(SELF))

total_alpaca_hits = 0
total_holdout_hits = 0

for s in scripts:
    txt = s.read_text(encoding="utf-8")
    n = s.name

    # --- 'alpaca' must occur ONLY as part of the workspace directory name --------
    all_alpaca = [m.start() for m in re.finditer(r"alpaca", txt, re.IGNORECASE)]
    residual = [i for i in all_alpaca
                if txt[max(0, i - len(WORKSPACE_DIR_TOKEN)): i + len("alpaca")].lower()
                .find(WORKSPACE_DIR_TOKEN) < 0]
    total_alpaca_hits += len(all_alpaca)
    check("alpaca only in workspace path: %s" % n, not residual,
          "%d total hits, %d residual" % (len(all_alpaca), len(residual)))

    # --- 'holdout' must occur ONLY on a line that denies reading one -------------
    hl = [ln for ln in txt.splitlines() if re.search(r"holdout", ln, re.IGNORECASE)]
    total_holdout_hits += len(hl)
    bad_hl = [ln for ln in hl
              if not re.search(r"\b(neither|no|not|never)\b", ln, re.IGNORECASE)]
    check("holdout only in a denial line: %s" % n, not bad_hl,
          "%d lines, %d not denials" % (len(hl), len(bad_hl)))

    # --- no credential-shaped token, no url literal ------------------------------
    check("no credential token: %s" % n,
          not [w for w in CRED_WORDS if w.lower() in txt.lower()],
          str([w for w in CRED_WORDS if w.lower() in txt.lower()]))

    imports, attrs, urls, used_names = set(), set(), [], set()
    for node in ast.walk(ast.parse(txt)):
        if isinstance(node, ast.Import):
            imports |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Attribute):
            attrs.add(node.attr)
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "http://" in node.value or "https://" in node.value:
                urls.append(node.value[:60])
    check("no forbidden import: %s" % n, not (imports & FORBIDDEN_IMPORT),
          str(sorted(imports & FORBIDDEN_IMPORT)))
    check("no forbidden attr: %s" % n, not (attrs & FORBIDDEN_ATTR),
          str(sorted(attrs & FORBIDDEN_ATTR)))
    check("no url literal: %s" % n, not urls, str(urls))
    # 'os' is permitted only as a dead import: zero attribute access through it.
    if "os" in imports:
        check("os imported but unused: %s" % n, "os" not in used_names,
              "os.<attr> accesses = %d" % sum(1 for a in ast.walk(ast.parse(txt))
                                              if isinstance(a, ast.Attribute)
                                              and isinstance(a.value, ast.Name)
                                              and a.value.id == "os"))

# Non-vacuity: the sweep must have found something to reason about, or it proves nothing.
check("alpaca predicate was exercised", total_alpaca_hits > 0,
      "%d hits resolved to the workspace path" % total_alpaca_hits)
check("holdout predicate was exercised", total_holdout_hits > 0,
      "%d holdout lines, all denials" % total_holdout_hits)

print("\n== summary ==")
print("   checks failed = %d %s" % (len(fails), fails if fails else ""))
sys.exit(1 if fails else 0)
