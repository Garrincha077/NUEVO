# GMLI Monthly Radar Price-Only Backtest — Research Summary

Run date: 2026-08-17
Branch: `research/monthly-radar-backtest`
Status: RESEARCH ONLY — no production/Core change

## Design

Universe: SPY, QQQ, IWM, GLD, SLV, DBC, USO, CPER, DBA, TLT, IEF, FXY, HYG, VNQ, EEM, VEA, BTC.

Data: Yahoo adjusted monthly close, maximum available ETF/asset history.

Trend rule is the current Radar monthly price rule:
- 3M return
- 10M moving average
- 3M change in the 10M moving average

Stages:
- EARLY_UP
- CONFIRMED_UP
- EARLY_DOWN
- CONFIRMED_DOWN

Price-only contrarian proxy:
- CHEAP = rolling 60M log-price z <= -1
- RICH = rolling 60M log-price z >= +1
- relative variants use asset/SPY rolling 60M log-ratio z-score

Only the first month entering a state/combination is counted as an event start. Repeated months in one episode are not double-counted.

Forward simple total returns are measured at 3M, 6M and 12M. SHORT returns are sign-inverted. No parameter search was performed.

## Main pooled results

| Signal | N | 3M mean / hit | 6M mean / hit | 12M mean / hit | Edge vs asset-matched baseline at 12M |
|---|---:|---:|---:|---:|---:|
| EARLY_UP | 289 | +0.9% / 54.0% | +2.9% / 56.3% | +8.4% / 57.4% | -0.5 pp |
| CONFIRMED_UP | 346 | +2.5% / 61.8% | +5.3% / 65.1% | +14.5% / 71.8% | +3.8 pp |
| CHEAP_EARLY_UP | 46 | -0.9% / 39.1% | +2.4% / 43.5% | +8.2% / 47.8% | +4.9 pp |
| CHEAP_CONFIRMED_UP | 8 | +3.6% / 50.0% | +1.1% / 50.0% | +11.5% / 62.5% | +9.8 pp |
| EARLY_DOWN (short) | 389 | -1.5% / 44.7% | -3.5% / 39.5% | -11.3% / 37.0% | -1.3 pp |
| CONFIRMED_DOWN (short) | 244 | -0.1% / 44.3% | -1.4% / 43.9% | -4.8% / 44.6% | +2.5 pp |
| RICH_EARLY_DOWN (short) | 179 | -1.4% / 45.3% | -2.6% / 44.3% | -6.4% / 41.8% | +6.0 pp |
| RICH_CONFIRMED_DOWN (short) | 28 | +3.8% / 53.6% | +3.5% / 46.4% | +3.1% / 59.3% | +14.9 pp |

Unconditional pooled long baseline sampled every 3 months after 60M warmup:
- 3M: +2.1%, hit 58.7%
- 6M: +4.4%, hit 62.5%
- 12M: +9.2%, hit 64.0%

Asset-matched baseline control compares each signal with the unconditional forward return of the same asset. For SHORT signals the benchmark is sign-inverted.

## 2018+ stability check

- CONFIRMED_UP: N=142; 12M mean +18.6%, hit 72.9%, edge +5.1 pp vs asset-matched baseline.
- EARLY_UP: N=121; 12M mean +15.0%, hit 64.0%, edge +3.8 pp; 6M edge was approximately zero.
- CHEAP_EARLY_UP: N=16; 12M mean +12.2% but median -3.9% and hit 37.5%; strong positive mean is therefore not robust across episodes.
- RICH_CONFIRMED_DOWN: N=16; short-direction 3M mean +3.4%, 12M mean +1.5%, 12M hit 66.7%; sample remains small.

## Interpretation

1. `CONFIRMED_UP` is the strongest and most stable price-only long state. The main advantage appears at the 12M horizon rather than immediately at 3M.
2. `EARLY_UP` by itself is not a strong full-sample entry rule. It behaves better in the 2018+ sample but still has little 6M edge. Treat EARLY as a watch/transition state that needs Money, positioning or another independent confirmation.
3. `CHEAP + EARLY_UP` does not reliably solve the falling-knife problem. Full-sample hit rates are below 50%; the 2018+ mean is positive but the median remains negative.
4. The pure short side is weak. EARLY_DOWN and CONFIRMED_DOWN alone generally lose money in absolute short-direction returns because many assets have positive long-run drift and rebounds are common.
5. `RICH + CONFIRMED_DOWN` is the only price-only short combination with positive pooled mean returns at 3M/6M/12M, but N=28 (N=16 since 2018). This is interesting RESEARCH evidence, not enough to promote a standalone short rule.
6. Relative-price early contrarian variants are unstable and should not be promoted from this test.

## Practical Radar implication

Do not change the frozen Money Core.

For the Radar:
- SETUP and EARLY should remain discovery/watch states, not automatic entries.
- CONFIRMED_UP deserves more weight as a long timing confirmation.
- A short candidate should require stronger alignment than the long side; price-only EARLY_DOWN is insufficient.
- The next highest-value test is to condition these monthly event starts on the existing Money/transmission regime and CFTC/dislocation context, without tuning thresholds.

## Caveats

- Price-only test; historical Money and CFTC are not yet conditioned.
- Different assets have different launch dates/history lengths.
- Overlapping forward horizons can occur across distinct assets/events.
- No transaction costs, taxes, slippage or execution lag.
- Descriptive research only; no p-value/FDR/parameter search.
