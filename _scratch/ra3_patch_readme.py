"""Apply the Attempt 3 updates to stockedge100/README.md.

Every figure written into the prose is asserted against its on-disk source before anything is
written: the Attempt 3 evidence record for gate and selection figures, the Attempt 3 protocol JSON
for seal-time counts, and the renderer's extracted scalar table for grid aggregates. A literal that
does not match refuses the patch. Every edit is located by a substring that must match exactly once.
"""
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path.cwd()
if not (ROOT / "governance").is_dir():
    sys.exit("wrong cwd: %s" % ROOT)

README = ROOT / "README.md"
EVP = ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json"
PROTO = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
TABLES = ROOT.parent / "_scratch/_ra3_tables.txt"
for p in (README, EVP, PROTO, TABLES):
    if not p.is_file():
        sys.exit("missing: %s" % p)

EM = chr(0x2014)      # em dash
MINUS = chr(0x2212)   # true minus sign
MID = chr(0xB7)       # middle dot, the separator the link list already uses
SECT = chr(0xA7)

FAILURES = []


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)


def bail(stage):
    if FAILURES:
        print("PATCH REFUSED (%s)" % stage)
        for f in FAILURES:
            print("  -", f)
        sys.exit(1)


EV = json.loads(EVP.read_text(encoding="utf-8"))
PR = json.loads(PROTO.read_text(encoding="utf-8"))

# ---- the scalar table the renderer emitted: NAME = VALUE lines under "### scalars" --------------
SCALARS = {}
in_scalars = False
for line in TABLES.read_text(encoding="utf-8").splitlines():
    if line.startswith("### "):
        in_scalars = line.strip() == "### scalars"
        continue
    if in_scalars and " = " in line:
        name, value = line.split(" = ", 1)
        SCALARS[name.strip()] = value.strip()
check(len(SCALARS) > 150, "only %d scalars parsed from the table" % len(SCALARS))
bail("scalar table")


def scalar(name, expected):
    got = SCALARS.get(name)
    check(got == expected, "scalar %s is %r on disk, the prose says %r" % (name, got, expected))


cr = EV["candidate_results"][0]
st = cr["stress_evaluation"]
conds = {c["id"]: c for c in cr["conditions"]}
sconds = {c["id"]: c for c in st["conditions"]}
sel = EV["selection"]
sc = sel["selected_score"]
lec = EV["ladder_engagement_comparison"]
mcd = EV["multiple_comparisons_disclosure"]
cm = PR["contamination_measurement"]
pmv = EV["prior_attempt_module_verification"]


def pct(raw, places=2):
    return str(round(Decimal(raw) * 100, places))


def dec(raw, places):
    return str(round(Decimal(raw), places))


# ---- every literal used below, bound to its source ---------------------------------------------
check(sel["selected_variant_id"] == "SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY",
      "the representative id in the prose is not the selected variant")
check(sel["result"]["selected_variant_id"] == sel["selected_variant_id"],
      "the selection result and the selection block name different variants")
check(sel["decided_at_step"] == 2, "SEL-2 did not decide at step 2")
check(sel["rule_id"] == "SE100-G2-SEL-2", "the selection rule id moved")
check(sel["return_blind"] is True, "the selection rule is not recorded as return-blind")
check(sel["result"]["eligible_count"] == 18 and sel["result"]["ineligible_variants"] == [],
      "the eligibility screen no longer admits all 18 variants")
check(sc["instability_score"] == "0.215471404", "the representative instability score moved")
check(sc["neighbour_count"] == 4, "the representative neighbour count moved")
check(sorted(sc["per_quantity_mean_dissimilarity"]) ==
      ["fill_count", "ladder_descents", "lockout_arms", "stops_filled"],
      "the four scored quantities moved")
runner = [n for n in sel["neighbour_scores"]
          if n["variant_id"] == "SE100-G2-S3-C3-ROTATION-RA3-L03-K1-QUARTERLY"]
check(len(runner) == 1, "the runner-up L03-K1-QUARTERLY is not among the neighbour scores")
if runner:
    check(runner[0]["instability_score"] == "0.215520012", "the runner-up score moved")
    margin = Decimal(runner[0]["instability_score"]) - Decimal(sc["instability_score"])
    check(str(margin) == "0.000048608", "the recomputed margin is %s" % margin)
    check(str(round(margin, 6)) == "0.000049", "the rounded margin is %s" % round(margin, 6))
scalar("SEL_MARGIN", "0.000048608")

check(pct(conds["S3-C1"]["measured"]) == "10.34", "base return is not 10.34%")
check(pct(sconds["S3-C1"]["measured"]) == "8.11", "stress return is not 8.11%")
check(dec(conds["S3-C2"]["measured"], 4) == "0.0994", "base drawdown is not 0.0994")
check(dec(sconds["S3-C2"]["measured"], 4) == "0.0993", "stress drawdown is not 0.0993")
check(dec(conds["S3-C3"]["measured"], 4) == "1.2704", "base profit factor is not 1.2704")
check(dec(sconds["S3-C3"]["measured"], 4) == "1.2005", "stress profit factor is not 1.2005")
check(conds["S3-C4"]["measured"] == "62", "closed trades is not 62")
check(conds["S3-C5"]["verdict"] == "MET", "S3-C5 is not MET on base")
check(dec(conds["S3-C6"]["measured"], 4) == "0.7505", "base concentration is not 0.7505")
check(dec(sconds["S3-C6"]["measured"], 4) == "0.9772", "stress concentration is not 0.9772")
check(pct(conds["S3-C6"]["measured"]) == "75.05", "base concentration is not 75.05%")
check(pct(sconds["S3-C6"]["measured"]) == "97.72", "stress concentration is not 97.72%")
check(conds["S3-C6"]["threshold"] == "<= 0.50", "the S3-C6 threshold moved")
check((cr["conditions_met"], cr["conditions_not_met"]) == (6, ["S3-C6"]),
      "the base tally is not 6 met with S3-C6 the only miss")
check((st["conditions_met"], st["conditions_not_met"]) == (6, ["S3-C6"]),
      "the stress tally is not 6 met with S3-C6 the only miss")
check(cr["admitted"] is False and EV["stage_verdict"]["admitted_candidates"] == [],
      "the candidate is recorded as admitted")
check(EV["stage_verdict"]["verdict_token"] == "STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE",
      "the verdict token moved")
check(cr["admission_basis"]["permissive_base_only_reading_would_give"] is False,
      "the permissive base-only reading no longer fails")
check(cr["admission_basis"]["conflict_ref"] == "G2A2-CONFLICT-25", "the inherited conflict ref moved")

for stat, a3, a2 in (("ladder_descents", 1008, 1605), ("lockout_recoveries_blocked", 3719, 6133)):
    e = lec["per_statistic"][stat]
    check((e["attempt_3_total"], e["attempt_2_total"]) == (a3, a2),
          "%s is %s/%s on disk, the prose says %d/%d"
          % (stat, e["attempt_3_total"], e["attempt_2_total"], a3, a2))
    check(e["runs_differing"] == 36, "%s differs on %d runs, not 36" % (stat, e["runs_differing"]))
fs = lec["sessions_at_full_sizing"]
check((fs["attempt_3_total"], fs["attempt_2_total"]) == (53671, 36886),
      "sessions at full sizing moved")
check(lec["runs_compared"] == 36, "the compared run count is not 36")
check(lec["runs_identical_on_every_compared_statistic"] == [],
      "some run is identical on every compared statistic")

check(mcd["cumulative_variants_this_hypothesis_family"] == 54, "cumulative variants is not 54")
check(mcd["cumulative_runs_this_hypothesis_family"] == 108, "cumulative runs is not 108")
check(len(EV["adaptation_disclosure_verbatim"]) == 1507, "the disclosure is not 1507 characters")

check(cm["python_files_scanned"] == 106, "the scanned file count is not 106")
check(cm["contamination_predicate"] == "CONTENT_BASED", "the predicate kind moved")
check(cm["predicate"].endswith("SE100-G2-S3-C3-ROTATION-RA3 at seal time."),
      "the content predicate string moved")
check(cm["sealer_names_the_candidate"] is False, "the sealer now names the candidate")
check(cm["prior_attempt_module_count"] == 17, "the prior module count is not 17")
check(cm["prior_attempt_modules_that_moved"] == [], "a prior attempt module moved")
check((pmv["attempt_1_module_count"], pmv["attempt_2_module_count"]) == (9, 8),
      "the 9 + 8 module split moved")
check(pmv["module_count"] == 17 and pmv["modules_that_moved"] == [],
      "the re-hash verification no longer reports 17 modules unmoved")
check(pmv["conflict_ref"] == "G2A3-CONFLICT-34", "the module-count conflict ref moved")

for name, value in (("A3_DD_MAX_PCT", "14.13%"), ("A3_DD_MAX_STRESS_PCT", "14.36%"),
                    ("A2_DD_MAX_PCT", "13.97%"), ("A3_POS_BASE", "18"),
                    ("REP_SYMBOLS", "24"), ("REP_TRADES", "62"), ("REP_SCORE", "0.215471404"),
                    ("GROSS_MIN_PCT", "51.10%"), ("GROSS_MAX_PCT", "51.84%"),
                    ("GROSS_EXCESS_MIN_PCT", "1.10%"), ("GROSS_EXCESS_MAX_PCT", "1.84%"),
                    ("A2_C6_BASE", "2.7176"), ("A2_C6_STRESS", "6.8824"),
                    ("A2_REP_NOT_SATISFIED_COUNT", "3"),
                    ("A3_LOWEST_TURNOVER_VARIANT", "L12-K1-QUARTERLY"),
                    ("A3_LOWEST_TURNOVER_RET_PCT", "+1.48%"),
                    ("A3_REP_RANK_BY_RETURN", "11"), ("A3_REP_IS_WORST", "false"),
                    ("A2_REP_RANK_BY_RETURN", "18"), ("A2_REP_IS_WORST", "true")):
    scalar(name, value)
check(len(SCALARS["A2_STRESS_NOT_SATISFIED"].split(",")) == 4,
      "attempt 2 did not miss four conditions on stress")
bail("figure verification")

# ------------------------------------------------------------------------------------------------
original = README.read_bytes()
if b"\r\n" in original:
    sys.exit("README.md already carries CRLF; refusing to patch")
text = original.decode("utf-8")
if "RA3" in text or "attempt 3" in text:
    sys.exit("README.md already refers to Attempt 3; refusing to patch twice")
trailing_newline = text.endswith("\n")
LINES = text.split("\n")
BEFORE = len(LINES)


def locate(needle):
    hits = [i for i, ln in enumerate(LINES) if needle in ln]
    if len(hits) != 1:
        print("PATCH REFUSED (anchor)")
        print("  - %r matched %d lines, expected 1" % (needle, len(hits)))
        sys.exit(1)
    return hits[0]


def sub(needle, old, new):
    """Replace `old` with `new` inside the single line found by `needle`."""
    i = locate(needle)
    if LINES[i].count(old) != 1:
        print("PATCH REFUSED (inline)")
        print("  - %r occurs %d times in L%d" % (old, LINES[i].count(old), i + 1))
        sys.exit(1)
    LINES[i] = LINES[i].replace(old, new, 1)


def replace_line(needle, new_lines):
    i = locate(needle)
    LINES[i:i + 1] = new_lines


def insert_after(needle, new_lines):
    i = locate(needle)
    LINES[i + 1:i + 1] = new_lines


def insert_before(needle, new_lines):
    i = locate(needle)
    LINES[i:i] = new_lines


# ---- E1: the generation heading ----------------------------------------------------------------
sub("open, and failing at Gate 3 at both attempts", "at both attempts", "at all three attempts")

# ---- E2: the attempt 3 gate row -----------------------------------------------------------------
insert_after("STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE`)", [
    "| Gate 3 attempt 3 " + EM + " development admissibility | **FAILED** (`FAIL " + EM + " "
    "STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE`), by a third route: the representative traded, survived, "
    "returned, and still missed one condition. The same 18-variant grid under **RA3** " + EM + " RA2 "
    "with the " + MINUS + "5% de-risk rung removed, reverting to Generation 1's original 8/10% ladder "
    + EM + " again recorded **zero** research shutdowns across all 36 runs, and a new return-blind "
    "rule (`SE100-G2-SEL-2`, neighbourhood stability across four non-return risk statistics) selected "
    "`SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY`. It satisfies **six of the seven** conditions on "
    "**both** runs " + EM + " +10.34% base and +8.11% stressed total return, 0.0994 and 0.0993 maximum "
    "drawdown, 1.2704 and 1.2005 profit factor, 62 closed trades " + EM + " and fails **`S3-C6`**: its "
    "largest single contributor supplies **0.7505** of total profit on base and **0.9772** on stress, "
    "against a 0.50 ceiling. `admissible_candidate_exists` is `NOT_MET`, and the permissive base-only "
    "reading fails on the same condition. |",
])

# ---- E3: the next-authorized-stage row ----------------------------------------------------------
replace_line("| Next authorized stage | **None.** Human review of the attempt 2 package.", [
    "| Next authorized stage | **None.** Human review of the attempt 3 package. Stage 4 has nothing "
    "to validate and is not authorized. Any further Generation 2 work restarts at Gate 3 with a "
    "**new** pre-registration and a **further disclosed adaptation** " + EM + " a fourth on one "
    "hypothesis family, whose cumulative multiplicity is already 54 variants across 108 runs. No grid "
    "may be loosened, re-run, or have a nineteenth variant appended to it; no runner-up or "
    "better-returning variant from any of the three attempts may be re-selected on return; and the "
    "two attempt 3 changes may not be separated after the fact by running RA3 without SEL-2 or SEL-2 "
    "without RA3. |",
])

# ---- E4: the link list --------------------------------------------------------------------------
replace_line("STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md).", [
    "[Stage 3 attempt 2 research](governance/generation_2/STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md) "
    + MID,
    "[Stage 3 attempt 3 pre-registration](governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md) "
    + MID,
    "[Stage 3 attempt 3 research](governance/generation_2/STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md).",
])

# ---- E5: the narrative pair ---------------------------------------------------------------------
insert_before("**No expected income, profit, or return is claimed", [
    "**Generation 2 attempt 3** was pre-registered after **both** prior attempts' results were known,",
    "and its 1507-character adaptation disclosure " + EM + " sealed in the protocol and carried verbatim in",
    "the report, the decision record, and every reference to the result " + EM + " says so and names what that",
    "costs. It changes two things, both chosen from non-return diagnostics only: the de-risk ladder loses",
    "the " + MINUS + "5% rung attempt 2 had added beyond Generation 1's own architecture, reverting to 8/10%",
    "spacing (**RA3**), and the representative is chosen by neighbourhood stability across `fill_count`,",
    "`ladder_descents`, `lockout_arms` and `stops_filled` rather than by raw turnover",
    "(**`SE100-G2-SEL-2`**). Both changes are visible in the throttle statistics. Across the same 36 runs",
    "the ladder descended **1008** times against attempt 2's **1605**, blocked re-entries fell from",
    "**6133** to **3719**, and sessions at full sizing rose from **36886** to **53671** " + EM + " every one of",
    "the 36 runs differing on each. All **18** variants stayed positive under base costs, and none shut",
    "down.",
    "",
    "**It failed anyway, on the one condition attempt 2 missed most severely.**",
    "`SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY` was selected at step 2 " + EM + " instability score",
    "**0.215471404** over four neighbours, with return read nowhere " + EM + " and it trades: **62** closed",
    "episodes over **24** distinct symbols, **+10.34%** base and **+8.11%** stressed total return, a",
    "**1.2704** profit factor, a **0.0994** maximum drawdown, and positive return after its single best",
    "trade is removed. Six of the seven hard conditions are satisfied on **both** runs. The seventh is",
    "concentration: the largest single contributor supplies **75.05%** of gross profit on the base run",
    "and **97.72%** on the stressed run, against a 50% ceiling. That condition is a concentration test,",
    "and a `k`-of-34 rotation that spends much of thirteen years in a few persistent leaders is",
    "structurally exposed to it. Attempt 2's representative missed the same condition far more severely",
    EM + " **2.7176** and **6.8824** as ratios against the same ceiling " + EM + " while also missing three other",
    "conditions on base and four on stress. That attempt 3 misses only this one narrows the failure mode",
    "and does not change the verdict, because the gate is conjunctive, and it is recorded as a fail.",
    "Two limits travel with the result. The selection margin over the runner-up is **0.000049**, so the",
    "rule was close to indifferent at the top of its own ranking. And attempt 2's rule, applied to this",
    "grid, would have picked the `L12-K1-QUARTERLY` axes again at **+1.48%**; SEL-2 instead picked a",
    "variant ranked **eleventh of eighteen** by return, where attempt 2's representative ranked",
    "**eighteenth of eighteen**. That is recorded because the cost of a return-blind rule should be",
    "visible, and **re-selecting on return remains forbidden**, in this session or any later one.",
    "",
])

# ---- E6: the pre-registration ordering section --------------------------------------------------
sub("seals its partition and each of its two rotation pre-registrations",
    "each of its two rotation", "each of its three rotation")

insert_after("sha256sum -c reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.sha256", [
    "sha256sum -c governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256",
    "sha256sum -c reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.sha256",
])

insert_before("One asymmetry is worth knowing before verifying anything", [
    "The attempt 3 protocol carries that content-based form unchanged: no `.py` file under",
    "`src/stockedge100` or `tests` contained the string `SE100-G2-S3-C3-ROTATION-RA3` at seal time,",
    "across **106** scanned files " + EM + " the sealer included, since it too loads the id from `config/` at",
    "run time. What attempt 3 widens is the immutability half. **Seventeen** modules are re-hashed rather",
    "than nine " + EM + " attempt 1's nine and attempt 2's eight " + EM + " against the digests each attempt's own run",
    "record wrote, both at seal time and again after this session's work; none moved. The operating",
    "instruction for the attempt implied nine modules and the sealed figure is seventeen, which is",
    "disclosed as `G2A3-CONFLICT-34` rather than resolved by trusting the instruction.",
    "",
])

sub("The Generation 2 governance artifacts are covered by the five records",
    "covered by the five records", "covered by the seven records")

# ---- E7: known limitations -----------------------------------------------------------------------
sub("sets now, and all of them travel with every downstream result", "Nine sets now", "Ten sets now")

replace_line(SECT + "17. An engine cannot be more trustworthy than its inputs", [
    SECT + "17. Selection-rule and ladder limitations settled at its Stage 3 attempt 3 " + EM + " all thirteen in",
    "[STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md](governance/generation_2/STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md)",
    SECT + "17. An engine cannot be more trustworthy than its inputs, and a research result cannot be more",
])

i = locate("minimum of 189 fills. Step 3, the lexicographic tiebreak")
tail = "  attempt and is covered only by unit tests on synthetic inputs."
if LINES[i + 1] != tail:
    print("PATCH REFUSED (bullet)")
    print("  - L%d is %r, expected %r" % (i + 2, LINES[i + 1], tail))
    sys.exit(1)
LINES[i:i + 2] = [
    "  minimum of 189 fills. Attempt 3 replaced that step with a neighbourhood-stability score and moved",
    "  turnover down to step 3, and step 2 decided outright again " + EM + " by **0.000049**. The turnover and",
    "  lexicographic tiebreaks have therefore still never run on real data in any of the three attempts,",
    "  and are covered only by unit tests on synthetic inputs.",
]

# the anchor is the bullet's LAST line; the sentence it completes is wrapped on the line above and
# must not be restated here
replace_line("intervened less has an advantage in step 2 that is not purely signal turnover.", [
    "  intervened less has an advantage in step 2 that is not purely signal turnover.",
    "  Attempt 3 measures the same deviation under RA3: every variant exceeds the ceiling on at least one",
    "  session, by **1.10%** to **1.84%** of equity (**51.10%** to **51.84%** gross), one session at a",
    "  time. The mechanism is the fill-open enforcement, not the ladder that changed, so removing a rung",
    "  could not have fixed it.",
    "- **Attempt 3's representative trades, survives, returns " + EM + " and still fails.** RA3 removed one ladder",
    "  rung and `SE100-G2-SEL-2` selected on neighbourhood stability instead of raw turnover. The result is",
    "  a representative that closes **62** trades over **24** symbols for **+10.34%** base and **+8.11%**",
    "  stressed return, at a **0.0994** drawdown and a **1.2704** profit factor, satisfying **six of seven**",
    "  conditions on both runs. It fails `S3-C6`: the largest single contributor supplies **75.05%** of",
    "  gross profit on base and **97.72%** on stress, against a 50% ceiling. A `k`-of-34 rotation that",
    "  spends much of thirteen years in a few persistent leaders is structurally exposed to a",
    "  concentration test. Attempt 2 missed the same condition far more severely, at **2.7176** and",
    "  **6.8824**, and missed three others with it on base and four on stress; that attempt 3 misses only",
    "  this one narrows the failure mode without changing the verdict, because the gate is conjunctive.",
    "- **The attempt 3 selection margin is 0.000049, and the rule cannot be separated from the ladder.**",
    "  The representative's instability score is **0.215471404** against the runner-up's **0.215520012** "
    + EM + "",
    "  about one part in four thousand, between two variants adjacent on the `k` axis. A different",
    "  dissimilarity denominator, or a different choice among the four scored quantities, could reverse",
    "  the order. RA3 and SEL-2 also changed in the same attempt: their effects move in separable",
    "  *directions*, which is an argument from where each mechanism can act, not a controlled comparison.",
    "  No run exists with one change alone, and making one is not authorized.",
    "- **Removing a ladder rung did not raise drawdown, and that does not show the rung was useless.** The",
    "  attempt 3 pre-registration declared that dropping the " + MINUS + "5% tier would put the drawdown condition",
    "  under more pressure and move the research shutdown closer. Neither happened: the deepest drawdown",
    "  anywhere in the grid was **14.36%** on a stressed run and **14.13%** on base, against attempt 2's",
    "  **13.97%** base worst, and no variant shut down " + EM + " essentially unchanged, while the ladder",
    "  descended **1008** times rather than **1605** and sessions at full sizing rose from **36886** to",
    "  **53671**. That is consistent with the rung having suppressed return without buying protection, and",
    "  equally consistent with a thirteen-year window that never contained the event the rung was for.",
    "  This attempt cannot distinguish the two, and no run that would is authorized. `G2A3-CONFLICT-29`.",
    "- **Cumulative multiplicity across this family is 54 variants and 108 runs, and they are not 54",
    "  independent tests.** Attempt 2's risk architecture was chosen after seeing where attempt 1 broke,",
    "  and attempt 3's ladder change and selection rule after seeing how attempt 2 behaved. The effective",
    "  number of researcher degrees of freedom is larger than 54 and grows faster than the variant count.",
    "  It is not quantified, because any quantification would itself be a choice made after the fact. No",
    "  multiplicity correction is applied to the thresholds either: they are constitutional, and may not",
    "  be altered by a stage that would benefit from altering them.",
])

# ---- post-conditions ----------------------------------------------------------------------------
patched = "\n".join(LINES)
check("at all three attempts" in patched, "the heading was not updated")
check("STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE" in patched, "the verdict token is absent")
check(patched.count("STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md") == 3,
      "the research report is named %d times, expected 3"
      % patched.count("STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md"))
check(patched.count("STAGE_3_G2_ROTATION_RA3_PROTOCOL") == 2,
      "the protocol is named %d times, expected 2" % patched.count("STAGE_3_G2_ROTATION_RA3_PROTOCOL"))
check("STAGE_3_G2_A3_ROTATION_RESEARCH.sha256" in patched, "the attempt 3 decision record is unverified")
check("Nine sets now" not in patched, "the old limitation count survived")
check("covered by the five records" not in patched, "the five-record claim survived")
check("failing at Gate 3 at both attempts" not in patched, "the old heading survived")
check("Human review of the attempt 2 package" not in patched, "the old next-stage row survived")
check("Step 3, the lexicographic tiebreak, has still never run" not in patched,
      "the superseded selection-rule sentence survived")
check(chr(13) not in patched, "the patched text carries a carriage return")
# No attempt 3 artifact may emit a prior attempt's verdict token. README.md is not an attempt 3
# artifact -- it is the standing project index, and it already carried attempt 1's and attempt 2's
# tokens in their own gate rows before this session. Deleting those would rewrite the prior
# attempts' record, which is forbidden. So the requirement here is that the patch introduces no
# NEW occurrence of any withheld token.
for tok in EV["stage_verdict"]["prior_attempt_tokens_withheld"]:
    check(patched.count(tok) == text.count(tok),
          "the patch changed the occurrence count of the withheld prior token %s from %d to %d"
          % (tok, text.count(tok), patched.count(tok)))
check(EV["stage_verdict"]["pass_token"] not in patched, "the patched README emits this gate's pass token")
bail("post-conditions")

if trailing_newline and not patched.endswith("\n"):
    patched += "\n"
README.write_text(patched, encoding="utf-8", newline="\n")
after = README.read_bytes()
if b"\r\n" in after:
    sys.exit("the written README carries CRLF")
print("patched README.md")
print("  bytes %d -> %d" % (len(original), len(after)))
print("  lines %d -> %d" % (BEFORE, len(LINES)))
