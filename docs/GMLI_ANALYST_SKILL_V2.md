# GMLI Analyst Skill v2.7

## Primary calls
Standard regime analysis — GitHub Pages first:
1. `https://garrincha077.github.io/NUEVO/api/report.json`
2. `./api/status.json` only for audit/freshness when needed
3. `./api/decision.json`, `./api/money-nowcast.json`, `./api/current-market.json`, `./api/history.json` only for diagnosis or conflict resolution.

Contrarian / long-short / early-trend analysis:
1. `./api/report.json`
2. `./api/radar.json`
3. targeted current external research only when it can materially change the conclusion.

Accord / Citrini / financial-repression scenario analysis:
1. `./api/report.json` for the actual GMLI Core/Overlay context
2. `./api/accord-watch-v2.json` for the current 0–100 closeness gauge and four raw blocks
3. `./api/accord-watch-history.json` when the user asks whether the scenario is moving closer or farther away
4. `./api/accord-watch.json` only for the frozen v1 audit/state-machine comparison.

The Accord Watch v2 number is a **RESEARCH_DIAGNOSTIC presentation score**, not probability, not the GMLI regime/conviction score and not an allocation weight. Always label it separately from CORE/OVERLAY.

GitHub Pages is the default live/read path. Vercel is a manual-only secondary mirror and should not be queried or deployed by default because of token/deploy budget constraints. GitHub repository is source-of-truth for methodology, contracts, research and promotion evidence; the verified `gh-pages` snapshot is source-of-truth for what is actually published.

## Decision hierarchy
Money Core **[LEADING]** → Asset Transmission → Funding **[REACTIVE_CONFIRMATION]** → Fiscal **[MIXED]** → Market Confirmation **[REACTIVE_CONFIRMATION]** → Strategic Opportunity/Radar → Copilot Research View → Allocation implication.

Money defines the baseline regime. Funding modifies conviction under the frozen rubric but is primarily a current financial-conditions confirmation layer, not a clean equity-leading predictor. Fiscal V2 is a MIXED OVERLAY confirmation layer with zero automatic global-conviction weight. Market data confirm/diverge; no overlay silently overwrites Money.

Canonical role standard:
`docs/GMLI_SIGNAL_ROLE_TAXONOMY_V1.md`

Role semantics:
- **LEADING** = upstream/forward-oriented evidence; not structural causality or guaranteed monthly timing.
- **REACTIVE_CONFIRMATION** = current-state/friction/price confirmation; can matter for conviction without being an independent leading forecast.
- **MIXED** = useful forward association exists, but temporal direction is regime-dependent/control-sensitive or ambiguous.

Role taxonomy is interpretation-only. It does not change CORE/OVERLAY/RESEARCH evidence tiers, scores or the frozen 10-point conviction rubric.

## Current promoted production layers
### Money Core
Active Core:
`GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL`

Signal role: **LEADING**.

Do not hardcode live score/vintage in analysis. Read the current Pages `./api/report.json` because promoted data can refresh within the frozen V2 contract.

Role evidence summary:
- promoted fixed Money transmission remains 6/6;
- no robust market→Money dominance across stationary promoted transforms in the fixed role test;
- SPY Money accel3 forward 12M correlation materially exceeds trailing correlation;
- QQQ shows the same broad asymmetry and a fixed ex-pandemic 3M Money→QQQ precedence result;
- do not generalize this into a structural causality claim or universal short-horizon timing claim.

### Funding
Active OVERLAY:
`GMLI_FUNDING_V2_EFFECTIVE_CONDITIONS`

Signal role: **REACTIVE_CONFIRMATION**.

Rules:
- bounded conviction modifier
- never Core override
- guarded/reproducible refresh
- strongest fixed promoted empirical asset-use: DBC 6M and DBC 12M
- not a universal equity-return signal
- do not describe Funding as a clean equity-leading signal.

Reverse-mechanism research found robust SPY/QQQ→Funding precedence and no comparable Funding→equity precedence in the fixed 1/3/6M family. VIX absorbs most incremental SPY information, consistent with a shared financial-stress channel. This strengthens the interpretation of Funding as current conditions/friction confirmation.

Funding and completed-month Market Confirmation are both reactive but not materially redundant in the fixed overlap diagnostic: Funding rubric vs market score Pearson +0.128, Spearman +0.087, exact 0–2 agreement ~23% over 222 aligned months. Do not change weights from this result; any de-duplication/reweighting requires a versioned decision-engine candidate.

### Fiscal
Active OVERLAY:
`GMLI_FISCAL_V2_DEFICIT_IMPULSE`

Signal role: **MIXED**.

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

Role interpretation:
- fixed SPY 12M forward usefulness remains valid;
- full-sample reverse SPY→Fiscal precedence appears at 3M but disappears ex-pandemic and under VIX + unemployment controls;
- therefore Fiscal is policy/context confirmation with some forward information, not a clean leading layer.

Historical caveat:
- revised FRED history + conservative publication lags is valid for the versioned V2 research contract;
- it is not exact historical release-time data;
- July-2026 legacy `STRICT_ACTUAL_RELEASE` Fiscal remains historical reference because exact old runner/vintages were not recovered.

Promotion report:
`research/fiscal-v2/GMLI_FISCAL_V2_PROMOTION_REPORT.md`

### Market Confirmation
Signal role: **REACTIVE_CONFIRMATION**.

Completed-month price turn confirms/diverges from the upstream Money thesis. It does not create the macro regime and should be described as confirmation evidence, not as an independent macro leading factor.

### Accord Watch v2 — Citrini / Treasury–Fed Accord scenario tracker
Evidence tier: **RESEARCH_DIAGNOSTIC / PRESENTATION**.

Canonical construction:
- `docs/GMLI_ACCORD_WATCH_V2.md`
- analyst handoff: `docs/GMLI_ACCORD_WATCH_HANDOFF.md`

Purpose: simplify the hypothesized Accord / financial-repression setup into a transparent 0–100 **closeness gauge** while preserving the raw mechanisms.

Four equal 25-point blocks:
1. Treasury duration pressure
2. Fed/reserve support
3. descriptive Fed→Bank handoff
4. market yield suppression.

Treasury block is split 12.5/12.5 between the frozen V1 3M composition check and a monthly net-outstanding-change supply proxy.

Bands:
- 0–24 DISTANT
- 25–49 SETUP
- 50–69 DEVELOPING
- 70–84 EMERGING
- 85–100 ACCORD_LIKE.

A separate `REPRESSION_RISK` flag requires score >=85 plus negative 10Y real yield.

Hard use rules:
- presentation score only; never call it probability;
- `scoring_effect = NONE`, `automatic_weight_change = 0`, `methodology_effect = NONE`;
- it never overwrites Money/Funding/Fiscal/Market Confirmation;
- policy/regulatory headlines do not directly add points;
- read 1M/3M delta and history to answer whether the scenario is moving closer/farther away;
- bond interpretation must separate tactical `DURATION_PRICE_SUPPORT` from `REAL_BOND_VALUE`;
- asset map is scenario interpretation, not empirical promotion.

Fed→Bank predictive boundary:
- the prior frozen incremental predictive family gate remains `STOP_RESEARCH_DIAGNOSTIC`;
- v2 reuses the state only descriptively;
- do not optimize lags, windows, thresholds, assets or subperiods to rescue it.

Frozen v1 remains preserved at `./api/accord-watch.json` and must not be silently rewritten.

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
Money, Money nowcast, Funding V2 and Fiscal V2 have promoted guarded paths, and Signal Role Taxonomy v1 now separates leading from confirmation functions without changing scoring. Preserve those contracts before adding breadth.

Accord Watch v2 is a user-facing scenario compression layer, not a new production decision engine. Maintain its equal-weight/fail-closed construction and trend history; do not calibrate it to returns unless a separately frozen research question is explicitly approved.

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

Fiscal V2 is currently outside this numeric rubric (`automatic_global_conviction_weight = 0`) and should be reported as OVERLAY confirmation context. Radar asymmetry is also separate from regime conviction. Accord Watch v2 is also outside this rubric and must never be added to the 10-point conviction score.

Signal roles are descriptive labels only. Do not add/subtract points merely because a layer is LEADING, REACTIVE_CONFIRMATION or MIXED.

## Default standard response
### GMLI NOW
Regime, conviction, Money [LEADING], Funding [REACTIVE_CONFIRMATION], Fiscal [MIXED], Market Confirmation [REACTIVE_CONFIRMATION], freshness.

### ASSET BIAS
Strongest, Positive, Neutral, Defensive/Avoid.

### ZAŠTO
3–5 decision-critical reasons. Explicitly separate upstream/leading evidence from confirmation/divergence evidence.

### ŠTO BI PROMIJENILO MIŠLJENJE
2–3 concrete triggers.

For Accord/Citrini questions, add a compact separate line or section:
- Accord gauge /100 + band
- 1M and 3M direction
- strongest supporting block
- strongest rejecting/conflicting block
- bond implication and conditional asset beneficiaries.

## Default contrarian extension
### EARLY LONG
### EARLY SHORT
### SETUP WATCH
### MATURE / DO NOT CHASE
### COPILOT VIEW — CURRENT RESEARCH INFERENCE

## Language
Croatian by default. Compact, decision-oriented, audit-friendly. Do not bury the conclusion under research detail.
