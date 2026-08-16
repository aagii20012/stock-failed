"""Check the hand-authored Attempt 2 pre-registration Markdown against its config.

The Markdown is prose; the config is the source of record. Every value the Markdown states about
the strategy must be findable in the config, not merely plausible. This is the same agreement the
sealer will enforce -- running it here means a disagreement is a cheap edit rather than a refusal
after the sealer is already written.

ASCII output only (cp1252 console).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
MD = ROOT / "governance" / "generation_2" / "STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"
CFG = ROOT / "config" / "generation_2" / "g2_rotation_ra1_protocol.json"
CRIT = ROOT / "config" / "generation_2" / "g2_gate_criteria_ra1.json"

md = MD.read_text(encoding="utf-8")
cfg = json.loads(CFG.read_text(encoding="utf-8"))
crit = json.loads(CRIT.read_text(encoding="utf-8"))
blob = json.dumps(cfg)

# The Markdown is hard-wrapped at 100 columns, so a prose sentence is routinely split across two
# lines. Search prose against a whitespace-collapsed copy; search table rows against the raw text,
# where the line structure is itself part of the claim.
flat = re.sub(r"\s+", " ", md)

FAILED: list[str] = []
N = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global N
    N += 1
    if not ok:
        FAILED.append(label)
    print("%-4s %s%s" % ("OK" if ok else "FAIL", label, ("  " + detail) if detail else ""))


def has(label: str, needle: str) -> None:
    check(label, needle in md, "" if needle in md else "missing: %r" % needle[:70])


def hasflat(label: str, needle: str) -> None:
    """Prose search, immune to the 100-column hard wrap."""
    n = re.sub(r"\s+", " ", needle)
    check(label, n in flat, "" if n in flat else "missing: %r" % n[:80])


# ---------------------------------------------------------------- identity
has("doc id SE100-GOV-2005", "`SE100-GOV-2005`")
has("strategy id", cfg["strategy_id"])
has("generation id", cfg["generation_id"])
has("family", cfg["family"])
check("candidate index C2", "| Candidate index | C2 |" in md and cfg["candidate_index"] == 2)
has("config artifact id", cfg["artifact_id"])
has("criteria artifact id", crit["artifact_id"])
has("attempt 1 doc id", "SE100-GOV-2003")
check("stage/gate/attempt", (cfg["stage"], cfg["gate_id"], cfg["attempt"]) == (3, 3, 2)
      and "| Stage | 3 |" in md and "| Attempt | 2 |" in md)
check("live_trading_authorized false", cfg["live_trading_authorized"] is False
      and "| `live_trading_authorized` | `false` |" in md)

# ---------------------------------------------------------------- universe
uni = cfg["eligible_universe"]
check("universe member count", "| Member count | 34 |" in md and uni["member_count"] == 34)
has("universe version", uni["universe_version"])
missing = [s for s in uni["members"] if not re.search(r"\b%s\b" % re.escape(s), md)]
check("all 34 members present in md", not missing, "missing: %s" % missing)
check("AAPL excluded and said so", "AAPL" in uni["excluded_symbols"] and "`AAPL`" in md)

# ---------------------------------------------------------------- weights
ps = cfg["position_sizing"]
weights = {int(k): v for k, v in ps["target_weights"].items()}
gross = {int(k): v for k, v in ps["target_gross_exposure"].items()}
for k in sorted(weights):
    row = "| %d | %s | %s |" % (k, weights[k], gross[k])
    check("weight row k=%d" % k, row in md, row)
check("attempt 1 formula quoted", ps["attempt_1_formula"].replace(" ", "") in md.replace(" ", ""),
      ps["attempt_1_formula"])
check("ROUND_DOWN called load-bearing", "`ROUND_DOWN` is load-bearing" in md
      and "load-bearing" in ps["round_down_note"])

# ---------------------------------------------------------------- run span
span = cfg["run_span"]
check("run start", "| Run start | %s (%s) |" % (span["run_start"], span["run_start_weekday"]) in md)
check("run end", "| Run end | %s |" % span["run_end"] in md)
check("session count", "| Run sessions | %d |" % span["sessions"] in md)
check("binding symbol", "| Binding symbol | `%s`, inception %s |"
      % (span["binding_symbol"], span["binding_symbol_inception"]) in md)
check("union sessions", "| Development union sessions | %d |" % span["development_union_sessions"] in md)
check("empty gap lists rendered as none",
      span["members_missing_a_bar_at_run_start"] == [] and span["symbols_ending_before_run_end"] == []
      and "| Members missing a bar at run start | none |" in md)
check("recheck requirement stated", "refuses to run if any differs" in md)

# ---------------------------------------------------------------- rebalance
mc = cfg["rebalance"]["measured_counts"]
for freq in ("monthly", "quarterly"):
    check("%s count" % freq, "| `%s` | %d |" % (freq.upper(), mc[freq]) in md, str(mc[freq]))
    check("%s first three" % freq, ", ".join(mc["%s_first_three" % freq]) in md)
    check("%s last" % freq, mc["%s_last" % freq] in md)
check("carried-from digest pinned", mc["carried_from_sha256"] in md)

# ---------------------------------------------------------------- grid
grid = cfg["grid"]
check("grid size 18", grid["size"] == 18 and "| Grid size | 18 variants |" in md)
rows = [ln for ln in md.splitlines() if ln.startswith("| ") and "-ROTATION-RA1-L" in ln]
check("18 grid rows in md", len(rows) == 18, "found %d" % len(rows))
for v in grid["variants"]:
    vid = v["variant_id"]
    line = [ln for ln in rows if "`%s`" % vid in ln]
    if not line:
        check("grid row %s" % vid, False, "absent")
        continue
    cells = [c.strip() for c in line[0].strip().strip("|").split("|")]
    want = [str(v["index"]), "`%s`" % vid, str(v["lookback_months"]), str(v["top_k"]),
            v["rebalance_frequency"], v["target_weight_per_position"],
            gross[v["top_k"]], str(v["scheduled_rebalance_sessions"])]
    check("grid row %s" % vid, cells == want, "" if cells == want else "%s != %s" % (cells, want))
check("variant id format stated", grid["variant_id_format"] in md)
rpv = cfg["runs_per_variant"]
runs_row = "| Runs | %d per variant (%s) — %d total |" % (
    rpv["count"], ", ".join("`%s`" % l for l in rpv["labels"]), rpv["total_runs"])
check("runs per variant", runs_row in md and rpv["count"] * grid["size"] == rpv["total_runs"], runs_row)
check("scenario labels", all(l in md for l in rpv["labels"]))
hasflat("both runs gate", "The stressed cost model is not a sensitivity check that may be waived.")

# ---------------------------------------------------------------- RA2
ra = cfg["risk_architecture"]
comp = ra["components"]
check("RA2 id", ra["id"] == "RA2" and "`RA2`" in md)
check("RA2 frozen, not gridded",
      ra["frozen_before_any_variant_is_run"] is True and ra["not_part_of_the_grid"] is True
      and "None of them is an axis of the grid." in flat
      and "applied uniformly to all eighteen variants" in flat)
check("RA2-1 value 0.50", comp["RA2-1"]["value"] == "0.50" and "aggregate exposure ceiling, 0.50 of equity" in md)
check("AGGREGATE_RA2 clamp named", "AGGREGATE_RA2" in md and "AGGREGATE_RA2" in json.dumps(comp["RA2-1"]))
check("clamp order", "REQUESTED_BUDGET -> AGGREGATE_RA2 -> AGGREGATE -> CASH_FLOOR -> CONCENTRATION" in md)
check("RA2-2 value 0.10", comp["RA2-2"]["value"] == "0.10" and "0.10 annualized" in md)
check("RA2-2 measured on the equity curve",
      comp["RA2-2"]["measured_on"] == "THE_EQUITY_CURVE" and "**the equity curve**" in md)
check("RA2-2 window arithmetic", all(t in md for t in ("21", "20", "19", "sqrt(252)")))
check("RA2-3 value 0.08", comp["RA2-3"]["value"] == "0.08" and "0.08 from entry" in md)
check("RA2-3 reference", comp["RA2-3"]["reference_price"] == "cost_basis / quantity"
      and "`cost_basis / quantity`" in md)
# The Markdown states the stop in two lines -- it binds `reference` first, then uses it. Verify by
# substitution rather than by literal match, so the abbreviation is checked instead of assumed.
ref_line = re.search(r"^reference = (.+)$", md, re.M)
cond_line = re.search(r"^condition: (.+)$", md, re.M)
check("RA2-3 reference bound in md", ref_line is not None and cond_line is not None)
if ref_line and cond_line:
    expanded = cond_line.group(1).replace("reference", "(%s)" % ref_line.group(1).strip())
    check("RA2-3 condition expands to the sealed condition",
          expanded == comp["RA2-3"]["condition"],
          "%r vs %r" % (expanded, comp["RA2-3"]["condition"]))
    check("RA2-3 reference is the sealed reference",
          ref_line.group(1).strip() == comp["RA2-3"]["reference_price"])
check("RA2-5 value 10", comp["RA2-5"]["value"] == 10 and "10 trading sessions" in md)

bands = comp["RA2-4"]["bands"]
check("4 ladder bands", len(bands) == 4, "found %d" % len(bands))
for b in bands:
    check("ladder band %d scalar %s" % (b["band"], b["scalar"]), "| %s |" % b["scalar"] in md)
    check("ladder band %d bound %s" % (b["band"], b["dd_from"]), b["dd_from"].rstrip("0").rstrip(".") in md
          or b["dd_from"] in md)
check("boundary convention stated",
      "closed at its lower bound and open at its upper bound" in md)
check("combined scalar formula", "f(t) = f_vol(t) * f_ladder(t)" in md
      and "f(t) = f_vol(t) * f_ladder(t)" in ra["combined_scalar"]["formula"])
check("multiplicative not minimum", "**Multiplicative, not `min()`.**" in md)
check("state owned by engine subclass",
      "**Attempt 2 engine subclass** owns it" in md and "subclass" in json.dumps(ra["state_ownership"]).lower())

# the ladder provenance table, recomputed here rather than trusted
F_BASE = 0.50
G1 = {"1.00": "0.500000000", "0.50": "0.250000000", "0.25": "0.125000000"}
for b in bands:
    absolute = "%.9f" % (F_BASE * float(b["scalar"]))
    check("provenance row band %d absolute %s" % (b["band"], absolute), absolute in md)
    if b["scalar"] in G1:
        check("band %d reproduces Gen 1 f_cap" % b["band"], G1[b["scalar"]] == absolute,
              "%s vs %s" % (G1[b["scalar"]], absolute))

# ---------------------------------------------------------------- disclosure, verbatim
want_txt = cfg["adaptation_disclosure_verbatim"]
tail = md[md.index("### 14.1"):]
block = re.search(r"\n((?:> .*\n)+)", tail)
check("disclosure blockquote found", block is not None)
if block:
    got = " ".join(ln[2:].strip() for ln in block.group(1).strip().splitlines())
    check("disclosure byte-identical", got == want_txt,
          "" if got == want_txt else "got[%d] != want[%d]" % (len(got), len(want_txt)))
    check("disclosure keeps em dashes",
          want_txt.count("—") > 0 and got.count("—") == want_txt.count("—"),
          "em dashes=%d" % want_txt.count("—"))
carriage = cfg["adaptation_disclosure_carriage_requirement"]
check("carriage requirement names this md",
      "STAGE_3_G2_ROTATION_RA1_PROTOCOL.md" in json.dumps(carriage))

# ---------------------------------------------------------------- conflicts
conflicts = cfg["conflicts_found"]
check("17 conflicts in config", len(conflicts) == 17, "found %d" % len(conflicts))
for c in conflicts:
    check("conflict %s in md" % c["id"], c["id"] in md)
stray = set(re.findall(r"G2A2-CONFLICT-\d+", md)) - {c["id"] for c in conflicts}
check("no conflict id in md the config lacks", not stray, "stray: %s" % sorted(stray))
check("G2A2-CONFLICT-18 not claimed here", "G2A2-CONFLICT-18" not in md, "it lives in the criteria file")
tbl = [ln for ln in md.splitlines() if ln.startswith("| `G2A2-CONFLICT-")]
check("conflict table has 17 rows", len(tbl) == 17, "found %d" % len(tbl))

# ---------------------------------------------------------------- verdict tokens
toks = sorted({v for v in re.findall(r'"(STAGE_3_G2_ATTEMPT_2[A-Z_0-9]*)"',
                                     json.dumps(crit["verdict_token_derivation"]))})
check("two sealed tokens in criteria", len(toks) == 2, "%s" % toks)
for t in toks:
    has("token %s in md" % t, t)
check("prompt tokens not invented", "DEVELOPMENT_ADMISSIBILITY_MET" not in md)

# ---------------------------------------------------------------- selection rule
sel = cfg["representative_selection_rule"]
check("selection return-blind", sel["return_blind"] is True and "**Return-blind.**" in md)
check("selection frozen pre-run", sel["frozen_before_any_variant_is_run"] is True)
check("SELECTION_FIELD_NAMES named", "SELECTION_FIELD_NAMES" in md
      and "SELECTION_FIELD_NAMES" in json.dumps(sel))
check("3 selection steps", len(sel["steps"]) == 3, "found %d" % len(sel["steps"]))
check("both fail routes same token",
      sel["no_candidate_path"]["verdict"] == sel["second_fail_path"]["verdict"]
      and "The **same** token is emitted on both routes" in md)
check("no reselection", "not reselected" in md and "not reselected" in sel["no_reselection"])

# ---------------------------------------------------------------- multiplicity
mcd = cfg["multiple_comparisons_disclosure"]
for key, label in (("cumulative_variants_this_hypothesis_family", "Cumulative variants"),
                   ("cumulative_runs_this_hypothesis_family", "Cumulative runs")):
    check("multiplicity %s" % label, "| %s, this hypothesis family | %d |" % (label, mcd[key]) in md,
          str(mcd[key]))

# ---------------------------------------------------------------- structural consequences
sc = cfg["structural_consequences_declared_before_running"]
check("6 structural consequences", len(sc) == 6, "found %d" % len(sc))
for k in sc:
    check("%s in md" % k, "**%s " % k in md)

# ---------------------------------------------------------------- adversarial tests
ats = cfg["adversarial_test_requirements"]
ids = sorted(k for k in ats if k.startswith("AT-"))
check("AT-A..AT-I declared", ids == ["AT-%s" % c for c in "ABCDEFGHI"], "%s" % ids)
for i in ids:
    check("%s in md" % i, "| `%s` |" % i in md)
check("regression floor stated", "permanent regression floor" in md
      and "permanent regression floor" in ats["regression_floor"])

# ---------------------------------------------------------------- windows
dev = cfg["window"]["development"]
check("development window", "%s → %s" % (dev["from"], dev["to"]) in md)
check("development last session", dev["last_session"] in md)
for w in cfg["window"]["prohibited"]:
    check("prohibited window %s" % w["state"], "%s → %s" % (w["from"], w["to"]) in md
          and "`%s`" % w["state"] in md, "%s..%s" % (w["from"], w["to"]))
check("window guard imported unmodified", "imported **unmodified**" in md
      and "imported unmodified" in cfg["window"]["enforcement"])
check("2021-08-01 non-authorization", "**2021-08-01**" in md)

# ---------------------------------------------------------------- non-authorizations
na = cfg["explicit_non_authorizations"]
check("13 non-authorizations in config", len(na) == 13, "found %d" % len(na))
check("md has the section", "### 17.1 Explicit non-authorizations" in md)
bullets = md[md.index("### 17.1"):].count("\n- ")
check("md non-authorization bullets >= 13", bullets >= 13, "found %d" % bullets)

# ---------------------------------------------------------------- attempt 1 immutability
mods = cfg["attempt_1_modules_immutable"]["modules"]
check("9 immutable modules", len(mods) == 9, "found %d" % len(mods))
for m in mods:
    check("module %s in md" % m.split("/")[-1], "| `%s` |" % m in md)
check("md warns two are under backtest/", "live under\n`backtest/`, not\n`strategies/`" in md
      or ("`backtest/`, not" in md and "`strategies/`" in md))
check("attempt 1 verdict stands", "FAIL — STAGE_3_G2_NO_CANDIDATE" in md)
a1 = cfg["attempt_1_ref"]
check("attempt 1 disposition closed", a1["disposition"] == "CLOSED_READ_ONLY" and "closed, read-only" in md)
check("pinned not to be changed", "**detectable**, not so that any of them may be changed" in md)

# ---------------------------------------------------------------- digest hygiene
own = hashlib.sha256(MD.read_bytes()).hexdigest()
check("md does not contain its own digest", own not in md)
check("md does not carry a repo_state_id value",
      "repo_state_id" in md and not re.search(r"repo_state_id`?\s*[:=]\s*`?[0-9a-f]{64}", md))
hits = re.findall(r"\b[0-9a-f]{64}\b", md)
pinned: dict[str, str] = {}
for path in sorted(ROOT.rglob("*.*")):
    if path.is_file():
        try:
            pinned[hashlib.sha256(path.read_bytes()).hexdigest()] = path.relative_to(ROOT).as_posix()
        except OSError:
            pass
unresolved = [h for h in hits if h not in pinned]
check("every 64-hex string resolves to a file on disk", not unresolved,
      "hits=%d unresolved=%s" % (len(hits), unresolved))
for h in hits:
    print("       pinned %s... -> %s" % (h[:16], pinned.get(h, "?? UNRESOLVED")))

# ---------------------------------------------------------------- contamination
pred = cfg["declared_before_any_strategy_code_measurement"]
check("predicate content-based", pred["contamination_predicate"] == "CONTENT_BASED"
      and "The predicate is content-based, not path-based." in flat)


def norm_pred(s: str) -> str:
    """Strip the Markdown's code ticks and its trailing path slashes, collapse whitespace."""
    return re.sub(r"\s+", " ", s.replace("`", "").replace("/ ", " ")).strip().rstrip(".")


quoted = re.search(r"\n((?:> .*\n)+)", md[md.index("## 13."):])
check("predicate quoted as a blockquote", quoted is not None)
if quoted:
    got = " ".join(ln[2:].strip() for ln in quoted.group(1).strip().splitlines())
    check("quoted predicate equals the sealed predicate",
          norm_pred(got) == norm_pred(pred["predicate"]),
          "%r vs %r" % (norm_pred(got), norm_pred(pred["predicate"])))
    check("quoted predicate names this candidate", cfg["strategy_id"] in got)
check("sealer indirection disclosed",
      "would falsify the predicate if it hard-coded the candidate id" in flat
      and "sealer_indirection_note" in pred)
check("sealer loads the id from config, and says so",
      "loads `strategy_id` from `config/generation_2/g2_rotation_ra1_protocol.json` at run time" in flat)
check("paired immutability check stated",
      "It is paired with an immutability check: every module below is re-hashed at seal time and "
      "must equal its recorded digest." in flat
      and "paired_immutability_check" in pred)

print()
print("%d checks, %d failed" % (N, len(FAILED)))
if FAILED:
    print("FAILURES:")
    for f in FAILED:
        print("  - %s" % f)
else:
    print("ALL CHECKS PASSED")
