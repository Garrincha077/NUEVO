# GMLI Signal Role Taxonomy v1

Status: ACTIVE INTERPRETATION STANDARD
Evidence tier of the taxonomy itself: RESEARCH
Scoring effect: NONE
Recorded: 2026-08-25

## Purpose

GMLI ne smije tretirati svaki koristan signal kao neovisan leading predictor. Ovaj standard razdvaja funkciju sloja od njegova CORE/OVERLAY/RESEARCH evidence tiera.

## Roles

### LEADING
Upstream signal s promoviranim forward evidenceom i bez robusne market-to-signal dominacije u fiksnom direction testu.

Ne znači strukturnu uzročnost niti da signal pouzdano timea svaki monthly move.

### REACTIVE_CONFIRMATION
Signal primarno opisuje ili potvrđuje aktualno stanje, friction ili price response. Tržište/stress mu može vremenski prethoditi.

Takav signal može biti važan za conviction i risk context bez toga da bude samostalan leading forecast.

### MIXED
Postoji korisna forward asocijacija, ali temporal direction je regime-dependent, control-sensitive ili dvosmislen.

## Current GMLI classification

| Layer | Role | Practical use |
|---|---|---|
| Money Core | LEADING | Baseline 3–12M liquidity/money regime |
| Asset Transmission | TRANSMISSION MAP | Gdje promoted Money signal ima empirijsku asset vezu |
| Funding V2 | REACTIVE_CONFIRMATION | Financial conditions/friction i bounded conviction context |
| Fiscal V2 | MIXED | Fiscal/policy context; zero automatic conviction weight |
| Market Confirmation | REACTIVE_CONFIRMATION | Completed-month price validation/divergence |

## Evidence

### Money Core
- Promoted Money V2 fixed transmission transfer: 6/6.
- Fixed role-direction follow-up: nema robusne market→Money dominacije na stacionarnim promoviranim transformima.
- SPY Money accel3: 12M forward Pearson +0.452 vs trailing +0.015.
- QQQ: forward +0.414 vs trailing +0.216.
- QQQ fixed 3M ex-pandemic Money→QQQ Granger p=0.0475; QQQ→Money p=0.696.
- GLD broad lead/lag je slabiji/mixed i ostaje asset-specific.
- DBC USD Money level ima jaku forward asocijaciju, ali ADF p=0.0985; zato se njegov Granger ne koristi za role classification.

Zaključak: Money ostaje **LEADING**, bez causal claima.

### Funding V2
Fixed reverse research:
- SPY/QQQ→Funding: 6/6 Holm-significant 1/3/6M testova.
- Funding→SPY/QQQ: 0/6.
- Ex-pandemic: ponovno 6/6 vs 0/6.
- VIX apsorbira većinu incremental SPY informacije, što upućuje na shared financial-stress channel.
- ANFCI i reserves nose najsnažniji input-level reverse precedence.

Zaključak: Funding je **REACTIVE_CONFIRMATION**, ne clean equity-leading signal. Njegov promoted DBC 6M/12M usefulness ostaje valjana asocijacija, ne causal claim.

### Fiscal V2
- Fixed SPY 12M usefulness gate: PASS.
- Full-sample SPY→Fiscal 3M reverse Holm p=0.0356.
- Reverse effect nestaje ex-pandemic i uz VIX + unemployment controls.
- SPY trailing 12M association je jača od forward u causality follow-upu.

Zaključak: Fiscal je **MIXED**, praktično policy/confirmation context. `automatic_global_conviction_weight = 0` ostaje nepromijenjen.

### Funding vs Market Confirmation overlap
Aligned 2007-03..2025-08, n=222:
- Funding raw vs market score Pearson +0.232; Spearman +0.080.
- Funding rubric 0–2 vs market score 0–2 Pearson +0.128; Spearman +0.087.
- Exact 0–2 agreement ~23%.

Zaključak: oba sloja jesu reactive, ali nisu isti signal. Funding mjeri financial conditions/volatility/rates/reserves, Market Confirmation cross-asset price turn. Ovaj test ne opravdava promjenu frozen 10-point rubrika.

## Mandatory interpretation order

1. Money Core [LEADING] postavlja baseline regime.
2. Asset Transmission određuje gdje je promoted Money mapping najjači.
3. Funding V2 [REACTIVE_CONFIRMATION] govori koliko su aktualni financial conditions supportive/restrictive i može mijenjati confidence, ali ne baseline Core.
4. Fiscal V2 [MIXED] daje fiscal/policy context s automatic weight 0.
5. Market Confirmation [REACTIVE_CONFIRMATION] potvrđuje ili divergira od upstream teze.

## Guardrail

Ova taxonomy ne mijenja:
- Money Core,
- Funding/Fiscal formule,
- promoted transmission odnose,
- regime thresholds,
- 10-point conviction weights,
- CORE / OVERLAY / RESEARCH evidence tiers.

Bilo kakva role-based reweighting ili de-duplication mora ići kroz zaseban versioned decision-engine candidate s predeclared empirical gateom.

Research audit:
- `research/signal-role-taxonomy/RESULT_SUMMARY.json`
- `research/reverse-overlay-mechanism/RESULT_SUMMARY.json`
