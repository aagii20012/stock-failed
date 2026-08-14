# Stage 2 — Backtest Engine Pre-registration

**Document ID:** `SE100-GOV-0005`
**Project:** StockEdge100
**Generation:** 1
**Stage:** 2 — honest backtest engine (pre-registration, written before any engine code existed)
**Declared (UTC):** 2026-08-08T15:10Z — the authoritative timestamp and the digest of every
pre-registered file are in `governance/STAGE_2_PREREGISTRATION.json`, which is generated after this
document and therefore cannot be quoted inside it.
**Status of this document:** pre-registration. It constrains Stage 2; it does not modify, supersede,
reinterpret, or extend `SE100-GOV-0001`.

---

## 1. Why this document exists

Constitution §9 gate 2 asks for an engine that is *honest*, and the honesty of a backtest engine is
almost entirely a question of ordering. Every cost assumption in a backtest is a free parameter until
someone writes it down. Charge 1 bp of slippage instead of 5 and a marginal strategy becomes a good
one; model a split as a share-count change on an already-adjusted series and the equity curve
manufactures money out of arithmetic. None of these choices announces itself in the result. Each of
them is defensible in isolation and indefensible if it was picked because of the number it produced.

So the numbers are fixed first. `config/stage2_cost_model.json` states every cost, rounding rule, and
corporate-action convention the engine will apply. `config/stage2_engine_spec.json` states what the
engine must be able to detect, and — critically — contains every expected value of the
hand-calculated fixtures, arithmetic done by hand before an engine existed to check it against.

At the moment this document is sealed, `src/stockedge100/backtest/` contains **no files**. There is
no engine, no engine output, no equity curve, and no trade list anywhere in this project. That fact
is verified by the sealing program, which refuses to run otherwise, and is recorded in the JSON.

---

## 2. Pre-registered files

| File | Content |
|---|---|
| `config/stage2_cost_model.json` | account limits, execution timing, frictions, sizing and rounding, corporate actions, stale-data policy, risk shutdown, benchmarks, metric definitions |
| `config/stage2_engine_spec.json` | gate 2 conditions, the twelve defect classes with their injected mutation and required detector, engine invariants, hand-calculated fixture values, benchmark reconciliation method, window policy, permitted probes |
| `governance/STAGE_2_PREREGISTRATION.md` | this document |
| `governance/STAGE_2_PREREGISTRATION.json` | authoritative declaration timestamp and digests of the three files above |
| `governance/STAGE_2_PREREGISTRATION.sha256` | checksum record covering the four files above |

`STAGE_2_PREREGISTRATION.sha256` records **project-root-relative** paths, matching the Stage 1
convention and differing deliberately from `STAGE_0_FREEZE.sha256`, which records bare filenames:

```bash
cd stockedge100 && sha256sum -c governance/STAGE_2_PREREGISTRATION.sha256
```

Neither record contains its own digest; nothing hashes itself.

---

## 3. The costs, and why these ones

Constitution §7 requires commission, exchange and regulatory fees, spread, slippage, fractional
rounding and minimum notional, next-session timing, dividends, splits, cash drag, rejected orders,
and a 2× stressed run. Every one is declared in the cost model. Three of the choices carry judgement
and are stated plainly here rather than buried in a JSON field.

**Spread and slippage are a proxy, not a measurement.** No historical quote data is available from
the Stage 1 provider, so no spread can be measured for any symbol in any year. §7 permits a
conservative documented proxy, and that is what 2.5 bps of half-spread plus 2.5 bps of slippage is —
5 bps per side, 10 bps round trip, charged on every fill of every symbol in every year. For the large
liquid ETFs in the frozen universe this is wider than a typical modern quoted spread and narrower
than a 1990s one. It is a single constant, uniform across symbols and eras, because nothing in this
project's evidence supports a finer estimate. Anyone reading a Stage 2 or later result should treat
the cost figure as a declared assumption, not as a measurement of what trading actually cost.

**The regulatory fee rates are fixed at present-day values across a 28-year window.** The SEC §31
rate has been reset many times and was substantially higher in parts of the sample; the FINRA TAF
per-share rate has also moved. A single fixed rate is a predeclared proxy whose error therefore has a
known direction in the early sample — it under-charges — and that direction is recorded in the stage
report's limitations rather than left for a reader to discover.

**The TAF is charged on adjusted shares.** Stage 1 established that as-traded price levels, and
therefore as-traded share counts, are unrecoverable from this provider. A per-share fee has no
well-defined value without them. Adjusted shares are greater than or equal to as-traded shares for
any back-adjusted series, so charging the fee on adjusted shares over-charges rather than
under-charges. The conservative direction is the reason the choice is acceptable, and it is recorded
as a limitation, not presented as correct.

**Every rounding step is adverse to the account.** Share quantity rounds down; buy notional rounds up
to the cent; sell proceeds and dividend credits round down; regulatory fees round up. Rounding in a
backtest is either a small cost or a small free lunch, and which one it is depends entirely on the
direction chosen. It is chosen here, once, before any result exists.

---

## 4. Splits and dividends, decided from measurement

Stage 1 measured — from two AAPL split fixtures, not from an assumption — that the provider's OHLC is
already split-adjusted, and that `adj_close` carries split **and** dividend adjustment. Two
consequences follow, and both are declared before the engine exists because both are the kind of bug
that produces a plausible, profitable, wrong equity curve:

1. **A split must not change the share count.** The price series does not gap at a split, because the
   gap has already been removed. Multiplying the share count as well would apply the same event
   twice. The engine instead asserts value continuity across every corporate-action session.
2. **The dividend column is denominated in split-adjusted space.** This is not assumed either: Stage
   1's `DIVIDEND_RECONCILES` check reconciled each recorded dividend against the split-adjusted prior
   close for every symbol, and passed. So the amount may be multiplied directly by the adjusted share
   count.

The unit of account is therefore the **adjusted share** — one share of the back-adjusted series, not
the number of certificates an account would actually have held on that date. It is the only
self-consistent unit available given what Stage 1 recorded, and calling it anything else would be a
fiction.

---

## 5. Why the benchmark reconciliation is an identity, not a tolerance

Gate 2 requires that "benchmark calculations reconcile". The weak version of that test computes SPY
total return two ways, finds them close, and picks a tolerance that accommodates the difference. That
proves nothing: the tolerance was chosen after seeing the gap.

Stage 1 measured the provider's adjustment convention as

    adj_t = close_t × Π over later ex-dates s of (1 − D_s / close_{s−1})

Given that convention, an explicit share-accumulation model — start with one share, buy more with
each dividend — reproduces the `adj_close` ratio **exactly**, and does so only if each reinvestment
happens at `close_{s−1} − D_s`. That is algebra, not calibration. The reinvestment price is forced by
the convention rather than tuned to fit.

So the two methods are one arithmetic identity computed along two different paths, and the declared
1e-6 relative tolerance is there to absorb floating-point summation over roughly 7,000 sessions, not
to absorb a modelling difference. Any disagreement larger than that is a defect in the engine or in
the data, and Stage 2 will report it as one.

---

## 6. Rules that bind the rest of the stage

1. **The engine may not be written to make a fixture pass.** The fixture values in
   `stage2_engine_spec.json` are sealed by this document. If engine output disagrees with them, the
   discrepancy is investigated and reported. Editing the sealed expected value to match the engine is
   prohibited, whichever one turns out to be wrong.
2. **Every defect class gets an injected-defect test.** A guard that has only ever seen correct input
   is untested. For each of the twelve classes, one test mutates exactly one thing and asserts the
   detector fires; clean controls sit at the top of the file so a failure below them is attributable.
3. **Development-window data only.** Stage 2 validates an engine; it has no need and no authorization
   to read validation or holdout data. The restriction is enforced in code by a window guard that
   raises, and asserted by test — not left to discipline.
4. **Nothing in Stage 2 is a strategy.** The probes are fixed mechanical schedules with no signal, no
   parameter, and no fitting. No probe result may be used to prefer one rule over another, and no
   Stage 2 artifact reports a strategy performance figure. Constitution §8 governs strategies; Stage 2
   produces none.
5. **Decimal arithmetic throughout.** No floating-point value enters a cash or quantity computation.
   This is what makes the fixtures hand-checkable and the reruns bit-identical.
6. **Invariants halt, they do not warn.** A violated cash, exposure, ordering, or corporate-action
   invariant stops the run. An engine that logs a broken invariant and continues is not an honest
   engine.
7. **If any gate 2 condition cannot be met, the stage returns
   `BLOCKED — BACKTEST_ENGINE_NOT_VALIDATED`** rather than a narrowed claim of partial validation.

---

## 7. What a passed Gate 2 does and does not mean

It means the engine's arithmetic is correct, its ordering is causal, its costs are charged as
declared, and it detects the twelve error classes the constitution names. That is a statement about
the instrument.

It is not a statement about any strategy, because none exists. It is not evidence that the declared
costs match real trading costs — they are a proxy and cannot be validated without quote data or fill
data, which arrive at gate 7 paper trading and not before. And it is not evidence that a backtested
result will be realized, which no backtest of any quality can establish.

---

## 8. Explicit non-authorizations, restated for this stage

Stage 2 does not authorize, and this stage will not perform:

- any read of validation-window or holdout-window data, for any purpose;
- any strategy definition, signal, parameter search, ranking, or performance claim;
- any credential access, or any read of a secret value;
- any order, paper or live;
- any modification of a frozen Stage 0 or Stage 1 artifact;
- any purchase, subscription, or account creation.

`live_trading_authorized` remains `false`.

---

## 9. Pre-freeze disclosure

Before this document was written, this session read the Stage 0 constitution, the Stage 1 artifacts
and their freeze records, the normalized data schema, and the existing source modules, and ran the
existing 140-test suite to establish a clean baseline. No backtest was run, no equity curve was
computed, and no price series was inspected for its returns. The two configuration files sealed here
were authored in this session; the fixture arithmetic in `stage2_engine_spec.json` was computed by
hand and checked twice, with no engine available to check it against.
