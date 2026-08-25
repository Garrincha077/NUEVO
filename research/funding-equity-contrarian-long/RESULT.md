# GMLI Funding Equity Contrarian Long-Horizon Result

Status: **FAIL_LONG_HORIZON_EQUITY_CONTRARIAN_RESEARCH**

Evidence tier: **RESEARCH**. Production Money Core, Funding Core, thresholds, scoring, and decision logic were not modified.

## Frozen test

- Signal: `100 - GMLI Funding V2 effective score` (higher = more restrictive Funding)
- Assets: SPY and QQQ only
- Horizon: 12M only
- Publication lag: 1M
- Sample: 2006-02 through latest fully observable 12M signal (2025-07 at the 2026-08-25 run)
- Prices: same exact-ticker Yahoo monthly adjusted-close helper used by existing GMLI transmission research
- No asset/horizon/lag/transform/threshold/parameter search; no FDR claim

## Positive-market-drift controls

1. High-minus-low inverted-Funding tercile spread, so common positive equity drift cancels.
2. Conditional returns compared with same-window unconditional 12M returns.
3. Expanding known-at-the-time drift baseline using only earlier completed 12M outcomes, minimum 36 prior observations.
4. HAC/Newey-West maxlags=12 for overlapping 12M forward returns.

## Full-sample result

| Asset | N | Raw Pearson | Raw Spearman | Raw HAC p | High-low mean | High-low median | Drift-excess Pearson | Drift-excess Spearman | Drift-excess high-low mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SPY | 234 | -0.251 | +0.067 | 0.3880 | -2.3% log-return spread | +3.0% log-return spread | +0.180 | +0.147 | +4.0% log-return spread |
| QQQ | 234 | -0.144 | +0.090 | 0.6038 | +0.3% log-return spread | +6.4% log-return spread | +0.221 | +0.155 | +5.5% log-return spread |

The frozen robustness gate failed for both assets.

## Fixed subperiods

Raw Pearson correlation between inverted Funding and 12M forward return:

| Asset | 2006-02..2012-12 | 2013-01..2019-12 | 2020-01+ |
|---|---:|---:|---:|
| SPY | -0.524 | -0.018 | +0.413 |
| QQQ | -0.422 | -0.022 | +0.549 |

Recent 2020+ behavior is strongly positive, but the earlier sample does not confirm a stable universal contrarian equity relationship.

Recent 2020+ high-minus-low inverted-Funding 12M log-return spreads were +0.118 for SPY and +0.239 for QQQ, while the 2006-12 spreads were -0.224 and -0.170 respectively.

## Fixed leave-out tests

Removing the GFC makes the full-sample Pearson positive (SPY +0.321, QQQ +0.311), showing that the 2007-09 episode is a major regime conflict. However removing 2020 or 2022 does not preserve a positive Pearson:

- SPY ex-2020: -0.290; ex-2022: -0.282
- QQQ ex-2020: -0.169; ex-2022: -0.196

This fails the predeclared episode-robustness condition.

## Interpretation

The short 2015+ / recent-OOS inverted-Funding equity result should not be promoted as a universal signal. The long test suggests a **regime-dependent recent contrarian effect**, strongest since 2020, rather than a stable 2006-2025 law.

Funding V2 remains unchanged: its promoted empirical asset-transmission use remains DBC/commodities, while any inverted Funding use for SPY/QQQ stays RESEARCH-only.

## Provenance

GitHub Actions run: `32823099191`
Artifact ID: `9553857217`
Artifact SHA256: `7783329fb777b1cf7718ac4d22e58310b7d46793775cd5d09327a3dc91c036bf`
Frozen branch test commit before first empirical run: `8701a6da82f4ad10f03ef573c748f58e60e7eeb6`
