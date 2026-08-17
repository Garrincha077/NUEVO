# GMLI — Project Documentation

## 1. Purpose

GMLI — Global Money & Liquidity Intelligence — praktični je decision system za procjenu globalnog monetarno-likvidnosnog režima i njegov prijenos na glavne klase imovine.

Glavno pitanje:

**Kakav je aktualni globalni liquidity regime, gdje se likvidnost najjasnije prenosi i što to znači za positioning tijekom približno sljedećih 3–12 mjeseci?**

Projekt koristi Pareto pristup: prioritet imaju robusni i decision-relevant signali, a ne maksimalna složenost modela.

---

## 2. Product architecture

### Level 1 — Decision

Pogled od desetak sekundi:

- GMLI regime
- conviction /10
- Money
- Funding
- Market Confirmation
- strongest / positive / neutral / defensive asset bias

### Level 2 — Why

Četiri glavna bloka:

1. Money Core
2. Asset Transmission
3. Funding / Financial Conditions
4. Market Confirmation

### Level 3 — Research / Audit

Sadrži:

- frozen specifications
- train/OOS rezultate
- FDR testove
- provenance
- vintages/revisions
- sensitivity testove
- source bytes i hashes
- migration rezultate
- test-suite rezultate

Research detalji ne smiju zatrpati glavni decision screen.

---

## 3. Core hierarchy

### 3.1 Money Core

Money je primarni makro signal i određuje baseline regime.

Pratimo:

- USD global money
- FX-neutral global money
- growth/impulse
- acceleration
- freshness
- coverage

Production Core mora imati čist source chain i frozen metodologiju.

### 3.2 Asset Transmission

Ne pretpostavljamo da liquidity djeluje jednako na sve assete.

Prioritetni odnosi iz migration researcha:

- SPY 12M accel3
- QQQ 12M accel3
- GLD FX-neutral 12M
- DBC USD 6M
- DBC USD 12M
- DBC FX-neutral 6M

Commodities zaslužuju poseban transmission view.

### 3.3 Funding

Funding nije univerzalni Core faktor.

v1.3 preliminary 4/5 empirical gate pokazuje preslab široki incremental OOS benefit za Core merge.

Funding zato ostaje:

**RESEARCH / REGIME OVERLAY**

Koristi se kao modifier convictiona:

- supportive
- neutral
- restrictive

Najzanimljiviji Funding-specific research kandidati su DBC 6M i 12M.

Funding ne smije automatski overrideati Money.

### 3.4 Market Confirmation

Aktualno tržište služi kao potvrda ili divergencija makro signala.

Prioritet:

- SPY
- QQQ
- GLD
- DBC
- DXY/USD
- real yields
- trend
- breadth
- značajne makro promjene od zadnje kompletne Money observacije

Market confirmation može promijeniti conviction ili najbolju asset ekspresiju.

Ne smije retunirati frozen GMLI.

---

## 4. Evidence tiers

Svaki signal ima status:

### CORE

Frozen i production/promoted signal.

### OVERLAY

Ekonomski ili empirijski koristan, ali nije odobren kao Core.

### RESEARCH

Obećavajući kandidat kojem treba dodatna potvrda.

Overlay ili research signal ne smije se neprimjetno promovirati.

---

## 5. Trenutni research status

### Money migration v1.8b

Migration rezultat je empirijski snažan, ali production promotion zahtijeva završni provenance gate.

Frozen nalazi:

- 9/9 ključnih pozitivnih hipoteza zadržava smjer
- 6/9 prolazi migration-only FDR
- 7/7 ključnih DBC/GLD odnosa zadržava smjer
- SPY i QQQ 12M accel3 preživljavaju
- GLD FX-neutral 12M preživljava
- DBC USD 6M i 12M preživljavaju
- DBC FX-neutral 6M preživljava

Production v1.7 ostaje netaknut dok v1.8b ne prođe završni gate.

Tijekom završnog reruna zabranjeno je mijenjati:

- weights
- lagove
- horizons
- thresholds
- FDR metodologiju

### Australia

AU growth koristi službeni RBA break-adjusted i seasonally adjusted published Broad Money growth.

RBA D3/DMABMS level history koristi se samo za:

**prior-year AU USD-share accounting weight + provenance/audit**

Ne koristi se za rekonstrukciju AU growtha.

AU accounting weight pokazao se ekonomski nematerijalno osjetljiv na ±15% level stress.

### Funding v1.3

Status:

`FAIL_CORE_MERGE`

Odnosno:

`KEEP_AS_SEPARATE_RESEARCH_OVERLAY`

Trenutni preliminary run ima 4/5 Funding komponenti.

Nedostaje Kim-Wright 10Y term-premium monthly-average snapshot.

Budući 5/5 run smije biti samo frozen confirmation test.

Nema retuninga.

---

## 6. Decision framework

Dashboard koristi pet širokih režima:

| Score | Regime |
|---|---|
| 0–25 | Strong Risk-Off |
| 25–40 | Risk-Off |
| 40–60 | Neutral |
| 60–75 | Risk-On |
| 75–100 | Strong Risk-On |

Score je pomoćni decision summary.

Male razlike u scoreu ne smiju izazivati promjenu portfelja.

---

## 7. Conviction

Conviction je odvojen od režimskog scorea.

Procjenjuje se iz:

- Money freshness
- slaganja USD i FX-neutral Money
- snage transmissiona
- Funding confirmationa
- market confirmationa
- kvalitete/provenance podataka

Standardni prikaz:

**Conviction: 1–10**

---

## 8. Vercel

Project:

`gmli-fred-dashboard`

Production dashboard:

`https://gmli-fred-dashboard.vercel.app`

Machine-readable endpoint:

`https://gmli-fred-dashboard.vercel.app/api/status`

Planirani Pareto endpoint:

`/api/decision`

### /api/decision treba vraćati

- as_of
- regime
- conviction_inputs
- money
- funding
- market_confirmation
- asset_bias
- freshness
- evidence_tiers
- key_reasons
- invalidation_triggers

Endpoint mora biti read-only.

Ne smije mijenjati frozen engine.

---

## 9. ChatGPT workflow

Kod aktualnog GMLI pitanja:

1. pročitaj `/api/decision`, ako postoji
2. inače pročitaj `/api/status`
3. provjeri freshness
4. razlikuj CORE / OVERLAY / RESEARCH
5. pribavi samo aktualne podatke koji mogu promijeniti odluku
6. usporedi tržište s engine signalom
7. formiraj GMLI regime i conviction
8. rangiraj asset bias
9. navedi razloge
10. navedi invalidation triggere

Uvijek razlikuj:

**ENGINE FACT**

od

**CURRENT RESEARCH INFERENCE**

---

## 10. Default output

### GMLI NOW

Regime  
Conviction  
Money  
Funding  
Market Confirmation  
Freshness

### ASSET BIAS

Strongest  
Positive  
Neutral  
Defensive/Avoid

### ZAŠTO

3–5 najvažnijih razloga.

### ŠTO BI PROMIJENILO MIŠLJENJE

2–3 konkretna triggera.

---

## 11. Guardrails

Nikada:

- ne optimizirati parametre tijekom običnog dashboard upita
- ne backfitati nakon tržišnog ishoda
- ne predstavljati stale Money kao live signal
- ne spajati Funding u Core bez promotion passa
- ne predstavljati RESEARCH kao CORE
- ne skrivati vintage/revision konflikte
- ne generirati automatski trade samo na temelju GMLI scorea

---

## 12. Operating principle

**Stable Core + strongest transmission + lightweight overlays + current market confirmation + simple decision output.**

Cilj nije znanstveno savršen model.

Cilj je robustan, auditabilan i praktično koristan decision process.
