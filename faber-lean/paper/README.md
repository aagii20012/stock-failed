# Faber sector rotation — hosted paper trading

Runs the verified Faber sector rotation against **Alpaca's paper API**, on a free GitHub
Actions cron. Same signal, different execution environment.

> **Paper only.** `paper_trade.py` constructs its trading client with `paper=True` and
> asserts the resolved base URL contains `paper-api.alpaca.markets` before sending
> anything. Live Alpaca keys do not authenticate against the paper endpoint, so there is
> no credential you can supply that makes this script trade real money. It also never
> touches [stockedge100/](../../stockedge100/).

## The signal is the tagged one, and that is tested

`faber_signal.py` is the strategy: top-3 of the 9 SPDR sector ETFs by 12-month momentum,
each slot held only while that sector's last completed monthly close is above its own
10-month SMA, failing slots routed to SHY.

`test_signal_parity.py` replays every rebalance in `../rebalance_log.csv` — the decision
record from tag `baseline-v1-faber-verified` — through the live `decide()` function:

```
replayed         : 236 rebalances
slots            : 708
skips            : 83 (11.7%)
fully defensive  : 11
mismatches       : 0
```

Those first four lines match the tag message exactly. Nothing in `faber_signal.py` may
change without re-running this.

It needs `../prices.csv`, which is gitignored derived vendor data, so it is skipped in CI
and must be run locally. Regenerate its inputs with `python local_backtest.py` from
`faber-lean/`.

---

## What you have to do by hand

Four steps. Roughly ten minutes. Nothing here needs a key pasted into a chat window.

### 1. Create an Alpaca paper account

Sign up at <https://alpaca.markets/> and open the **Paper Trading** dashboard
(<https://app.alpaca.markets/paper/dashboard/overview>). A paper account is funded with
$100,000 of fake money by default; no bank link, no identity verification, no funding step
is required to paper trade. Do not complete a live-account application — this setup has no
use for one.

### 2. Generate paper API keys

In the paper dashboard, right-hand panel → **API Keys** → **Generate New Key**. You get
two values:

| Alpaca shows it as | This is |
|---|---|
| `API Key ID` | the public identifier, e.g. `PK...` |
| `Secret Key` | shown **once**, at generation time |

Copy them straight into GitHub in the next step. If you lose the secret, regenerate the
pair — it cannot be re-displayed.

Confirm the key ID starts with `PK`. Live keys start with `AK`, and a live key here would
simply fail to authenticate rather than trade — but there is no reason to find that out.

### 3. Add them as GitHub repository secrets

In this repository: **Settings** → **Secrets and variables** → **Actions** →
**Secrets** tab → **New repository secret**. Create exactly these names — the workflow
reads them by name and nothing else:

| Secret name | Value | Required |
|---|---|---|
| `ALPACA_API_KEY_ID` | the `API Key ID` from step 2 | **yes** |
| `ALPACA_API_SECRET_KEY` | the `Secret Key` from step 2 | **yes** |
| `WEBHOOK_URL` | a Discord or Slack incoming webhook URL | no |

Leave `WEBHOOK_URL` out unless you want it; the script skips the ping when it is unset.
`GITHUB_TOKEN` is **not** something you create — Actions injects it automatically.

Secrets are write-only once saved: GitHub will let you overwrite a secret but never
display it, and it masks the value in workflow logs. `paper_trade.py` checks these two by
name only and never prints, logs, or writes either value.

### 4. Get the workflow onto the default branch

**This is the step that is easy to miss.** GitHub only fires `on: schedule` for workflow
files that exist on the repository's **default branch**. This work is on
`faber-sector-rotation`; the default branch is `main`. Until the workflow file reaches
`main`, the cron will never run — `workflow_dispatch` from the Actions tab will still work
on any branch, so you can test it first.

```bash
git checkout main
git merge faber-sector-rotation
git push origin main
```

Then, before waiting on the cron: **Actions** → **Faber paper trade** → **Run workflow**,
with `dry_run` checked. That proves the keys, the data feed and the calendar all work
without sending an order.

One standing caveat: GitHub **disables scheduled workflows after 60 days with no repository
activity** and emails you when it does. This job commits its own log on any run that
changes it, which counts as activity — but a long stretch of `SKIPPED`-only runs writes
nothing. If it goes quiet, check the Actions tab for a "workflow disabled" banner and
re-enable it there.

---

## Checking on it from your phone

**Recommended, and already wired: GitHub issues + the GitHub mobile app.** Zero new
accounts, no webhook to manage, and the notification is a real push.

The workflow opens an issue assigned to you whenever something happened — a rebalance, a
deferral, a rebalance day with no usable signal, or an error. Being *assigned* is what
triggers the mobile push; plain repository activity does not, by default. Install **GitHub
Mobile** (iOS / Android), sign in, and leave notifications on. Each issue body is the full
run summary: target weights, the momentum ranking, which slots the trend filter sent to
SHY, the orders, and links to the workflow run and your Alpaca dashboard. Close them as
you read them; they are labelled `faber-paper`, so `is:issue label:faber-paper` is your
history.

Routine "nothing to do today" runs do **not** notify. They are still recorded — see below.

**Optional: Discord or Slack.** If you already have a server or workspace, create an
incoming webhook and store the URL as `WEBHOOK_URL`. The script detects which service from
the URL and posts a one-paragraph version of the same summary. It is additive, never
fatal: a failed ping is logged and the run still succeeds. Set up nothing here if you do
not already have one — the issue route covers it.

## Where the record lives

Three places, deliberately overlapping:

- **`paper_log.csv`** — one committed row per run, every run. This is the durable history.
  Columns include the action, the signal month, the ranking, the skips, target weights,
  per-sector momentum, the per-sector trend test, equity, cash, positions at run start,
  the orders, and which data feed answered.
- **`state.json`** — committed. What the next run needs to know: the last traded signal
  month, the orders it submitted (so the following run can confirm the fills), and any
  deferral.

### The signal is recorded every run, not only on rebalance days

The strategy trades once a month, so for roughly twenty of every twenty-one runs there is
nothing to do. Those runs still fetch the bars and compute the full decision — the
momentum of all nine sectors, each one's trend test, the resulting top-3 and target
weights — and write it to the log without acting on it. `rebalance_day` stays `False`
and no order is ever built, so this changes what is recorded and nothing about what is
traded.

The reason is that the outcome columns are silent when the strategy is idle. Between a
cold start and the first trading day of the next month the account is flat, and `equity`
repeats the same opening balance every day; that stretch of rows says only "still
waiting". The signal columns turn the same rows into a daily series that can be diffed
against the backtest's decision log before a single fill exists, and a ranking that drifts
from the reference shows up on the day it drifts rather than at the next rebalance.

Two properties keep this from touching the trading path. The bars are fetched **once** and
the rebalance, when there is one, is computed from that same read — so the row records
the decision that was executed, not a second look at the data taken moments later. And an
observation is allowed to fail: if the data feed is unavailable on a non-rebalance day the
run notes `signal not observed: …` and reports the action it actually took, because a
day with nothing to trade must not be able to go red over telemetry. On a rebalance day
the same failure is still a hard `ERROR`.

`momentum` and `trend_ok` were added to `LOG_FIELDS` after the log already had rows in it,
so `append_log()` rewrites a file whose header is narrower than the current one, padding
the earlier rows. Appending wide rows under a narrow header would still parse — which
is exactly why it would have gone unnoticed until someone read the series back.
- **The run summary** — rendered into the Actions run page (`$GITHUB_STEP_SUMMARY`), the
  notification issue, and a 90-day artifact with the raw `run_result.json`.

The commit step stages **explicit paths only**, never `git add -A`: this repository also
holds the frozen `stockedge100/` tree and an unreviewed `_scratch/` directory, and a
blanket add here has swept unreviewed files into a commit before.

## Actions the run can report

| Action | Meaning | Notifies |
|---|---|---|
| `REBALANCED` | Orders computed and submitted (or, under `--dry-run`, computed only) | yes |
| `HELD` | Rebalance day, but the target is already held — or this month's signal was already traded | on a rebalance day |
| `SKIPPED` | Not a trading day, not a rebalance day, or no usable signal | only when a rebalance day yielded no signal |
| `DEFERRED` | Rebalance was due but the run fired after the market-on-close window closed | yes |
| `ERROR` | Anything raised. The job also fails, so the Actions run shows red | yes |

### The trigger is keyed on the signal month, not the date

Because GitHub Actions can delay a scheduled run by tens of minutes — or drop it entirely
under load — a date-keyed "rebalance if today is the 1st trading day" would silently skip
a whole month, which the backtest never does. `rebalance_trigger()` instead asks whether
*this month's signal has been traded yet*:

- **First trading day of the month** → rebalance. The normal path.
- **Already traded this month's signal** → hold. A re-run or a re-dispatch cannot trade
  the same signal twice.
- **Later in the month, signal still untraded** → catch up, and say so in the notes and
  the notification. Trading a few days late is a real deviation from the verified fill
  bar, but it is a much smaller one than skipping the month.
- **Cold start, mid-month** → do nothing. Entering on whatever date you happened to deploy
  is an arbitrary entry the backtest never takes, so it is opt-in: dispatch with
  `force_rebalance`, or wait for the 1st.

Three independent layers stop a double trade: the `concurrency` group in the workflow, the
signal-month check above, and a deterministic `client_order_id`
(`faber-<date>-<symbol>-<side>`) that Alpaca itself rejects as a duplicate.

---

## Behaviour differences vs the LEAN backtest

The signal is identical and tested. Everything below is *execution*. Ordered by how much
it can move the result.

### 1. Fill timing — matched on purpose

This is the one that mattered most, and the port reproduces the backtest rather than
diverging from it.

On daily data LEAN converts market orders to MarketOnClose: all **726/726** fills of the
verified backtest landed on the **close of the first trading day of the month**, not at
the scheduled 10:00-ish time. `paper_trade.py` submits `TimeInForce.CLS`, which routes to
the same closing auction on the same day. Alpaca accepts CLS any time before 15:50 ET, so
a 15:00 UTC cron has five to six hours of slack — even an hour-late run still gets the
right bar.

**Consequence for expectations:** the number to hold this against is the LEAN one. CAGR
**9.32%**, Sharpe vs SHY **0.537**, max drawdown **−24.75%**. Not the pandas harness's
−22.58%, which trades a day earlier and is therefore flattered on de-risking moves. A
naive `market`/`day` port would have filled around 10:00 ET — neither implementation's bar
— so this is a difference actively avoided rather than one introduced.

### 2. Sizing price is not the fill price

LEAN sized and filled on the same close, because it had the bar in hand. Here the run
sizes at the latest trade available mid-morning, then the order fills at the close six
hours later. Whatever the market does in between shows up as weight error. It is
self-correcting — next month's rebalance diffs against actual positions — but expect
realized weights to sit slightly further from 33.3% each than the backtest's did.

### 3. Whole shares, no fractional

Alpaca's fractional trading supports `DAY` time-in-force only; a fractional CLS order is
rejected. So sizing floors to whole shares, matching LEAN's whole-share quantization. A
0.25% cash buffer (LEAN's own `FreePortfolioValuePercentage` default) keeps the flooring
from over-committing.

Scale-dependent: on a $100k paper account a one-third slot is thousands of dollars and
rounding is noise. On a small account it is not — a $2k account cannot express a third of
itself in whole shares of a $290 ETF without meaningful error.

### 4. Auction risk that the backtest does not model

LEAN filled every order, always. A real closing-auction order can be rejected, or in
principle go unfilled, if the symbol is halted or the auction is unbalanced. Alpaca also
will not let you cancel an MOC order after 15:50 ET. The script records each rejection
with its reason, keeps going with the rest, and the next rebalance re-diffs toward target
— so a rejection costs tracking error, not correctness.

### 5. Dividends and splits are real now

The backtest ran on back-adjusted closes, which behave as though every dividend were
reinvested instantly and continuously. The paper account gets actual cash dividends that
sit idle until the next rebalance reinvests them, and actual split ratios applied to share
counts. SHY and XLU are the ones that will show it. This is *more* realistic than the
backtest, not less, and it is a small persistent drag relative to it.

### 6. A different data vendor

The backtest ran on yfinance `auto_adjust=True` closes. Live runs pull Alpaca SIP
consolidated daily bars with `adjustment=all`. Both are split- and dividend-adjusted, but
not by identical methodology, so in a near-tie month the two could rank sectors 3 and 4
differently, or disagree on a close sitting within a hair of its 10-month SMA. Unlikely to
matter often; impossible to rule out.

The free Basic plan serves SIP history for data older than 15 minutes, so the run asks for
bars up to 25 minutes ago. If SIP is refused it degrades SIP → delayed-SIP → IEX and
**records which feed answered** in the log. An IEX-only fallback means single-venue closes
rather than consolidated ones — worth noticing in the log if a decision ever looks odd.

### 7. Rebalance-day definition

LEAN used `date_rules.month_start(SPY)`. Here it is the first entry in Alpaca's
`/v2/calendar` for the month, i.e. NYSE. In practice the same day; both treat an early
close as a trading day.

### 8. Scheduler reliability has no backtest analogue

Covered above. Catch-up trades late rather than not at all; the log and notification say
which happened.

---

## Files

| File | |
|---|---|
| `faber_signal.py` | The strategy. Pure — no network, no broker, no clock. Do not change without re-running the parity test. |
| `paper_trade.py` | Execution shell: calendar, data, sizing, orders, logging, notification. |
| `test_signal_parity.py` | Replays the 236-rebalance tagged log through `decide()`. Local only. |
| `test_execution.py` | 17 tests needing no keys, no network, no price cache. This is what CI gates on. |
| `requirements.txt` | Pinned, so a scheduled job cannot change behaviour on its own. |
| `paper_log.csv`, `state.json` | Written by runs and committed. Not in the repo until the first run. |
| [`../../.github/workflows/faber-paper.yml`](../../.github/workflows/faber-paper.yml) | The schedule. |

## Running it locally

```bash
cd faber-lean/paper
pip install -r requirements.txt

# No keys, no network: signal only, from the backtest's own price cache.
python paper_trade.py --offline ../prices.csv --dry-run

# Any past month, to sanity-check against rebalance_log.csv.
python paper_trade.py --offline ../prices.csv --asof 2020-04-01 --dry-run

# With keys in the environment: everything except order submission.
python paper_trade.py --dry-run

# Tests.
python -m pytest -q                  # both suites
python test_signal_parity.py         # parity, with the summary report
```

Other flags: `--force-rebalance`, `--cash-buffer`, `--log`, `--state`, `--result`.

Environment variables read: `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY`, `WEBHOOK_URL`,
and Actions' own `GITHUB_STEP_SUMMARY`. Presence is checked by name; values are never
printed.

## Not resolved by this setup

The open finding from the backtest stands and paper trading will not settle it: the
momentum ranking showed **no selection skill** over 2007–2026 — CAGR flattened at top-N=3
while Sharpe and drawdown improved monotonically with N, and 0 of 48 swept configurations
beat SPY's 11.02%. That sweep ran at a cost model since found to be ~6.7× too harsh, so
its absolute CAGRs are understated and the SPY comparison needs re-running at ~1.5 bps
before anything is concluded from it. See [`../README.md`](../README.md).

A few months of paper trading is far too short a sample to say anything about that. What
it does test is the plumbing: that the signal fires on the right day, sizes sanely,
survives real corporate actions and a real broker, and reports what it did.
