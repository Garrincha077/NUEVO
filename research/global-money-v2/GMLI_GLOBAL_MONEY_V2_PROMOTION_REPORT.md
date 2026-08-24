# GMLI Global Money V2 — Promotion Gate Report

Date: 2026-08-24
Candidate: `GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL`
Evidence tier at time of report: `RESEARCH_PROMOTION_CANDIDATE`
Gate status: **PASS — PRODUCTION INTEGRATION REVIEW**

## Decision

**Recommendation: promote this explicitly versioned Money V2 candidate to the prospective production Money Core, subject to a separate production-integration PR, frozen/version guards, Vercel deployment, and endpoint smoke tests.**

This report does **not** itself modify `lib/state.js` or production Core.

The historical v1.8b exact-rerun result remains unchanged:

`BLOCKED_MISSING_FROZEN_INPUT_BYTES`

Money V2 is a new audited production-source version. It is not presented as recovery or reconstruction of the missing historical frozen bytes.

## Why the gate passes

1. The seven-region Money construction remains the documented production architecture: US/CN/EA/JP/GB/CA/AU, prior-year USD money-level share weights, local and USD-translated channels, 1M publication lag, rolling 120M z with 36M minimum and population variance, and score `50 + (50/3)*z`.
2. China 2015+ accounting levels come from official PBoC Money Supply HTML history with preserved source bytes and SHA-256 provenance.
3. The 2015 train start is preserved without pretending to recover a missing 2014 observed series. The 2014 China rows are explicitly `ACCOUNTING_SEED_ONLY`, `observed_stock: false`, derived from the exact 2015 precision level and official PBoC published comparable YoY for the same month.
4. The May-2026 bridge convention regression passes very closely against the prior v1.8 benchmark.
5. All six previously promoted transmission relationships retain the required direction in train and OOS under a fixed protocol with no asset, horizon, lag or parameter search and no new FDR claim.

## Source / comparable-base gate

Status: `PASS_CONTINUOUS_OFFICIAL_V2_SOURCE_WITH_COMPARABLE_BASE_SEED`

China history used by the candidate:
- 2015-01 onward: precise official PBoC Money Supply HTML levels.
- 2015 published YoY: official PBoC Financial Statistics reports. March/June/September/December use only the corresponding Q1/H1/Q3/annual period report and require the requested month-end balance sentence.
- 2014: comparable accounting base only, derived as:

`implied_2014_base_m = precise_2015_level_m / (1 + official_2015_yoy_m / 100)`

The comparable-base layer has 12/12 months, uses only official PBoC components, is not an observed stock history, and is not a historical exact rerun.

## Global Money V2 bridge regression

May 2026:

| Channel | Legacy bridge | Money V2 | Delta |
| --- | ---: | ---: | ---: |
| USD YoY | 9.3258% | 9.341915% | +0.016115 pp |
| FX-neutral YoY | 6.1275% | 6.153468% | +0.025968 pp |

Convention regression: **PASS**.

## Latest decision-eligible Money V2 observation

Observation month: **2026-06**  
Available date under the frozen 1M publication lag: **2026-07-31**

- USD Money YoY: **7.956975%**
- USD z: **+0.306729**
- USD score: **55.1121**
- FX-neutral Money YoY: **5.946277%**
- FX-neutral z: **-0.330721**
- FX-neutral score: **44.4880**
- FX effect: **+2.010698 pp**

Interpretation at the Money-only level: USD and FX-neutral channels are no longer sharply divergent in regime classification; both sit inside the broad 40–60 neutral band, with USD mildly positive and FX-neutral mildly soft.

## Fixed transmission-transfer gate

Protocol:
- Train signal months: 2015-01 through 2022-12.
- OOS signal months: 2023-01 onward.
- Publication lag: 1 month.
- Returns: forward log returns from exact-ticker Yahoo monthly adjusted closes.
- No asset search.
- No horizon search.
- No lag search.
- No parameter search.
- No new FDR-family claim.
- PASS rule: positive train Pearson + positive OOS Pearson + positive OOS Spearman for every preselected relation.

Result: **6/6 PASS**.

| Frozen relation | Train Pearson | OOS Pearson | OOS Spearman | Result |
| --- | ---: | ---: | ---: | --- |
| SPY USD accel3 12M | +0.447331 | +0.361302 | +0.335887 | PASS |
| QQQ USD accel3 12M | +0.389688 | +0.566297 | +0.558871 | PASS |
| GLD FX-neutral accel3 12M | +0.087184 | +0.590323 | +0.565726 | PASS |
| DBC USD level 6M | +0.589183 | +0.632397 | +0.543148 | PASS |
| DBC USD level 12M | +0.634025 | +0.634434 | +0.593548 | PASS |
| DBC FX-neutral level 6M | +0.627034 | +0.707962 | +0.684922 | PASS |

### Reading the transfer result

The most important result is not that every coefficient is large; it is that the precommitted transmission map survives the source/version migration without retuning. DBC remains the strongest and most consistent Money-transmission family. QQQ remains strong OOS. SPY remains positive. GLD keeps the historically weak train Pearson relationship but retains strong positive OOS Pearson/Spearman, so its behavior is not a new weakness introduced by V2.

## Promotion boundary

This report authorizes only the next controlled step: **production integration review**.

A production promotion must:
1. preserve the old 2026-02-28 Core as historical reference/audit state rather than erase it;
2. introduce Money V2 as an explicit new Core version, not silently overwrite provenance;
3. keep the historical v1.8b blocker visible;
4. update frozen/version guards to test both historical reference integrity and the new active Core contract;
5. deploy to the existing `gmli-fred-dashboard` Vercel project;
6. smoke at minimum `/api/status`, `/api/report`, `/api/money-nowcast`, and `/api/decision`;
7. call V2 production only after all smoke tests pass.

## Evidence classification after this report

- Historical 2026-02-28 Money Core: **CORE / HISTORICAL REFERENCE** until production promotion completes.
- `GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL`: **RESEARCH / PROMOTION_GATE_PASS** until production integration and smoke complete.
- Historical v1.8b candidate: **RESEARCH / BLOCKED_MISSING_FROZEN_INPUT_BYTES**.

No overlay or research signal is promoted by this report.
