# GMLI Fiscal V2 Promotion Report

Status: **PASS_FOR_PRODUCTION_INTEGRATION**  
Promotion target: `GMLI_FISCAL_V2_DEFICIT_IMPULSE`  
Evidence tier after promotion: **OVERLAY**  
Date: 2026-08-25

## Decision

Promote `GMLI_FISCAL_V2_CANDIDATE_1` as a refreshable Fiscal confirmation overlay, subject to fail-closed refresh, last-good preservation, Data Health integration, CI guards and production endpoint smoke.

This does **not** modify Money Core or Funding V2 and does not silently add Fiscal to the existing 10-point global conviction rubric.

## Why legacy reverse-engineering stopped

The preserved production Fiscal reading is July 2026 `STRICT_ACTUAL_RELEASE`, score `52.539556447652046`, z `0.1523733868591229`, regime `NEUTRAL`.

Production and the prospective source archive confirm that exact historical strict-release runner/vintages were not recovered. Current revised FRED history therefore cannot honestly be substituted and called an exact rerun.

The legacy reading is preserved as a historical reference. Fiscal V2 is a separately versioned construction.

## Frozen Candidate 1 construction

- monthly source: `MTSDS133FMS`
- denominator: nominal `GDP`
- component 1: TTM federal deficit / nominal GDP
- component 2: 12M change in deficit/GDP (fiscal impulse)
- rolling z-score window: 120 months
- minimum history: 24 months
- component z clip: [-3, +3]
- equal weights: 50/50
- score: `clip(50 + (50/3) * composite_z, 0, 100)`
- regimes: `<40 RESTRICTIVE`, `40–60 NEUTRAL`, `>60 SUPPORTIVE`

Debt, federal interest payments, receipts and expenditures remain diagnostics only and are not added as extra scoring weights.

Historical research uses revised FRED history with conservative frozen publication lags; it is not represented as exact historical release-time data.

## Fixed construction sanity

PASS.

Predeclared pandemic sanity:
- 2020-06 expected `SUPPORTIVE`
- actual `SUPPORTIVE`
- score `100.0`

Latest eligible Candidate 1 reading as of 2026-08-25:
- observation month: 2026-06
- available date: 2026-07-31
- TTM deficit: $1.805T
- deficit/GDP: 5.5566%
- fiscal impulse: -0.6669 pp YoY
- composite z: -0.24550
- score: **45.9084**
- regime: **NEUTRAL**

Legacy comparator is also NEUTRAL, score 52.5396. The 6.63-point difference was reported and not tuned away.

Frozen audit: `research/fiscal-v2/CANDIDATE_1_RESULT.json`.

## Narrow usefulness gate

PASS 1/1 on the single predeclared primary relation.

### SPY 12M — primary

- train n=62, Pearson **+0.306755**
- OOS n=30, Pearson **+0.446855**
- OOS Spearman **+0.486096**
- direction PASS

Protocol was frozen before empirical execution. Fiscal observation `t` is treated as available at month-end `t+1`; the return window starts at monthly adjusted close in `t+2`.

There was no asset, horizon, lag, component, weight, threshold or subperiod search and no FDR claim.

Frozen gate: `research/fiscal-v2-usefulness-gate.json`.  
Frozen result: `research/fiscal-v2/USEFULNESS_RESULT.json`.

## Secondary diagnostics

These cannot change promotion PASS/FAIL:

- QQQ 12M: positive train and OOS direction, but report-only.
- DBC 12M: positive train direction but OOS Pearson only +0.0269; this is too weak for a commodity usefulness claim.

Therefore Fiscal V2 is **not** promoted as a universal asset-return predictor and no DBC/QQQ claim is made.

## Decision-engine boundary

Promotion will refresh and expose the Fiscal overlay, but the existing 10-point global conviction rubric remains unchanged.

Reason: the legacy Fiscal reading was not an explicit weighted component of that rubric. Adding automatic Fiscal points now would be a separate methodology change. If desired later, that must be tested through a separately frozen decision-engine candidate rather than being smuggled into this promotion.

## Production integration requirements

Promotion is complete only when all are true:

1. `lib/fiscal-v2-active.js` contains the guarded last-good active snapshot.
2. `lib/state.js` identifies Fiscal as `GMLI_FISCAL_V2_DEFICIT_IMPULSE` OVERLAY.
3. Legacy July Fiscal is preserved as historical reference.
4. Refresh verifies source bytes/hashes against the captured prospective manifest.
5. Refresh refuses available-date regression and preserves last-good production state on any failure.
6. `OVERLAY_REFRESH_STATUS.fiscal` reports active guarded V2 refresh rather than the legacy strict-release blocker.
7. `/api/report` exposes active Fiscal V2, its promotion scope and historical reference.
8. Data Health marks Fiscal V2 refreshable.
9. Existing global conviction weighting remains unchanged.
10. CI and deployment smoke tests pass before the change is called live.

## Promotion semantics

`PASS_FOR_PRODUCTION_INTEGRATION` means Candidate 1 is reproducible enough and has sufficient narrow empirical usefulness to replace the stale legacy Fiscal reading prospectively as an OVERLAY. It does not make Fiscal Core, prove causality, create a universal trading signal, or authorize automatic portfolio sizing changes.
