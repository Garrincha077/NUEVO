# GMLI Prospective Fiscal Source Archive

Status: RESEARCH / OVERLAY SUPPORT ONLY

Purpose: preserve future Fiscal source vintages prospectively so raw bytes, retrieval timing and source hashes are not lost.

## Captured series

- `MTSDS133FMS` — monthly federal surplus/deficit
- `GDP` — nominal GDP
- `GFDEBTN` — total federal debt
- `A091RC1Q027SBEA` — federal interest payments
- `FGRECPT` — federal government current receipts
- `FGEXPND` — federal government current expenditures

## Guardrails

- The archive does **not** compute or update the production Fiscal score.
- Current revised FRED history is provenance context only; it is **not** an exact substitute for missing historical strict-actual-release vintages.
- The production July 2026 Fiscal baseline remains `z = 0.1523733868591229`, score `52.539556447652046`, mode `STRICT_ACTUAL_RELEASE` until a valid refresh contract is proven.
- Every future raw source is preserved with SHA-256, retrieval timestamp and latest observation metadata.
- Date regression fails closed.
- A future Fiscal score may advance only after the strict-release transformation is implemented and the July 2026 production baseline is reproduced exactly under CI.

## Files

`latest/` contains the most recently captured raw FRED CSV bytes and `manifest.json`. Git history preserves prior committed byte versions when sources change. CI artifacts retain each capture audit separately.

This archive is an input-provenance layer, not a new model and not a Core promotion path.
