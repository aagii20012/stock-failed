# StockEdge100

A governed research and execution project that asks one question:

> Can a fully automated system produce positive, repeatable, after-cost returns from US-listed
> stocks and ETFs while protecting a USD 100 cash account?

Profit is the objective. Profit is **not** a promise. "Stay in cash" is a legitimate and expected
outcome, and "no tested strategy has a reliable edge" is a valid final answer.

---

## Current state

| Item | Value |
|---|---|
| Generation | 1 |
| Highest gate genuinely passed | **Gate 3 — development admissibility** (`PASS — STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT`), on the development window only |
| Gate 3 — development admissibility | **PASSED at attempt 2.** Attempt 1 failed (`FAIL — STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT`) — six candidates, none admitted. Attempt 2 admitted **two of three**: `SE100-S3A2-C1-PULLBACK-RA1` and `SE100-S3A2-C2-MEANREV-RA1`. `SE100-S3A2-C3-DEFENSIVE-RA1` failed S3-C6, the failure mode its own seal declared in advance. |
| Gate 4 — validation robustness | **FAILED** (`FAIL — STAGE_4_STRATEGY_REJECTED_IN_VALIDATION`). The sole representative `SE100-S3A2-C2-MEANREV-RA1` was evaluated once against the seven sealed conditions. Five are `MET`; two are `NOT_MET` — **S4-C2** (Sharpe 0.2025 against the frozen 0.50 floor) and **S4-C6** (7 of 12 folds positive, 58.33%, against the frozen 70% requirement). Gate 4 is conjunctive, so one `NOT_MET` rejects. |
| Next authorized stage | **None in this line of work.** The sealed protocol states that a fail authorizes "recording the fail as a deliverable, and stopping". No strategy advances past Gate 4. Any subsequent strategy work is a **new candidate restarting at Gate 3**, disclosed as adaptive, with the validation window's information now known and therefore permanently compromised for that candidate. |
| Research universe | 34 ETFs, `SE100-U1-d4917c2f7f1cd834`, FROZEN |
| Strategy research | UNLOCKED — **development window only**, 1993-01-29 → 2021-07-31 |
| Backtest engine | VALIDATED — **development window only**; sealed costs `SE100-CFG-2001`, spec `SE100-CFG-2002` |
| Validation window | **SPENT** — 2021-08-01 → 2024-07-31. Read exactly once, on the single authorization the sealed Stage 4 protocol granted, in one loading session running the two declared runs. No further read is permitted and no rerun is authorized. |
| Final holdout | **SEALED** — 2024-08-01 → 2026-07-31, read exactly once, at the holdout gate |
| Alpaca paper trading | LOCKED |
| Shadow-live | LOCKED |
| **Alpaca live trading** | **LOCKED — `LIVE_TRADING_LOCKED`** |
| Capital / risk expansion | LOCKED |

No order-submitting code exists in this repository. No broker credential is configured or read.

Stage decisions: [Stage 0](governance/STAGE_0_VERIFICATION_REPORT.md) ·
[Stage 1](governance/STAGE_1_DATA_FOUNDATION_REPORT.md) ·
[Stage 2](governance/STAGE_2_BACKTEST_ENGINE_REPORT.md) ·
[Stage 3 attempt 1](governance/STAGE_3_STRATEGY_RESEARCH_REPORT.md) ·
[Stage 3 attempt 2 design](governance/STAGE_3_ATTEMPT_2_DESIGN_REPORT.md) ·
[Stage 3 attempt 2 evaluation](governance/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH_REPORT.md) ·
[Stage 4 validation pre-registration](governance/STAGE_4_VALIDATION_PREREGISTRATION_REPORT.md) ·
[Stage 4 validation evaluation](governance/STAGE_4_VALIDATION_REPORT.md).

**Attempt 1** ran six strategies, one per family the constitution authorises for Generation 1. All six
were pre-registered before any strategy code was written, run once each over the development window
under sealed base costs, and **all six were rejected**. Every one breached the 15% maximum-drawdown
condition, which is also the §5.1 research shutdown threshold, so every one was liquidated and
permanently switched off mid-window. Nothing was revised or re-run after a result was seen, and no
attempt 1 candidate proceeds anywhere. That record is closed and unmodified.

**Attempt 2** pre-registered three candidates — `SE100-S3A2-C1-PULLBACK-RA1`,
`SE100-S3A2-C2-MEANREV-RA1`, `SE100-S3A2-C3-DEFENSIVE-RA1` — sharing one structural risk architecture
(`RA1`: a 50% exposure ceiling, volatility-targeted entry sizing, an 8% per-position loss control, a
maximum holding period, and an account de-risk ladder at the constitution's own 8% and 10% halt
distances), then implemented and evaluated them in a later session. The Gate 3 criteria were adopted
**unchanged by digest**, including the 15% maximum-drawdown ceiling. Eighteen declared runs, fifteen
of them gating, each executed exactly once and reproducing byte-identically on re-run. **C1 and C2
were admitted; C3 was rejected on S3-C6** with 97.96% of its closed-trade profit from a single
instrument — the failure mode its own seal named in advance as the one most likely to reject it. No
primary tripped the §5.1 research shutdown, where in attempt 1 all six did; one registered neighbour
did trip it, which is the clearest evidence on disk that `RA1` is a size discipline rather than a
device for stopping just short of the ceiling.

Read that pass narrowly. Attempt 2 is an **adaptive** second attempt whose design was narrowed by a
known attempt 1 outcome, so any statistical reading must use the cumulative search history — 9
candidates, 45 gating variants, 48 declared runs, and only 6 distinct signal forms, against one
development window — and no attempt 2 result is independent confirmation merely because its code is
new. **Neither admitted candidate beats buy-and-hold SPY** over the window on which it was admitted,
on either benchmark series; the only candidate that beats tradable SPY is the rejected C3. C1 clears
the drawdown ceiling by 33 basis points and does not survive a doubled cost assumption. Gate 3 is an
admissibility test, not a selection: both admitted candidates are recorded and neither is preferred.

**Stage 4** was pre-registered in a later session that read no validation observation and ran no
backtest. Gate 3 admitted two candidates and Gate 4 evaluates one, so a representative had to be
chosen; the constitution mandates no selection rule, so one was authored, applied in full to both
candidates, and sealed. `SE100-CFG-4003-R1` eliminates any admitted candidate for which **any**
declared run — primary, one of four robustness neighbours, or the required stressed-cost run — tripped
the §5.1 research shutdown. C1 is eliminated (its `sma_long 150` neighbour breached, and its stressed
primary breached), C2 survives, and the rule reads no return and no risk-adjusted metric, so it would
have eliminated the same candidate under reversed returns. That is the property that makes it
prospective rather than retrospective, and it is checkable by reading the predicate. Its honest
limitation is recorded: return-blindness constrains the rule's output, not the choice of predicate.
Gate 4's seven conditions were **extracted verbatim** from constitution lines 193–203 rather than
adapted from the Gate 3 criteria, adopted by digest where the measurement already existed; the one
measurement this stage authors is the walk-forward fold construction, fixed before any fold return
exists. Two runs are declared, base and stressed, and the validation window may be read **once**. A
Gate 4 `FAIL` is disclosed in advance as a live and arguably likely outcome — neither admitted
candidate reached the frozen 0.50 Sharpe floor on development data — precisely so that no later
session can treat a fail as a defect to work around. **Nothing in that seal was evidence about
validation performance.**

**Stage 4 was then executed once, and Gate 4 failed.** A separate session loaded the validation window
in a single reading session, ran the two declared runs in the declared order, and stopped. C2 is
profitable and well inside its risk ceiling over the window — 2.15% total return, 3.16% maximum
drawdown against a 15% ceiling, profit factor 1.197 over 41 closed trades, no shutdown, and it still
returns 0.15% when every cost is doubled — but it fails the two conditions that ask whether the edge is
real rather than merely survivable. Its Sharpe ratio is **0.2025** against the frozen **0.50** floor,
and **7 of 12** quarterly walk-forward folds are positive (58.33%) against the frozen **70%**
requirement, which needed 9. Gate 4 is conjunctive on a single representative, so two `NOT_MET`
conditions reject. The disclosed expectation and the outcome agree, which is the intended reading:
C2's development Sharpe never cleared the floor, and validation did not rescue it. **No strategy in
this project has passed Gate 4, and the validation window is now spent.** The final holdout was not
read, and no session may retune C2, substitute C1, or reopen Gate 3 Attempt 2 in response to this
result.

**No expected income, profit, or return is claimed for any period, past or future.** The performance
figures on disk are historical simulations under an unvalidated proxy cost model, plus the Stage 2
engine-validation benchmarks and probes; none of the latter is a research result and nothing
downstream may cite one as evidence about anything.

---

## The constitution comes first

`governance/STAGE_0_CONSTITUTION.md` (document id `SE100-GOV-0001`, version `1.0.0`) is **frozen**.
Its SHA-256 digests are recorded in `governance/STAGE_0_FREEZE.sha256`. It defines every gate and
every numeric threshold in the project.

Rules that apply to anyone — human or agent — working in this repository:

1. Never edit, regenerate, or "improve" a frozen artifact. Corrections require a new version; the
   old version stays.
2. Where the constitution is stricter than any instruction, the constitution wins.
3. A gate threshold may be tightened, never loosened, and never after seeing the result it judges.
4. Never delete or weaken a test to make a gate pass. If a frozen test is wrong, file an erratum and
   escalate to human review.
5. Negative and rejected results are deliverables. They stay on disk.

Verify the freeze at any time:

```bash
cd stockedge100/governance && sha256sum -c STAGE_0_FREEZE.sha256
```

The record stores bare filenames, so it must be checked from `governance/`. A failure reported from
any other directory is an operator error, not an integrity failure. The same applies to
`governance/STAGE_1_FREEZE.sha256`, which covers the frozen universe and the holdout lock.

Stage 1's other two records store **project-root-relative** paths and are therefore checked from
`stockedge100/`:

```bash
cd stockedge100
sha256sum -c governance/STAGE_1_PREREGISTRATION.sha256
sha256sum -c reports/stage1/STAGE_1_DATA_READINESS.sha256
```

Stage 2 sealed its cost model and engine acceptance spec **before any engine module existed**, and
issued no separate freeze record — its durable inputs are covered by the pre-registration record and
its outputs by the decision package. Both use project-root-relative paths:

```bash
cd stockedge100
sha256sum -c governance/STAGE_2_PREREGISTRATION.sha256
sha256sum -c reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256
```

Stage 3 sealed its strategy protocol and gate criteria **before any strategy module existed** — the
seal record carries the module and output counts at seal time that make that claim falsifiable. Its
records also use project-root-relative paths:

```bash
cd stockedge100
sha256sum -c governance/STAGE_3_PREREGISTRATION.sha256
sha256sum -c reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256
```

Stage 3 attempt 2 sealed a new strategy protocol and gate-criteria binding **before any module for its
three candidates existed**. Attempt 1's own modules and outputs are on disk and may not be deleted, so
the seal cannot prove its ordering by counting `strategies/` to zero the way attempt 1 did; it uses
four narrower contamination predicates instead, each with its own definition in the seal record. Two
of those counts legitimately become non-zero **after** sealing — the seal writes its own run record,
and this design session's reports live under `reports/stage3_attempt2/` — and both moves are
anticipated in the sealed definitions. Project-root-relative paths again:

```bash
cd stockedge100
sha256sum -c governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256
sha256sum -c reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256
```

The attempt 2 evaluation session that followed produced its own decision package, whose record also
uses project-root-relative paths. It covers the strategy research report, the machine-readable
decision record, the per-candidate and per-variant results, the test summary, the raw pytest output,
and the artifact manifest — the manifest is covered by this record and excludes itself, and this
record does not cover itself:

```bash
cd stockedge100
sha256sum -c reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256
```

Stage 4 sealed its representative, validation protocol and gate criteria **before any Stage 4
evaluator module or result file existed**, and before any validation observation was read. Its seal
record covers five files — the pre-registration Markdown and JSON and the three `config/` artifacts —
and, like Stage 3 attempt 2, carries the counts at seal time that make the ordering falsifiable.
Three counts legitimately become non-zero **after** sealing: the seal writes its own run record, this
design session's reports live under `reports/stage4/`, and the decision-package builder
`src/stockedge100/reporting/stage4_package.py` is a `reporting/` module that the sealed
`stage_4_evaluator_or_result_modules` predicate counts. The first two are anticipated in the sealed
definitions; the third is **not**, and is disclosed as a governance defect in the pre-registration
report rather than evaded by renaming the file. Both remaining counts were zero at seal time:
`modules_naming_a_stage_4_run_label` and
`stage_4_modules_touching_restricted_data_or_a_broker`, both AST questions rather than text searches,
because a text search over either module would match the words of its own predicate definition.

The evaluation session that followed left the first of those at zero and moved the second, which is
`S4-CONFLICT-7` in the validation report. That predicate's sealed purpose is to prove the
*pre-registration* path cannot reach restricted data or a broker, but its mechanical scope is every
`stage4`-named module, and the evaluator the pre-registration authorized must call a dataset loader.
Its data-access half therefore can never read zero again. The half that matters — broker or network
import, environment-variable read, connection, URL constant — **is still zero**, every hit on the
other half is resolved by name to an authorized read, and the marker test asserting the sealed value
is left **failing on purpose** as the disclosure. It was not weakened, skipped or deleted, the
evaluator was not renamed out of scope, and the seal was not edited after a validation read.

Project-root-relative paths:

```bash
cd stockedge100
sha256sum -c governance/STAGE_4_PREREGISTRATION.sha256
sha256sum -c reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.sha256
sha256sum -c reports/stage4/STAGE_4_VALIDATION.sha256
```

---

## Stage and gate map

The operating instructions and the constitution number the gates differently. The constitution's
ids are authoritative for threshold lookup. The mapping is fixed in
`governance/STAGE_0_VERIFICATION_REPORT.md` §6.3 and repeated here:

| Stage | Purpose | Constitution gate id |
|---|---|---|
| 0 | Constitution freeze and verification | 0 |
| 1 | Data foundation, universe freeze, holdout lock | 1 |
| 2 | Honest backtest engine | 2 |
| 3 | Baselines and strategy-family research | 3 (development admissibility) |
| 4 | Robustness, then the single holdout ceremony | 4 (validation) **and** 5 (holdout) |
| 5 | Portfolio controller / production decision engine | 6 |
| 6 | Alpaca paper trading (≥90 days, ≥30 closed trades) | 7 |
| 7 | Shadow-live validation (≥60 days or ≥20 round trips, longer) | 8 |
| 8 | Live deployment preparation — stops for human authorization | 9 |
| 9 | Limited live execution — only after dated written owner approval | 9 |
| 10 | Controlled expansion — a new generation, new holdout | new |

Stage 4 must clear **two** constitutional gates: robustness thresholds before the holdout is
unlocked, holdout thresholds after.

---

## Repository layout

```
stockedge100/
├── governance/     frozen constitution, freeze hashes, verification and stage decision records
├── config/         versioned, hashed configuration (no secrets, ever)
├── data/
│   ├── raw/         immutable provider payloads exactly as received
│   ├── normalized/  derived, reproducible datasets
│   ├── reference/   calendars, corporate actions, universe reference data
│   ├── manifests/   acquisition manifests and dataset hashes
│   └── quarantine/  anomalies held for explanation — never silently deleted
├── src/stockedge100/
│   ├── audit.py     hashing, manifests, run records (shared by every stage)
│   ├── data/ universe/ backtest/ strategies/ portfolio/
│   └── execution/ broker/ risk/ monitoring/ reporting/
├── tests/          unit / integration / adversarial / regression
├── reports/        human-readable and machine-readable stage decision packages
├── runs/           one reproducibility record per material run
├── logs/           structured operational logs
└── deployment/     runbooks, checklists, incident and rollback procedures
```

Everything under `data/`, `runs/`, and `logs/` is generated and git-ignored. It is reproducible
from the manifests, not from version control.

---

## Installation

Python 3.10 or later.

```bash
python -m pip install -e stockedge100        # or: pip install -r requirements
python -m pytest stockedge100/tests -q
```

Runtime dependencies are declared in `pyproject.toml`. Exact installed versions are recorded in
every run record under `runs/`, because a rerun that produces different numbers must be
attributable.

---

## Reproducibility

This working tree is not a git repository. Repository identity is therefore established by a
**repo state id**: a SHA-256 over the sorted map of tracked source and governance file digests
(`stockedge100.audit.hash_tree` → `tree_digest`). Every material run records the repo state id,
config hash, dataset hashes, dependency versions, seed, command, and output artifact hashes.

Running `git init` here is available on request; it has not been done, and nothing has been
committed.

---

## Safety posture

The system fails closed. No order may be generated or transmitted when data are missing, stale,
duplicated or ambiguous; when the calendar, account state, buying power, or positions are unknown;
when a config or code hash mismatches; when an order is unresolved; or when a kill switch or
drawdown halt is active. A caught exception is never permission to bypass a control.

Live trading requires a separate dated written approval from the project owner after gates 0–8
pass. No prior approval of research, paper trading, or shadow-live operation implies it.

---

## Known limitations (kept current)

Seven sets now, and all of them travel with every downstream result. Data limitations settled at
Stage 1 — full detail and the remaining seven items in
[STAGE_1_DATA_FOUNDATION_REPORT.md](governance/STAGE_1_DATA_FOUNDATION_REPORT.md) §9. Engine
limitations settled at Stage 2 — all twelve in
[STAGE_2_BACKTEST_ENGINE_REPORT.md](governance/STAGE_2_BACKTEST_ENGINE_REPORT.md) §11. Research
limitations settled at Stage 3 — all eight in
[STAGE_3_STRATEGY_RESEARCH_REPORT.md](governance/STAGE_3_STRATEGY_RESEARCH_REPORT.md) §16. Design
limitations settled at Stage 3 attempt 2 — all ten in
[STAGE_3_ATTEMPT_2_DESIGN_REPORT.md](governance/STAGE_3_ATTEMPT_2_DESIGN_REPORT.md) §19. Evaluation
limitations settled at the attempt 2 evaluation — all sixteen in
[STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH_REPORT.md](governance/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH_REPORT.md)
§20. Validation pre-registration limitations settled at Stage 4 — all eleven in
[STAGE_4_VALIDATION_PREREGISTRATION_REPORT.md](governance/STAGE_4_VALIDATION_PREREGISTRATION_REPORT.md)
§20. Validation evaluation limitations settled at the Stage 4 evaluation — all seven in
[STAGE_4_VALIDATION_REPORT.md](governance/STAGE_4_VALIDATION_REPORT.md) §11. An engine cannot be more
trustworthy than its inputs, and a research result cannot be more
trustworthy than the engine, so each list applies to everything downstream of it.

- **Single provider.** Every price comes from one unofficial public Yahoo Finance endpoint via
  `yfinance`. There is no second source to cross-check against, so a systematic provider error would
  pass all 16 validation checks undetected. This is the largest unmitigated risk in the project.
- **Survivorship bias is narrowed, not controlled.** The research universe was prospectively
  restricted to ETFs and sealed before any price was fetched. Residual fund-closure bias remains,
  disclosed and **unquantified**: funds that launched and closed inside the development window are
  absent from a candidate list assembled in 2026. Individual stocks are `PROHIBITED` for
  Generation 1 without a point-in-time constituent source.
- **As-traded price levels are unavailable.** The provider returns split-adjusted OHLC, so any later
  rule involving per-share tick size, whole-share sizing, or a price level must treat this as a
  missing input rather than approximate it.
- No broker credential is configured, so Alpaca tradability and fractional eligibility are
  `UNVERIFIED` for all 34 members and recorded as such rather than assumed. The universe is
  conditional: a member later found non-tradable must be removed and every affected gate re-run.
- **The spread is a constant, not a measurement.** No historical quote data exists, so the engine
  charges 2.5 bps per side on every symbol in every year — almost certainly too narrow in the 1990s
  and too wide today. Slippage is likewise a declared constant, not an observed fill distribution.
- **Partial fills are not modelled, and market-on-next-open is the only order type.** A strategy
  needing limits, stops, or intraday timing is outside what this engine has been validated for.
  Partial fills are a paper-trading observable at gate 7, not a research assumption.
- **The engine was validated against its own sealed spec, not against a second implementation.** The
  independent check is hand arithmetic over one synthetic instrument and eight sessions; no
  cross-implementation comparison exists.
- **One parameterisation per family is not a test of the family.** Attempt 1 ran six candidates, not
  six families, and attempt 2 ran three specifications over three of those same signal forms. Attempt
  1's neighbour runs alone span 0.27 to 3.04 total return for a single candidate, and in attempt 2
  three of C1's four neighbours outperform C1's own primary — which is how much of a result belongs to
  the particular number chosen rather than to the rule. A neighbour may never be promoted, under any
  result.
- **Every attempt 1 candidate was switched off before its window ended**, between 1997 and 2010, by
  the §5.1 research shutdown, so its full-window CAGR, Sharpe and exposure describe a live period
  followed by a long dead one and are not properties of the rule. No attempt 2 primary was switched
  off; one registered attempt 2 neighbour was, on 2020-02-27.
- **Only base costs gate.** Attempt 1 ran base costs alone. Attempt 2 added three declared stressed
  runs at double the trading friction, and they gate nothing because the gating cost model was fixed
  before results — but under that stress C1 returns 0.0018 instead of 0.0986, crosses the 15% level,
  and trips the research shutdown on 2018-02-05. Drawdown is measured at session closes because no
  intraday data exists, so every recorded drawdown is a lower bound and every recorded return is the
  optimistic case. The cost model remains a proxy that cannot be validated before paper trading at
  gate 7.
- **The development window is no longer pristine.** Nine specifications now share it, all nine
  evaluated, across 45 gating variants and 48 declared runs — and attempt 2's design space was
  narrowed by an observed attempt 1 outcome, so the effective search is wider than nine independent
  draws and cannot be bounded by counting runs. New code does not make attempt 2 an independent
  confirmation of anything. Nothing corrects for this numerically; the protection was that an admitted
  candidate must still survive Gate 4, the single sealed holdout read at Gate 5, and the
  duration-based paper and shadow gates. That protection did its job: the representative did not
  survive Gate 4.
- **The admitted margin is thin, and the risk rule is not a bound.** C1 clears the 15% ceiling by 33
  basis points (`0.1467` against `0.15`) — a margin smaller than the difference between its base and
  stressed cost runs. Its `sma_long 150` neighbour breaches the ceiling outright and trips the §5.1
  shutdown on 2020-02-27. And the 8% per-position loss control is referenced to a session close and
  filled at the next open, so a gap can exceed it: it constrains the intended exit, not the realised
  loss. Neither admitted candidate beats buy-and-hold SPY on either benchmark series.
- **The Stage 4 representative was chosen by a rule this project authored, not by the constitution.**
  The constitution mandates no selection rule between two admitted candidates, so one was written,
  applied in full to both, and sealed before any validation observation existed. It is return-blind,
  which constrains its output but not the choice of predicate: a different return-blind predicate
  might have selected differently, and no correction for that freedom exists. The survivor had no
  drawdown headroom to spare — its largest non-breaching development neighbour sat 34 basis points
  below the same 15% level Gate 4 imposes — and neither admitted candidate reached the frozen 0.50
  Sharpe floor on development data, so a Gate 4 `FAIL` was the disclosed expectation rather than a
  surprise. It is now the recorded outcome, on the Sharpe floor and on fold stability. **What that
  fail settles is narrow: one representative, on one window, under one parameterisation. It is not
  evidence that C1 would have failed, and C1 cannot now be tested — the validation window is spent
  and its information is known.**
