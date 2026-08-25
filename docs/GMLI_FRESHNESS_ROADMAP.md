# GMLI Freshness & Data Integrity Roadmap

Status: ACTIVE
Owner: GMLI project
Started: 2026-08-24
Last updated: 2026-08-25

## Goal

Keep the decision-critical GMLI stack fresh, reproducible and auditable while preserving a strict separation between CORE, OVERLAY and RESEARCH.

Pareto rule: finish the few layers that can materially change the 3–12M allocation/risk decision before adding more indicators or asset-specific research.

## Current production stack

### Money Core — DONE / ACTIVE

`GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL`

Current promoted vintage at this roadmap update:
- observation month: 2026-06
- available date: 2026-07-31
- USD-translated broad-money YoY: 7.956975%
- FX-neutral broad-money YoY: 5.946277%
- FX contribution: approximately +2.010698 pp
- USD Money score: 55.1121 — NEUTRAL
- FX-neutral Money score: 44.4880 — NEUTRAL
- fixed transmission transfer gate: 6/6 PASS

The 2026-02-28 Core remains HISTORICAL REFERENCE only. Historical v1.8b remains `BLOCKED_MISSING_FROZEN_INPUT_BYTES` as an audit fact only.

### Money nowcast — DONE / ACTIVE

US, euro area, Japan and China are covered 4/4 through scheduled validated official-source refresh with last-good preservation.

### Funding V2 — DONE / ACTIVE OVERLAY

`GMLI_FUNDING_V2_EFFECTIVE_CONDITIONS`

Current promoted vintage at this roadmap update:
- observation month: 2026-06
- available date: 2026-07-31
- score: 37.9684402601
- regime: RESTRICTIVE
- structural support score: 37.9684402601
- observed conditions score: 59.0994961494

Funding V2 is reproducible, guarded and scheduled. It is a bounded OVERLAY and never overrides Money Core.

Promotion evidence:
- Candidate 1 rejected without retuning after 2020 stress failure.
- Candidate 2 fixed stress gate passed 2008-10, 2020-03 and current state.
- Narrow fixed usefulness gate passed 2/2 for DBC 6M/12M.
- No universal equity-return claim.

### Market confirmation — DONE / ACTIVE

Completed-month structural confirmation remains separate from current/live SPY/QQQ/GLD/DBC confirmation and divergence flags.

### Production resilience / observability — DONE

- canonical Vercel production smoke covers `/api/status`, `/api/decision`, `/api/report`, `/api/money-nowcast`, `/api/current-market`, `/api/history`
- GitHub Pages remains verified resilient snapshot
- `/api/history` is runtime-compatible and current
- Data Health exposes active versions/freshness/guardrails

## Guardrails

- Never reconstruct missing frozen bytes from current revised public data and call it an exact rerun.
- Frozen methodology must not be silently retuned.
- Better methods advance only as explicit versioned candidates with regression/promotion gates.
- RESEARCH and OVERLAY signals never silently replace CORE.
- Funding remains a bounded modifier and cannot overwrite Money Core.
- Overlay refreshes fail closed unless the old production construction is reproduced or explicitly replaced by a better versioned method.
- Do not broaden empirical search merely because an interesting secondary correlation appears.

## Research note — Funding equity contrarian effect

Status: **CLOSED / RESEARCH-ONLY / NOT PROMOTED**

A fixed long test of inverted Funding V2 (`100 - effective score`) for SPY/QQQ 12M found a materially positive contrarian relationship in the **2020+ regime**, but not over the broader 2006–2025 history.

Fixed-subperiod raw Pearson:

| Period | SPY | QQQ |
|---|---:|---:|
| 2006-02..2012-12 | -0.524 | -0.422 |
| 2013-01..2019-12 | -0.018 | -0.022 |
| 2020-01+ | +0.413 | +0.549 |

Interpretation: contrarian Funding can make sense in a particular recent regime, but it is not a broad historical equity rule. No production change and no further optimization planned.

Permanent note: `research/funding-equity-contrarian-long/README.md`.

## Pareto priorities

### P0 — Money Core V2 official-source path — DONE

Official PBoC M2 V2 plus Global Money V2 is promoted and guarded. Fixed six-relation transmission transfer remains 6/6 PASS.

Promoted transmission relationships:
- SPY USD 12M accel3
- QQQ USD 12M accel3
- GLD FX-neutral 12M
- DBC USD 6M
- DBC USD 12M
- DBC FX-neutral 6M

### P0 — Money nowcast 4/4 — DONE

Scheduled validated official-source refresh with last-good preservation.

### P1 — Funding V2 — DONE

Completed promotion, active integration, guarded refresh, provenance archive and Data Health exposure.

### P1 — Fiscal refresh/versioning — ACTIVE NEXT

Current production Fiscal baseline remains:
- mode: `STRICT_ACTUAL_RELEASE`
- z: `0.1523733868591229`
- score: `52.539556447652046`
- July-2026 production reference

Prospective raw-source capture is already active for:
- `MTSDS133FMS`
- `GDP`
- `GFDEBTN`
- `A091RC1Q027SBEA`
- `FGRECPT`
- `FGEXPND`

The prospective archive preserves raw bytes, retrieval time, SHA-256 and latest-observation metadata but does **not** compute or advance the production Fiscal score.

Next action:
1. inspect active Fiscal state and latest prospective manifest;
2. attempt strict legacy reproduction only if historical release semantics are recoverable without guesswork;
3. if not, stop legacy reverse-engineering and build an explicit versioned Fiscal V2 candidate;
4. freeze sources/transforms/lags/scoring before empirical evaluation;
5. run only a narrow usefulness/regression gate;
6. if promoted, add guarded scheduled refresh + Data Health + production smoke.

Detailed handoff: `docs/FISCAL_HANDOFF_2026-08-25.md`.

### P2 — Credit / Velocity — DEFER

Current status remains `BLOCKED_MISSING_FROZEN_CONSTRUCTION_PROVENANCE`. Build a new version only if Money + Funding + Fiscal leave a material decision gap.

### P2 — Selective asset expansion — DEFER

Do not expand into broad HYG/BTC/REIT/ex-US research during Fiscal work. Reassess only after Fiscal is resolved and only when incremental allocation value is clear.

## Execution order

### Phase 1 — Freshness infrastructure — DONE
- [x] Canonical Data Health block
- [x] China scheduled nowcast ingestion
- [x] Fiscal prospective source archive
- [x] Explicit overlay freshness/refreshability/last-good status

### Phase 2 — Money V2 promotion — DONE
- [x] Official China source/provenance
- [x] Global Money V2 rebuild and regression
- [x] Fixed 6/6 transfer gate
- [x] promotion contract/report
- [x] active Core + guarded refresh
- [x] history API and Pages snapshot

### Phase 3 — Current market confirmation — DONE
- [x] current SPY/QQQ/GLD/DBC layer
- [x] completed-month structural layer remains separate
- [x] divergences surfaced

### Phase 4 — Production resilience / observability — DONE
- [x] canonical Vercel deployment + smoke
- [x] GitHub Pages resilient snapshot
- [x] fail-closed history/core consistency
- [x] Data Health / refresh status

### Phase 5 — Funding V2 — DONE
- [x] freeze minimal candidate inputs/semantics
- [x] reproducible historical series
- [x] fixed stress gate
- [x] narrow DBC usefulness gate
- [x] promotion without retuning
- [x] guarded refresh + provenance + Data Health

### Phase 6 — Fiscal versioning — ACTIVE NEXT
- [ ] inspect latest production Fiscal + prospective manifest
- [ ] resolve legacy reproduction vs explicit Fiscal V2
- [ ] freeze strict release semantics/versioned candidate
- [ ] narrow usefulness/regression gate
- [ ] guarded refresh + Data Health if promoted
- [ ] Vercel + Pages + API smoke

### Phase 7 — Optional gap-filling — DEFER
- [ ] Credit/Velocity only if material gap remains
- [ ] selective asset expansion only if allocation value is clear

## Definition of done

GMLI core infrastructure is materially healthy when:
1. Money Core is reproducible, official-source and guarded. **DONE.**
2. Money nowcast is verified 4/4 with last-good preservation. **DONE.**
3. Funding is reproducible, fresh, versioned and bounded. **DONE.**
4. Current and structural market confirmation remain separate. **DONE.**
5. Vercel and Pages expose a consistent production state with smoke guards. **DONE.**
6. Fiscal is either exactly reproducible under its legacy strict-release contract or explicitly superseded by a better versioned Fiscal V2 with guards. **ACTIVE NEXT.**
7. Historical frozen results and rejected research remain auditable without silently influencing production.
