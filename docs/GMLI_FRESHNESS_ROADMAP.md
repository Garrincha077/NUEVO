# GMLI Freshness & Data Integrity Roadmap

Status: ACTIVE
Owner: GMLI project
Started: 2026-08-24
Last updated: 2026-08-26

## Goal
Keep the decision-critical GMLI stack fresh, reproducible and auditable while preserving strict CORE / OVERLAY / RESEARCH separation.

Pareto rule: finish the few layers that can materially change the 3–12M allocation/risk decision before adding more indicators or asset-specific research.

## Current production architecture

### Money Core — DONE / ACTIVE
`GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL`

Current promoted GitHub Pages vintage at this roadmap update:
- observation month: 2026-06
- available date: 2026-07-31
- USD Money score: 54.9994 — NEUTRAL
- FX-neutral Money score: 44.2502 — NEUTRAL
- fixed transmission transfer gate: 6/6 PASS

Signal role taxonomy: **LEADING**. This is an interpretation label, not a new score or causal claim.

The 2026-02-28 Core remains HISTORICAL REFERENCE only. Historical v1.8b remains `BLOCKED_MISSING_FROZEN_INPUT_BYTES` as audit context only.

### Money nowcast — DONE / ACTIVE
US, euro area, Japan and China are covered 4/4 through scheduled validated official-source refresh with last-good preservation.

Latest verified Pages snapshot:
- US: 2026-07
- euro area: 2026-06
- Japan: 2026-07
- China: 2026-07
- coverage: 4/4
- directional tilt: SUPPORTIVE_MIXED.

### Funding V2 — DONE / ACTIVE OVERLAY
`GMLI_FUNDING_V2_EFFECTIVE_CONDITIONS`

Current promoted vintage:
- observation month: 2026-06
- available date: 2026-07-31
- score: 37.9684402601
- regime: RESTRICTIVE
- structural support score: 37.9684402601
- observed conditions score: 59.0994961494

Funding V2 is reproducible, guarded and scheduled. It is a bounded OVERLAY and never overrides Money Core.

Signal role taxonomy: **REACTIVE_CONFIRMATION**.

Promotion evidence:
- Candidate 1 rejected without retuning after 2020 stress failure.
- Candidate 2 fixed stress gate passed 2008-10, 2020-03 and current state.
- Narrow fixed usefulness gate passed 2/2 for DBC 6M/12M.
- No universal equity-return claim.

### Fiscal V2 — DONE / ACTIVE OVERLAY
`GMLI_FISCAL_V2_DEFICIT_IMPULSE`

Signal role taxonomy: **MIXED**.

Legacy reproduction decision:
- exact July-2026 `STRICT_ACTUAL_RELEASE` historical runner/vintages were not recovered without guesswork;
- revised present-day FRED history is not substituted and called an exact legacy rerun;
- legacy score 52.539556447652046 / NEUTRAL is preserved as HISTORICAL REFERENCE.

Frozen Candidate 1:
- TTM federal deficit / nominal GDP
- 12M change in deficit/GDP (fiscal impulse)
- rolling 120M z-score, minimum 24M, ddof=0, component clip ±3
- equal 50/50 weighting
- `<40 RESTRICTIVE`, `40–60 NEUTRAL`, `>60 SUPPORTIVE`
- debt, interest, receipts and expenditures remain diagnostics only.

Fixed construction sanity:
- 2020-06 expected SUPPORTIVE → actual SUPPORTIVE / score 100 — PASS.

Current promoted reading in the verified Pages snapshot:
- observation month: 2026-06
- available date: 2026-07-31
- TTM deficit: $1.805T
- deficit/GDP: 5.5566%
- 12M fiscal impulse: -0.6669 pp
- composite z: -0.24550
- score: 45.9084
- regime: NEUTRAL.

Pre-frozen narrow usefulness gate:
- primary only: SPY 12M
- train n=62 Pearson +0.306755
- OOS n=30 Pearson +0.446855
- OOS Spearman +0.486096
- PASS 1/1.

QQQ/DBC 12M were diagnostics only. DBC OOS effect was weak and is not a promotion claim. No asset/horizon/lag/parameter/threshold/subperiod search and no FDR claim.

Promotion boundary:
- evidence tier: OVERLAY
- guarded refresh with raw SHA-256 archive and date-regression protection
- `automatic_global_conviction_weight = 0`
- existing 10-point global conviction rubric unchanged
- Money Core unchanged
- Funding V2 unchanged.

Production closeout:
- promotion lock: `PASS_FISCAL_V2_PRODUCTION_PROMOTION`
- guarded refresh: `PASS_ACTIVE_FISCAL_V2_REFRESH_GUARDS`
- GitHub Pages fetch-first status: `PASS_FETCH_FIRST`
- static snapshot build: `PASS_GITHUB_PAGES_SNAPSHOT`
- Pages workflow run `32937776235`: build SUCCESS + deploy SUCCESS
- verified static API set: report, status, decision, money-nowcast, current-market, history, radar, opportunity, positioning, context-history, refresh-status and money-extremes
- `gh-pages/api/report.json` exposes Fiscal V2 as active promoted OVERLAY
- Fiscal automatic global conviction weight remains 0.

Vercel is no longer required for this definition of live. It is retained only as a manual secondary mirror to conserve deploy/token budget.

### Market confirmation — DONE / ACTIVE
Completed-month structural confirmation remains separate from current/live SPY/QQQ/GLD/DBC confirmation and divergence flags.

Signal role taxonomy: **REACTIVE_CONFIRMATION** by construction.

### Signal Role Taxonomy v1 — DONE / INTERPRETATION-ONLY
Canonical standard:
- `docs/GMLI_SIGNAL_ROLE_TAXONOMY_V1.md`
- `research/signal-role-taxonomy/RESULT_SUMMARY.json`

Fixed findings:
- Money Core: **LEADING**
- Funding V2: **REACTIVE_CONFIRMATION**
- Fiscal V2: **MIXED**
- Market Confirmation: **REACTIVE_CONFIRMATION**

Money role test:
- promoted Money V2 transmission remains 6/6;
- no robust market→Money dominance across stationary promoted transforms;
- SPY Money accel3 12M forward Pearson +0.452 vs trailing +0.015;
- QQQ +0.414 vs +0.216;
- QQQ fixed ex-pandemic 3M Money→QQQ p=0.0475; reverse p=0.696;
- DBC Money-level Granger excluded from role count because ADF p=0.0985.

Reverse overlay finding:
- Funding: SPY/QQQ→Funding 6/6 Holm-significant fixed 1/3/6M tests; Funding→equities 0/6; same 6/6 vs 0/6 ex-pandemic; VIX absorbs most incremental SPY information.
- Fiscal: fixed SPY 12M usefulness remains, but reverse precedence is regime/control sensitive and not robust ex-pandemic.

Funding vs Market Confirmation overlap:
- aligned n=222 months;
- Funding rubric vs market score Pearson +0.128, Spearman +0.087;
- exact 0–2 score agreement ~23%.

Conclusion: Funding and Market Confirmation are both reactive but are not materially the same signal. No frozen conviction-weight change is justified by this diagnostic.

Scoring effect of taxonomy: **NONE**. Any role-based reweighting/de-duplication requires a separately frozen versioned decision-engine candidate.

### Decision Delta + Decision Brief — DONE / ACTIVE PRESENTATION LAYER
GitHub Pages now exposes a compact usability layer derived only from already verified production components:
- `gh-pages/api/decision-delta.json`
- embedded `decision_delta` and `decision_brief` in `gh-pages/api/report.json` and `decision.json`
- dashboard `DECISION` / `WHAT CHANGED` section.

Decision Delta v1 compares each layer with its immediately previous verified component row:
- Money USD and FX-neutral score/regime change
- Funding V2 score/regime change
- Fiscal V2 score/regime change
- completed-month Market Confirmation change
- current conviction versus an explicitly labeled `RECONSTRUCTED_FIXED_RUBRIC_PROXY` for the prior component rows.

Guardrails:
- evidence tier: `RESEARCH_DIAGNOSTIC`
- `scoring_effect = NONE`
- `automatic_weight_change = 0`
- `methodology_effect = NONE`
- no synthetic Money Core score
- no new signal, threshold, weight or asset promotion
- prior conviction proxy is not represented as an archived historical live decision
- Fiscal automatic global conviction weight remains 0.

Production closeout:
- first integration attempt failed closed before deploy on a UI nav marker mismatch; existing live Pages remained unchanged
- subsequent integration passed build/publish but live audit found a JS initialization-order issue
- runtime-order-safe fix added and guarded in the postprocessor
- GitHub Pages workflow run `32940549838` (#101): build SUCCESS + deploy SUCCESS
- live `gh-pages` verifies independent Decision Brief initialization and no pre-definition `renderDecisionBrief()` call.

This layer is intended to answer “što se promijenilo?” and compress the existing engine into a practical brief. It is not Phase 7 and does not justify engine expansion by itself.

### Production resilience / observability — DONE
- GitHub Pages is the primary production/read path
- Pages production workflow performs fetch-first guarded Money/Nowcast/Funding/Fiscal refresh with per-layer last-good fallback
- verified Pages static APIs include `report.json`, `status.json`, `decision.json`, `money-nowcast.json`, `current-market.json`, `history.json`, `decision-delta.json` and `refresh-status.json`
- `/api/history.json` is consistent with active Money V2 and current through 2026-06 / available 2026-07-31
- Data Health exposes active versions/freshness/guardrails
- Vercel workflow is manual-only secondary mirror and no longer runs on every `main` push.

## Guardrails
- Never reconstruct missing frozen bytes from current revised public data and call it an exact rerun.
- Frozen methodology must not be silently retuned.
- Better methods advance only as explicit versioned candidates with regression/promotion gates.
- RESEARCH and OVERLAY signals never silently replace CORE.
- Funding remains a bounded modifier and cannot overwrite Money Core.
- Fiscal V2 remains an OVERLAY; automatic global conviction weight stays 0 unless a separately frozen decision-engine candidate is tested and promoted.
- Signal Role Taxonomy is descriptive only and cannot silently change weights or evidence tiers.
- Decision Delta / Decision Brief is a presentation/diagnostic layer only and cannot change scoring, weights, evidence tiers or methodology.
- Overlay refreshes fail closed and preserve last-good state on source/provenance/date-regression failures.
- Do not broaden empirical search merely because an interesting secondary correlation appears.
- GitHub Pages production status must be verified from the built/deployed snapshot; a `main` commit alone is not evidence that a change is live.

## Research note — Funding equity contrarian effect
Status: **CLOSED / RESEARCH-ONLY / NOT PROMOTED**

A fixed long test of inverted Funding V2 (`100 - effective score`) for SPY/QQQ 12M found a materially positive contrarian relationship in the 2020+ regime, but not over the broader 2006–2025 history.

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
- DBC FX-neutral 6M.

### P0 — Money nowcast 4/4 — DONE
Scheduled validated official-source refresh with last-good preservation.

### P1 — Funding V2 — DONE
Completed promotion, active integration, guarded refresh, provenance archive and Data Health exposure.

### P1 — Fiscal V2 — DONE
Completed:
- [x] inspect production Fiscal + prospective manifest
- [x] stop unrecoverable legacy reverse-engineering without guessing
- [x] freeze explicit Fiscal V2 Candidate 1
- [x] fixed construction sanity
- [x] predeclared narrow SPY 12M usefulness gate
- [x] promotion lock/report
- [x] guarded refresh + raw source archive + last-good policy
- [x] active state / Data Health / API integration
- [x] merge + GitHub Pages fetch-first refresh/build/deploy smoke
- [x] verify `gh-pages` report/status/decision/nowcast/history/refresh-status snapshot.

Detailed evidence:
- `research/fiscal-v2/GMLI_FISCAL_V2_PROMOTION_REPORT.md`
- `research/fiscal-v2/promotion.lock.json`
- `research/fiscal-v2/latest/manifest.lock.json`
- GitHub Pages workflow run `32937776235`.

### P1 — Signal Role Taxonomy v1 — DONE
Completed:
- [x] fixed Money direction test using only promoted transforms
- [x] stationarity guard before Granger role counting
- [x] reverse Funding/Fiscal mechanism research
- [x] Funding vs Market Confirmation overlap diagnostic
- [x] canonical role standard + API read-only metadata
- [x] zero scoring/weight change guard.

### P1 — Decision Delta / Decision Brief — DONE
Completed:
- [x] current-vs-previous verified component deltas
- [x] compact decision brief for regime / tilt / conviction / opportunity focus / main risk
- [x] explicitly labeled prior conviction reconstruction rather than invented historical live state
- [x] zero scoring/weight/methodology-effect guards
- [x] fail-closed Pages integration
- [x] runtime initialization-order fix and live audit
- [x] GitHub Pages run `32940549838` build + deploy SUCCESS.

### P2 — Credit / Velocity — DEFER
Current status remains `BLOCKED_MISSING_FROZEN_CONSTRUCTION_PROVENANCE`. Do not infer the old formula. Build a new version only if the promoted Money + Funding + Fiscal stack still leaves a material decision gap, with construction/usefulness gates frozen before testing.

### P2 — Selective asset expansion — DEFER
Do not expand broadly until incremental allocation value is clear. HYG/BTC/REIT/ex-US work remains secondary to maintaining promoted refresh contracts.

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
- [x] GitHub Pages primary production snapshot
- [x] fetch-first guarded refresh with per-layer last-good fallback
- [x] fail-closed history/core consistency
- [x] Data Health / refresh status
- [x] Vercel moved to manual-only secondary mirror.

### Phase 5 — Funding V2 — DONE
- [x] freeze minimal candidate inputs/semantics
- [x] reproducible historical series
- [x] fixed stress gate
- [x] narrow DBC usefulness gate
- [x] promotion without retuning
- [x] guarded refresh + provenance + Data Health

### Phase 6 — Fiscal V2 — DONE
- [x] legacy reproduction decision
- [x] frozen candidate construction
- [x] narrow usefulness gate
- [x] promotion without retuning
- [x] guarded refresh + provenance + Data Health/API integration
- [x] GitHub Pages fetch-first refresh + build + deploy + static API smoke
- [x] `gh-pages` snapshot verified after deployment.

### Phase 6b — Signal Role Taxonomy — DONE
- [x] Money = LEADING interpretation supported without reverse dominance
- [x] Funding = REACTIVE_CONFIRMATION
- [x] Fiscal = MIXED
- [x] Market Confirmation = REACTIVE_CONFIRMATION
- [x] overlap check does not justify frozen rubric changes
- [x] canonical docs and report metadata updated

### Phase 6c — Decision usability layer — DONE
- [x] Decision Delta v1 derived from verified component histories
- [x] Decision Brief v1 exposed in report/decision and dashboard UI
- [x] prior conviction comparison explicitly labeled reconstructed proxy
- [x] `scoring_effect = NONE`, `automatic_weight_change = 0`, `methodology_effect = NONE`
- [x] GitHub Pages fail-closed integration
- [x] live runtime-order audit
- [x] run `32940549838` build + deploy SUCCESS.

### Phase 7 — Optional gap-filling — DEFER
- [ ] Credit/Velocity only if a material decision gap remains
- [ ] selective asset expansion only if allocation value is clear
- [ ] any automatic Fiscal conviction weighting only through a separate frozen decision-engine candidate
- [ ] any role-based Funding/market de-duplication only through a separate frozen decision-engine candidate.

## Definition of done
GMLI core infrastructure is materially healthy when:
1. Money Core is reproducible, official-source and guarded. **DONE.**
2. Money nowcast is verified 4/4 with last-good preservation. **DONE.**
3. Funding is reproducible, fresh, versioned and bounded. **DONE.**
4. Current and structural market confirmation remain separate. **DONE.**
5. GitHub Pages exposes a consistent, guarded production snapshot with fetch-first refresh and static API smoke. **DONE.**
6. Fiscal legacy ambiguity is explicitly superseded by versioned Fiscal V2 with frozen construction, narrow PASS, fail-closed refresh and verified Pages deployment. **DONE.**
7. Signal roles are explicitly separated without silently changing scoring. **DONE.**
8. Historical frozen results and rejected research remain auditable without silently influencing production. **DONE.**
9. Decision Delta / Brief explains verified change without creating a new score or silently changing frozen logic. **DONE.**

Vercel is not part of the mandatory definition-of-done path; it is a manual secondary mirror only.
