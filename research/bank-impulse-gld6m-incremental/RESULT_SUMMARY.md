# Bank Impulse → GLD 6M incremental robustness gate v1

Status: **STOP_RESEARCH_DIAGNOSTIC**

Evidence tier: **RESEARCH_DIAGNOSTIC**  
Scoring effect: **NONE**  
Automatic weight change: **0**  
Methodology effect: **NONE**

Workflow run: `33196142937` — **SUCCESS**.

## Question tested

Does the existing Bank Balance-Sheet Impulse add stable GLD 6M forward information beyond the existing GMLI GLD Money predictor (`FX-neutral accel3`)?

The model/horizon/split/gate were frozen before results. No asset, horizon, lag, sign, threshold or subperiod search was performed.

## Fixed model comparison

- Train n: **93**
- OOS n: **36**
- Candidate standardized Bank beta: **+0.02735**
- Bank Newey-West/HAC p-value, maxlags 5: **0.00010**
- Baseline train R²: **0.00770**
- Candidate train R²: **0.09796**
- OOS RMSE baseline: **0.154083**
- OOS RMSE candidate: **0.153335**
- OOS incremental R² vs Money-only baseline: **+0.00969**
- OOS prediction Pearson baseline: **+0.58149**
- OOS prediction Pearson candidate: **+0.38470**
- Fixed non-overlap phase wins: **3/6**
- Median phase incremental R²: **+0.00739**

## Frozen gate

- **PASS** — train Bank coefficient > 0
- **PASS** — HAC p-value < 0.10
- **PASS** — aggregate OOS incremental R² > 0
- **FAIL** — candidate OOS prediction correlation is not worse than baseline
- **FAIL** — candidate wins at least 4/6 non-overlapping phases with positive median phase incremental R²

Because the gate required **all** checks to pass, the result is mechanically `STOP_RESEARCH_DIAGNOSTIC`.

## Six fixed non-overlapping OOS phases

| Phase | N | Incremental R² | Candidate better SSE? |
|---:|---:|---:|---|
| 0 | 6 | +0.01757 | YES |
| 1 | 6 | +0.02336 | YES |
| 2 | 6 | +0.02632 | YES |
| 3 | 6 | -0.02760 | NO |
| 4 | 6 | -0.00873 | NO |
| 5 | 6 | -0.00279 | NO |

## Interpretation

The Bank Impulse result is **real enough to explain the positive first-pass backtest, but not stable enough to deserve a production role**.

The train coefficient is positive and strongly HAC-significant, and aggregate OOS SSE/RMSE improves slightly. However, the improvement is tiny (~0.97% incremental OOS R²), the candidate's OOS prediction correlation falls materially from **+0.581** to **+0.385**, and only **3 of 6** fixed non-overlapping phase cohorts improve.

That combination is consistent with a signal that contains some episodic/regime information but does not add sufficiently stable incremental forecasting value beyond Money for the predeclared GLD 6M use case.

## Decision

**STOP. Do not promote or optimize this relation further.**

Bank Balance-Sheet Impulse remains useful as **informational Liquidity Context** only:
- no GMLI score effect;
- no conviction points;
- no automatic allocation weight;
- no CORE or OVERLAY promotion.

Treasury Duration Mix also remains informational only under the prior fixed backtest.

Any future attempt to promote Bank Impulse would require a materially new, explicitly frozen research question rather than retuning this failed gate.
