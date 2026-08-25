# GMLI Fiscal Phase Handoff — 2026-08-25

Status: **READY FOR NEXT CHAT**

## Where GMLI stands

### Money Core — DONE / ACTIVE

Active Core: `GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL`

Current promoted vintage at handoff:
- observation month: 2026-06
- available date: 2026-07-31
- USD-translated broad-money YoY: 7.956975%
- FX-neutral broad-money YoY: 5.946277%
- FX contribution: +2.010698 pp
- USD Money score: 55.1121 — NEUTRAL
- FX-neutral Money score: 44.4880 — NEUTRAL
- fixed transmission transfer gate: 6/6 PASS

Do not modify Money methodology during Fiscal work.

### Funding V2 — DONE / ACTIVE OVERLAY

Active Funding: `GMLI_FUNDING_V2_EFFECTIVE_CONDITIONS`

Current promoted vintage at handoff:
- observation month: 2026-06
- available date: 2026-07-31
- score: 37.9684402601
- regime: RESTRICTIVE
- structural support score: 37.9684402601
- observed conditions score: 59.0994961494

Funding V2 is guarded, reproducible and scheduled. It remains a bounded OVERLAY and never overrides Money Core.

Promoted empirical asset-transmission scope remains strongest for DBC/commodities 6M/12M.

### Funding-equity contrarian side research — CLOSED / NOT PROMOTED

A long 2006–2025 fixed test of `100 - Funding V2` for SPY/QQQ 12M failed the full robustness gate.

Important nuance retained for future interpretation:
- 2006–2012: inverted Funding relation was materially negative
- 2013–2019: approximately flat
- 2020+: materially positive / contrarian (SPY +0.413 Pearson, QQQ +0.549)

Conclusion: contrarian Funding can make sense in a **specific recent regime**, but not as a broad historical law. No further research is planned now. See `research/funding-equity-contrarian-long/README.md` and PR #25.

## Fiscal — NEXT ACTIVE PHASE

### Current production Fiscal reference

Existing Fiscal remains an OVERLAY using the preserved production baseline:
- mode: `STRICT_ACTUAL_RELEASE`
- z: `0.1523733868591229`
- score: `52.539556447652046`
- production baseline date/context: July 2026

The baseline must not be silently recalculated from revised present-day history.

### Existing prospective source capture

The repository already archives raw FRED source bytes prospectively with SHA-256, retrieval timestamps and latest-observation metadata.

Captured series:
- `MTSDS133FMS` — monthly federal surplus/deficit
- `GDP` — nominal GDP
- `GFDEBTN` — total federal debt
- `A091RC1Q027SBEA` — federal interest payments
- `FGRECPT` — federal government current receipts
- `FGEXPND` — federal government current expenditures

Relevant files:
- `scripts/capture-prospective-fiscal-inputs.py`
- `.github/workflows/gmli-fiscal-prospective-capture.yml`
- `research/fiscal-prospective/README.md`
- `research/fiscal-prospective/latest/manifest.json`

Important limitation: this capture layer **does not compute or update the production Fiscal score** and current revised FRED history is not an exact substitute for missing historical strict-release vintages.

## Pareto execution plan for next chat

1. **Inspect current Fiscal production state and latest prospective manifest.**
   - Confirm current score/date/mode in `lib/state.js`, overlay refresh status and `/api/report`.
   - Confirm source archive freshness and hashes.

2. **Attempt a narrow legacy reproduction only if the required strict actual-release semantics are recoverable.**
   - Do not spend a large research cycle reverse-engineering missing vintages.
   - Success means reproducing the July-2026 baseline exactly enough under a frozen runner/contract.

3. **If exact legacy reproduction is not realistically recoverable, stop and build an explicit versioned Fiscal V2 candidate.**
   - Preserve the existing Fiscal baseline as historical reference.
   - Freeze source definitions, transformations, publication lags and scoring before empirical evaluation.
   - Prefer simple/reproducible construction over legacy compatibility for its own sake.

4. **Run only a narrow usefulness/regression gate.**
   - No broad horizon/parameter search.
   - Fiscal remains an OVERLAY/conviction modifier, not Money Core.
   - Test only whether it materially improves regime interpretation or allocation conviction.

5. **If promoted, add guarded refresh and Data Health.**
   - raw bytes + hashes + transformed history + promotion lock
   - fail closed on source/date/contract mismatch
   - scheduled refresh only after promotion

6. **Production completion gate.**
   - CI/frozen/promotion guards PASS
   - integrate without changing Money/Funding methodology
   - deploy existing Vercel project
   - update verified GitHub Pages snapshot
   - smoke at minimum `/api/report`, `/api/status`, `/api/money-nowcast`, `/api/decision`, `/api/history`

## Explicit non-goals for Fiscal phase

- no more Funding-equity contrarian optimization
- no Credit/Velocity rebuild unless Fiscal reveals a material remaining decision gap
- no broad secondary asset expansion
- no retuning Money/Funding to make Fiscal fit
- no treating revised historical FRED data as if it were exact historical release-time data

## Starting prompt for next chat

`Nastavi GMLI prema docs/FISCAL_HANDOFF_2026-08-25.md. Fiscal je sljedeća aktivna faza. Prvo provjeri aktualni Git/production state i prospective Fiscal manifest, zatim po Pareto principu odluči može li se postojeći STRICT_ACTUAL_RELEASE Fiscal reproducirati bez nagađanja. Ako ne može, odmah idi na zasebni versioned Fiscal V2 candidate. Ne diraj Money Core ni Funding V2.`
