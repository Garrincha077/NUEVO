# GMLI Accord Watch v1 — frozen construction

Status: **FROZEN BEFORE FIRST RESULT**  
Evidence tier: **RESEARCH_DIAGNOSTIC**  
Scoring effect: **NONE**  
Automatic weight change: **0**  
Methodology effect: **NONE**

## Purpose

Track whether the hypothesized Treasury–Fed "Accord 2.0" / financial-repression setup is actually beginning to materialize.

This is **not** an assumption that an Accord exists and **not** a new macro score. It is a compact state machine that answers:
1. is Treasury reducing private-sector duration pressure;
2. is the Fed/reserve system becoming more supportive;
3. is the bond market confirming through lower/stable real-yield and term-premium pressure;
4. what asset exposures would be mechanically helped or hurt if the state progresses.

The existing GMLI Money Core remains the baseline liquidity regime. Accord Watch cannot override Money, Funding, Fiscal, Market Confirmation or the frozen 10-point conviction rubric.

## Pareto design

V1 intentionally uses only three blocks.

### A. Treasury duration-supply pressure proxy
Source: U.S. Treasury Fiscal Data — MSPD Table 1, debt held by the public, standard marketable classes.

- short/floating = Bills + FRNs
- fixed duration = Notes + Bonds + TIPS
- compare latest month with approximately 3 months earlier
- `fixed_duration_share_change_3m_pp = latest fixed-duration share - prior fixed-duration share`

Classification:
- `< 0` → `SUPPORTIVE` (less fixed-duration share pressure)
- `> 0` → `RESTRICTIVE`
- `= 0` → `NEUTRAL`

This is a **stock-change composition proxy**, not DV01, weighted-average maturity, true net issuance or a buyback-flow measure. Do not represent it as such.

### B. Fed / reserve support
Source: Federal Reserve H.4.1 Data Download Program.

Series:
- total Federal Reserve assets, Wednesday level (`RESPPA_N.WW`)
- reserve balances with Federal Reserve Banks, Wednesday level (`RESH4R_N.WW`)

For each, calculate the fixed 13-week percentage change using the nearest observation on or before 91 days earlier.

Classification:
- total assets `>= 0` and reserve balances `>= 0` → `SUPPORTIVE`
- total assets `< 0` and reserve balances `>= 0` → `RESERVE_CUSHION`
- total assets `>= 0` and reserve balances `< 0` → `MIXED`
- total assets `< 0` and reserve balances `< 0` → `RESTRICTIVE`

`SUPPORTIVE` and `RESERVE_CUSHION` count as supportive policy/mechanism evidence. No threshold search is allowed.

### C. Market yield-suppression verdict
Two independent inputs:

1. 10-year Treasury real par yield from U.S. Treasury Daily Treasury Par Real Yield Curve Rates.
2. 10-year nominal term premium from the Federal Reserve Board three-factor nominal term-structure model (Kim-Wright implementation).

For each series compare the latest observation with the nearest observation on or before 91 days earlier.

Classification:
- both 3M changes `<= 0` → `CONFIRM`
- both 3M changes `> 0` → `REJECT`
- otherwise → `MIXED`

The Board term-premium model is a staff research product, not an official statistical release, and may be revised. Accord Watch uses it only as a market-diagnostic input.

## Frozen state machine

Let Treasury supportive = block A `SUPPORTIVE`.

Let Fed/reserve supportive = block B in `{SUPPORTIVE, RESERVE_CUSHION}`.

States:
- `REPRESSION` = Treasury supportive AND Fed/reserve supportive AND market `CONFIRM` AND latest 10Y real yield `< 0%`.
- `EMERGING` = Treasury supportive AND Fed/reserve supportive AND market `CONFIRM`, without the negative-real-yield condition.
- `SETUP` = at least one of Treasury supportive or Fed/reserve supportive, but `EMERGING`/`REPRESSION` conditions are not met.
- `HYPOTHESIS_ONLY` = neither Treasury nor Fed/reserve block is supportive.

A market `REJECT` never permits `EMERGING` or `REPRESSION`; it is shown explicitly as a conflict inside `SETUP` or `HYPOTHESIS_ONLY`.

No numeric 0–100 Accord score is produced.

## Bond interpretation

V1 must keep two bond concepts separate:

- `DURATION_PRICE_SUPPORT`: tactical support for nominal Treasury prices when policy/mechanism support is present and market yield pressure is confirming.
- `REAL_BOND_VALUE`: simply report whether the observed 10Y real yield is `POSITIVE_REAL_YIELD`, `ZERO_REAL_YIELD` or `NEGATIVE_REAL_YIELD`; do not convert this into an allocation score.

This permits a valid reading such as: long nominal Treasuries tactically supported while real long-run value is poor.

## Asset map — interpretation only

This map is a scenario interpretation, not empirical promotion and not a trading signal.

- GLD: strongest positive sensitivity as Accord progresses, especially if real yields fall.
- TIPS: positive as repression risk rises.
- 2–5Y Treasuries: positive when Fed/reserve support increases and rate pressure eases.
- 10–30Y nominal Treasuries: tactical price support when duration pressure/term premium fall; structural real-value risk rises if real yields become negative.
- QQQ: positive when real yields/term premium fall; conditional on inflation not destabilizing growth/discount rates.
- SPY: moderately positive through easier financial conditions.
- BTC: RESEARCH-only high-beta monetary-debasement beneficiary; never CORE transmission.
- DBC: conditional; Accord alone is insufficient. Needs separate reflation / weaker-USD confirmation.
- USD: conditional negative bias only once repression/liquidity evidence becomes broad; no hard signal in v1.

Only SPY, QQQ, GLD and DBC retain their existing promoted Money-transmission status. Accord Watch does not promote BTC, TIPS, Treasury duration buckets or USD.

## Guardrails

- CORE / OVERLAY / RESEARCH separation is mandatory.
- no score or conviction points;
- no automatic portfolio weights;
- no parameter, threshold, lag, horizon, asset or subperiod optimization;
- source failure → block `UNAVAILABLE`; never impute a supportive state;
- if any required block for `EMERGING`/`REPRESSION` is unavailable, fail closed to at most `SETUP`/`HYPOTHESIS_ONLY` with incomplete-data flag;
- Treasury stock-change proxy must not be described as true issuance flow;
- a future true issuance/buyback-flow model must be a separately versioned candidate.

## Refresh cadence

The diagnostic may rebuild daily, but source economics differ:
- MSPD: monthly;
- H.4.1: weekly;
- Treasury real yields: daily;
- Fed term-premium model: generally weekly.

Daily rebuild does not imply daily change in all blocks.
