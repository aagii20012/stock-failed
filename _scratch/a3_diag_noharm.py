"""Confirm the IWM diagnostic perturbed nothing sealed.

Read-only. Asserts:
  1. repo_state_id still equals the value the sealed Attempt 3 package recorded.
  2. Every sealed Attempt 3 checksum record still verifies.
  3. Stage 0 freeze still verifies.
  4. The only paths this diagnostic wrote are outside every repo_state_id pattern.
  5. No holdout path was opened by the diagnostic scripts (AST + text sweep of _scratch).
"""

import ast
import fnmatch
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Product\stock-trade-alpaca\stockedge100")
SCRATCH = Path(r"D:\Product\stock-trade-alpaca\_scratch")
sys.path.insert(0, str(ROOT / "src"))
from stockedge100.reporting.stage_package import repo_state, verify_sha256_record  # noqa: E402

fails = []


def check(label, ok, detail=""):
    print("   [%s] %-46s %s" % ("OK" if ok else "FAIL", label, detail))
    if not ok:
        fails.append(label)


# ---- 1. repo_state_id against the sealed Attempt 3 decision record -------------
print("== 1. repo_state_id vs sealed Attempt 3 record ==")
dec = json.loads(
    (ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.json").read_text(
        encoding="utf-8"
    )
)
sealed_rsid = dec["reproducibility"]["repo_state_id"]
code_hashes, rsid = repo_state()
check("sealed repo_state_id found", bool(sealed_rsid), sealed_rsid)
check("recomputed == sealed", rsid == sealed_rsid, rsid)
check("pattern file count non-empty", len(code_hashes) > 0, "%d files" % len(code_hashes))

# ---- 2. sealed Attempt 3 checksum records ------------------------------------
print("\n== 2. sealed Attempt 3 checksum records ==")
for rec in sorted((ROOT / "reports/stage3_g2_attempt3").glob("*.sha256")):
    res = verify_sha256_record(rec, ROOT)
    bad = {p: s for p, s in res.items() if s != "OK"}
    check(rec.name, len(res) > 0 and not bad, "%d entries, %d not OK" % (len(res), len(bad)))
for rec in sorted((ROOT / "governance/generation_2").glob("*A3*.sha256")):
    res = verify_sha256_record(rec, ROOT)
    bad = {p: s for p, s in res.items() if s != "OK"}
    check(rec.name, len(res) > 0 and not bad, "%d entries, %d not OK" % (len(res), len(bad)))

# ---- 3. Stage 0 freeze -------------------------------------------------------
print("\n== 3. Stage 0 freeze ==")
gov = ROOT / "governance"
res = verify_sha256_record(gov / "STAGE_0_FREEZE.sha256", gov)
bad = {p: s for p, s in res.items() if s != "OK"}
check("STAGE_0_FREEZE.sha256", len(res) > 0 and not bad, "%d entries, %d not OK" % (len(res), len(bad)))

# ---- 4. what this diagnostic wrote is outside every pattern ------------------
print("\n== 4. written paths vs repo_state_id patterns ==")
PATTERNS = [
    "governance/*.md", "governance/*.json", "governance/*.sha256",
    "src/**/*.py", "tests/**/*.py",
    "config/**/*.json", "config/**/*.yaml",
    "pyproject.toml", "README.md", ".gitignore",
]
OUTDIR = ROOT / "reports/diagnostics/attempt3_iwm_trace"
written = sorted(p.relative_to(ROOT).as_posix() for p in OUTDIR.rglob("*") if p.is_file())
check("wrote at least one file", len(written) > 0, str(written))
for rel in written:
    hit = [pat for pat in PATTERNS if fnmatch.fnmatch(rel, pat)]
    check("outside patterns: %s" % rel, not hit, str(hit) if hit else "")
    check("in code_hashes? %s" % rel, rel not in code_hashes, "")
# the positive control: a path that IS covered, so the predicate is not vacuous
check(
    "control: README.md IS matched by a pattern",
    any(fnmatch.fnmatch("README.md", p) for p in PATTERNS) and "README.md" in code_hashes,
    "predicate is discriminating",
)
check(
    "control: config/generation_2 json IS covered",
    any(k.startswith("config/generation_2/") for k in code_hashes),
    "%d such keys" % sum(1 for k in code_hashes if k.startswith("config/generation_2/")),
)

# ---- 5. no holdout / broker access from the diagnostic scripts ---------------
print("\n== 5. holdout and broker sweep over _scratch diagnostic scripts ==")
FORBIDDEN_TEXT = ("holdout", "HOLDOUT", "alpaca", "ALPACA", "api_key", "secret")
FORBIDDEN_IMPORT = {
    "requests", "httpx", "aiohttp", "socket", "urllib", "http", "https",
    "websocket", "websockets", "boto3", "alpaca", "alpaca_trade_api", "os",
}
FORBIDDEN_ATTR = {"environ", "getenv", "urlopen", "connect", "urlretrieve", "system", "popen"}
scripts = sorted(SCRATCH.glob("a3_*.py")) + sorted(SCRATCH.glob("patch_trace.py"))
check("diagnostic scripts found", len(scripts) > 0, str([s.name for s in scripts]))
for s in scripts:
    txt = s.read_text(encoding="utf-8")
    hits = [w for w in FORBIDDEN_TEXT if w in txt]
    check("no holdout/broker string: %s" % s.name, not hits, str(hits) if hits else "")
    imports, attrs, urls = set(), set(), []
    for node in ast.walk(ast.parse(txt)):
        if isinstance(node, ast.Import):
            imports |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Attribute):
            attrs.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "http://" in node.value or "https://" in node.value:
                urls.append(node.value)
    check("no forbidden import: %s" % s.name, not (imports & FORBIDDEN_IMPORT),
          str(sorted(imports & FORBIDDEN_IMPORT)))
    check("no forbidden attr: %s" % s.name, not (attrs & FORBIDDEN_ATTR),
          str(sorted(attrs & FORBIDDEN_ATTR)))
    check("no url literal: %s" % s.name, not urls, str(urls))

print("\n== summary ==")
print("   checks failed = %d %s" % (len(fails), fails if fails else ""))
sys.exit(1 if fails else 0)
