# StockEdge100 Project Constitution

**Document ID:** `SE100-GOV-0001`  
**Version:** `1.0.0`  
**Status:** `FROZEN`  
**Effective date:** `2026-08-08` (Asia/Ulaanbaatar)  
**Project:** StockEdge100  
**Stage:** 0 — Constitution and pass/fail gates

## 1. Mandate

StockEdge100 is a new, independent research project whose objective is to discover whether an automated system can earn positive returns from US-listed stocks and ETFs after realistic trading frictions, while preserving a small account.

The project is designed for an eventual **USD 100 Alpaca cash account**. Profit is an objective, not a promise. A valid conclusion may be that no tested strategy has a reliable edge or that USD 100 is operationally uneconomic.

This project must not import code, data, results, strategies, parameter choices, or verdicts from any earlier FX, crypto, or other trading project. General engineering techniques may be independently reimplemented, but provenance must be recorded.

## 2. Governing principles

1. **Falsification first.** The burden of proof is on each strategy.
2. **Cash is a position.** The system must not trade merely to stay active.
3. **No result-driven rule changes.** A failed gate cannot be weakened after results are observed.
4. **No hidden discretion.** Every signal, ranking, allocation, order, rejection, and override must be reproducible from recorded inputs.
5. **Economic realism.** Results are measured after spread, slippage, fees, dividends, splits, and rejected/unfilled orders where applicable.
6. **No future leakage.** A decision may use only information available before its simulated decision time.
7. **Survival before scale.** Increasing capital, exposure, frequency, or product complexity requires a new written approval.
8. **Negative results are deliverables.** Rejected strategies are recorded and not silently recycled.

## 3. Fixed scope for Generation 1

| Item | Frozen rule |
|---|---|
| Broker target | Alpaca; research and backtesting remain broker-independent where practical |
| Account model | USD 100 cash account |
| Securities | US-listed common stocks and unleveraged ETFs that pass data, liquidity, tradability, and fractional-eligibility rules |
| Direction | Long-only |
| Products prohibited | Options, futures, CFDs, leveraged/inverse ETFs, OTC securities, penny stocks, short sales, margin, and crypto |
| Data frequency | Daily bars; corporate actions and reference data as required |
| Decision frequency | At most once per trading session per strategy |
| Execution assumption | No same-close execution from a signal using that close; earliest normal fill is the next eligible session |
| Portfolio breadth | One open risky position in Generation 1; otherwise cash |
| Gross exposure | Maximum 95% of current equity; minimum 5% cash buffer |
| Order sizing | Fractional shares; minimum notional must respect the broker's then-current rule |
| Strategy families | Trend/momentum, pullback, mean reversion, breakout, ETF rotation, and defensive regime logic may be researched separately |
| Event/fundamental/ML strategies | Deferred until separately authorized with point-in-time data controls |
| Human intervention | Allowed only for safety or operational shutdown; never to improve a backtest or override an ordinary signal |

## 4. Research objective and benchmarks

The primary question is:

> Does a predeclared strategy produce a positive, repeatable, after-cost edge that is sufficiently robust to justify paper trading under the USD 100 constraint?

Every candidate is compared with:

- **SPY total return:** opportunity-cost benchmark.
- **Cash return:** a 3-month US Treasury-bill proxy when reliable point-in-time data are available; otherwise 0% cash, explicitly labeled conservative for return comparison.
- **Do nothing:** zero trades, used to expose strategies whose activity destroys capital.

Beating SPY is not mandatory if a strategy materially reduces drawdown, but passing requires positive after-cost performance and better risk-adjusted performance than cash.

## 5. Capital and risk policy

### 5.1 Research and paper limits

- Starting equity: **USD 100.00**.
- Maximum allocation to one position: **95% of current equity**.
- No averaging down unless it is an explicit, predeclared rule tested as part of the strategy.
- No order may create negative cash or leverage.
- A strategy enters a research shutdown state if simulated equity falls **15% below its running high-water mark**.
- The future production controller must enter a broker/data safety shutdown on stale data, reconciliation mismatch, duplicate-order risk, unknown position, authentication failure, or an unhandled exception.

### 5.2 Future live-account limits

Live trading is outside Stage 0 authorization. If later unlocked, the initial account-level loss limit will be stricter:

- Soft risk halt at **8%** below live high-water mark: no new entries pending review.
- Hard risk halt at **10%** below live high-water mark: cancel open entry orders and permit only risk-reducing exits.
- Any change to these values requires a new constitution version approved before further live orders.

Stops are risk tools, not guarantees; overnight gaps may exceed intended losses.

## 6. Data constitution

Before strategy computation, Stage 1 must freeze a data manifest covering provider, API/version, retrieval time, raw hashes, licenses, fields, timezone, session calendar, adjustment semantics, and known coverage limits.

Required controls:

- Preserve raw data immutably and derive normalized data reproducibly.
- Retain adjusted and unadjusted OHLCV, or document a verified transformation between them.
- Validate splits, dividends, duplicate bars, impossible prices/volumes, missing sessions, symbol changes, and delistings where the universe requires them.
- Use point-in-time universe membership and tradability/fractional eligibility when testing a changing stock universe.
- A static present-day stock list may not be used to make historical claims without an explicit survivorship-bias verdict.
- A dataset that cannot support the required bias controls may still support ETF-only research if that narrower use is frozen before strategy results are viewed.

### 6.1 Prospective time partition

The exact dates will be computed once, immediately after the usable data cutoff is frozen and **before any strategy result is generated**:

1. Exclude the incomplete cutoff month.
2. Lock the most recent **24 complete calendar months** as the final holdout.
3. Lock the preceding **36 complete calendar months** as validation/walk-forward assessment.
4. Use all earlier eligible history as development, subject to a minimum of five years.

The final holdout is sealed: no parameter choice, strategy selection, feature choice, or bug-driven redesign may use its results. A material bug found after holdout access invalidates that holdout for promotion; the project must obtain a new prospective period or stop with `HOLDOUT_INVALIDATED`.

## 7. Cost and execution constitution

The base backtest must include:

- commission and regulatory fees applicable to the modeled order;
- bid-ask spread, using quotes when available or a conservative documented proxy;
- slippage beyond the spread;
- fractional-share rounding/minimum-notional behavior;
- next-session timing and no fills outside eligible market sessions;
- dividends, splits, cash, and rejected/unfilled orders;
- a stressed-cost run at **2× the complete base trading-friction assumption**.

Zero-commission does not mean zero-cost. If a reliable cost component is unavailable, the project must use a conservative predeclared proxy and label the limitation.

## 8. Strategy research protocol

Each strategy experiment requires a signed specification created before execution containing:

- immutable experiment ID and hypothesis;
- eligible universe and exclusions;
- signal timing, features, parameters, and permitted parameter grid;
- entry, exit, sizing, ranking, and conflict rules;
- cost assumptions and benchmarks;
- development/validation data permitted;
- primary metric and all pass/fail gates;
- maximum number of research iterations;
- code commit/hash and configuration hash.

No machine learning is authorized for Generation 1. Strategy families must first be tested independently. Combining strategies is prohibited until each component has an independent verdict.

## 9. Stage gates

Gates are conjunctive: **every hard condition must pass**. `NOT_RUN`, `UNKNOWN`, or missing evidence is not a pass.

### Gate 0 — Constitution freeze

**Pass only if:**

- this document and its machine-readable companion exist;
- their SHA-256 hashes are recorded in `STAGE_0_FREEZE.sha256`;
- machine-readable validation passes;
- no strategy backtest result was used to set these rules.

**Fail verdict:** `STAGE_0_NOT_FROZEN`.

### Gate 1 — Data readiness

**Pass only if:**

- raw and normalized manifests are complete and hash-verified;
- session, timestamp, OHLCV, split, dividend, missing-data, and duplication tests pass;
- adjustment behavior is independently checked on known corporate-action examples;
- universe bias is controlled or the research universe is prospectively narrowed;
- time partitions and final holdout are locked before results.

**Fail verdict:** `DATA_NOT_FIT_FOR_RESEARCH`.

### Gate 2 — Backtest-engine validity

**Pass only if:**

- deterministic reruns produce identical trades and equity curves;
- tests detect look-ahead, same-close fill, split/dividend, delisting, stale-price, cash, rounding, fee, slippage, rejected-order, and duplicate-order errors;
- independent hand-calculated fixtures match engine output;
- benchmark calculations reconcile.

**Fail verdict:** `BACKTEST_ENGINE_NOT_VALIDATED`.

### Gate 3 — Development admissibility

This gate rejects obviously weak or fitted candidates before sealed evaluation.

**Pass only if, on development data after base costs:**

- total return is positive;
- maximum drawdown is no worse than **15%**;
- profit factor is at least **1.10**;
- at least **30 closed trades** exist, unless a lower-frequency protocol predeclared a longer evidence requirement before results;
- performance is not dependent on one trade: removing the single best trade leaves total return above 0%;
- no single instrument contributes more than **50%** of total strategy profit for a multi-instrument strategy;
- reasonable neighboring parameter values do not reverse the sign of net return.

**Fail verdict:** `STRATEGY_REJECTED_IN_DEVELOPMENT`.

### Gate 4 — Validation robustness

**Pass only if, on the locked validation/walk-forward period:**

- after-cost total return is positive;
- annualized Sharpe ratio is at least **0.50** using daily equity returns and a documented cash rate;
- maximum drawdown is no worse than **15%**;
- profit factor is at least **1.15**;
- stressed-cost total return remains positive;
- at least **70%** of completed walk-forward test folds have positive after-cost return;
- no material rule, feature, universe, or parameter change is made in response to validation results.

**Fail verdict:** `STRATEGY_REJECTED_IN_VALIDATION`.

### Gate 5 — Final holdout

The holdout is opened once for the frozen candidate and exact production-intent configuration.

**Pass only if:**

- after-cost holdout total return is positive and exceeds the cash benchmark;
- Sharpe ratio is at least **0.50**;
- maximum drawdown is no worse than **12%**;
- profit factor is at least **1.15**;
- stressed-cost return is non-negative;
- removing the best trade does not make total return negative;
- trade count is at least **20**; otherwise the verdict is `INSUFFICIENT_HOLDOUT_EVIDENCE`, not pass or fail;
- there is no execution, data, or governance breach.

**Fail verdict:** `STRATEGY_REJECTED_ON_HOLDOUT`.

Passing Gate 5 means only `ELIGIBLE_FOR_PAPER_TRADING`; it does not authorize live trading.

### Gate 6 — Portfolio controller

**Pass only if:**

- every included strategy passed Gate 5 independently;
- selection and conflict resolution are deterministic and predeclared;
- portfolio validation improves at least one of after-cost return, Sharpe, or maximum drawdown without materially degrading the other two;
- maximum drawdown remains no worse than **12%**;
- correlation concentration and simultaneous-signal behavior are tested;
- cash behavior and all shutdown paths pass.

**Fail verdict:** `PORTFOLIO_CONTROLLER_REJECTED`.

### Gate 7 — Alpaca paper trading

Minimum observation: **90 calendar days and 30 closed trades**. If 30 trades are not reached, continue up to **180 calendar days**; if still not reached, return `INSUFFICIENT_PAPER_EVIDENCE`.

**Pass only if:**

- the same production-intent signal and order code runs without manual trade selection;
- zero duplicate orders, unknown positions, unreconciled cash breaks, or unhandled execution failures remain unresolved;
- every order decision and broker response is logged and reconcilable;
- realized paper slippage/cost does not exceed the research stress assumption on a sustained basis;
- after-cost paper return is positive, maximum drawdown is no worse than **10%**, and profit factor is at least **1.10**;
- all kill switches are tested successfully.

**Fail verdict:** `PAPER_TRADING_NOT_VALIDATED`.

### Gate 8 — Shadow-live readiness

Minimum observation: **20 intended round trips or 60 calendar days**, whichever is longer.

**Pass only if:**

- live quotes, intended orders, fractional eligibility, and market-session behavior match modeled assumptions within predeclared tolerances;
- no unresolved stale-data, clock, corporate-action, symbol, or reconciliation defect exists;
- expected live costs remain inside the stressed research envelope.

**Fail verdict:** `SHADOW_LIVE_NOT_VALIDATED`.

### Gate 9 — Limited live authorization

Gate 9 cannot be passed by software automatically. It requires a separate dated written approval by the project owner after Gates 0–8 pass.

Initial live constraints remain USD 100, long-only, cash-only, one position, 95% maximum exposure, and the 8%/10% soft/hard halt rules. Any capital increase or scope expansion requires a new gate decision.

**Absent approval verdict:** `LIVE_TRADING_LOCKED`.

## 10. Verdict vocabulary

Every stage ends with exactly one primary verdict:

- `PASS`
- `FAIL`
- `BLOCKED_BY_DATA`
- `BLOCKED_BY_INFRASTRUCTURE`
- `INSUFFICIENT_EVIDENCE`
- `INVALIDATED`
- `NOT_RUN`

The stage-specific reason code must accompany the primary verdict. Missing evidence may never be converted to `PASS` or `NOT_APPLICABLE` merely for convenience.

## 11. Change control

- This version is immutable once its hashes are recorded.
- Corrections require a new version; the old version remains preserved.
- A change that affects universe, timing, cost, signal, parameter range, metric, threshold, or data partition is material.
- A material change after seeing validation results creates a new candidate and restarts at Gate 3.
- A material change after seeing holdout results cannot reuse that holdout for promotion.
- Safety thresholds may be tightened without promoting a failed strategy, but the change must still be versioned.
- Code fixes require impact analysis, new hashes, deterministic reruns, and re-execution of every affected gate.

## 12. Explicit non-authorizations

This constitution does not authorize:

- downloading or purchasing data;
- placing paper or live orders;
- accessing Alpaca credentials;
- depositing, withdrawing, or transferring funds;
- selecting a winning strategy from holdout results;
- claiming expected income or guaranteed profitability;
- expanding beyond the Generation 1 scope.

## 13. Stage 0 decision

If the companion JSON validates and the freeze hashes match, Stage 0 verdict is:

> `PASS — STAGE_0_CONSTITUTION_FROZEN`

The next authorized activity is **Stage 1: data-source decision, universe freeze, acquisition protocol, and holdout-lock calculation**. No strategy backtest is authorized before Gate 1 passes.

