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
- Overlay refreshes are fail-closed: a scheduler may advance an overlay only after its exact July 2026 production baseline is regression-matched from documented/preserved inputs.

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

Success condition: US/EA/JP/CN refresh automatically with auditable last-good fallback. **MET.**

### P1 — Funding / Credit / Fiscal refresh

Automate monthly validated refresh for these overlays without changing their scoring logic.

Freshness policy:
- FRESH: <=35 days
- AGING: 36-60 days
- STALE: >60 days

Current refreshability audit:
- **Funding:** `BLOCKED_BASELINE_MISMATCH`. Frozen 5/5 research report gives July z -0.796 / 36.73, while production baseline is z -0.8378753441 / 36.0354109320. Exact production baseline must be reproduced before automation.
- **Credit/Velocity:** `BLOCKED_MISSING_FROZEN_CONSTRUCTION_PROVENANCE`. Final July score is preserved, but exact frozen component/source construction has not been recovered. Do not redesign it.
- **Fiscal:** `PROSPECTIVE_SOURCE_CAPTURE_IMPLEMENTED_SCORE_REFRESH_BLOCKED`. Frozen strict actual-release construction is documented and its July z/score exactly matches production. Because the exact historical strict-release runner/vintages were not recovered, current revised history will not be substituted. A prospective raw-source archive now preserves future source bytes, hashes and first-seen timing; production score remains locked until a strict-release transform can reproduce the July baseline exactly under CI.

Success condition: each overlay carries source date, age, freshness label, last verified status and an auditable refreshability state; only regression-matched overlays may auto-advance.

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

Canonical `/api/report` freshness must show validated Core, candidate, per-country nowcast, overlays, market structure, positioning, oldest critical input and overlay refreshability/last-good state.

Freshness affects conviction, not the underlying Money score.

### P2 — Close historical v1.8b blocker

Keep the old candidate as RESEARCH evidence only. Do not spend further work reconstructing missing Aug-15 frozen bytes. Re-open only if original preserved inputs are recovered.

### P3 — Secondary research gaps

Defer HYG, BTC, VNQ/VEA and other new asset-specific models until freshness and Core promotion plumbing are reliable.

## Execution order

### Phase 1 — Freshness infrastructure
- [x] Add canonical Data Health block
- [x] Validate/add China scheduled ingestion
- [ ] Add Funding/Credit/Fiscal scheduled refresh — refreshability audit complete; Fiscal prospective capture implemented pending CI/production verification; Funding/Credit remain blocked
- [x] Add explicit freshness labels, overlay refreshability and last-good status

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
- [ ] Smoke-test first prospective Fiscal raw-source capture; verify production Fiscal score remains unchanged

## Progress log

### 2026-08-24 — Data Health slice complete
- `/api/report` upgraded to `gmli-report-v1.2` with canonical `data_health`.
- Production correctly reports `DEGRADED_CORE_STALE` and identifies validated Money Core 2026-02-28 as the oldest decision-critical input.
- Frozen Money scores and methodology were unchanged.

### 2026-08-24 — Prospective promotion plumbing started
- Added fail-closed source manifest and raw-input capture runner with exact bytes, SHA-256, retrieval provenance, manifest hash, runner hash and frozen-state hash.
- Capture refuses promotion-readiness while any required source remains unresolved and never modifies `lib/state.js`.

### 2026-08-24 — BoE / BoC / BoJ prospective sources validated
- Official BoJ M2, BoE M4 and BoC M2 paths passed live CI validation.
- Frozen Core values remain unchanged.

### 2026-08-24 — Exact-ticker market raw-source contract validated
- Exact set: SPY, QQQ, GLD, DBC, IEF, TLT, BIL.
- Six Yahoo adjusted-close sources plus Digrin BIL passed CI; raw capture preserves independent bytes/hashes.
- Prospective Core capture still fails closed on `CN_M2`.

### 2026-08-24 — Official PBoC RESEARCH nowcast production complete
- PBoC filtered-search/report parser passed CI and was merged in PR #5.
- Scheduled refresh committed the verified 2026-07 snapshot: M2 355.51tn CNY, YoY 7.7%, with source hashes.
- Production smoke tests returned 200 for `/api/status`, `/api/report`, `/api/money-nowcast`, `/api/decision`.
- Prospective Core `CN_M2` remains a separate unresolved stitched-level problem.

### 2026-08-24 — Overlay refreshability audit
- Funding construction is documented but its published July 5/5 baseline does not equal production; automation is blocked until exact regression matching is recovered.
- Fiscal strict actual-release construction is documented and its July strict z 0.1523733869 exactly matches production.
- Credit/Velocity exact construction/source provenance could not be recovered; automation is blocked rather than guessed.
- `/api/report` exposes last-good dates and refresh blockers without changing scores.

### 2026-08-24 — Fiscal prospective source-capture contract
- Exact historical strict-release runner/vintages were not recovered, so current revised FRED history is explicitly not used as an exact historical backfill.
- Added a prospective raw capture for the six documented Fiscal source series: `MTSDS133FMS`, `GDP`, `GFDEBTN`, `A091RC1Q027SBEA`, `FGRECPT`, `FGEXPND`.
- Capture preserves exact FRED CSV bytes, SHA-256, retrieval timestamp, first-observed timestamp for the newest observation, latest observation metadata and date-regression checks.
- `--validate-only` performs a live source test without writing state/files.
- Scheduler stores only source vintages and audit artifacts; it cannot compute or advance the production Fiscal score.
- Unlock condition for score refresh remains: implement strict-release transformation and reproduce the July 2026 production z/score exactly under CI.

## Definition of done

GMLI is materially improved when:
1. A newer Money vintage can be promoted prospectively with fully preserved inputs.
2. Money nowcast is verified 4/4 without brittle request-time scraping. **DONE.**
3. Funding/credit/fiscal freshness is explicit and automated where provenance permits.
4. Current market confirmation is separated from structural completed-month confirmation.
5. `/api/report` makes stale or non-refreshable decision-critical inputs impossible to miss.
6. Frozen methodology remains unchanged.
