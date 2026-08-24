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

Current scheduled refresh already handles US, euro area, Japan and USD translation. China is preserved as last verified because a stable official PBoC machine-readable parser is not yet validated.

Tasks:

- Validate a stable PBoC source/ingestion path.
- Add `refresh_china()` with date regression checks, YoY sanity checks and last-good preservation.
- Include China in refresh audit output.
- Keep request-time live parsing disabled; scheduled verified snapshots remain the intended path.

Success condition: US/EA/JP/CN refresh automatically with auditable last-good fallback.

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
- [ ] Add canonical Data Health block
- [ ] Validate/add China scheduled ingestion
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
- [ ] Failure preserves last verified data
- [ ] Audit artifacts retained
- [ ] Deploy to existing `gmli-fred-dashboard`
- [ ] Smoke-test `/api/status`, `/api/report`, `/api/money-nowcast`, `/api/decision`

## Definition of done

GMLI is materially improved when:

1. A newer Money vintage can be promoted prospectively with fully preserved inputs.
2. Money nowcast is verified 4/4 without brittle request-time scraping.
3. Funding/credit/fiscal freshness is explicit and automated.
4. Current market confirmation is separated from structural completed-month confirmation.
5. `/api/report` makes stale decision-critical inputs impossible to miss.
6. Frozen methodology remains unchanged.
