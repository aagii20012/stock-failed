# Stage 10 — Generation 2 charter

| Field | Value |
|---|---|
| Document id | `SE100-GOV-2001` |
| Title | Generation 2 charter — controlled expansion to a genuinely cross-sectional strategy |
| Project | StockEdge100 |
| Generation | 2 |
| Generation id | `SE100-GEN2-7394207c543401e2` |
| Status | `OPEN` |
| Authored (UTC) | 2026-08-15T03:40:41Z |
| Constitution ref | `SE100-GOV-0001` v1.0.0 (FROZEN) |
| Supersedes | Nothing. Generation 1 is closed, not replaced. |
| `live_trading_authorized` | `false` |

---

## 1. Why Generation 2 exists

Generation 1 reached constitutional Gate 4 and failed it:

> `FAIL — STAGE_4_STRATEGY_REJECTED_IN_VALIDATION`
> — `reports/stage4/STAGE_4_VALIDATION.json`, field `verdict`

The validated representative was `SE100-S3A2-C2-MEANREV-RA1`, selected under
`config/stage4_representative_selection.json` (`SE100-CFG-4003`) by a declared-variant
research-shutdown screen. Its measured validation-window figures, read from
`reports/stage4/STAGE_4_VALIDATION.json`, were:

| Measurement | Value | Field read |
|---|---|---|
| Total return (base costs) | `0.0215` | `run_evidence.base.total_return` |
| Sharpe | `0.2025294206503088680547420121230750` | `run_evidence.base.sharpe` |
| Total return (stressed costs) | `0.0015` | `run_evidence.stress.total_return` |
| Positive folds | 7 of 12 | `gate_conditions.S4-C6.evidence.condition_evidence` |
| Symbols traded | `['SPY']` | `run_evidence.runs[0].measure.symbols_loaded` |
| P&L contribution | `{'SPY': '2.15'}` | `run_evidence.runs[0].measure.contribution_by_symbol` |

The last two rows are the finding this charter is built on. Generation 1 declared a
34-symbol research universe, and the candidate that survived to validation traded exactly one
symbol in it. Every measurement above is a measurement of a single-symbol timing rule on SPY
under a 15%-drawdown ceiling. The universe was never used.

That is not a defect in the Generation 1 evidence — the evidence is correct and it is preserved
unchanged — but it means the Generation 1 research question was answered narrowly. Whether the
frozen universe carries a *cross-sectional* edge was never tested, because no admitted candidate
ever selected among its members.

## 2. The single variable that changes

Generation 2 changes **one** thing, and states it here so any later reader can check that nothing
else moved:

> **Portfolio breadth and cross-sectional selection.** A Generation 2 strategy must select among
> multiple members of the frozen universe and may hold more than one risky position at a time.
> Generation 1 held at most one risky position and, in the candidate that reached validation,
> collapsed onto a single symbol.

Held constant, deliberately and by reference to the Generation 1 artifact that fixes each one:

| Held constant | Value | Source (Generation 1, unmodified) |
|---|---|---|
| Data provider | Yahoo Finance via `yfinance` | `config/stage1_data_source.json` |
| Universe | 34 ETFs, `SE100-U1-d4917c2f7f1cd834` | `governance/STAGE_1_UNIVERSE.json` |
| Account model | USD 100 cash, long-only, fractional shares | `config/stage2_cost_model.json` → `account` |
| Bar frequency | Daily | constitution §3 |
| Execution assumption | Decision at close *t*, earliest fill at open *t+1* | `config/stage2_cost_model.json` → `execution` |
| Cost model | 2.5 bps half-spread + 2.5 bps slippage per side, 2× stress, SEC §31 and FINRA TAF as sealed | `config/stage2_cost_model.json` → `frictions` |
| Gross exposure ceiling | 95% of equity, 5% minimum cash | constitution §3, `account` |
| Research shutdown | 15% below the running high-water mark, `LIQUIDATE_AT_NEXT_OPEN_AND_BLOCK_ENTRIES` | constitution §5.1, `risk` |
| Gate 3 thresholds | Unchanged; all seven conditions evaluated | `config/stage3_gate_criteria.json` |
| Development window end | 2021-07-31 | `governance/STAGE_1_HOLDOUT_LOCK.json` |

The cost model is **not** revised. Where Generation 2 needs a value the Generation 1 cost model
fixes at a Generation-1-specific number — there is exactly one such value, the account's
`max_open_risky_positions` — the derived file records the Generation 1 digest it was derived from,
changes only that field, and says so in its own text. Nothing else in the cost model is touched.

## 3. Universe re-check, and what it is not

Section 1 of the operating instruction authorizes "a liquidity/eligibility re-check on development
data, never a symbol add/drop based on any performance figure". The re-check applies the four
`measured_on_development_window_only` rules already sealed in `config/stage1_universe_spec.json`
(`MIN_DEVELOPMENT_SESSIONS`, `MEDIAN_DOLLAR_VOLUME`, `MIN_CLOSE`, `DATA_QUALITY`) to
development-window rows only.

**Result: all 34 symbols pass. No symbol is added, dropped, or substituted.** The binding figures
are recorded in `STAGE_3_G2_ROTATION_PROTOCOL.md` §3 and re-measured mechanically at seal time.

The re-check measures inception date, session count, median dollar volume, and minimum close. It
measures no return, no drawdown, no Sharpe, and no profit factor of any kind. The distinction
matters because the latest inception date among the 34 (VEA, 2007-07-26) is what sets Generation 2's
run start, and a reader is entitled to know that this number was obtained from an eligibility
measurement and not from a performance sweep.

## 4. What Generation 2 does not change

- Generation 1's artifacts. Every file under `governance/`, `config/`, `reports/`, `runs/`, and
  every existing `.sha256` record is read-only for the whole of Generation 2. Generation 2 writes
  only into `governance/generation_2/`, `config/generation_2/`, `reports/generation_2/`, new
  modules under `src/` and `tests/`, and new append-only files under `runs/`.
- Generation 1's sealed final holdout, 2024-08-01 → 2026-07-31. It is never read, by any person or
  by any code written under this charter, for any reason, at any stage. It was read once, at
  Generation 1's own holdout gate authority, and it is spent.
- The frozen constitution. Where this charter and the constitution differ, the constitution's value
  governs wherever it is more restrictive, and the divergence is recorded in §6 below.
- `live_trading_authorized`, which stays `false`.

## 5. Generation identity

`SE100-GEN2-7394207c543401e2` is the first sixteen hexadecimal characters of the SHA-256 of the
canonical JSON serialisation of the following map. Every input already existed on disk before any
Generation 2 file was written, so the id can be recomputed by a reader and contains no digest of
itself:

```
{"constitution_ref": "SE100-GOV-0001",
 "constitution_sha256": "b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5",
 "cost_model_sha256": "f62d98436445cfc436463765ff6006dd234a3082ddf429992296645e697586e2",
 "development_window": ["1993-01-29", "2021-07-31"],
 "generation": 2,
 "generation_1_terminal_verdict": "FAIL - STAGE_4_STRATEGY_REJECTED_IN_VALIDATION",
 "holdout_window": ["2026-08-01", "2028-07-31"],
 "project": "StockEdge100",
 "single_variable_changed": "PORTFOLIO_BREADTH_AND_CROSS_SECTIONAL_SELECTION",
 "universe_sha256": "01601a60fa950a2429f72a2e9f627ec5af4c1853d1b47ffab35e81debc7eb67a",
 "universe_version": "SE100-U1-d4917c2f7f1cd834",
 "validation_window": ["2021-08-01", "2024-07-31"]}
```

Full identity digest: `7394207c543401e20fc80f3550c8a6a5aae4de622f2c28eb81dfa116f8b4ae52`.
The derivation is implemented in `stockedge100.reporting.g2_partition_lock.generation_identity()`
and asserted by test; this block is the human-readable copy of that function's input, not a second
source of truth.

## 6. Conflicts found

Recorded, not silently resolved. Each states what the instruction said, what the artifact on disk
says, which value was adopted, and why.

### G2-CONFLICT-1 — the cited constitution section does not exist

**Instruction.** Generation 2 is described as proceeding "under Stage 10 of the frozen constitution
(`governance/STAGE_0_CONSTITUTION.md` §19)".

**On disk.** `governance/STAGE_0_CONSTITUTION.md` has thirteen sections. There is no §19, and the
string "Stage 10" appears nowhere in it. The only occurrence of Stage 10 anywhere in the frozen or
sealed tree is one row of the stage/gate map in `README.md` line 245:

> `| 10 | Controlled expansion — a new generation, new holdout | new |`

— where the constitution gate id is the literal word `new`, meaning *no constitutional gate has been
written for this stage*.

**Adopted.** The citation is not repeated as though it existed. Generation 2 proceeds as a
controlled expansion in the sense of that README row, and the authorizing instrument is the owner's
written instruction, not a constitutional section. Constitution §12 is explicit that the
constitution "does not authorize … expanding beyond the Generation 1 scope"; that is a statement
about what the constitution authorizes, and it is accurate. Generation 2 is authorized by its owner
and constrained by the constitution, which is a different relationship from the one Generation 1
had, and this charter says so rather than implying constitutional cover it does not have.

**Consequence for the reader.** Gate 3 for Generation 2 is the constitution's Gate 3, adopted with
its thresholds unchanged. There is no constitutional Gate 10 to satisfy and none is claimed.

### G2-CONFLICT-2 — portfolio breadth

**Constitution §3.** "Portfolio breadth | One open risky position **in Generation 1**; otherwise
cash." The section is titled "Fixed scope for Generation 1".

**Generation 2.** Holds up to *k* positions, *k* ∈ {1, 2, 3}.

**Adopted.** The rule is scoped by its own text to Generation 1, so Generation 2 holding more than
one position does not contradict §3. What it does contradict is §12's "expanding beyond the
Generation 1 scope", which is the non-authorization recorded in G2-CONFLICT-1. The more restrictive
constitutional values that *are* generation-independent are carried forward unchanged and enforced
in code: 95% maximum gross exposure, 5% minimum cash buffer (constitution §3), and the 15%
research-shutdown drawdown (§5.1). Generation 2 additionally adopts a 50% single-position
concentration ceiling, which is Generation-1-consistent (`config/stage3_attempt2_strategy_protocol.json`
→ `risk_architecture.RA1-1.rule`: "f_base = 0.50") and is more restrictive than anything the
constitution requires.

### G2-CONFLICT-3 — one governance stage per session

**Project rule.** `CLAUDE.md`: "One governance stage per session. Finish the stage, issue exactly
one verdict, stop."

**Instruction.** This session must author a charter, a partition lock, a Stage 3 pre-registration,
and then run and report Stage 3 — four stage-shaped units of work — while issuing exactly one
verdict, at Stage 3.

**Adopted.** The instruction, per the precedence order in `CLAUDE.md` §Precedence (constitution,
then the operating prompt, then `CLAUDE.md`). The protection the one-stage rule exists to provide is
that a pre-registration cannot be written after its results are known. That protection is preserved
mechanically rather than by session boundary: the Stage 3 pre-registration is sealed by a program
that refuses to run if any Generation 2 strategy module, result artifact, or run record exists, and
records the counts it measured inside the sealed record. Exactly one verdict is issued, at Stage 3.

### G2-CONFLICT-4 — `governance/generation_2/**` is outside `repo_state_id`

**On disk.** `REPO_STATE_PATTERNS` in `src/stockedge100/reporting/stage_package.py` includes
`governance/*.md`, `governance/*.json`, `governance/*.sha256` — all single-level globs — and
`config/**/*.json`, which is recursive.

**Consequence.** Files written to `config/generation_2/` **are** covered by `repo_state_id`. Files
written to `governance/generation_2/` are **not**.

**Adopted.** `REPO_STATE_PATTERNS` is not changed. It is described in its own source as "Kept
byte-identical to the Stage 0 definition", and widening it would change the meaning of every
`repo_state_id` recorded since Stage 0 — every historical value would then describe a different
pattern set from the one that produced it. Generation 2's governance files are covered instead by
their own `.sha256` records, by the Stage 3 artifact manifest, and by the `output_artifact_hashes`
of the `runs/` records that wrote them. The gap is real, is disclosed here, and is the reason the
partition lock and the rotation protocol each carry a checksum record of their own.

### G2-CONFLICT-5 — five declared Gate 3 thresholds against the constitution's seven conditions

**Instruction.** "Gate 3 thresholds: unchanged from constitution: net return positive; max drawdown
≤15%; profit factor ≥1.10; closed trades ≥30; best-trade-removed return still positive." Five.

**On disk.** `config/stage3_gate_criteria.json` (`SE100-CFG-3002`) declares **seven** conditions,
S3-C1 through S3-C7, and already resolves this exact discrepancy as `S3-CONFLICT-1`: "The Markdown is
authoritative and is the more restrictive of the two. All seven conditions are evaluated and all
seven must pass." The five named in the instruction are exactly the five in
`frozen_gate_json_companion_verbatim.thresholds`; the two additional conditions are S3-C6
(instrument-concentration of P&L ≤ 50%) and S3-C7 (robustness-neighbour sign stability).

**Adopted.** All seven. The instruction says the thresholds are "unchanged from constitution", and
unchanged means seven. Generation 2 applies the identical resolution Generation 1 recorded, for the
identical reason. Two of the seven require a Generation-2-specific *measurement procedure* because
their Generation 1 procedures are written in terms of a one-position portfolio; those redefinitions
are recorded as G2-CONFLICT-6 and G2-CONFLICT-7 in `STAGE_3_G2_ROTATION_PROTOCOL.md` §8, sealed
before any variant runs, and they change no threshold.

## 7. Windows

The binding partition is `STAGE_1_G2_PARTITION_LOCK.md` / `.json` in this directory. Summarised:

| Window | Bounds | State under this charter |
|---|---|---|
| Development | earliest available history → 2021-07-31 | **OPEN** — the only window any code written under this charter may read |
| Validation | 2021-08-01 → 2024-07-31 | **LOCKED** — reused from Generation 1; carries a disclosed multiplicity cost |
| Generation 2 holdout | 2026-08-01 → 2028-07-31 | **SEALED — HAS NOT YET ELAPSED.** Today is 2026-08-15; 23 of its 24 months are still in the future. |
| Generation 1 holdout | 2024-08-01 → 2026-07-31 | **SPENT AND PROHIBITED** — read once at Generation 1's holdout authority, never readable again by anyone |

The Generation 2 holdout may not be shortened, moved, or partially read, and may not be read before
2028-08-01 even in part. Its start date, 2026-08-01, has already passed in calendar time; that makes
the *beginning* of the window observable and changes nothing, because the window is read once, whole,
at the constitutional holdout gate.

## 8. Explicit non-authorizations under this charter

This charter does not authorize:

- reading, editing, deleting, regenerating, or reinterpreting any Generation 1 artifact;
- reading Generation 1's holdout window (2024-08-01 → 2026-07-31) for any purpose;
- reading Generation 2's holdout window (2026-08-01 → 2028-07-31) before that period has completed
  in real calendar time;
- reading any session dated 2021-08-01 or later in any Stage 3 work;
- Stage 4 validation, which requires a separate, explicitly authorized session;
- accessing an Alpaca credential, placing an order of any kind, or connecting to any broker;
- paper trading, shadow-live trading, or live trading;
- revising the cost model;
- adding or removing a universe member on the basis of any performance figure;
- claiming expected income, profit, or return for any period.

## 9. Authorized next activity

Stage 1 (Generation 2): partition lock. Then Stage 3 (Generation 2): pre-registration, then
implementation and development-window evaluation, then exactly one verdict. Stop there.

---

*This document contains no tree digest and no digest of itself. Digests of the files it names are in
`STAGE_1_G2_PARTITION_LOCK.json`, `STAGE_3_G2_ROTATION_PROTOCOL.json`, and the corresponding
`runs/` records.*
