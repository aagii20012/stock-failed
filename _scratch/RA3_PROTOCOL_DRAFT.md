# Stage 3 (Generation 2, Attempt 3) — cross-sectional rotation under risk architecture RA3 and representative-selection rule SE100-G2-SEL-2

| Field | Value |
|---|---|
| Document id | `SE100-GOV-2007` |
| Status | `SEALED` |
| Project | StockEdge100 |
| Generation | 2 |
| Generation id | `SE100-GEN2-7394207c543401e2` |
| Stage | 3 |
| Gate | 3 — development admissibility |
| Attempt | 3 |
| Authored (UTC) | 2026-08-16T06:59:30Z |
| Charter | [STAGE_10_GENERATION_2_CHARTER.md](STAGE_10_GENERATION_2_CHARTER.md) (`SE100-GOV-2001`) |
| Partition lock | [STAGE_1_G2_PARTITION_LOCK.md](STAGE_1_G2_PARTITION_LOCK.md) (`SE100-GOV-2002`) |
| Attempt 1 protocol | [STAGE_3_G2_ROTATION_PROTOCOL.md](STAGE_3_G2_ROTATION_PROTOCOL.md) (`SE100-GOV-2003`) — closed, read-only |
| Attempt 2 protocol | [STAGE_3_G2_ROTATION_RA1_PROTOCOL.md](STAGE_3_G2_ROTATION_RA1_PROTOCOL.md) (`SE100-GOV-2005`) — closed, read-only |
| Constitution | `SE100-GOV-0001` 3, 4, 5.1, 6.1, 9 gate 3, 11 |
| Machine companion | `STAGE_3_G2_ROTATION_RA3_PROTOCOL.json`, sealed by `STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256` |
| Source of record | `config/generation_2/g2_rotation_ra3_protocol.json` (`SE100-CFG-3105`) |
| Gate criteria | `config/generation_2/g2_gate_criteria_ra3.json` (`SE100-CFG-3106`) |
| `live_trading_authorized` | `false` |

This protocol, in both of its sealed forms - governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md and its JSON companion, of which config/generation_2/g2_rotation_ra3_protocol.json is the source of record - was written and sealed before any Attempt 3 strategy, engine, selection, gate or runner module existed, and before any Attempt 3 variant was run. That claim is machine-checked by the sealer, which measures contamination before it writes: no module under src/stockedge100 or tests may name this attempt's strategy_id, and every one of the seventeen Attempt 1 and Attempt 2 modules must still match the digest its own run record recorded. See declared_before_any_strategy_code_measurement. What this file cannot claim, and does not claim, is that the *development window* is pristine for this hypothesis family. It is not, and it is now less pristine than it was when SE100-CFG-3103 said the same thing: two full eighteen-variant grids have been run on this window and both results are known. See adaptation_disclosure_verbatim.

This is the third attempt at Gate 3 in Generation 2 and the third disclosed adaptation on one hypothesis family. It changes exactly two things from Attempt 2 — the de-risk ladder and the representative-selection rule — and nothing else. Section 1 states both changes, section 14.1 carries the mandated adaptation disclosure verbatim, and section 12 declares the structural consequences of both changes before any variant is run.

## 1. What is pre-registered

| Field | Value |
|---|---|
| Strategy id | `SE100-G2-S3-C3-ROTATION-RA3` |
| Candidate index | 3 |
| Family | CROSS_SECTIONAL_RELATIVE_STRENGTH_RISK_ARCHITECTURE |
| Attempt | 3 |
| Risk architecture | `RA3` — Generation 2 Attempt 3 risk architecture |
| Selection rule | `SE100-G2-SEL-2` |
| Declared before any strategy code | `true` |
| Currency | USD |

**Hypothesis.** Cross-sectional relative strength over a fixed 34-member ETF universe, held in an equally weighted top-k basket and refreshed on a fixed calendar, produces a positive net return over the Generation 2 development window while remaining inside the constitutional research-shutdown ceiling, WHEN exposure is capped at half of equity, scaled down by realized portfolio volatility, staged down further once the equity drawdown reaches 8 percent, and cut at the position level by a fixed stop.

**Candidate index note.** C3, not C2 and not C1. Attempt 3 is a distinct candidate specification, not a re-run of Attempt 2's: it holds full sizing through a band in which Attempt 2's candidate was throttled to 75 percent, and it is selected by a different frozen rule. Constitution section 9 makes a gate conjunctive *within a candidate*, so reusing C2 would attach Attempt 2's already-recorded FAIL to the same candidate id and make two results look like one candidate evaluated twice. They are three candidates, evaluated once each, in a family whose development window is no longer pristine and has now been read twice. See G2A3-CONFLICT-24 in SE100-CFG-3106.

**What this attempt changes from attempt 2.** Exactly two things, and nothing else. (1) The de-risk ladder loses its 5-to-8 percent rung, reverting to the three-band spacing Generation 1's RA1-5 sealed before Attempt 1 was ever run. (2) The representative-selection rule changes from lowest turnover to SE100-G2-SEL-2, a neighbourhood-stability score over four risk-behaviour counters. The signal, the universe, the calendar, the grid, the cost model, the gate thresholds, the aggregate ceiling, the volatility target, the stop, the lockout, the throttle and the episode ledger are all held fixed. Because two things change rather than one, this attempt cannot by itself attribute an outcome to either. That is stated here, before the run, rather than discovered afterwards.

**What this attempt adds over attempt 1.** Attempt 1 tested the rotation signal with no mechanism to reduce exposure before a research-shutdown breach: between scheduled rebalances it issued no orders at all. Attempt 2 holds the signal, the universe, the calendar, the grid, the cost model and the gate thresholds fixed and adds only risk architecture. Any difference in outcome is therefore attributable to the risk architecture rather than to a re-tuned signal - which is the only reason a second attempt on a contaminated window is worth running at all.

**What this attempt adds over attempt 1 carriage.** Copied verbatim from SE100-CFG-3103. It describes the risk architecture Attempt 3 still carries, minus one rung, and is retained so the lineage statement is not silently reworded.

**What makes this genuinely cross sectional.** The ranking scores all 34 eligible members against each other on one date and takes the top k. It is not k independent single-symbol rules run side by side: a symbol is held because it outranked the other 33, not because it cleared an absolute threshold. The risk architecture added in Attempt 2 is portfolio-level (aggregate ceiling, portfolio volatility, portfolio drawdown ladder) with one position-level component (the stop), and none of it re-scores a symbol against anything but the basket it is already in.

### 1.1 Frozen inputs, re-verified at seal time

| Artifact | SHA-256 |
|---|---|
| `governance/STAGE_0_CONSTITUTION.md` | b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5 |
| `governance/STAGE_0_CONSTITUTION.json` | af45fda6b37bed50768d5f3d01d4a91175da93e708c9daf1b630e35a981e2ff5 |
| `governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md` | 865a2feffe683e0baf71f1ab976e286fbb2d003109ab47cfaffc1fe6a63dbc90 |
| `governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md` | 5ae2408dc318e5b87a054a6014e4439d8c6b1934748617c787720f63356b0773 |
| `governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md` (JSON companion) | e17ea82c499d51cf23fc9986e7231dce6388f8a3c7394d3dd3c0e3d27fbacbe7 |
| `config/generation_2/g2_cost_model.json` | b9491485b9560b948ec83d3eb86ee4946c1e83b128a368b71473d14ad0f73650 |
| `config/generation_2/g2_rotation_protocol.json` (Attempt 1) | 1cc5f94ffa70d66e059182a6330bffab2a72f7e4f46db07e50c2924f42799810 |
| `config/generation_2/g2_gate_criteria.json` (Attempt 1) | a1ac96f98dcbe9e5ce975f2eb27914fcbc7728cad6355a1650dc1ec137ad0d31 |
| `governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.md` (Attempt 1) | be8f9320036de8eb4503a111e77f99f337832229898de185a0b8e6f6d0cd8a63 |
| `governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json` (Attempt 1) | f805129dba90bc9e7877d62547c27dcfd599cd9ccd75046cd643d676a8c4a547 |
| `governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.sha256` (Attempt 1) | 64d1377705dd3ae6ffc710f39a2616e2285c5610b593f7223f4e8ce7fde026b1 |
| `governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md` (Attempt 1) | 07a1ec202060de83820e284bd110486fd9e38f8e7ccaff3f3e4b97ec0fffc939 |
| `reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json` (Attempt 1) | 5c46393b69b1048a045c8401f5ea40edc82039a9cd319d0980a39a2efbea5955 |
| `reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json` (Attempt 1) | 5c7d3238f51965cdff37fec0a1b4ec27bc261288ab5cfbd65485e4a820b9bbb1 |
| `reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json` (Attempt 1) | 8d0510d7aadce4ffecc871c71941729e7ca8dc3f563b3fcaeb888a2dc0bdc99f |
| `config/generation_2/g2_rotation_ra1_protocol.json` (Attempt 2) | 0054edce91a8a49dc39f4f53529969902e318ddc3d67e9cc0307e2c015ca6880 |
| `config/generation_2/g2_gate_criteria_ra1.json` (Attempt 2) | 3b9626214db6a6f6183384456489338ea19a277866e35a1aa6c09b0bacb3e625 |
| `governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md` (Attempt 2) | 40e39f13e85574dc15cdb11ae57bc8bb45a16c62164a08e6d545f4924c95553a |
| `governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json` (Attempt 2) | c1a4742b93ca1e34e6e119012f756720446ac9a125441c6ab4b802259858a2dc |
| `governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256` (Attempt 2) | ee96a4678ff2770c60a59b783625e4a165991bf7948ce5f30daaf2820f70f148 |
| `governance/generation_2/STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md` (Attempt 2) | 96db0e2f809fefc8ef7e9248524d8a7465cfd0dfeb7b1a6835e1a8f7291e0169 |
| `reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json` (Attempt 2) | b0d90cf5dd70dad113b747312f462ba4f54151bf24bcf3e5ec668f2ce344bfdb |
| `reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json` (Attempt 2) | 6f0c8f861541cb38cf9769658a72dc28994c1763f844db164beed4355ce00b91 |
| `reports/stage3_g2_attempt2/STAGE_3_G2_A2_ARTIFACT_MANIFEST.json` (Attempt 2) | 468643612dcf9e7b08d5ad6810085c011a9eb79f15ae93738734f0d9f55551d2 |

**Refs reverified.** Every digest in this block, in attempt_1_ref and in attempt_2_ref was recomputed from the file it names at the moment this file was generated. None was transcribed from SE100-CFG-3103 without being checked against the file itself.

### 1.2 Mechanics carried unchanged

**Method.** Each block was copied from SE100-CFG-3103 programmatically, not retyped, so a transcription difference between the two attempts is impossible by construction. Only grid.variant_id_format and grid.variants[].variant_id differ, because a variant id encodes the candidate index and the architecture name.

**Why this matters.** Attempt 3 changes two things. Any third difference, including an accidental one in a constant nobody re-read, would make the result uninterpretable.

- `eligible_universe`
- `ranking_signal`
- `ranking_rule`
- `position_count`
- `rebalance`
- `execution`
- `position_sizing`
- `concentration_ceiling`
- `window`
- `run_span`
- `grid`
- `runs_per_variant`
- `gate_evaluation_scope`

### 1.3 Serialisation

| Field | Value |
|---|---|
| Numbers | Every quantity that enters arithmetic is a decimal STRING, parsed with stockedge100.backtest.config.dec, which refuses float input. |
| Dates | ISO-8601 calendar dates, exchange sessions only. |
| Rounding | stockedge100.backtest.costs.ENGINE_CONTEXT, prec=34, ROUND_HALF_EVEN, with explicit ROUND_FLOOR / ROUND_CEILING cent quantization at the adverse boundary and explicit ROUND_DOWN where a fraction is quantized to share_decimals. |

## 2. Eligible universe

| Field | Value |
|---|---|
| Source | governance/STAGE_1_UNIVERSE.json |
| Source SHA-256 | 01601a60fa950a2429f72a2e9f627ec5af4c1853d1b47ffab35e81debc7eb67a |
| Universe version | SE100-U1-d4917c2f7f1cd834 |
| Universe identity SHA-256 | d4917c2f7f1cd8344728a39165929b352766fbe7193b3c64e71a971749dcbf38 |
| Member count | 34 |
| Unchanged from attempt 1 | true |

```
AGG      TLT
BND      VEA
DIA      VGK
DVY      VIG
EEM      VNQ
EFA      VTI
HYG      VWO
IEF      VYM
IVV      XLB
IWM      XLE
IYR      XLF
LQD      XLI
MDY      XLK
QQQ      XLP
SHY      XLU
SPY      XLV
TIP      XLY
```

**Eligibility recheck convention.** Generation 2 re-checks eligibility on development data only and never adds, drops or substitutes a symbol. The membership is Stage 1's and is frozen.

**Excluded symbols.**

- `AAPL` — Present in the data tree as a Stage 2 single-symbol fixture. Never a member of the eligible universe and never ranked.

## 3. Ranking signal

| Field | Value |
|---|---|
| Name | N_MONTH_TOTAL_RETURN_BACKWARD_DIVIDEND_CHAIN |
| Unchanged from attempt 1 | true |
| Implementation reuse | stockedge100.strategies.g2_rotation.total_return is imported and called unmodified. Reimplementing a sealed formula for a second attempt would create two definitions of one signal and a place for them to diverge; importing it keeps the signal literally identical and makes 'the signal did not change' checkable rather than asserted. |

```
TR(t0 -> t1) = (close[t1] / close[t0]) / product over sessions s in (t0, t1] of (1 - D[s] / close[s-1]) - 1
```

**Look ahead note.** An adjusted-close read at t1 would be a look-ahead: adj_close[t1] is a function of every dividend paid after t1. The product form above touches only sessions inside the interval. adj_close is never read by the ranking signal, in either attempt.

**Undefined result.** None means excluded from this date's ranking, recorded as an exclusion event. It never means zero.

| Field | Value |
|---|---|
| Sort key | (-signal, symbol) |
| Tie break | Ascending ticker, applied to exactly equal Decimal signals, so the result cannot depend on dict insertion order or file load order. |
| Unchanged from attempt 1 | true |

## 4. Portfolio construction and position sizing

| Field | Value |
|---|---|
| Axis | top_k |
| Values | [1, 2, 3] |
| Unchanged from attempt 1 | true |

**Target weight formula.** w(k) = min(A / k, C), quantized to nine decimal places with ROUND_DOWN, where A = 0.50 is the Attempt 2 aggregate exposure ceiling (RA2-1) and C = 0.50 is the sealed per-position concentration ceiling.

**Changed from attempt 1.** `true`

**Attempt 1 formula.** w(k) = min(0.95 / k, 0.50)

**Why changed.** Attempt 1 sized against the constitutional 95% gross ceiling. RA2-1 caps aggregate exposure at 50% of equity, so sizing k positions at 0.95/k each would demand 95% gross and be clamped down to 50% on every rebalance - the strategy would be defined by its clamp rather than by its weights. The weight is derived from the ceiling that actually binds.

| k | Target weight per position | Target gross exposure |
|---|---|---|
| 1 | 0.500000000 | 0.500000000 |
| 2 | 0.250000000 | 0.500000000 |
| 3 | 0.166666666 | 0.499999998 |

**Round down note.** ROUND_DOWN is load-bearing. At prec=34 and ROUND_HALF_EVEN, 0.50 / 3 rounds up and three such weights exceed the ceiling by one ulp, which would make the aggregate clamp bind on the last buy of every k=3 rebalance for a pure representation reason. The 0.499999998 above is that ulp, taken deliberately on the safe side.

**Equal weight is an entry rule.** A symbol that survives a rebalance is left exactly as it is - never trimmed to target, never topped up. Carried unchanged from Attempt 1's G2-CONFLICT-10. The Attempt 2 throttle is not an exception to this: it trims toward the aggregate ceiling, never toward a per-position target, and it fires only when the ceiling is breached.

**Budget evaluated at the open.**

- *Statement* — The entry budget recorded on the OrderRequest is w(k) * equity at the decision close. The engine re-evaluates w(k) * f(t) * equity at the fill session's open, where f(t) is the combined risk scalar measured at the decision close.
- *Why* — A frozen Order has nowhere to carry a weight, so the recorded budget is the record of the intent rather than the number that sizes the fill. Carried from Attempt 1's G2-CONFLICT-16.
- *Scalar timing* — f(t) is measured at the close of the decision session t and is the value in force when the order fills at the open of t+1. This is not a choice: the engine's session loop records equity and updates risk state at step 6 and takes decisions at step 7, and fills happen at step 2 of the following session, so the scalar read at fill time is necessarily the decision session's. Using t+1's scalar would require measuring a close that has not happened.

**Attempt 1 k1 half cash bias neutralised.**

- *Attempt 1 condition* — Under w(k) = min(0.95/k, 0.50), k=1 targeted 50% gross while k=2 and k=3 targeted 95%. Attempt 1 declared this as SC-3: the k=1 variants were structurally half in cash and so were structurally less likely to breach the shutdown screen than their k=2 and k=3 siblings, which biases a selection rule whose first criterion is zero shutdown events.
- *Attempt 2 condition* — Under w(k) = min(0.50/k, 0.50) all three k values target the same 50% gross. The bias is removed, not by adjusting the selection rule, but because the ceiling that produced it now applies uniformly.
- *Honesty note* — This is a genuine improvement in the comparability of the eighteen variants and it was not the reason RA2-1 was chosen; RA2-1 was specified in the operating prompt as a risk control. It is recorded because a reader comparing the two attempts' selection outcomes needs to know that the k axis is no longer confounded with gross exposure.
- *Conflict ref* — G2A2-CONFLICT-7

### 4.1 Concentration ceiling

| Field | Value |
|---|---|
| Value | 0.50 |
| Source | config/stage3_attempt2_strategy_protocol.json risk_architecture.RA1-1.rule, f_base = 0.50 |
| Source SHA-256 | 77f1451c20e37640bd2843ff86d69eb54cbc0ebb592a696972fbdea6e05b5433 |
| Scope | Per position, as a fraction of equity, evaluated at the fill open. |
| Unchanged from attempt 1 | true |

**Non binding note.**

- *Statement* — With the aggregate ceiling at 0.50, the per-position concentration ceiling is non-binding for k = 2 and k = 3 (targets 0.25 and 0.1666...) and exactly coincident with the aggregate ceiling for k = 1 (target 0.50).
- *Why it is still enforced* — It is a sealed clamp of the Generation 2 engine and is left in place and still checked. A clamp that never binds is not a clamp that may be removed - removing it would mean that a future change to the aggregate ceiling silently removed the per-position bound too.
- *Conflict ref* — G2A2-CONFLICT-11

## 5. Risk architecture `RA3`

| Field | Value |
|---|---|
| Id | RA3 |
| Name | Generation 2 Attempt 3 risk architecture |
| Frozen before any variant is run | true |
| Not part of the grid | true |
| Derived from | RA2, by deleting one ladder band. Four of the five components are identical. |

**Provenance.** RA3-1, RA3-2, RA3-3 and RA3-5 are RA2-1, RA2-2, RA2-3 and RA2-5 unchanged, which are in turn the values of the Attempt 2 operating prompt and, for RA2-2 and RA2-3, of Generation 1's RA1. RA3-4 is Generation 1's RA1-5 ladder restored: see components.RA3-4.provenance, which quotes SE100-CFG-3103's own statement that only RA2-4's band 1 was new. Every constant in RA3 was therefore sealed before Attempt 1 ran.

**Single difference from RA2.** RA2-4's band 1 (0.05 <= dd < 0.08, scalar 0.75) is deleted and band 0 is extended to 0.08. No other threshold, scalar, formula, order of operations or code path differs. The engine subclasses Attempt 2's and overrides the band table and the state derived from it; see G2A3-CONFLICT-31.

**Why not gridded.** Every constant below is fixed and applied uniformly to all eighteen variants. Searching them alongside the rotation parameters would cross from a disclosed risk control into curve-fitting to 2008 and 2020 - the two episodes whose observation motivated this attempt in the first place. The grid remains exactly the eighteen rotation parameterisations of Attempt 1 and is not widened.

### 5.1 Provenance of the constants

The de-risk ladder is the one component that changed, and it changed by reverting. The table below is computed at generation time: the absolute ceiling column is `f_base * scalar` from this document's own band table, and the Generation 1 column is parsed out of `config/stage3_attempt2_strategy_protocol.json`'s sealed `RA1-5` rule list. The `Same?` column is the comparison of those two, not an assertion about them.

| Band | Drawdown from HWM | Scalar | Absolute ceiling | Generation 1 `RA1-5` | Same? |
|---|---|---|---|---|---|
| 0 | `dd < 0.08` | 1.00 | 0.500 | 0.500 (`dd < 0.08`) | yes |
| 1 | `0.08 <= dd < 0.10` | 0.50 | 0.250 | 0.250 (`0.08 <= dd < 0.10`) | yes |
| 2 | `dd >= 0.10` | 0.25 | 0.125 | 0.125 (`dd >= 0.10`) | yes |

Every row answers yes. Under RA2 the corresponding table had four rows and one of them answered no: band 1, `0.05 <= dd < 0.08` at scalar 0.75, which Generation 1's ladder did not have. Deleting it is this attempt's architectural change, and it leaves RA3 with no post-Attempt-1 degree of freedom in it at all.

### 5.2 `RA3-1` — aggregate_exposure_ceiling

| Field | Value |
|---|---|
| Value | 0.50 |
| Unit | fraction of equity |
| Purpose | Tighter than the base constitutional 95% gross ceiling. |
| Inherited unchanged from | RA2-1 |

**Definition.** gross(t) = sum over held symbols of quantity * close(t). The ceiling in force at session t is ceiling(t) = 0.50 * f(t) * equity(t), where f(t) is the combined risk scalar defined below. gross(t) must not exceed ceiling(t).

**Part a entry clamp.**

- *Name* — AGGREGATE_RA2
- *Rule* — At the fill open, the budget for an entry is clamped to max(0, 0.50 * f * equity_open - position_value_open), where position_value_open is the gross value of the book as already settled on that open. Because the Attempt 1 engine executes all SELL legs before any BUY leg and re-reads the book between buys, the clamp is evaluated against the settled book and cannot be breached by the ordering of legs within one rebalance.
- *Why a new clamp and not a lower cost model ceiling* — stockedge100.backtest.g2_costs.derive_mapping permits exactly one JSON-pointer difference from the Generation 1 sealed cost model, and that single permitted override is already spent on /account/max_open_risky_positions. Lowering max_gross_exposure_fraction to 0.50 would require a second override and would silently change the meaning of every cost-model-derived quantity Attempt 1 recorded. RA2-1 is therefore a new named clamp in the Attempt 2 engine, applied in addition to - not instead of - the inherited 0.95 AGGREGATE clamp, which remains in place and is simply never the binding one.
- *Clamp names* — ["REQUESTED_BUDGET", "AGGREGATE_RA2", "AGGREGATE", "CASH_FLOOR", "CONCENTRATION"]
- *Clamp order note* — AGGREGATE_RA2 is evaluated before the inherited AGGREGATE so that the binding clamp is reported by its own name rather than being masked by a looser one.
- *Over ceiling behaviour* — If the book is already at or above the ceiling when an entry is decided, the clamp yields a budget of zero and the entry is rejected. That is the correct conservative outcome and it is not an error.
- *Rejection reason* — INSUFFICIENT_CASH, with the clamp named in the detail string.
- *Why that reason* — stockedge100.backtest.orders.REASONS is a closed declared set. Inventing an AGGREGATE_RA2 rejection reason at runtime would widen a sealed set. The existing reason is reused and the clamp is named in the detail, exactly as Attempt 1's own clamps do.
- *Conflict refs* — ["G2A2-CONFLICT-2", "G2A2-CONFLICT-16"]

**Part b continuous throttle.**

- *Rule* — At every session close t at which the strategy takes a decision, compute the projected book after any STOP and EXIT legs already merged for that session. If projected_gross(t) exceeds ceiling(t), sell down the excess, largest projected position value first, ties broken by ascending symbol, scheduling partial SELL legs for the next open.
- *Why this is mandatory and not an extra* — A ladder that reduced sizing only at entries would do nothing at all between scheduled rebalances - which is precisely when Attempt 1's drawdowns happened. A quarterly variant takes 53 decisions about size in thirteen years. The operating prompt's statement of the problem is that Attempt 1 'had no mechanism to reduce exposure before a breach'; the continuous throttle IS that mechanism, and the de-risk ladder is inert without it.
- *Appreciation drift worked example* — Start gross 50, cash 50, equity 100, exposure 0.500. The position doubles: gross 100, cash 50, equity 150, exposure 0.667. No order was placed and the ceiling is breached by a third. Only a continuous measurement catches this.
- *Minimum notional skip* — A trim leg whose notional would fall below the sealed min_order_notional is skipped rather than submitted, because the engine would reject it as MIN_NOTIONAL anyway. Skipped legs are counted as throttle_legs_below_min_notional and reported per variant. The consequence is that the ceiling can be transiently exceeded by less than one minimum lot; that is disclosed rather than papered over.
- *Turnover cost* — The throttle adds fills, and total fill count is the representative-selection tiebreak. This is a real and declared structural consequence: see SC-4.
- *Conflict ref* — G2A2-CONFLICT-17

**Part c measurement.**

- *Rule* — max_gross_fraction_observed = max over sessions of gross(t) / equity(t) is recorded for every run and reported for every variant.
- *Purpose* — The ceiling is a claim about behaviour. The measurement is what makes it checkable. A run whose maximum observed gross fraction exceeds 0.50 by more than the declared minimum-notional slack is a defect, not a result.
- *Assertion* — The engine asserts the ceiling holds after every fill and raises rather than continuing.

**Carriage.** Copied verbatim from SE100-CFG-3103's RA2-1. Prose inside it that says 'Attempt 2' or 'RA2-1' refers to the attempt and component the text was written for; the mechanism, its constants and its code path are inherited by RA3-1 unchanged and are not reimplemented. Runtime identifiers keep their original names for the same reason — the clamp is still called AGGREGATE_RA2 in the engine because it is literally the same code, and renaming it would suggest a change that did not happen.

### 5.3 `RA3-2` — portfolio_volatility_target

| Field | Value |
|---|---|
| Value | 0.10 |
| Unit | annualized standard deviation of portfolio returns |
| Purpose | Position sizing scales down when trailing realized volatility exceeds target. Carried from Generation 1's RA1. |
| Measured on | THE_EQUITY_CURVE |
| Inherited unchanged from | RA2-2 |

**Definition.** At session t, take the last 21 recorded equity points, form the 20 session-over-session simple returns r_i = E_i / E_(i-1) - 1, take the sample standard deviation with denominator 19, and multiply by the square root of 252. That is sigma_p(t).

**Shape note.** This is exactly the shape of stockedge100.strategies.attempt2_indicators.vol20 - 21 bars, 20 returns, divide by 19, times sqrt(252) - applied to the equity curve rather than to a price series. The window length, the sample denominator and the annualisation factor are Generation 1's and are not re-chosen here.

**Why the equity curve and not a price series.** Section 3 of the operating prompt specifies a portfolio-level volatility target. A weighted average of member volatilities is not the portfolio's volatility - it ignores the correlations that are the entire reason a k=3 basket differs from three k=1 baskets, and it ignores the cash. The equity curve is the portfolio's realized return series by definition. It also sidesteps the adj_close look-ahead exception entirely: the equity curve is built from marks the engine has already taken and contains no forward-looking column.

**Scalar.** f_vol(t) = min(1, 0.10 / sigma_p(t)) when sigma_p(t) > 0, else 1. Quantized to nine decimal places, ROUND_DOWN.

**Undefined before 21 points.** f_vol(t) = 1. The strategy is not scaled down for lack of a measurement.

**Run start note.** Before the first fill the equity curve is flat, every return is exactly zero, sigma_p is zero and f_vol is 1. This is correct and not a special case: a portfolio of cash has no volatility to target.

**Self reference.**

- *Statement* — sigma_p is measured on an equity curve that f_vol itself influences. Lower exposure produces a lower measured volatility, which raises f_vol, which raises exposure.
- *Assessment* — The feedback is negative and therefore stabilising, and it is damped by a 20-session lag. It is not a circularity that can diverge, and it is not corrected here - correcting it would mean measuring a counterfactual unlevered equity curve, which is a second backtest with its own assumptions.
- *Measurement* — The realized distribution of f_vol is reported per variant (minimum, mean, and the count of sessions on which it was below 1), so a reader can see how often the term actually bound.
- *Conflict ref* — G2A2-CONFLICT-13

**Carriage.** Copied verbatim from SE100-CFG-3103's RA2-2. Prose inside it that says 'Attempt 2' or 'RA2-2' refers to the attempt and component the text was written for; the mechanism, its constants and its code path are inherited by RA3-2 unchanged and are not reimplemented. Runtime identifiers keep their original names for the same reason — the clamp is still called AGGREGATE_RA2 in the engine because it is literally the same code, and renaming it would suggest a change that did not happen.

### 5.4 `RA3-3` — per_position_stop

| Field | Value |
|---|---|
| Value | 0.08 |
| Unit | fractional loss from entry price |
| Purpose | Cut a position that has moved 8% against the entry. Same threshold Generation 1's RA1 used. |
| Reference price | cost_basis / quantity |
| Inherited unchanged from | RA2-3 |

**Reference price definition.**

- *Statement* — stockedge100.backtest.portfolio.Position carries no entry price. It carries cost_basis, which is the all-in cash paid for the position including commission and fees, because the engine debits -fill.cash_delta. The stop reference is therefore the all-in per-share cost basis, not the raw fill reference price.
- *Consequence* — The reference is very slightly above the traded price, by the per-share commission and fees, so the stop triggers marginally earlier than a raw-price stop would. The difference is on the order of a basis point at the sealed cost model and is in the conservative direction.
- *Why frozen explicitly* — Leaving 'entry price' implied would let the implementation choose between two defensible readings after seeing which one performed better. It is frozen here so it cannot be.
- *Partial sell note* — The Attempt 1 portfolio prorates cost_basis on a partial sell, so cost_basis / quantity is invariant under a throttle trim. A trimmed position keeps the same stop reference it had before the trim.
- *Conflict ref* — G2A2-CONFLICT-14

**Condition.** close(t) <= (1 - 0.08) * (cost_basis / quantity)

**Evaluated at.** session close

**Exit at.** next session open, whole position

**Interaction with rebalance.** A stop and a scheduled signal exit on the same symbol on the same session are the same fill; the STOP tag wins by precedence and the coincidence is counted.

**No re entry bar.** A symbol stopped out may be re-entered at a later scheduled rebalance if it ranks in the top k. There is no per-symbol cooldown. Adding one would be a second free parameter and it was not specified.

**Measurement.** Stop exits are counted per variant, and the realized loss at each stop fill is recorded so the report can state how far past 8% the one-session lag actually carried.

**Carriage.** Copied verbatim from SE100-CFG-3103's RA2-3. Prose inside it that says 'Attempt 2' or 'RA2-3' refers to the attempt and component the text was written for; the mechanism, its constants and its code path are inherited by RA3-3 unchanged and are not reimplemented. Runtime identifiers keep their original names for the same reason — the clamp is still called AGGREGATE_RA2 in the engine because it is literally the same code, and renaming it would suggest a change that did not happen.

### 5.5 `RA3-4` — de_risk_ladder

**Purpose.** Staged exposure reduction as the drawdown from the equity high-water mark deepens, re-normalizing as the drawdown recovers. The one changed component of this attempt.

**Derived from.** RA2-4, with band 1 deleted and the remaining bands renumbered.

**Inherited unchanged from.** `null`

**Drawdown definition.** dd(t) = (high_water(t) - equity(t)) / high_water(t), where high_water(t) is the running maximum of equity including session t. This is the same high-water mark the constitutional research shutdown uses, read from the engine rather than recomputed, so the ladder and the shutdown cannot disagree about the drawdown.

`Inherited unchanged from` is `null` for this component alone. The other four name the RA2 component they are byte-equal to; this one cannot, because it is the component that changed.

| Band | Condition | `f_ladder` |
|---|---|---|
| 0 | `0.00 <= dd < 0.08` | 1.00 |
| 1 | `0.08 <= dd < 0.10` | 0.50 |
| 2 | `dd >= 0.10` | 0.25 |

**Boundary convention.** Each band is closed at its lower bound and open at its upper bound, so dd exactly equal to 0.08 is band 1, not band 0. Stated because a threshold is a decision and an inequality direction chosen at implementation time is a free parameter. The convention is RA2-4's and is not re-chosen; only the threshold it applies to has moved.

**Descent.** Immediate and to the full computed band. If the band computed from dd(t) is above the current band, the current band becomes that band in one step, at session t. There is no smoothing of the descent - a fast drawdown is exactly the case the ladder exists for.

**Recovery.** At most one band per session, and only when the computed band is strictly below the current band AND the re-entry lockout of RA3-5 has elapsed. Recovery from band 2 to band 0 therefore requires at least two sessions after the lockout expires. RA2-4's ladder was one rung deeper and required at least three.

**Hysteresis note.** The asymmetry - immediate down, one step up, gated by a cooldown - is the mechanism. A symmetric ladder would re-lever into a bear-market rally at the first band boundary it crossed back over, which is the failure the lockout exists to prevent.

**Scalar.** f_ladder(t) = the scalar of the current band after the transition rule has been applied for session t.

**Measurement.** Per variant: the number of downward transitions (ladder descents), the number of upward transitions, the deepest band reached, the number of sessions spent in each band, and the number of sessions on which a recovery was computed but blocked by the lockout. All five are reported alongside Attempt 2's corresponding figures, and the descent count is one of SE100-G2-SEL-2's four inputs.

**Provenance.**

- *Statement* — RA3-4 is not a new ladder. It is Generation 1's sealed RA1-5 ladder, restored. SE100-CFG-3103's own provenance field records that three of RA2-4's four bands reproduce the RA1-5 f_cap values exactly and that 'only band 1 is new'. Deleting band 1 therefore leaves an architecture with no post-Attempt-1 degree of freedom in it at all.
- *Quoted from attempt 2* — RA2-1, RA2-2, RA2-3 and RA2-5 take the values specified in the Stage 3 Attempt 2 operating prompt. RA2-4's ladder thresholds and scalars take the prompt's proposed -5/-8/-10 to 75%/50%/25% staging; the prompt permitted a more principled staging with documented reasoning, and none was found that was not itself a fit to the observed drawdown dates, so the proposed staging is adopted unchanged. That staging is nevertheless not unsourced. Expressed as absolute aggregate ceilings (f_base * ladder scalar), three of RA2-4's four bands reproduce the sealed Generation 1 RA1-5 f_cap values exactly: band 0 gives 0.500000000 against RA1-5's 0.500000000 for dd < 0.08, band 2 gives 0.250000000 against RA1-5's 0.250000000 for 0.08 <= dd < 0.10, and band 3 gives 0.125000000 against RA1-5's 0.125000000 for dd >= 0.10. Only band 1 is new, and it is new as a subdivision rather than as a value: RA1-5 has no threshold at 0.05 and holds f_cap flat at 0.500000000 across the whole of [0.05, 0.08), which RA2-4 splits and tightens to 0.375000000. RA2-4 is therefore a strict tightening of an architecture that was sealed before Attempt 1's results existed, not a fresh choice made after seeing them, and the single degree of freedom it adds is one threshold and one scalar. RA2-2 and RA2-3 are carried from Generation 1's RA1 (config/stage3_attempt2_strategy_protocol.json), which is why this architecture is named RA2 and its modules carry the _ra1 suffix that names their lineage.
- *Absolute ceilings* — Expressed as absolute aggregate ceilings (f_base * ladder scalar), RA3-4's three bands give 0.500000000 for dd < 0.08, 0.250000000 for 0.08 <= dd < 0.10 and 0.125000000 for dd >= 0.10. Those are the three RA1-5 f_cap values SE100-CFG-3103 names, in the same order, at the same thresholds.
- *Degrees of freedom added by this change* — 0
- *Degrees of freedom removed by this change* — One threshold (0.05) and one scalar (0.75) — precisely the pair SE100-CFG-3103 identified as 'the single degree of freedom it adds'.
- *Why this direction* — The adaptation disclosure states the reasoning: a 5-percent-from-peak dip is common in ordinary markets, so a rung at 5 percent throttles ordinary conditions rather than crises. Attempt 2's own non-return evidence is consistent with that — the combined scalar ran as low as 0.19 and the ladder descended over a thousand times across 36 runs — but consistency is not proof, and no return figure was consulted in making the change.
- *What would falsify the reasoning* — If RA3's ladder-descent counts are close to RA2's, the 5-percent rung was not the cause of the near-constant throttling and the change was aimed at the wrong mechanism. The descent counts are therefore reported per variant against Attempt 2's, and the comparison is required by the operating instruction rather than optional.

**Relationship to the shutdown threshold.**

- *Statement* — The deepest rung still fires at a 10 percent drawdown. The constitutional research shutdown fires at 15 percent, and Gate 3's max-drawdown condition S3-C2 is also 15 percent. The ladder remains entirely inside the threshold it is trying to keep the strategy away from, by construction. What has changed is the shallow end: RA3 holds full sizing across the whole of [0, 0.08), where RA2 throttled to 75 percent from 0.05.
- *Consequence for the gate* — This sharpens Attempt 1's S3-CONFLICT-3. A MET S3-C2 was already near-structural in Generation 2 because the representative-selection rule requires zero shutdown events and a shutdown fires at the same 15%. In Attempt 2 the architecture additionally cuts exposure to a quarter before that point is reached. S3-C2 must therefore be read as almost entirely a statement about the risk architecture and almost not at all about the signal, and it is not independent evidence of an edge.
- *Consequence for the shutdown* — Less exposure reduction on the way down means a shutdown breach is easier to reach than it was in Attempt 2. Attempt 1, with no ladder at all, tripped 36 of 36. Attempt 2, with four rungs, tripped 0 of 36. RA3 sits between them and the outcome is not predictable from either. See G2A3-CONFLICT-29.
- *Conflict refs* — ["G2A2-CONFLICT-15", "G2A3-CONFLICT-22", "G2A3-CONFLICT-29"]

The worst case is worth writing down before it is observed rather than after. Take a run that does nothing but lose the full 0.08 per-position stop on the full permitted aggregate exposure, round trip after round trip, with no recovery between them. The equity compounds down and the ladder tightens as it goes. The table below is computed by the same model that reproduces Attempt 2's sealed nine-row table row for row; only the band table differs.

| Trip | `dd` before | Band | `f_cap` | Loss this trip | `dd` after |
|---|---|---|---|---|---|
| 1 | 0.0000% | 0 | 0.500 | 4.000% | 4.0000% |
| 2 | 4.0000% | 0 | 0.500 | 4.000% | 7.8400% |
| 3 | 7.8400% | 0 | 0.500 | 4.000% | 11.5264% |
| 4 | 11.5264% | 2 | 0.125 | 1.000% | 12.4111% |
| 5 | 12.4111% | 2 | 0.125 | 1.000% | 13.2870% |
| 6 | 13.2870% | 2 | 0.125 | 1.000% | 14.1542% |
| 7 | 14.1542% | 2 | 0.125 | 1.000% | **15.0126% — breach** |

Under RA3 that walk reaches the 15% research-shutdown threshold on trip **7**; under RA2's four rungs it took **9**. RA3 is the shallower brake and it is meant to be. Two things are worth noting. Band **1** is never visited in this walk — the run steps from 7.8400% straight to 11.5264%, jumping the whole of `[0.08, 0.10)` — so a band can be sealed, correct, and still never bind on a fast drawdown. And the walk is a bound, not a forecast: it assumes every position stops out every time with no winning trade in between.

### 5.6 `RA3-5` — re_entry_lockout

| Field | Value |
|---|---|
| Value | 10 |
| Unit | trading sessions |
| Purpose | Minimum cooldown after a de-risk step before exposure returns to full sizing. Prevents re-entering into continued volatility. |
| Inherited unchanged from | RA2-5 |

**Armed by.** Any downward ladder transition. The lockout expires 10 trading sessions after the session on which the transition occurred.

**Not armed by.** An upward ladder transition. Only de-risking arms the cooldown.

**Gates.** Every upward ladder transition, not only the final step to band 0. The stricter reading is taken deliberately: the prompt's phrase is 'before exposure returns to full sizing', and gating only the last step would let a strategy climb from band 3 to band 1 the session after a de-risk and sit at 75% sizing through the drawdown that caused it.

**Counted in sessions not days.** Trading sessions, by index into the run's session list. A calendar-day cooldown would be shortened by a holiday and lengthened by a weekend for no reason connected to the market.

**Measurement.** Per variant: the number of times the lockout was armed (equal to the number of downward transitions), and the number of sessions on which a computed recovery was blocked by it.

**Carriage.** Copied verbatim from SE100-CFG-3103's RA2-5. Prose inside it that says 'Attempt 2' or 'RA2-5' refers to the attempt and component the text was written for; the mechanism, its constants and its code path are inherited by RA3-5 unchanged and are not reimplemented. Runtime identifiers keep their original names for the same reason — the clamp is still called AGGREGATE_RA2 in the engine because it is literally the same code, and renaming it would suggest a change that did not happen.

### 5.7 The combined scalar

```
f(t) = f_vol(t) * f_ladder(t), quantized to nine decimal places, ROUND_DOWN.
```

**Multiplicative not minimum.** The two terms answer different questions - how violent is the market, and how much have we already lost - and a portfolio in a violent drawdown should be smaller than one in either condition alone. min() would discard whichever answer was less extreme.

**Range.** (0, 1]. f(t) = 1 exactly when volatility is at or below target and the drawdown is below 8 percent. Under RA2 the second clause read 5 percent; the widening of that clause is the whole of this attempt's architectural change.

| Applies to | Does not apply to |
|---|---|
| the entry budget at the fill open: w(k) * f * equity | the per-position stop, which is an absolute condition on price and not a sizing rule |
| the aggregate ceiling at every session: 0.50 * f * equity | the constitutional research shutdown, which is the engine's and is not modified by this attempt |

### 5.8 Where the risk state lives

**Owner.** The Attempt 3 engine subclass.

**Why not the candidate.** The candidate sees only DecisionContext, which carries (session, cash, equity, open_symbols, shutdown_active). It carries no per-position cost basis - needed for the stop - and no high-water mark - needed for the ladder. Extending DecisionContext would mean editing stockedge100/backtest/engine.py, a Generation 1 file that is frozen and read-only.

**Why this works.** The Generation 1 session loop runs the risk step (step 6: record equity, update the high-water mark, test the shutdown) strictly before the decision step (step 7: build the DecisionContext and call the candidate). Risk state updated during step 6 is therefore current when step 7 runs, in the same session, with no change to the base loop.

**No generation 1 or prior attempt file is edited.** The Attempt 3 engine subclasses the Attempt 2 RotationEngineRA1, which subclasses the Attempt 1 RotationEngine, which subclasses the frozen Generation 1 engine. Each layer overrides only its own methods. Nothing below Attempt 3 is modified, and all seventeen prior-attempt modules are re-hashed at seal time and again at package time.

## 6. Rebalance calendar

**Axis.** rebalance_frequency

**Values.**

- MONTHLY
- QUARTERLY

**Rule.** A session is a scheduled rebalance if it is the run's first session, or if its calendar month differs from that of the previous session the strategy saw. A quarterly variant additionally requires that month to be one of January, April, July and October.

**Backward looking note.** The calendar looks strictly backwards. Month-end would need tomorrow's date to be decidable today. See Attempt 1's G2-CONFLICT-8, carried unchanged.

**Unchanged from attempt 1.** `true`

| Frequency | Rebalance sessions | First three | Last |
|---|---|---|---|
| `MONTHLY` | 157 | 2008-07-28, 2008-08-01, 2008-09-02 | 2021-07-01 |
| `QUARTERLY` | 53 | 2008-07-28, 2008-10-01, 2009-01-02 | 2021-07-01 |

**Carried from.** config/generation_2/g2_rotation_protocol.json

**Carried from SHA-256.** 1cc5f94ffa70d66e059182a6330bffab2a72f7e4f46db07e50c2924f42799810

**Recheck requirement.** The runner recomputes both counts on the actual session list and refuses to run if either differs. A carried measurement that is not re-measured is a restated constant, and a restated constant can drift.

**Attempt 2 note.** The rebalance calendar governs entries and signal-driven exits only. The stop, the throttle and the ladder are evaluated at every session close, not only on rebalance sessions. That is the departure from Attempt 1 recorded as G2A2-CONFLICT-1.

## 7. Window, run span, and the guard

| Field | Value |
|---|---|
| Development window | 1993-01-29 — 2021-07-31 |
| Last development session | 2021-07-30 |
| Run start | 2008-07-28 (Monday) |
| Run end | 2021-07-30 |
| Sessions | 3276 |
| Development union sessions | 7178 |
| Binding symbol | `VEA`, inception 2007-07-26 |
| Members missing a bar at run start | 0 |
| Symbols ending before run end | 0 |

**Carried from.** config/generation_2/g2_rotation_protocol.json

**Carried from SHA-256.** 1cc5f94ffa70d66e059182a6330bffab2a72f7e4f46db07e50c2924f42799810

**Recheck requirement.** The runner recomputes every value below from the loaded series and refuses to run if any differs.

**Why unchanged.** Attempt 2 changes the strategy, not the data, the universe or the window. An identical run span is what makes the two attempts comparable at all.

**Reverification required.** The span above is carried from Attempt 2 and must not be assumed. The Attempt 3 runner recomputes it from the loaded data before the first variant runs, asserts equality with every field recorded here, and writes the recomputation to reports/stage3_g2_attempt3/run_span_recheck.json. A mismatch is a blocker, not a value to adopt.

**Enforcement.** stockedge100.strategies.g2_window_guard, imported unmodified from Attempt 1. Every series is truncated while parsing, not after, and the bound is re-asserted after loading. Reusing the guard rather than re-deriving the bound is deliberate: a second derivation of the same bound is a second place for it to be wrong.

**Unchanged from attempt 1.** `true`

## 8. Execution

| Event | Timing |
|---|---|
| Fill timing | Orders are decided at a session close and filled at the next session's open. Unchanged from Attempt 1 and from the Generation 1 engine. |
| Entry | A symbol entering the top k at a scheduled rebalance is bought at the next session's open. |
| Signal exit | A symbol dropping out of the top k at a scheduled rebalance is sold in full at the next session's open. |

### 8.1 Order kinds this attempt may issue

| Tag | Side | When | Quantity |
|---|---|---|---|
| `ENTRY` | BUY | scheduled rebalance only | sized by the budget rule below |
| `EXIT` | SELL | scheduled rebalance only | the whole position |
| `STOP` | SELL | any session close at which the stop condition holds | the whole position |
| `THROTTLE` | SELL | any session close at which projected gross exposure exceeds the scaled ceiling | partial, largest position first |
| `SHUTDOWN` | SELL | the session a research shutdown triggers | the whole position |

`SHUTDOWN` is issued by the engine, unchanged from Generation 1

### 8.2 Attempt 1's `no_discretionary_exits` clause is narrowed, not weakened

**Attempt 1 text.** Between scheduled rebalances the strategy issues no orders at all. There is no stop, no trailing stop, no profit target, and no intra-period re-rank.

**Attempt 1 source.** config/generation_2/g2_rotation_protocol.json -> execution.no_discretionary_exits

**Attempt 2 position.** Attempt 2 departs from this clause deliberately and only in the direction of reducing exposure. Between scheduled rebalances Attempt 2 may issue SELL orders - a stop exit or a throttle trim - and may issue no BUY order of any kind. There is still no profit target and still no intra-period re-rank: the ranking is consulted only on scheduled rebalance sessions, exactly as before. The clause is not weakened for entries; it is narrowed to entries.

**Conflict ref.** G2A2-CONFLICT-1

### 8.3 One order per symbol per session

**Constraint.** stockedge100.backtest.orders.OrderBook.submit refuses two orders in one symbol on one decision session whatever the sides are, raising DuplicateOrderError.

**Resolution.** Order kinds are merged by symbol under a frozen precedence before scheduling: STOP > EXIT > THROTTLE > ENTRY. At most one request per symbol reaches the book. An ENTRY can never collide with a STOP, an EXIT or a THROTTLE because all three apply only to currently held symbols and an ENTRY is issued only for symbols not currently held; the precedence is nonetheless applied unconditionally and the merged list is asserted to have unique symbols, because 'cannot happen' is a claim and not a guarantee.

**Coincidence recorded.** A session on which a STOP suppresses an EXIT for the same symbol is counted and reported as stop_preempted_signal_exit. Both are full sells, so the fill is identical; the count exists so the report can say how often the stop was the binding reason rather than a redundant one.

### 8.4 Execution lag

**Statement.** A stop condition observed at the close of session t is exited at the open of session t+1, not at the close of t. A throttle computed at the close of t is trimmed at the open of t+1. The strategy therefore carries one session of exposure past every risk signal it observes.

**Why it is not a defect.** It is the direct consequence of next-session-open execution, which the constitution requires and which both generations use everywhere. The research shutdown itself has exactly the same lag: constitution section 5.1 liquidates at the *next* open, not at the close that triggered it. Attempt 2 does not get a tighter execution convention than the shutdown it is trying to avoid.

**Measurement.** The gap between the close that triggered each stop and the open that filled it is recorded per fill, so the report can state the realized slippage of the lag rather than assert it is small.

**Conflict ref.** G2A2-CONFLICT-5

## 9. The grid

**Size.** 18

**Unchanged from attempt 1.** `true`

**Unchanged from attempt 2.** `true`

**Not widened.** The grid is complete at eighteen and may not be widened, narrowed or re-centred. The risk architecture constants are not axes.

**Enumeration order.** lookback_months outer, then top_k, then rebalance_frequency. The index is part of the seal.

**Variant id format.** SE100-G2-S3-C3-ROTATION-RA3-L{lookback:02d}-K{k}-{FREQUENCY}

**Zero padding note.** The lookback is zero-padded because the final tiebreak of the representative-selection rule is lexicographic, and an unpadded L12 would sort before L3.

**Variant id change note.** Only the candidate index and architecture segment differ from Attempt 2's ids: C2-ROTATION-RA1 becomes C3-ROTATION-RA3. The axes, their orderings, the enumeration order, the zero padding, the target weights and the scheduled-rebalance counts are copied and unchanged, so variant n of Attempt 3 is the same parameterisation as variant n of Attempts 1 and 2 and the three grids are directly comparable row by row.

| Index | Variant id | Lookback (months) | k | Rebalance | Target weight | Target gross | Scheduled sessions |
|---|---|---|---|---|---|---|---|
| 1 | `SE100-G2-S3-C3-ROTATION-RA3-L03-K1-MONTHLY` | 3 | 1 | MONTHLY | 0.500000000 | 0.500000000 | 157 |
| 2 | `SE100-G2-S3-C3-ROTATION-RA3-L03-K1-QUARTERLY` | 3 | 1 | QUARTERLY | 0.500000000 | 0.500000000 | 53 |
| 3 | `SE100-G2-S3-C3-ROTATION-RA3-L03-K2-MONTHLY` | 3 | 2 | MONTHLY | 0.250000000 | 0.500000000 | 157 |
| 4 | `SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY` | 3 | 2 | QUARTERLY | 0.250000000 | 0.500000000 | 53 |
| 5 | `SE100-G2-S3-C3-ROTATION-RA3-L03-K3-MONTHLY` | 3 | 3 | MONTHLY | 0.166666666 | 0.499999998 | 157 |
| 6 | `SE100-G2-S3-C3-ROTATION-RA3-L03-K3-QUARTERLY` | 3 | 3 | QUARTERLY | 0.166666666 | 0.499999998 | 53 |
| 7 | `SE100-G2-S3-C3-ROTATION-RA3-L06-K1-MONTHLY` | 6 | 1 | MONTHLY | 0.500000000 | 0.500000000 | 157 |
| 8 | `SE100-G2-S3-C3-ROTATION-RA3-L06-K1-QUARTERLY` | 6 | 1 | QUARTERLY | 0.500000000 | 0.500000000 | 53 |
| 9 | `SE100-G2-S3-C3-ROTATION-RA3-L06-K2-MONTHLY` | 6 | 2 | MONTHLY | 0.250000000 | 0.500000000 | 157 |
| 10 | `SE100-G2-S3-C3-ROTATION-RA3-L06-K2-QUARTERLY` | 6 | 2 | QUARTERLY | 0.250000000 | 0.500000000 | 53 |
| 11 | `SE100-G2-S3-C3-ROTATION-RA3-L06-K3-MONTHLY` | 6 | 3 | MONTHLY | 0.166666666 | 0.499999998 | 157 |
| 12 | `SE100-G2-S3-C3-ROTATION-RA3-L06-K3-QUARTERLY` | 6 | 3 | QUARTERLY | 0.166666666 | 0.499999998 | 53 |
| 13 | `SE100-G2-S3-C3-ROTATION-RA3-L12-K1-MONTHLY` | 12 | 1 | MONTHLY | 0.500000000 | 0.500000000 | 157 |
| 14 | `SE100-G2-S3-C3-ROTATION-RA3-L12-K1-QUARTERLY` | 12 | 1 | QUARTERLY | 0.500000000 | 0.500000000 | 53 |
| 15 | `SE100-G2-S3-C3-ROTATION-RA3-L12-K2-MONTHLY` | 12 | 2 | MONTHLY | 0.250000000 | 0.500000000 | 157 |
| 16 | `SE100-G2-S3-C3-ROTATION-RA3-L12-K2-QUARTERLY` | 12 | 2 | QUARTERLY | 0.250000000 | 0.500000000 | 53 |
| 17 | `SE100-G2-S3-C3-ROTATION-RA3-L12-K3-MONTHLY` | 12 | 3 | MONTHLY | 0.166666666 | 0.499999998 | 157 |
| 18 | `SE100-G2-S3-C3-ROTATION-RA3-L12-K3-QUARTERLY` | 12 | 3 | QUARTERLY | 0.166666666 | 0.499999998 | 53 |

### 9.1 Multiplicity

| Field | Value |
|---|---|
| Variants this attempt | 18 |
| Runs this attempt | 36 |
| Variants attempt 1 | 18 |
| Runs attempt 1 | 36 |
| Variants attempt 2 | 18 |
| Runs attempt 2 | 36 |
| Cumulative variants this hypothesis family | 54 |
| Cumulative runs this hypothesis family | 108 |

**No correction applied.** No multiplicity correction is applied to the gate thresholds, because the thresholds are constitutional and may not be altered by a stage that would benefit from altering them. The multiplicity is disclosed instead, and it is the reason a development pass is explicitly not evidence of an edge.

**Adaptive design note.** The 54 cumulative variants are not 54 independent tests. Attempt 2's risk architecture was chosen after seeing where Attempt 1 broke; Attempt 3's ladder change and selection rule were chosen after seeing how Attempt 2 behaved. The effective number of researcher degrees of freedom is larger than 54 and grows faster than the variant count, because each attempt conditions on all preceding results. It is not quantified here because any quantification would itself be a choice made after the fact.

**Third attempt note.** A third adaptation on one hypothesis family is the point at which a development PASS carries very little evidential weight on its own. This is stated before the run. See G2A3-CONFLICT-33.

**Statement.** See adaptation_disclosure_verbatim, which is the binding text and must be carried verbatim wherever this attempt's development result is referenced.

## 10. Representative selection rule `SE100-G2-SEL-2`

| Field | Value |
|---|---|
| Id | SE100-G2-SEL-2 |
| Frozen before any variant is run | true |
| Return blind | true |
| Unchanged from attempt 1 | false |
| Unchanged from attempt 2 | false |
| Replaces | The unnamed lowest-turnover rule of SE100-CFG-3103, which selected SE100-G2-S3-C2-ROTATION-RA1-L12-K1-QUARTERLY. |

**Why it changes.** Attempt 2's rule preferred the variant that traded least. On a grid where every variant survived the eligibility screen, 'traded least' selected the quarterly k=1 corner — the parameterisation that by construction takes the fewest decisions and holds the fewest positions. Lowest turnover is a defensible tiebreak among near-equals and a poor primary criterion on a grid with no ties, because it is monotone in a structural property of the axes rather than in anything about the strategy's behaviour. SEL-2 prefers a variant whose immediate neighbours behave like it does, which is a stability criterion rather than a corner-seeking one. Turnover is retained as the tiebreak.

| Order | Criterion | Scope |
|---|---|---|
| 1 | `zero_research_shutdown_events` | across BOTH runs of the variant |
| 2 | `lowest_neighbourhood_instability_score` | The immediate grid neighbours of a variant are the variants reachable by exactly one single-axis step: lookback one position up or down the ordered list [3, 6, 12], k one position up or down the ordered list [1, 2, 3], and the rebalance frequency flipped. Every other axis value is held equal. |
| 3 | `lowest_turnover` | total fill count across both runs |
| 4 | `lexicographic_variant_id` | A total order. Reached only if two variants tie on all criteria above. |

**Scope.** across BOTH runs of the variant

**Eliminates.** any variant with one or more shutdown events in either run

**Unchanged from attempt 2.** `true`

**Definition.** total fill count across both runs

**Role change.** Attempt 2's primary criterion becomes Attempt 3's tiebreak. Its rationale is unchanged and is carried from SE100-CFG-3103: gross notional traded is a partial return proxy and fill count is not.

**Purpose.** A total order. Reached only if two variants tie on all criteria above.

### 10.1 Structural enforcement

**Mechanism.** The scoring function accepts a frozen SelectionInputV2 dataclass whose fields are exactly (variant_id, shutdown_events, fill_count, ladder_descents, lockout_arms, stops_filled). No return, drawdown, profit factor, Sharpe, trade-count or equity figure can reach it, because there is no field to carry one.

**Frozen dataclass.** frozen=True, so a field cannot be reassigned between scoring and selection either.

**Import time assertion.** The module asserts at import that the dataclass's actual field tuple equals the declared SELECTION_V2_FIELD_NAMES, in order. A field added later fails the import rather than silently widening what the selector can see. This is the same mechanism SE100-CFG-3103 required of Attempt 2's SelectionInput, extended to six fields.

**What is still excluded.** Every performance quantity, without exception. What is newly admitted relative to Attempt 2 is three risk-behaviour counters, and they are admitted as dispersions across neighbours rather than as levels. See G2A3-CONFLICT-26, which records that Attempt 2 explicitly excluded two of them and does not pretend the change is continuity.

```
variant_id
shutdown_events
fill_count
ladder_descents
lockout_arms
stops_filled
```

### 10.2 The neighbourhood

**Neighbours.** The immediate grid neighbours of a variant are the variants reachable by exactly one single-axis step: lookback one position up or down the ordered list [3, 6, 12], k one position up or down the ordered list [1, 2, 3], and the rebalance frequency flipped. Every other axis value is held equal.

**Neighbour counts.** 3, 4 or 5. The frequency axis has two values, so it contributes exactly one neighbour to every variant with no edge case. The lookback and k axes have three ordered values each and contribute one neighbour at an end and two in the middle. A variant at an end of both ordered axes has 1+1+1 = 3; at an end of one of them, 1+2+1 = 4; at the middle of both, 2+2+1 = 5. Over the eighteen variants the partition is 8 with three neighbours, 8 with four, and 2 with five.

**Neighbour counts provenance.** The 8/8/2 partition was computed by enumerating the sealed grid, not counted by hand: 2 end values on the lookback axis times 2 end values on the k axis times 2 frequencies is 8 variants at an end of both ordered axes, 1 middle lookback times 1 middle k times 2 frequencies is 2 at the middle of both, and the remaining 8 are at an end of exactly one. A hand count of this partition was wrong on the first pass, which is why the build asserts it.

**Symmetry.** The neighbour relation is symmetric: b is a neighbour of a if and only if a is a neighbour of b. Asserted over all eighteen variants at build time and again in AT-J.

**Neighbour count conflict.** The operating instruction describes this as 'up to 4 neighbours' with corner=2, edge=3, interior=4. That is the count for a two-axis grid and omits the frequency axis, which the same instruction lists as a one-step change. Adding the frequency neighbour to each of the instruction's figures gives exactly 3, 4 and 5. The sealed counts are 3/4/5. See G2A3-CONFLICT-27 in SE100-CFG-3106.

**Quantities.**

- fill_count
- ladder_descents
- lockout_arms
- stops_filled

**Quantity basis.** Each quantity is summed across the variant's two runs (#BASE and #STRESS) before any comparison, so a variant contributes one integer per quantity.

**Per pair dissimilarity.** abs(a - b) / max(abs(a), abs(b), 1)

**Score.** The arithmetic mean of the per-pair dissimilarity over all (neighbour, quantity) pairs: sum over neighbours, sum over the four quantities, divided by 4 * len(neighbours). Lower is preferred.

**Arithmetic.** Computed in Decimal under the sealed ENGINE_CONTEXT and quantized to nine decimal places, ROUND_HALF_EVEN, so the score is reproducible and comparable without float drift. The inputs are integers, so the only inexactness is the division.

**Denominator floor note.** The max(..., 1) term means a quantity that is zero for both a variant and its neighbour contributes 0, reading as perfect stability where in fact nothing fired. The formula is sealed as the instruction specifies it and is not repaired; the per-quantity contributions are reported per variant so a reader can see how much of a low score is agreement and how much is absence. See G2A3-CONFLICT-32 in SE100-CFG-3106.

**Eligibility of neighbours.** Neighbours are structural, not filtered by eligibility. A variant's score uses all of its grid neighbours whether or not those neighbours passed the shutdown screen, because the score measures the smoothness of the parameter region and an ineligible neighbour is part of that region. Only the variant being scored must itself be eligible to be selectable.

The partition below is enumerated from the sealed grid at generation time, not counted by hand, and the neighbour relation is asserted symmetric over all eighteen variants before the table is written.

| Neighbours | Variants | Examples |
|---|---|---|
| 3 | 8 | `SE100-G2-S3-C3-ROTATION-RA3-L03-K1-MONTHLY`, `SE100-G2-S3-C3-ROTATION-RA3-L03-K1-QUARTERLY`, ... |
| 4 | 8 | `SE100-G2-S3-C3-ROTATION-RA3-L03-K2-MONTHLY`, `SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY`, ... |
| 5 | 2 | `SE100-G2-S3-C3-ROTATION-RA3-L06-K2-MONTHLY`, `SE100-G2-S3-C3-ROTATION-RA3-L06-K2-QUARTERLY` |

### 10.3 The two fail routes

| Route | Condition | Verdict |
|---|---|---|
| No eligible variant | If all eighteen variants record at least one research-shutdown event, no variant is eligible and no representative exists. | `FAIL — STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE` |
| Representative fails Gate 3 | If a representative is selected and then fails one or more Gate 3 conditions. | `FAIL — STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE` |

**Attempt closes.** The attempt closes. No Attempt 4 is authorized by this file, and no Attempt 4 may be opened without a further disclosed adaptation and a separate authorization.

**Live possibility note.** This route is materially more likely under RA3 than under RA2, because RA3 removes a rung. See G2A3-CONFLICT-29.

**Same token note.** The same FAIL token is emitted on both fail routes. The routes are distinguished in the decision record's gate conditions and in the report prose, not in the token. Carried from Attempt 1's G2-CONFLICT-11 through Attempt 2's G2A2-CONFLICT-9. See G2A3-CONFLICT-36.

**Runner up not promoted.** If the representative fails, no runner-up is promoted. Promoting one would convert a return-blind selection into a search over eighteen candidates for one that passes.

**Conflict ref.** G2A3-CONFLICT-36

**Retrospective check disclosure.**

- *Statement* — SEL-2 was checked against Attempt 2's frozen recorded statistics before being sealed, to confirm it computes and produces a total order on real data rather than only on fixtures.
- *What the check did not do* — It did not compare the variant SEL-2 would have chosen in Attempt 2 against that variant's return, drawdown or profit factor, and no such comparison informed the rule. The adaptation disclosure states this as 'a retrospective (but not selection-informing) check'.
- *Why disclosed* — A rule tested on the data of a prior attempt is not fully independent of it, however narrow the test. Saying so is cheaper than defending it later.

**No reselection.** The representative is selected once, before any gate condition is evaluated. It is not reselected, re-ranked or substituted for any reason.

## 11. Gate 3 evaluation

| Field | Value |
|---|---|
| Evaluated on | The selected representative variant only, across both of its runs. |
| Conjunctive | All Gate 3 conditions must be satisfied. Constitution section 9. |
| Criteria source | config/generation_2/g2_gate_criteria_ra3.json |
| Thresholds changed from attempt 1 | none |
| Thresholds changed from generation 1 | none |
| Thresholds changed from attempt 2 | none |

**Gate criteria SHA-256 not recorded here.** SE100-CFG-3106 is sealed alongside this file and the two are mutually referential: it names this file as protocol_ref and this file names it as gate_criteria_ref. Recording either digest inside the other would make the pair unwritable. Both are covered by repo_state_id (config/**/*.json is recursive) and both are listed in the Attempt 3 artifact manifest.

### 11.1 The frozen gate text and its companion

The gate text below is the constitution's own, carried verbatim through `config/generation_2/g2_gate_criteria_ra3.json`. The seven conditions that follow are its decomposition; no threshold in either is Attempt 3's to set.

> This gate rejects obviously weak or fitted candidates before sealed evaluation. Pass only if, on development data after base costs: total return is positive; maximum drawdown is no worse than 15%; profit factor is at least 1.10; at least 30 closed trades exist, unless a lower-frequency protocol predeclared a longer evidence requirement before results; performance is not dependent on one trade: removing the single best trade leaves total return above 0%; no single instrument contributes more than 50% of total strategy profit for a multi-instrument strategy; reasonable neighboring parameter values do not reverse the sign of net return. Fail verdict: STRATEGY_REJECTED_IN_DEVELOPMENT.

| Frozen companion field | Value |
|---|---|
| Gate id | 3 |
| Gate name | `development_admissibility` |
| Fail result | `STRATEGY_REJECTED_IN_DEVELOPMENT` |
| Net return positive | true |
| Max drawdown pct | 15 |
| Profit factor min | 1.1 |
| Closed trades min | 30 |
| Best trade removed return positive | true |

**Adaptation disclosure carried.** This file is part of an attempt whose pre-registration was written after BOTH Attempt 1's and Attempt 2's development results were known. The full disclosure text is carried verbatim in SE100-CFG-3105 field adaptation_disclosure_verbatim and in every downstream artifact listed in its adaptation_disclosure_carriage_requirement. It is not restated here in paraphrase, because a paraphrased disclosure is a weakened disclosure. This is the third disclosed adaptation on one hypothesis family; see multiple_comparisons_disclosure in SE100-CFG-3105 and G2A3-CONFLICT-33 below.

### 11.2 Relationship to the three earlier criteria files

**Relationship to generation 1 criteria.**

- *Carried over unchanged* — `S3-C1`, `S3-C2`, `S3-C3`, `S3-C4`, `S3-C6`
- *Redefined for generation 2* — `S3-C5`, `S3-C7`
- *Thresholds changed* — none
- *Note* — This row describes the relationship to Generation 1 and is identical to the rows in SE100-CFG-3102 and SE100-CFG-3104. Attempt 3 changes no threshold either.

**Relationship to attempt 1 criteria.**

- *Thresholds changed* — none
- *Predicates changed* — No relation and no threshold changed. As in Attempt 2, six of the seven predicate strings are character-identical to SE100-CFG-3102's and the seventh differs by one operand name.
- *Measurement basis changed* — `S3-C3`, `S3-C4`, `S3-C5`, `S3-C6`
- *Measurement basis unchanged* — `S3-C1`, `S3-C2`, `S3-C7`
- *Note* — These two lists are reproduced from SE100-CFG-3104 because the evaluator reads them by name to populate the decision record. They describe the change Attempt 2 made against Attempt 1, and Attempt 3 inherits both the change and the description. Attempt 3 makes no further change of measurement basis against Attempt 2; see relationship_to_attempt_2_criteria.

**Relationship to attempt 2 criteria.**

- *Thresholds changed* — none
- *Predicates changed* — none. All seven predicate strings are character-identical to SE100-CFG-3104's.
- *Measurement basis changed* — (empty)
- *Measurement basis unchanged* — `S3-C1`, `S3-C2`, `S3-C3`, `S3-C4`, `S3-C5`, `S3-C6`, `S3-C7`
- *Episode ledger inherited* — The episode ledger of G2A2-CONFLICT-18 is inherited unchanged and is built by the Attempt 2 module stockedge100.backtest.g2_episodes_ra1, which is imported and NOT modified, NOT copied and NOT subclassed. RA3 trims positions for exactly the same two reasons RA2 does — the aggregate throttle and the de-risk ladder — so the conflict that made the ledger necessary applies with undiminished force. Removing the -5% rung reduces how often a trim happens; it does not remove the mechanism, and a ledger that was necessary at a thousand descents is still necessary at one.
- *What actually differs*
  - The two verdict tokens, which are Attempt 3's and are checked against all four tokens belonging to the two closed attempts.
  - The candidate id named in S3-C6 scope_interpretation.applies_to, which is SE100-G2-S3-C3-ROTATION-RA3.
  - The grid named in S3-C7 measurement.neighbour_definition, which is the eighteen-variant Attempt 3 grid.
  - Three prose passages that described RA2's three-rung 5/8/10 ladder and now describe RA3's two-rung 8/10 ladder: S3-CONFLICT-3.attempt_3_note, G2A3-CONFLICT-19 and G2A3-CONFLICT-22 (the successors of Attempt 2's G2A2-CONFLICT-19 and G2A2-CONFLICT-22).
  - Eight new conflict entries, G2A3-CONFLICT-26 through G2A3-CONFLICT-33, recording what is new in this attempt.
- *Why a new file at all* — Because the tokens must differ and a verdict token may never be shared across attempts, and because three of Attempt 2's prose fields state a ladder geometry Attempt 3 does not run. Editing SE100-CFG-3104 in place was not available: Attempt 2 is closed and its file is read-only, its digest is pinned by its own governance record, and its verdict of FAIL stands permanently against the figures that file describes.

### 11.3 The seven conditions

| Id | Required (verbatim) | Status |
|---|---|---|
| `S3-C1` | total return is positive | unchanged from Attempt 2 in threshold, predicate and measurement basis |
| `S3-C2` | maximum drawdown is no worse than 15% | unchanged from Attempt 2 in threshold, predicate and measurement basis |
| `S3-C3` | profit factor is at least 1.10 | unchanged from Attempt 2 in threshold, predicate and measurement basis; the episode ledger of G2A2-CONFLICT-18 is inherited |
| `S3-C4` | at least 30 closed trades exist, unless a lower-frequency protocol predeclared a longer evidence requirement before results | unchanged from Attempt 2 in threshold, predicate and measurement basis; the episode ledger of G2A2-CONFLICT-18 is inherited |
| `S3-C5` | performance is not dependent on one trade: removing the single best trade leaves total return above 0% | unchanged from Attempt 2: REDEFINED for Generation 2 by G2-CONFLICT-6, carried with the episode-ledger P&L of G2A2-CONFLICT-18 and the qualification of G2A2-CONFLICT-23 |
| `S3-C6` | no single instrument contributes more than 50% of total strategy profit for a multi-instrument strategy | unchanged from Attempt 2 in threshold, predicate and measurement basis; the episode ledger of G2A2-CONFLICT-18 is inherited |
| `S3-C7` | reasonable neighboring parameter values do not reverse the sign of net return | unchanged from Attempt 2: REDEFINED for Generation 2 by G2-CONFLICT-7, qualified by G2A3-CONFLICT-22, and now with a second consumer per G2A3-CONFLICT-27 |

Each condition's remaining fields follow. They are reproduced from `config/generation_2/g2_gate_criteria_ra3.json` in full rather than summarised, so a reader of this document alone can reconstruct the gate arithmetic; the criteria file remains the source of record and the sealer asserts the two agree. The field set differs between conditions — every key each condition actually carries is rendered, so a field cannot be dropped by a renderer that expected a fixed shape.

**`S3-C1`.**

- *Measurement* — total_return over the representative's base run, from stockedge100.backtest.metrics.total_return on the engine equity curve: final equity / starting equity - 1, exact Decimal. Under G2A2-CONFLICT-25 the same measurement is also required on the stress run.
- *Predicate* — total_return > 0
- *Costs* — base cost model, all costs already charged inside the equity curve
- *Not evaluable treatment* — An equity curve with fewer than two points is NOT_EVALUABLE and fails.
- *Attempt 3 note* — Unaffected by G2A2-CONFLICT-18: the equity curve reflects every cash movement including partial sales. This is the condition Attempt 2's representative failed by the widest margin in relative terms, at +0.42 percent base and -0.08 percent stress over thirteen years. RA3 can only increase exposure relative to RA2 — it removes a throttle rung and adds nothing — so an improvement here is a predictable consequence of the architecture change and is NOT evidence about the rotation signal. A FAIL here under RA3 would say the signal is weak independently of how hard the ladder throttled it, which is a stronger statement than Attempt 2's evidence supported.

**`S3-C2`.**

- *Measurement* — max_drawdown from stockedge100.backtest.metrics: the largest peak-to-trough decline of the daily closing equity curve, expressed as a non-negative fraction of the running peak. Session-close granularity; the project holds no intraday data and none is imputed.
- *Predicate* — max_drawdown <= 0.15
- *Boundary* — Inclusive. 'No worse than 15%' admits exactly 15%.
- *Not evaluable treatment* — An equity curve with fewer than two points is NOT_EVALUABLE and fails, on the same guard as S3-C1. Otherwise this condition is always evaluable: a run that never declined has a maximum drawdown of exactly zero, which is a measured value and not absent evidence.
- *Interaction* — See S3-CONFLICT-3 and G2A3-CONFLICT-19. A MET verdict here is produced by three overlapping devices and is not independent evidence about the hypothesis. A NOT_MET verdict, by contrast, is informative: under RA3 it means the two remaining rungs were not enough where the three-rung ladder was, which is direct evidence that the removed rung was load-bearing.

**`S3-C3`.**

- *Measurement* — Gross profit divided by gross loss over CLOSED EPISODES, where an episode's P&L is exit_cash plus dividends received while held minus entry_cash, with both legs' costs already inside those cash figures, and exit_cash is summed across every sale leg of the episode rather than only the leg that closed it. On any episode with exactly one sale leg this is numerically identical to stockedge100.backtest.metrics.profit_factor over Portfolio.trades.
- *Predicate* — profit_factor >= 1.10
- *Undefined cases*
  - *No closed episodes* — profit_factor is null. Recorded as NOT_EVALUABLE and the condition FAILS. It is not passed by default and not marked not-applicable.
  - *No losing episodes* — profit_factor is null because gross loss is zero. If closed episodes exist and gross profit is positive, this is recorded as UNDEFINED_NO_LOSSES_TREATED_AS_MET, with the raw null preserved in the evidence rather than replaced by a number. The sealed cost model requires profit factor undefined when there are no losses to be reported as null, never as infinity.
- *Attempt 3 note* — The frozen metrics function is not modified and is still called for the reconciliation figure. Both numbers are reported: profit factor over the episode ledger, which gates, and profit factor over Portfolio.trades, which does not. Where they differ, the difference is the trimmed proceeds the frozen recorder drops. Under RA3 that difference is expected to be SMALLER than Attempt 2's, because one of the two trimming mechanisms fires less often; the size of the reduction is direct evidence of how much of Attempt 2's trimming the removed rung caused, and is reported for that reason.

**`S3-C4`.**

- *Measurement* — Count of closed episodes in the representative's base run. An episode is closed when a sale returns the position to zero. A position still open on the final session is not closed and is not counted; at k = 3 up to three positions may be open on the final session and none of them counts. A position that has been trimmed but not closed is still open and is not counted.
- *Predicate* — closed_episodes >= 30
- *Not evaluable treatment* — This condition is always evaluable. A count is defined for every run, and a run with no closed episodes has a count of zero, which is a measured value that fails the predicate rather than absent evidence.
- *Exception invoked* — `false`
- *Exception note* — No Attempt 3 variant invokes the lower-frequency exception. The exception permits a LONGER evidence requirement, not a smaller trade count, so it could not lower this floor in any case. Recorded explicitly and before results so that a quarterly variant cannot be argued into it once its count is known. See G2A2-CONFLICT-20 for the two opposing effects the risk architecture has on this count.
- *Counting identity* — A closed episode and a closed Portfolio.Trade are the same event: both are the moment a position returns to zero. The episode ledger changes what P&L is attributed to that event, not when the event occurs, so this count is identical to the count over Portfolio.trades. It is asserted equal at evaluation time rather than assumed.

**`S3-C5`.**

- *Measurement*
  - *Basis* — Closed episodes only. Each episode's multiple is taken against the equity that actually existed when that episode was entered, which is well defined whether or not other positions were open at the time and whether or not the position was later trimmed.
  - *Procedure*
    - For the i-th closed episode, E_entry[i] = account equity at the CLOSE of the session immediately preceding that episode's entry fill, read from the engine's own equity curve. If the entry fill is on the first session of the run, E_entry[i] = starting equity = 100.00.
    - Per-episode equity multiple r[i] = 1 + pnl[i] / E_entry[i], with pnl[i] the episode P&L defined in S3-C3.
    - Reconstructed total return = product of all r[i], minus 1.
    - Best-episode-removed return = product of r[i] for i not equal to j, minus 1.
  - *Which trade is removed* — Two removals are computed and BOTH must leave a positive return. j1 is the episode with the largest equity multiple r[i]. j2 is the episode with the largest absolute P&L pnl[i]. These usually coincide and need not. Requiring both is the stricter reading, carried over unchanged from Generation 1, Attempt 1 and Attempt 2, and it is fixed here so the stricter or looser reading cannot be chosen after seeing which one the representative survives.
  - *Tie handling* — If several episodes tie on the maximum, the earliest by index is removed. Carried over from Generation 1's max(..., key=(value, -index)) tiebreak so that the removal is deterministic.
  - *Relation to headline return* — The reconstruction is NOT expected to equal the equity-curve total return, and no attempt is made to make it equal. Concurrent positions mean the products do not telescope; dividends credited outside an episode and positions still open on the final session also contribute; and under RA3, as under RA2, the exposure scalar changes within an episode's life. Both figures are reported side by side, together with their difference, and the condition is evaluated on the reconstruction.
  - *Disclosure requirement* — The Attempt 3 report states the reconstructed return, the equity-curve return, and the gap between them explicitly. A material gap is a limitation to disclose, not a defect to reconcile.
- *Predicate* — best_trade_removed_return > 0 for BOTH removals
- *Not evaluable treatment* — Fewer than two closed episodes is NOT_EVALUABLE and fails; a result that is one episode is the exact dependence this condition tests for.
- *Implementation* — The Attempt 3 gate module, which imports Attempt 2's condition_5_ra1 unmodified rather than restating it. Generation 1's stockedge100.strategies.gate.condition_5 and Attempt 1's stockedge100.strategies.g2_gate are not called and neither is modified.

**`S3-C6`.**

- *Measurement* — For each instrument, contribution = sum of pnl over that instrument's closed EPISODES, divided by the sum of pnl over all closed episodes. Evaluated only when total closed-episode P&L is strictly positive; when total P&L is zero or negative the share is not a meaningful proportion and the case is recorded as NOT_EVALUABLE — which is moot, because S3-C1 has already failed such a candidate.
- *Predicate* — max instrument contribution <= 0.50
- *Why the basis matters here* — This is the condition G2A2-CONFLICT-18 distorts most. Attribution is a ratio of one symbol's P&L to the total, so dropping a trim's proceeds corrupts both the numerator and the denominator. Computing the ratio over episodes is what makes the answer a fact about the strategy rather than about which positions happened to be trimmed.
- *Scope interpretation*
  - *Applies to* — SE100-G2-S3-C3-ROTATION-RA3, unconditionally.
  - *Rationale* — Applicability is decided by the DECLARED universe, never by the realized symbol count. A candidate that declares one instrument cannot have a concentration problem the condition could detect, so it is NOT_APPLICABLE_BY_CONDITION_TEXT. A candidate that declares many and then trades one is exactly the case this condition exists to catch, so it remains applicable and fails.
  - *Why it always applies* — Attempt 3's declared universe is the full 34-member frozen list at every rebalance, so the strategy is multi-instrument by declaration regardless of how many symbols it turns out to trade. Deciding applicability from the realized count would let a candidate that collapsed onto one symbol escape the condition precisely when it is most informative.
  - *Single instrument treatment* — Not reachable in Attempt 3. Retained in the schema so this file remains comparable to SE100-CFG-3104, SE100-CFG-3102 and SE100-CFG-3002.
  - *Attempt 3 significance* — This is the condition that tests the claim in the charter's section 2, and it is one of the four Attempt 2's representative failed: at k = 1 quarterly the representative concentrated its profit in a single instrument. RA3 changes nothing about position count — k is still a grid axis, not a risk constant — so if SEL-2 again selects a k = 1 variant this condition is at high risk of failing again for the same structural reason. That is a property of the selection outcome and not of the risk architecture, and the report must attribute it correctly if it happens.

**`S3-C7`.**

- *Measurement*
  - *Neighbour definition* — Every variant in the eighteen-variant Attempt 3 grid that differs from the representative in exactly one axis by exactly one step.
  - *Axis orderings*
    - *Lookback months* — `3`, `6`, `12`
    - *Top k* — `1`, `2`, `3`
    - *Rebalance frequency* — `MONTHLY`, `QUARTERLY`
  - *One step note* — A step is to an adjacent value in the ordering above. From lookback 3 the only neighbour is 6, not 12. From k = 2 both 1 and 3 are neighbours. The frequency axis has two values, so its single neighbour is always the other one.
  - *Neighbour count* — 3 when the representative is at an endpoint of both the lookback and the k axis; 5 when it is interior on both; 4 otherwise. The count is a function of the representative's grid position and is not chosen.
  - *Neighbour count conflict* — The Attempt 3 operating instruction states 2, 3 and 4 for these three cases. See G2A3-CONFLICT-27: those counts omit the frequency axis, which contributes exactly one neighbour to every variant. The sealed counts govern.
  - *Shared with selection* — SE100-G2-SEL-2 averages its stability score over this same neighbour set, computed by this same rule from these same axis_orderings. One implementation serves both, so the neighbourhood the selection rule reasons about and the neighbourhood this condition tests cannot diverge.
  - *No new runs* — Every neighbour is already a declared member of the Attempt 3 grid and is already run under the same window, the same base cost model, the same frozen risk architecture and the research shutdown enforced. This condition creates no new parameterisation and no new run.
  - *Risk constants have no neighbours* — The five RA3 constants are identical across all eighteen variants and are not gridded, so no neighbour differs from the representative in any risk parameter. See G2A3-CONFLICT-22: this condition is silent about the robustness of the risk architecture and a MET verdict must not be read as covering it.
  - *What is read* — Each neighbour's base-run equity-curve total return and its sign. Nothing else about a neighbour enters this condition.
- *Predicate* — sign(neighbour total_return) == sign(representative total_return) for EVERY neighbour, where sign is positive, negative, or zero and zero matches nothing
- *Selection prohibition* — Neighbour runs are read for the sign of net return and nothing else. No neighbour is ever promoted to representative, and the representative's parameterisation is never revised because a neighbour did better. Doing so would be a material change under constitution section 11 and would create a new candidate restarting at Gate 3. It would also destroy the return-blind property of the selection rule, since the promotion would be driven by a return. This prohibition binds with additional force in Attempt 3, because SEL-2 already reads the neighbourhood for its own purposes and a reader could mistake that for licence to read returns there. It is not: SEL-2's inputs are four counters, structurally enforced, and the returns this condition reads are never available to it.
- *Not evaluable treatment* — A neighbour that fails to run is NOT_RUN, which is not a pass; the condition fails.
- *Implementation* — The Attempt 3 gate module. Generation 1's condition_7 raises ConfigViolation on a neighbour count other than four and is not called; it is not modified. Attempt 1's g2_gate and Attempt 2's g2_gate_ra1.condition_7_ra1 are not called for Attempt 3, because both resolve the neighbour set against their own attempt's grid, and neither is modified.

### 11.4 Verdict tokens

| Outcome | Token |
|---|---|
| Admitted | `STAGE_3_G2_ATTEMPT_3_STRATEGY_ADMITTED_IN_DEVELOPMENT` |
| Rejected | `STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE` |

**Pass condition.** The representative selected by the frozen return-blind rule SE100-G2-SEL-2 in SE100-CFG-3105 satisfies EVERY hard condition of Gate 3, on its base-cost development run and — under the restrictive reading of G2A2-CONFLICT-25 — on its stressed-cost run for S3-C1 through S3-C6.

**Fail condition.** Either no representative exists, because every one of the eighteen variants recorded at least one research-shutdown event, or a representative exists and does not satisfy every hard condition.

**Conjunctive note.** Constitution section 9: gates are conjunctive; every hard condition must pass, and NOT_RUN, UNKNOWN, NOT_EVALUABLE, or missing evidence is not a pass. Conjunction applies WITHIN a candidate. Attempt 3 declares one live candidate, so the cross-candidate disjunction is over a set of size one — see G2-CONFLICT-15 and G2A3-CONFLICT-24.

**Constitutional fail result equivalent.** STRATEGY_REJECTED_IN_DEVELOPMENT

**Token naming note.** See G2A3-CONFLICT-21. The fail token names the absence of an admissible candidate; the constitution's names the rejection of one. They denote the same stage outcome and both are recorded in the decision package. The Attempt 3 operating instruction named no token and required that the token be derived from this file, which is what has been done.

**Prior attempt tokens are not available here.** STAGE_3_G2_STRATEGY_ADMITTED_IN_DEVELOPMENT and STAGE_3_G2_NO_CANDIDATE belong to Attempt 1. STAGE_3_G2_ATTEMPT_2_STRATEGY_ADMITTED_IN_DEVELOPMENT and STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE belong to Attempt 2. Both attempts are closed. No Attempt 3 artifact may emit any of those four, and the Attempt 3 evaluator and package builder both assert that the verdict token written is one of the two sealed above and is none of the four.

**Other tokens available.** BLOCKED_BY_DATA, BLOCKED_BY_INFRASTRUCTURE, INSUFFICIENT_EVIDENCE, INVALIDATED, NOT_RUN, per constitution section 10. Missing evidence may never be converted to PASS or NOT_APPLICABLE for convenience.

**Fail is a deliverable.** FAIL — STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE is a legitimate and fully anticipated outcome. It is recorded, kept on disk, and does not license a nineteenth variant, a re-run with a different grid, a loosened risk constant, a third selection rule, or a promotion of the runner-up. Per SE100-CFG-3105 it closes the attempt: there is no Attempt 4 without a further disclosed adaptation authorised in a later session, and G2A3-CONFLICT-33 records what the cumulative multiplicity of a fourth would be.

**Neither token is a stage verdict for any other stage.** These two tokens belong to Generation 2 Stage 3 Attempt 3 alone. No artifact at any other stage, and no artifact of any other attempt, may emit either.

### 11.5 Evaluation integrity rules

1. Conditions are evaluated by a program that reads the engine's own outputs. No condition verdict is typed by hand into a report.
2. Every condition verdict is one of MET, NOT_MET, NOT_EVALUABLE, or NOT_APPLICABLE_BY_CONDITION_TEXT. There is no fifth value and no borderline value.
3. The candidate's admissibility is the conjunction of its applicable conditions. NOT_EVALUABLE never counts as MET.
4. Thresholds are compared as exact Decimals. No comparison is made in floating point, and no result is rounded before comparison.
5. The evidence file records the measured value alongside every verdict, so a reader can recompute the comparison without rerunning the engine.
6. The representative is selected before any condition is evaluated, by the return-blind rule SE100-G2-SEL-2 in SE100-CFG-3105. Condition evaluation cannot feed back into selection, because selection has already happened and is not repeated.
7. If the representative fails any condition, the stage fails. No other variant is evaluated against the gate.
8. The episode ledger is reconciled against the frozen Portfolio.trades on every run, not only on the representative's. For every episode with exactly one sale leg, entry_cash, exit_cash, dividends and pnl are asserted equal to the corresponding Trade, and the closed episode count is asserted equal to the closed trade count. A failure of either assertion halts evaluation rather than being reported as a discrepancy.
9. That reconciliation must not be allowed to pass vacuously. The evaluator asserts that the number of single-leg episodes compared is greater than zero before asserting that they agree, and reports the compared count alongside the mismatch count.
10. The gate threshold seal check runs before any condition is evaluated: the five frozen thresholds, the S3-C6 predicate text and the S3-C4 exception flag are asserted unchanged against the constitution. A file that has drifted from the seal cannot be used to evaluate anything, whatever its conditions say.
11. The verdict token emitted is asserted to be one of the two sealed in verdict_token_derivation and to be none of the four belonging to Attempts 1 and 2. Those four are read from the two closed attempts' own sealed criteria files, whose digests are recomputed against the pins above, rather than being restated here as literals: two files agreeing is evidence, one file quoting itself is not.
12. The selection score is computed by a module whose only input is a frozen dataclass carrying (variant_id, shutdown_events, fill_count, ladder_descents, lockout_arms, stops_filled) and nothing else, asserted at import time. A field added later — including a return, a drawdown or a profit factor — fails the import rather than silently widening what the selector can see.

### 11.6 Reported for every variant, gating nothing

- net return, both runs
- maximum drawdown, both runs
- profit factor, both runs
- closed trade count, both runs
- best-trade-removed return, both runs
- research-shutdown event count and the session of each, both runs
- total fill count, both runs
- de-risk ladder activations (downward transitions), both runs
- de-risk ladder upward transitions and deepest band reached, both runs
- sessions spent in each ladder band, both runs
- re-entry lockout arms and sessions on which a recovery was blocked by it, both runs
- stop exits and the realized loss at each, both runs
- throttle legs issued and throttle legs skipped below minimum notional, both runs
- maximum observed gross exposure fraction, both runs
- minimum and mean combined risk scalar, and sessions on which it was below 1, both runs
- ranking digest, both runs
- The SE100-G2-SEL-2 stability score, its four per-quantity components, and the identity and score of every neighbour used to compute it.
- The Attempt 2 counterpart of each ladder, lockout and stop statistic, so the required comparison is on the same page as the figure it compares.

`config/generation_2/g2_gate_criteria_ra3.json` carries its own list of 10 non-gating quantities against this document's 18. The two lists were written independently and share **0** entries by exact string — each file names the same measurements in its own wording. That is not a disagreement to reconcile: neither list gates anything, no condition in section 11.3 reads from either, and the sealer asserts only that both are non-empty. The criteria file's 10 entries are reproduced below so that neither document has to be read through the other.

- The representative's stress run, in full. Under G2A2-CONFLICT-25's restrictive reading S3-C1 through S3-C6 are additionally required to be satisfied on it; the permissive base-only reading is also reported, and the two readings are stated separately so a reader can see which one the verdict rests on.
- All eighteen variants' return, maximum drawdown, profit factor, closed episode count, and shutdown event count, for both runs. Descriptive record only.
- The RA3 risk-architecture counters, for all eighteen variants and both runs: de-risk ladder activations by band, re-entry lockout triggers, aggregate-throttle trim events, per-position stop exits, the combined sizing scalar's minimum and mean, and the maximum gross exposure fraction observed at any session. Four of these — fill count, ladder descent count, lockout arm count and stop fill count — ARE inputs to SE100-G2-SEL-2's stability score and are therefore selection inputs as well as descriptive evidence. None of them gates anything, and no threshold anywhere in this file is expressed in terms of them.
- The comparison of every RA3 ladder statistic against Attempt 2's corresponding figure, required by the operating instruction, which requires in particular that at least the ladder-engagement statistics be shown to differ. Descriptive; it gates nothing.
- The full SE100-G2-SEL-2 computation for every eligible variant: the four raw counters, each neighbour's counters, the per-quantity dissimilarities, the per-neighbour averages and the final score, together with the scores of the selected variant's own neighbours. Required by the operating instruction to be traced to the actual computation rather than asserted.
- The reconciliation between the episode ledger and Portfolio.trades: episode count, trade count, the per-symbol P&L difference, and the total trimmed proceeds the frozen recorder attributes to no trade. Descriptive, and the direct evidence for G2A2-CONFLICT-18.
- CAGR, annualised volatility, Sharpe ratio at a 0.00% risk-free rate, exposure fraction, win rate, average win, average loss, longest flat streak, distinct symbols traded, and per-symbol contribution.
- SPY total return and SPY tradable buy-and-hold over the representative's own window, with the research shutdown both enforced and disabled, the latter explicitly labelled a benchmark reference account; the cash benchmark at 0.00% annual; and the do-nothing benchmark.
- The comparison of Attempt 3 shutdown-trigger dates, if any, against Attempt 1's and Attempt 2's. Descriptive; it gates nothing and cannot change a condition verdict.
- Constitution section 4 requires better risk-adjusted performance than cash for a strategy to pass overall, and beating SPY is not mandatory where drawdown is materially reduced. Neither is among the seven hard conditions of Gate 3, so neither gates this stage.

## 12. Structural consequences, declared before running

**SC-1.** A quarterly k=1 variant has 53 scheduled rebalances over the run and can therefore close at most 52 positions by signal exit. Gate 3 requires at least 30 closed trades.

- *Attempt 2 amendment* — In Attempt 2 the stop and the throttle can also close or reduce a position, so the closed-trade count is no longer bounded by the rebalance count. The direction of the change is upward and it is the risk architecture, not the signal, that produces the additional trades. A representative that clears the 30-trade condition mainly on stop exits has cleared it on evidence about its risk controls.
- *Risk* — Low turnover remains the failure mode for quarterly k=1; it is now less likely to bind and the reason it is less likely is disclosed.
- *Attempt 3 amendment* — Unchanged in kind from Attempt 2. The stop and the throttle still close positions, so the closed-trade count is still not bounded by the rebalance count. RA3 throttles less, so fewer of the additional trades come from the ladder and more of the exposure is left in place; the direction of the effect on trade count is not predictable and is measured.

**SC-2.** Starting equity is $100.00 and the sealed minimum order notional is $1.00. At k=3 and a 50% aggregate ceiling the per-position budget is about $16.67, sixteen times the minimum.

- *Attempt 2 amendment* — This margin is thinner than Attempt 1's, where the k=3 budget was about $31.67. With the combined risk scalar at its floor of 0.25 * (a volatility scalar that can go lower still), a k=3 entry budget can approach the minimum notional. Entries rejected as MIN_NOTIONAL or ZERO_QUANTITY are counted and reported per variant rather than treated as absent decisions.
- *Throttle interaction* — A throttle trim on a small position is the case most likely to fall below the minimum notional and be skipped. See G2A2-CONFLICT-17.
- *Attempt 3 amendment* — The margin is wider than Attempt 2's at shallow drawdowns, because the combined scalar is 1 rather than 0.75 across [0.05, 0.08), and identical to Attempt 2's at 0.08 and beyond. MIN_NOTIONAL and ZERO_QUANTITY rejections are still counted and reported.

**SC-3.** Attempt 1's k=1 half-cash bias is removed. All three k values now target the same 50% gross exposure, so the k axis is no longer confounded with exposure and the zero-shutdown screen is no longer structurally easier for k=1.

- *See* — position_sizing.attempt_1_k1_half_cash_bias_neutralised

**SC-4.** The continuous throttle adds SELL fills that Attempt 1 could not produce, and total fill count is the representative-selection tiebreak.

- *Consequence* — The tiebreak now partly measures how often the risk architecture intervened - a variant whose exposure drifted above the ceiling more often will have a higher fill count and lose the tiebreak to one that drifted less. That is a defensible ordering (less intervention is less turnover is less cost) but it is not the same quantity Attempt 1's tiebreak measured, and the two attempts' turnover figures are not comparable.
- *Not corrected* — The rule is not changed to exclude throttle legs. It was frozen before Attempt 1 ran and adjusting it now, after reasoning about how it might behave, would be exactly the researcher degree of freedom this document exists to constrain.
- *Attempt 3 amendment* — Turnover is no longer the primary selection criterion, so the objection SC-4 raised against it — that it partly measures how often the risk architecture intervened — now bites only on the tiebreak. It is not thereby resolved: fill_count is also one of SEL-2's four stability quantities, where the same objection applies to its dispersion rather than its level. See G2A3-CONFLICT-26.

**SC-5.** The 5% minimum cash buffer of the sealed cost model can never bind at a 50% aggregate exposure ceiling, because cash is at least 50% of equity at all times.

- *Consequence* — The CASH_FLOOR clamp is present, enforced and never the binding clamp. Reported as such rather than removed.
- *Conflict ref* — G2A2-CONFLICT-12

**SC-6.** The risk architecture reduces exposure and can only reduce it. Every one of RA3-1, RA3-2, RA3-4 and RA3-5 scales sizing down or holds it, and RA3-3 exits.

- *Consequence* — Attempt 2's expected gross return is lower than Attempt 1's would have been on the same signal, mechanically, before any question of whether the drawdown protection is worth it. Gate 3's first condition is that net return is positive, and halving exposure roughly halves the return while the fixed costs of trading do not halve. A FAIL on net return would be a predictable consequence of the architecture and not a new fact about the signal.
- *Why declared now* — So that a FAIL on S3-C1 cannot be presented afterwards as a surprising discovery, and so that a PASS cannot be presented as evidence the architecture is free.
- *Attempt 3 amendment* — RA3 reduces exposure strictly less than RA2 did, and never more. At every session the RA3 combined scalar is greater than or equal to the RA2 scalar for the same drawdown, with equality outside [0.05, 0.08). Mechanically this raises both the expected return and the expected drawdown relative to Attempt 2. A FAIL on net return remains a predictable consequence of an architecture that halves exposure, and a PASS on net return that arrives together with a materially larger drawdown is the architecture being paid for, not the signal being better.

**SC-7.** SE100-G2-SEL-2 scores a variant using four quantities the risk architecture produces: ladder descents, lockout arms, stop fills and total fills. On a grid where the architecture rarely engages, three of the four are small integers and the score is dominated by fill_count.

- *Consequence* — If RA3 turns out to engage rarely, SEL-2 degenerates toward a fill-count dispersion rule and is closer to Attempt 2's turnover rule than its description suggests. The per-quantity components are reported so this is visible in the evidence rather than inferred.
- *Not corrected* — The rule is not reweighted to compensate. It is sealed before the run and the degenerate case is declared before the run.

**SC-8.** RA3 holds full sizing across the whole of [0, 0.08) drawdown, where RA2 throttled to 75 percent from 0.05.

- *Consequence* — Every drawdown episode that reached 5 percent but not 8 percent — which on thirteen years of equity-index history is the common case — is now traversed at full sizing. This is the intended effect. It also means the maximum drawdown condition S3-C2 is under more pressure than in Attempt 2, and the research shutdown is closer than it was.
- *Why declared now* — So that a larger drawdown under RA3 is read as the declared cost of the change and not as a defect, and so that a S3-C2 failure cannot be presented afterwards as unforeseen.

## 13. Contamination measurement

> No .py file under src/stockedge100 or tests contains the string SE100-G2-S3-C3-ROTATION-RA3 at seal time.

**Predicate type.** `CONTENT_BASED`

**Why not path based.** Attempt 1's predicate was path-based: it refused to seal if any module basename under strategies/ or backtest/ contained 'g2_'. That predicate was correct when strategies/ held no Generation 2 code and is now vacuously false - Attempt 1's own six modules live there and are supposed to. A path test would either refuse to seal forever or have to be loosened until it tested nothing. The honest form is content-based: this attempt's candidate id appears nowhere yet.

**Paired immutability check.** Every module listed in prior_attempt_modules_immutable is re-hashed at seal time and must equal the digest recorded for it. The list is now seventeen modules, not Attempt 2's nine: Attempt 1's nine plus Attempt 2's own eight, which became immutable the moment Attempt 2 closed. A content-based predicate alone would pass while a prior attempt's module was being quietly rewritten; the pair does not.

**Sealer indirection note.** The sealing program is itself a .py file under src/stockedge100 and would falsify the predicate if it hard-coded the candidate id as a literal. It does not: it loads strategy_id from this file at run time, so the predicate above is literally true rather than true-with-a-named-exception. That is disclosed here rather than left to be discovered, because a predicate satisfied by an indirection the reader cannot see is worth no more than one that is simply false. The indirection is also the correct design independently of the predicate - this file is the single source of the id, and a sealer that restated it could disagree with it. Attempt 1 took the other route and named its permitted sealing programs explicitly; either is honest, but only one of them stays true when a second sealer is added.

**Conflict ref.** G2A3-CONFLICT-34

**Supersedes in scope.** G2A2-CONFLICT-3, which declared the same predicate over nine modules and is not edited.

| Path | Sealed by |
|---|---|
| `src/stockedge100/strategies/g2_rotation.py` | Attempt 1 |
| `src/stockedge100/strategies/g2_gate.py` | Attempt 1 |
| `src/stockedge100/strategies/g2_runner.py` | Attempt 1 |
| `src/stockedge100/strategies/g2_window_guard.py` | Attempt 1 |
| `src/stockedge100/backtest/g2_engine.py` | Attempt 1 |
| `src/stockedge100/backtest/g2_costs.py` | Attempt 1 |
| `src/stockedge100/reporting/g2_rotation_preregistration.py` | Attempt 1 |
| `src/stockedge100/reporting/g2_stage3_evidence.py` | Attempt 1 |
| `src/stockedge100/reporting/g2_stage3_package.py` | Attempt 1 |
| `src/stockedge100/strategies/g2_rotation_ra1.py` | Attempt 2 |
| `src/stockedge100/strategies/g2_gate_ra1.py` | Attempt 2 |
| `src/stockedge100/strategies/g2_runner_ra1.py` | Attempt 2 |
| `src/stockedge100/backtest/g2_engine_ra1.py` | Attempt 2 |
| `src/stockedge100/backtest/g2_episodes_ra1.py` | Attempt 2 |
| `src/stockedge100/reporting/g2_rotation_ra1_preregistration.py` | Attempt 2 |
| `src/stockedge100/reporting/g2_stage3_attempt2_evidence.py` | Attempt 2 |
| `src/stockedge100/reporting/g2_stage3_attempt2_package.py` | Attempt 2 |

**Count.** 17

**Attempt 1 list source.** SE100-CFG-3103.attempt_1_modules_immutable.modules, copied unchanged.

**Attempt 2 list source.** The eight Generation 2 modules created by Attempt 2, enumerated by listing src/stockedge100/{strategies,backtest,reporting} and subtracting Attempt 1's nine and the Stage 1 module g2_partition_lock.py, which belongs to neither attempt.

**G2 partition lock excluded.** src/stockedge100/reporting/g2_partition_lock.py is a Generation 2 STAGE 1 module. It is immutable for the ordinary reason that every sealed module is, and it is covered by repo_state_id, but it is not a Stage 3 attempt module and is not listed here.

**Digests recorded by.** governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json at seal time

**Digests not recorded here.** This file is a config/ artifact covered by repo_state_id. The measured digests belong in the sealed governance JSON and the runs/ record, not here, so that this file does not have to be rewritten to record a measurement.

## 14. Windows referenced, and the two mandated disclosures

| Span | State | Note |
|---|---|---|
| 1993-01-29 — 2021-07-31 | `DEVELOPMENT` | the only window this attempt reads |
| 2021-08-01 — 2024-07-31 | `LOCKED` | Generation 2 validation window. Not read by this attempt. |
| 2024-08-01 — 2026-07-31 | `SPENT_AND_PROHIBITED` | Generation 1's holdout. Sealed and off-limits regardless of generation. |
| 2026-08-01 — 2028-07-31 | `SEALED` | Generation 2's holdout. Never to be read, by any code, at any stage, before that period exists in real calendar time. |

`config/generation_2/g2_gate_criteria_ra3.json` carries the same windows independently. Its development window was compared against the one above at generation time and agrees. Its holdout and validation states:

**Authorized.**

- development

**Validation window state.** LOCKED

**Generation 1 holdout state.** SPENT_AND_PROHIBITED

**Holdout window state.** SEALED

**Enforcement.** ResearchWindow raises WindowViolation on any session outside the development window, MarketView raises LookAheadError on any read past the decision session, and stockedge100.strategies.g2_window_guard adds the three Generation 2 checks sealed in STAGE_1_G2_PARTITION_LOCK.md section 4. Attempt 3 reuses that guard unmodified, exactly as Attempt 2 did, rather than re-deriving its bounds. All are structural; none depends on a strategy behaving well.

**Disclosed limitation reference.** Any Generation 2 report that references the validation window reproduces the disclosure text of STAGE_1_G2_PARTITION_LOCK.md section 2 verbatim. This stage does not read the validation window at all.

**Generation 1 holdout.** 2024-08-01 to 2026-07-31. Spent by Generation 1 and prohibited. Never read by this stage or any code it runs.

**Generation 2 holdout.** 2026-08-01 to 2028-07-31. Never read, by this stage or any code it runs, and not readable before that period exists in real calendar time.

### 14.1 The adaptation disclosure

Carried verbatim, byte for byte, into every artifact listed below. The sealer refuses to seal if any of them disagrees with this text.

> This pre-registration was designed after both Attempt 1 and Attempt 2's development results were known. Attempt 1 (no risk architecture) failed via research-shutdown on all 18 variants, clustered around the 2008 financial crisis. Attempt 2 (RA2 risk architecture) survived every variant without a shutdown, but its representative — selected by a rule blind to return — earned approximately 0.4% over thirteen years, indicating the risk architecture suppressed ordinary-market returns as well as crisis losses. Attempt 3 makes two disclosed, evidence-informed changes: (1) a new representative-selection rule (SE100-G2-SEL-2) that screens for neighborhood stability across non-return risk-behavior statistics rather than raw turnover, and (2) a revised risk architecture (RA3) that removes a −5%-drawdown de-risk tier RA2 had added beyond Generation 1's own original architecture, on the reasoning that a 5%-from-peak dip is common in ordinary markets and is a plausible cause of RA2's near-constant throttling. Both changes were selected using only non-return diagnostics already on record — RA2's ladder-activation and combined-scalar statistics, and a retrospective (but not selection-informing) check of SEL-2 against Attempt 2's frozen data. No return figure from any prior attempt informed either change. This is nonetheless a third disclosed adaptation on the same hypothesis family, and cumulative multiplicity across all three attempts must be carried forward in any final assessment of this family.

- `governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md`
- `governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json`
- `governance/generation_2/STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md`
- `reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.json`
- `reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json`

**Enforcement.** The sealer and the package builder both assert byte-equality of this string against the value in this file. A paraphrase is a failure, not a stylistic choice.

**Encoding note.** The string is stored with the em dashes of the source prose, as UTF-8, matching every other governance artifact in this tree. An earlier draft of this file substituted ASCII hyphen-minus on the stated grounds that the tree was ASCII-only; that was false — the Attempt 1 protocol Markdown alone carries 49 em dashes — and it would have made 'verbatim' mean 'verbatim except for two characters'. Byte-equality is checked against this stored form. The consequence is that no diagnostic script may print this string to a cp1252 console; scripts compare it and report a boolean instead.

**Attempt 3 encoding addendum.** This attempt's string carries one character the Attempt 2 string did not: U+2212 MINUS SIGN, in the phrase naming the removed drawdown tier. It is stored as it appears in the source prose, for the same reason the em dashes are. A reader diffing the two strings for a hyphen will not find one and should not add one.

**Source.** The Attempt 3 operating instruction, section 1, which requires this paragraph to be carried verbatim in the decision report and everywhere the development result is referenced.

### 14.2 The validation-reuse disclosure

> Generation 2's validation window (2021-08-01 → 2024-07-31) overlaps the exact period Generation 1 used for its own Gate 4 validation read. The researcher therefore already knows, from Generation 1's published report, approximately how SPY (and by extension the broad market) behaved in this window — including its Sharpe ratio (≈0.20), total return (≈2.15%), and fold-by-fold sign pattern (7 of 12 positive). Generation 2 tests a different hypothesis (cross-sectional multi-asset selection vs. single-symbol mean reversion) over the same calendar period, which limits but does not eliminate the concern. This is a real multiplicity cost, disclosed and not minimized, and it is the reason Generation 2's validation result alone — without a clean holdout confirmation — cannot be treated as sufficient evidence of an edge.

## 15. Conflicts and interpretations

| Id | Conflict | Resolution | Provenance |
|---|---|---|---|
| `G2A2-CONFLICT-1` | Per-session decision-taking departs from Attempt 1's sealed execution.no_discretionary_exits clause. | The clause is narrowed to entries rather than weakened: Attempt 2 may issue risk-reducing SELL orders between rebalances and may issue no BUY of any kind. The ranking is still consulted only on scheduled rebalance sessions. | carried from SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 unchanged, so the conflict is inherited unchanged and keeps its original id.; see execution.no_discretionary_exits_superseded |
| `G2A2-CONFLICT-2` | The 50% aggregate exposure ceiling has no cost-model derivation route: g2_costs.derive_mapping permits exactly one JSON-pointer override and it is spent on /account/max_open_risky_positions. | RA2-1 is enforced as a new named engine clamp AGGREGATE_RA2 in the Attempt 2 engine subclass, in addition to the inherited 0.95 AGGREGATE clamp, which stays in place and is never binding. The sealed cost model is not modified. | carried from SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 unchanged, so the conflict is inherited unchanged and keeps its original id.; see risk_architecture.components.RA2-1.enforcement.part_a_entry_clamp |
| `G2A2-CONFLICT-4` | Target weights change from min(0.95/k, 0.50) to min(0.50/k, 0.50). | Derived from the ceiling that actually binds. Declared here before any run and checked against this table by the candidate. | carried from SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 unchanged, so the conflict is inherited unchanged and keeps its original id.; see position_sizing |
| `G2A2-CONFLICT-5` | Stop and throttle decisions carry one session of execution lag. | Accepted and measured. It is the constitutional next-open convention, which the research shutdown itself obeys. | carried from SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 unchanged, so the conflict is inherited unchanged and keeps its original id.; see execution.execution_lag |
| `G2A2-CONFLICT-7` | Attempt 1's declared k=1 half-cash bias (its SC-3) is removed as a side effect of RA2-1. | Recorded so that a reader comparing selection outcomes across the two attempts knows the k axis is no longer confounded with gross exposure. | carried from SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 unchanged, so the conflict is inherited unchanged and keeps its original id.; see position_sizing.attempt_1_k1_half_cash_bias_neutralised |
| `G2A2-CONFLICT-11` | The per-position concentration ceiling (0.50) now equals the aggregate ceiling, so it is non-binding for k>=2 and coincident with RA2-1 at k=1. | Left in place and still enforced. A clamp that never binds is not a clamp that may be removed. | carried from SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 unchanged, so the conflict is inherited unchanged and keeps its original id.; see concentration_ceiling.non_binding_note |
| `G2A2-CONFLICT-12` | The sealed 5% minimum cash buffer can never bind at a 50% gross ceiling. | Enforced anyway and reported as never binding. | carried from SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 unchanged, so the conflict is inherited unchanged and keeps its original id.; see structural_consequences_declared_before_running.SC-5 |
| `G2A2-CONFLICT-13` | The RA2-2 volatility measure is taken on an equity curve that RA2-2 itself influences. | The feedback is negative, damped by a 20-session lag, and cannot diverge. Not corrected - correcting it would require a counterfactual unlevered equity curve. The realized distribution of the scalar is reported instead. | carried from SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 unchanged, so the conflict is inherited unchanged and keeps its original id.; see risk_architecture.components.RA2-2.self_reference |
| `G2A2-CONFLICT-14` | Position carries no entry price, so the 8% stop reference must be defined. | Frozen as cost_basis / quantity, the all-in per-share cost including commission and fees. Marginally conservative and invariant under a partial trim. | carried from SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 unchanged, so the conflict is inherited unchanged and keeps its original id.; see risk_architecture.components.RA2-3.reference_price_definition |
| `G2A2-CONFLICT-16` | stockedge100.backtest.orders.REASONS is a closed declared set with no entry for an aggregate-ceiling rejection. | An entry clamped to zero by AGGREGATE_RA2 is rejected as INSUFFICIENT_CASH with the clamp named in the detail string. The sealed set is not widened at runtime. | carried from SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 unchanged, so the conflict is inherited unchanged and keeps its original id.; see risk_architecture.components.RA2-1.enforcement.part_a_entry_clamp |
| `G2A2-CONFLICT-17` | A throttle trim below the sealed minimum order notional is skipped, so the aggregate ceiling can be transiently exceeded by less than one minimum lot. | Skipped legs are counted and reported per variant, and the ceiling assertion admits exactly this slack and no more. | carried from SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 unchanged, so the conflict is inherited unchanged and keeps its original id.; see risk_architecture.components.RA2-1.enforcement.part_b_continuous_throttle |
| `G2A3-CONFLICT-34` | The paired immutability check must now cover seventeen modules, not nine: Attempt 2's eight became immutable when Attempt 2 closed, and a check that still counted nine would pass while an Attempt 2 module was being rewritten. | prior_attempt_modules_immutable enumerates both lists separately and declares the total. The Attempt 3 sealer refuses to seal unless it measures seventeen, and the count is a literal in the sealer so a silently shortened list fails loudly rather than quietly. | supersedes in scope: G2A2-CONFLICT-3, which declared a content-based contamination predicate over Attempt 1's nine modules and is not edited.; see prior_attempt_modules_immutable, declared_before_any_strategy_code_measurement |
| `G2A3-CONFLICT-35` | This pre-registration was written after TWO attempts' development results were known, and both of its changes were chosen in response to the second. Pre-registration constrains what happens after this file is sealed; it cannot undo what was known before. | The adaptation is disclosed in adaptation_disclosure_verbatim, which is carried byte for byte into five artifacts and enforced by both the sealer and the package builder. The multiplicity is disclosed as 54 variants and 108 runs with an explicit statement that the effective degrees of freedom exceed the count. No threshold is adjusted in either direction to compensate. | supersedes in scope: G2A2-CONFLICT-6, which disclosed that Attempt 2's pre-registration was written after Attempt 1's results were known, and is not edited.; see adaptation_disclosure_verbatim, multiple_comparisons_disclosure, G2A3-CONFLICT-33 |
| `G2A3-CONFLICT-36` | Both fail routes — no eligible representative, and a representative that fails the gate — emit the same token, STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE, although they are different findings. Under RA3 the two routes are also more nearly equally likely than they were in Attempt 2, where the first was effectively closed. | The route is recorded as an explicit fail_route field in the verdict record, in the gate conditions and in the report prose. The token is not split, because the token vocabulary is sealed in SE100-CFG-3106 and minting a third would be a stage inventing its own verdict space. | supersedes in scope: G2A2-CONFLICT-9, which recorded the same collision for Attempt 2's token and is not edited.; see representative_selection_rule.no_candidate_path, .second_fail_path |
| `G2A3-CONFLICT-37` | The Attempt 3 operating instruction names no verdict token at all. It requires a token 'of your own derivation' and directs that the sealed criteria file be grepped for the actual strings rather than inventing one from the prompt. | There is no prompt string to conflict with, so the tokens are minted once, in SE100-CFG-3106's verdict_token_derivation, and every other artifact reads them from there. This is the first attempt in which the prompt and the sealed derivation cannot disagree, which removes the failure mode G2A2-CONFLICT-8 described rather than resolving it a second time. The four tokens belonging to Attempts 1 and 2 are read from those attempts' own files and asserted absent from every Attempt 3 verdict field. | supersedes in scope: G2A2-CONFLICT-8, which recorded that the Attempt 2 operating prompt named verdict tokens existing in no artifact, and is not edited.; see SE100-CFG-3106 verdict_token_derivation, G2A3-CONFLICT-21 |
| `G2A3-CONFLICT-38` | Attempt 2's sealed pre-registration forbids this attempt. Binding rule 7 of SE100-GOV-2005 section 17 reads 'No Attempt 3 is authorized. If Attempt 2 fails, the attempt closes.' Attempt 2 failed and this attempt is nevertheless open, so a sealed artifact and this session disagree on the face of the record. | Attempt 2's rule is not edited, reopened or reinterpreted; it stands exactly as sealed, and the disagreement is recorded here rather than resolved away. That rule bound the attempt that wrote it in the absence of any further authorization, and its force is to require a new authorization rather than to make one impossible. The authorization is external and human: a written operating instruction for this session that opens Attempt 3 as a third disclosed adaptation and mandates the verbatim adaptation disclosure carried in adaptation_disclosure_verbatim. A stage artifact's self-imposed closure rule is not a constitutional provision and does not outrank the operator; what it does outrank is a silent reopening, which is the thing that did not happen here. This file writes the identical rule about an Attempt 4 (see explicit_non_authorizations and representative_selection_rule.no_candidate_path.attempt_closes), and that rule is to be read the same way: it forbids an undisclosed continuation, not a disclosed and separately authorized one. | see SE100-GOV-2005 section 17 rule 7, adaptation_disclosure_verbatim, G2A3-CONFLICT-35, explicit_non_authorizations |

**Note.** The Attempt 3 conflict numbering is one space shared by this file and SE100-CFG-3106, exactly as Attempt 2's was shared by SE100-CFG-3103 and SE100-CFG-3104. Ids 18 to 25 were taken by Attempt 2's criteria file; ids 26 to 33 are fresh ids taken by Attempt 3's criteria file; this file takes 34 onward. Four entries in Attempt 3's criteria file reuse a number below 26 on purpose: G2A3-CONFLICT-19, 21, 22 and 24 each supersede in scope the same-numbered G2A2 entry, so a superseding conflict keeps its predecessor's number and changes only its prefix. The prefix makes the two distinct ids. Nothing is duplicated across the two files, so the two cannot drift into disagreeing versions of one conflict.

**Declared in g2 gate criteria RA3.**

- G2A3-CONFLICT-19
- G2A3-CONFLICT-21
- G2A3-CONFLICT-22
- G2A3-CONFLICT-24
- G2A3-CONFLICT-26
- G2A3-CONFLICT-27
- G2A3-CONFLICT-28
- G2A3-CONFLICT-29
- G2A3-CONFLICT-30
- G2A3-CONFLICT-31
- G2A3-CONFLICT-32
- G2A3-CONFLICT-33

**Inherited and restated in g2 gate criteria RA3.**

- S3-CONFLICT-1
- S3-CONFLICT-3
- G2-CONFLICT-6
- G2-CONFLICT-7
- G2-CONFLICT-15
- G2A2-CONFLICT-18
- G2A2-CONFLICT-20
- G2A2-CONFLICT-23
- G2A2-CONFLICT-25

## 16. Adversarial tests required

**Note.** Declared here before the tests exist, so that the test suite is written against a specification rather than against the implementation's behaviour. Each item is a required test, not a suggestion.

| Id | Requirement |
|---|---|
| `AT-A` | Aggregate exposure never exceeds 50% of equity at any session, including mid-rebalance, verified after every fill and not only at session close. |
| `AT-B` | Volatility scaling reduces position size when trailing realized portfolio volatility exceeds 10% annualized, verified against a hand-constructed high-volatility equity fixture with an independently computed expected scalar. |
| `AT-C` | A position breaching the 8% stop is exited at the NEXT session's open, not at the same close, and the exit is a full sell. |
| `AT-D` | The de-risk ladder steps down at the declared RA3 thresholds and back up only after the declared recovery condition, verified against a hand-constructed drawdown-and-recovery fixture that visits every band in both directions. The fixture must include a drawdown that reaches 6 percent and assert that the combined ladder scalar is exactly 1 there, which is the single behavioural difference from RA2 and would otherwise be tested only by absence. |
| `AT-E` | The re-entry lockout genuinely blocks a return to a higher sizing band before its cooldown elapses, verified by a fixture in which recovery is available and blocked for exactly the declared number of sessions. |
| `AT-F` | Determinism: identical inputs produce identical trade, equity, ranking and risk-state digests on a clean rerun. |
| `AT-G` | The Generation 2 window guard still blocks any read at or after 2021-08-01, exercised through the Attempt 3 loading path. The guard is reused, not reimplemented, and the test asserts that the module under test is the existing g2_window_guard. |
| `AT-H` | No Generation 1, Attempt 1 or Attempt 2 module is modified: every one of the seventeen modules listed in prior_attempt_modules_immutable re-hashes to its recorded digest. |
| `AT-I` | The selection input cannot carry a performance figure: the SelectionInputV2 field tuple equals SELECTION_V2_FIELD_NAMES and the import-time assertion fires when it does not. The test also asserts that no field name matches a performance vocabulary (return, pnl, profit, drawdown, sharpe, equity, ratio, factor), so a future field named plausibly rather than obviously is also caught. |
| `AT-J` | Neighbour identification is correct at the grid edges: the neighbour counts are 3, 4 and 5, the partition over the eighteen variants is 8 / 8 / 2, and at least one variant of each class has its full neighbour set written out as a literal in the test and compared element by element against the computed set. The relation is also asserted symmetric, and asserted to contain no variant outside the grid and never the variant itself. |
| `AT-K` | SE100-G2-SEL-2 is deterministic: identical recorded statistics produce identical scores, identical component breakdowns and an identical selected variant across two independent computations in the same process and one from a round-trip through the serialised selection inputs. |
| `AT-L` | The RA3 band table is the sealed one and contains no band boundary below 0.08: the loaded architecture has exactly three bands, its scalars are strictly decreasing in (0, 1], its first band starts at 0.00 with scalar 1.00, its last band is open-ended, and the absolute aggregate ceilings it induces equal 0.500000000 / 0.250000000 / 0.125000000. |
| `AT-M` | The RA3 engine re-derives exactly the risk-dependent attributes it must after calling super().__init__, verified by parsing the Attempt 2 engine's __init__ for the attributes assigned from self.risk and asserting the RA3 subclass reassigns precisely that set. This is the same AST mechanism Attempt 2 used against Attempt 1's __init__. |

**Regression floor.** The existing suite is a permanent regression floor. No test is weakened, skipped or deleted to make this attempt pass.

### 16.1 Reproducibility

**Determinism.** Two clean runs of the same variant and scenario must produce byte-identical trade payloads, equity payloads, ranking digests, and risk-architecture state traces.

**Risk state trace digest.** As Attempt 2: a SHA-256 over the per-session risk state (band, lockout counter, volatility scalar, combined scalar) in session order, recorded in addition to the ranking digest. Under RA3 the band alphabet is {0, 1, 2} rather than {0, 1, 2, 3}, so an Attempt 3 trace digest is not comparable with an Attempt 2 trace digest and neither is expected to equal the other.

**No wall clock in payloads.** No run id, timestamp or filesystem path enters any digested payload.

**Seed.** `null`

**Seed note.** There is no randomness in this strategy. The field is null rather than absent so that a future stage cannot read its absence as an oversight.

**Selection determinism.** SE100-G2-SEL-2 must produce identical scores, identical per-quantity components, identical neighbour sets and an identical selected variant on a clean rerun from the same recorded statistics. This is tested directly against the recorded selection inputs, not only end-to-end, so a determinism failure in the selector cannot hide behind a determinism pass in the engine.

## 17. Binding rules

1. This document is sealed on write. If a defect is found in this protocol after it is sealed, it is reported as a blocker and recorded in the stage report. This file is not edited. A correction means a new artifact with a new id that supersedes this one, and the superseding artifact carries the reason. — applies equally to Every Generation 1 artifact, every Generation 2 Attempt 1 artifact, every Generation 2 Attempt 2 artifact, and this one..
2. **Attempt 1 and Attempt 2 are closed.** Attempt 1's verdict `FAIL — STAGE_3_G2_NO_CANDIDATE` and Attempt 2's verdict `FAIL — STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE` stand permanently against the figures their own records describe. Generation 1, Generation 2 Attempt 1 and Generation 2 Attempt 2 are read-only: nothing in this attempt edits, deletes, reopens, re-runs, loosens or supersedes any of their artifacts or modules. All 17 prior-attempt modules listed in section 13 are re-hashed at seal time and again at package time, and a single changed digest is a blocker. They are pinned so that a change to any of them is **detectable**, not so that any of them may be changed.
3. **Attempt 2's own binding rule 7 forbids this attempt**, and is not edited. Section 17 of `SE100-GOV-2005` reads "No Attempt 3 is authorized. If Attempt 2 fails, the attempt closes." That rule bound the attempt that wrote it in the absence of any further authorization; its force is to require a new authorization, not to make one impossible. The authorization for this attempt is external and human, and the adaptation it authorizes is disclosed verbatim in section 14.1. The rule this file writes about an Attempt 4 in section 17.1 is to be read the same way. See `G2A3-CONFLICT-38`.
4. The grid is not widened. The grid is complete at eighteen and may not be widened, narrowed or re-centred. The risk architecture constants are not axes.
5. `RA3` is frozen before any variant is run and is not part of the grid. Every constant below is fixed and applied uniformly to all eighteen variants. Searching them alongside the rotation parameters would cross from a disclosed risk control into curve-fitting to 2008 and 2020 - the two episodes whose observation motivated this attempt in the first place. The grid remains exactly the eighteen rotation parameterisations of Attempt 1 and is not widened.
6. `SE100-G2-SEL-2` is frozen before any variant is run and is return-blind by construction, enforced at import time. The module asserts at import that the dataclass's actual field tuple equals the declared SELECTION_V2_FIELD_NAMES, in order. A field added later fails the import rather than silently widening what the selector can see. This is the same mechanism SE100-CFG-3103 required of Attempt 2's SelectionInput, extended to six fields.
7. Gate 3 thresholds are unchanged from Generation 1, Attempt 1 and Attempt 2. No threshold is adjusted in either direction to compensate for either change.
8. No window at or after 2021-08-01 is read, by this document or by any code it governs. The prohibited windows are listed in section 14.
9. The adaptation disclosure of section 14.1 is carried verbatim into all 5 artifacts listed there.
10. `live_trading_authorized` is `false` and this document does not change it.

### 17.1 Explicit non-authorizations

- This file does not authorize reading any session at or after 2021-08-01, in this or any later stage.
- This file does not authorize reading Generation 1's holdout (2024-08-01 to 2026-07-31), which is spent and prohibited regardless of generation.
- This file does not authorize reading Generation 2's holdout (2026-08-01 to 2028-07-31), which is sealed and must never be read before that period exists in real calendar time.
- This file does not authorize Stage 4 validation. Stage 4 requires an explicit human go-ahead recorded in a later session.
- This file does not authorize live trading, order placement, order cancellation, order replacement, liquidation, or unattended scheduling. live_trading_authorized remains false.
- This file does not authorize reading, writing, printing or logging any broker credential, and no module of this attempt may import a network client.
- This file does not authorize editing, deleting, re-running, reopening or loosening any Generation 1 artifact or module.
- This file does not authorize editing, deleting, re-running, reopening or loosening any Generation 2 Attempt 1 artifact or module. Attempt 1's verdict stands permanently.
- This file does not authorize editing, deleting, re-running, reopening or loosening any Generation 2 Attempt 2 artifact or module. Attempt 2's verdict stands permanently.
- This file does not authorize widening, narrowing or re-centring the eighteen-variant grid.
- This file does not authorize grid-searching, tuning or adjusting any RA3 constant, or any SE100-G2-SEL-2 quantity, weight or threshold, before or after seeing a result.
- This file does not authorize promoting a runner-up if the representative fails the gate.
- This file does not authorize an Attempt 4. If Attempt 3 fails, the attempt closes and any further work requires a further disclosed adaptation and a separate authorization. SE100-CFG-3103 said the same of Attempt 3; see G2A3-CONFLICT-28, which records that this attempt exists on a separate authorization and not on SE100-CFG-3103's.
- This file does not authorize weakening, skipping or deleting any existing test.
- This file does not authorize a fourth selection rule, a reweighting of SE100-G2-SEL-2's four quantities, or the addition of a fifth, at any point after this file is sealed.
- This file does not authorize isolating the two changes by re-running either of them alone. An isolation attempt is a further attempt and requires its own authorization and its own disclosure of the multiplicity it adds.

*Machine companion: `STAGE_3_G2_ROTATION_RA3_PROTOCOL.json`, sealed by `STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256`. The tree digest `repo_state_id` for the sealing run is recorded in `runs/`, deliberately not in this document — `repo_state_id` covers files in this tree, and a document that carried it would invalidate it on write.*
