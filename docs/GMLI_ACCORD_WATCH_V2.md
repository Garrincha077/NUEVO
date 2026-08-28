# GMLI Accord Watch v2 — frozen construction

Status: **FROZEN BEFORE FIRST V2 RESULT**  
Evidence tier: **RESEARCH_DIAGNOSTIC / PRESENTATION**  
GMLI scoring effect: **NONE**  
Automatic weight change: **0**  
Methodology effect: **NONE**

## Purpose

Accord Watch v2 compresses the Citrini/Treasury–Fed Accord 2.0 hypothesis into one simple **0–100 closeness gauge** while preserving the raw mechanisms underneath.

- `0` = measured conditions are far from the hypothesized Accord / financial-repression setup.
- `100` = all four measurable mechanisms are aligned with the hypothesis.

The gauge is **not** the GMLI regime score, not a probability forecast, not a portfolio weight and not an empirical return model. Money Core remains the baseline GMLI liquidity regime.

V1 remains frozen and auditable. V2 is a separately versioned presentation/research diagnostic because V1 explicitly produced no numeric score.

## Pareto design — four equal blocks

The v2 gauge uses four blocks worth **25 points each**. Equal weights are chosen for transparency, not because they were optimized against asset returns.

### A. Treasury duration pressure — 0 / 12.5 / 25

Two fixed subchecks, 12.5 points each.

#### A1. Composition
Same frozen V1 stock-composition rule:
- short/floating = Bills + FRNs
- fixed duration = Notes + Bonds + TIPS
- compare latest MSPD month with approximately 3 months earlier
- fixed-duration share change `< 0` → supportive = **12.5 points**
- otherwise → **0 points**

#### A2. Net-supply flow proxy
Use the same official MSPD Table 1 debt-held-by-public class levels and compare the latest month with the immediately preceding available month.

- short/floating net change = Δ(Bills + FRNs)
- fixed-duration net change = Δ(Notes + Bonds + TIPS)
- if short/floating net change `>=` fixed-duration net change → duration-light net supply = **12.5 points**
- otherwise → **0 points**

This is a monthly **net-outstanding-change supply proxy**. It is closer to net issuance/redemption pressure than the V1 stock share, but it is not auction-level DV01, WAM or a separate buyback accounting model; TIPS indexation can affect the fixed-duration level.

Missing Treasury source data scores **0** for the missing subcheck; source failure cannot create support.

### B. Fed / reserve support — 0 to 25

Reuse the frozen V1 H.4.1 13-week classifications:

- `SUPPORTIVE` → **25**
- `RESERVE_CUSHION` → **20**
- `MIXED` → **10**
- `RESTRICTIVE` → **0**
- `UNAVAILABLE` → **0**

No threshold search.

### C. Fed → Bank handoff — 0 to 25

This is a **descriptive reuse** of the already-frozen/closed `citrini-fed-bank-handoff-v1` state construction. The failed predictive result is not reopened or retuned.

Inputs:
- Fed H.4.1 total assets: fixed 13-week percentage change.
- H.8/FRED Total Assets, All Commercial Banks: fixed 13-week percentage change.

States and gauge points:
- Fed `< 0`, banks `> 0` → `PRIVATE_HANDOFF` → **25**
- Fed `>= 0`, banks `> 0` → `BROAD_EASING` → **15**
- Fed `>= 0`, banks `<= 0` → `FED_OFFSET` → **5**
- Fed `< 0`, banks `<= 0` → `TRUE_TIGHTENING` → **0**
- missing source → `UNAVAILABLE` → **0**

Bank loans/leases may be displayed as a secondary diagnostic if available, but they do **not** add points in v2.

The prior predictive family gate remains `STOP_RESEARCH_DIAGNOSTIC`; this block is narrative/current-state monitoring only.

### D. Market yield-suppression verdict — 0 / 12.5 / 25

Reuse the frozen V1 market block:
- 10Y Treasury real par yield 3M change
- 10Y Fed/Kim-Wright term premium 3M change

Points:
- both changes `<= 0` → `CONFIRM` → **25**
- one up and one down → `MIXED` → **12.5**
- both changes `> 0` → `REJECT` → **0**
- unavailable → **0**

Market `REJECT` remains an explicit conflict even if the total gauge is elevated by other blocks.

## Gauge bands

Bands are descriptive only:

- **0–24** → `DISTANT`
- **25–49** → `SETUP`
- **50–69** → `DEVELOPING`
- **70–84** → `EMERGING`
- **85–100** → `ACCORD_LIKE`

If score is `>= 85` **and** latest 10Y real yield is `< 0%`, display the separate flag `REPRESSION_RISK`.

The band is not a probability. `70` does not mean 70% probability.

## Trend

V2 computes the same frozen gauge rules on historical monthly endpoints using only observations available on or before each endpoint.

Display:
- current gauge score
- change versus approximately **1 month earlier**
- change versus approximately **3 months earlier**
- trend arrow from the sign of the 1M change: `↑`, `→`, `↓`

No smoothing, fitted trend, threshold optimization or return-based calibration is allowed in v2.

History target: at least the latest **12 monthly points** when all source paths provide sufficient history. Missing block data contribute zero under the same fail-closed rule and must be marked in coverage metadata.

## Asset interpretation

Asset labels remain scenario interpretation only; no asset is promoted by this gauge.

- **GLD / TIPS**: naturally favored as real-yield suppression/repression risk rises.
- **UST 2–5Y**: favored when Fed/reserve support and easier rate pressure are present.
- **UST 10–30Y**: tactical price support when Treasury duration pressure and market yields/term premium fall; structural real-value risk remains separate.
- **QQQ / SPY**: conditional beneficiaries of lower discount-rate pressure.
- **BTC**: RESEARCH-only high-beta debasement beneficiary.
- **DBC**: Accord alone is insufficient; separate reflation/weaker-USD confirmation is required.
- **USD**: conditional negative interpretation only when evidence is broad.

Only SPY, QQQ, GLD and DBC keep their existing promoted Money-transmission status.

## Simplicity rule

The dashboard should show, in this order:
1. one large 0–100 gauge + band + 1M/3M trend;
2. four block contributions out of 25;
3. concise bond read and asset implications;
4. raw details only underneath for audit.

Policy/regulatory headlines remain in the event ledger and **do not directly add gauge points**. They matter only when they change measurable Treasury/Fed/bank/market evidence. This prevents subjective headline scoring.

## Hard guardrails

- `evidence_tier = RESEARCH_DIAGNOSTIC`
- `scoring_effect = NONE` for GMLI regime/conviction
- `automatic_weight_change = 0`
- `methodology_effect = NONE`
- no CORE/Funding/Fiscal/Market Confirmation override
- no asset-return fitting or gauge calibration
- no rescue optimization of the failed Fed→Bank predictive relation
- source failure cannot create supportive points
- V1 remains preserved; V2 is a new version
- any future auction-level DV01/buyback model is a separate versioned candidate
