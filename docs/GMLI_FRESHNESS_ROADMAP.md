# GMLI Freshness & Data Integrity Roadmap

Status: ACTIVE
Owner: GMLI project
Started: 2026-08-24

## Goal

Improve decision quality by fixing stale data plumbing and replacing brittle/opaque sources with reproducible official-source versions where that is materially better. Historical frozen results remain auditable facts; they are not permanent blockers on a better explicitly versioned engine.

The priority is freshness, auditability and clear separation of ENGINE FACT from CURRENT RESEARCH INFERENCE.

## Guardrails

- Never reconstruct missing frozen input bytes from today's revised public data and call it an exact rerun.
- Historical v1.8b remains `BLOCKED_MISSING_FROZEN_INPUT_BYTES`; a better new version does not rewrite that fact.
- Better sources/methods may advance as explicitly versioned candidates after fixed regression/transfer gates.
- RESEARCH and OVERLAY signals never silently replace CORE.
- Funding remains an overlay and cannot override Money Core.
- Completed-month market structure remains separate from current/live market confirmation.
- Every future promoted Money version must preserve raw source bytes, hashes, transformed matrices, runner version and audit outputs.
- Overlay refreshes remain fail-closed unless their production construction is sufficiently reproduced or explicitly replaced by a better versioned method.

## Pareto priorities

### P0 — Money Core V2 official-source path

The opaque China legacy stitch has been superseded prospectively by `PBOC_OFFICIAL_M2_V2`, a continuous official PBoC HTML Money Supply history with preserved raw bytes/hashes.

Global Money V2 reuses the documented seven-region production architecture:
- US / CN / EA / JP / GB / CA / AU
- prior-year USD money-level share weights
- local-money and USD-translated channels
- 1M publication lag
- rolling 120M z, minimum 36, population ddof=0
- score `50 + (50/3)*z`

Current gate status:
1. [x] Official PBoC V2 source history 2015-01 through 2026-07, 139/139 months.
2. [x] Global Money V2 May-2026 convention regression against v1.8 bridge.
3. [ ] Extend official China history to 2014 if available so the original 2015-2022 signal/train window is fully preserved.
4. [ ] Run fixed transmission-transfer test only on the preselected promoted relationships.
5. [ ] Emit explicit V2 promotion report.
6. [ ] Promote V2 only if transfer quality is robust and production smoke passes.

May-2026 regression result: old bridge USD 9.3258% / FX-neutral 6.1275%; V2 USD 9.341915% / FX-neutral 6.153468%. Deltas are only +0.0161 pp and +0.0260 pp respectively.

Latest full-coverage V2 headline is observation 2026-06, available 2026-07-31: USD YoY 7.956975%, score 55.1121; FX-neutral YoY 5.946277%, score 44.4880. This remains RESEARCH/PROMOTION CANDIDATE until the fixed transmission gate passes.

### P0 — Money nowcast 4/4 automated

US, euro area, Japan and China use scheduled validated official-source refresh with last-good preservation. China uses the official central PBoC monthly Financial Statistics Report and preserves source hashes in the audit/snapshot.

Success condition: US/EA/JP/CN refresh automatically with auditable last-good fallback. **MET.**

### P1 — Funding / Credit / Fiscal refresh

Freshness policy:
- FRESH: <=35 days
- AGING: 36-60 days
- STALE: >60 days

Current refreshability audit:
- **Funding:** `BLOCKED_BASELINE_MISMATCH`. Construction is documented, but exact production July baseline is not reproduced yet. A better version may replace it if explicitly validated.
- **Credit/Velocity:** `BLOCKED_MISSING_FROZEN_CONSTRUCTION_PROVENANCE`. Do not infer the old formula; redesign only as an explicit new version if useful.
- **Fiscal:** prospective raw-source capture is active. Production strict-actual-release score remains unchanged until a valid refresh/version gate is proven.

### P1 — Current market confirmation

**IMPLEMENTED.** Dashboard and `/api/report` distinguish completed-month structural confirmation from a current SPY/QQQ/GLD/DBC layer using latest completed session, 1M return, 50D/200D trend and divergence flags.

### P1 — Data Health block

**IMPLEMENTED.** Canonical `/api/report` shows Core/candidate freshness, per-country nowcast, overlays, current/structural market context and overlay refreshability/last-good state.

### P2 — Historical v1.8b blocker

Closed as a historical audit fact. Do not spend further effort trying to reconstruct missing Aug-15 bytes. New official-source V2 work proceeds independently.

### P3 — Secondary research gaps

Defer HYG, BTC, VNQ/VEA and other new asset-specific models until Money V2 transfer/promotion is resolved.

## Execution order

### Phase 1 — Freshness infrastructure
- [x] Canonical Data Health block
- [x] China scheduled nowcast ingestion
- [x] Fiscal prospective source archive
- [x] Explicit overlay freshness/refreshability/last-good status

### Phase 2 — Money V2 prospective promotion
- [x] Preserve official PBoC raw bytes and hashes
- [x] Continuous official China V2 source archive
- [x] Rebuild Global Money headline from official production sources
- [x] May-2026 bridge convention regression
- [ ] Preserve Global Money V2 source/transformed candidate archive on schedule
- [ ] Extend China source history to 2014 if official archive permits
- [ ] Fixed transmission transfer gate
- [ ] Explicit V2 promotion contract/report
- [ ] Promote only on PASS

### Phase 3 — Current market confirmation
- [x] Daily SPY/QQQ/GLD/DBC current confirmation layer
- [x] Keep completed-month structural signal separate
- [x] Surface divergences in `/api/report` and dashboard

### Phase 4 — Production hardening
- [x] Main-only write-capable Money nowcast refresh
- [x] PBoC V2 main-only source capture
- [ ] Global Money V2 main-only candidate capture — PR #11 pending final merge/production capture
- [x] Failure preserves validated production Core
- [x] Audit artifacts retained for implemented prospective captures
- [x] Smoke-tested current production decision endpoints after prior production changes

## Progress log

### 2026-08-24 — Data Health / nowcast / market-confirmation infrastructure
- Canonical Data Health and explicit freshness shipped.
- Official-source 4/4 Money nowcast shipped.
- Current SPY/QQQ/GLD/DBC confirmation layer shipped separately from monthly structure.
- Funding/Credit/Fiscal refreshability is explicit rather than silently assumed.

### 2026-08-24 — Official PBoC M2 V2 source milestone
- Replaced the prospective opaque China legacy dependency with official PBoC Money Supply HTML tables.
- Full archive is continuous 2015-01 through 2026-07: 139 months, zero missing.
- Exact source HTML bytes and SHA-256 provenance are preserved.
- Latest 2026-07 official level is 3,555,077.24 RMB 100m; derived YoY ~7.7483%, consistent with the rounded 7.7% monthly report cross-check.
- This is a new versioned source candidate, not a false historical v1.8b exact rerun.

### 2026-08-24 — Global Money V2 headline regression PASS
- Reconstructed the documented seven-region production construction on current official sources.
- Provider transport normalization was made explicit for BoJ, BoE and RBA without changing economic logic.
- Recovered the documented Euro Area split: ECB M2 stock level for accounting/weights; official comparable ECB M2 annual-growth series for the signal.
- May-2026 V2 reproduces the old bridge nearly exactly: USD 9.341915% vs 9.3258%; FX-neutral 6.153468% vs 6.1275%.
- Latest full-coverage candidate (2026-06, available 2026-07-31): USD score 55.1121, FX-neutral score 44.4880.
- No Core value was modified. Next material gate is fixed transmission transfer, preferably after extending official China history through 2014.

## Definition of done

GMLI is materially improved when:
1. Money V2 has a reproducible official-source history and fixed transfer evidence sufficient for an explicit promotion decision.
2. Money nowcast remains verified 4/4 without brittle request-time scraping. **DONE.**
3. Funding/credit/fiscal freshness is explicit and automated/re-versioned where provenance permits.
4. Current market confirmation remains separate from structural completed-month confirmation. **DONE.**
5. `/api/report` makes stale or non-refreshable decision-critical inputs impossible to miss. **DONE.**
6. Historical frozen results remain auditable, while demonstrably better versioned solutions are allowed to replace them prospectively.
