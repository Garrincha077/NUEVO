# GMLI Signal Role Taxonomy v1

Status: **RESEARCH interpretation — recorded / no scoring change**

Recorded: 2026-08-25

## Purpose

Separate GMLI signals by what they empirically appear to do, instead of treating every useful macro/market layer as an independent leading predictor.

This taxonomy is descriptive. It does **not** change Core/Overlay evidence tiers, scores, thresholds, promotion status or the 10-point conviction rubric.

## Roles

### Money Core — LEADING

`GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL`

Use as the upstream 3–12M regime layer.

Evidence:
- promoted Money V2 transmission transfer remains 6/6 under the frozen relationships;
- fixed directional follow-up found no robust market→Money dominance across the stationary promoted transforms;
- SPY Money accel3 12M correlation: forward +0.452 vs trailing +0.015;
- QQQ: forward +0.414 vs trailing +0.216;
- QQQ fixed 3M ex-pandemic Money→QQQ Granger p=0.0475, while QQQ→Money p=0.696;
- GLD is weaker/mixed in the broad lead-lag diagnostic and should remain asset-specific;
- DBC USD Money level has strong forward association but failed the fixed ADF 5% stationarity check (p=0.0985), so its Granger values are excluded from role classification.

`LEADING` is **not** a structural-causality claim and not a claim that Money times every monthly move.

### Funding V2 — REACTIVE_CONFIRMATION

`GMLI_FUNDING_V2_EFFECTIVE_CONDITIONS`

Use primarily as a financial-conditions/friction overlay.

Fixed reverse-mechanism research found:
- SPY/QQQ → Funding: 6/6 Holm-significant 1/3/6M tests;
- Funding → SPY/QQQ: 0/6;
- after excluding 2020-03..2021-12: again 6/6 vs 0/6;
- VIX absorbs most incremental SPY information, consistent with a shared financial-stress channel;
- ANFCI and reserves carry the clearest input-level market precedence.

Funding's promoted DBC 6M/12M usefulness evidence remains valid as an association. It is not upgraded to a causal claim.

### Fiscal V2 — MIXED

`GMLI_FISCAL_V2_DEFICIT_IMPULSE`

Use as policy/fiscal context and confirmation, not as a clean independent leading layer.

Evidence:
- fixed SPY 12M usefulness gate passed;
- full-sample SPY→Fiscal 3M reverse precedence was significant after Holm (p=0.0356);
- that reverse effect disappears ex-pandemic and under VIX + unemployment controls;
- Fiscal is more related to trailing than forward 12M SPY in the causality follow-up.

Automatic global conviction weight remains **0**.

### Market confirmation — REACTIVE_CONFIRMATION

Completed-month price turn is confirmation by construction. It validates or contradicts the upstream Money thesis; it does not create the macro regime.

## Is Funding double-counting Market Confirmation?

The fixed overlap diagnostic says **not materially**.

Aligned sample: 222 months, 2007-03..2025-08.

- Funding raw vs market score Pearson: +0.232
- Spearman: +0.080
- Funding rubric 0–2 vs market 0–2 Pearson: +0.128
- Spearman: +0.087
- exact 0–2 score agreement: 23.0%

So Funding and Market Confirmation are both reactive, but they measure different things:
- Funding: financial conditions / volatility / rates / reserves;
- Market Confirmation: cross-asset completed-month price trend.

Adding Funding to a market-score-only 12M SPY regression raised descriptive R² by 0.085, but the Funding HAC coefficient was not significant (p=0.316). This does not justify changing the frozen rubric.

## Practical hierarchy

1. **Money Core [LEADING]** — baseline regime.
2. **Asset Transmission** — where the Money signal has promoted empirical mapping.
3. **Funding V2 [REACTIVE_CONFIRMATION]** — current financial friction / confidence modifier.
4. **Fiscal V2 [MIXED]** — fiscal/policy context; zero automatic weight.
5. **Market Confirmation [REACTIVE_CONFIRMATION]** — price validation/divergence.

## Guardrail

No score, threshold, weight or promoted relationship changed.

If this role taxonomy is ever used to reweight/de-duplicate the conviction rubric, that must be a separately frozen versioned decision-engine candidate with its own predeclared gate.

Canonical result: `research/signal-role-taxonomy/RESULT_SUMMARY.json`.
