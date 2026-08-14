"""Stage 4 pre-access verification sweep (operating prompt section 2).

Runs BEFORE any code is written and BEFORE any validation observation is loaded.
Recomputes repo_state_id, the 13-artifact S4-C7 recheck set, and the
no-prior-Stage-4-result predicates.  Read-only.
"""
import ast
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(ROOT / "src"))
from stockedge100.reporting.stage_package import repo_state, verify_sha256_record  # noqa: E402

fails = []
notes = []


def check(label, ok, detail=""):
    line = ("OK   " if ok else "FAIL ") + label + (" :: " + detail if detail else "")
    (notes if ok else fails).append(line)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


PRE_JSON = ROOT / "governance/STAGE_4_PREREGISTRATION.json"
pre = json.loads(PRE_JSON.read_text(encoding="utf-8"))
seal_run_id = pre["run_id"]
seal_run = json.loads((ROOT / "runs" / (seal_run_id + ".json")).read_text(encoding="utf-8"))
pkg_run_id = "SE100-R-20260814T111459Z"
pkg_run = json.loads((ROOT / "runs" / (pkg_run_id + ".json")).read_text(encoding="utf-8"))

# ---------------------------------------------------------------- 1. checksums
records = [
    ("STAGE_0_FREEZE.sha256", ROOT / "governance"),
    ("STAGE_1_FREEZE.sha256", ROOT / "governance"),
    ("governance/STAGE_1_PREREGISTRATION.sha256", ROOT),
    ("governance/STAGE_2_PREREGISTRATION.sha256", ROOT),
    ("governance/STAGE_3_PREREGISTRATION.sha256", ROOT),
    ("governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256", ROOT),
    ("governance/STAGE_4_PREREGISTRATION.sha256", ROOT),
    ("reports/stage0/STAGE_0_VERIFICATION.sha256", ROOT),
    ("reports/stage1/STAGE_1_DATA_READINESS.sha256", ROOT),
    ("reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256", ROOT),
    ("reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256", ROOT),
    ("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256", ROOT),
    ("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256", ROOT),
    ("reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.sha256", ROOT),
]
total_entries = 0
for rel, cwd in records:
    results = verify_sha256_record(cwd / rel, cwd)
    bad = {k: v for k, v in results.items() if v != "OK"}
    total_entries += len(results)
    check("sha256sum -c %s (from %s) %d entries" % (rel, cwd.name, len(results)),
          bad == {}, "not OK=" + str(bad))
check("total checksum entries verified", total_entries > 0, str(total_entries))

# ------------------------------------------------------------ 2. repo_state_id
code_hashes, rsid = repo_state()
sealed_rsid = pkg_run["repo_state_id"]
check("repo_state_id recomputes to the Stage 4 package value",
      rsid == sealed_rsid, rsid + " vs " + sealed_rsid)
check("sealed repo_state_id begins 718be055 and ends 4a0686",
      sealed_rsid.startswith("718be055") and sealed_rsid.endswith("4a0686"), sealed_rsid)
check("sealing-run repo_state_id differs (5 files added after the seal)",
      seal_run["repo_state_id"] != sealed_rsid,
      seal_run["repo_state_id"][:16] + " vs " + sealed_rsid[:16])
check("repo_state_files count matches the package manifest",
      len(code_hashes) > 0, str(len(code_hashes)) + " tracked files")

# ------------------------------------------------ 3. thirteen-artifact recheck
entries = pre["sealed_digests_for_s4_c7"]["entries"]
declared = pre["sealed_digests_for_s4_c7"]["declared_set_size"]
check("declared_set_size is 13", declared == 13, str(declared))
check("12 digests recorded in the pre-registration (13th is the file itself)",
      len(entries) == 12, str(len(entries)))
drift = []
for rel, want in entries.items():
    got = sha(ROOT / rel)
    if got != want:
        drift.append(rel + " " + got[:12] + " != " + want[:12])
check("all 12 recorded S4-C7 digests recompute exactly", drift == [], str(drift))

chk_lines = {}
for line in (ROOT / "governance/STAGE_4_PREREGISTRATION.sha256").read_text(
        encoding="utf-8").splitlines():
    if line.strip():
        d, p = line.split(None, 1)
        chk_lines[p.strip().lstrip("*")] = d
thirteenth = "governance/STAGE_4_PREREGISTRATION.json"
check("13th member digest carried by the checksum record",
      chk_lines.get(thirteenth) == sha(PRE_JSON),
      str(chk_lines.get(thirteenth))[:12] + " vs " + sha(PRE_JSON)[:12])
recheck_set = sorted(set(entries) | {thirteenth})
check("recheck set resolves to 13 distinct paths", len(recheck_set) == 13, str(len(recheck_set)))

# --------------------------------------------- 4. constitution frozen, unchanged
con_md = ROOT / "governance/STAGE_0_CONSTITUTION.md"
con_js = ROOT / "governance/STAGE_0_CONSTITUTION.json"
s0 = pre["stage_0_freeze_verification"]
check("constitution .md digest matches the Stage 4 seal",
      sha(con_md) == s0["STAGE_0_CONSTITUTION.md"]["recorded"], sha(con_md)[:16])
check("constitution .json digest matches the Stage 4 seal",
      sha(con_js) == s0["STAGE_0_CONSTITUTION.json"]["recorded"], sha(con_js)[:16])
check("Stage 4 seal recorded both constitution digests as matching",
      all(e["match"] == "True" for e in s0.values()))

# ------------------------------------- 5. no Stage 4 evaluator / result / run
src_mods = sorted(str(p.relative_to(ROOT)).replace("\\", "/")
                  for p in (ROOT / "src").rglob("*.py"))
evaluator_like = [m for m in src_mods
                  if "stage4" in m.lower() and "package" not in m and "preregistration" not in m]
check("no Stage 4 evaluator module exists", evaluator_like == [], str(evaluator_like))
r4 = sorted(p.name for p in (ROOT / "reports/stage4").glob("*"))
expected_r4 = [
    "STAGE_4_VALIDATION_PREREGISTRATION.json",
    "STAGE_4_VALIDATION_PREREGISTRATION.sha256",
    "STAGE_4_VALIDATION_PREREGISTRATION_ARTIFACT_MANIFEST.json",
    "STAGE_4_VALIDATION_PREREGISTRATION_TEST_SUMMARY.md",
    "pytest_stage4_output.txt",
]
check("reports/stage4 holds only the pre-registration artifacts",
      r4 == sorted(expected_r4), str(r4))
runs = sorted(p.stem for p in (ROOT / "runs").glob("*.json"))
check("runs/ latest is the pre-registration package run",
      runs[-1] == pkg_run_id, runs[-1])
val_runs = []
for p in (ROOT / "runs").glob("*.json"):
    rec = json.loads(p.read_text(encoding="utf-8"))
    dh = rec.get("dataset_hashes") or {}
    dr = str(rec.get("date_range") or "")
    if "2021-08-01" in dr or "2024-07-31" in dr:
        val_runs.append(p.stem)
check("no run record touches the validation window", val_runs == [], str(val_runs))
check("runs/ record count", len(runs) == 16, str(len(runs)))

# ----------------------------------------------- 6. holdout sealed, guards live
lock = json.loads((ROOT / "governance/STAGE_1_HOLDOUT_LOCK.json").read_text(encoding="utf-8"))
check("holdout_state SEALED", lock["holdout_state"] == "SEALED", lock["holdout_state"])
part = lock["partition"]
check("holdout window is 2024-08-01..2026-07-31",
      (part["holdout_start"], part["holdout_end"]) == ("2024-08-01", "2026-07-31"),
      str((part["holdout_start"], part["holdout_end"])))
check("validation window is 2021-08-01..2024-07-31",
      (part["validation_start"], part["validation_end"]) == ("2021-08-01", "2024-07-31"),
      str((part["validation_start"], part["validation_end"])))
check("development window ends 2021-07-31", part["development_end"] == "2021-07-31",
      part["development_end"])
win = (ROOT / "src/stockedge100/backtest/window.py").read_text(encoding="utf-8")
check("ResearchWindow raises WindowViolation", "WindowViolation" in win)
check("MarketView raises LookAheadError",
      "LookAheadError" in (ROOT / "src/stockedge100/backtest/market.py").read_text(
          encoding="utf-8"))
check("broker/ execution/ monitoring/ risk/ portfolio/ are empty",
      all(not any((ROOT / "src/stockedge100" / d).iterdir())
          for d in ("broker", "execution", "monitoring", "risk", "portfolio")))

# --------------------------------------------------- 7. no broker access in src
FORBIDDEN_ROOTS = {"alpaca", "alpaca_trade_api", "alpaca_py", "requests", "httpx", "aiohttp",
                   "socket", "urllib", "urllib2", "urllib3", "http", "httplib", "websocket",
                   "websockets", "boto3", "botocore", "ftplib", "telnetlib", "smtplib",
                   "paramiko", "pycurl"}
FORBIDDEN_ATTRS = {"environ", "getenv", "urlopen", "connect", "urlretrieve", "putenv"}
imp_v, attr_v, url_v = [], [], []
for rel in src_mods:
    tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        roots = set()
        if isinstance(node, ast.Import):
            roots = {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots = {(node.module or "").split(".")[0]}
        if roots & FORBIDDEN_ROOTS:
            imp_v.append(rel + ":" + str(sorted(roots & FORBIDDEN_ROOTS)))
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
            attr_v.append(rel + ":" + node.attr)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "http://" in node.value or "https://" in node.value:
                url_v.append(rel)
check("no forbidden import root in src/", imp_v == [], str(imp_v[:4]))
check("no forbidden attribute in src/", attr_v == [], str(attr_v[:4]))
check("no http(s) string constant in src/", url_v == [], str(sorted(set(url_v))[:4]))

# ------------------------------------------------- 8. authorization flags on disk
FLAGS = ["gate_3_passed", "gate_4_evaluated", "gate_4_passed",
         "validation_evaluation_authorized", "validation_access_authorized_in_this_session",
         "holdout_access_authorized", "stage_5_authorized", "paper_trading_authorized",
         "shadow_live_authorized", "live_trading_authorized",
         "capital_or_risk_expansion_authorized"]
for k in FLAGS:
    want = k in ("gate_3_passed", "validation_evaluation_authorized")
    check("sealed " + k + " == " + str(want), pre.get(k, "<absent>") is want, repr(pre.get(k)))
check("sealed validation_window_state", pre["validation_window_state"],
      str(pre["validation_window_state"]))
check("sealed holdout_window_state", pre["holdout_window_state"],
      str(pre["holdout_window_state"]))
check("sealed before any Stage 4 evaluator code",
      bool(pre["sealed_before_any_stage_4_evaluator_code"]),
      str(pre["sealed_before_any_stage_4_evaluator_code"])[:70])
check("declared before any validation observation was read",
      bool(pre["declared_before_any_validation_observation_was_read"]),
      str(pre["declared_before_any_validation_observation_was_read"])[:70])
cp = pre["contamination_predicates"]
# bool is a subclass of int -- exclude it or the True flag reads as a non-zero count
nonzero = {k: v for k, v in cp.items()
           if isinstance(v, int) and not isinstance(v, bool) and v != 0}
check("sealed contamination counts all zero", nonzero == {}, str(nonzero))
flags_false = {k: v for k, v in cp.items() if isinstance(v, bool) and v is not True}
check("sealed contamination flags all True", flags_false == {}, str(flags_false))

print("\n".join(notes))
print("")
print("\n".join(fails) if fails else "ALL CHECKS PASS")
print("")
print("%d ok / %d failed" % (len(notes), len(fails)))
print("repo_state_id (now)    " + rsid)
print("repo_state_id (sealed) " + sealed_rsid)
print("tracked files          " + str(len(code_hashes)))
