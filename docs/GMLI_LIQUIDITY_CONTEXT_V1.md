# GMLI Liquidity Context v1

## Status

- Version: `GMLI_LIQUIDITY_CONTEXT_V1`
- Evidence tier: `RESEARCH_DIAGNOSTIC`
- `scoring_effect = NONE`
- `automatic_weight_change = 0`
- `methodology_effect = NONE`

Ovaj sloj je informativan. Ne mijenja Money Core, Asset Transmission, Funding V2, Fiscal V2, Market Confirmation, regime, tilt ni frozen 10-point conviction rubric.

## 1. Bank balance-sheet impulse

Izvor: Federal Reserve H.8 preko FRED serije `TLAACBW027SBOG` — Total Assets, All Commercial Banks, weekly seasonally adjusted, USD billions.

Prikazujemo:
- aktualnu razinu ukupne aktive banaka;
- promjenu kroz približno 13 tjedana;
- promjenu u prethodnih približno 13 tjedana;
- `impulse_acceleration_pp = current_13w_change_pct - prior_13w_change_pct`;
- približni YoY rast.

Interpretacija je samo smjer promjene tempa:
- `ACCELERATING` ako je impulse > 0;
- `DECELERATING` ako je impulse < 0;
- `FLAT` ako je jednak 0.

Nema dodatnih pragova niti bullish/bearish bodovanja.

## 2. Treasury duration mix proxy

Izvor: U.S. Treasury Fiscal Data, Monthly Statement of the Public Debt (MSPD), Table 1 — Summary of Treasury Securities Outstanding.

Baza je `Debt Held by the Public` za standardne marketable klase:
- Bills
- Notes
- Bonds
- Treasury Inflation-Protected Securities (TIPS)
- Floating Rate Notes (FRNs)

Proxy konstrukcija:
- `short_or_floating = Bills + FRNs`
- `fixed_duration = Notes + Bonds + TIPS`
- udjeli se računaju u zbroju pet navedenih standardnih marketable klasa;
- usporedba smjera koristi promjenu `short_or_floating_share_pct` prema približno tri mjeseca ranije.

Interpretacija:
- `MORE_SHORT_OR_FLOATING` ako je short/floating udio porastao;
- `MORE_FIXED_DURATION` ako je pao;
- `UNCHANGED` ako je isti.

Federal Financing Bank securities su isključeni. Ovo je face-value composition proxy, a ne DV01, weighted-average maturity, term-premium model ili issuance-flow model. Zato se ne smije predstavljati kao precizan mjerač tržišnog duration supplya.

## Source/failure policy

Oba izvora se dohvaćaju tijekom Pages builda. Ako pojedini izvor nije dostupan, taj blok dobiva `status = UNAVAILABLE`; izostanak podataka nikada ne mijenja GMLI score niti blokira interpretaciju postojećeg enginea.

## Promotion boundary

Bilo kakva buduća uporaba ovih podataka za scoring, conviction, asset bias ili automatsku težinu zahtijeva zaseban versioned candidate, unaprijed definiranu konstrukciju i usefulness/promotion gate. Bez toga ostaju isključivo `RESEARCH_DIAGNOSTIC`.
