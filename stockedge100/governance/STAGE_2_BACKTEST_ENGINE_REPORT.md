# StockEdge100 — Stage 2 backtest engine report

| | |
| --- | --- |
| Document id | `SE100-GOV-2000` |
| Project | StockEdge100, Generation 1 |
| Stage | Prompt Stage 2 — backtest engine. Constitution **gate 2, backtest_engine_validity**. |
| Governing document | `SE100-GOV-0001` v1.0.0, FROZEN, unmodified by this stage |
| Pre-registration | `SE100-GOV-0005`, sealed 2026-08-08T15:12:15Z, before any engine module existed |
| Authored (UTC) | 2026-08-09T01:21:27Z |
| Verdict | **PASS — STAGE_2_BACKTEST_ENGINE_VALIDATED** |
| `live_trading_authorized` | `false` |

`run_id` and `repo_state_id` for this stage are **not** written here: `repo_state_id` covers
`governance/*.md`, so a digest embedded in this file would be invalidated the moment the file was
saved. Both values live in
[reports/stage2/STAGE_2_BACKTEST_ENGINE.json](../reports/stage2/STAGE_2_BACKTEST_ENGINE.json) and in
the append-only record under [runs/](../runs/).

---

## 1. What this stage was allowed to do

Build a backtest engine and prove it honest. Nothing else.

**No strategy exists at the end of this stage.** Every run in the evidence is either a synthetic
fixture, a benchmark, or a deliberately trivial probe — a buy-and-hold and an always-cash agent whose
only purpose is to exercise engine paths. No signal was searched for, no parameter was tuned, no
instrument was selected on the basis of a result, and no performance number in this report is
offered as a research finding. §10 says so again about the one run that most looks like one.

The validation window was not read. The holdout remains `SEALED` and was not opened, sampled, or
counted. Every run in this stage is confined to the development window locked at Stage 1,
1993-01-29 → 2021-07-31, and the engine refuses a run whose bounds fall outside it.

Nothing frozen was edited. The Stage 0 constitution and its companion, and the Stage 1 universe,
holdout lock, and freeze record, were opened read-only and re-verified before anything else ran; the
verification detail is in the decision record under `constitution.freeze_verification` and
`stage1.freeze_verification`.

No money was spent, no account was created, and no credential was read. Constitution §6.4 forbids
all four until a later gate.

## 2. The order things happened in, and why it is the whole argument

An engine that is checked against expectations written after its first output has not been checked
against anything. So the order is the evidence, and it was:

1. **Seal the cost model.** `config/stage2_cost_model.json` (`SE100-CFG-2001` v1.0.0) — commissions,
   spread, slippage, regulatory fees, rounding directions, the stress multiplier, the stale-data
   policy, and the account limits — was written and digested before a single engine module existed.
2. **Seal the acceptance spec.** `config/stage2_engine_spec.json` (`SE100-CFG-2002` v1.0.0) — the
   twelve defect classes with the mutation and detector for each, the twelve invariants, the
   determinism protocol, the benchmark tolerance, and the complete hand-calculated fixture
   arithmetic — likewise.
3. **Record both digests in governance.** `governance/STAGE_2_PREREGISTRATION.json` recorded
   `sealed_before_any_engine_code: true` and, as the check that makes the claim falsifiable,
   `engine_modules_present_at_seal_time: 0`.
4. **Then write the engine**, against a loader that refuses a config whose digest has drifted.

The fixture arithmetic matters most here. FIXT's entry price, share quantity, charged notional,
dividend credit, exit proceeds, both regulatory fee components, and final equity were computed by
hand and written into the sealed spec — with the derivation of each — while there was no engine to
copy them from. When §8 reports that engine output matches them line by line, the comparison is
against numbers that could not have been back-filled from an engine run.

The sealed digests are recorded in
[governance/STAGE_2_PREREGISTRATION.sha256](STAGE_2_PREREGISTRATION.sha256) and re-verified in the
decision record. `stockedge100.backtest.config.load_stage2_config()` recomputes them on every load
and raises `PreRegistrationViolation` on any drift, so a silently edited cost assumption stops the
engine rather than changing a result.

## 3. The cost, execution, and accounting model

Constitution §7 requires a complete friction assumption, a conservative documented proxy wherever
data is missing, and a stressed run at twice the whole assumption. What was sealed:

| | |
| --- | --- |
| Decision point | the close of session *t* |
| Earliest fill | the **open** of session *t+1*; same-close execution is structurally impossible |
| Order modelled | `MARKET_ON_NEXT_OPEN`, one session of life, never carried forward |
| Commission | `0.00` — Alpaca charges none on US equities and ETFs |
| Half spread | 2.5 bps per side, `PROXY_CONSERVATIVE_CONSTANT` |
| Slippage | charged adversely on every fill, buys above and sells below the reference |
| SEC §31 fee | 0.0000278 of sale principal, **sells only**, rounded up |
| FINRA TAF | 0.000166 per share, capped at 8.30, **sells only**, rounded up |
| Stress scenario | ×2.0 on the *complete* assumption, cap included |
| Account | 100.00 USD cash, long-only, no margin, ≤ 1 open risky position, 5% cash buffer |

Three choices are worth naming because each is a proxy that could have been dressed up as a
measurement, and was not.

**The spread is a constant.** No historical quote data exists in the Stage 1 dataset, so 5.0 bps
round trip is applied uniformly to every symbol in every year. For a large ETF this is wider than a
modern quoted spread and narrower than a 1990s one. It is a documented constant, not an estimate,
and it is carried into §11 as a limitation rather than presented as calibration.

**The regulatory rates are fixed at one value each.** The statutory §31 rate has been reset many
times across a 28-year window; using one number is a predeclared proxy whose error direction is
recorded rather than hidden.

**The TAF is charged on adjusted share counts.** Stage 1 established that as-traded price levels are
not recoverable from this provider. Adjusted share counts are ≥ as-traded counts for any
split-adjusted series, so this over-charges. That direction was chosen deliberately and sealed.

The stress multiplier applies to every component including the TAF cap. Doubling the per-share rate
while leaving the cap fixed would have made the stressed run *cheaper* than 2× for large orders — a
soft stress test that looks like a hard one.

All arithmetic is `Decimal` under a pinned 34-digit context (`prec=34, ROUND_HALF_EVEN`) applied by
an `@exact` decorator, so no result depends on binary floating-point rounding or on the ambient
context of whatever called the engine. Every rounding step is adverse to the account: quantities
floor, buy notional and every regulatory fee round up, sale proceeds and dividend credits round down.

## 4. The engine

Ten modules under `src/stockedge100/backtest/`. The two that carry the gate are the market view and
the order lifecycle.

**The market view is bounded at construction.** A probe is handed a view whose visibility limit is
the session it is deciding on; asking it for a later bar raises `LookAheadError`. The bound is not a
parameter the caller can widen — that is what makes it structural rather than a convention the next
author can forget.

**A fill is a different object from a decision, and the timing rule is enforced twice.** `Order`
raises `FillTimingError` at construction if its fill session is not strictly later than its decision
session, and the engine raises again at execution. A rejected order is not silently dropped: it is
recorded with one of ten sealed reason codes and provably leaves cash, positions, and equity
byte-identical to their pre-order state.

**The portfolio reconciles after every movement**, not once at the end of the run. Twelve invariants
are asserted on every event: `CASH_NON_NEGATIVE`, `CASH_CONSERVATION`, `CASH_IS_WHOLE_CENTS`,
`NO_LEVERAGE`, `LONG_ONLY`, `MAX_ONE_RISKY_POSITION`, `ADVERSE_PRICE`, `ADVERSE_ROUNDING`,
`POSITIVE_COST`, `FILL_AFTER_DECISION`, `FILL_ON_SESSION`, `NO_POSITION_PAST_LAST_BAR`.

**Missing data fails closed.** A fill requires a bar on the fill session itself; if the exchange
calendar reports a session and the symbol has no bar, the order is rejected `STALE_PRICE` rather than
filled at yesterday's price. Equity still has to be computed on such a session, so it is marked at
the last known close and the point is **flagged** — the flag is counted and reported, never dropped.
A stale run longer than the Stage 1 `MISSING_SESSION_RUN` limit halts the run outright with
`DataIntegrityHalt`.

Constitution §5.1's 15% research shutdown is enforced inside the engine, not left to the caller: on
breach the engine liquidates and refuses every later entry, including one that has already reached
the execution path.

## 5. Determinism — condition 1

Five cases, each run twice from a cold start, compared on SHA-256 digests of canonical JSON over the
trade list and the equity curve. **All five identical.**

| Case | Trades digest | Identical |
| --- | --- | --- |
| `FIXT_BASE` | `8e1fd4a4…03de` | yes |
| `FIXT_STRESSED` | `4e3f98e2…9dd2` | yes |
| `PROBE_BUY_AND_HOLD_SPY_development` | `29d4825c…0f7f` | yes |
| `PROBE_ALWAYS_CASH_development` | `72142784…cbec` | yes |
| `PROBE_BUY_AND_HOLD_SPY_symbols_supplied_in_reverse_order` | `29d4825c…0f7f` | yes |

Two properties make that table mean something.

The digest **carries no run identity** — no run id, no timestamp, no label, no path — which is
asserted by its own test. Without that, two runs would compare equal for a reason that has nothing to
do with the engine.

The digest **discriminates**: base and stressed costs produce different digests, so equality is a
falsifiable claim rather than a constant. The last row is the same digest as the third by design —
supplying the symbols in the opposite order changes nothing, which is the specific non-determinism
that dictionary iteration order used to introduce.

## 6. Look-ahead — condition 2, structural half

Structurally, §4: the visibility bound. Empirically: the run is executed twice over SPY, once on the
full series and once with **every bar after the run end deleted** — run end 2000-12-29, **6437 bars
removed**. Both digests are unchanged (`29d4825c…0f7f` trades, `061e810e…bb53` equity).

The check has a companion that is easy to omit and worthless to omit: a test asserts that the
truncation *actually removed bars*. A truncation that deleted nothing would pass against an engine
that peeks, and would look exactly like this table.

## 7. Defect detection — condition 2

The sealed spec declares twelve defect classes, each with the mutation that introduces it and the
detector that must catch it. All twelve are exercised in
[tests/adversarial/test_stage2_defects.py](../tests/adversarial/test_stage2_defects.py), and the
evidence harness AST-parses that file to confirm each declared class names tests that exist — it does
not compose test ids from a naming convention, which would report success for tests nobody wrote.

The standard is two-sided: a class counts as covered only if the **clean** engine passes and the
**mutated** engine is caught. Three clean controls sit at the top of the file — a clean fixture run, a
correctly applied split, a correctly applied dividend — so a failure below them is attributable to
the injected defect and not to the harness.

The full class-by-class table is in
[reports/stage2/STAGE_2_TEST_SUMMARY.md](../reports/stage2/STAGE_2_TEST_SUMMARY.md). Two mutations
deserve naming here.

**The split mutation is dataset-specific.** Stage 1 *measured* that this provider returns
split-adjusted OHLC. Therefore a split must **not** change the share count, and the guard has to fire
on a series where it does — the opposite of the guard a project on as-traded prices would write.
Getting this backwards would silently double or halve a position on every split in the window.

**The slippage guard lives downstream of the code it guards.** A guard sitting inside the price
function is deleted by the same mutation that introduces the defect, so it can never catch it. The
adverse-price assertion is made at the fill, and the test replaces the price function wholesale to
prove the assertion survives its removal.

## 8. Hand-calculated fixtures — condition 3

FIXT is a synthetic eight-session instrument. Its entry fill session, exit fill session, effective
prices, share quantity, charged notional, cash after each leg, dividend credit, each regulatory fee
component, and final equity were hand-derived into the sealed spec before the engine existed.

**All checks match: 20 for `BASE`, 19 for `STRESSED`.** The comparison is line by line, not on the
final equity alone — two compensating errors satisfy a final-equity check and fail this one.

Four properties are asserted beyond equality. The entry pays no regulatory fee and the exit pays
both, because §31 and the TAF are sell-side. The stressed scenario leaves the account strictly worse
off than the base one. The closed trade reconciles against its own legs. And no decision ever fills
on its own session.

## 9. Benchmark reconciliation — condition 4

SPY total return is computed two ways over 1993-01-29 → 2021-07-30 across **115 dividends**:

| | |
| --- | --- |
| Method A — adjusted-close ratio | `15.99666381615945001616471638324911` |
| Method B — explicit share accumulation, never consulting an adjusted close | `15.99666027184343712208367222872284` |
| Relative difference | `2.215659498522246340035879336605371E-7` |
| Sealed tolerance | `1e-6` |
| **Reconciles** | **yes** |

The two methods are an arithmetic identity under the adjustment convention Stage 1 measured —
`adj_t = close_t × Π_{s>t}(1 − D_s/close_{s−1})` forces reinvestment at `close_{s−1} − D_s`. The
residual is accumulated decimal rounding over 115 events, not a modelling disagreement. Because the
post-window factors cancel in the ratio, the identity must also hold on sub-windows, and it is
checked on four of them.

That sub-window check states the sealed tolerance on the **growth factors** rather than on the
returns, and the test says why in its docstring: over 2005–2009 the return is 0.0246, so dividing an
absolute agreement of 3.8e-7 by it reports 1.6e-5 — a number that measures how short the window is,
not whether the engine reconciles. The sealed `reconciles(1e-6)` check on the full development window
runs unchanged; nothing was loosened to make this pass.

Three further reconciliations, all passing: the cash and do-nothing benchmarks return **exactly**
`"0"` over 7178 sessions with zero trades — exactly, not approximately, which is the check that
catches a stray cost applied to an account that never traded — and the always-cash probe leaves the
equity curve flat with zero trades.

The **tradable** SPY buy-and-hold — a real USD 100 cash account rather than an index — is reported
under both readings of the §5.1 research shutdown, because the shutdown is written for a strategy and
this is a benchmark. Both readings finish strictly below the index, as they must:

| Reading | Total return | Final equity | Fills |
| --- | --- | ---: | ---: |
| With research shutdown | `1.274` | 227.40 | 2 (shutdown 1998-08-31) |
| Without research shutdown | `10.1852271074553927876` | 1118.52 | 1 (position still open) |

Against an index total return of 15.997, the shortfall has three named causes and no unexplained
residue: only 94.99 of the 100.00 is ever invested (the 5% buffer and the budget safety margin are
never deployed); dividends are credited to cash and never reinvested, because a re-entry rule would
be a strategy decision this stage has no authority to make; and execution friction is charged on
every fill. The sealed check passes under both readings, so the ambiguity does not touch the gate.

## 10. The reference probe run is not a research result

The evidence file reports metrics for `PROBE_BUY_AND_HOLD_SPY` over the development window: 7178
sessions, 100.00 → 227.40, total return `1.274`, CAGR `0.0292`, max drawdown `0.1764`, Sharpe
`0.5355` at a 0.00 risk-free rate, exposure fraction `0.1966`, 1 closed trade, research shutdown
triggered 1998-08-31, profit factor **undefined** (no losing closed trade).

It is reported because a metrics module that has never produced a number is not evidence that the
metrics module works. It is **not** a research result. It is a single asset, held by a probe that
takes no decision, over the window strategies will later be developed on, and its shutdown at
1998-08-31 means it spent four fifths of the window in cash. Reading it as a finding about
buy-and-hold, about SPY, or about anything else would be exactly the error this governance exists to
prevent. The profit factor is left `null` with a stated reason rather than defaulted to a number,
since a fabricated denominator is worse than an absent metric.

## 11. Limitations that survive this stage

1. **The spread is a constant, not a measurement.** 2.5 bps per side for every symbol in every year.
   Almost certainly too narrow in the 1990s and too wide today. No quote data exists to do better.
2. **Slippage is a modelled constant**, not drawn from any observed fill distribution.
3. **Partial fills are not modelled.** An order fills in full or not at all. Modelling a partial-fill
   distribution would be inventing one; it is a Gate 7 paper-trading observable.
4. **Market-on-next-open is the only order type.** No limits, no stops, no intraday timing. Any
   strategy needing them is out of scope for this engine as validated.
5. **The regulatory rates are single fixed values** across 28 years of rate changes.
6. **The TAF is charged on adjusted share counts** and therefore over-charges, by a margin that grows
   with the number of splits behind the fill.
7. **The cash benchmark pays 0%.** No T-bill series was acquired. This is conservative for judging
   cash and generous for judging a strategy that must beat it.
8. **Every Stage 1 data limitation is inherited whole** — single provider, unquantified residual ETF
   closure bias, split-adjusted-only price space, no as-traded prices, and the one disclosed
   adjustment-consistency failure. An engine cannot be more trustworthy than its inputs.
9. **Delisting is enforced but untested against a real delisting**, because the frozen universe
   contains no delisted symbol. The guard is exercised on synthetic series only.
10. **Validation is against the sealed spec, not against a second independent engine.** No
    cross-implementation comparison was performed. The hand calculations are the independent check,
    and they cover one synthetic instrument over eight sessions.
11. **The dividend model credits cash and never reinvests.** Correct for an engine and a real
    constraint on any strategy built on it.
12. **The reference probe run is not a research result** (§10), and nothing downstream may cite it as
    one.

## 12. Conflict found between frozen artifacts

`STAGE_0_CONSTITUTION.json` records gate 2 as `{"id": 2, "name": "backtest_engine_validity",
"fail_result": "BACKTEST_ENGINE_NOT_VALIDATED"}` — with **no `pass_result`**, while the Markdown gate
table in §9 is complete. This is the same defect Stage 1 recorded for gate 1; per the precedence rule
the Markdown governs.

Neither frozen file was edited. The pass reason code below is the affirmative of the recorded fail
token, carrying the stage prefix Stage 0 established with `STAGE_0_CONSTITUTION_VERIFIED` and Stage 1
followed. The derivation is recorded in the decision record under `verdict_token_derivation` so a
later reader can see it was chosen, and on what basis, rather than assumed.

## 13. No separate Stage 2 freeze record, and why

Stage 1 issued `STAGE_1_FREEZE.sha256` because it produced governance artifacts — the universe and
the holdout lock — that later stages consume and must not silently change. Stage 2 produces no such
artifact. Its durable outputs are the sealed configs, already covered by
`STAGE_2_PREREGISTRATION.sha256`, and its code, whose identity is the `repo_state_id` recorded in the
decision package alongside a `.sha256` record over every file the package produced.

A second freeze record would restate digests already recorded and add a third place they could
disagree. The absence is a decision taken here on the record, not an omission.

## 14. Tests

**273 passed, 0 failed, 0 skipped.** The 27 Stage 0 tests and the 113 Stage 1 tests are unmodified;
Stage 2 adds 133 — 54 unit, 42 adversarial, 37 integration.
Detail: [reports/stage2/STAGE_2_TEST_SUMMARY.md](../reports/stage2/STAGE_2_TEST_SUMMARY.md).
Raw output: [reports/stage2/pytest_stage2_output.txt](../reports/stage2/pytest_stage2_output.txt).

No test was weakened, skipped, `xfail`ed, or removed to make this gate pass. `tests/conftest.py` was
not touched; every Stage 2 fixture is defined locally. No test writes into `data/`, `governance/`,
`config/`, or `reports/`.

Each of the four gate conditions is asserted **twice**: directly against the engine, and against
`backtest/harness.py`, which is what the evidence file and this report quote. The second form is not
redundant — a summary boolean that was true because the harness never compared anything would be
worse than no evidence at all, so every harness assertion reaches past the flag to the digests,
counts, and differences underneath it.

The engine validation evidence is reproducible: two runs at different `generated_utc` values produced
the identical `evidence_digest` `9af271e4…317b`, which covers every field of the file except its own
entry and the timestamp. That the findings digest is stable while the timestamp moves is the
statement that the output is a function of code and data only.

### 14.1 A defect the suite did not catch, and what closed it

The first build of this stage recorded a different `evidence_digest`. Post-build verification
recomputed the digest from the written file, following the file's own `evidence_digest_covers`
description literally, and got a value that did not match the one recorded there. The writer had
appended that description *after* taking the digest, so the recorded digest excluded three fields
while the description named two. Every finding was correct and every number in this report was
unaffected; what was wrong was that the file asserted a coverage it did not have, which is exactly
the class of discrepancy the digest exists to expose — occurring in the digest itself.

It is worth stating plainly that 270 passing tests did not find this. Only performing the
recomputation found it. The fix moves the field-assembly into a single `finalize()` function that
seals the description before hashing, and adds the three unit tests that would have caught it
(recompute from the sealed body; vary only the timestamp and require no movement; tamper with each
non-excluded field in turn and require movement). Those three tests are the difference between the
270 of the first build and the 273 above.

Because `src/**/*.py` and `tests/**/*.py` are both `repo_state_id` patterns, the repair invalidated
the first decision package and forced a full regeneration. `runs/` is append-only, so both run
records stand; the superseding record names the one it replaces, and the authoritative package is
whichever matches `reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256`.

## 15. Gate 2 assessment

Gates are conjunctive; `NOT_RUN` or missing evidence is not a pass.

| Constitution §9 gate 2 condition | Verdict | Basis |
| --- | --- | --- |
| deterministic reruns produce identical trades and equity curves | PASS | 5/5 cases identical on both digests across cold reruns; digests proven to carry no run identity and to discriminate between runs that really differ; symbol order proven irrelevant (§5) |
| tests detect look-ahead, same-close fill, split/dividend, delisting, stale-price, cash, rounding, fee, slippage, rejected-order, and duplicate-order errors | PASS | all twelve sealed defect classes injected one at a time and caught, over three clean controls; each class's tests confirmed to exist by AST parse, not by naming convention; look-ahead additionally established empirically by deleting 6437 future bars with both digests unchanged (§6, §7) |
| independent hand-calculated fixtures match engine output | PASS | FIXT hand arithmetic sealed before any engine code existed; 20/20 `BASE` and 19/19 `STRESSED` checks match line by line (§2, §8) |
| benchmark calculations reconcile | PASS | two SPY total-return methods agree to 2.2e-7 against a sealed 1e-6 across 115 dividends, and on four sub-windows; cash and do-nothing benchmarks return exactly zero; tradable buy-and-hold strictly below the index under both shutdown readings with the shortfall fully accounted (§9) |

## 16. Authorization state after this stage

| Activity | State |
| --- | --- |
| Strategy research | **UNLOCKED — development window only** (1993-01-29 → 2021-07-31) |
| Backtesting | **UNLOCKED — this engine, development window only** |
| Validation window | LOCKED |
| Final holdout | **SEALED** |
| Alpaca paper trading | LOCKED |
| Shadow live | LOCKED |
| Alpaca live trading | LOCKED |
| Capital or risk expansion | LOCKED |

`live_trading_authorized` remains `false`. No live order, cancel, replace, liquidation, or unattended
scheduling is authorized by anything in this stage.

Next authorized stage: **Stage 3 — strategy development** (constitution gate 3,
`development_admissibility`), development window only.

---

## Verdict

**PASS — STAGE_2_BACKTEST_ENGINE_VALIDATED**

All four gate 2 conditions pass. The engine is validated **within the twelve limitations recorded in
§11**, of which the constant spread proxy, the absence of partial fills, and the inherited Stage 1
data limitations are the three that most constrain what any backtest produced on it may claim. No
strategy, and no research result, exists at the end of this stage.
