# GMLI — gmli-fred-dashboard

This branch is the isolated Git home for the GMLI Vercel project.

Production dashboard: `https://gmli-fred-dashboard.vercel.app`

## Safety boundary

This project is completely separate from `Garrincha077/makro-cockpit`.

Do not merge GMLI files into Macro Cockpit. The temporary Macro Cockpit PR used for transport was closed without merge.

## Frozen guardrails

Do not change without an explicit research/promotion decision:

- Money Core country weights
- lags
- horizons
- thresholds
- train/validation split
- FX-neutral methodology
- FDR rules

Funding remains an overlay and does not overwrite Money Core.

## Current migration status

This branch initially contains the project documentation and the live Money freshness repair package. The existing local `gmli-fred-dashboard` source should be imported here as-is before this branch becomes the Vercel Git source of truth.

The production Vercel project must not be reconnected to Git until the imported source is verified against `/api/status`, `/api/decision`, and `/api/report`.
