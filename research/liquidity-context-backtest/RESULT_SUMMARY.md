# Liquidity Context fixed backtest v1 — result summary

Status: **RESEARCH_DIAGNOSTIC / NOT PROMOTED**

Fixed family: 24 tests. PASS_STRONG=7, PASS_WEAK=12, FAIL=5.
OOS Pearson positive: 20/24. OOS positive-vs-nonpositive conditional return spread positive: 19/24. Full-sample Pearson BH q<=0.05: 0/24.

## Fixed results

| Indicator | Asset | H | N | Train r | OOS r | OOS rho | OOS +signal − <=0 return | BH q | Class |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| BANK_IMPULSE | DBC | 3M | 243 | -0.125 | +0.091 | +0.127 | +1.05 pp | +0.808 | PASS_WEAK |
| BANK_IMPULSE | DBC | 6M | 240 | +0.009 | -0.019 | +0.117 | +2.39 pp | +0.987 | PASS_WEAK |
| BANK_IMPULSE | DBC | 12M | 234 | +0.001 | +0.117 | +0.256 | +9.69 pp | +0.709 | PASS_STRONG |
| BANK_IMPULSE | GLD | 3M | 258 | +0.140 | +0.168 | +0.023 | +1.11 pp | +0.348 | PASS_STRONG |
| BANK_IMPULSE | GLD | 6M | 255 | +0.063 | +0.239 | +0.269 | +8.44 pp | +0.348 | PASS_STRONG |
| BANK_IMPULSE | GLD | 12M | 249 | +0.017 | +0.084 | +0.076 | +3.04 pp | +0.709 | PASS_STRONG |
| BANK_IMPULSE | QQQ | 3M | 326 | -0.032 | +0.240 | +0.282 | +5.97 pp | +0.709 | PASS_WEAK |
| BANK_IMPULSE | QQQ | 6M | 323 | +0.004 | +0.146 | +0.125 | +2.18 pp | +0.709 | PASS_STRONG |
| BANK_IMPULSE | QQQ | 12M | 317 | +0.009 | +0.127 | +0.197 | +8.64 pp | +0.709 | PASS_STRONG |
| BANK_IMPULSE | SPY | 3M | 400 | -0.161 | +0.191 | +0.314 | +4.16 pp | +0.709 | PASS_WEAK |
| BANK_IMPULSE | SPY | 6M | 397 | -0.066 | +0.085 | +0.081 | +0.57 pp | +0.987 | PASS_WEAK |
| BANK_IMPULSE | SPY | 12M | 391 | -0.003 | +0.118 | +0.161 | +4.29 pp | +0.709 | PASS_WEAK |
| TREASURY_DURATION_MIX | DBC | 3M | 243 | -0.115 | -0.099 | -0.163 | -3.77 pp | +0.695 | FAIL |
| TREASURY_DURATION_MIX | DBC | 6M | 240 | -0.037 | -0.024 | -0.159 | -6.11 pp | +0.987 | FAIL |
| TREASURY_DURATION_MIX | DBC | 12M | 234 | -0.108 | +0.084 | -0.250 | -12.58 pp | +0.987 | FAIL |
| TREASURY_DURATION_MIX | GLD | 3M | 258 | +0.022 | +0.084 | +0.208 | +3.66 pp | +0.709 | PASS_STRONG |
| TREASURY_DURATION_MIX | GLD | 6M | 255 | -0.110 | -0.075 | +0.089 | -0.28 pp | +0.700 | FAIL |
| TREASURY_DURATION_MIX | GLD | 12M | 249 | -0.030 | +0.037 | +0.303 | +13.19 pp | +0.987 | PASS_WEAK |
| TREASURY_DURATION_MIX | QQQ | 3M | 300 | -0.102 | +0.170 | +0.106 | +1.25 pp | +0.987 | PASS_WEAK |
| TREASURY_DURATION_MIX | QQQ | 6M | 297 | -0.054 | +0.293 | +0.260 | +4.14 pp | +0.695 | PASS_WEAK |
| TREASURY_DURATION_MIX | QQQ | 12M | 291 | -0.054 | +0.363 | +0.299 | +11.11 pp | +0.376 | PASS_WEAK |
| TREASURY_DURATION_MIX | SPY | 3M | 300 | -0.237 | +0.110 | +0.059 | -0.27 pp | +0.376 | FAIL |
| TREASURY_DURATION_MIX | SPY | 6M | 297 | -0.153 | +0.276 | +0.181 | +1.50 pp | +0.987 | PASS_WEAK |
| TREASURY_DURATION_MIX | SPY | 12M | 291 | -0.131 | +0.498 | +0.422 | +9.42 pp | +0.627 | PASS_WEAK |

## Interpretation

The predeclared directional screen is broadly positive out of sample, but **none of the 24 full-sample Pearson relationships survives BH q<=0.05**. `PASS_STRONG` therefore means only that all four predeclared directional checks were positive; it is not statistical promotion evidence.

The most internally consistent first-pass result is **Bank balance-sheet impulse for GLD**, especially 3M/6M: train and OOS Pearson are both positive, and GLD 6M has OOS Pearson +0.239, OOS Spearman +0.269 and an +8.44 pp OOS positive-vs-nonpositive signal return spread. Bank impulse also passes the directional screen for QQQ 6M/12M and DBC 12M, but the train Pearson values there are close to zero, so those should be treated as fragile rather than robust.

**Treasury duration mix is much less stable.** DBC fails at all 3M/6M/12M horizons. SPY and QQQ show negative train correlations but positive OOS correlations at 6M/12M, which looks regime-sensitive rather than like a stable universal relation. GLD 3M passes the directional screen, but there is no broad horizon consistency.

## Interpretation guard

Strong directional survivors: BANK_IMPULSE/GLD/6M, BANK_IMPULSE/GLD/3M, BANK_IMPULSE/QQQ/6M, BANK_IMPULSE/QQQ/12M, BANK_IMPULSE/DBC/12M, BANK_IMPULSE/GLD/12M, TREASURY_DURATION_MIX/GLD/3M.

Weak directional survivors: TREASURY_DURATION_MIX/SPY/12M, TREASURY_DURATION_MIX/QQQ/12M, TREASURY_DURATION_MIX/QQQ/6M, TREASURY_DURATION_MIX/SPY/6M, BANK_IMPULSE/QQQ/3M, BANK_IMPULSE/SPY/3M, TREASURY_DURATION_MIX/QQQ/3M, BANK_IMPULSE/SPY/12M, BANK_IMPULSE/DBC/3M, BANK_IMPULSE/SPY/6M, TREASURY_DURATION_MIX/GLD/12M, BANK_IMPULSE/DBC/6M.

Do not promote from this run. H.8 uses revised current history rather than exact real-time vintages; MSPD uses a conservative fixed availability lag; Yahoo adjusted closes are a research market-data source and are not independently archived by this runner. Overlapping 3M/6M/12M forward returns also mean ordinary correlation p-values are only diagnostic here. Any candidate use in GMLI would require a separately frozen robustness/promotion protocol and stronger return/source validation.
