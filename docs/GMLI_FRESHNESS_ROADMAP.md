# GMLI Freshness & Data Integrity Roadmap

Status: ACTIVE
Owner: GMLI project
Started: 2026-08-24

## Goal

Improve decision quality by fixing stale data plumbing without changing frozen Money Core methodology, country weights, lags, horizons, thresholds, train/validation split, FX-neutral methodology or FDR rules.

The priority is freshness, auditability and clear separation of ENGINE FACT from CURRENT RESEARCH INFERENCE.

## Guardrails

- Never reconstruct missing frozen input bytes from today's revised public data and call it an exact rerun.
- v1.8b remains `BLOCKED_MISSING_FROZEN_INPUT_BYTES` unless the original preserved bytes are recovered.
- RESEARCH and OVERLAY signals never silently replace CORE.
- Funding remains an overlay and cannot override Money Core.
- Completed-month market structure remains separate from current/live market confirmation.
- Every promoted future Money vintage must preserve raw source bytes, hashes, transformed matrices, runner version and audit outputs.

## Pareto priorities

### P0 — Fresh Money Core

Build a prospective promotion pipeline for the next complete Money vintage:

1. Fetch production-source Money inputs.
2. Preserve raw source bytes immediately.
3. SHA-256 every source file/input.
4. Preserve transformed Money matrix.
5. Record exact Git commit and runner hash.
6. Run existing frozen tests unchanged.
7. Emit explicit promotion contract/report.
8. Promote only on full PASS; otherwise fail closed.

Success condition: a newer formally validated CORE vintage with preserved, reproducible inputs.

### P0 — Money nowcast 4/4 automated

US, euro area, Japan and China now use scheduled validated official-source refresh with last-good preservation. China uses the official central PBoC monthly Financial Statistics Report and preserves source hashes in the audit/snapshot.

Tasks:

- Validate a stable PBoC source/ingestion path. **DONE 2026-08-24.**
- Add `refresh_china()` with date regression checks, YoY sanity checks and last-good preservation. **DONE 2026-08-24.**
- Include China in refresh audit output. **DONE 2026-08-24.**
- Keep request-time live parsing disabled; scheduled verified snapshots remain the intended path. **DONE.**

Success condition: US/EA/JP/CN refresh automatically with auditable last-good fallback. **MET.**

### P1 — Funding / Credit / Fiscal refresh

Automate monthly validated refresh for these overlays without changing their scoring logic.

Freshness policy:

- FRESH: <=35 days
- AGING: 36-60 days
- STALE: >60 days

Success condition: each overlay carries source date, age, freshness label and last verified refresh status.

### P1 — Current market confirmation

Keep existing completed-month structural signal, then add a separate current market layer for SPY, QQQ, GLD and DBC.

Minimum fields:

- latest completed session date
- 1M return
- simple 50D/200D trend state or equivalent minimal trend flag
- divergence vs structural completed-month signal

Optional contextual inputs only when materially useful: DXY and real yields.

Success condition: dashboard distinguishes STRUCTURAL MONTHLY CONFIRMATION from CURRENT MARKET CONFIRMATION.

### P1 — Data Health block

Add one canonical freshness block to `/api/report` and dashboard.

It must show:

- validated Money Core date and age
- production candidate date and age
- per-country Money nowcast dates
- Funding/Credit/Fiscal dates
- market structure date
- CFTC positioning date
- oldest decision-critical input
- explicit status such as HEALTHY / DEGRADED_CORE_STALE

Freshness affects conviction, not the underlying Money score.

### P2 — Close historical v1.8b blocker

Keep the old candidate as RESEARCH evidence only. Do not spend further work reconstructing missing Aug-15 frozen bytes. Re-open only if original preserved inputs are recovered.

### P3 — Secondary research gaps

Defer HYG, BTC, VNQ/VEA and other new asset-specific models until freshness and Core promotion plumbing are reliable.

## Execution order

### Phase 1 — Freshness infrastructure
- [x] Add canonical Data Health block
- [x] Validate/add China scheduled ingestion
- [ ] Add Funding/Credit/Fiscal scheduled refresh
- [ ] Add explicit freshness labels and last-good status

### Phase 2 — Prospective Money promotion
- [ ] Preserve raw bytes for next vintage
- [ ] Preserve hashes and transformed matrix
- [ ] Run frozen guard suite
- [ ] Emit promotion contract
- [ ] Promote only on PASS

### Phase 3 — Current market confirmation
- [ ] Add daily SPY/QQQ/GLD/DBC confirmation layer
- [ ] Keep completed-month structural signal unchanged
- [ ] Surface divergences in `/api/report`

### Phase 4 — Production hardening
- [ ] CI checks for date regression and stale critical data
- [x] Write-capable Money refresh push trigger restricted to `main`
- [ ] Failure preserves last verified data
- [ ] Audit artifacts retained
- [x] Deploy initial Data Health slice to existing `gmli-fred-dashboard`
- [x] Smoke-test `/api/status`, `/api/report`, `/api/money-nowcast`, `/api/decision` for initial Data Health slice
- [x] Smoke-test PBoC scheduled refresh and resulting production deployment

## Progress log

### 2026-08-24 — Data Health slice complete

- `/api/report` upgraded to `gmli-report-v1.2` with canonical `data_health`.
- Production correctly reports `DEGRADED_CORE_STALE` and identifies validated Money Core 2026-02-28 as the oldest decision-critical input.
- Freshness policy is FRESH <=35 days, AGING 36-60 days, STALE >60 days.
- Frozen Money scores and methodology were unchanged.
- CI/frozen Core guards passed and production smoke tests returned HTTP 200.

### 2026-08-24 — Prospective promotion plumbing started

- Added a fail-closed prospective source manifest.
- Added a raw-input capture runner that preserves exact bytes, SHA-256, retrieval provenance, manifest hash, runner hash and frozen-state hash.
- Capture refuses to run as promotion-ready while any required source remains unresolved and never modifies `lib/state.js`.
- Source validation is intentionally separate from capture.

### 2026-08-24 — BoE / BoC / BoJ prospective sources validated

- Added a read-only source validation runner and gated the new paths in CI.
- GitHub Actions fetched all three official sources successfully with HTTP 200 and provider-native series markers:
  - BoJ M2 level `MD02'MAM1NAM2M2MO`.
  - BoE M4 `LPMAUYN`.
  - BoC seasonally adjusted gross M2 `V41552796`.
- Prospective source manifest now has explicit validated fetch paths for US, EA, JP, GB, CA and both AU inputs.
- Frozen Core values remain unchanged.

### 2026-08-24 — Exact-ticker market raw-source contract validated

- v1.2 documentation reconfirmed the frozen exact-ticker set: SPY, QQQ, GLD, DBC, IEF, TLT and BIL.
- Prospective capture supports multipart raw sources with independent bytes and SHA-256 for every part.
- Six Yahoo/yfinance tickers use max-history monthly Chart API responses with adjusted close present; BIL retains the v1.2 Digrin adjusted-price provenance.
- GitHub Actions live-fetched all seven parts successfully with HTTP 200.
- The future transform contract is recorded but not executed by raw capture: 2015-01+, monthly adjusted price, local mirror rounded to 2 decimals.
- `ASSET_ADJUSTED_PRICE_MIRROR` is no longer unresolved. The prospective Core capture still fails closed on `CN_M2`.
- Frozen Core values and all frozen Money methodology parameters remain unchanged.

### 2026-08-24 — Official PBoC RESEARCH nowcast production complete

- Initial unfiltered PBoC search attempt failed closed, proving the gate works.
- Discovery was corrected to the PBoC filtered-search contract (`dr=true`, relevance sort) rather than weakening validation.
- CI passed official central-PBoC report discovery and extraction of report month, M2 balance, M2 YoY and raw-source SHA-256 provenance.
- PR #5 merged to `main` after all source and frozen Core guards passed.
- The write-capable scheduled refresh ran automatically after merge and committed a verified snapshot at 2026-08-24T08:29:10Z.
- China production snapshot: 2026-07, M2 balance 355.51tn CNY, YoY 7.7%, source = official PBoC Financial Statistics Report, with article/search SHA-256 preserved.
- Vercel deployed the refresh commit to production and `/api/status`, `/api/report`, `/api/money-nowcast`, `/api/decision` all returned HTTP 200.
- This resolves the RESEARCH nowcast path only. Prospective Core `CN_M2` remains intentionally unresolved until frozen stitched-level semantics are reproduced and preserved.

## Definition of done

GMLI is materially improved when:

1. A newer Money vintage can be promoted prospectively with fully preserved inputs.
2. Money nowcast is verified 4/4 without brittle request-time scraping. **DONE.**
3. Funding/credit/fiscal freshness is explicit and automated.
4. Current market confirmation is separated from structural completed-month confirmation.
5. `/api/report` makes stale decision-critical inputs impossible to miss.
6. Frozen methodology remains unchanged.
