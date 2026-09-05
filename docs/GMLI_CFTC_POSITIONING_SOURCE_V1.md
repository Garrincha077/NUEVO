# GMLI CFTC Positioning Source Contract v1

Status: ACTIVE RESEARCH SOURCE CONTRACT
Evidence tier: RESEARCH
Role: ENTRY_QUALITY_ONLY
Scoring effect: NONE
Automatic weight change: 0

## Purpose

Provide a reproducible and resilient source path for the existing GMLI CFTC positioning factor used by the Contrarian Trend Radar and Opportunity entry-quality layer.

This contract fixes source freshness/reliability only. It does **not** promote CFTC positioning to CORE or OVERLAY and does not change the existing positioning methodology, thresholds, direct mappings, basket definitions, strategic eligibility rules or the 10-point conviction rubric.

## Official source

Primary refresh source:
- CFTC Historical Compressed **Traders in Financial Futures (TFF) — Futures Only** annual ZIP files
- CFTC Historical Compressed **Disaggregated — Futures Only** annual ZIP files
- official host: `https://www.cftc.gov/files/dea/history/`

The refresh runner downloads every annual file needed for the existing rolling source window and records SHA-256, byte size, ZIP member and parsed-row count in:
- `research/cftc-positioning/latest/manifest.lock.json`

Active guarded snapshot:
- `research/cftc-positioning/latest/positioning.json`

Runner:
- `scripts/refresh-cftc-positioning.py`

## Frozen semantics preserved

The source migration preserves the existing GMLI positioning semantics:
- futures-only data;
- net speculative position / open interest;
- existing 3Y percentile semantics with the pre-existing one-month source buffer;
- sample-standard-deviation z-score;
- contrarian-friendly threshold: percentile <= 25;
- crowded threshold: percentile >= 75;
- existing direct futures mappings;
- existing transparent DBC and DBA component averages.

No parameter, asset, horizon, lag, threshold or subperiod search is allowed as part of this source refresh.

## Direct mappings

The guarded source contract must keep direct positioning available for the four core Radar assets that already have CFTC mappings:
- SPY — S&P 500 TFF leveraged money
- QQQ — Nasdaq-100 TFF leveraged money
- GLD — Gold Disaggregated managed money
- DBC — existing crude/copper/corn/wheat Disaggregated managed-money percentile composite

Other existing direct/research mappings remain unchanged where source rows exist.

Assets without sufficiently direct CFTC mapping remain missing. In particular, the source refresh must not invent mappings for HYG, VNQ, EEM, VEA or BTC merely to fill the factor.

## Freshness / fail-closed guards

A refresh passes only when:
- official annual ZIPs are fetched and parsed successfully;
- a latest CFTC report date exists;
- latest report age is between 0 and 14 days at refresh time;
- SPY, QQQ, GLD and DBC direct/core mappings are available;
- output stays `evidence_tier = RESEARCH` and `role = ENTRY_QUALITY_ONLY`;
- `methodology_changed = false`;
- `scoring_effect = NONE`;
- `automatic_weight_change = 0`.

Failed refreshes do not create a new snapshot. GitHub Pages uses its standard per-layer last-good fallback behavior.

## Runtime source order

`lib/cftc-positioning.js` uses:
1. the latest guarded archived official CFTC snapshot when available;
2. the legacy `publicreporting.cftc.gov` PRE/Socrata path only when no guarded archived snapshot exists.

A PRE/Socrata outage therefore must not erase a previously verified positioning snapshot.

## Automation

Dedicated workflow:
- `.github/workflows/gmli-cftc-positioning-refresh.yml`

Schedule:
- weekly Friday after the normal CFTC weekly release window;
- manual dispatch is also supported.

Successful non-PR refreshes:
1. run source/freshness/mapping guards;
2. archive the last-good snapshot + manifest on `main` when changed;
3. dispatch the verified GitHub Pages workflow.

GitHub Pages fetch-first also runs the same CFTC refresh as a RESEARCH layer before building the static snapshot. A CFTC failure may fall back only this layer and must never block or modify Money Core, Funding V2, Fiscal V2 or Market Confirmation methodology.

## Production verification

A change is considered live only after:
- guarded CFTC workflow passes;
- normal GMLI source / Pages guards pass;
- GitHub Pages build and deploy pass;
- `gh-pages/api/positioning.json` exposes available direct mappings rather than a transport-level `fetch failed` state;
- `gh-pages/api/status.json` no longer reports CFTC positioning as UNKNOWN when a valid guarded snapshot exists;
- `gh-pages/api/refresh-status.json` reports the CFTC layer refresh/fallback outcome.

Git commit alone is not production evidence.
