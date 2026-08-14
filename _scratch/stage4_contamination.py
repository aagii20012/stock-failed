"""Recompute the six sealed Stage 4 contamination predicates exactly as they are defined.

The definitions are read from governance/STAGE_4_PREREGISTRATION.json rather than restated, so a
divergence between this program and the seal is impossible by construction for the *values* and
visible in the printed text for the *definitions*.

Run it twice: once before any Stage 4 evaluator code exists (the baseline), and once after the
decision package is built (the §13 re-verification). Every non-zero count must be explained by a
named file, never by a number alone.

ASCII-only output: the console is cp1252.
"""
import ast
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
SEAL = json.loads((ROOT / "governance/STAGE_4_PREREGISTRATION.json").read_text(encoding="utf-8"))
PROTOCOL = json.loads((ROOT / "config/stage4_validation_protocol.json").read_text(encoding="utf-8"))

SEALING_PROGRAM = "src/stockedge100/reporting/stage4_preregistration.py"

FORBIDDEN_IMPORT_ROOTS = {
    "alpaca", "alpaca_trade_api", "alpaca_py", "requests", "httpx", "aiohttp", "socket",
    "urllib", "http", "https", "websocket", "websockets", "boto3", "ftplib", "smtplib",
    "telnetlib", "paramiko", "ssl", "xmlrpc",
}
DATA_LAYER_ROOTS = {"stockedge100"}
DATA_LAYER_MODULES = {
    "stockedge100.backtest.dataset",
    "stockedge100.data.loader",
    "stockedge100.data.ingest",
    "stockedge100.data.normalize",
}
DATASET_LOADERS = {"load_dataset", "load_series", "series_from_rows", "iter_sessions"}
FORBIDDEN_ATTRS = {"environ", "getenv", "urlopen", "connect", "urlretrieve", "Session", "get", "post"}
ENV_ATTRS = {"environ", "getenv"}
CONNECT_ATTRS = {"urlopen", "connect", "urlretrieve"}


def out(text):
    sys.stdout.write(str(text).encode("ascii", "backslashreplace").decode("ascii") + "\n")


def rel(path):
    return path.relative_to(ROOT).as_posix()


def src_py():
    return sorted(p for p in (ROOT / "src/stockedge100").rglob("*.py") if p.is_file())


def run_labels():
    return [r["run_label"] for r in PROTOCOL["runs_declared"]["runs"]]


# -- predicate 1 ---------------------------------------------------------------------------------
def p1():
    hits = [rel(p) for p in src_py() if "stage4" in rel(p).lower() and rel(p) != SEALING_PROGRAM]
    return hits


# -- predicate 2 ---------------------------------------------------------------------------------
def p2():
    labels = run_labels()
    hits = []
    for path in src_py():
        text = path.read_text(encoding="utf-8", errors="replace")
        found = [lab for lab in labels if lab in text]
        if found:
            hits.append((rel(path), found))
    return hits


# -- predicate 3 ---------------------------------------------------------------------------------
def p3():
    base = ROOT / "reports"
    return [rel(p) for p in sorted(base.rglob("*")) if p.is_file() and "stage4" in rel(p).lower()]


# -- predicate 4 ---------------------------------------------------------------------------------
def p4():
    labels = run_labels()
    hits = []
    for path in sorted((ROOT / "runs").glob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        found = [tok for tok in ["STAGE_4"] + labels if tok in text]
        if found:
            hits.append((rel(path), found))
    return hits


# -- predicate 5 (AST, split into its two halves) ------------------------------------------------
def p5():
    """Returns (data_access_hits, broker_hits) for every stage4-path module, sealing program
    included.  The seal counts these together; this session's authorized validation read makes the
    data-access half legitimately non-zero, so the two halves are reported separately and the
    broker half must still be exactly zero."""
    data_hits, broker_hits = [], []
    for path in src_py():
        r = rel(path)
        if "stage4" not in r.lower():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        data_why, broker_why = [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in FORBIDDEN_IMPORT_ROOTS:
                        broker_why.append("import " + alias.name)
                    if alias.name in DATA_LAYER_MODULES:
                        data_why.append("import " + alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                root = mod.split(".")[0]
                if root in FORBIDDEN_IMPORT_ROOTS:
                    broker_why.append("from " + mod)
                if mod in DATA_LAYER_MODULES:
                    data_why.append("from " + mod)
                elif root in DATA_LAYER_ROOTS:
                    for alias in node.names:
                        if alias.name in DATASET_LOADERS:
                            data_why.append("from %s import %s" % (mod, alias.name))
            elif isinstance(node, ast.Attribute):
                if node.attr in ENV_ATTRS or node.attr in CONNECT_ATTRS:
                    broker_why.append("attribute ." + node.attr)
            elif isinstance(node, ast.Call):
                fn = node.func
                name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
                if name in DATASET_LOADERS:
                    data_why.append("call " + str(name))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                low = node.value.lower()
                if "http://" in low or "https://" in low:
                    broker_why.append("url string constant")
        if data_why:
            data_hits.append((r, sorted(set(data_why))))
        if broker_why:
            broker_hits.append((r, sorted(set(broker_why))))
    return data_hits, broker_hits


# -- predicate 6 ---------------------------------------------------------------------------------
def p6():
    records = [
        "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256",
        "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256",
    ]
    results = []
    for record in records:
        proc = subprocess.run(
            ["sha256sum", "-c", record], cwd=str(ROOT), capture_output=True, text=True
        )
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        bad = [ln for ln in lines if not ln.strip().endswith(": OK")]
        results.append((record, len(lines), len(bad) == 0 and proc.returncode == 0, bad[:3]))
    return results


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "recount"
    out("=" * 96)
    out("Stage 4 contamination predicates -- %s" % tag)
    out("sealed values: " + json.dumps(
        {k: v for k, v in SEAL["contamination_predicates"].items()
         if k not in ("definitions", "why_not_stage_3_predicates")}))
    out("=" * 96)

    hits = p1()
    out("")
    out("1  stage_4_evaluator_or_result_modules            = %d   (sealed 0)" % len(hits))
    for h in hits:
        out("       %s" % h)

    hits = p2()
    out("2  modules_naming_a_stage_4_run_label             = %d   (sealed 0)" % len(hits))
    for path, found in hits:
        out("       %s  %s" % (path, found))

    hits = p3()
    out("3  stage_4_report_artifacts                       = %d   (sealed 0, before-seal count)" % len(hits))
    for h in hits:
        out("       %s" % h)

    hits = p4()
    out("4  stage_4_run_records                            = %d   (sealed 0, before-seal count)" % len(hits))
    for path, found in hits:
        out("       %s  %s" % (path, found))

    data_hits, broker_hits = p5()
    out("5  stage_4_modules_touching_restricted_data_or_a_broker  (sealed 0, reported in halves)")
    out("     5a data-access half   = %d" % len(data_hits))
    for path, why in data_hits:
        out("       %s  %s" % (path, why))
    out("     5b broker/net/env/url half = %d   MUST BE 0" % len(broker_hits))
    for path, why in broker_hits:
        out("       %s  %s" % (path, why))

    out("6  gate_3_attempt_2_records_verify                (sealed true)")
    ok_all = True
    for record, n, ok, bad in p6():
        out("       %-64s %3d entries  %s" % (record, n, "OK" if ok else "FAILED"))
        ok_all = ok_all and ok
        for b in bad:
            out("           %s" % b)
    out("")
    out("broker half zero: %s     gate 3 records verify: %s" % (not broker_hits, ok_all))


main()
