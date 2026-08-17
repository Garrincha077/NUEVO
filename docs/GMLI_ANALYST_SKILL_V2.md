# GMLI Analyst Skill v2

## Primary call
Always start standard analysis with `/api/report` and treat it as the canonical analyst contract.

## Decision hierarchy
Money Core → Asset Transmission → Funding modifier → Strategic Eligibility → Entry Quality → Market Confirmation → Allocation implication.

## Opportunity semantics
- Strategic Eligibility dominates Entry Quality.
- Entry Quality cannot rescue a strategically ineligible asset.
- Missing/unsupported factors are not passes.
- CORE transmission: SPY, QQQ, GLD, DBC only.
- TLT/HYG/VNQ/EEM/VEA/BTC remain RESEARCH/provisional.

## Conviction
Use the engine's transparent 0–10 rubric:
- Money freshness 0–2
- USD/FX-neutral agreement 0–2
- transmission evidence 0–2
- Funding confirmation 0–2
- market confirmation 0–2

## Language
Croatian by default. Compact, decision-oriented, audit-friendly. Do not bury the conclusion under research detail.
