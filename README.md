# GMLI 2.3 — Global Money & Liquidity Intelligence

Canonical production: `gmli-fred-dashboard.vercel.app`

This repository is isolated from Macro Cockpit. The frozen Money Core remains unchanged. Live Money data are a RESEARCH freshness overlay only.

## Architecture
- `lib/state.js` — frozen Core/overlay state; do not retune silently.
- `lib/nowcast-state.js` — last-verified fallback snapshot.
- `lib/live-money-nowcast.js` — live official-source freshness overlay with per-block fallback.
- `api/status.js` — ENGINE FACT frozen state.
- `api/money-nowcast.js` — live RESEARCH freshness.
- `api/decision.js` — current decision inference and conviction rubric.
- `api/opportunity.js` — Strategic Eligibility before Entry Quality.
- `api/report.js` — canonical analyst/ChatGPT contract.

## Guardrail
RESEARCH/OVERLAY never overwrite CORE. No changes to frozen weights, lags, horizons, thresholds, FX-neutral methodology or FDR rules in the live-freshness repair.
