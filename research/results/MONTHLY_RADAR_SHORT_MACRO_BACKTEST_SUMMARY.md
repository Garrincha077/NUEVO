# GMLI Monthly Radar — Pre-Specified Macro Short Backtest

Run date: 2026-08-17  
Branch: `research/monthly-radar-backtest`  
Status: **RESEARCH ONLY — SHORT MODEL REJECTED; no Core or production Radar change**

## Question

Can a separate short-only monthly model improve on the failed symmetric short logic by requiring a broad deterioration in funding/conditions before a rich/crowded asset turns down?

## Pre-specified design

Universe: SPY, QQQ, IWM, GLD, DBC, USO, CPER, DBA.

Main short model required all of:
1. monthly price stage = `EARLY_DOWN`;
2. at least **3 of 4** macro/conditions headwinds worsened over the prior 3 months:
   - 10Y real yield (`DFII10`) higher;
   - broad trade-weighted USD (`DTWEXBGS`) higher;
   - credit spread proxy higher;
   - Chicago Fed NFCI higher;
3. asset is **rich OR CFTC crowded**:
   - rich = 60M price/dislocation z >= +1;
   - crowded = historical trailing-3Y CFTC percentile >= 75.

`CONFIRMED_DOWN` was tested with the same macro + rich/crowded gate.

Forward returns: 3M / 6M / 12M, signed to the short direction. Only the first month entering the complete state is an event. Asset-matched unconditional short baselines are included. No threshold, parameter or horizon search was performed after seeing results.

## Data audit and correction

The first implementation used ICE BofA US High Yield OAS (`BAMLH0A0HYM2`). Through the FRED CSV route used by the runner, that input exposed only 36 monthly observations, 2023-08 through 2026-07. That truncated run is **invalid and discarded**.

To preserve the pre-specified economic meaning without changing the rule, the credit input was replaced with `BAA10Y`, the Moody's Baa corporate yield spread relative to the 10Y Treasury, explicitly as a **long-history credit-stress proxy**.

Corrected data audit:
- DFII10: 2003-01 to 2026-07, N=283
- DTWEXBGS: 2006-01 to 2026-07, N=247
- BAA10Y: 2003-01 to 2026-07, N=283
- NFCI: 2003-01 to 2026-07, N=283
- common 4-series range: 2006-01 to 2026-07, N=247; 204 months before 2023 and 43 months from 2023 onward.

The **3-of-4 gate, 3M change window, z thresholds, CFTC thresholds, price stages and forward horizons were not changed**. Network retry/backoff was later added solely for transport reliability after transient CFTC connection timeouts.

## Corrected results

| Signal | N | 3M mean / edge | 6M mean / edge | 12M mean / edge | 12M hit |
|---|---:|---:|---:|---:|---:|
| EARLY_DOWN | 97 | -2.9% / -0.6pp | -6.2% / -1.8pp | -9.6% / -0.9pp | 34.8% |
| EARLY_DOWN + macro 3/4 | 52 | -2.6% / -0.2pp | -2.8% / +2.0pp | -8.1% / +1.3pp | 37.5% |
| EARLY_DOWN + macro 3/4 + rich | 24 | -3.8% / -1.0pp | -5.1% / +0.4pp | -9.7% / +1.6pp | 40.0% |
| EARLY_DOWN + macro 3/4 + crowded | 15 | -6.5% / -3.9pp | -4.6% / +0.7pp | -11.4% / -0.8pp | 30.8% |
| **Main short model: EARLY_DOWN + macro 3/4 + (rich OR crowded)** | **28** | **-4.4% / -1.6pp** | **-4.6% / +1.0pp** | **-10.3% / +1.1pp** | **37.5%** |
| CONFIRMED_DOWN + macro 3/4 + (rich OR crowded) | 7 | -8.1% / -5.3pp | -8.4% / -2.9pp | -31.5% / -20.5pp | 14.3% |

A positive `edge` alone is not sufficient: the main model's absolute short-direction returns remain negative at all horizons.

## Stability

### 2015–2022
Main short model, N=20:
- 3M: -1.6%, edge +1.3pp, hit 45%
- 6M: -3.1%, edge +2.7pp, hit 45%
- 12M: -7.5%, edge +4.2pp, hit 45%

### 2023+
Main short model, N=8; only four events currently have complete 6M/12M forward windows:
- 3M: -11.5%, edge -8.9pp, hit 12.5%
- 6M: -12.2%, edge -7.4pp, hit 25%
- 12M: -24.1%, edge -14.4pp, hit **0%** on completed 12M observations

The recent sample therefore contradicts rather than confirms the model.

## Episode composition

Main model event starts:
- SPY 9
- QQQ 8
- IWM 3
- GLD 2
- DBC 1
- USO 0
- CPER 4
- DBA 1

Leave-one-asset-out does not rescue the model. For example:
- excluding SPY: 12M signed short mean -8.9%, hit 43.8%
- excluding QQQ: -5.2%, hit 47.1%
- excluding CPER: -13.4%, hit 28.6%

Thus failure is not attributable to one single asset.

## Interpretation

1. **The pre-specified macro short model fails.** Tightening financial conditions, rising real yields/USD/credit spread, rich/crowded positioning and a monthly downside turn did not produce positive absolute short returns.
2. Short-side asymmetry is materially different from the long side. The long research result (`Money + contrarian setup + EARLY_UP`) should not be mirrored mechanically.
3. `CONFIRMED_DOWN` with the same macro gate is even worse in this sample and should not be promoted.
4. Positive asset-matched edge in parts of the 2015–2022 sample is not enough to justify shorting when the signed absolute return remains negative and the 2023+ sample deteriorates sharply.
5. No further parameter/horizon search is justified under the Pareto research rule. Searching for a combination that makes the short backtest positive now would be classic overfitting risk.

## Decision

**REJECT the mechanical GMLI high-conviction short model.**

No Core change. No production Radar promotion.

Practical semantics going forward:
- keep long-side `SETUP_LONG / EARLY_LONG / CONFIRMED_LONG` research hierarchy;
- `EARLY_SHORT` / `CONFIRMED_SHORT` may remain descriptive mechanical market states, but must **not** be treated as validated trade signals;
- high-conviction shorts require `COPILOT VIEW — CURRENT RESEARCH INFERENCE` with asset-specific catalysts, funding/liquidity stress and current market confirmation;
- begin forward logging/scorecard rather than further backtest tuning.

## Next action

Stop retrospective model search. Log every future monthly Radar state and the contemporaneous engine/Copilot context, then score realized 3M/6M/12M outcomes out-of-sample. Revisit short-model research only after enough genuinely new forward episodes accumulate or a clearly different economic hypothesis is specified before looking at results.
