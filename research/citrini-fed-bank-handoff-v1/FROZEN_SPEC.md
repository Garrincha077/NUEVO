# Citrini Fed → Bank Handoff v1 — frozen incremental research gate

Status: **FROZEN BEFORE RESULTS / RESEARCH ONLY / NOT PROMOTED**

## Purpose

Test the narrow regime hypothesis discussed from Citrini Research: a shrinking Federal Reserve balance sheet need not equal tightening when commercial-bank balance sheets are expanding at the same time. The candidate state is called **PRIVATE_HANDOFF**.

This research asks only whether that state adds stable forward information beyond the already-promoted GMLI Money predictors. It does not change Liquidity Context, Money Core, Funding, Fiscal, Market Confirmation, conviction points or production allocation logic.

## Fixed handoff construction

### Fed balance sheet
- Source: FRED `WALCL`, Total Assets: Total Assets (Less Eliminations from Consolidation), weekly.
- Monthly endpoint: latest weekly observation in each calendar month.
- Fed 13W change: percentage change versus the latest observation on or before approximately 91 calendar days earlier.

### Commercial-bank balance sheet
- Source: Federal Reserve H.8 Data Download Program `B1151NCBA`, the official-source all-commercial-bank total-assets history used by prior Liquidity Context research when the long FRED transfer proved less reliable in CI.
- Monthly endpoint: latest weekly observation in each calendar month.
- Bank 13W change: percentage change versus the latest observation on or before approximately 91 calendar days earlier.

### State
For months where both changes exist:
- `BROAD_EASING`: Fed 13W > 0 and Bank 13W > 0
- `PRIVATE_HANDOFF`: Fed 13W < 0 and Bank 13W > 0
- `TRUE_TIGHTENING`: Fed 13W < 0 and Bank 13W < 0
- `FED_OFFSET`: Fed 13W > 0 and Bank 13W < 0
- `MIXED_FLAT`: either change is exactly zero

No volatility threshold, smoothing, alternate window, lag, sign flip or state relabeling may be introduced after results.

The candidate predictor is fixed to the binary variable `private_handoff = 1` only in `PRIVATE_HANDOFF`, otherwise 0. The research sign hypothesis is **positive/supportive**.

## Conservative availability

Both weekly balance-sheet series are converted to a monthly state and treated as investable only with a **one-month lag**. Thus state month `t` may enter a forecast whose return starts in month `t+1`.

This is deliberately more conservative than attempting to reconstruct exact historical weekly publication timestamps. Histories are current revised histories, not exact real-time vintages.

## Fixed Money baselines and asset horizons

Reuse exactly the six already-promoted Money transmission relationships — no new asset/horizon search:

1. `SPY_USD_ACCEL3_12M` — SPY, USD Money accel3, 12M
2. `QQQ_USD_ACCEL3_12M` — QQQ, USD Money accel3, 12M
3. `GLD_FXN_ACCEL3_12M` — GLD, FX-neutral Money accel3, 12M
4. `DBC_USD_LEVEL_6M` — DBC, USD Money level, 6M
5. `DBC_USD_LEVEL_12M` — DBC, USD Money level, 12M
6. `DBC_FXN_LEVEL_6M` — DBC, FX-neutral Money level, 6M

Money history: `research/global-money-v2/latest/global_money_v2.csv`.

Money publication lag remains **1 month**, matching the promoted transmission contract.

## Market data and outcome

- Exact tickers: `SPY`, `QQQ`, `GLD`, `DBC`.
- Source: Yahoo Finance monthly adjusted close.
- Current incomplete month excluded.
- Outcome: forward log adjusted return over each relation's already-promoted horizon.

No return-horizon, ticker or return-transformation search is allowed.

## Fixed train / OOS split

- Train signal months: `2015-01` through `2022-12`.
- OOS signal months: `2023-01+`.

The decision/start month is signal month + 1 month. Forward returns start there.

## Fixed model comparison

For each of the six relations:

Baseline:
`forward_return ~ const + standardized Money predictor`

Candidate:
`forward_return ~ const + standardized Money predictor + private_handoff`

Standardization parameters are estimated on train only. Candidate coefficients are estimated on train only and frozen for OOS prediction.

Because forward returns overlap, candidate train inference uses Newey-West/HAC with `maxlags = horizon_months - 1`.

## Fixed relation-level diagnostics

For every relation report:
- train private-handoff coefficient and HAC p-value;
- OOS baseline and candidate RMSE/SSE;
- OOS incremental R² relative to baseline: `1 - SSE_candidate / SSE_baseline`;
- OOS prediction Pearson for baseline and candidate;
- fixed non-overlap phase diagnostics: rows partitioned by decision-month index modulo the horizon; each phase reports baseline vs candidate SSE and incremental R²;
- OOS mean forward return in PRIVATE_HANDOFF vs all other states as a descriptive diagnostic only.

## Frozen family gate

`PROMOTION_CANDIDATE` requires **all** of the following:

1. Positive train private-handoff coefficient in at least **4 of 6** promoted relations.
2. Positive OOS incremental R² in at least **4 of 6** relations.
3. Median OOS incremental R² across the six relations > 0.
4. Candidate OOS prediction correlation is not worse than baseline in at least **4 of 6** relations.
5. Across all fixed non-overlap relation-phase cells with data, candidate wins strictly more than 50% and median phase incremental R² > 0.

HAC p-values are reported but are **not** a family pass threshold because the six relations share assets/horizons and this gate is about stable incremental prediction, not a new multiple-testing significance claim.

Any failed gate condition forces `STOP_RESEARCH_DIAGNOSTIC`.

## Interpretation guard

Even `PROMOTION_CANDIDATE` would **not** promote the signal. It would only justify a later, separately frozen promotion protocol and a live diagnostic implementation review.

If this gate returns `STOP_RESEARCH_DIAGNOSTIC`, do not optimize the 13W window, threshold, sign, asset set, horizon set, state mapping or subperiods to rescue the result. The handoff concept may remain descriptive macro context, but it gets no GMLI score or weight.

## Evidence boundaries

- Evidence tier: `RESEARCH_DIAGNOSTIC`.
- `scoring_effect = NONE`.
- `automatic_weight_change = 0`.
- `methodology_effect = NONE`.
- CORE / OVERLAY / RESEARCH separation remains unchanged.
