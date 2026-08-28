# GMLI Accord Watch — current analyst handoff

Status: **RESEARCH_DIAGNOSTIC / zero GMLI scoring / zero automatic weight**

Primary current presentation layer: `GMLI_ACCORD_WATCH_V2`  
Canonical v2 construction: `docs/GMLI_ACCORD_WATCH_V2.md`  
Detailed v2 analyst note: `docs/GMLI_ACCORD_WATCH_V2_HANDOFF.md`

Frozen v1 remains preserved for audit at `docs/GMLI_ACCORD_WATCH_V1.md` and `./api/accord-watch.json`.

## Analyst use

Accord Watch answers one narrow question: **how close are measurable conditions to the hypothesized Treasury–Fed Accord 2.0 / financial-repression setup, and is that closeness increasing or decreasing?**

Never assume that the Accord exists.

For current analysis read, in order:
1. `./api/accord-watch-v2.json`
2. `./api/accord-watch-history.json` when trend context is needed
3. `./api/accord-watch.json` only for the frozen v1 audit/state-machine comparison
4. `./api/report.json` for the actual GMLI Core/Overlay decision context.

## V2 gauge

The v2 0–100 number is a **presentation closeness gauge**, not probability and not GMLI conviction.

Bands:
- `0–24 DISTANT`
- `25–49 SETUP`
- `50–69 DEVELOPING`
- `70–84 EMERGING`
- `85–100 ACCORD_LIKE`

A separate `REPRESSION_RISK` flag requires score >=85 plus negative 10Y real yield.

Four equal 25-point blocks:
1. Treasury duration pressure
2. Fed / reserve support
3. Fed → Bank handoff
4. market yield suppression.

Treasury itself splits 12.5/12.5 between the frozen v1 composition check and the monthly net-outstanding-change supply proxy.

## Fed → Bank handoff boundary

The current handoff block is descriptive only. The prior frozen predictive family gate is permanently:

`STOP_RESEARCH_DIAGNOSTIC`

Do not optimize it further or represent the handoff points as a return forecast.

## Trend

Use the same frozen v2 gauge applied at historical cutoffs:
- `trend.delta_1m_points`
- `trend.delta_3m_points`
- `trend.arrow`
- `./api/accord-watch-history.json`

No smoothing or return-based calibration.

## Bonds

Always separate:
- `DURATION_PRICE_SUPPORT` — tactical nominal bond price support;
- `REAL_BOND_VALUE` — sign of the 10Y real yield.

It is valid to say nominal duration is tactically supported while long-run real value is poor.

## Asset interpretation boundary

Asset labels are **scenario interpretation only**, not empirical promotion or trade instructions. Only SPY, QQQ, GLD and DBC retain their existing promoted Money-transmission status.

- GLD / TIPS: most naturally helped as real yields are suppressed.
- 2–5Y UST: helped by easier Fed/reserve/rate pressure.
- 10–30Y UST: tactical duration-price beneficiary if term premium/real yields fall; real-value risk under repression.
- QQQ / SPY: conditional beneficiaries of lower discount-rate pressure.
- BTC: RESEARCH-only high-beta debasement interpretation.
- DBC: requires separate reflation / weaker-USD confirmation; Accord alone is insufficient.
- USD: only conditional negative interpretation once evidence is broad.

## Policy / regulatory events

Policy headlines and Citrini-style regulatory catalysts belong in the event ledger and **do not directly add gauge points**. The gauge moves only when Treasury/Fed/bank/market evidence changes. This keeps the tracker simple and avoids subjective headline scoring.

## Hard guardrails

- `scoring_effect = NONE` for GMLI regime/conviction
- `automatic_weight_change = 0`
- `methodology_effect = NONE`
- no Core/Funding/Fiscal/Market Confirmation override
- no probability language from the v2 number
- no parameter/threshold/lag/horizon/asset/subperiod optimization
- source failure fails closed to zero support for the missing block
- v1 remains frozen/auditable
- auction-level DV01/WAM/buyback accounting, if ever needed, requires a separate versioned candidate.

## Production verification

A Git commit is not live evidence. After any implementation change verify the published GitHub Pages snapshot, especially:
- `./api/report.json`
- `./api/accord-watch.json`
- `./api/accord-watch-v2.json`
- `./api/accord-watch-history.json`
- `./api/liquidity-context.json`
- dashboard gauge and Guide section.

The production state may change with source refreshes, so do not reuse a historical state from this document.
