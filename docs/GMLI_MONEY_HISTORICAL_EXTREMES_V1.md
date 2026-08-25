# GMLI Money Historical Extremes v1

Status: ACTIVE DIAGNOSTIC CANDIDATE / PAGES UI
Evidence tier: **RESEARCH_DIAGNOSTIC**
Scoring effect: **NONE**
Automatic weight change: **0**

## Purpose
Historical Extremes adds context to the promoted Global Money V2 history without changing Money Core. It answers two practical questions:
1. Is the current broad-money growth level historically unusual?
2. Is the current 3-month change in broad-money YoY growth historically unusual?

It is an interpretation/visualization layer only. It cannot change Money Core, promoted asset-transmission relationships, Funding/Fiscal overlays, Signal Role Taxonomy or the frozen 10-point conviction rubric.

## Inputs
Use only the promoted `/api/history` Global Money V2 monthly history already used by the Pages Money charts:
- USD-translated broad-money YoY
- FX-neutral broad-money YoY.

No additional source series are introduced.

## Transforms
For each USD and FX-neutral channel:
- `level = current YoY broad-money growth`
- `accel3 = YoY(t) - YoY(t-3)`

The accel3 definition matches the semantics of the promoted Money transmission transform used for SPY/QQQ and GLD research relationships.

## Standardization
For each of the four series independently:
- frequency: monthly
- rolling window: 120 months
- minimum observations: 36 months
- standard deviation: population, `ddof=0`
- no clipping
- no look-ahead: each month uses only that month and earlier observations
- z-score: `(current - trailing mean) / trailing population SD`
- percentile: mid-rank empirical percentile within the same trailing rolling window.

Interpretive bands are descriptive only:
- `z >= +2`: EXTREME_HIGH
- `+1 <= z < +2`: ELEVATED_HIGH
- `-1 < z < +1`: NORMAL
- `-2 < z <= -1`: ELEVATED_LOW
- `z <= -2`: EXTREME_LOW.

These are not regime thresholds and are not trading rules.

## Reading rules
- High **level z**: money growth is historically strong relative to its own trailing distribution.
- Low **level z**: money growth is historically weak.
- High **accel3 z**: broad-money growth is accelerating unusually quickly.
- Low **accel3 z**: broad-money growth is decelerating unusually quickly.
- High level + negative accel3: liquidity can still be strong in absolute terms while its impulse is deteriorating.
- Low level + positive accel3: liquidity can still be weak while its impulse is improving.

Percentiles are included because they are more intuitive than z-scores for many users. A 90th percentile reading means the current value is above roughly 90% of observations in the trailing window.

## Investor-use boundary
Use Historical Extremes for context, asymmetry and risk discussion after the canonical hierarchy:
Money Core → promoted asset transmission → Funding/Fiscal context → Market Confirmation → Historical Extremes → Radar/timing.

Do not:
- add z-score points to conviction;
- treat `z > +2` as an automatic short;
- treat `z < -2` as an automatic long;
- replace the promoted Money score with this diagnostic;
- generalize promoted SPY/QQQ/GLD/DBC relationships to unsupported assets.

Any future attempt to use these diagnostics as an automatic allocation or conviction weight requires a separately frozen versioned decision-engine candidate and empirical gate defined before testing.