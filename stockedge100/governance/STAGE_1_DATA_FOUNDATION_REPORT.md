# StockEdge100 — Stage 1 data foundation report

| | |
| --- | --- |
| Document id | `SE100-GOV-1000` |
| Project | StockEdge100, Generation 1 |
| Stage | Prompt Stage 1 — data foundation. Constitution **gate 1, data readiness**. |
| Governing document | `SE100-GOV-0001` v1.0.0, FROZEN, unmodified by this stage |
| Authored (UTC) | 2026-08-08T11:14:05Z |
| Verdict | **PASS — STAGE_1_DATA_FIT_FOR_RESEARCH** |
| `live_trading_authorized` | `false` |

`run_id` and `repo_state_id` for this stage are **not** written here: `repo_state_id` covers
`governance/*.md`, so a digest embedded in this file would be invalidated the moment the file was
saved. Both values live in
[reports/stage1/STAGE_1_DATA_READINESS.json](../reports/stage1/STAGE_1_DATA_READINESS.json) and in
the append-only record under [runs/](../runs/).

---

## 1. What this stage was allowed to do

Build the data foundation and stop. No strategy, no signal, no backtest, no performance number of
any kind exists at the end of this stage, and constitution gate 2 has not been attempted. The
holdout window has not been read.

Nothing frozen was edited. The Stage 0 constitution and its companion were opened read-only and
re-verified before anything else ran; the verification detail is in the decision record under
`constitution.freeze_verification`.

No money was spent, no subscription was taken, no account was created, and no credential was read.
Stage 0 §6.4 forbids all four at this stage.

## 2. The order things happened in, and why it is the whole argument

Stage 1's claim is not "the data looks clean". It is **"the rules that decide whether the data is
clean were fixed before anyone could see the data."** Without that, every threshold in this report
would be unfalsifiable — any failure could have been tuned away by moving a limit.

| Event | UTC | Artifact |
| --- | --- | --- |
| Rules sealed | 2026-08-08T10:40:10Z | `STAGE_1_PREREGISTRATION.json` |
| First provider request | 2026-08-08T10:45:49Z | `STAGE_1_RAW_MANIFEST.json` |
| Acquisition finished | 2026-08-08T10:46:52Z | `STAGE_1_RAW_MANIFEST.json` |
| Normalization | 2026-08-08T10:49:47Z | `STAGE_1_NORMALIZED_MANIFEST.json` |
| Validation battery | 2026-08-08T10:53:30Z | `STAGE_1_VALIDATION_REPORT.json` |
| Universe frozen, holdout locked | 2026-08-08T10:55:32Z | `STAGE_1_UNIVERSE.json`, `STAGE_1_HOLDOUT_LOCK.json` |

The seal is machine-enforced rather than asserted. `stage1_preregistration.py` refuses to run if any
raw data file exists, and it recorded `raw_data_files_present_at_seal_time: 0`. The seal covers
three files by SHA-256:

| File | SHA-256 |
| --- | --- |
| `config/stage1_data_source.json` | `7c6273ca501e3aaceafd006b0902ce4f329f83a67c4a9e5190155e8edf83064f` |
| `config/stage1_universe_spec.json` | `0583ef00fb5907feaedab561b13b4056c7e07e7c9ce1aae03d8ae197245f4057` |
| `governance/STAGE_1_PREREGISTRATION.md` | `53cea32ff202a4763378a5ecedc360c7e2fa1ccf1ce969d329c2e36b1cb5caee` |

Those three digests are pinned a second time, independently, in
`tests/unit/test_stage1_preregistration.py`. Rewriting a configuration file *and* its checksum
record together would still fail the suite. `load_stage1_config()` — the single entry point every
Stage 1 module goes through — recomputes all three on every call and raises
`PreRegistrationViolation` on any drift. `test_stage1_adversarial.py` proves that by tampering with
one byte of each in a throwaway copy of the tree.

## 3. Data source

| | |
| --- | --- |
| Provider | Yahoo Finance |
| Client | `yfinance` 1.4.1 |
| Endpoint mode | unofficial public chart endpoint via the yfinance client |
| Cost | $0. No subscription, no account, no credential. |
| Licence | personal and non-commercial use only, no redistribution |

The licence is the binding constraint here, not the price. Data is stored under `data/`, which is
git-ignored, and is never committed or published. This stage's artifacts record digests of the data,
never its contents.

**What "raw" means.** The client does not expose the underlying HTTP payload, so the immutable
"raw" layer is the frame the client returned, serialised to CSV with no value altered, rounded,
reordered, or dropped. That is a weaker guarantee than a stored HTTP response and is recorded as
such in the raw manifest rather than glossed over.

Request parameters were sealed before acquisition and are recorded in the manifest:
`auto_adjust=false`, `back_adjust=false`, `actions=true`, `repair=false`, `rounding=false`,
`prepost=false`, `interval="1d"`, `timeout=60s`. `repair` and `rounding` are off deliberately: a
provider-side repair would silently alter values the battery is meant to judge.

## 4. Acquisition

34 candidates plus 1 reference fixture (AAPL), 35 series in total.

| | |
| --- | --- |
| Acquisition failures | 0 |
| Failure fraction | 0.0, against a sealed blocking threshold of 0.2 |
| Stage blocked by acquisition | no |
| Provider revisions quarantined | none |

The raw manifest records, per symbol: role, status, path, SHA-256, byte count, row count, first and
last session, columns, source timezone, requested window, and retrieval time.
`test_stage1_data_foundation.py` recomputes all 35 digests from disk.

The longest series is SPY: 8,438 sessions, 1993-01-29 to 2026-08-07, requested as `max`.

**AAPL was requested with a bounded window**, `['2010-01-01', '2021-07-31']`, declared in the sealed
spec. The reason is structural: a data-quality fixture must never be able to see validation or
holdout data. That truncation has a consequence, discussed in §6.

## 5. Normalization

Nine columns, sealed before the data was seen:
`session, open, high, low, close, adj_close, volume, dividend, split_ratio`.

**Session key.** The calendar date of the provider instant expressed in America/New_York,
timezone-naive. Every one of the 35 series was checked row by row: all rows land on local midnight,
zero non-midnight rows, with the expected `-0400`/`-0500` offset pair across DST. Row counts in
equal row counts out for every symbol — nothing was dropped in normalization.

**Storage is CSV, not parquet.** `pyproject.toml` declares an optional parquet path, but `pyarrow`
is not installed in this environment. This is a recorded deviation from the declared preference, not
an unremarked one.

### 5.1 Adjustment semantics were measured, not assumed

Assuming a provider's adjustment convention is the classic silent error in this kind of work, so the
convention was **measured** against known corporate actions and the measurement is falsifiable.

Method: take the close-to-close step across a known split and compare it against the `1/ratio` step
an as-traded series would necessarily show.

| Symbol | Session | Declared ratio | Recorded ratio | Unadjusted close step | Step if as-traded |
| --- | --- | ---: | ---: | ---: | ---: |
| AAPL | 2014-06-09 | 7.0 | 7.0 | 1.01600138 | 0.14285714 |
| AAPL | 2020-08-31 | 4.0 | 4.0 | 1.03391215 | 0.25 |

Both steps sit next to 1.0, nowhere near `1/7` or `1/4`. **Determination: the provider's OHLC is
already split-adjusted**, and `adj_close` is split- and dividend-adjusted. The consequence is
concrete and is what the battery then enforces: the expected adjustment-factor step at a split is
`1.0`, not `ratio`, because splits are already present in both series.

This measurement drives the split reconciliation check, so it is not decorative. The adversarial
suite confirms it can fail: a split recorded but never applied, and a split whose factor step is
wrong, both trip `SPLIT_RECONCILES`.

**As-traded price levels are not obtainable from this provider** when OHLC arrives already
back-adjusted. Constitution §6 is satisfied by retaining the immutable raw payload plus a measured,
documented transformation between the two retained series. The unavailability of true historical
price *levels* is recorded as a limitation (§9) rather than papered over, and it binds later stages:
anything modelling per-share minimum tick, whole-share sizing, or a price-level rule must treat this
as a missing input, not approximate it from adjusted prices.

## 6. Validation battery

16 checks, declared in the sealed configuration before any data existed, run over all 35 symbols —
560 check results.

| Check | PASS | FAIL | WARN | N/A |
| --- | ---: | ---: | ---: | ---: |
| `SESSION_IN_CALENDAR` | 35 | 0 | 0 | 0 |
| `NO_DUPLICATE_SESSIONS` | 35 | 0 | 0 | 0 |
| `SESSIONS_STRICTLY_INCREASING` | 35 | 0 | 0 | 0 |
| `NO_FUTURE_SESSIONS` | 35 | 0 | 0 | 0 |
| `OHLC_CONSISTENT` | 35 | 0 | 0 | 0 |
| `VOLUME_VALID` | 35 | 0 | 0 | 0 |
| `ADJ_CLOSE_POSITIVE` | 35 | 0 | 0 | 0 |
| `TERMINAL_FACTOR_IS_ONE` | 34 | **1** | 0 | 0 |
| `FACTOR_NON_DECREASING` | 35 | 0 | 0 | 0 |
| `SPLIT_RECONCILES` | 35 | 0 | 0 | 0 |
| `DIVIDEND_RECONCILES` | 35 | 0 | 0 | 0 |
| `CORPORATE_ACTION_FIXTURE` | 1 | 0 | 0 | 34 |
| `MISSING_SESSION_FRACTION` | 35 | 0 | 0 | 0 |
| `MISSING_SESSION_RUN` | 35 | 0 | 0 | 0 |
| `EXTREME_MOVE_EXPLAINED` | 35 | 0 | 0 | 0 |
| `PRICE_NOT_PENNY` | 35 | 0 | 0 | 0 |

Symbols with warnings: none. Quarantine records: none. Unclassified failures: none.

**The trading calendar is independent of the price provider.** `XNYS` via `exchange_calendars`
4.13.2, bounds 1990-01-02 to 2027-08-06. Checking a provider's sessions against the same provider's
idea of a session would be circular. `test_stage1_calendar_partition.py` checks that calendar
against independently known facts — Christmas 2020, the 2015 Independence Day Friday observance,
the Hurricane Sandy closure of 2012-10-29 — rather than against anything in `data/`.

**Scope.** Integrity checks cover the full series including the holdout window, because confirming a
session key or a split reconciliation is not a research result and gate 1 requires *complete*
manifests. What is forbidden is using holdout *values* to make a decision. The one value-threshold
check, `PRICE_NOT_PENNY`, is therefore restricted to the development window.

### 6.1 The one failure, stated plainly

`AAPL : TERMINAL_FACTOR_IS_ONE : FAIL`

The check's premise is that the final row of a series is the provider's terminal session, so that
the back-adjustment factor there must be 1. For AAPL that premise is false by construction: its
window was truncated at 2021-07-31 by the sealed spec, precisely so that a data-quality fixture can
never touch validation or holdout data. Vendor back-adjustment is anchored at the true last traded
session, so a truncated series ends at a factor other than 1 no matter how correct it is.

This is **a defect in the Stage 1 pre-registration**, which failed to scope that check to
untruncated series. It is recorded as such in the validation report under
`preregistration_scope_gaps`, with `sealed_check_amended: false`.

What was deliberately *not* done: the sealed check was not amended, relaxed, re-scoped, or deleted
to make the battery green. Rewriting a rule after seeing the result it produced is the exact failure
mode pre-registration exists to prevent, and doing it here would have cost more than the failure it
hid.

Why it does not contaminate research:

- AAPL is a **reference fixture, not a research symbol**. It is not in the 34-member universe and
  the universe spec prohibits it from being one.
- Every fixture comparison the stage relies on is a **ratio**. A constant scale factor cancels, so
  the split measurement in §5.1 is unaffected.
- `research_universe_battery_passed: true`, `research_universe_failures: []`,
  `unclassified_failures: []`. The classifier is keyed off `requested_window`, which was recorded in
  the raw manifest *before* validation ran, so the explanation is not retrofitted.

The battery as a whole did not pass — `battery_passed: false` is what the report says, and it is
left saying it.

## 7. Universe

| | |
| --- | --- |
| `universe_version` | `SE100-U1-d4917c2f7f1cd834` |
| Identity SHA-256 | `d4917c2f7f1cd8344728a39165929b352766fbe7193b3c64e71a971749dcbf38` |
| Class | `ETF_ONLY` |
| Members | 34 |
| Rejected | 0 |
| Not acquired | 0 |
| Frozen (UTC) | 2026-08-08T10:55:32Z |

AGG, BND, DIA, DVY, EEM, EFA, HYG, IEF, IVV, IWM, IYR, LQD, MDY, QQQ, SHY, SPY, TIP, TLT, VEA, VGK,
VIG, VNQ, VTI, VWO, VYM, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY.

Every candidate cleared every eligibility rule, so nothing was rejected. That is a fact about a
deliberately conservative candidate list — large, liquid, long-established funds — not evidence that
the screen is lax; the adversarial suite drives symbols through the same screen and fails them.

Eligibility was measured on the development window only, 1993-01-29 to 2021-07-31. This is enforced
in code: `universe.build.measure` raises `WindowViolation` if handed a session past the development
end. It is not a convention, and `test_stage1_adversarial.py` triggers the exception.

Six structural rules — US-listed, unleveraged, non-inverse, not a K-1 partnership, not a commodity
trust, rules-based index — are **asserted at candidate construction** and cannot be verified from
price data. They are labelled `ASSERTED`, not measured.

### 7.1 Survivorship bias — two verdicts, neither of them comfortable

**Individual stocks: `SURVIVORSHIP_BIAS_UNCONTROLLED`.** This provider offers no point-in-time index
constituent history. Any stock list assembled in 2026 is a list of companies that survived to 2026.
Stock research is therefore `PROHIBITED_IN_GENERATION_1_WITHOUT_A_NEW_DATA_SOURCE`.

**ETFs: `RESIDUAL_FUND_CLOSURE_BIAS_DISCLOSED_AND_UNQUANTIFIED`.** The candidate list was assembled
in 2026 and therefore contains only funds that still exist in 2026. Funds that launched and closed
between the start of the development window and the cutoff are absent from it. This is a real
residual survivorship bias, it is **not** eliminated by the ETF narrowing, and it is **not**
quantified.

Gate 1 asks for bias "controlled **or** the research universe prospectively narrowed". This stage
satisfies the **second** disjunct and explicitly does not claim the first. The narrowing is
prospective in the literal sense that matters: the candidate list was sealed and hashed before any
price was fetched, so no symbol entered on the strength of how its history looked.

### 7.2 Broker eligibility is unverified, and the universe is conditional on it

`alpaca_tradable` and `alpaca_fractionable` are both `UNVERIFIED` for all 34 members. No credential
access is authorized at Stage 1, so this cannot be resolved here; it resolves at Stage 6
(constitution gate 7, paper trading). The consequence is binding: any member later found
non-tradable or non-fractionable at Alpaca must be removed, and every affected gate re-run.

## 8. Time partition and holdout lock

Computed per constitution §6.1 from the data, not from the wall clock. The cutoff is the latest
session present in the acquired candidate data.

| | |
| --- | --- |
| Usable cutoff session | 2026-08-07 |
| Cutoff month | 2026-08, **incomplete** (last session would be 2026-08-31) — excluded |
| Last complete month | 2026-07 |
| Development | 1993-01-29 → 2021-07-31 (28.501 years) |
| Validation | 2021-08-01 → 2024-07-31 (36 months) |
| Holdout | 2024-08-01 → 2026-07-31 (24 months) |
| Minimum development | 5 years required, satisfied |
| `holdout_state` | **SEALED** |
| Locked (UTC) | 2026-08-08T10:55:32Z |

The windows are contiguous, non-overlapping, and every boundary falls on a month boundary — all
three checked arithmetically rather than by eye.

The lock was written before any strategy, engine, or result existed, which is the only moment at
which locking a holdout means anything. Its binding rules: the holdout is read exactly once, at the
constitutional holdout gate; no parameter, threshold, symbol, or rule may be chosen using any value
inside validation or holdout; these boundaries may not be recomputed, widened, narrowed, or shifted
by any later stage; and if the dataset is re-acquired and the cutoff moves, **the existing lock still
governs**.

That last rule has teeth in code, not just in prose: the builder refuses to overwrite a lock whose
boundaries differ, exits 5, and writes nothing. `test_stage1_adversarial.py` plants a lock with a
moved holdout start and asserts exactly that.

## 9. Limitations that survive this stage

Every one of these travels with all downstream results.

1. **Single provider.** Every price here comes from one unofficial public endpoint. There is no
   second source to cross-check against, so a systematic provider error would pass all 16 checks
   undetected. This is the largest unmitigated risk in the stage.
2. **Licence.** Personal, non-commercial, no redistribution. Not a licence for commercial use; a
   later stage needing one must acquire it.
3. **Residual ETF closure bias**, disclosed and unquantified (§7.1).
4. **Stocks are prohibited** for Generation 1 without a point-in-time constituent source (§7.1).
5. **`AAPL:TERMINAL_FACTOR_IS_ONE` fails**, classified as a pre-registration scope gap, sealed check
   not amended (§6.1).
6. **As-traded price levels are unavailable** (§5.1).
7. **CSV instead of parquet**, because `pyarrow` is absent (§5).
8. **`raise_errors=True` is deprecated in yfinance 1.4.1.** The acquisition code was left exactly as
   it ran, so the recorded code state is what produced the data. A future client version may remove
   the argument and break re-acquisition.
9. **Broker eligibility UNVERIFIED** for all 34 members; the universe is conditional (§7.2).
10. **Six structural eligibility rules are asserted, not measured** (§7).

## 10. Conflict found between frozen artifacts

`STAGE_0_CONSTITUTION.json` records gate 1 as `{"id": 1, "name": "data_readiness", "fail_result":
"DATA_NOT_FIT_FOR_RESEARCH"}` — with **no `pass_result`**, while the Markdown gate table in §9 is
complete. Per the precedence rule the Markdown governs.

Neither frozen file was edited. The pass reason code below is the affirmative of the recorded fail
token, carrying the stage prefix Stage 0 established with `STAGE_0_CONSTITUTION_VERIFIED`. The
derivation is recorded in the decision record under `verdict_token_derivation` so that a later reader
can see it was chosen, and on what basis, rather than assumed.

## 11. Tests

**140 passed, 0 failed, 0 skipped.** The 27 Stage 0 tests are unmodified; Stage 1 adds 113.
Detail: [reports/stage1/STAGE_1_TEST_SUMMARY.md](../reports/stage1/STAGE_1_TEST_SUMMARY.md).

No test was weakened, skipped, or removed to make this gate pass.

## 12. Gate 1 assessment

Gates are conjunctive; `NOT_RUN` or missing evidence is not a pass.

| Constitution §9 gate 1 condition | Verdict | Basis |
| --- | --- | --- |
| raw and normalized manifests complete and hash-verified | PASS | 35/35 acquired, 0 failures, all 70 digests recomputed from disk by test; normalized manifest chains to the raw manifest by digest (§4, §5) |
| session, timestamp, OHLCV, split, dividend, missing-data, duplication tests pass | PASS | all seven families 35/35 PASS (§6) |
| adjustment behavior independently checked on known corporate-action examples | PASS | semantics MEASURED on two known AAPL splits; `CORPORATE_ACTION_FIXTURE` PASS; one adjustment-consistency failure disclosed and classified, sealed check unamended (§5.1, §6.1) |
| universe bias controlled **or** research universe prospectively narrowed | PASS | second disjunct: prospective narrowing to `ETF_ONLY`, sealed before acquisition; residual bias disclosed and unquantified; first disjunct explicitly not claimed (§7.1) |
| time partitions and final holdout locked before results | PASS | locked 2026-08-08T10:55:32Z, `holdout_state: SEALED`, no strategy or result exists; refusal to move enforced in code and tested (§8) |

## 13. Authorization state after this stage

| Activity | State |
| --- | --- |
| Strategy research | **UNLOCKED — development window only** (1993-01-29 → 2021-07-31) |
| Validation window | LOCKED |
| Final holdout | **SEALED** |
| Alpaca paper trading | LOCKED |
| Shadow live | LOCKED |
| Alpaca live trading | LOCKED |
| Capital or risk expansion | LOCKED |

`live_trading_authorized` remains `false`. No live order, cancel, replace, liquidation, or
unattended scheduling is authorized by anything in this stage.

Next authorized stage: **Stage 2 — backtest engine** (constitution gate 2, `backtest_engine_validity`).

---

## Verdict

**PASS — STAGE_1_DATA_FIT_FOR_RESEARCH**

All five gate 1 conditions pass. The data foundation is fit for research **within the ten limitations
recorded in §9**, of which the single-provider dependency and the unquantified residual ETF closure
bias are the two that most constrain what any downstream result can claim.
