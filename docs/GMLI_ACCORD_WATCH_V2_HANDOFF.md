# GMLI Accord Watch v2 — analyst handoff

Status: **RESEARCH_DIAGNOSTIC / PRESENTATION SCORE / zero GMLI weight**

Canonical frozen construction: `docs/GMLI_ACCORD_WATCH_V2.md`.

## What it answers

Accord Watch v2 answers one practical question:

> **How close are measurable Treasury/Fed/bank/market conditions to the hypothesized Citrini-style Treasury–Fed Accord 2.0 / financial-repression setup, and is that closeness increasing or decreasing?**

Read the latest production `./api/accord-watch-v2.json` first. A Git commit is not live evidence.

## Gauge

- 0–24 `DISTANT`
- 25–49 `SETUP`
- 50–69 `DEVELOPING`
- 70–84 `EMERGING`
- 85–100 `ACCORD_LIKE`
- score >=85 plus negative 10Y real yield → separate `REPRESSION_RISK=true`

The number is **not a probability** and **not the GMLI conviction score**.

## Four blocks

Each carries 25 presentation points:
1. Treasury duration pressure
2. Fed / reserve support
3. Fed → Bank handoff
4. market yield-suppression verdict

Treasury itself is split 12.5/12.5 between the frozen V1 3M composition check and the monthly net-outstanding-change supply proxy.

Policy/regulatory headlines do not directly add points. They belong in the event ledger and matter when they change measured Treasury/Fed/bank/market evidence.

## Fed → Bank boundary

The handoff block reuses the already-frozen descriptive state construction:
- `PRIVATE_HANDOFF`
- `BROAD_EASING`
- `FED_OFFSET`
- `TRUE_TIGHTENING`

The predictive research remains permanently `STOP_RESEARCH_DIAGNOSTIC`. Do not optimize lags, thresholds, windows, assets or subperiods to rescue it.

## Trend

Use:
- `trend.delta_1m_points`
- `trend.delta_3m_points`
- `trend.arrow`
- `./api/accord-watch-history.json`

Trend is the same frozen score applied at historical cutoffs; there is no fitted smoothing or return calibration.

## Bonds

Always keep two outputs separate:
- `DURATION_PRICE_SUPPORT` — tactical price support
- `REAL_BOND_VALUE` — current sign of the 10Y real yield

Long nominal duration can be tactically bullish while structurally unattractive in real terms.

## Asset interpretation

Scenario interpretation only:
- GLD / TIPS: strongest natural beneficiaries as real-yield suppression grows
- 2–5Y UST: helped by Fed/reserve support and easier rate pressure
- 10–30Y UST: tactical beneficiary only when Treasury/market duration pressure confirms
- QQQ / SPY: conditional lower-discount-rate beneficiaries
- BTC: RESEARCH-only high-beta debasement beneficiary
- DBC: needs separate reflation/weaker-USD confirmation
- USD: only conditionally negative with broad evidence

Only SPY, QQQ, GLD and DBC keep their pre-existing promoted Money-transmission status.

## Guardrails

- evidence tier RESEARCH_DIAGNOSTIC
- GMLI `scoring_effect = NONE`
- `automatic_weight_change = 0`
- `methodology_effect = NONE`
- no CORE/Funding/Fiscal/Market Confirmation override
- no probability language from the 0–100 gauge
- no predictive promotion from the handoff block
- source failure contributes zero support and must remain visible in coverage
- V1 remains preserved at `./api/accord-watch.json`

## Production verification

After any implementation change verify:
- `./api/report.json`
- `./api/accord-watch.json` (frozen v1 audit)
- `./api/accord-watch-v2.json`
- `./api/accord-watch-history.json`
- dashboard gauge and Guide section
- source checks + Pages build/deploy
