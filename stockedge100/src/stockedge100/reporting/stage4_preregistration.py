"""Seal the Stage 4 validation-evaluation pre-registration.

Run from ``stockedge100/``, **before** any Stage 4 evaluator code exists and before any validation
observation has been read::

    PYTHONPATH=src python -m stockedge100.reporting.stage4_preregistration

Writes:

* ``governance/STAGE_4_PREREGISTRATION.json``   — authoritative declaration timestamp, the digest of
  every pre-registered file, and the concrete digest set that Gate 4's S4-C7 will recheck
* ``governance/STAGE_4_PREREGISTRATION.sha256`` — checksum record over those files
* one reproducibility record under ``runs/``

As in every earlier stage the JSON carries **no** ``repo_state_id``: it lives in ``governance/`` and
is one of the inputs to that digest, so any value written here would be stale on write. The binding
value is in the ``runs/`` record.

Four files are sealed simultaneously, so none of them carries the digest of another — a file cannot
contain the digest of a file that contains its own. The enclosing ``.sha256`` record carries all
four plus this JSON record. For the same reason the S4-C7 digest set recorded here is **twelve**
concrete paths, not thirteen: the thirteenth entry of that set is this record itself, and nothing
hashes itself.

Why the contamination check is not Stage 3's check
-------------------------------------------------

The available predicates narrow with every stage. ``src/stockedge100/strategies/`` and
``reports/stage3_attempt2/`` are legitimately populated and may not be emptied, so counting to zero
over those paths proves nothing about Stage 4. Six Stage-4-specific predicates replace it, each
narrow enough to be zero only if no Stage 4 evaluator, result, or restricted read exists, and each
carrying its own definition into the sealed record so a reader can check what was counted rather
than trusting the count. Five must be zero; the sixth must verify.

Two of the six are **AST** questions rather than text searches, because a text search over this very
module would match the words in these predicate definitions. Walking the syntax tree counts imports,
calls, attributes and string constants that the interpreter would actually execute, so prose about a
forbidden name is not a use of it.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

from stockedge100.audit import (
    RunRecord,
    dependency_versions,
    sha256_file,
    utc_now_iso,
    write_sha256_record,
)
from stockedge100.reporting.stage_package import (
    PROJECT_ROOT,
    RUNS_DIR,
    TRACKED_DEPENDENCIES,
    new_run_id,
    repo_state,
    verify_sha256_record,
    verify_stage0_freeze,
)

PROTOCOL_REL = "config/stage4_validation_protocol.json"
CRITERIA_REL = "config/stage4_gate_criteria.json"
SELECTION_REL = "config/stage4_representative_selection.json"
DOCUMENT_REL = "governance/STAGE_4_PREREGISTRATION.md"

PREREGISTERED = (PROTOCOL_REL, CRITERIA_REL, SELECTION_REL, DOCUMENT_REL)

RECORD_REL = "governance/STAGE_4_PREREGISTRATION.json"
RECORD_SHA_REL = "governance/STAGE_4_PREREGISTRATION.sha256"
RECORD_JSON = PROJECT_ROOT / RECORD_REL
RECORD_SHA = PROJECT_ROOT / RECORD_SHA_REL

SRC_DIR = PROJECT_ROOT / "src" / "stockedge100"
STRATEGY_DIR = SRC_DIR / "strategies"
REPORTS_DIR = PROJECT_ROOT / "reports"

THIS_MODULE_REL = "src/stockedge100/reporting/stage4_preregistration.py"

STAGE_MARKER = "stage4"
STAGE_TOKEN = "STAGE_4"

# Records verified before sealing. Freeze records list bare filenames and verify from the directory
# that holds them; every other record here uses project-root-relative paths and verifies from the
# project root. Passing the wrong root reports MISSING for every entry and looks like an integrity
# failure when it is an operator error.
FREEZE_RECORDS = (("stage1_freeze", "governance/STAGE_1_FREEZE.sha256", 2),)
ROOT_RECORDS = (
    ("stage1_prereg", "governance/STAGE_1_PREREGISTRATION.sha256", 4),
    ("stage2_prereg", "governance/STAGE_2_PREREGISTRATION.sha256", 4),
    ("stage3_prereg", "governance/STAGE_3_PREREGISTRATION.sha256", 4),
    ("stage3_attempt2_prereg", "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256", 4),
    ("stage0_decision", "reports/stage0/STAGE_0_VERIFICATION.sha256", 8),
    ("stage1_decision", "reports/stage1/STAGE_1_DATA_READINESS.sha256", 19),
    ("stage2_decision", "reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256", 20),
    ("stage3_decision", "reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256", 26),
    ("stage3_attempt2_design", "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256", 31),
    (
        "stage3_attempt2_decision",
        "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256",
        37,
    ),
)

# The Gate 3 Attempt 2 immutability pair: the pre-registration that declared the candidates and the
# decision record that evaluated them. If either moved by a byte, the evidence this selection rests
# on is not the evidence that was sealed.
GATE_3_IMMUTABILITY = (
    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256",
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256",
)

# AST vocabulary for the two structural predicates. These are matched against import roots, imported
# module paths, call targets, attribute names and string constants in the parsed tree, never against
# the raw text of a file, so naming one here is not using one.
DATA_LAYER_MODULES = ("stockedge100.data", "stockedge100.datasets")
LOADER_CALLS = frozenset(
    {"load_series", "load_dataset", "load_prices", "load_panel", "read_csv", "read_parquet"}
)
NETWORK_IMPORT_ROOTS = frozenset(
    {
        "alpaca",
        "alpaca_trade_api",
        "aiohttp",
        "boto3",
        "http",
        "httpx",
        "requests",
        "socket",
        "urllib",
        "urllib3",
        "websocket",
        "websockets",
    }
)
CREDENTIAL_ATTRIBUTES = frozenset({"environ", "getenv", "urlopen", "urlretrieve", "connect"})
# Composed rather than written out, because this module is itself one of the files the predicate
# walks: a literal marker here would be a string constant containing a URL scheme, and the check
# would flag its own marker table. The first dry-run did exactly that.
URL_MARKERS = tuple(scheme + "://" for scheme in ("http", "https", "ftp", "ws", "wss"))

HEX64 = re.compile(r"\b[0-9a-f]{64}\b")

# The phrase in the S4-C7 measurement text that stands in for an entry of the sealed digest list.
# Two entries of that list are named collectively and one is named by role rather than by path, so a
# literal substring test would report a disagreement that is not there.
S4_C7_COVERING_PHRASES = {
    "governance/STAGE_4_PREREGISTRATION.md": "both Stage 4 pre-registration files",
    RECORD_REL: "both Stage 4 pre-registration files",
}

PREDICATE_DEFINITIONS = {
    "stage_4_evaluator_or_result_modules": (
        "Count of files under src/stockedge100/ with suffix .py whose path relative to the project "
        "root, lowercased with backslashes normalised to forward slashes, contains 'stage4', "
        "EXCLUDING exactly " + THIS_MODULE_REL + ". The exclusion is this sealing program itself, "
        "which would otherwise count itself; it is one named file rather than a whole directory, so "
        "a Stage 4 evaluator placed anywhere - including under reporting/ - is still counted. Must "
        "be 0."
    ),
    "modules_naming_a_stage_4_run_label": (
        "Count of files under src/stockedge100/ with suffix .py whose decoded text contains any run "
        "label declared in " + PROTOCOL_REL + " runs_declared. Catches a Stage 4 evaluator added to "
        "an existing module, which the path-based predicate above would miss. Must be 0."
    ),
    "stage_4_report_artifacts": (
        "Count of files anywhere under reports/ whose project-root-relative path, lowercased and "
        "slash-normalised, contains 'stage4'. Any Stage 4 result, metric, fold table, or evidence "
        "artifact would appear here. Must be 0 at sealing. The Stage 4 decision package written "
        "later in this same session is a design-session package and lands under reports/stage4/ "
        "AFTER this seal; a re-verification then legitimately counts more than zero, and the value "
        "recorded here is the count that existed before this seal."
    ),
    "stage_4_run_records": (
        "Count of files under runs/ whose decoded text contains 'STAGE_4' or any run label declared "
        "in " + PROTOCOL_REL + " runs_declared. Measured BEFORE this seal writes its own run record, "
        "which carries stage STAGE_4_VALIDATION_PRE_REGISTRATION and therefore contains the token by "
        "construction. Must be 0."
    ),
    "stage_4_modules_touching_restricted_data_or_a_broker": (
        "Count of files under src/stockedge100/ with suffix .py whose relative path contains "
        "'stage4' - this sealing program INCLUDED - whose parsed syntax tree contains an import of "
        "the data-access layer, a call to a dataset loader, an import of a network or broker "
        "package, an attribute access used to read an environment variable or open a connection, or "
        "a string constant containing a URL scheme. This is an AST question, not a text search: a "
        "text search would match the words of this very definition. It is the fail-closed proof "
        "that the pre-registration path cannot read a validation or holdout observation and cannot "
        "reach a broker. Must be 0."
    ),
    "gate_3_attempt_2_records_verify": (
        "Both governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256 and "
        "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256 verify entry-for-entry "
        "from the project root. This is the Gate 3 Attempt 2 immutability check: the representative "
        "was selected from that decision record, so it fails if the evidence behind the selection "
        "changed by a single byte. Must be true."
    ),
}


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _normalised_prose(text: str) -> str:
    """Strip Markdown presentation so a sentence can be compared across the two formats."""
    lines = [line.lstrip().lstrip(">").strip() for line in text.splitlines()]
    stripped = " ".join(lines).replace("*", "").replace("`", "")
    return " ".join(stripped.split())


def _run_labels(protocol: dict) -> list[str]:
    return [run["run_label"] for run in protocol["runs_declared"]["runs"]]


def _source_files() -> list[Path]:
    if not SRC_DIR.is_dir():
        return []
    return sorted(path for path in SRC_DIR.rglob("*.py") if path.is_file())


def _stage_4_modules() -> list[str]:
    return sorted(
        _rel(path)
        for path in _source_files()
        if STAGE_MARKER in _rel(path).lower() and _rel(path) != THIS_MODULE_REL
    )


def _modules_naming_a_run_label(run_labels: list[str]) -> list[str]:
    hits = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(label in text for label in run_labels):
            hits.append(_rel(path))
    return hits


def _stage_4_report_artifacts() -> list[str]:
    if not REPORTS_DIR.is_dir():
        return []
    return sorted(
        _rel(path)
        for path in REPORTS_DIR.rglob("*")
        if path.is_file() and STAGE_MARKER in _rel(path).lower()
    )


def _stage_4_run_records(run_labels: list[str]) -> list[str]:
    if not RUNS_DIR.is_dir():
        return []
    hits = []
    for path in sorted(RUNS_DIR.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if STAGE_TOKEN in text or any(label in text for label in run_labels):
            hits.append(_rel(path))
    return hits


def _restricted_access_findings(path: Path) -> list[str]:
    """Return the AST findings that would let ``path`` reach restricted data or a broker."""
    findings: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in NETWORK_IMPORT_ROOTS:
                    findings.append(f"import {alias.name}")
                if alias.name.startswith(DATA_LAYER_MODULES):
                    findings.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".")[0] in NETWORK_IMPORT_ROOTS:
                findings.append(f"from {module} import ...")
            if module.startswith(DATA_LAYER_MODULES):
                findings.append(f"from {module} import ...")
            findings += [
                f"from {module} import {alias.name}"
                for alias in node.names
                if alias.name in LOADER_CALLS
            ]
        elif isinstance(node, ast.Call):
            target = node.func
            name = (
                target.id
                if isinstance(target, ast.Name)
                else target.attr
                if isinstance(target, ast.Attribute)
                else None
            )
            if name in LOADER_CALLS:
                findings.append(f"call {name}()")
        elif isinstance(node, ast.Attribute):
            if node.attr in CREDENTIAL_ATTRIBUTES:
                findings.append(f"attribute .{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if any(marker in node.value for marker in URL_MARKERS):
                findings.append("string constant containing a URL scheme")
    return sorted(set(findings))


def _stage_4_modules_touching_restricted_data() -> list[str]:
    hits = []
    for path in _source_files():
        if STAGE_MARKER not in _rel(path).lower():
            continue
        findings = _restricted_access_findings(path)
        if findings:
            hits.append(f"{_rel(path)}: {', '.join(findings)}")
    return hits


def _check_record(label: str, rel: str, root: Path, expected: int) -> list[str]:
    """Verify one checksum record and return every line that is not ``OK``."""
    path = PROJECT_ROOT / rel
    if not path.is_file():
        return [f"{label}: record missing at {rel}"]
    results = verify_sha256_record(path, root=root)
    problems = sorted(f"{label}: {name} -> {result}" for name, result in results.items() if result != "OK")
    if len(results) != expected:
        problems.append(f"{label}: {len(results)} entries, expected {expected}")
    return problems


def _digest_index() -> dict[str, list[str]]:
    """Map every on-disk digest to the tracked files that currently have it."""
    index: dict[str, list[str]] = {}
    patterns = (
        "governance/*.md",
        "governance/*.json",
        "config/*.json",
        "src/stockedge100/**/*.py",
        "reports/**/*.json",
        "reports/**/*.md",
        "README.md",
    )
    for pattern in patterns:
        for path in PROJECT_ROOT.glob(pattern):
            if path.is_file():
                index.setdefault(sha256_file(path), []).append(_rel(path))
    return index


def _resolve_strategy_module(experiment_id: str) -> list[str]:
    if not STRATEGY_DIR.is_dir():
        return []
    return sorted(
        _rel(path)
        for path in STRATEGY_DIR.rglob("*.py")
        if path.is_file() and experiment_id in path.read_text(encoding="utf-8", errors="replace")
    )


def build() -> int:
    if RECORD_JSON.exists() or RECORD_SHA.exists():
        print("REFUSED: a Stage 4 pre-registration record already exists.", file=sys.stderr)
        print("A pre-registration is sealed once. Regenerating it would destroy its meaning.", file=sys.stderr)
        return 2

    missing = [name for name in PREREGISTERED if not (PROJECT_ROOT / name).is_file()]
    if missing:
        print(f"REFUSED: pre-registered file(s) missing: {missing}", file=sys.stderr)
        return 5

    protocol = json.loads((PROJECT_ROOT / PROTOCOL_REL).read_text(encoding="utf-8"))
    criteria = json.loads((PROJECT_ROOT / CRITERIA_REL).read_text(encoding="utf-8"))
    selection = json.loads((PROJECT_ROOT / SELECTION_REL).read_text(encoding="utf-8"))
    document = (PROJECT_ROOT / DOCUMENT_REL).read_text(encoding="utf-8")

    representative = selection["application"]["outcome"]["selected_representative"]
    run_labels = _run_labels(protocol)

    # --- contamination, measured before anything is written ----------------------------------
    modules = _stage_4_modules()
    naming = _modules_naming_a_run_label(run_labels)
    artifacts = _stage_4_report_artifacts()
    records = _stage_4_run_records(run_labels)
    restricted = _stage_4_modules_touching_restricted_data()

    contamination = {
        "stage_4_evaluator_or_result_modules": modules,
        "modules_naming_a_stage_4_run_label": naming,
        "stage_4_report_artifacts": artifacts,
        "stage_4_run_records": records,
        "stage_4_modules_touching_restricted_data_or_a_broker": restricted,
    }
    dirty = {name: hits for name, hits in contamination.items() if hits}
    if dirty:
        print("REFUSED: Stage 4 implementation, result, or restricted-access artifacts exist.", file=sys.stderr)
        for name, hits in sorted(dirty.items()):
            print(f"  {name}: {len(hits)}", file=sys.stderr)
            for hit in hits:
                print(f"    {hit}", file=sys.stderr)
        print(
            "The pre-registration is not prospective with respect to those artifacts. Record the "
            "contamination and stop; do not seal.",
            file=sys.stderr,
        )
        return 3

    # --- upstream integrity ------------------------------------------------------------------
    freeze_ok, freeze_detail = verify_stage0_freeze()
    if not freeze_ok:
        print("REFUSED: the Stage 0 freeze does not verify. Stop and investigate.", file=sys.stderr)
        return 4

    problems: list[str] = []
    record_entry_counts: dict[str, int] = {}
    for label, rel, expected in FREEZE_RECORDS:
        path = PROJECT_ROOT / rel
        problems += _check_record(label, rel, path.parent, expected)
        record_entry_counts[rel] = len(verify_sha256_record(path, root=path.parent))
    for label, rel, expected in ROOT_RECORDS:
        problems += _check_record(label, rel, PROJECT_ROOT, expected)
        record_entry_counts[rel] = len(verify_sha256_record(PROJECT_ROOT / rel, root=PROJECT_ROOT))
    if problems:
        print("REFUSED: an upstream checksum record does not verify:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 4

    # --- everything adopted by digest must still bind -----------------------------------------
    drifted: list[str] = []
    bound: dict[str, dict[str, str]] = {}
    for source, entries in (
        (PROTOCOL_REL, protocol["inputs_bound"]["bound_by_digest"]),
        (CRITERIA_REL, criteria["measurement_adopted_by_digest"]["bound_artifacts"]),
    ):
        for entry in entries:
            rel = entry["path"]
            target = PROJECT_ROOT / rel
            if not target.is_file():
                drifted.append(f"{source} binds {rel}, which is not on disk")
                continue
            live = sha256_file(target)
            if live != entry["sha256"]:
                drifted.append(f"{source} binds {rel} at {entry['sha256']}, live is {live}")
            bound[rel] = {"artifact_id": entry["artifact_id"], "sha256": live, "bound_by": source}
    if drifted:
        print("REFUSED: an artifact adopted by digest does not match the live file:", file=sys.stderr)
        for line in drifted:
            print(f"  {line}", file=sys.stderr)
        print(
            "Stage 4 adopts its measurements by reference, so a drifted digest means the "
            "measurements it claims to adopt are not the measurements on disk.",
            file=sys.stderr,
        )
        return 6

    # --- the sealed representative must map to exactly one strategy module --------------------
    strategy_modules = _resolve_strategy_module(representative)
    if len(strategy_modules) != 1:
        print(
            f"REFUSED: {len(strategy_modules)} strategy modules name {representative}; "
            "S4-C7 recomputes the digest of exactly one.",
            file=sys.stderr,
        )
        for hit in strategy_modules:
            print(f"    {hit}", file=sys.stderr)
        return 8
    strategy_rel = strategy_modules[0]

    # --- the document and the machine-readable specification must agree ----------------------
    normalised_document = _normalised_prose(document)
    disagreements: list[str] = []

    if representative not in document:
        disagreements.append(f"the representative {representative} is not named in {DOCUMENT_REL}")
    derivation = criteria["verdict_token_derivation"]
    for role in ("pass_token", "fail_token"):
        if derivation[role] not in document:
            disagreements.append(f"the Gate 4 {role} {derivation[role]} is not named in {DOCUMENT_REL}")
    for source, key, label in (
        (protocol, "research_question", "research question"),
        (criteria, "frozen_gate_text_verbatim", "frozen Gate 4 text"),
    ):
        if _normalised_prose(source[key]) not in normalised_document:
            disagreements.append(f"the {label} in the document does not match the specification")
    if _normalised_prose(selection["selection_rule"]["statement"]) not in normalised_document:
        disagreements.append("the selection rule in the document does not match the selection record")
    if _normalised_prose(protocol["single_validation_read_rule"]["rule"]) not in normalised_document:
        disagreements.append("the single-read rule in the document does not match the protocol")

    # The selection record must decide, and it must decide the representative it names. A record that
    # named a representative the rule did not select would be a retrospective choice wearing a
    # prospective rule's clothes.
    outcome = selection["application"]["outcome"]
    survivors = [
        entry["candidate"]
        for entry in selection["application"]["candidates"]
        if entry["screen_result"] == "SURVIVES"
    ]
    if survivors != [representative]:
        disagreements.append(
            f"the rule leaves survivors {survivors}, which is not exactly [{representative}]"
        )
    if outcome["survivors"] != survivors or outcome["survivor_count"] != len(survivors):
        disagreements.append("the recorded outcome does not match the per-candidate screen results")
    if outcome["survivor_count"] != 1 or outcome["human_selection_required"] is not False:
        disagreements.append(
            "the rule did not decide; the stage must stop for human selection rather than seal"
        )

    folds = criteria["walk_forward_fold_construction"]["test_folds"]
    if folds["count"] != len(folds["folds"]):
        disagreements.append(
            f"the declared fold count {folds['count']} is not the number of folds enumerated "
            f"({len(folds['folds'])})"
        )
    if criteria["walk_forward_fold_construction"]["train_folds"]["count"] != 0:
        disagreements.append("train_folds is not empty; Gate 4 forbids re-fitting on validation")
    if str(folds["count"]) not in document:
        disagreements.append(f"the fold count {folds['count']} is not stated in {DOCUMENT_REL}")

    if protocol["runs_declared"]["count"] != len(protocol["runs_declared"]["runs"]):
        disagreements.append("runs_declared.count is not the number of runs enumerated")
    for label in run_labels:
        if label not in document:
            disagreements.append(f"the run label {label} is not named in {DOCUMENT_REL}")

    # S4-C7 is measured from the protocol's recheck list, so the two must enumerate the same set.
    recheck = protocol["reproducibility_requirements"]["sealed_digests_to_recheck"]
    condition_7 = next(item for item in criteria["conditions"] if item["id"] == "S4-C7")
    measurement = condition_7["measurement"]
    for item in recheck:
        if item in measurement:
            continue
        phrase = S4_C7_COVERING_PHRASES.get(item)
        if phrase and phrase in measurement:
            continue
        if item.startswith("the strategy module") and "the strategy module" in measurement:
            continue
        disagreements.append(f"S4-C7 does not name the sealed digest entry {item!r}")
    if f"{len(recheck)}-item" not in measurement:
        disagreements.append(
            f"S4-C7 does not state the size of the sealed digest set as {len(recheck)}-item"
        )

    for source_rel, payload in (
        (PROTOCOL_REL, protocol),
        (CRITERIA_REL, criteria),
        (SELECTION_REL, selection),
    ):
        if payload.get("live_trading_authorized") is not False:
            disagreements.append(f"{source_rel} does not record live_trading_authorized false")

    # Every 64-hex string in the document must resolve to a file whose current digest it is. That
    # catches a tree digest (which resolves to nothing), a stale pin, and the document's own digest.
    index = _digest_index()
    document_digest = sha256_file(PROJECT_ROOT / DOCUMENT_REL)
    pinned = sorted(set(HEX64.findall(document)))
    for digest in pinned:
        if digest == document_digest:
            disagreements.append("the document contains its own digest; nothing hashes itself")
        elif digest not in index:
            disagreements.append(f"the document pins {digest}, which is no file on disk")

    if disagreements:
        print("REFUSED: the document and the machine-readable specification disagree:", file=sys.stderr)
        for line in disagreements:
            print(f"  {line}", file=sys.stderr)
        return 7

    timestamp = utc_now_iso()
    run_id = new_run_id(timestamp)
    digests = {name: sha256_file(PROJECT_ROOT / name) for name in PREREGISTERED}

    # The concrete digest set S4-C7 will recheck. Twelve entries, not thirteen: the thirteenth is
    # this record, whose digest is carried by the enclosing .sha256 record because nothing hashes
    # itself. The strategy module is resolved by content rather than named by hand.
    sealed_digests = {}
    for item in recheck:
        if item == RECORD_REL:
            continue
        rel = strategy_rel if item.startswith("the strategy module") else item
        sealed_digests[rel] = sha256_file(PROJECT_ROOT / rel)

    record = {
        "document_id": "SE100-GOV-0008",
        "project": "StockEdge100",
        "generation": 1,
        "stage": 4,
        "record_type": "PRE_REGISTRATION",
        "status": "SEALED",
        "declared_utc": timestamp,
        "run_id": run_id,
        "constitution_ref": "SE100-GOV-0001",
        "document_id_note": (
            "SE100-GOV-0004 is unused across the tree. This record takes 0008, the next number after "
            "the highest in use, rather than filling a gap whose reason is not recorded anywhere on "
            "disk."
        ),
        "supersedes": None,
        "declared_before_any_validation_observation_was_read": True,
        "gate": {
            "constitutional_gate": criteria["gate_id"],
            "name": criteria["gate_name"],
            "prompt_stage": 4,
            "conditions_evaluated": len(criteria["conditions"]),
            "condition_ids": [item["id"] for item in criteria["conditions"]],
            "within_candidate": "CONJUNCTIVE",
            "across_candidates": "NOT_APPLICABLE_EXACTLY_ONE_REPRESENTATIVE",
            "pass_token": derivation["pass_token"],
            "fail_token": derivation["fail_token"],
            "token_source": CRITERIA_REL + " verdict_token_derivation",
            "gate_4_evaluated": False,
            "gate_4_passed": False,
            "conflicts_recorded": [item["id"] for item in criteria["conflicts_found"]],
        },
        "sealed_representative": {
            "experiment_id": representative,
            "selection_rule_id": selection["selection_rule"]["id"],
            "selection_rule_name": selection["selection_rule"]["name"],
            "survivor_count": selection["application"]["outcome"]["survivor_count"],
            "human_selection_required": selection["application"]["outcome"][
                "human_selection_required"
            ],
            "eliminated_by_the_rule": sorted(
                entry["candidate"]
                for entry in selection["application"]["candidates"]
                if entry["screen_result"] != "SURVIVES"
            ),
            "screen_results": {
                entry["candidate"]: {
                    "declared_run_count": entry["declared_run_count"],
                    "shutdown_trip_count": entry["shutdown_trip_count"],
                    "screen_result": entry["screen_result"],
                }
                for entry in selection["application"]["candidates"]
            },
            "strategy_module": strategy_rel,
            "strategy_module_sha256": sealed_digests[strategy_rel],
            "strategy_module_resolution": (
                "Resolved by content: exactly one module under src/stockedge100/strategies/ names "
                "the sealed representative. Not named by hand, so it cannot silently point at the "
                "wrong file."
            ),
        },
        "walk_forward_fold_construction": {
            "id": criteria["walk_forward_fold_construction"]["id"],
            "test_folds": folds["count"],
            "train_folds": criteria["walk_forward_fold_construction"]["train_folds"]["count"],
            "first_fold": folds["folds"][0],
            "last_fold": folds["folds"][-1],
            "authored_in_this_session": True,
            "why_authored_here": (
                "No fold definition exists anywhere on disk, so S4-C6 is unmeasurable without one. "
                "Constitution section 8's requirement of a signed specification created before "
                "execution is the authority to write it prospectively. Recorded as S4-CONFLICT-4."
            ),
        },
        "runs_declared": {
            "count": protocol["runs_declared"]["count"],
            "count_is_a_hard_limit": protocol["runs_declared"]["count_is_a_hard_limit"],
            "run_labels": run_labels,
            "sessions_reading_validation": protocol["iteration_budget"]["sessions_reading_validation"],
            "re_runs_permitted_after_a_valid_completed_run": protocol["iteration_budget"][
                "re_runs_permitted_after_a_valid_completed_run"
            ],
        },
        "stage_0_freeze_verified": True,
        "stage_0_freeze_verification": freeze_detail,
        "upstream_records_verified": record_entry_counts,
        "gate_3_attempt_2_immutability_records": list(GATE_3_IMMUTABILITY),
        "inputs_bound_recomputed": bound,
        "sealed_before_any_stage_4_evaluator_code": True,
        "contamination_predicates": {
            "definitions": PREDICATE_DEFINITIONS,
            "stage_4_evaluator_or_result_modules": len(modules),
            "modules_naming_a_stage_4_run_label": len(naming),
            "stage_4_report_artifacts": len(artifacts),
            "stage_4_run_records": len(records),
            "stage_4_modules_touching_restricted_data_or_a_broker": len(restricted),
            "gate_3_attempt_2_records_verify": True,
            "why_not_stage_3_predicates": (
                "Stage 3 Attempt 2 counted modules and artifacts carrying the marker 'attempt2'. "
                "That marker is now legitimately all over src/stockedge100/strategies/ and "
                "reports/stage3_attempt2/, and those files may not be deleted, so it says nothing "
                "about Stage 4. Two of the six predicates here are AST questions rather than text "
                "searches, because a text search over the sealing program would match the words of "
                "its own predicate definitions."
            ),
        },
        "restricted_data_posture": {
            "validation_rows_read": 0,
            "validation_prices_read": 0,
            "validation_indicators_computed": 0,
            "validation_trades_counted": 0,
            "holdout_observations_read": 0,
            "dataset_loads_in_this_session": 0,
            "how_this_is_known": (
                "Structural, not asserted. No module on the pre-registration path imports the data "
                "layer or calls a dataset loader, which is the AST predicate "
                "stage_4_modules_touching_restricted_data_or_a_broker, recorded above as 0 and "
                "exercised by tests/unit/test_stage4_preregistration.py on dates alone."
            ),
        },
        "preregistered_files": {name: {"sha256": digest} for name, digest in digests.items()},
        "sealed_digests_for_s4_c7": {
            "entries": sealed_digests,
            "declared_set_size": len(recheck),
            "recorded_here": len(sealed_digests),
            "own_digest_excluded": RECORD_REL,
            "own_digest_location": (
                "The thirteenth entry of the declared set is this record. Nothing hashes itself, so "
                "its digest is carried by " + RECORD_SHA_REL + " instead."
            ),
            "recheck_rule": protocol["reproducibility_requirements"]["recheck_rule"],
        },
        "checksum_record": {
            "path": RECORD_SHA_REL,
            "path_convention": "project-root-relative",
            "verify_from": "stockedge100/",
            "command": "cd stockedge100 && sha256sum -c " + RECORD_SHA_REL,
        },
        "repo_state_id_location": (
            "Deliberately omitted here. This file lives in governance/ and is one of the inputs to "
            "repo_state_id, so any value written into it would be stale on write. The binding value "
            f"is the repo_state_id field of runs/{run_id}.json."
        ),
        "simultaneous_seal_note": (
            "Four files are sealed at this timestamp: " + ", ".join(PREREGISTERED) + ". None carries "
            "the digest of another, because a file cannot contain the digest of a file that contains "
            "its own. They reference each other by artifact id and path; " + RECORD_SHA_REL + " "
            "carries every digest."
        ),
        "binding_consequences": [
            "The representative is " + representative + " and may not change for any reason, "
            "including a Gate 4 FAIL. No robustness neighbour may be substituted for it, no "
            "parameter may be altered, and no risk overlay may be added.",
            "The other Gate 3 admitted candidate is not evaluated on validation, is not run for "
            "comparison, and is not repaired. C3 remains rejected and is not reconsidered.",
            "The validation partition is read exactly once, in exactly one authorized session, from "
            "exactly one dataset load, with both declared runs executed inside that session against "
            "that load. Two runs over one load is one read.",
            "Two runs, one parameterisation, zero re-runs after a valid completed run, and no "
            "neighbour runs. There is no search at Gate 4.",
            "Gate 4's seven conditions, their thresholds, and the 0% documented cash rate are "
            "extracted from frozen artifacts and adopted by digest, not chosen here. The one "
            "measurement authored in this session is the walk-forward fold construction, and it is "
            "derived from the frozen window boundaries alone.",
            "The stressed-cost run changes status from non-gating at Gate 3 to gating at Gate 4. The "
            "multiplier is the 2.0 already sealed in SE100-CFG-2001.",
            "S4-C3's drawdown ceiling and the section 5.1 research shutdown are the same 15% on the "
            "same series, so S4-C3 is met if and only if the shutdown never fires.",
            "A Gate 4 FAIL is a deliverable, not a reason to retune, substitute, promote a "
            "neighbour, relax a threshold, or read the window again. There is no Attempt 2 at Gate "
            "4 in this design.",
            "The selection is an adaptive step taken with knowledge of Gate 3 development results. "
            "The rule is return-blind and parameter-free, the disclosure is in "
            + SELECTION_REL
            + " adaptation_disclosure, and the cumulative development experiment count is not reset "
            "by this stage.",
            "Validation stays LOCKED until the separately authorized evaluation session. The holdout "
            "stays SEALED regardless of the Gate 4 outcome.",
            "live_trading_authorized remains false.",
        ],
        "authorized_windows_in_this_session": [],
        "validation_window_state": protocol["partitions"]["validation"]["state_now"],
        "holdout_window_state": protocol["partitions"]["holdout"]["state"],
        "validation_evaluation_authorized": True,
        "validation_evaluation_authorized_for": (
            "Exactly one evaluation of "
            + representative
            + " on the locked validation window, in a later separately authorized session, under "
            + PROTOCOL_REL
            + " and "
            + CRITERIA_REL
            + " exactly as sealed here. Nothing else."
        ),
        "validation_access_authorized_in_this_session": False,
        "holdout_access_authorized": False,
        "gate_3_passed": True,
        "gate_4_evaluated": False,
        "gate_4_passed": False,
        "stage_5_authorized": False,
        "paper_trading_authorized": False,
        "shadow_live_authorized": False,
        "capital_or_risk_expansion_authorized": False,
        "live_trading_authorized": False,
    }
    RECORD_JSON.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # Written last so it covers the final bytes of the JSON above. It does not contain its own
    # digest; nothing hashes itself.
    covered = dict(digests)
    covered[RECORD_REL] = sha256_file(RECORD_JSON)
    own_digest = write_sha256_record(covered, RECORD_SHA)

    code_hashes, repo_state_id = repo_state()
    RunRecord(
        run_id=run_id,
        stage="STAGE_4_VALIDATION_PRE_REGISTRATION",
        command="python -m stockedge100.reporting.stage4_preregistration",
        timestamp_utc=timestamp,
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=digests[PROTOCOL_REL],
        dataset_hashes={},
        universe_version="SE100-CFG-1002@1.0.0",
        date_range=None,
        holdout_state="SEALED",
        strategy_id=None,
        random_seed=None,
        dependency_versions=dependency_versions(TRACKED_DEPENDENCIES),
        exit_status="OK",
        output_artifact_hashes={
            RECORD_REL: covered[RECORD_REL],
            RECORD_SHA_REL: own_digest,
        },
        notes=[
            "The validation procedure, the Gate 4 criteria, the representative selection record and "
            "the pre-registration document sealed before any Stage 4 evaluator code existed and "
            "before any validation observation was read.",
            "Representative " + representative + " selected by " + selection["selection_rule"]["id"]
            + ", a return-blind screen over the declared variant set. The other admitted candidate "
            "was eliminated by the same predicate. No validation or holdout information entered the "
            "selection.",
            "Gate 4's seven conditions extracted verbatim from the frozen constitution; six "
            "thresholds and the 0% documented cash rate adopted by digest from frozen artifacts. "
            "The walk-forward fold construction is the one measurement authored here, derived from "
            "the frozen window boundaries alone.",
            "Contamination measured over six Stage-4-specific predicates, five zero and one "
            "verifying, each with its definition recorded in the sealed JSON. Two are AST questions "
            "because a text search over the sealing program would match its own definitions.",
            "Gate 3 Attempt 2 immutability verified: the pre-registration and decision checksum "
            "records both verify entry-for-entry, so the evidence behind the selection is the "
            "evidence that was sealed.",
            "strategy_id is null because no strategy was run. The sealed representative is recorded "
            "in the pre-registration record, not as a run of this session.",
            "dataset_hashes is empty because no dataset was loaded. No validation row, price, "
            "indicator or trade was read or computed, and the holdout was not touched.",
            "No credential access. No network access. No broker client. No order, cancel, replace or "
            "liquidation. live_trading_authorized remains false.",
        ],
    ).write(RUNS_DIR)

    print(f"run_id           {run_id}")
    print(f"declared_utc     {timestamp}")
    print(f"repo_state_id    {repo_state_id}")
    print(f"representative   {representative}  via {selection['selection_rule']['id']}")
    print(f"strategy module  {strategy_rel}")
    print(f"gate             {criteria['gate_id']} {criteria['gate_name']}  "
          f"{len(criteria['conditions'])} conditions, {len(criteria['conflicts_found'])} conflicts")
    print(f"runs declared    {protocol['runs_declared']['count']}  {', '.join(run_labels)}")
    print(f"folds            {folds['count']} test, "
          f"{criteria['walk_forward_fold_construction']['train_folds']['count']} train")
    print("contamination    " + ", ".join(
        f"{name}={len(hits)}" for name, hits in sorted(contamination.items())
    ))
    print(f"digests pinned   {len(pinned)} in {DOCUMENT_REL}, all resolved to files on disk")
    print(f"s4_c7 set        {len(sealed_digests)} recorded of {len(recheck)} declared "
          f"(own digest in {RECORD_SHA_REL})")
    for name, digest in digests.items():
        print(f"  {digest}  {name}")
    print(f"sealed           {RECORD_REL} / {RECORD_SHA_REL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
