"""Strict dry-run of g2_stage3_attempt3_package.build().

The loose dry-run (ra3_dryrun_loose.py) stubbed three things because the research report and the
pytest capture did not exist yet. Both exist now and the README update has landed, so this run stubs
exactly ONE thing:

  * build_stage_package -> captures the StageDecision instead of writing anything

Everything else runs for real: the pytest capture is parsed off disk, the disclosure carriage is
checked against the actual report bytes, every checksum record is verified, both directions of
G2A3-CONFLICT-30 are asserted, and the evidence self-digest is recomputed.

It then diffs the assembled gate conditions against the research report's own gate table, which is
the check CLAUDE.md asks for: "print the assembled gate conditions, and diff them against the
report's own gate table."

ASCII output only - limitations[0] carries U+2212, which cp1252 cannot encode.
"""

import dataclasses
import json
import pathlib
import re
import sys
import traceback

SRC = "d:/Product/stock-trade-alpaca/stockedge100/src"
ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
OUT = pathlib.Path("d:/Product/stock-trade-alpaca/_scratch")
sys.path.insert(0, SRC)

import stockedge100.reporting.g2_stage3_attempt3_package as g2p  # noqa: E402


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


captured = {}


class FakeResult:
    run_id = "SE100-R-DRYRUN"
    repo_state_id = "0" * 64
    timestamp_utc = "DRY-RUN-NO-CLOCK-READ"
    freeze_ok = True
    checksum_digest = "0" * 64

    def __init__(self, root):
        self.decision_path = root / "reports/DRYRUN/decision.json"
        self.manifest_path = root / "reports/DRYRUN/manifest.json"
        self.checksum_path = root / "reports/DRYRUN/record.sha256"
        self.run_record_path = root / "runs/DRYRUN.json"


def fake_build_stage_package(decision):
    captured["decision"] = decision
    return FakeResult(g2p.PROJECT_ROOT)


g2p.build_stage_package = fake_build_stage_package

# ---- what the real capture on disk parses to, before build() is entered -------------------------
print("== real pytest capture ==")
try:
    raw = g2p.read_text(g2p.PYTEST_CAPTURE)
    print("  path      %s" % g2p.PYTEST_CAPTURE)
    print("  bytes     %d" % len((ROOT / g2p.PYTEST_CAPTURE).read_bytes()))
    print("  parsed    %s" % safe(g2p.test_counts(raw)))
    for line in raw.splitlines():
        if "passed" in line or "failed" in line or "collected" in line:
            print("  | %s" % safe(line.strip()))
except Exception:
    print(safe(traceback.format_exc()))

print("\n== real disclosure carriage (no stub) ==")
try:
    state = g2p.disclosure_carriage(g2p.load(g2p.PROTOCOL), g2p.load(g2p.EVIDENCE))
    print("  characters             %d" % state["characters"])
    print("  sha256_of_utf8         %s" % state["sha256_of_utf8"])
    print("  digest_agrees_with_ev  %s" % state["digest_agrees_with_evidence"])
    print("  all_carriers_verbatim  %s" % state["all_carriers_verbatim"])
    print("  all_byte_exact         %s" % state["all_carriers_byte_exact"])
    print("  need_normalisation     %s" % safe(state["carriers_requiring_normalisation"]))
    for rel, c in state["carriers"].items():
        print("  %-70s present=%-5s verbatim=%-5s byte_exact=%s"
              % (rel, c["present"], c["carries_verbatim"], c["carries_byte_exact"]))
except Exception:
    print(safe(traceback.format_exc()))

print("\n== build() with only build_stage_package stubbed ==")
code = None
try:
    code = g2p.build()
    print("  return code: %s" % code)
except Exception:
    print(safe(traceback.format_exc()))

decision = captured.get("decision")
if decision is None:
    print("\nNO StageDecision WAS ASSEMBLED - the guard above refused. Fix and re-run.")
    raise SystemExit(1)

body = dataclasses.asdict(decision)
(OUT / "ra3_dryrun_strict_decision.json").write_text(
    json.dumps(body, indent=1, default=str, ensure_ascii=False), encoding="utf-8", newline="\n"
)

# ---- the diff CLAUDE.md asks for ----------------------------------------------------------------
REPORT = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md"
md = REPORT.read_text(encoding="utf-8")

table = {}
for line in md.split("\n"):
    m = re.match(r"^\| `(S3-C\d)` \| (.+?) \| `(\w+)` \| (.+?) \| (.+?) \| `(\w+)` \| (.+?) \|$", line)
    if m:
        cid, text, bv, bm, thr, sv, sm = m.groups()
        table[cid] = {"text": text, "base_verdict": bv, "base_measured": bm,
                      "threshold": thr, "stress_verdict": sv, "stress_measured": sm}

rollup = None
for line in md.split("\n"):
    m = re.match(r"^\| `admissible_candidate_exists` \| \*\*(\w+)\*\* \|$", line)
    if m:
        rollup = m.group(1)

lines = []


def emit(text=""):
    lines.append(text)
    print(safe(text))


emit()
emit("== gate table parsed from the report ==")
emit("  condition rows: %d   admissible_candidate_exists: %r" % (len(table), rollup))

gc = body["gate_conditions"]
emit()
emit("== assembled gate_conditions (%d keys) ==" % len(gc))
for key in gc:
    emit("  %s" % key)

DIFFS = []
emit()
emit("== diff: assembled vs the report's table ==")
if len(table) != 7:
    DIFFS.append("the report's table parsed to %d rows, expected 7" % len(table))
if rollup is None:
    DIFFS.append("the report carries no admissible_candidate_exists rollup row")

for cid in sorted(table):
    if cid not in gc:
        DIFFS.append("%s is in the report but not in the assembled conditions" % cid)
        continue
    row = gc[cid]
    r = table[cid]
    # the assembled row aggregates on satisfaction across both runs; the report reports each run
    both = {r["base_verdict"], r["stress_verdict"]}
    expect_satisfied = both <= {"MET", "NOT_APPLICABLE_BY_CONDITION_TEXT"}
    got_satisfied = bool(row["satisfied"])
    ok = expect_satisfied == got_satisfied
    if not ok:
        DIFFS.append("%s satisfied=%s assembled, report verdicts %s"
                     % (cid, got_satisfied, sorted(both)))
    # the required text must be the report's own condition text
    if r["text"].strip() != row["required_verbatim"].strip():
        DIFFS.append("%s condition text differs:\n      report:    %r\n      assembled: %r"
                     % (cid, r["text"][:120], row["required_verbatim"][:120]))
    # the report's measured value must appear in the assembled row's measured field
    measured = json.dumps(row["measured"], default=str)
    for label, value in (("base", r["base_measured"]), ("stress", r["stress_measured"])):
        if value not in measured:
            DIFFS.append("%s %s measured %r is absent from the assembled measured field"
                         % (cid, label, value[:80]))
    emit("  %-8s report base=%-8s stress=%-8s | assembled verdict=%-32s satisfied=%s"
         % (cid, r["base_verdict"], r["stress_verdict"], row["verdict"], got_satisfied))

for cid in sorted(k for k in gc if k.startswith("S3-C")):
    if cid not in table:
        DIFFS.append("%s is assembled but absent from the report's table" % cid)

ace = gc.get("admissible_candidate_exists")
emit()
emit("== admissible_candidate_exists ==")
if ace is None:
    DIFFS.append("the assembled conditions carry no admissible_candidate_exists row")
else:
    for field in sorted(ace):
        emit("  %-46s %s" % (field, safe(json.dumps(ace[field], default=str))[:300]))
    if rollup is not None:
        expect = rollup.lower() == "true"
        if bool(ace["value"]) != expect:
            DIFFS.append("admissible_candidate_exists value=%s assembled, report says %r"
                         % (ace["value"], rollup))
    if ace["verdict"] != "NOT_MET":
        DIFFS.append("the rollup verdict is %r on a FAIL" % ace["verdict"])
    if ace["permissive_base_only_reading_would_give"] is not False:
        DIFFS.append("the permissive reading is %r, not the evidence's False"
                     % ace["permissive_base_only_reading_would_give"])
    # The rollup row's required_verbatim is NOT a quotation from the report -- the report expresses
    # the rollup as a `| `admissible_candidate_exists` | **false** |` table row plus prose. It is a
    # builder-authored paraphrase of constitution section 9, and the checkable claim about it is
    # continuity: Attempt 1's and Attempt 2's closed decision records carry the same sentence, so
    # Attempt 3's rollup row must not silently reword it. Compare against those records on disk.
    PRIOR_RECORDS = ("reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json",
                     "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json")
    for rel in PRIOR_RECORDS:
        prior = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        rows = prior["gate_conditions"]["admissible_candidate_exists"]
        if rows["required_verbatim"] != ace["required_verbatim"]:
            DIFFS.append("the rollup required_verbatim differs from %s: prior %r vs assembled %r"
                         % (rel, rows["required_verbatim"], ace["required_verbatim"]))
    # and the report must carry the rollup label with the same value, which the rollup parse above did
    if "| `admissible_candidate_exists` | **false** |" not in md:
        DIFFS.append("the report does not carry the rollup row as a false table row")

# ---- the verdict, and the tokens it must not emit -----------------------------------------------
ev = g2p.load(g2p.EVIDENCE)
sv = ev["stage_verdict"]
emit()
emit("== verdict coherence ==")
emit("  assembled verdict      %s" % safe(body["verdict"]))
emit("  evidence token         %s" % sv["verdict_token"])
emit("  gate_passed            %s" % body["gate_passed"])
emit("  admitted_candidates    %s" % sv["admitted_candidates"])
if sv["verdict_token"] not in body["verdict"]:
    DIFFS.append("the assembled verdict does not carry the sealed token")
if body["gate_passed"] is not False:
    DIFFS.append("gate_passed is %r on a FAIL" % body["gate_passed"])
# "Emitting" a token means using it as an outcome. Naming it inside the sealed
# verdict_token_derivation block, or inside the withheld-list metadata that exists precisely to
# declare which tokens are being withheld, is the disclosure -- not a violation of it. So the
# predicate is scoped: no token may appear at any path OUTSIDE that declared allowlist.
# matched as substrings, not prefixes: the StageDecision wraps its payload in a `body` key, so the
# real paths are /body/body/... and a prefix match on /body/ silently missed all of them
ALLOWED_PATHS = (
    "/verdict_token_derivation/",
    "/stage_verdict/pass_token",
    "/stage_verdict/fail_token",
    "/stage_verdict/prior_attempt_tokens_withheld",
    "/stage_verdict/prior_attempt_tokens_note",
)
WATCHED = [sv["pass_token"]] + list(sv["prior_attempt_tokens_withheld"])


def scan(node, path, found):
    if isinstance(node, dict):
        for k, v in node.items():
            scan(v, path + "/" + str(k), found)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            scan(v, path + "[%d]" % i, found)
    else:
        s = str(node)
        for tok in WATCHED:
            start = 0
            while True:
                j = s.find(tok, start)
                if j < 0:
                    break
                start = j + 1
                # a bare Attempt 1 token is a substring of the Attempt 2/3 tokens; skip those hits
                pre = s[max(0, j - 12):j]
                if pre.endswith("ATTEMPT_2_") or pre.endswith("ATTEMPT_3_"):
                    if tok.startswith("STAGE_3_G2_STRATEGY") or tok == "STAGE_3_G2_NO_CANDIDATE":
                        continue
                found.append((tok, path))


FOUND = []
scan(body, "/body", FOUND)
emit()
emit("== token emission scan (%d hit(s)) ==" % len(FOUND))
for tok, path in FOUND:
    allowed = any(frag in path for frag in ALLOWED_PATHS)
    emit("  %-6s %-58s %s" % ("ok" if allowed else "STRAY", tok[-46:], path))
    if not allowed:
        DIFFS.append("the token %s is emitted at %s, outside the declared allowlist" % (tok, path))
if not any(t2 == sv["pass_token"] for t2, _ in FOUND):
    DIFFS.append("this gate's PASS token appears nowhere, so the derivation was not carried")
if sv["pass_token"] in body["verdict"]:
    DIFFS.append("the verdict field itself carries this gate's PASS token")
for tok in sv["prior_attempt_tokens_withheld"]:
    if tok in body["verdict"]:
        DIFFS.append("the verdict field carries the withheld prior token %s" % tok)

emit()
emit("== tests / dates / config ==")
for key in ("tests", "date_range", "universe_version", "config_hash", "holdout_state",
            "gate_id", "gate_name", "generation"):
    emit("  %-18s %s" % (key, safe(body[key])))
emit("  %-18s %d evidence / %d limitations / %d conflicts / %d run_notes"
     % ("counts", len(body["evidence"]), len(body["limitations"]),
        len(body["conflicts_found"]), len(body["run_notes"])))

emit()
if DIFFS:
    emit("== %d DISAGREEMENT(S) ==" % len(DIFFS))
    for d in DIFFS:
        emit("  - %s" % d)
else:
    emit("== NO DISAGREEMENT between the assembled conditions and the report's gate table ==")

(OUT / "ra3_dryrun_strict_report.txt").write_text(
    "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
)
raise SystemExit(1 if DIFFS or code != 0 else 0)
