# Stage 3 Attempt 2 — design-session decision report

| Field | Value |
| --- | --- |
| Document id | `SE100-GOV-3001` |
| Project | StockEdge100 |
| Stage | Prompt stage 3, second attempt — constitutional gate 3 (development admissibility) |
| Session type | Design and pre-registration only. No strategy implementation, no evaluation. |
| Governing document | `SE100-GOV-0001` — `governance/STAGE_0_CONSTITUTION.md`, FROZEN, v1.0.0 |
| Pre-registration sealed | `SE100-GOV-0007` — `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.{md,json}`, sealed `2026-08-10T11:59:33Z` |
| Attempt 1 record | `SE100-GOV-0006` — `FAIL — STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT`, run `SE100-R-20260810T101622Z`. Unmodified. |
| Evidence | `config/stage3_attempt2_strategy_protocol.json` (`SE100-CFG-3003`), `config/stage3_attempt2_gate_criteria_binding.json` (`SE100-CFG-3004`) |
| Authored (UTC) | 2026-08-10T12:30:44Z |
| Verdict | `PASS — STAGE_3_ATTEMPT_2_PREREGISTRATION_FROZEN` |
| Gate 3 passed | **No.** Gate 3 was not evaluated in this session and no candidate was implemented. |
| `live_trading_authorized` | `false` |

The `run_id` of this design session and the repository-state digest are deliberately **not** written
into this file. `repo_state_id` is computed over `governance/*.md` among other patterns, so writing a
tree digest here would invalidate it on write. Both values live in
`reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.json` and in the append-only `runs/` record for
this session, which are outside the digest's patterns. Individual **file** digests are quoted below,
because a file digest is not a digest of the tree that contains this file.

---

## 1. What this session was for, and what it was not

Attempt 1 of prompt stage 3 evaluated six pre-registered candidates and admitted none. All six
breached the frozen 15% maximum-drawdown ceiling. The gate was not passed, stage 4 stayed locked, the
holdout stayed sealed, and Attempt 1's decision record set
`next_authorized_stage = NONE_ON_THE_CURRENT_LINE_OF_WORK`.

This session did exactly one thing: it designed a new candidate set, wrote the specification down in
full, and sealed it before any code for it existed. It did not implement a strategy, run a backtest,
run a simulation, run a parameter sweep, compute a performance number, load a market observation for
performance analysis, read a validation-period result, or touch the holdout. Nothing in this report
states how any Attempt 2 candidate performs, because nothing in this session could find out.

The purpose is not to rescue Attempt 1. Attempt 1 is closed, on disk, byte-for-byte unchanged, and
cited rather than recycled — constitution §2: "Negative results are deliverables. Rejected
strategies are recorded and not silently recycled."

## 2. Integrity verification performed before anything was written

Every check below is read-only and was run before the first Attempt 2 artifact was authored. Freeze
records that use bare filenames were verified from `stockedge100/governance/`; records that use
project-root-relative paths were verified from `stockedge100/`. Running them from the wrong working
directory is an operator error, not an integrity failure, so the directory is recorded with each.

| Record | Verify from | Entries | Result |
| --- | --- | ---: | --- |
| `governance/STAGE_0_FREEZE.sha256` | `governance/` | 2 | all OK |
| `governance/STAGE_1_FREEZE.sha256` | `governance/` | 2 | all OK |
| `governance/STAGE_1_PREREGISTRATION.sha256` | project root | 4 | all OK |
| `governance/STAGE_2_PREREGISTRATION.sha256` | project root | 4 | all OK |
| `governance/STAGE_3_PREREGISTRATION.sha256` | project root | 4 | all OK |
| `reports/stage0/STAGE_0_VERIFICATION.sha256` | project root | 8 | all OK |
| `reports/stage1/STAGE_1_DATA_READINESS.sha256` | project root | 19 | all OK |
| `reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256` | project root | 20 | all OK |
| `reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256` | project root | 26 | all OK |
| `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256` | project root | 4 | all OK (written by this session) |

Both halves of the frozen Stage 0 constitution were verified, human-readable and machine-readable:
`STAGE_0_CONSTITUTION.md` `b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5` and
`STAGE_0_CONSTITUTION.json` `af45fda6b37bed50768d5f3d01d4a91175da93e708c9daf1b630e35a981e2ff5`,
recorded digest equal to computed digest in both cases. The machine-readable counterpart was read as
well as the prose one, because the gate table it carries is what settles whether a second attempt
needs human approval (§3 below).

The repository-state digest was recomputed by the project's canonical method —
`tree_digest(hash_tree(root, REPO_STATE_PATTERNS))` from `reporting/stage_package.py` — and matched
the value recorded in Attempt 1's run record `runs/SE100-R-20260810T101622Z.json` before this session
wrote anything. Both the starting value and the value at the moment this session's package was built
are recorded in the `runs/` records, not here.

`governance/STAGE_1_HOLDOUT_LOCK.json` was read for integrity metadata only. It carries
`status: LOCKED` and `holdout_state: SEALED` and has no separate validation-state field, so the
validation window's `LOCKED` state rests on its binding rule — "No parameter, threshold, symbol, or
rule may be chosen using any value inside the validation or holdout windows" — which
`SE100-CFG-3004` restates as `windows.validation = "LOCKED"`. The boundary dates were deliberately
not restated in any Attempt 2 artifact, which binds the lock by digest
(`9696161c4c5612fc7f6b3e5a3410917f20ad5707cb9b89b8bcc39cb70831dfb3`) and reads the bounds at run
time instead. No holdout observation was read.

**No frozen artifact was modified, regenerated, replaced, or reformatted.** Attempt 1's protocol
`config/stage3_strategy_protocol.json` (`SE100-CFG-3001`,
`04dbe3fa8c6b2a9e725a66d24f5dc0a3a7e3567e70d38bfd2e96869cc6e169b6`) contains non-ASCII em dashes,
and `SE100-CFG-3002` carries a damaged non-ASCII byte inside
`verdict_token_derivation.fail_is_a_deliverable`. Both are frozen and neither is repaired, corrected,
reformatted, or re-encoded by this attempt; where `SE100-CFG-3004` quotes the damaged field it
describes the byte rather than reproducing it. Attempt 2's own JSON artifacts declare
`"encoding": "UTF-8, ASCII-only characters"` and are ASCII-only in fact, so no comparable ambiguity
is introduced. The claim is about the JSON, not about prose: this report and the pre-registration
Markdown carry the same em dashes and section signs every governance report in this project uses.

## 3. Whether a second attempt is permitted at all

The operating prompt for this session was **not** treated as authority for this question.
`SE100-CFG-3003` records the determination, the answer, and eight items of on-disk evidence; the
finding is:

> Yes, by a new pre-registration declaring new candidates, sealed before any code for them exists. No
> erratum, no new project generation, and no separate human written approval is required at this gate.

The load-bearing evidence, in descending order of directness:

1. **Constitution §11, line 293** — "Safety thresholds may be tightened without promoting a failed
   strategy, but the change must still be versioned." Attempt 2 tightens safety and promotes no
   failed strategy: F1–F6 are not re-run, not edited, not superseded, not carried forward. The
   versioning requirement is met by a new artifact id at version 1.0.0 rather than by an edit to
   `SE100-CFG-3001`.
2. **Constitution §11, lines 290–291** — "A change that affects universe, timing, cost, signal,
   parameter range, metric, threshold, or data partition is material." and "A material change after
   seeing validation results creates a new candidate and restarts at Gate 3." A new candidate
   restarting at gate 3 is the mechanism Attempt 2 uses. The scope gap is stated rather than glossed:
   the second sentence's trigger is *validation* results, and Attempt 1's results are
   development-only, so the clause does not literally cover this case. It is relied on a fortiori —
   if a material change made after seeing the more strongly protected validation results costs no
   more than restarting at gate 3, a change made after seeing only development results cannot require
   more. The silence is not read as permission for anything beyond restarting at gate 3.
3. **`STAGE_0_CONSTITUTION.json`**, gates entry id 3, carries a `fail_result` and **no** once-only
   clause, **no** attempt limit, and **no** `manual_written_approval_required` flag. The only gate
   carrying `manual_written_approval_required: true` is gate 9.
4. **Attempt 1's own report**, `STAGE_3_STRATEGY_RESEARCH_REPORT.md` §19 — "A further attempt at Gate
   3 requires a new pre-registration declaring new candidates, sealed before any code for them
   exists, under the same prohibition on revising a specification because of a result it produced."
   And §15 — "A future generation of candidates is a new pre-registration and a new Gate 3, not an
   amendment to this one."
5. **`STAGE_3_PREREGISTRATION.md` §7.8** bars a seventh candidate "in this session". That bar is
   scoped to the Attempt 1 session. Attempt 2 does not add a seventh candidate to Attempt 1's set; it
   declares a new set under a new pre-registration.

Constitution §2's "No result-driven rule changes. A failed gate cannot be weakened after results are
observed." is satisfied because no gate 3 condition, threshold, denominator, predicate, boundary, or
measurement is changed by this attempt. **No frozen rule was reinterpreted or weakened to permit
Attempt 2.**

Four interpretations were nevertheless required, and each is recorded in `SE100-CFG-3003` with the
frozen text it interprets, the rejected alternative reading, and what it leaves unchanged:

| Id | Subject | Effect |
| --- | --- | --- |
| `A2-INTERP-1` | Attempt 1's sealed `sizing_rule` — "No candidate sizes by volatility … position size is not a research variable in this stage." | Scoped to Attempt 1's six candidates. The broader reading — that no gate 3 candidate may ever size by volatility — is recorded and rejected: it would read a sentence in a candidate-set config as an amendment to the constitution, which §1 precedence does not permit. The constitutional 95% gross / 5% cash ceiling is unchanged, and Attempt 2 requests **less**. Direction of change: downward only. |
| `A2-INTERP-2` | S3-C7 names `SE100-CFG-3001` as the artifact declaring the neighbours. | For Attempt 2 candidates the declaring artifact is `SE100-CFG-3003`. Nothing else changes: still exactly four neighbours, declared before any result, same window, same base costs, shutdown enforced, sign of net return only. |
| `A2-INTERP-3` | S3-C6's `applies_to` enumeration names two Attempt 1 ids. | The **rule** is "candidates whose declared universe contains more than one instrument". Applying it to Attempt 2's set yields exactly one candidate, `SE100-S3A2-C3-DEFENSIVE-RA1`. The enumeration is re-derived by the sealed rule, not replaced. |
| `A2-INTERP-4` | S3-C4's lower-frequency exception. | Not invoked by any Attempt 2 candidate. The 30-closed-trade floor applies unchanged to all three. Invoking it now, after Attempt 1's per-candidate trade counts are known, "would be the precise move the sealed note exists to forbid." |

The constitution does **not** require all six families again. §3's scope table reads that the six
families "may be researched separately" — permissive, not mandatory — and §8's "Strategy families
must first be tested independently" is a precondition on *combining*, whose own next sentence is
"Combining strategies is prohibited until each component has an independent verdict." Attempt 2
combines nothing.

## 4. What Attempt 1 established, and the only numbers carried forward

Attempt 1's headline fact, quoted from `SE100-CFG-3003`:

> All six candidates produced positive after-cost total return and all six passed neighbour sign
> stability, and all six breached the 15% maximum-drawdown ceiling of S3-C2. Three additionally
> missed the 30-closed-trade floor of S3-C4, two failed the profit-concentration condition S3-C6, and
> one failed the best-trade-removal condition S3-C5.

The design carried forward exactly one quantitative input beyond that qualitative fact: the six
per-candidate closed-trade counts (F1 15, F2 141, F3 109, F4 13, F5 6, F6 48). They were used for one
purpose — excluding families whose specification form cannot plausibly reach 30 closed round trips —
and for nothing else. `SE100-CFG-3003` records the restriction explicitly: no return, drawdown,
profit factor, equity path, or trade-level outcome from Attempt 1 informed any Attempt 2 parameter,
threshold, lookback, or rule.

The most useful thing Attempt 1 produced was not a number. Its report observed that under S3-C2 the
risk control and the quality gate are the same number, and handed that observation forward to
"whoever writes the next pre-registration". Attempt 2's design target follows from it directly:
**never tripping the §5.1 research shutdown is the design target, not a side effect.** S3-C2 is
satisfied if and only if that shutdown never fires — same 15%, same session-close equity series,
sealed action `LIQUIDATE_AT_NEXT_OPEN_AND_BLOCK_ENTRIES`.

## 5. The research question

> Can structurally lower-risk, economically intelligible strategies remain meaningfully profitable
> after costs while satisfying the unchanged 15% maximum-drawdown ceiling of Gate 3 and every other
> frozen Gate 3 condition?

Both halves matter. A structure that never breaches the ceiling and never makes money fails S3-C1 and
S3-C3, and `SE100-CFG-3003` records that as "a real and anticipated way for Attempt 2 to fail."

## 6. Three candidates, not six

The declared set is the smallest that can answer the question while keeping S3-C6 live for at least
one candidate.

| Candidate id | Family | Universe | Signal form shared with |
| --- | --- | --- | --- |
| `SE100-S3A2-C1-PULLBACK-RA1` | pullback | SPY | `SE100-S3-F2-PULLBACK-SMA200-SMA10` (rejected) |
| `SE100-S3A2-C2-MEANREV-RA1` | mean reversion | SPY | `SE100-S3-F3-MEANREV-RSI2` (rejected) |
| `SE100-S3A2-C3-DEFENSIVE-RA1` | defensive regime logic | SPY, SHY | `SE100-S3-F6-DEFENSIVE-SMA200-SHY` (rejected) |

Three families were excluded prospectively, by one rule applied consistently: a family is excluded if
its specification **form** cannot plausibly produce the 30 closed round trips S3-C4 requires. Trade
frequency is a structural property of a rule, not a performance result.

| Excluded family | Attempt 1 reference | Prospective reason |
| --- | --- | --- |
| trend/momentum | `SE100-S3-F1-TREND-SMA200`, 15 closed trades | A single 200-session moving-average crossing rule changes state a small number of times per decade by construction. RA1-3 and RA1-4 would add exits, but the form starts roughly half the required count short and the added exits are themselves what RA1-6 then delays. |
| breakout | `SE100-S3-F4-BREAKOUT-DONCHIAN-50-25`, 13 closed trades | A 50-session closing-high entry with a 25-session closing-low exit is a low-frequency channel rule. Same argument, and S3-C4's lower-frequency exception is not invoked. |
| ETF rotation | `SE100-S3-F5-ROTATION-DUALMOM`, 6 closed trades | A monthly top-one rotation over four broad ETFs changes selection rarely. RA1-4 at a one-year horizon would convert a multi-year hold into annual round trips, still far short of 30 over the run available once the shortest-lived universe member's inception is respected. |

The cost is disclosed rather than hidden: excluding rotation costs Attempt 2 its most naturally
diversified candidate. C3 carries the multi-instrument role instead — a risk leg, a Treasury leg, and
a genuine third state in cash — which is also why a three-candidate set keeps one multi-instrument
candidate at all: otherwise S3-C6 would be `NOT_APPLICABLE_BY_CONDITION_TEXT` for every candidate and
the attempt would answer less of the question.

**None of the three is an independent test of its family's hypothesis.** All three hold the entry and
exit signal in the same rule form as a rejected Attempt 1 candidate, deliberately: if the return
source is held fixed, any difference in risk behaviour is attributable to the risk architecture
rather than to a new signal. This is stated in each candidate's `distinction_from_attempt_1` block
and again in the adaptation disclosure.

## 7. RA1 — one structural risk architecture, shared identically

All three candidates share one architecture, `RA1`, declared once. `SE100-CFG-3003`:

> Declaring one architecture once, identically across candidates, means its degrees of freedom are
> counted once rather than three times. If RA1 were tuned per candidate, three candidates would carry
> three independent sets of risk parameters and the search would be three times wider than it
> appears.

| Mechanism | Rule | Where the constant comes from |
| --- | --- | --- |
| `RA1-1` Exposure ceiling | `f_base = 0.50`. No entry may request a budget above `f_base × equity` at the decision close. | Not fitted. Constitution §5.2's live soft risk halt is 8% below the high-water mark and its hard halt is 10%; RA1-3 caps a single position's nominal decline at `L = 0.08`, so `f_base × L = 0.040` is half the soft-halt distance. Applies to the defensive Treasury leg too — no per-instrument carve-out. |
| `RA1-2` Volatility-targeted entry sizing | `sigma_target = 0.10` annualised; `f_vol = sigma_target / VOL20`; `f = min(f_cap, f_vol)`; `f_floor = 0.05`. At entry only. | `f = min(...)`, so volatility targeting can only **reduce** exposure below the RA1-1 ceiling; it can never raise it. Entry-only because the sealed accounting appends a closed trade only on full close, so positions are all-or-nothing. |
| `RA1-3` Per-position loss control | `L = 0.08` measured from the entry **decision close** `P_ref`; a close at or below `P_ref × 0.92` emits a full exit `EXIT_LOSS_CONTROL`. | 0.08 is the constitution's own §5.2 soft risk halt distance, adopted at position level — "Taking the number from a frozen artifact rather than choosing one keeps it out of the search space." Referenced to the decision close, not the fill, because the fill is next session's open and is not visible at decision time. |
| `RA1-4` Maximum holding period | `H` per candidate; `sessions_held >= H` emits `EXIT_MAX_HOLD`. | Each `H` is set from its candidate's own stated thesis horizon and is longer than that horizon in every case, so it is an outer bound rather than the operative exit. |
| `RA1-5` Account de-risk ladder | `dd < 0.08 → f_cap = 0.50`; `0.08 ≤ dd < 0.10 → 0.25`; `dd ≥ 0.10 → 0.125`. Read at entry only. | 0.08 and 0.10 are §5.2's live soft and hard halt distances verbatim; the multipliers halve and halve again. `context.equity` is the same series the engine reads before evaluating the §5.1 shutdown, so the ladder and the shutdown read one series, not two approximations of one. |
| `RA1-6` Re-entry lockout | `R = 5` decision sessions on the exited symbol after `EXIT_LOSS_CONTROL` or `EXIT_MAX_HOLD`. `EXIT_SIGNAL` creates no lockout. | One exchange week. Not load-bearing for the drawdown arithmetic, which assumes no lockout at all. |
| `RA1-7` Conflict resolution | The shared `flat_first_rule`, adopted unchanged. Every symbol switch costs one full session out of the market. | Inherited from Attempt 1's sealed shared rules. |
| `RA1-8` All-or-nothing positions | No partial entry or exit, no scaling, no averaging down, no pyramiding. | §5.1 prohibits averaging down without an explicit predeclared rule, and partial exits would make the closed-trade series — the basis of S3-C3 through S3-C6 — ambiguous. |

Exit precedence is `EXIT_LOSS_CONTROL` → `EXIT_MAX_HOLD` → `EXIT_SIGNAL`, and it exists for reason
attribution only: at most one exit is emitted per session because positions are all-or-nothing, so
the precedence "changes no exit decision — the position closes either way — so it cannot affect any
metric." It is what makes RA1-3 and RA1-4 diagnosable from exit-reason counts instead of needing a
neighbour each.

Two mechanisms record a **rejected earlier formulation**, because both defects are instructive and
both are the same defect. An earlier RA1-5 blocked new entries once `dd` reached 0.08 until equity
recovered above the high-water mark; an earlier RA1-6 held the lockout until the entry condition
evaluated false at least once. A flat account's equity is constant, so it can never recover, and a
regime condition can remain true for years — either rule could produce a permanently dead strategy.
The sealed versions reduce size and expire after a fixed count instead. Neither ever blocks an entry
outright, and `f_cap` is never zero.

One new indicator was added, `VOL20`: annualised standard deviation of the 20 most recent simple
daily total returns computed from 21 visible `adj_close` values, sample denominator **19**, scaled by
`sqrt(252)`. The denominator is fixed in the specification precisely so that the choice between 19
and 20 — a factor of about 1.026 — cannot be made after seeing a result. Zero volatility blocks the
entry with reason `NO_ENTRY_ZERO_VOLATILITY`; insufficient history means cash.

## 8. Why RA1 is not a stop at 14.99%

The prohibition is declared in the architecture itself:

> RA1 is not a device for stopping at 14.99%. No rule references the 15% ceiling, no rule references
> a drawdown level between 10% and 15%, and no rule is conditioned on proximity to the shutdown. The
> deepest level RA1 reacts to is 10%, which is the constitution's own section 5.2 hard risk halt,
> declared for live trading and adopted here as a research-side de-risking trigger.

Every RA1 constant is either taken verbatim from a frozen artifact (`0.08` and `0.10` from §5.2,
`0.05` mirroring the §5.1/§3 minimum cash buffer read as a smallest-meaningful-fraction) or derived
arithmetically from constants that are (`f_base × L = 0.040`, the halving multipliers). None was
selected by inspecting an Attempt 1 equity path. `sigma_target = 0.10` and the choice to halve are
the two researcher choices, both declared once and both probed by a neighbour.

Nor is the strategy made incapable of trading in order to suppress drawdown: the ladder never blocks
an entry, `f_floor = 0.05` binds only above 200% annualised volatility — "far above any level the
frozen universe has exhibited" — and S3-C4's unchanged 30-closed-trade floor is a live failure mode
for all three candidates rather than a formality.

## 9. The drawdown arithmetic of the declared constants

`SE100-CFG-3003` carries a seven-step hand computation over the declared constants, labelled in the
file as "an arithmetic property of the declared constants … **NOT** a prediction, **NOT** a
guarantee, and **NOT** a claim that S3-C2 will be met." Worst case is consecutive round trips each
losing exactly `L`, from the high-water mark, with loss per trade `f_cap × L`:

| Trade | `dd` before | `f_cap` | Loss | Equity | `dd` after |
| ---: | --- | --- | --- | --- | --- |
| 1 | 0.0000% | 0.500 | 4.000% | 0.960000 | 4.0000% |
| 2 | 4.0000% | 0.500 | 4.000% | 0.921600 | 7.8400% |
| 3 | 7.8400% | 0.500 | 4.000% | 0.884736 | 11.5264% |
| 4 | 11.5264% | 0.125 | 1.000% | 0.875889 | 12.4111% |
| 5 | 12.4111% | 0.125 | 1.000% | 0.867130 | 13.2870% |
| 6 | 13.2870% | 0.125 | 1.000% | 0.858459 | 14.1541% |
| 7 | 14.1541% | 0.125 | 1.000% | 0.849874 | **15.0126% — BREACH** |

Seven consecutive maximum-loss round trips are required to breach; six leave drawdown at 14.15%. The
0.25 rung is skipped on this particular path because trade 3 carries drawdown from 7.84% straight to
11.53%; the middle rung is reached by paths made of smaller individual losses.

The five caveats are part of the specification, not commentary. RA1-3 is **not** a bound: the trigger
is a close and the fill is the next open, so a gap can exceed `L` and the per-trade loss can exceed
`f_cap × L` — constitution §5.2, "Stops are risk tools, not guarantees; overnight gaps may exceed
intended losses." Drawdown is measured at session closes because the project holds no intraday data,
so every measured drawdown is a lower bound on the true intraday figure — an Attempt 1 limitation
inherited unchanged. Losses need not be consecutive, and interleaved small losses can walk the
account down through the rungs more slowly than this path does. And the arithmetic says nothing about
profitability.

## 10. What the architecture costs, disclosed before any result

Five costs are declared in `SE100-CFG-3003`. The first is counter-intuitive enough to be worth
stating in full: sell-side regulatory fees in the sealed cost model `SE100-CFG-2001` round **up** to
the cent, so a sale costs about two cents regardless of size — roughly 2 bps on a 95%-of-equity
position, roughly 4 bps on a 50% position, roughly 16 bps on a 12.5% position. **Lowering exposure
raises cost per unit of exposure**, and RA1 pays that drag on every trade.

The other four: RA1-1 halves exposure and therefore roughly halves participation in the returns that
made every Attempt 1 candidate profitable — which is precisely what the research question asks about;
RA1-1 applies to the defensive Treasury leg, reducing its carry contribution; RA1-4 forces an exit
and later re-entry on any position held to its horizon, costing at least six sessions out of the
market and two round-trip charges per cycle once RA1-6 and RA1-7 are applied; and RA1-6 keeps the
account in cash for five sessions after every risk exit, forgoing any recovery inside that window.

## 11. The three candidates

Full specifications are in `SE100-CFG-3003`; each candidate block carries all 31 fields the test
suite requires, and 39, 39, and 41 declared fields respectively. Summarised:

**`SE100-S3A2-C1-PULLBACK-RA1`** — SPY only, 200-session warm-up. Enter when `close > SMA(200)` and
`close < SMA(10)`; exit by RA1-3, else RA1-4 at 20 sessions, else on signal. `H = 20` is one exchange
month, an outer bound on a thesis whose own signal exit fires quickly. Parameters `sma_long 200`,
`sma_short 10`, `f_base 0.50`, `vol_target 0.10`, `loss_control 0.08`, `max_hold 20`,
`reentry_delay 5`. Neighbours: `sma_long 150`, `sma_short 20`, `vol_target 0.08`, `f_base 0.35` — two
on the signal, two on the new risk machinery. Single instrument, so S3-C6 is
`NOT_APPLICABLE_BY_CONDITION_TEXT`. Economic rationale: a pullback inside an uptrend is short-horizon
liquidity provision whose edge is small and per-trade, making it the family least damaged by halving
exposure and the one where a loss control is most natural.

**`SE100-S3A2-C2-MEANREV-RA1`** — SPY only, 101-session warm-up (the sealed RSI definition declares
`warmup_changes 100`). Enter when Wilder `RSI(2) < 10`; exit by RA1-3, else RA1-4 at 10 sessions,
else when `close > SMA(5)`. `H = 10` is double the upper end of the sealed F3 thesis's stated
two-to-five session horizon. Neighbours: `rsi_entry_below 5`, `exit_sma 10`, `vol_target 0.08`,
`loss_control 0.12`. The risk pair differs from C1's and C3's deliberately: F3 explicitly declared it
had **no** stop, so the loss control is the most consequential addition here, and the neighbour
*loosens* it to 0.12 to test whether the sign depends on the specific limit. `rsi_period` and
`f_base` appear in the permitted grid as single-value **pins**, recording that this candidate
deliberately does not probe them. Expected to be in cash most of the time by construction — "that is
the point of it and not a defect."

**`SE100-S3A2-C3-DEFENSIVE-RA1`** — SPY and SHY, 200-session warm-up, run start governed by SHY's
inception because the run start rule reads the **declared** universe. Route to SPY when
`close(SPY) > SMA(200)(SPY)`, else to SHY if it has a visible bar, else cash; the regime is read from
the risk symbol only — "the defensive leg is a destination, never a signal." `H = 252` is one
exchange year, the natural re-underwriting horizon for a 200-session regime lookback. `VOL20` is
measured on the **target** symbol. A locked-out target is not substituted by the other leg, because
substituting would let a lockout on one instrument silently change the asset allocation. Neighbours:
`sma_long 150`, `defensive_symbol null`, `vol_target 0.08`, `f_base 0.35`. IEF is deliberately **not**
in the grid: F6 probed it, and a second Treasury duration would probe the signal source rather than
the risk architecture.

C3 also carries a disclosed risk, recorded before any result: S3-C6 is the condition most likely to
reject it even if the risk architecture works, because a regime strategy with an equity risk leg and
a short-duration Treasury leg has no reason to split profit evenly, and F6 failed exactly that
condition in Attempt 1. C3 was kept with that failure mode understood and accepted.

**Window comparability.** C1 declares 200 sessions of warm-up where F2 declared 250, and C3 declares
200 where F6 declared 250, so run windows differ. No Attempt 2 candidate is a matched-window
controlled comparison against any Attempt 1 candidate, and no Attempt 2 number may be differenced
against an Attempt 1 number and reported as the effect of the risk architecture.

The shared rules adopted **unchanged** from `SE100-CFG-3001` are `one_decision_per_session`,
`long_only` (one open risky position at a time, per the sealed cost model's
`max_open_risky_positions` of 1), `flat_first_rule`, `insufficient_history_rule`, `tie_break`,
`warmup_rule`, `run_start_rule`, `warmup_data_source`, `no_intraday`, `no_machine_learning`, and
`no_combination`. Exactly one shared rule is replaced: `sizing_rule`, by RA1-1/RA1-2/RA1-5, under
`A2-INTERP-1` and §11, direction of change **downward only**.

## 12. Gate 3, unchanged

The criteria are **adopted by digest, not by copy**: `config/stage3_gate_criteria.json`
(`SE100-CFG-3002`, `310f1c978380f4a1d6b98b8c368975b1515476b032c123afb06f1dd597e3e18d`). As
`SE100-CFG-3003` puts it, "Binding this file by digest rather than copying it is what makes 'the 15%
ceiling is unchanged' checkable by arithmetic instead of by reading."

| Condition | Threshold and predicate | Status for Attempt 2 |
| --- | --- | --- |
| S3-C1 total return | positive; `total_return > 0` | unchanged |
| S3-C2 maximum drawdown | no worse than 15%; `max_drawdown <= 0.15`, inclusive boundary | **unchanged.** Satisfied iff the §5.1 research shutdown never fires. |
| S3-C3 profit factor | at least 1.10; `profit_factor >= 1.10` | unchanged |
| S3-C4 minimum trade count | at least 30 closed trades; `closed_trades >= 30` | unchanged; lower-frequency exception **not** invoked by any candidate |
| S3-C5 best-trade removal | both removals — largest equity multiple and largest absolute P&L — must leave total return above 0% | unchanged |
| S3-C6 concentration | maximum single-instrument share of total closed-trade P&L `<= 0.50`, evaluated only when total closed-trade P&L is strictly positive, else `NOT_EVALUABLE` | unchanged; applies to C3 only, by `A2-INTERP-3` / `A2-REDERIVE-1` |
| S3-C7 neighbour stability | sign of net return equal to the primary's for all four declared neighbours | unchanged; declaring artifact is `SE100-CFG-3003` for Attempt 2 candidates, by `A2-INTERP-2` / `A2-REDERIVE-2` |

`max_drawdown_ceiling: "0.15"`, `max_drawdown_ceiling_changed: false`,
`criteria_changed_for_attempt_2: false`, `conditions_evaluated: 7`.

**Admission logic, frozen now rather than at evaluation time.** Within a candidate the conditions are
**conjunctive**; across candidates the stage verdict is a **disjunction**;
`admissible_candidates_required: 1`. Satisfied is wider than met: a condition counts as satisfied when
its verdict is `MET` **or** `NOT_APPLICABLE_BY_CONDITION_TEXT`, and `NOT_MET`, `NOT_EVALUABLE`,
`NOT_RUN`, `UNKNOWN`, and a missing verdict are never satisfied. A per-condition rollup across
candidates settles nothing — it means only "at least one candidate satisfied this" — and the gate is
decided by `admissible_candidate_exists` alone. Verdict tokens are derived from the sealed
`verdict_token_derivation` rather than restated as literals: pass
`STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT`, fail `STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT`. A fail is
a deliverable.

Also settled prospectively, so that no implementation session can decide any of it from a result:
neighbours are diagnostic and can never be promoted to primary or representative; a shutdown breach
liquidates at the next open and blocks entries, and never re-arms; no result may be re-run after a
valid completed evaluation; the permitted parameter grid is a declared **boundary**, not a search
space, and no search is performed. The two re-derivations, `A2-REDERIVE-1` (S3-C6's `applies_to`) and
`A2-REDERIVE-2` (S3-C7's declaring artifact), each quote the sealed text, state why the re-derivation
is necessary, and state what it leaves unchanged; both are recorded in
`config/stage3_attempt2_gate_criteria_binding.json` (`SE100-CFG-3004`).

Cost stress is treated as constitution §7 requires and Attempt 1 deferred: each primary runs once
more at 2× base friction, three runs, `gating: false`, producing a `STRESS_FRAGILE` flag that may
**not** be used to admit or reject a candidate.

Benchmarks: SPY total return; SPY tradable buy-and-hold both with and without the shutdown; cash at
0.00% with the direction of the concession recorded; and a do-nothing flat USD 100.00. No benchmark
becomes a gate. Constitution §4 — "Beating SPY is not mandatory if a strategy materially reduces
drawdown, but passing requires positive after-cost performance and better risk-adjusted performance
than cash." — is the clause under which Attempt 2's thesis is constitutionally coherent.

## 13. Nine candidates against one development window

This is the disclosure that belongs before the result, not after it. Recorded in full in
`SE100-CFG-3003` and reproduced here in substance:

| Count | Attempt 1 | Attempt 2 | Cumulative |
| --- | ---: | ---: | ---: |
| Candidates | 6 | 3 | **9** |
| Gating variants | 30 | 15 | **45** |
| Total runs | 30 | 18 | **48** |

The binding number for any later statistical statement is the cumulative figure: 9 candidates and 45
gating variants against the same development window. Attempt 2 introduces no new signal form, so the
cumulative count of distinct *signal forms* tested at gate 3 remains 6 while distinct *specifications*
is 9 — which makes the reuse more concentrated, not less.

> Three candidates are tested against the same development data that six candidates were already
> tested against, by a researcher who knows how those six failed. A per-candidate criterion is not a
> family-wise one, and the probability that at least one of nine specifications passes by chance
> exceeds the probability that any single pre-specified one does. Because the Attempt 2 design space
> was narrowed by an observed Attempt 1 outcome, the effective search is wider than nine independent
> draws and cannot be bounded by counting runs. Nothing in this attempt corrects for it numerically.
> The correction the constitution relies on is that an admitted candidate must still survive Gate 4
> robustness, Gate 5's single sealed holdout read, and the duration-based paper and shadow gates.
> Attempt 2 weakens none of those and earns no relief from any of them.

The full ten-item adaptive-research disclosure is in `SE100-CFG-3003`
(`adaptive_research_disclosure`) and each item is asserted individually by the test suite. Its
substance: Attempt 1's results are known; this is an adaptive second attempt, not an independent
first look; all six Attempt 1 candidates breached the ceiling and some also failed the trade-count,
concentration, and best-trade-removal conditions; the development data are no longer pristine with
respect to that broad fact and the per-candidate trade counts; researcher degrees of freedom and
false-discovery risk are correspondingly higher; the total experiment count is cumulative; no Attempt
2 result may be called independent confirmation merely because its code is new; all three candidates
reuse a rejected candidate's signal form; validation and holdout protections are unchanged; and a
passing development result authorises only the next frozen evaluation step and is not evidence of a
trading edge.

The adaptation is **not** concealed behind a new strategy identifier. Every candidate id carries the
`RA1` suffix naming the shared risk architecture, and every candidate block names the rejected
Attempt 1 candidate whose signal form it reuses.

The iteration budget is 3 candidates × (1 primary + 4 neighbours) = 15 gating variants, plus 3
non-gating stress runs, 18 runs total, `revisions_permitted: 0`. Neighbour runs are not iterations;
stress runs are not iterations.

## 14. What happens on a bad outcome, decided before any outcome exists

Six rules are fixed by the seal, because a rule that must be interpreted at implementation time is a
rule that was not pre-registered:

- **Attempt-level abandonment** — declared in full in `SE100-CFG-3003`, closing with the reason it
  exists: "A rule that must be interpreted at implementation time is a rule that was not
  pre-registered, and repairing it after any Attempt 2 number exists would make the specification
  retrospective."
- **No retuning** — no parameter, rule, or threshold changes after the seal. Neighbours are never
  promoted. Under §11 a material change creates a **new** candidate that restarts at gate 3.
  Tightening a safety threshold is permitted but "may not be applied to a candidate whose result is
  already known."
- **Post-seal software defect** — a defect found before any result is fixed and recorded; a defect
  found after a result means the result is recorded `INVALIDATED` per §10 and every affected run is
  re-run **in full**. "Selectively re-running only the runs whose numbers were disliked is
  prohibited." A defect in a frozen upstream artifact is a blocker, not a repair. No code defect
  authorises a change to the specification.
- **Partial or failed runs** — a failed neighbour is `NOT_RUN` and fails S3-C7; a failed primary makes
  its candidate `NOT_EVALUABLE` and therefore not admissible; a failed stress run is `NOT_RUN` and
  non-gating. Partial completion is not a result, and no substitution is permitted.
- **Missing or invalid data** — declared in `SE100-CFG-3003`.
- **Reproducibility** — deterministic exact-`Decimal` arithmetic under the sealed `ENGINE_CONTEXT`, no
  randomness, ASCII ordering, and declared run-record contents. `random_seeds` is present and `null`
  "so that its absence cannot later be read as an omission."

## 15. Sealing — measured, not asserted

`SE100-CFG-3003` states the ordering claim, and the seal record measures it rather than repeating it:

> The seal record `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json` measures that claim rather than
> asserting it.

Attempt 1 could prove its ordering with two counts of zero over `strategies/` and `reports/stage3/`.
Both directories are now legitimately non-empty with Attempt 1's own modules and results, which may
not be deleted, so counting to zero over those paths is no longer the available test. Attempt 2 uses
four narrower predicates plus an immutability check, each carrying its own definition in the seal:

| Predicate | Value at sealing |
| --- | ---: |
| `attempt_2_strategy_modules` — `.py` files under `src/stockedge100/` whose path contains `attempt2`, excluding `reporting/` (where the sealing program itself lives; the exclusion narrows the check and is recorded rather than hidden) | 0 |
| `modules_naming_an_attempt_2_candidate` — `.py` files under `src/stockedge100/strategies/` whose text contains any declared candidate id (catches an Attempt 2 implementation grafted into an Attempt 1 module) | 0 |
| `attempt_2_report_artifacts` — files under `reports/` whose path contains `attempt2` | 0 at sealing |
| `attempt_2_run_records` — files under `runs/` whose text contains `ATTEMPT_2` or any declared candidate id, measured **before** this seal wrote its own run record | 0 |
| `attempt_1_records_verify` — both Attempt 1 records verify entry-for-entry from the project root | `true` |

Two of those counts move legitimately after the seal, and both moves were anticipated in the sealed
definitions themselves rather than discovered afterwards: `attempt_2_run_records` becomes 1 because
the seal writes a run record whose stage token contains `ATTEMPT_2` by construction, and
`attempt_2_report_artifacts` becomes non-zero because this design session's own test summary, pytest
output, decision record, manifest, and checksum record live under `reports/stage3_attempt2/`. The
sealed definition of the latter says "Must be 0 **at sealing**" and names "test artifact" among the
things it would catch. Neither is strategy code and neither is a performance result. §17 below
enumerates every file that makes them non-zero.

The seal records the sealing timestamp `2026-08-10T11:59:33Z`, the run id
`SE100-R-20260810T115933Z`, the verified state of every upstream freeze record, the window states,
and the digests of the three pre-registered files:

| Pre-registered file | sha256 |
| --- | --- |
| `config/stage3_attempt2_strategy_protocol.json` | `77f1451c20e37640bd2843ff86d69eb54cbc0ebb592a696972fbdea6e05b5433` |
| `config/stage3_attempt2_gate_criteria_binding.json` | `a482f499173c0d7e2b0ca158b2edf7cb2e25a516ac2eb361e1441b2964006c8e` |
| `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.md` | `d9e34b3ce61f5998fe91c0b7b551a29a778fdb410330e60d6919c0a94ec447c6` |

The checksum record `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256` covers those three files
plus the seal JSON, uses project-root-relative paths, and is verified with
`cd stockedge100 && sha256sum -c governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256` — four entries,
all OK. It does not name itself, because nothing hashes itself. The seal deliberately omits
`repo_state_id`; the binding value is the field in the `runs/` record. The sealing program refuses to
run a second time — re-invoking it returns exit 2 because the record already exists — which is what
makes the seal unrepeatable.

All three Attempt 2 JSON artifacts — `SE100-CFG-3003`, `SE100-CFG-3004`, and the seal record — are
ASCII-only in fact, verified by `text.isascii()` and not merely declared, so their digests are stable
under any reader's codec. The pre-registration Markdown is UTF-8 and carries em dashes and section
signs like every other governance document here; its digest is pinned in the seal, so its encoding
cannot drift silently either.

## 16. Tests

Command, verbatim:

```
cd stockedge100 && python -m pytest tests/unit/test_stage0_governance.py tests/unit/test_stage1_preregistration.py tests/unit/test_stage3_attempt2_preregistration.py -q
```

**115 passed, 0 failed, 0 skipped.** The new file alone is 71 passed, 0 failed, 0 skipped. Raw output:
`reports/stage3_attempt2/pytest_stage3_attempt2_output.txt`. Full detail:
`reports/stage3_attempt2/STAGE_3_ATTEMPT_2_TEST_SUMMARY.md`.

The broad command `python -m pytest tests -q` was **not** run, and deliberately: two integration
modules read the normalised dataset and drive the engine over it, which this session may not do. The
recorded command is a three-file selection that reads only governance documents, `config/` JSON,
`src/` text, `runs/` records, and trees the tests build themselves under `tmp_path`. **No test in the
selection opens a price file, computes a return, or touches the validation or holdout windows.** The
two pre-existing files are controls rather than coverage: Stage 0's 27 tests re-verify the
constitution and its freeze record, and Stage 1's 17 re-verify a pre-registration seal of the same
shape, so a failure among the new 71 is attributable to the new file.

The suite floor rose from 389 to **460** collected (`python -m pytest tests --collect-only -q`, which
imports every module but executes no body). Because the whole suite was deliberately not executed,
"unmodified" is asserted by digest instead of by a green run: every `tests/**/*.py` entry in Attempt
1's run record was recomputed against disk — 11 recorded, 11 unchanged, 0 changed, 0 missing, against
12 live files, the one addition being the new file. A weakened or deleted test would appear there as
changed or missing. `tests/conftest.py` is one of the 11 verified entries and was not touched.

What the new tests establish, in outline: the seal parses and declares itself sealed; the three
digests are pinned as literals **independently** of the checksum record, so rewriting an artifact and
its record together still fails; the four contamination predicates are exercised in **both**
directions — clean tree reads empty, planted contamination is caught — and a parametrised test forces
each predicate non-empty in turn and requires the sealing program to return exit 3 with nothing
written, so the predicates are wired to refusal rather than merely reported; Attempt 1's two records
verify entry-for-entry and the seal's `supersedes` is null; the gate criteria are pinned by digest
independently of the binding file, so a criteria change fails even if the binding were updated to
match; the admissibility rule is applied from the sealed `satisfied_definition` rather than a literal
and tested in both directions on synthetic verdict tables; three unique candidate ids each specify
all 31 required fields; eleven required disclosure substrings are asserted individually; and the
window guard is exercised structurally on **dates only**, reading no observation.

Three clean controls sit at the top of the file, and the third matters most: a synthetic candidate
whose seven condition verdicts are all satisfied **is** admissible under the sealed rule. Attempt 1
admitted nothing, and a rule that admits nothing would look identical to a correct one without a
control that requires it to admit something.

No test covers the decision package, and none can: `tests/**/*.py` is one of the patterns
`repo_state_id` is computed over, so a test asserting that digest would invalidate the value it
asserts the moment it was written. The package is verified by re-running the recomputation.

## 17. Contamination assessment

| Question | Finding |
| --- | --- |
| Did strategy implementation exist for any intended Attempt 2 candidate before the seal? | **No.** Measured by two independent predicates — a path-based one over `src/stockedge100/` and a content-based one over `src/stockedge100/strategies/` — both 0, both tested in the negative direction. |
| Was any Attempt 2 performance generated or inspected? | **No**, because none could be. No strategy module exists for the three candidates; no backtest, simulation, parameter sweep, or performance calculation was run. |
| Was validation-period data or any validation result accessed? | **No.** The validation window is `LOCKED` and was read only as integrity metadata. |
| Was the holdout accessed? | **No.** The holdout window is `SEALED`. `STAGE_1_HOLDOUT_LOCK.json` was read for its lock state and bound by digest; its boundary dates were deliberately not restated in any Attempt 2 artifact. |
| Is the design prospective with respect to Attempt 2 results? | **Yes**, and measured rather than asserted: every symbol, parameter, threshold, lookback, rule, sizing rule, risk rule, benchmark, and neighbour was written before any Attempt 2 code existed and before any Attempt 2 candidate produced any number. |
| Is the design prospective with respect to Attempt 1 results? | **No, and this is disclosed, not claimed.** Attempt 1's results are known. The adaptation is recorded in a ten-item disclosure, in the cumulative experiment count, in the family-exclusion reasoning, and in each candidate's `distinction_from_attempt_1` block. |

Files created by this session that make the two movable predicates non-zero after the seal, each
classified:

| Path | Class |
| --- | --- |
| `runs/SE100-R-20260810T115933Z.json` | the seal's own run record — anticipated in the predicate definition |
| `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_TEST_SUMMARY.md` | test artifact |
| `reports/stage3_attempt2/pytest_stage3_attempt2_output.txt` | test artifact |
| `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.json` | design-session decision record |
| `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_ARTIFACT_MANIFEST.json` | artifact manifest |
| `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256` | checksum record |
| `runs/<this session's run id>.json` | design-session reproducibility record |

None is strategy code. None is a performance result. None contains a return, a drawdown, a trade
count, or an equity value for any Attempt 2 candidate.

One authoring correction is recorded, and it was caught before anything was hashed: an earlier draft
of `SE100-CFG-3003` declared a C2 robustness neighbour varying `loss_control` while omitting that key
from C2's permitted parameter grid, violating the grid invariant the same file declares. It was
corrected before the seal. Two citation defects were corrected at the same time — a modal verb
capitalised in a quotation that reads lower-case in the source, and a §11 scope gap that was being
glossed rather than stated. All three are recorded in §10 of the sealed pre-registration. No
timestamp in any Attempt 2 artifact was hand-typed.

## 18. Design-session gate conditions

Gate 3 itself was **not** evaluated in this session. The conditions below are the conditions for a
legitimate seal, and they are what the decision record carries.

| Condition | Requirement | Verdict |
| --- | --- | --- |
| `A2D-C1` frozen governance verified | Stage 0 freeze (both halves), Stage 1 freeze, and the Stage 1/2/3 pre-registration and decision checksum records all verify from their intended working directories before any artifact is authored | MET |
| `A2D-C2` second attempt permitted | Frozen on-disk governance permits a further gate 3 attempt by new pre-registration, with the determination resting on quoted frozen text and not on the operating prompt | MET |
| `A2D-C3` prospective with respect to Attempt 2 | All four contamination predicates read 0 at sealing and Attempt 1's records verify; each predicate is tested in both directions and wired to refusal | MET |
| `A2D-C4` Gate 3 unchanged | Criteria adopted by digest, 7 conditions, ceiling `0.15` unchanged, conjunction logic unchanged; two re-derivations apply sealed rules to a new candidate set and change no threshold, predicate, measurement, or token | MET |
| `A2D-C5` adaptation disclosed | Ten-item disclosure recorded, each item asserted individually through eleven required substrings; cumulative count 9 candidates / 45 gating variants / 48 runs; no result may be called independent confirmation because its code is new | MET |
| `A2D-C6` specification complete | 3 candidates, each carrying all 31 required fields (39, 39, 41 declared); attempt-level content complete; grid invariant holds; no discretionary choice is left to an implementation session | MET |
| `A2D-C7` sealing integrity | Checksum record verifies 4/4 from the project root; MD and JSON materially agree; serialisation deterministic and all three JSON artifacts ASCII-only in fact; manifest self-reference policy followed; no tree digest written inside a covered file | MET |
| `A2D-C8` partitions unchanged | Development window only authorised; validation `LOCKED`; holdout `SEALED`; enforcement structural through `ResearchWindow` / `MarketView`; no boundary changed | MET |
| `A2D-C9` test floor rose | 460 collected, up from 389; targeted selection 115 passed / 0 failed / 0 skipped; 11 of 11 recorded test-file digests unchanged; nothing weakened, skipped, `xfail`ed, or deleted | MET |
| `gate_3_admissible_candidate_exists` | Whether at least one candidate satisfies all applicable gate 3 conditions | **NOT_RUN.** No candidate was implemented or evaluated. This row exists so that this package cannot be read as a gate 3 determination. |

## 19. Limitations

- **Gate 3 is not passed.** A sealed design is a specification, not evidence. Nothing here indicates
  that any Attempt 2 candidate will satisfy S3-C2 or any other condition.
- **The drawdown arithmetic in §9 is not a guarantee.** It is a property of the declared constants
  under an idealised worst-case sequence, with five caveats that all cut the same way.
- **The development window is no longer pristine.** Nine specifications now share it, and the
  effective search is wider than nine independent draws.
- **No Attempt 2 candidate is a controlled comparison against Attempt 1.** Warm-up lengths differ, so
  run windows differ; differencing an Attempt 2 number against an Attempt 1 number would not measure
  the risk architecture.
- **Attempt 2 introduces no new signal form.** All three signals are reused from rejected candidates,
  so the attempt cannot corroborate any family's hypothesis.
- **Drawdown is measured at session closes.** The project holds no intraday data, so every measured
  drawdown is a lower bound on the true intraday figure. Inherited from Attempt 1, unchanged.
- **Lower exposure raises cost per unit of exposure**, because sell-side regulatory fees round up to
  the cent. The drag is charged, not modelled away.
- **S3-C6 remains a live failure mode for C3**, declared and accepted before any result.
- **The whole test suite was not executed**, so "unmodified" for the pre-existing test files is
  asserted by digest recomputation rather than by a green run.
- **`scipy` and `pyarrow` are not installed**, and no Attempt 2 rule requires either.

## 20. Authorization state

| Activity | State |
| --- | --- |
| Attempt 2 implementation — writing strategy modules for exactly the three sealed candidates | **UNLOCKED** for a later, separately authorized session. Nothing else. |
| Attempt 2 development-window evaluation | **UNLOCKED** in that same session, development window only |
| Validation-window access | **LOCKED** |
| Final holdout | **SEALED** |
| Stage 4 / constitutional gates 4 and 5 | **LOCKED.** Requires an admitted candidate; none exists. |
| Alpaca paper trading | **LOCKED** |
| Shadow-live | **LOCKED** |
| Alpaca live trading | **LOCKED.** `live_trading_authorized = false`. |
| Capital or risk expansion | **LOCKED** |

Stage 4 remains prohibited on the conditions listed in `SE100-CFG-3003`
(`stage_4_remains_prohibited_conditions`, eight items, closing "`live_trading_authorized` remains
false regardless of any development result"), and the twelve `explicit_non_authorizations` in the
same file close the same way, on "`live_trading_authorized` remains false." Gate 3 is admissibility, not selection: no candidate is ranked,
preferred, or named a winner, and no expected income, profit, or return is claimed for any period.

## 21. Next authorized action

Exactly one: **a separate session that implements and evaluates only the three candidates sealed in
`SE100-GOV-0007`**, on the development window only, at their declared primary parameterisations plus
their four declared neighbours each, with the sealed base cost model, the research shutdown enforced,
and the three non-gating stressed-cost runs. No parameter may be changed, no candidate re-run after a
result, no neighbour promoted, and no fourth candidate added.

## Verdict

`PASS — STAGE_3_ATTEMPT_2_PREREGISTRATION_FROZEN`

The verdict means one thing and nothing more: a prospective, complete, internally consistent
specification for a second gate 3 attempt has been sealed before any code for it exists, its
adaptation to a known prior outcome is disclosed rather than hidden, the frozen gate 3 criteria —
including the 15% maximum-drawdown ceiling — are adopted unchanged, and implementation may therefore
begin in a later separately authorized session. It is **not** a gate 3 pass, **not** a statement that
any candidate will be admitted, **not** a performance claim, and **not** an authorization for
validation access, holdout access, stage 4, paper trading, shadow-live, or live trading. StockEdge100
is not trade-ready.
