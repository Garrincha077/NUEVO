# GMLI Monthly Radar — Money + CFTC Conditioning Backtest

Run date: 2026-08-17  
Branch: `research/monthly-radar-backtest`  
Status: **RESEARCH ONLY — no Core or production Radar change**

## Question

Does existing GMLI-style Money/transmission context improve the weak price-only monthly `EARLY` signal, and does CFTC/dislocation context add further value?

## Guardrails

- Core assets only: SPY, QQQ, GLD, DBC.
- Monthly adjusted closes.
- Forward simple total returns: 3M / 6M / 12M.
- First month entering the complete condition only; repeated months are not double-counted.
- 1M Money publication lag retained.
- Existing transmission modes retained conceptually:
  - SPY/QQQ: `accel3`
  - GLD: `accel3`
  - DBC: `level`
- Historical frozen seven-region Money bytes were not preserved. Therefore this test uses OECD monthly M3 YoY (`OECDMABMM301GYSAM`) as an explicitly **RESEARCH long-history Money proxy**. It is not an exact Core rerun.
- CFTC percentile is calculated historically as-of each month using a trailing 3Y window; no current positioning is backfilled into history.
- Existing Radar CFTC thresholds retained: <=25th percentile = washed/contrarian-long; >=75th = crowded/contrarian-short.
- Existing price-dislocation threshold retained: z <= -1 cheap; z >= +1 rich. GLD/DBC use CPI-lagged real price.
- No parameter search or threshold tuning.

## Full 2015+ result

| Signal | N | 3M mean / edge | 6M mean / edge | 12M mean / edge | 12M hit |
|---|---:|---:|---:|---:|---:|
| EARLY_UP | 29 | +0.3% / -1.7pp | +2.7% / -1.3pp | +10.4% / +2.5pp | 65.5% |
| **EARLY_UP + Money** | **10** | **+4.1% / +1.9pp** | **+11.2% / +6.7pp** | **+20.0% / +11.2pp** | **90.0%** |
| EARLY_UP + Money + cheap | 4 | +2.2% / +0.7pp | +10.0% / +6.9pp | +21.2% / +15.3pp | 100% |
| EARLY_UP + Money + washed CFTC | 3 | +4.2% / +0.7pp | +6.5% / -0.6pp | +22.7% / +8.2pp | 100% |
| **EARLY_UP Radar-style: Money + (cheap OR washed)** | **6** | **+3.7% / +1.4pp** | **+10.9% / +6.1pp** | **+24.9% / +15.4pp** | **100%** |
| **CONFIRMED_UP Radar-style** | 24 events; 21 with 12M forward | +3.5% / +0.3pp | +9.7% / +3.5pp | +23.3% / +10.3pp | 100% of available 12M |
| EARLY_DOWN short | 47 | -2.9% / -0.4pp | -7.9% / -2.9pp | -13.2% / -3.1pp | 34.1% |
| EARLY_DOWN + Money headwind | 30 | -2.0% / +0.6pp | -6.3% / -1.3pp | -10.6% / -0.6pp | 37.9% |
| **EARLY_DOWN Radar-style short** | **20** | **-3.4% / -0.4pp** | **-7.9% / -1.9pp** | **-13.2% / -1.1pp** | **31.6%** |
| CONFIRMED_DOWN Radar-style short | 6 | -6.0% / -2.7pp | -7.3% / -0.8pp | -24.4% / -10.9pp | 0% |

`edge` is versus the 3-month-spaced unconditional forward return of the same asset; short benchmarks are sign-inverted.

## Episode composition

`EARLY_UP + Money` has 10 episodes:
- QQQ: 2
- GLD: 5
- DBC: 3
- SPY: 0

`EARLY_UP Radar-style` has 6 episodes, evenly distributed:
- QQQ: 2
- GLD: 2
- DBC: 2

Leave-one-asset-out 12M mean for `EARLY_UP Radar-style` remains positive in every case:
- drop QQQ: +21.2%
- drop GLD: +33.9%
- drop DBC: +19.6%

This reduces, but does not remove, concentration concern because the total sample is still only six episodes.

## Holdout / freshness caveat

The strongest apparent `EARLY_UP + Money` result is **not independently confirmed post-2023**: there were zero qualifying EARLY_UP+Money episodes from 2023 through the available Money-proxy window.

`CONFIRMED_UP Radar-style` does have post-2023 observations. Six event starts occurred, but only three currently have complete 12M forward returns:
- SPY 2023-12: +24.9% 12M
- SPY 2024-08: +15.9% 12M
- SPY 2025-01: +16.3% 12M

The remaining later events do not yet have a complete 12M horizon.

Therefore the large EARLY_UP improvement is **promising research evidence, not a validated promotion result**.

## Interpretation

1. **Money appears to be the high-value filter for early longs.** Price-only EARLY_UP had weak 3M/6M edge; adding the pre-specified Money direction changed 6M edge from -1.3pp to +6.7pp and 12M edge from +2.5pp to +11.2pp in this sample.
2. **Contrarian context may further improve selectivity**, but it reduces N from 10 to 6. The Radar-style early-long condition produced strong results across QQQ, GLD and DBC, but sample size is too small for promotion.
3. **Confirmed-up remains the safer timing state.** Radar-style confirmed-up had +10.3pp 12M edge with 21 completed 12M observations.
4. **The short side fails the symmetry test.** Inverting Money + dislocation/CFTC + downside trend did not produce a profitable short rule. This is important evidence against treating long and short Radar logic as mirror images.
5. A better short model likely needs different drivers — Funding/real yields, USD, credit deterioration or asset-specific macro — rather than merely `Money headwind + rich/crowded + downtrend`.

## Practical implication

Do not alter frozen Money Core.

For Radar research semantics:
- `SETUP_LONG` / `EARLY_LONG` should continue to require Money/transmission support; this backtest supports that design direction.
- `EARLY_LONG` remains a discovery/staging state because N is small and there is no post-2023 qualifying EARLY holdout yet.
- `CONFIRMED_LONG` deserves higher confidence than price-only EARLY.
- Do **not** give symmetric high-confidence `EARLY_SHORT` status from inverted long rules. Keep short conviction lower until a separate Funding/USD/credit-conditioned test succeeds.

## Next highest-value test

Pre-specify one short-only research test using current Funding/real-yield/USD variables and the same monthly price event starts. Do not search thresholds or horizons. Separately, continue forward validation of new EARLY_LONG+Money episodes after August 2026.
