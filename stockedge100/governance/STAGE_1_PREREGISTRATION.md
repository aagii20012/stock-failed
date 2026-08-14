# Stage 1 — Data Foundation Pre-registration

**Document ID:** `SE100-GOV-0003`
**Project:** StockEdge100
**Generation:** 1
**Stage:** 1 — data foundation (pre-registration, written before any data was acquired)
**Declared (UTC):** 2026-08-08T10:35Z — the authoritative timestamp and the digest of every
pre-registered file are in `governance/STAGE_1_PREREGISTRATION.json`, which is generated after this
document and therefore cannot be quoted inside it.
**Status of this document:** pre-registration. It constrains Stage 1; it does not modify, supersede,
reinterpret, or extend `SE100-GOV-0001`.

---

## 1. Why this document exists

`STAGE_0_VERIFICATION_REPORT.md` §11 recorded that two provider reachability probes had already been
run before Stage 1 began, and imposed a binding consequence:

> Stage 1 must declare its provider and fallback policy in writing, hash that declaration, and only
> then acquire data.

This document and its two companion configuration files are that declaration. They are written,
hashed, and recorded **before** the first byte of market data is requested, so that no later reader
has to take on trust that the acquisition rules were not adjusted once the data was visible.

The ordering is the point. A rule chosen after seeing the data it governs is not a rule.

---

## 2. Pre-registered files

| File | Content |
|---|---|
| `config/stage1_data_source.json` | provider decision, acquisition protocol, normalization spec, validation battery, time-partition rule |
| `config/stage1_universe_spec.json` | scope decision, survivorship verdicts, eligibility rules, candidate list, reference symbols |
| `governance/STAGE_1_PREREGISTRATION.md` | this document |
| `governance/STAGE_1_PREREGISTRATION.json` | authoritative declaration timestamp and digests of the three files above |
| `governance/STAGE_1_PREREGISTRATION.sha256` | checksum record covering the four files above |

`STAGE_1_PREREGISTRATION.sha256` records **project-root-relative** paths, so it is verified from
`stockedge100/`:

```bash
cd stockedge100 && sha256sum -c governance/STAGE_1_PREREGISTRATION.sha256
```

This differs deliberately from `STAGE_0_FREEZE.sha256`, which records bare filenames and is verified
from `governance/`. The two records cover different directories and cannot use the same convention.
Neither record contains its own digest; nothing hashes itself.

---

## 3. The data-source decision

**Selected:** Yahoo Finance daily bars, retrieved with the `yfinance` client, no API key, no
account, no payment.

Stooq was rejected: Stage 0 observed its documented CSV endpoint returning an anti-bot HTML page
(HTTP 200) and HTTP 404 for a dated variant. It is not usable for automated retrieval from this
environment. No paid provider was evaluated, because no purchase is authorized.

This leaves **exactly one** viable provider. The consequences are declared here rather than
discovered later:

1. **Single-provider risk is not mitigated.** There is no second free source, so no cross-provider
   agreement check exists. Every downstream number inherits whatever Yahoo gets wrong.
2. **The endpoint is unofficial.** There is no schema contract and no service guarantee.
3. **The licence is personal and non-commercial, with no redistribution.** Acquired data stays local
   and git-ignored. It is never committed, published, or shared.
4. **Vendor history can be silently revised.** Mitigation is immutable raw preservation plus hash
   comparison on every rerun. A changed payload is quarantined as `PROVIDER_REVISION`, never
   silently accepted.

`auto_adjust=False` is mandatory. The constitution (§6) requires retaining adjusted **and**
unadjusted OHLCV, or documenting a verified transformation between them. Requesting pre-adjusted
data would destroy the evidence needed to verify the adjustment.

---

## 4. The universe decision, and the honest part of it

The provider offers no point-in-time index membership and no delisted-security coverage. A
present-day list of individual stocks backtested over history would therefore embed an uncontrolled
upward survivorship bias — the companies that failed are simply not in the list.

Constitution §6 anticipates this exact situation and supplies the remedy: narrow prospectively to
ETF-only research, frozen before any strategy result is viewed. That is what is done.

**Verdicts recorded, as §6 requires explicitly:**

| Question | Verdict |
|---|---|
| Individual-stock universe | `SURVIVORSHIP_BIAS_UNCONTROLLED` — stock research is prohibited in Generation 1 without a new data source |
| ETF universe | `RESIDUAL_FUND_CLOSURE_BIAS_DISCLOSED_AND_UNQUANTIFIED` |

The second verdict deserves plain language. Narrowing to ETFs **reduces** survivorship bias; it does
not remove it. The 34 candidates were listed in 2026, so they are by definition funds that still
exist in 2026. ETFs that launched and closed during the sample period are absent. The residual is
smaller than the stock case — closures concentrate in small, narrow, recently launched products, and
the pre-registered inception cutoff of 2010-01-04 excludes that whole population — but it is real,
it is not quantifiable without a delisted-fund database, and no Stage 1 artifact may describe this
universe as survivorship-free.

The candidate list was chosen on **structure and longevity**: asset-class coverage first, then the
oldest and largest fund for each exposure. No return series was inspected before the list was
frozen. Four near-duplicate pairs (IVV/SPY, VEA/EFA, VWO/EEM, AGG/BND) are included deliberately as
a redundancy control — two sponsors tracking one exposure give the only independent data-quality
cross-check available to a single-provider feed.

**Narrower than the constitution, never wider.** Physical-commodity grantor trusts (`GLD`, `SLV`,
`IAU`) are excluded. Constitution §3 defines the scope as "US-listed common stocks and unleveraged
ETFs"; a physical-metal grantor trust is not a registered investment company and is not literally an
ETF. Stage 1 declines to widen a frozen scope by interpretation. Adding that class requires a new
constitution version, not a Stage 1 decision.

**Broker eligibility is `UNVERIFIED`, not assumed.** No credential access is authorized at Stage 1,
so Alpaca tradability and fractional eligibility are recorded as unknown for every symbol and
resolved at Stage 6. The realized universe is therefore conditional: any symbol later found
non-tradable or non-fractionable must be removed and every affected gate re-run.

---

## 5. Rules that bind the rest of the stage

1. **Eligibility is mechanical.** The rules in `stage1_universe_spec.json` are applied as written.
   No symbol may be added or removed by judgement after the data is visible.
2. **Every eligibility and quality measurement reads development-window data only.** No liquidity
   screen, no price floor, no quality statistic may touch the validation or holdout window. This is
   enforced by test, not by convention.
3. **Raw data is write-once.** An existing raw file is never overwritten. A differing payload is
   quarantined and recorded.
4. **No row is silently dropped.** A row failing a sanity rule is retained, flagged, and copied to
   `data/quarantine/` with a reason.
5. **Adjustment semantics are measured, not assumed.** The normalizer determines empirically whether
   the provider's unadjusted OHLC is already split-adjusted, and records what it measured.
6. **The time partition is computed once**, from the frozen usable cutoff, before any strategy
   result exists, and the holdout is then `SEALED`.
7. **If more than 20% of candidates fail acquisition, the stage returns
   `BLOCKED_BY_DATA — DATA_NOT_FIT_FOR_RESEARCH`** rather than proceeding on a thinned universe.

---

## 6. Explicit non-authorizations, restated for this stage

Stage 1 does not authorize, and this stage will not perform:

- any purchase, subscription, or account creation — if a provider demands payment, the stage stops
  and asks the project owner;
- any credential access, or any read of a secret value;
- any order, paper or live;
- any strategy computation, signal, parameter, ranking, or performance figure of any kind;
- any read of holdout-window data for an eligibility or quality decision.

`live_trading_authorized` remains `false`.

---

## 7. Pre-freeze disclosure

One provider reachability probe was performed in this session **before** this document was written:
an HTTP status check of the Yahoo chart endpoint for `SPY` and of the Stooq CSV endpoint. Yahoo
returned HTTP 200 with `application/json`; Stooq returned HTTP 200 with `text/html`, reproducing the
Stage 0 finding. Response bodies were not parsed and no price value was read or displayed. It is
recorded here so that the provider decision above cannot be characterised as having been made in
ignorance of, or in concealment of, an observation already made.

The earlier Stage 0 probes — a toolchain inventory, the `exchange_calendars` install, and eight SPY
daily bars from January 2024 — remain disclosed in `STAGE_0_VERIFICATION_REPORT.md` §11 and are
inputs to this decision rather than discoveries made after it.
