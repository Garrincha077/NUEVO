#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildAccordWatch, accordWatchHtml } from './pages-accord-watch.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PAGES = path.join(ROOT, '.pages');
const API = path.join(PAGES, 'api');

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
  const guide = `<div id="accordWatchGuide" class="guideGrid" style="margin-top:12px"><div class="guideCard" style="grid-column:1/-1"><h3>Accord Watch v1 — kako ga čitati</h3><p>Accord Watch ne pretpostavlja da postoji Treasury–Fed Accord 2.0. To je <b>RESEARCH_DIAGNOSTIC hypothesis tracker</b> s weight 0 koji pita pojavljuju li se tri konkretna mehanizma.</p><ul><li><b>Treasury duration supply</b>: pada li fixed-duration udio (Notes + Bonds + TIPS) u odnosu na Bills + FRNs. To je stock-change proxy, ne pravi net issuance/buyback flow.</li><li><b>Fed / reserves</b>: 13-tjedna promjena Fed ukupne aktive i reserve balances.</li><li><b>Market verdict</b>: potvrđuju li 10Y real yield i 10Y term premium kroz ne-rastući 3M pritisak.</li></ul><p>Stanja su <b>HYPOTHESIS_ONLY → SETUP → EMERGING → REPRESSION</b>. EMERGING traži da su Treasury i Fed/reserve blok supportive te market verdict CONFIRM. REPRESSION dodatno traži negativan 10Y real yield. Market REJECT nikad ne dopušta EMERGING/REPRESSION.</p><p>Za obveznice se odvojeno prikazuju <b>DURATION_PRICE_SUPPORT</b> i <b>REAL_BOND_VALUE</b>, pa je moguće da su dugi nominalni Treasuries taktički bullish po cijeni, ali strukturno loši u realnim terminima. Asset map je scenario interpretation, ne trading signal ni empirical promotion.</p></div></div>`;
  return html.replace(anchor, `${guide}${anchor}`);
}

async function main() {
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
  await fs.writeFile(path.join(API, 'accord-watch.json'), JSON.stringify(accord, null, 2) + '\n');

  const htmlPath = path.join(PAGES, 'index.html');
  const html = await fs.readFile(htmlPath, 'utf8');
  const enhanced = enhanceAccordGuide(enhanceAccordWatch(html, accord));
  if (!enhanced.includes('id="accordWatch"') || !enhanced.includes('accord-watch.json')) {
    throw new Error('Accord Watch UI integration failed');
  }
  if (!enhanced.includes('id="accordWatchGuide"') || !enhanced.includes('HYPOTHESIS_ONLY → SETUP → EMERGING → REPRESSION')) {
    throw new Error('Accord Watch guide integration failed');
  }
  await fs.writeFile(htmlPath, enhanced);

  console.log(JSON.stringify({
    status: 'PASS_GMLI_ACCORD_WATCH_V1',
    version: accord.version,
    evidence_tier: accord.evidence_tier,
    scoring_effect: accord.scoring_effect,
    automatic_weight_change: accord.automatic_weight_change,
    methodology_effect: accord.methodology_effect,
    state: accord.state,
    data_complete: accord.data_complete,
    market_conflict: accord.market_conflict,
    treasury: accord.blocks.treasury_duration_supply.direction,
    fed_reserves: accord.blocks.fed_reserve_support.direction,
    market: accord.blocks.market_yield_suppression.direction,
    pages_accord_watch_ui: true,
    pages_accord_watch_guide: true
  }, null, 2));
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
