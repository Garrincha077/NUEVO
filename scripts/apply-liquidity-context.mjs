#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildLiquidityContext, enhanceLiquidityContext } from './pages-liquidity-context.mjs';
import { buildAccordWatch, accordWatchHtml } from './pages-accord-watch.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PAGES = path.join(ROOT, '.pages');
const API = path.join(PAGES, 'api');

function enhanceLiquidityGuide(html) {
  if (html.includes('id="liquidityContextGuide"')) return html;

  const anchor = '<div class="guideWarn">';
  if (!html.includes('id="investorGuide"') || !html.includes(anchor)) return html;

  const guide = `<div id="liquidityContextGuide" class="guideGrid" style="margin-top:12px">
<div class="guideCard"><h3>Liquidity Context — svrha i osvježavanje</h3><p>Liquidity Context je <b>RESEARCH_DIAGNOSTIC</b> sloj za dodatni kontekst o bankovnim bilancama i strukturi ročnosti američkog Treasury duga. Ne mijenja Money Core, Funding, Fiscal, Market Confirmation, GMLI režim ni conviction; <b>scoring effect = NONE</b> i automatic weight = 0.</p><ul><li>Preračunava se pri svakom production GitHub Pages buildu; scheduled Pages build pokreće se dnevno.</li><li>H.8 bankovni source je tjedni, a MSPD Treasury source mjesečni, pa novi dnevni build ne mora značiti novu observation.</li><li>Ako source nije dostupan, odgovarajući blok može prikazati <b>UNAVAILABLE</b>; to ne utječe na GMLI score.</li></ul></div>
<div class="guideCard"><h3>Bank balance-sheet impulse — izračun i rezultati</h3><p>Izvor je Federal Reserve H.8 preko FRED serije <b>TLAACBW027SBOG</b> (Total Assets, All Commercial Banks, weekly seasonally adjusted). Mjeri mijenja li se tempo rasta ukupne aktive komercijalnih banaka.</p><ul><li><b>Current 13W change</b> = promjena ukupne aktive od približno prije 13 tjedana do danas.</li><li><b>Prior 13W change</b> = promjena u prethodnom približno 13-tjednom razdoblju.</li><li><b>Impulse acceleration</b> = current 13W change − prior 13W change; uz to se prikazuje približni YoY rast.</li><li><b>ACCELERATING</b>: impulse &gt; 0; <b>DECELERATING</b>: impulse &lt; 0; <b>FLAT</b>: impulse = 0; <b>UNAVAILABLE</b>: nema verificiranog source rezultata.</li></ul><p>To opisuje smjer promjene tempa bankovnih bilanci, a nije samostalni bullish/bearish score.</p></div>
<div class="guideCard"><h3>Treasury duration mix — izračun i rezultati</h3><p>Izvor je U.S. Treasury Fiscal Data, MSPD Table 1. Proxy koristi <b>Debt Held by the Public</b> i pet standardnih marketable klasa: Bills, Notes, Bonds, TIPS i FRNs.</p><ul><li><b>Short/floating</b> = Bills + FRNs.</li><li><b>Fixed duration</b> = Notes + Bonds + TIPS.</li><li>Udjeli se računaju u zbroju tih pet klasa, a short/floating share uspoređuje se s približno tri mjeseca ranije.</li><li><b>MORE_SHORT_OR_FLOATING</b>: short/floating share raste; <b>MORE_FIXED_DURATION</b>: pada; <b>UNCHANGED</b>: nema promjene; <b>UNAVAILABLE</b>: nema verificiranog source rezultata.</li></ul><p>To je face-value composition proxy, ne DV01, weighted-average maturity, term-premium model niti issuance-flow model.</p></div>
<div class="guideCard"><h3>Kako čitati Liquidity Context</h3><p>Ne postoji zaseban composite Liquidity Context score. Bank impulse i Treasury duration mix čitaju se kao dva odvojena informativna smjera i mogu međusobno divergirati.</p><ul><li>Bank blok govori <b>ubrzava li ili usporava bankovna ekspanzija bilance</b>.</li><li>Treasury blok govori <b>pomaknuo li se face-value mix prema kratkom/floating ili fixed-duration dugu</b>.</li><li>Nijedan rezultat sam po sebi ne prepisuje Money Core niti automatski mijenja allocation bias.</li><li>Bilo kakav budući scoring zahtijevao bi zaseban versioned candidate i promotion gate.</li></ul></div>
</div>
`;

  return html.replace(anchor, `${guide}${anchor}`);
}

function enhanceAccordWatch(html, accord) {
  if (html.includes('id="accordWatch"')) return html;
  const anchor = '<div class="audit" id="liquidityContextAudit"';
  if (!html.includes('id="liquidityContext"') || !html.includes(anchor)) return html;
  const section = `<div class="liquidityContextGrid" style="margin-top:12px">${accordWatchHtml(accord)}</div>`;
  return html.replace(anchor, `${section}${anchor}`);
}

function enhanceAccordGuide(html) {
  if (html.includes('id="accordWatchGuide"')) return html;
  const anchor = '<div class="guideWarn">';
  if (!html.includes('id="investorGuide"') || !html.includes(anchor)) return html;
  const guide = `<div id="accordWatchGuide" class="guideGrid" style="margin-top:12px"><div class="guideCard" style="grid-column:1/-1"><h3>Accord Watch v1 — hypothesis tracker</h3><p>Accord Watch ne pretpostavlja da postoji Treasury–Fed Accord 2.0. To je <b>RESEARCH_DIAGNOSTIC</b> s weight 0 koji prati tri konkretna mehanizma: Treasury duration pressure, Fed/reserve support i market yield suppression.</p><ul><li><b>HYPOTHESIS_ONLY</b>: nema dovoljno policy/mehanizam potpore.</li><li><b>SETUP</b>: barem jedan policy/mehanizam blok je supportive, ali puna tržišna potvrda ne postoji.</li><li><b>EMERGING</b>: Treasury i Fed/reserve blok su supportive, a 10Y real yield i term premium potvrđuju kroz ne-rastući 3M pritisak.</li><li><b>REPRESSION</b>: EMERGING plus negativan 10Y real yield.</li></ul><p>Market <b>REJECT</b> nikad ne dopušta EMERGING/REPRESSION. Treasury signal je stock-change proxy, ne pravi net issuance/buyback flow.</p><p>Za obveznice se odvojeno prikazuju <b>DURATION_PRICE_SUPPORT</b> i <b>REAL_BOND_VALUE</b>, pa nominalni Treasuries mogu biti taktički podržani po cijeni, a istodobno strukturno slabi u realnim terminima. Asset map je scenario interpretation, ne trading signal ni empirical promotion.</p></div></div>`;
  return html.replace(anchor, `${guide}${anchor}`);
}

async function main() {
  const context = await buildLiquidityContext();
  if (context.version !== 'GMLI_LIQUIDITY_CONTEXT_V1') throw new Error('Unexpected liquidity context version');
  if (context.evidence_tier !== 'RESEARCH_DIAGNOSTIC') throw new Error('Liquidity context evidence tier changed');
  if (context.scoring_effect !== 'NONE' || context.automatic_weight_change !== 0 || context.methodology_effect !== 'NONE') {
    throw new Error('Liquidity context zero-scoring guard failed');
  }

  const accord = await buildAccordWatch();
  if (accord.version !== 'GMLI_ACCORD_WATCH_V1') throw new Error('Unexpected Accord Watch version');
  if (accord.evidence_tier !== 'RESEARCH_DIAGNOSTIC') throw new Error('Accord Watch evidence tier changed');
  if (accord.scoring_effect !== 'NONE' || accord.automatic_weight_change !== 0 || accord.methodology_effect !== 'NONE') {
    throw new Error('Accord Watch zero-scoring guard failed');
  }
  if (!['HYPOTHESIS_ONLY', 'SETUP', 'EMERGING', 'REPRESSION'].includes(accord.state)) {
    throw new Error(`Unexpected Accord Watch state: ${accord.state}`);
  }
  if ((accord.state === 'EMERGING' || accord.state === 'REPRESSION') && !accord.data_complete) {
    throw new Error('Accord Watch cannot be EMERGING/REPRESSION with incomplete data');
  }
  if ((accord.state === 'EMERGING' || accord.state === 'REPRESSION') && accord.market_conflict) {
    throw new Error('Accord Watch market-reject fail-closed guard failed');
  }

  await fs.mkdir(API, { recursive: true });
  await fs.writeFile(path.join(API, 'liquidity-context.json'), JSON.stringify(context, null, 2) + '\n');
  await fs.writeFile(path.join(API, 'accord-watch.json'), JSON.stringify(accord, null, 2) + '\n');

  const htmlPath = path.join(PAGES, 'index.html');
  const html = await fs.readFile(htmlPath, 'utf8');
  const enhanced = enhanceAccordGuide(enhanceAccordWatch(enhanceLiquidityGuide(enhanceLiquidityContext(html, context)), accord));
  if (!enhanced.includes('id="liquidityContext"') || !enhanced.includes('liquidity-context.json')) {
    throw new Error('Liquidity context UI integration failed');
  }
  if (!enhanced.includes('id="liquidityContextGuide"') || !enhanced.includes('Bank balance-sheet impulse — izračun i rezultati') || !enhanced.includes('Treasury duration mix — izračun i rezultati')) {
    throw new Error('Liquidity context investor guide integration failed');
  }
  if (enhanced.includes('id="bankImpulseDirection">Loading') || enhanced.includes('Loading liquidity context')) {
    throw new Error('Liquidity context must be statically rendered in the published snapshot');
  }
  if (!enhanced.includes('id="accordWatch"') || !enhanced.includes('accord-watch.json') || !enhanced.includes('id="accordWatchGuide"')) {
    throw new Error('Accord Watch static integration failed');
  }
  await fs.writeFile(htmlPath, enhanced);

  console.log(JSON.stringify({
    status: 'PASS_GMLI_LIQUIDITY_CONTEXT',
    schema_version: context.schema_version,
    version: context.version,
    evidence_tier: context.evidence_tier,
    scoring_effect: context.scoring_effect,
    automatic_weight_change: context.automatic_weight_change,
    methodology_effect: context.methodology_effect,
    bank_status: context.bank_balance_sheet_impulse.status,
    bank_latest_date: context.bank_balance_sheet_impulse.latest_date || null,
    treasury_status: context.treasury_duration_mix.status,
    treasury_latest_date: context.treasury_duration_mix.latest_date || null,
    pages_liquidity_context_ui: true,
    pages_liquidity_context_static_render: true,
    pages_liquidity_context_guide: true,
    accord_watch_version: accord.version,
    accord_watch_state: accord.state,
    accord_watch_data_complete: accord.data_complete,
    accord_watch_market_conflict: accord.market_conflict,
    accord_watch_scoring_effect: accord.scoring_effect,
    accord_watch_automatic_weight_change: accord.automatic_weight_change,
    pages_accord_watch_ui: true,
    pages_accord_watch_guide: true
  }, null, 2));
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
