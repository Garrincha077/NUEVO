# Bank Balance-Sheet Impulse → GLD 6M incremental robustness gate v1

Status: **FROZEN BEFORE RESULTS / RESEARCH ONLY / NOT PROMOTED**

## Purpose

Test one narrow question left by the fixed Liquidity Context backtest: **does the Bank Balance-Sheet Impulse add stable forward information for GLD 6M beyond the existing GMLI Money signal?**

This is not a new asset/horizon/lag search. The prior fixed 24-test screen identified `BANK_IMPULSE / GLD / 6M` as the cleanest directional survivor. This gate tests only that survivor and must end in either `PROMOTION_CANDIDATE` or `STOP_RESEARCH_DIAGNOSTIC`.

No result from this gate may directly change Money Core, Liquidity Context semantics, conviction, weights, evidence tiers, or production allocation logic.

## Frozen inputs

### Bank Balance-Sheet Impulse

Concept: production Liquidity Context H.8 total-assets impulse.

Research fetch path: Federal Reserve H.8 Data Download Program series `B1151NCBA`, used as the official-source history path for the same all-commercial-bank total-assets concept after the FRED CSV endpoint proved unreliable in CI.

Construction is unchanged from Liquidity Context v1:
- monthly endpoint = latest weekly observation in each month;
- current 13W growth = percentage change versus approximately 91 days earlier;
- prior 13W growth = percentage change from approximately 182 days earlier to 91 days earlier;
- `bank_impulse = current_13w_growth - prior_13w_growth`;
- conservative availability = weekly observation date + 14 calendar days.

No alternative bank window, transformation, smoothing, threshold, or sign is tested.

### Money baseline

Use the active Global Money V2 historical file:
`research/global-money-v2/latest/global_money_v2.csv`

The GLD-specific upstream predictor is frozen to the already-promoted channel/transformation:
- channel: **FX-neutral** (`gbm_fxn_yoy_pct`);
- transformation: **accel3** = current FX-neutral Money YoY minus its value 3 months earlier;
- mandatory availability lag: **1 month**.

Important boundary: GLD 12M is the promoted Money transmission relation. Here the same promoted GLD Money predictor is used only as a **baseline control for a 6M incremental-value diagnostic**. This does not promote a standalone GLD 6M Money relation.

### GLD returns

Source: Yahoo Finance monthly adjusted close for exact ticker `GLD`.

Outcome:
- fixed horizon: **6 months only**;
- forward log adjusted return from the decision month to decision month + 6;
- current incomplete month is excluded.

No alternate asset, return horizon, price source, or return transformation is searched.

## Alignment / availability

For each bank monthly endpoint:
1. compute `bank_available_date = observation_date + 14 days`;
2. decision / GLD start month = calendar month containing that availability date, representing the first month-end close after the information is available;
3. Money signal month = decision month − 1 month, enforcing the frozen one-month Money availability lag;
4. Money accel3 is calculated on that Money signal month;
5. GLD 6M forward return starts at the decision-month adjusted close.

Rows with missing Money, bank, start price, or +6M price are dropped mechanically.

## Frozen train / OOS split

Reuse the promoted Money transfer split, defined by **Money signal month**:
- train: `2015-01 .. 2022-12`;
- OOS: `2023-01+`.

There is no subperiod search.

## Models

Predictors are standardized using **train-only mean and standard deviation**, then the same scaling is applied OOS.

Baseline:
`GLD_6M_return ~ intercept + Money_FXN_accel3`

Candidate:
`GLD_6M_return ~ intercept + Money_FXN_accel3 + Bank_Impulse`

Both are fitted once on the frozen train sample. OOS predictions use those fixed train coefficients; there is no recursive refit or model selection.

## Overlap-aware inference

Because monthly 6M forward returns overlap, ordinary OLS standard errors are not treated as reliable promotion evidence.

Frozen inference:
- candidate Bank coefficient is reported with **Newey-West / HAC covariance, maxlags = 5**;
- ordinary coefficient p-values are not used for the gate.

## Non-overlapping robustness

Create six fixed OOS phase cohorts using `decision_month_index mod 6`.
Within each phase, observations are six months apart, providing a non-overlapping directional forecast-error check.

All six phases are reported. No phase is selected or excluded based on results.

## Promotion-candidate gate — frozen before results

The result is `PROMOTION_CANDIDATE` only if **all** conditions hold:

1. Train candidate Bank coefficient > 0.
2. Train Newey-West/HAC two-sided p-value for the Bank coefficient < 0.10.
3. Full OOS incremental forecast R² versus baseline is > 0, where `R2_incremental = 1 - SSE_candidate / SSE_baseline`.
4. Candidate OOS prediction Pearson correlation with realized GLD 6M returns is at least as high as baseline correlation.
5. Non-overlapping phase robustness: candidate SSE < baseline SSE in at least **4 of 6** fixed phase cohorts **and** median phase incremental R² > 0.

If any condition fails, result = `STOP_RESEARCH_DIAGNOSTIC`.

No threshold may be changed after observing results.

## Interpretation boundary

Even `PROMOTION_CANDIDATE` is not promotion. It would justify a separate versioned promotion protocol with archived input provenance and production-integration review.

`STOP_RESEARCH_DIAGNOSTIC` means Bank Impulse remains useful only as informational Liquidity Context unless a materially different future research question is explicitly frozen first.

In both cases:
- evidence tier remains `RESEARCH_DIAGNOSTIC` for this run;
- `scoring_effect = NONE`;
- `automatic_weight_change = 0`;
- `methodology_effect = NONE`;
- CORE / OVERLAY / RESEARCH separation is unchanged.
