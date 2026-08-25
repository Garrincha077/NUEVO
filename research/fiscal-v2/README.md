# GMLI Fiscal V2 — Candidate 1 research phase

Status: **RESEARCH / NOT PROMOTED**

## Legacy reproduction decision

Decision: **STOP_LEGACY_REVERSE_ENGINEERING_BUILD_VERSIONED_V2**.

The preserved production Fiscal reference remains:
- mode: `STRICT_ACTUAL_RELEASE`
- available date: `2026-07-31`
- z: `0.1523733868591229`
- score: `52.539556447652046`
- regime: `NEUTRAL`

Production `/api/report` and the prospective Fiscal manifest confirm that raw prospective capture is active but the exact historical strict-release runner/vintages were not recovered. Current revised FRED history is therefore not used to claim an exact legacy rerun.

The legacy reading remains a historical production reference. Candidate 1 is a separately versioned research construction and is not tuned to reproduce the legacy score.

## Candidate 1

Version: `GMLI_FISCAL_V2_CANDIDATE_1`

Frozen contract:
- `research/fiscal-v2-candidate-1-contract.json`

Runner:
- `scripts/build-fiscal-v2.py`

Pareto construction:
1. trailing-12-month federal deficit as % of nominal GDP;
2. 12-month change in that deficit/GDP ratio (fiscal impulse);
3. rolling 120-month z-scores, minimum 24 months;
4. equal 50/50 weighting;
5. score mapping `clip(50 + (50/3) * z, 0, 100)`.

Only `MTSDS133FMS` and `GDP` enter the score. `GFDEBTN`, `A091RC1Q027SBEA`, `FGRECPT` and `FGEXPND` remain diagnostics to avoid silently double-counting overlapping fiscal information.

Historical research uses current/revised FRED history with conservative frozen publication lags. It is explicitly **not** represented as exact point-in-time release history.

## Fixed construction sanity

Before any asset usefulness result can matter, Candidate 1 must classify `2020-06` as `SUPPORTIVE` under the frozen construction. The current legacy reading is reported as a comparator only and does not need to match.

A construction failure is a real failure. Candidate 1 must not be retuned after the result.

## Narrow usefulness gate

Frozen before empirical execution:
- `research/fiscal-v2-usefulness-gate.json`

Runner:
- `scripts/test-fiscal-v2-usefulness.py`

Primary relation only:
- `SPY` 12M forward total return.

Primary PASS requires:
- train Pearson > 0;
- OOS Pearson > 0;
- OOS Spearman > 0.

Train signals end `2022-12`; OOS starts `2023-01`. A fiscal observation for month `t` is treated as available at month-end `t+1`, and the forward-return window starts from the adjusted monthly close in `t+2`.

`QQQ` 12M and `DBC` 12M are diagnostics only and cannot change PASS/FAIL.

There is no asset, horizon, lag, component, weight, threshold or subperiod search and no FDR claim.

## Promotion boundary

Even a usefulness PASS does **not** promote Fiscal. It only permits a production-readiness review.

Production promotion would still require:
- explicit promotion decision/lock;
- prospective raw-byte/hash provenance;
- fail-closed source/date/contract guards;
- guarded scheduled refresh;
- Data Health integration;
- CI/frozen guards;
- Vercel and GitHub Pages deployment;
- production API smoke.

Until then:
- Money Core is unchanged;
- Funding V2 is unchanged;
- production Fiscal remains the July-2026 `STRICT_ACTUAL_RELEASE` reference;
- Candidate 1 remains RESEARCH.
