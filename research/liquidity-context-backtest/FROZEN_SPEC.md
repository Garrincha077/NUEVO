# GMLI Liquidity Context backtest — frozen research specification v1.1

Status: RESEARCH ONLY / NOT PROMOTED

## Purpose
Test whether the two existing `GMLI_LIQUIDITY_CONTEXT_V1` diagnostics contain stable forward information for the existing GMLI core asset set. This research must not change Money Core, Funding, Fiscal, Market Confirmation, conviction weights or any current Liquidity Context semantics.

## Indicators — frozen before results

### 1. Bank balance-sheet impulse
Source: Federal Reserve H.8. Production identifies the FRED series `TLAACBW027SBOG`; the historical runner uses the Federal Reserve Data Download Program equivalent series `B1151NCBA` (Total Assets, All Commercial Banks, seasonally adjusted) because the FRED CSV endpoint timed out in GitHub Actions before any empirical result was produced.

For each monthly endpoint, use the latest weekly observation in that month and reproduce the production construction:
- current 13W growth = pct change from approximately 91 days earlier;
- prior 13W growth = pct change between approximately 182 and 91 days earlier;
- bank impulse = current 13W growth - prior 13W growth.

Research sign hypothesis: higher / positive bank impulse is more liquidity-supportive.

Conservative availability rule: weekly H.8 observation is treated as available `observation_date + 14 calendar days`. Forward returns begin from the first month-end price after that availability date.

### 2. Treasury duration mix proxy
Source: U.S. Treasury Fiscal Data MSPD Table 1, Debt Held by the Public, marketable securities.

Production construction:
- short/floating = Bills + FRNs;
- fixed duration = Notes + Bonds + TIPS;
- short/floating share = short/floating / (Bills + Notes + Bonds + TIPS + FRNs);
- signal = current short/floating share minus the share approximately 3 months earlier.

Research sign hypothesis: a higher / positive shift toward short/floating composition is more liquidity-supportive.

Conservative availability rule: each month-end MSPD observation is treated as available `record_date + 7 calendar days`. Forward returns begin from the first month-end price after that availability date.

## Assets and horizons — fixed
Assets: `SPY`, `QQQ`, `GLD`, `DBC` only.

Forward horizons: `3M`, `6M`, `12M` only.

No secondary asset expansion, no lag search, no alternate window search, no threshold search, no sign flipping after results.

## Market data
Primary research market source: Yahoo Finance chart API using monthly **adjusted closes**, consistent with the Yahoo source family already used by the canonical GMLI current-market implementation. Stooq monthly data was the initially specified source but returned no usable SPY data in GitHub Actions; this source substitution was frozen before any backtest result was produced and changes no asset, horizon, signal or evaluation rule.

Adjusted-close forward returns are used. This is still a research return source and not a final promotion-grade independently archived return dataset.

## Evaluation — fixed
For every indicator × asset × horizon:
- chronological 70% train / 30% OOS split after alignment;
- Pearson correlation train, OOS and full sample;
- Spearman correlation OOS and full sample;
- OOS mean forward return when signal is positive vs non-positive;
- OOS difference in mean forward returns (`positive - non_positive`).

Primary robustness classification:
- `PASS_STRONG`: train Pearson > 0, OOS Pearson > 0, OOS Spearman > 0 and OOS conditional-return difference > 0;
- `PASS_WEAK`: at least 3 of those 4 directional checks are positive;
- `FAIL`: fewer than 3 directional checks are positive.

This classification is directional robustness only; it is not a statistical promotion gate.

## Multiple-testing / interpretation guard
The family contains 24 fixed tests (2 indicators × 4 assets × 3 horizons). Raw p-values are diagnostic only. Benjamini-Hochberg q-values over the 24 full-sample Pearson tests are reported to prevent cherry-picking, but no production promotion can occur from this exploratory run alone.

## Historical-data caveats
- H.8 history is current revised history, not exact historical real-time vintages.
- MSPD history is official monthly history but the test uses a conservative fixed availability lag rather than exact historical release timestamps.
- Yahoo adjusted closes are a research market-data source; exact provider adjustment history is not independently archived by this runner.

Therefore this run is `RESEARCH_DIAGNOSTIC`, not CORE or OVERLAY promotion evidence.
