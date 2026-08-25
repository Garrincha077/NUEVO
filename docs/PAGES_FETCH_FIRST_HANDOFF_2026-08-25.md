# GMLI Pages fetch-first handoff — 2026-08-25

Status: IMPLEMENTED ON BRANCH / CI + LIVE VERIFY PENDING
Branch: `gmli-pages-fetch-first`

## Goal
Make GitHub Pages obtain fresh decision-critical inputs before building the static fallback, rather than merely redrawing the last checked-in snapshot.

## Design
Production Pages runs use `scripts/refresh-pages-inputs.py` before `scripts/build-pages-snapshot.mjs`.

Refresh order:
1. official PBoC M2 V2 + promoted Global Money V2 + frozen 6/6 transmission gate + active Money sync;
2. Money nowcast;
3. Funding V2 guarded refresh;
4. Fiscal prospective capture + Fiscal V2 guarded refresh;
5. current SPY/QQQ/GLD/DBC market confirmation remains live inside `api/report.js` during the snapshot build.

Each upstream layer is isolated by path. If a layer refresh command fails, only that layer is restored to checked-in `HEAD` and marked `LAST_GOOD_FALLBACK`; other successful layers remain fresh for the ephemeral Pages build. The workflow never weakens promotion or consistency guards.

Pages publishes `api/refresh-status.json` with per-layer refresh outcome. The Pages job does not commit refreshed engine inputs back to `main`; the existing dedicated guarded refresh workflows remain responsible for canonical source archive commits.

## Important guard change
The Pages builder no longer hardcodes active Money date `2026-07-31`. Instead it requires a valid ISO date not older than the promoted baseline and enforces exact report/history consistency, so the first legitimate future vintage can advance without a code edit.

## No methodology change
- Money Core formula/weights unchanged.
- Funding V2 unchanged.
- Fiscal V2 unchanged; automatic conviction weight remains 0.
- Signal Role Taxonomy remains scoring effect NONE.
- 10-point conviction rubric unchanged.
