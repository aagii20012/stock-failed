# Stage 0 — Constitution Verification Report

**Document ID:** `SE100-GOV-0002`
**Project:** StockEdge100
**Generation:** 1
**Stage:** 0 — Constitution verification (re-verification of a previously frozen artifact)
**Verification completed (UTC):** 2026-08-08T10:15Z — the authoritative timestamp, run id, and
repository state id are in `reports/stage0/STAGE_0_VERIFICATION.json` and the matching record under
`runs/`. Run records are append-only; the latest one governs.
**Verifier:** automated agent session, working directory `D:\Product\stock-trade-alpaca`
**Status of this document:** verification evidence. It does **not** modify, supersede, reinterpret, or extend `SE100-GOV-0001`.

---

## 1. Scope and authorization boundary

Authorized in this stage:

- read-only inspection of the frozen Stage 0 artifacts;
- cryptographic verification of the recorded freeze hashes;
- consistency comparison between the human-readable and machine-readable constitutions;
- comparison of the operating prompt against the constitution to detect weakening;
- creation of new, additive verification evidence.

Explicitly **not** performed in this stage:

- any edit to `STAGE_0_CONSTITUTION.md`, `STAGE_0_CONSTITUTION.json`, or `STAGE_0_FREEZE.sha256`;
- any data download;
- any strategy computation;
- any broker contact;
- any credential access.

---

## 2. Observed facts — artifact presence

| Artifact | Path | Present | Bytes | Notes |
|---|---|---|---|---|
| Human-readable constitution | `governance/STAGE_0_CONSTITUTION.md` | yes | see manifest | 316 lines, 13 sections |
| Machine-readable constitution | `governance/STAGE_0_CONSTITUTION.json` | yes | see manifest | parses as valid JSON, 18 top-level keys |
| Freeze hash record | `governance/STAGE_0_FREEZE.sha256` | yes | see manifest | 2 entries, coreutils format, bare relative filenames |

---

## 3. Observed facts — hash verification

The freeze file records bare filenames (`STAGE_0_CONSTITUTION.md`, `STAGE_0_CONSTITUTION.json`) with no
directory component. The working directory implied by that record is therefore
`stockedge100/governance/`. Verification was executed from that directory.

Command:

```
cd stockedge100/governance && sha256sum -c STAGE_0_FREEZE.sha256
```

Result:

```
STAGE_0_CONSTITUTION.md: OK
STAGE_0_CONSTITUTION.json: OK
exit status 0
```

Independently recomputed digests:

| File | Recorded SHA-256 | Recomputed SHA-256 | Match |
|---|---|---|---|
| `STAGE_0_CONSTITUTION.md` | `b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5` | `b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5` | yes |
| `STAGE_0_CONSTITUTION.json` | `af45fda6b37bed50768d5f3d01d4a91175da93e708c9daf1b630e35a981e2ff5` | `af45fda6b37bed50768d5f3d01d4a91175da93e708c9daf1b630e35a981e2ff5` | yes |

`STAGE_0_FREEZE.sha256` does not contain a digest of itself; that is expected and is not treated as
a defect. Its own digest is recorded below as external evidence only.

- `STAGE_0_FREEZE.sha256` observed digest: recorded in `reports/stage0/STAGE_0_VERIFICATION.sha256`.

**Verification verdict for hashes: PASS.**

---

## 4. Observed facts — JSON validity

`STAGE_0_CONSTITUTION.json` parses under a strict JSON parser with no errors. It declares gate
records for ids 0–9 inclusive, with no duplicate or missing id in that range.

**Verification verdict for JSON validity: PASS.**

---

## 5. Calculated result — human vs machine rule comparison

Every quantitative rule present in both documents was compared field by field.

| Rule | Markdown (`.md`) | JSON (`.json`) | Consistent |
|---|---|---|---|
| Document id | `SE100-GOV-0001` | `SE100-GOV-0001` | yes |
| Version | `1.0.0` | `1.0.0` | yes |
| Status | `FROZEN` | `FROZEN` | yes |
| Effective date | `2026-08-08` | `2026-08-08` | yes |
| Timezone | Asia/Ulaanbaatar | `Asia/Ulaanbaatar` | yes |
| Capital | USD 100.00 | `100.0` | yes |
| Broker target | Alpaca | `Alpaca` | yes |
| Long only | yes | `true` | yes |
| Cash account only | yes | `true` | yes |
| Daily data | yes | `true` | yes |
| Max risky positions | 1 | `1` | yes |
| Max gross exposure | 95% | `95` | yes |
| Fractional shares required | yes | `true` | yes |
| Prohibited products | options, futures, CFDs, leveraged/inverse ETFs, OTC, penny stocks, shorts, margin, crypto | same 10 tokens | yes |
| Research drawdown shutdown | 15% below high-water mark | `research_max_drawdown_pct: 15` | yes |
| Live soft halt | 8% | `8` | yes |
| Live hard halt | 10% | `10` | yes |
| Exclude incomplete cutoff month | yes | `true` | yes |
| Holdout months | 24 complete | `24` | yes |
| Validation months | 36 complete | `36` | yes |
| Minimum development | 5 years | `5` | yes |
| Partition computed before results | yes | `true` | yes |
| Stressed cost multiplier | 2× | `2.0` | yes |
| Gate 3 thresholds | return>0, MDD≤15%, PF≥1.10, ≥30 closed trades, best-trade removal still >0 | identical | yes |
| Gate 4 thresholds | return>0, Sharpe≥0.50, MDD≤15%, PF≥1.15, stressed>0, ≥70% positive folds | identical | yes |
| Gate 5 thresholds | return>0 and > cash, Sharpe≥0.50, MDD≤12%, PF≥1.15, stressed≥0, best-trade removal >0, ≥20 trades | identical | yes |
| Gate 6 threshold | MDD ≤ 12% | `12` | yes |
| Gate 7 thresholds | 90 days min / 180 max, 30 closed trades, return>0, MDD≤10%, PF≥1.10 | identical | yes |
| Gate 8 thresholds | 60 days, 20 intended round trips, whichever is longer | identical | yes |
| Gate 9 | manual written approval required, default `LIVE_TRADING_LOCKED` | identical | yes |
| Stage 0 verdict | `PASS — STAGE_0_CONSTITUTION_FROZEN` | `PASS` / `STAGE_0_CONSTITUTION_FROZEN` | yes |

Non-material asymmetries observed (recorded, not treated as conflicts):

1. The Markdown contains narrative sections (mandate, principles, benchmarks, data constitution,
   research protocol, change control, non-authorizations) with no JSON counterpart. The JSON is a
   threshold companion, not a full serialization. The Markdown is therefore the controlling text
   wherever the JSON is silent.
2. The Markdown Gate 3 rule "no single instrument contributes more than 50% of total strategy
   profit for a multi-instrument strategy" and "neighbouring parameter values do not reverse the
   sign of net return" have no JSON keys. Both are treated as binding via the Markdown.
3. The JSON records no `pass_result` string for gates 1, 2, 3, 4, 6, 7, 8. Absence of a pass token
   is not a weakening; the Markdown pass conditions govern.

**Verification verdict for MD/JSON consistency: PASS — no material conflict.**

---

## 6. Calculated result — does the operating prompt weaken the constitution?

The operating prompt for this session was compared against `SE100-GOV-0001`. Where the two differ,
the constitution governs. No rule in the prompt was found that weakens a frozen rule.

### 6.1 Rules where the constitution is stricter — constitution applied

| Topic | Prompt | Constitution | Applied rule |
|---|---|---|---|
| Research drawdown ceiling | not specified numerically for research | 15% below running high-water mark (§5.1); Gate 5 tightens to 12% | 15% development/validation, 12% holdout and controller |
| Development trade minimum | "adequate trade count" | ≥30 closed trades (Gate 3) | ≥30 |
| Holdout trade minimum | "adequate trade count" | ≥20, else `INSUFFICIENT_HOLDOUT_EVIDENCE` (Gate 5) | ≥20 with the explicit third outcome |
| Stressed costs | "adverse cost scenario" | exactly 2× the complete base friction assumption (§7) | 2× |
| Walk-forward | "walk-forward evaluation" | ≥70% of folds positive after cost (Gate 4) | ≥70% |
| Paper duration | ≥3 months and a declared minimum | 90 days **and** 30 closed trades; extend to 180; else `INSUFFICIENT_PAPER_EVIDENCE` (Gate 7) | 90/180 days with 30 closed trades |
| Shadow duration | "freeze a minimum before starting" | 20 intended round trips **or** 60 days, whichever is longer (Gate 8) | longer of the two |
| Paper drawdown ceiling | not specified | ≤10%, PF ≥1.10, return >0 (Gate 7) | applied |
| Combination of strategies | allowed at Stage 5 with a frozen rule | prohibited until each component has an independent verdict (§8) | each family gets an independent verdict first |
| Machine learning | prohibited in Generation 1 | not authorized for Generation 1 (§8) | prohibited |
| Live authorization | explicit human authorization | Gate 9 requires a **separate dated written approval by the project owner after Gates 0–8 pass** (§9) | dated written owner approval required |

### 6.2 Rules where the prompt is stricter or more detailed — prompt applied as implementation detail

The prompt adds operational requirements (quarantine policy, decision ledgers, idempotent client
order ids, kill switch, reconciliation, structured audit logs, reproducibility record fields).
None of these relax a frozen rule; they are additive and are adopted.

### 6.3 Gate numbering divergence — recorded, not a conflict

The prompt and the constitution use different gate numbers for the same checkpoints. To prevent
ambiguity in later reports, the following mapping is binding for this project. **Constitution gate
ids are authoritative for threshold lookup; prompt stage numbers are used for narrative stage
sequencing.**

| Prompt stage | Prompt gate token | Constitution gate id | Constitution gate name |
|---|---|---|---|
| Stage 0 | `GATE_0` | 0 | constitution_freeze |
| Stage 1 | `GATE_1` | 1 | data_readiness |
| Stage 2 | `GATE_2` | 2 | backtest_engine_validity |
| Stage 3 | `GATE_3` | 3 | development_admissibility |
| Stage 4 (robustness) | `GATE_4` part 1 | 4 | validation_robustness |
| Stage 4 (holdout) | `GATE_4` part 2 | 5 | final_holdout |
| Stage 5 | `GATE_5` | 6 | portfolio_controller |
| Stage 6 | `GATE_6` | 7 | alpaca_paper_trading |
| Stage 7 | `GATE_7` | 8 | shadow_live_readiness |
| Stage 8 / 9 | `GATE_8` / `GATE_9` | 9 | limited_live_authorization |

Consequence recorded explicitly: prompt Stage 4 must satisfy **two** constitutional gates (4 and 5),
not one. Robustness/walk-forward thresholds (gate id 4) must pass *before* the holdout ceremony, and
holdout thresholds (gate id 5) after it.

### 6.4 Apparent tension examined and resolved

Constitution §12 states that the constitution "does not authorize ... downloading or purchasing
data" and "accessing Alpaca credentials", while §13 names Stage 1 as the next authorized activity
and §6 requires a Stage 1 data manifest containing provider, retrieval time and raw hashes — which
presupposes retrieval.

Reading applied: §12 is a **scope disclaimer**, not a prohibition. It prevents authorization for
those actions from being *inferred from Stage 0 approval alone*; it does not forbid them once the
project owner separately authorizes the stage that needs them. The project owner's Stage 1
instruction supplies that authorization for **free, no-cost, read-only** data retrieval.

Conservative constraints adopted as a result, and binding on Stage 1:

- no paid data, no purchase, no subscription, no account creation — if any provider requires
  payment, the stage stops and asks the owner;
- no credential access at Stage 1; Alpaca tradability and fractional eligibility are recorded as
  **UNVERIFIED** placeholders to be resolved at the paper stage, not guessed;
- no inference of live-trading authorization from any of the above.

This reading does not weaken any threshold and is recorded here so that a future auditor can see the
tension was found, examined, and resolved conservatively rather than silently.

---

## 7. Observed facts — live-trading lock state

| Check | Observation |
|---|---|
| Constitution Gate 9 default result | `LIVE_TRADING_LOCKED` |
| Manual written approval recorded on disk | none found |
| Owner authorization present in this session | none |
| Alpaca credential environment variables present | none detected (names scanned only; no values read) |
| Any order-submitting code present in repository | none — repository contained only the three governance files at session start |

**Live trading state: LOCKED.**

---

## 8. Observed facts — repository state at verification time

At the start of this session the project directory contained exactly three files, all under
`governance/`. No other tracked or untracked project file existed. `D:\Product\stock-trade-alpaca`
is **not** a git repository; repository-state identity is therefore established by content hashing
rather than by commit id. No unrelated user file was read, moved, or deleted.

Files added during this session (none of them frozen, none of them overwriting anything):

| Path | Purpose |
|---|---|
| `governance/STAGE_0_VERIFICATION_REPORT.md` | this document |
| `README.md`, `pyproject.toml`, `.gitignore` | stage-neutral project foundation |
| `src/stockedge100/__init__.py`, `audit.py` | hashing, manifests, run records |
| `src/stockedge100/reporting/stage0_package.py` | decision-package generator for this stage |
| `tests/conftest.py`, `tests/unit/test_stage0_governance.py` | 27 executable governance tests |
| `reports/stage0/*` | decision record, artifact manifest, checksum record, test summary, raw pytest output |
| `runs/SE100-R-*.json` | reproducibility records, append-only |
| directory skeleton with `.gitkeep` files | required repository structure |

The repository state id is a SHA-256 over the sorted digest map of every governance, source, test,
and configuration file. It is deliberately **not** quoted inside this document: this document is
one of the hashed inputs, so any literal written here would be stale the moment it was written. The
binding value is the `repo_state_id` field of `reports/stage0/STAGE_0_VERIFICATION.json` and of the
latest run record.

---

## 9. Limitations

1. Verification proves the three artifacts are byte-identical to what the freeze file recorded. It
   cannot prove the freeze file itself was created before any strategy result existed; that claim
   rests on `SE100-GOV-0001` §9 Gate 0 and is accepted as declared, not independently verified.
2. There is no detached signature or external timestamp authority on the freeze. Integrity is
   local-filesystem integrity only.
3. The Markdown/JSON comparison is a rule-by-rule human-readable comparison, not a formal schema
   validation; the JSON declares a `$schema` URL that was not fetched (no network dependency was
   introduced into governance verification).

---

## 10. Gate 0 conditions

| Condition | Result |
|---|---|
| Required artifacts exist | PASS |
| SHA-256 hashes verify from the directory implied by the freeze record | PASS |
| Machine-readable companion is valid | PASS |
| Human and machine rules do not materially conflict | PASS |
| The operating prompt does not weaken the constitution | PASS |
| No frozen file was modified during verification | PASS |
| Live trading remains locked | PASS (locked) |

---

## 11. Disclosure — environment activity during this session

Recorded so that the Stage 1 prospective freeze cannot later be claimed to have been made in
ignorance of information already seen. Nothing below inspected any strategy result.

| Action | Detail | Contamination assessment |
|---|---|---|
| Toolchain inventory | Python 3.10.6, pip 26.1.2, git 2.54.0 detected; installed packages listed (numpy 2.2.6, pandas 2.3.3, requests 2.34.2, pytest 8.4.2, yfinance 1.4.1 present; `exchange_calendars`, `scipy`, `alpaca` absent) | none |
| Package installation | `exchange_calendars` 4.13.2 installed into the user's existing Python 3.10 environment (free, open source, no purchase). Purpose: an independent NYSE session calendar for Stage 1 validation | none; additive install, no user file removed |
| Provider reachability probe — Stooq | `GET stooq.com/q/d/l/?s=spy.us&i=d` returned HTTP 200 with an anti-bot HTML page, not CSV; a dated variant returned HTTP 404. Conclusion recorded: Stooq is **not** usable as an automated no-key provider from this environment | none; no price data obtained |
| Provider reachability probe — Yahoo via `yfinance` | 8 SPY daily bars for 2024-01-02..2024-01-11 retrieved to confirm reachability and column schema (`Open, High, Low, Close, Adj Close, Volume, Dividends, Stock Splits, Capital Gains`, tz `America/New_York`). Three of those rows were displayed | Dates fall inside what will become the **validation** window, not the final holdout (holdout begins 2024-08-01 under §6.1 arithmetic). No strategy, signal, parameter, or performance figure was computed. Recorded as a descriptive schema probe |
| Credential scan | Environment scanned for variable **names** matching `ALPACA|APCA|TRADING`; none present. No value was read or printed. `~/.alpaca` absent, project `.env` absent | none |

Consequence for Stage 1: the provider-availability facts above are already known and must be stated
as *inputs* to the Stage 1 data-source decision rather than presented as a discovery made after
freezing. Stage 1 must declare its provider and fallback policy in writing, hash that declaration,
and only then acquire data.

---

## 12. Verdict

`PASS — STAGE_0_CONSTITUTION_VERIFIED`

Constitutional equivalent (unchanged, not re-issued): `PASS — STAGE_0_CONSTITUTION_FROZEN`.

Next authorized activity: **Stage 1 — data-source decision, universe freeze, acquisition protocol,
data validation, and holdout lock.** No strategy backtest is authorized before Gate 1 passes.
