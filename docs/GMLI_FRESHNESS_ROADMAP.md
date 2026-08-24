# GMLI Freshness & Data Integrity Roadmap

Status: ACTIVE
Owner: GMLI project
Started: 2026-08-24
Last updated: 2026-08-24

## Goal

Improve decision quality by keeping the decision-critical GMLI stack fresh, reproducible and auditable while preserving a strict separation between ENGINE FACT, OVERLAY and CURRENT RESEARCH INFERENCE.

Pareto rule: finish the few layers that can materially change the 3–12M allocation/risk decision before adding more indicators or asset-specific research.

## Current production state

Active Money Core:

`GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL`

Current promoted vintage:
- observation month: 2026-06
- available date: 2026-07-31
- USD-translated broad-money YoY: 7.956975%
- FX-neutral broad-money YoY: 5.946277%
- FX contribution: approximately +2.010698 pp
- USD Money score: 55.1121 — NEUTRAL
- FX-neutral Money score: 44.4880 — NEUTRAL
- fixed transmission transfer gate: 6/6 PASS

The 2026-02-28 Core is now HISTORICAL REFERENCE only.

Historical v1.8b remains `BLOCKED_MISSING_FROZEN_INPUT_BYTES`. This means only that the missing original frozen bytes cannot be exact-rerun. It does not block the separately validated and promoted Money V2.

Primary decision surface:
- Vercel `/api/report` when current and available
- verified GitHub Pages snapshot when Vercel is unavailable/stale
- repository `Garrincha077/NUEVO` remains source-of-truth for engine code, frozen contracts, history, CI and promotion evidence

GitHub Pages:
- https://garrincha077.github.io/NUEVO/
- verified static Core/History/Radar snapshot
- automatic rebuild on relevant `main` changes and daily schedule
- fail-closed if active Money Core and history disagree

Current hosting note: Money V2 is active in the repository/verified Pages production path. Vercel canonical catch-up remains a hosting/deployment task when Vercel build limits allow; do not treat a stale Vercel frontend as evidence that the promoted engine reverted.

## Guardrails

- Never reconstruct missing frozen bytes from current revised public data and call it an exact rerun.
- Historical v1.8b blocker remains an audit fact.
- Frozen methodology must not be silently retuned.
- Better sources/methods may advance only as explicit versioned candidates with relevant regression/promotion gates.
- RESEARCH and OVERLAY signals never silently replace CORE.
- Funding remains an OVERLAY and cannot override Money Core by itself.
- Completed-month structural market confirmation remains separate from current/live market confirmation.
- Every future promoted Money version must preserve source provenance, transformed data, runner/version information and audit outputs.
- Overlay refreshes remain fail-closed unless the old production construction is reproduced or explicitly replaced by a better versioned method.

## Pareto priorities

### P0 — Money Core V2 official-source path — DONE

The opaque China legacy stitch has been superseded prospectively by `PBOC_OFFICIAL_M2_V2` and promoted through Global Money V2.

2014 China rows are explicit comparable accounting bases derived from official 2015 PBoC components:

`implied_2014_base_m = precise_2015_level_m / (1 + official_2015_yoy_m / 100)`

They remain `ACCOUNTING_SEED_ONLY`, `observed_stock: false`; they are not claimed as observed 2014 M2 history or recovered frozen bytes.

Global Money V2 production architecture:
- US / CN / EA / JP / GB / CA / AU
- prior-year USD money-level share weights
- USD-translated and FX-neutral channels
- 1M publication lag
- rolling 120M z-score, minimum 36, population ddof=0
- score `50 + (50/3)*z`

Promotion chain:
1. [x] Official PBoC V2 precision history
2. [x] 12/12 official-component 2014 comparable accounting seed
3. [x] May-2026 convention regression against the v1.8 bridge
4. [x] Fixed transfer test on only the six already-promoted relationships: 6/6 PASS
5. [x] Explicit V2 promotion contract/report
6. [x] Active Core integration while preserving historical Core/audit facts
7. [x] Automated active-vintage sync after official-source build + regression + 6/6 gate
8. [x] `/api/history` monthly Money history contract
9. [x] GitHub Pages resilient production snapshot
10. [x] YoY + Money-score history charts with 3Y/5Y/MAX views and touch-friendly explainers

May-2026 regression:
- old bridge USD 9.3258% / FX-neutral 6.1275%
- V2 USD 9.341915% / FX-neutral 6.153468%
- deltas +0.0161 pp / +0.0260 pp

Fixed transmission result, with no asset/horizon/lag/parameter search and no new FDR claim:
- SPY USD accel3 12M: train Pearson +0.4473; OOS Pearson +0.3613; OOS Spearman +0.3359
- QQQ USD accel3 12M: +0.3897; +0.5663; +0.5589
- GLD FX-neutral accel3 12M: +0.0872; +0.5903; +0.5657
- DBC USD level 6M: +0.5892; +0.6324; +0.5431
- DBC USD level 12M: +0.6340; +0.6344; +0.5935
- DBC FX-neutral level 6M: +0.6270; +0.7080; +0.6849

Promotion report:
`research/global-money-v2/GMLI_GLOBAL_MONEY_V2_PROMOTION_REPORT.md`

### P0 — Money nowcast 4/4 automated — DONE

US, euro area, Japan and China use scheduled validated official-source refresh with last-good preservation. China uses the official central PBoC monthly Financial Statistics Report and preserves source provenance.

### P1 — Funding V2 — NEXT

Current legacy Funding status:
`BLOCKED_BASELINE_MISMATCH`

The old construction is documented but the exact production July baseline is not reproduced cleanly enough to keep extending it by assumption.

Next action: build an explicit `GMLI_FUNDING_V2` candidate rather than patching the legacy baseline indefinitely.

Pareto design goal:
- simple, reproducible and refreshable
- output only `SUPPORTIVE / NEUTRAL / RESTRICTIVE` plus compact score/conviction modifier
- remain an OVERLAY, never Money Core
- prefer a small number of robust inputs such as real yields, front-end policy rate/funding pressure, term premium and central-bank/reserve liquidity measures
- add Treasury plumbing only if it materially improves the decision

Funding V2 gate:
1. [ ] Freeze candidate source definitions and publication/freshness rules
2. [ ] Build reproducible history and preserve provenance
3. [ ] Compare with legacy Funding direction around known historical windows
4. [ ] Test only whether the overlay materially improves regime conviction/asset interpretation; avoid broad parameter search
5. [ ] Promote only if clearly more reliable/useful than the legacy baseline
6. [ ] Add scheduled refresh and Data Health status

### P1 — Fiscal refresh — AFTER FUNDING V2

Prospective raw-source capture is active.

Next action after Funding V2: either reproduce the existing strict-actual-release construction sufficiently or replace it with a clearly versioned Fiscal V2. Do not change production Fiscal merely because a new raw observation exists.

### P2 — Credit / Velocity — DEFER

Current status:
`BLOCKED_MISSING_FROZEN_CONSTRUCTION_PROVENANCE`

Do not reverse-engineer the old formula by guesswork. Build a new Credit/Velocity version only if Money + Funding + Fiscal leave a material decision gap.

### P1 — Current market confirmation — DONE

Dashboard and `/api/report` distinguish completed-month structural confirmation from a current SPY/QQQ/GLD/DBC layer using latest completed session, 1M return, 50D/200D trend and divergence flags.

### P1 — Data Health — DONE

Canonical `/api/report` surfaces Money freshness, nowcast, overlays, market context and refreshability/last-good state. `/api/history` exposes the promoted monthly Money history used by the Pages charts.

### P2 — Historical v1.8b blocker — CLOSED

Historical audit fact only. Do not spend more effort trying to reconstruct missing Aug-15 frozen bytes.

### P3 — Secondary asset research — UNBLOCKED BUT DEFERRED

Money V2 production is resolved, so HYG, BTC, VNQ/REIT, VEA/EEM and other asset-specific work is no longer blocked by Money promotion.

However, defer broad expansion until Funding V2 is resolved. After that, add only 1–2 asset families at a time when they can materially improve allocation decisions.

## Execution order

### Phase 1 — Freshness infrastructure — DONE
- [x] Canonical Data Health block
- [x] China scheduled nowcast ingestion
- [x] Fiscal prospective source archive
- [x] Explicit overlay freshness/refreshability/last-good status

### Phase 2 — Money V2 promotion — DONE
- [x] Official PBoC raw/provenance archive
- [x] Continuous official China V2 precision source
- [x] Official-component 2014 comparable accounting seed
- [x] Global Money V2 official-source rebuild
- [x] May-2026 bridge regression
- [x] Main-scheduled source/transformed archive
- [x] Fixed 6/6 transmission transfer gate
- [x] Explicit promotion contract/report
- [x] Active Money V2 Core integration
- [x] Automated promoted-vintage refresh guard

### Phase 3 — Current market confirmation — DONE
- [x] Daily SPY/QQQ/GLD/DBC current layer
- [x] Completed-month structural signal remains separate
- [x] Divergences surfaced in `/api/report` and dashboard

### Phase 4 — Production resilience / observability — DONE EXCEPT VERCEL HOSTING CATCH-UP
- [x] Main-only write-capable Money nowcast refresh
- [x] PBoC V2 main-only source capture
- [x] Global Money V2 gated active-Core refresh
- [x] Failure preserves validated last-good Core
- [x] Historical Core and v1.8b blocker preserved
- [x] `/api/history` production contract
- [x] GitHub Pages verified resilient snapshot
- [x] Daily/triggered Pages rebuild
- [x] Money YoY + score history charts
- [x] Touch/mobile explainers
- [ ] Vercel canonical deployment catch-up when build-rate limits permit

### Phase 5 — Funding V2 — ACTIVE NEXT
- [ ] Freeze minimal candidate inputs/semantics
- [ ] Build reproducible historical series
- [ ] Validate against legacy directional behavior where comparable
- [ ] Run narrow usefulness/conviction gate
- [ ] Promote or reject without retuning to force PASS
- [ ] Automate refresh + Data Health

### Phase 6 — Fiscal versioning
- [ ] Resolve legacy reproduction vs explicit Fiscal V2
- [ ] Validate strict actual-release semantics
- [ ] Automate only after version gate passes

### Phase 7 — Selective asset expansion
- [ ] Reassess HYG / BTC / REIT / ex-US candidates after Funding V2
- [ ] Add only relationships with clear incremental allocation value
- [ ] Keep new research separate from Core until promoted

## Progress log

### 2026-08-24 — Money V2 source / regression / transfer
- Official PBoC M2 V2 source path established with preserved provenance.
- Flawed attempt to treat irregular 2014 search results as observed history was rejected.
- 2014 became explicit comparable accounting seed only.
- Global Money V2 reproduced the May bridge within very small deltas.
- Fixed six-relation transmission transfer gate passed 6/6 without retuning.

### 2026-08-24 — Money V2 production promotion
- `GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL` became active Money Core.
- Current promoted vintage: observation 2026-06, available 2026-07-31.
- Previous 2026-02-28 Core retained as historical reference.
- Historical v1.8b missing-byte blocker retained as audit fact only.
- Active-vintage refresh is gated by official-source rebuild, May bridge regression and fixed 6/6 transfer before sync.

### 2026-08-24 — GitHub Pages resilience / history
- Added `/api/history` backed by promoted `research/global-money-v2/latest/global_money_v2.csv`.
- Pages build fails closed if the latest history point and active Core disagree.
- GitHub Pages became verified resilient frontend/snapshot while Vercel deployment is constrained.
- Added YoY broad-money and Money-score charts with USD-translated / FX-neutral series, 3Y/5Y/MAX ranges, reference bands and mobile/touch explainers.

### 2026-08-24 — Next priority selected
- Money Core work is no longer the primary development bottleneck.
- `GMLI_FUNDING_V2` is now the next active P1 because Funding remains the largest stale/non-reproducible conviction modifier.
- Fiscal follows Funding V2.
- Credit/Velocity and broader asset expansion remain deferred under the Pareto rule.

## Definition of done

GMLI core infrastructure is materially healthy when:
1. Money Core has reproducible official-source history, validated transfer evidence and a guarded automatic promoted-vintage path. **DONE.**
2. Money nowcast is verified 4/4 with last-good preservation. **DONE.**
3. Current market confirmation remains separate from structural completed-month confirmation. **DONE.**
4. `/api/report` and `/api/history` make freshness/history visible and internally consistent. **DONE.**
5. A resilient published snapshot remains available even when the primary host has deployment issues. **DONE via GitHub Pages.**
6. Funding becomes reproducible, fresh and explicitly versioned without being allowed to overwrite Money Core. **NEXT.**
7. Fiscal is refreshed/re-versioned after Funding if it still adds material decision value.
8. Historical frozen results remain auditable while demonstrably better versioned successors can replace them prospectively.
