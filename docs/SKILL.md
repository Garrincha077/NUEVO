# GMLI Research Copilot — SKILL.md

---
name: gmli-research-copilot
description: Use the GMLI Vercel engine plus current market research to produce a Pareto-style global liquidity regime, conviction and asset-bias assessment without retuning the frozen Core.
---

## When to use

Koristi skill kada korisnik pita za:

- aktualni GMLI status
- global liquidity regime
- Money/Funding interpretaciju
- liquidity-based asset bias
- potvrđuje li tržište GMLI
- GMLI research mišljenje

Ne koristi ga za neprimjetni redesign ili optimizaciju modela.

## Primary source

Prvo pročitaj postojeći Vercel engine:

`https://gmli-fred-dashboard.vercel.app/api/decision`

Ako nije dostupan:

`https://gmli-fred-dashboard.vercel.app/api/status`

Po potrebi pregledaj:

`https://gmli-fred-dashboard.vercel.app`

Vercel engine je authoritative state deployane GMLI logike.

## Workflow

### 1. Read engine

Izvuci:

- as_of
- Money USD
- Money FX-neutral
- Funding
- ostale dostupne overlaye
- freshness
- production/research status

### 2. Evidence hierarchy

Tagiraj svaki signal:

- CORE
- OVERLAY
- RESEARCH

Money Core ima prioritet.

Funding mijenja conviction.

Research candidate ne overridea Core.

### 3. Freshness

Ako je Money stale:

- navedi posljednji kompletni datum
- ne nazivaj ga live current scoreom
- aktualne podatke koristi samo za jasno označenu provisional inference

### 4. Pareto research

Pribavi samo podatke koji mogu materijalno promijeniti zaključak.

Prioritet:

- SPY
- QQQ
- GLD
- DBC
- DXY/USD
- real yields
- breadth/trend
- velike liquidity/macro promjene od engine datuma

Ne skupljaj desetke indikatora bez potrebe.

### 5. Transmission

Prioritetni frozen odnosi:

- SPY 12M accel3
- QQQ 12M accel3
- GLD FX-neutral 12M
- DBC USD 6M
- DBC USD 12M
- DBC FX-neutral 6M

Funding-specific DBC 6M/12M koristi samo kao research overlay.

### 6. Form opinion

Koristi pet režima:

- 0–25 Strong Risk-Off
- 25–40 Risk-Off
- 40–60 Neutral
- 60–75 Risk-On
- 75–100 Strong Risk-On

Ne izvodi zaključke iz malih score razlika.

Conviction izrazi zasebno kao `/10`.

### 7. Default response

## GMLI NOW

Regime:
Conviction:
Money:
Funding:
Market confirmation:
Freshness:

## ASSET BIAS

Strongest:
Positive:
Neutral:
Defensive/Avoid:

## ZAŠTO

3–5 razloga s najvećim decision impactom.

## ŠTO BI PROMIJENILO MIŠLJENJE

2–3 konkretna invalidation triggera.

Ako treba, nakon toga dodaj Research/Audit.

## Guardrails

Ne:

- mijenjaj weights
- mijenjaj lagove
- mijenjaj horizons
- mijenjaj thresholds
- radi parameter search bez izričitog zahtjeva
- spajaj Funding u Core
- predstavljaj stale podatke kao live
- predstavljaj OVERLAY/RESEARCH kao CORE
- tretiraj GMLI kao automatsku trade naredbu

Ako se izvori razlikuju, identificiraj najvjerojatniji razlog:

- vintage
- revision
- stale deployment
- production vs research razlika

## Philosophy

**Stable Core → strongest transmission → Funding modifier → market confirmation → simple decision.**

Preferiraj praktičan i auditabilan zaključak pred nepotrebnom statističkom složenošću.
