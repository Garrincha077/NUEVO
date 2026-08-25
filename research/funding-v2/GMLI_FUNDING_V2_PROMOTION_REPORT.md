# GMLI Funding V2 Promotion Report

Status: **PASS_FOR_PRODUCTION_INTEGRATION**  
Promotion target: `GMLI_FUNDING_V2_EFFECTIVE_CONDITIONS`  
Evidence tier after promotion: **OVERLAY**  
Date: 2026-08-25

## Decision

Promote `GMLI_FUNDING_V2_CANDIDATE_2` as the refreshable Funding/Conditions overlay, subject to production integration guards, scheduled source capture, last-good preservation, Data Health integration and endpoint smoke tests.

This promotion does **not** modify or replace the Money Core. Funding remains a bounded conviction modifier under the existing decision-engine rubric.

## Why Candidate 1 was rejected

`GMLI_FUNDING_V2_CANDIDATE_1` used an equal-weight average of four signed funding/conditions channels:

- ANFCI broad observed financial conditions
- 10Y real yield (`DFII10`)
- 10Y Kim-Wright term premium (`THREEFYTP10`)
- 3M bank-reserve impulse (`WRESBAL`)

It matched the current legacy Funding direction and passed 2008-10, but failed the predeclared 2020-03 stress sanity: emergency policy easing and reserve expansion overwhelmed the simultaneously extreme observed financial stress. Candidate 1 is preserved as `REJECTED_FOR_PROMOTION`; it was not retuned.

Frozen audit: `research/funding-v2/CANDIDATE_1_RESULT.json`.

## Candidate 2 frozen construction

Candidate 2 keeps the same sources, transformations, publication lag, standardization and regime thresholds as Candidate 1.

- Frequency: monthly
- Publication lag: 1 month
- Rolling z-score: 120 months, minimum 36, population ddof=0
- Component signed z clip: [-3, +3]
- Structural support score: equal-weight average of the four signed z-scores mapped by `50 + (50/3) * z`, clipped 0–100
- Observed conditions score: signed ANFCI z mapped by the same score function
- **Effective Funding score = min(structural support score, observed conditions score)**
- Regime: `<40 RESTRICTIVE`, `40–60 NEUTRAL`, `>60 SUPPORTIVE`

Economic interpretation: policy support may improve the backdrop, but it cannot make effective Funding more supportive than the broad financial conditions actually being observed.

Frozen contract: `research/funding-v2-candidate-2-contract.json`.

## Fixed directional gate

PASS.

Current eligible reading:

- observation month: 2026-06
- available date: 2026-07-31
- effective score: **37.9684402601**
- regime: **RESTRICTIVE**
- structural support score: 37.9684402601
- observed ANFCI conditions score: 59.0994961494
- legacy production Funding: 36.0354109320 — RESTRICTIVE
- current direction match: PASS

Stress sanity:

- 2008-10: RESTRICTIVE — PASS
- 2020-03: RESTRICTIVE — PASS

No weights, windows, thresholds or horizons were tuned to obtain the pass.

## Narrow usefulness gate

PASS 2/2 on the two predeclared commodity/Funding relationships.

### DBC 6M

- train n=96, Pearson +0.096982
- OOS n=37, Pearson +0.341202
- OOS Spearman +0.322191
- direction PASS

### DBC 12M

- train n=96, Pearson +0.011965
- OOS n=31, Pearson +0.345475
- OOS Spearman +0.390323
- direction PASS

Protocol was frozen before the empirical run: no asset search, horizon search, lag search, parameter search, threshold search or new FDR claim.

Frozen gate: `research/funding-v2-usefulness-gate.json`.  
Frozen result: `research/funding-v2/USEFULNESS_RESULT.json`.

## Important limitation

Secondary diagnostics were not part of the gate and do **not** support treating Funding V2 as a universal forward-return predictor:

- SPY 12M: negative train and OOS direction
- QQQ 12M: negative train and OOS direction
- GLD 12M: negative train, positive OOS

Therefore Funding V2 is promoted only as:

1. a Funding/Conditions regime overlay,
2. a bounded conviction modifier,
3. a particularly relevant modifier for the already pre-identified DBC/commodity transmission channel.

It must not overwrite Money Core, market confirmation or asset-specific transmission models.

## Production integration requirements

Promotion is complete only when all are true:

1. `lib/funding-v2-active.js` contains the guarded last-good active snapshot.
2. `lib/state.js` identifies Funding as `GMLI_FUNDING_V2_EFFECTIVE_CONDITIONS` OVERLAY.
3. Legacy July Funding is preserved as historical reference, not deleted.
4. Scheduled refresh archives source bytes/hashes and cannot regress available date.
5. Refresh fails closed and leaves last-good production Funding untouched on source or validation failure.
6. `OVERLAY_REFRESH_STATUS.funding` reports the V2 refresh contract rather than the legacy baseline blocker.
7. `/api/report` explicitly identifies Funding V2 as an overlay and removes the stale legacy Funding blocker from active research gaps.
8. Existing conviction contribution remains bounded at its current Funding weight; no extra weight is granted by this promotion.
9. CI guards Candidate 1 rejection, Candidate 2 directional PASS, usefulness PASS and Money Core non-modification.
10. GitHub Pages and production endpoint smoke tests pass before calling the change live.

## Promotion semantics

`PASS_FOR_PRODUCTION_INTEGRATION` means the candidate is sufficiently reproducible and decision-useful to replace the stale legacy Funding overlay prospectively. It does not mean Funding is a new Core, a trading signal, or a universal asset-return forecast.
