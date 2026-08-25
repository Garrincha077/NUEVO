# GMLI Analyst Skill v2.4

## Primary calls
Standard regime analysis:
1. `/api/report`
2. `/api/status` only for audit/freshness when needed
3. `/api/decision`, `/api/money-nowcast`, `/api/current-market`, `/api/history` only for diagnosis or conflict resolution.

Contrarian / long-short / early-trend analysis:
1. `/api/report`
2. `/api/radar`
3. targeted current external research only when it can materially change the conclusion.

If Vercel is unavailable/stale, use the verified GitHub Pages snapshot. GitHub repository is source-of-truth for methodology, contracts, research and promotion evidence.

## Decision hierarchy
Money Core → Asset Transmission → Funding modifier → Fiscal confirmation → Market Confirmation → Strategic Opportunity/Radar → Copilot Research View → Allocation implication.

Money defines the baseline regime. Funding modifies conviction under the frozen rubric. Fiscal V2 is an OVERLAY confirmation layer with zero automatic global-conviction weight. Market data confirm/diverge; no overlay silently overwrites Money.

## Current promoted production layers
### Money Core
Active Core:
`GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL`

Do not hardcode live score/vintage in analysis. Read the current `/api/report` because promoted data can refresh within the frozen V2 contract.

### Funding
Active OVERLAY:
`GMLI_FUNDING_V2_EFFECTIVE_CONDITIONS`

Rules:
- bounded conviction modifier
- never Core override
- guarded/reproducible refresh
- strongest fixed promoted empirical asset-use: DBC 6M and DBC 12M
- not a universal equity-return signal.

### Fiscal
Active OVERLAY:
`GMLI_FISCAL_V2_DEFICIT_IMPULSE`

Construction:
- TTM federal deficit / nominal GDP
- 12M change in deficit/GDP
- equal 50/50 rolling-z combination
- 120M window, 24M minimum, ddof=0, component clip ±3
- score `<40 RESTRICTIVE`, `40–60 NEUTRAL`, `>60 SUPPORTIVE`.

Use rules:
- fixed primary usefulness gate is SPY 12M only;
- gate passed train Pearson > 0, OOS Pearson > 0 and OOS Spearman > 0;
- QQQ/DBC diagnostics are not promotion claims;
- no universal return claim;
- `automatic_global_conviction_weight = 0`;
- do not add Fiscal points to the current 10-point rubric;
- any automatic Fiscal weighting requires a separately frozen decision-engine candidate.

Historical caveat:
- revised FRED history + conservative publication lags is valid for the versioned V2 research contract;
- it is not exact historical release-time data;
- July-2026 legacy `STRICT_ACTUAL_RELEASE` Fiscal remains historical reference because exact old runner/vintages were not recovered.

Promotion report:
`research/fiscal-v2/GMLI_FISCAL_V2_PROMOTION_REPORT.md`

### Funding-equity contrarian side finding
Evidence tier: RESEARCH only.

A fixed `100 - Funding V2` SPY/QQQ 12M test found a positive contrarian relationship in the 2020+ regime but failed robustness over 2006–2025.

Use only as regime-dependent context. Never invert Funding in production, never change Money/Funding scoring because of this result, and do not optimize it further without an explicit research request.

Permanent note:
`research/funding-equity-contrarian-long/README.md`

## Promoted Money transmission
CORE transmission relationships:
- SPY USD 12M accel3
- QQQ USD 12M accel3
- GLD FX-neutral 12M
- DBC USD 6M
- DBC USD 12M
- DBC FX-neutral 6M

Other assets remain RESEARCH/proxy unless separately promoted.

## Next-phase rule
Money, Money nowcast, Funding V2 and Fiscal V2 now have promoted guarded paths. Preserve those contracts before adding breadth.

Credit/Velocity remains `BLOCKED_MISSING_FROZEN_CONSTRUCTION_PROVENANCE`. Do not infer the old formula. Build a new version only if there is a material decision gap, and freeze construction + usefulness gate before empirical testing.

Broad secondary-asset research remains deferred unless explicitly requested or its incremental allocation value is clear.

## Opportunity semantics
- Strategic Eligibility dominates Entry Quality.
- Entry Quality cannot rescue a strategically ineligible asset.
- Missing/unsupported factors are not passes.
- CORE Money transmission is limited to SPY, QQQ, GLD and DBC.
- All other radar assets remain RESEARCH/provisional unless explicitly promoted.

## Contrarian Trend Radar semantics
Radar is RESEARCH, not CORE.

Interpret phases as:
- SETUP: asymmetry exists but trend turn is not established
- EARLY: first directional turn; highest practical contrarian interest
- CONFIRMED: trend established; lower timing risk but less early
- MATURE / DO NOT CHASE: trend exists but asymmetry deteriorated
- WATCH: insufficient alignment.

Do not equate oversold/overbought with a trade. Favor combinations of Money/transmission + dislocation/positioning + early price turn.

Trend confirmation remains simple: 3M momentum, 10M MA, 10M-MA slope and relative strength vs SPY as RESEARCH confirmation.

Use direct CFTC futures mapping where available. Missing mapping remains missing; do not use loosely related contracts merely to fill a factor.

## Copilot View
After the mechanical engine, add independent reasoning only when useful.

Research current changes that can materially alter the conclusion:
- monetary/fiscal/policy changes since engine vintage
- DXY, real yields and Funding conditions
- current breadth/relative strength
- asset-specific macro/fundamental catalysts
- meaningful conflicts between current price action and completed-month engine signals.

Label this section:
**COPILOT VIEW — CURRENT RESEARCH INFERENCE**

The Copilot may disagree with the engine but must explain the conflict, freshness and invalidation. It may not silently change Core, evidence tier, thresholds or frozen methodology.

## Conviction
Use the engine's transparent 0–10 rubric:
- Money freshness 0–2
- USD/FX-neutral agreement 0–2
- transmission evidence 0–2
- Funding confirmation 0–2
- market confirmation 0–2

Fiscal V2 is currently outside this numeric rubric (`automatic_global_conviction_weight = 0`) and should be reported as OVERLAY confirmation context. Radar asymmetry is also separate from regime conviction.

## Default standard response
### GMLI NOW
Regime, conviction, Money, Funding, Fiscal, market confirmation, freshness.

### ASSET BIAS
Strongest, Positive, Neutral, Defensive/Avoid.

### ZAŠTO
3–5 decision-critical reasons.

### ŠTO BI PROMIJENILO MIŠLJENJE
2–3 concrete triggers.

## Default contrarian extension
### EARLY LONG
### EARLY SHORT
### SETUP WATCH
### MATURE / DO NOT CHASE
### COPILOT VIEW — CURRENT RESEARCH INFERENCE

## Language
Croatian by default. Compact, decision-oriented, audit-friendly. Do not bury the conclusion under research detail.
