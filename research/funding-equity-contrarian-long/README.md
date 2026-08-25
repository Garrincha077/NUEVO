# Funding V2 equity contrarian finding

Status: **RESEARCH — REGIME-DEPENDENT / NOT PROMOTED**

Recorded: 2026-08-25

## Finding

A simple inverted Funding V2 signal (`100 - effective Funding score`, higher = more restrictive Funding) has **some contrarian value for SPY/QQQ in the recent regime, but it is not robust over the broader 2006–2025 sample**.

Fixed long-horizon test:
- assets: SPY and QQQ only
- horizon: 12M only
- publication lag: 1M
- sample: 2006-02 through latest fully observable 12M signal (2025-07 in the 2026-08-25 run)
- no asset/horizon/lag/transform/threshold/parameter search
- positive market drift explicitly controlled with conditional-vs-unconditional comparisons, high-minus-low tercile spreads, expanding known-at-the-time drift baseline and HAC/Newey-West for overlapping 12M returns

### Fixed subperiod Pearson correlations

| Period | SPY | QQQ |
|---|---:|---:|
| 2006-02..2012-12 | -0.524 | -0.422 |
| 2013-01..2019-12 | -0.018 | -0.022 |
| 2020-01+ | +0.413 | +0.549 |

Full-sample raw Pearson:
- SPY: -0.251
- QQQ: -0.144

Recent 2020+ high-minus-low inverted-Funding 12M log-return spreads:
- SPY: +0.118
- QQQ: +0.239

But the 2006–2012 spreads were negative:
- SPY: -0.224
- QQQ: -0.170

## Interpretation

The recent result is worth remembering as a **regime-dependent contrarian research observation**: during some recent tightening/stress/easing-transition environments, more restrictive Funding has coincided with stronger subsequent 12M equity returns.

It must **not** be generalized into a broad historical rule. The longer sample fails the predeclared robustness gate and shows materially different behavior in earlier regimes.

Therefore:
- do not invert production Funding for SPY/QQQ;
- do not alter Money Core, Funding V2, thresholds or decision logic;
- do not continue optimizing this relationship unless a future explicit research question requires it;
- Funding V2's promoted empirical asset-transmission use remains DBC/commodities;
- SPY/QQQ Funding-contrarian use stays RESEARCH-only context.

## Provenance

Research PR: #25 `Research long-horizon equity Funding contrarian effect`

GitHub Actions run: `32823099191`

Artifact ID: `9553857217`

Artifact SHA256: `7783329fb777b1cf7718ac4d22e58310b7d46793775cd5d09327a3dc91c036bf`

Frozen pre-run commit: `8701a6da82f4ad10f03ef573c748f58e60e7eeb6`
