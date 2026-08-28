# GMLI Accord Watch v1 — handoff

Status: **RESEARCH_DIAGNOSTIC / zero scoring / zero automatic weight**

Canonical construction: `docs/GMLI_ACCORD_WATCH_V1.md`.

## Analyst use

Accord Watch answers one narrow question: **is the hypothesized Treasury–Fed Accord 2.0 / financial-repression setup actually beginning to materialize?**

Never assume that the Accord exists. Read the latest production `./api/accord-watch.json` first.

State order:
- `HYPOTHESIS_ONLY`
- `SETUP`
- `EMERGING`
- `REPRESSION`

Interpret the three blocks separately:
1. Treasury duration-supply pressure proxy;
2. Fed / reserve support;
3. market yield-suppression verdict.

`EMERGING` requires Treasury supportive + Fed/reserve supportive + market `CONFIRM`. `REPRESSION` additionally requires a negative 10Y real yield. Market `REJECT` blocks both.

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

## Hard guardrails

- `scoring_effect = NONE`
- `automatic_weight_change = 0`
- `methodology_effect = NONE`
- no Core/Funding/Fiscal/Market Confirmation override
- no 0–100 Accord score
- no parameter/threshold/lag/horizon/asset/subperiod optimization
- source failure fails closed
- Treasury block is a stock-change composition proxy, not true net issuance, DV01, WAM or buyback flow
- any future true issuance/buyback-flow model is a separate versioned candidate

## Production verification

A Git commit is not live evidence. After any implementation change verify the published GitHub Pages snapshot, especially:
- `./api/accord-watch.json`
- `./api/liquidity-context.json`
- `./api/report.json`
- dashboard Accord Watch card and Guide section.

The production state may change with source refreshes, so do not reuse a historical state from this document.
