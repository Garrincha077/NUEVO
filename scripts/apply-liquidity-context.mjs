#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildLiquidityContext, enhanceLiquidityContext } from './pages-liquidity-context.mjs';
import { buildAccordWatch } from './pages-accord-watch.mjs';
import { buildAccordWatchV2, accordWatchV2Html } from './pages-accord-watch-v2.mjs';

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
<div class="guideCard"><h3>Kako čitati Liquidity Context</h3><p>Bank impulse i Treasury duration mix ostaju raw audit kontekst. Novi Accord Watch v2 ih komprimira zajedno s Fed/reserve, private-bank handoff i market-yield evidenceom u zaseban presentation gauge koji i dalje ima <b>zero GMLI scoring effect</b>.</p><ul><li>Raw Liquidity Context ne prepisuje Money Core.</li><li>Accord gauge nije probability i nije portfolio weight.</li><li>Policy headline sam po sebi ne dodaje bodove dok ne promijeni mjerljive podatke.</li><li>Bilo kakav budući production scoring zahtijevao bi zaseban promotion candidate.</li></ul></div>
</div>
`;

  return html.replace(anchor, `${guide}${anchor}`);
}

function enhanceAccordStyles(html) {
  if (html.includes('.accordGaugeWrap{')) return html;
  const css = `.accordGaugeCard{overflow:hidden}.accordGaugeWrap{display:grid;grid-template-columns:minmax(220px,340px) 1fr;gap:18px;align-items:center;margin-top:10px}.accordGauge{position:relative;min-height:180px}.accordGauge svg{width:100%;height:170px;display:block}.accordGaugeBase,.accordGaugeFill{fill:none;stroke-width:18;stroke-linecap:round}.accordGaugeBase{stroke:#1c3142}.accordGaugeFill{stroke:#8fb8d3}.accordGaugeValue{position:absolute;left:0;right:0;bottom:30px;text-align:center;font-size:42px;font-weight:780;letter-spacing:-.04em}.accordGaugeValue span{font-size:15px;color:#8ea3b4;letter-spacing:0}.accordGaugeBand{text-align:center;margin-top:-24px;font-size:12px;color:#9fb1c1;letter-spacing:.08em}.accordGaugeSummary{min-width:0}@media(max-width:760px){.accordGaugeWrap{grid-template-columns:1fr}.accordGauge{min-height:155px}.accordGauge svg{height:150px}}`;
  return html.replace('</style>', `${css}</style>`);
}

function enhanceAccordWatchV2(html, accordV2) {
  if (html.includes('id="accordWatchV2"')) return html;
  const anchor = '<div class="audit" id="liquidityContextAudit"';
  if (!html.includes('id="liquidityContext"') || !html.includes(anchor)) return html;
  const section = `<div class="liquidityContextGrid" style="margin-top:12px">${accordWatchV2Html(accordV2)}</div>`;
  return enhanceAccordStyles(html.replace(anchor, `${section}${anchor}`));
}

function enhanceAccordGuideV2(html) {
  if (html.includes('id="accordWatchGuideV2"')) return html;
  const anchor = '<div class="guideWarn">';
  if (!html.includes('id="investorGuide"') || !html.includes(anchor)) return html;
  const guide = `<div id="accordWatchGuideV2" class="guideGrid" style="margin-top:12px"><div class="guideCard" style="grid-column:1/-1"><h3>Accord Watch v2 — jednostavni 0–100 Citrini gauge</h3><p>Gauge pokazuje <b>koliko su mjerljivi uvjeti blizu hypothesized Treasury–Fed Accord / financial-repression setupu</b>. To nije probability, nije GMLI regime score i nema portfolio weight. V1 ostaje frozen audit; v2 je zaseban presentation/research candidate.</p><ul><li><b>0–24 DISTANT</b>: daleko od scenarija.</li><li><b>25–49 SETUP</b>: dio mehanizama se pojavljuje.</li><li><b>50–69 DEVELOPING</b>: više kanala ide u istom smjeru.</li><li><b>70–84 EMERGING</b>: većina mehanizama je usklađena.</li><li><b>85–100 ACCORD_LIKE</b>: gotovo svi mjerljivi kanali potvrđuju; negativan 10Y real yield dodatno pali REPRESSION_RISK.</li></ul><p>Četiri jednaka bloka nose po 25 bodova: <b>Treasury duration pressure</b>, <b>Fed/reserves</b>, <b>Fed→Bank handoff</b> i <b>market yield suppression</b>. Treasury blok pola bodova daje frozen 3M composition pravilu, a pola mjesečnom net-outstanding-change supply proxyju.</p><p><b>Trend</b> je isti frozen score izračunat približno 1M i 3M ranije; strelica samo pokazuje smjer promjene. Handoff predictive research ostaje STOP_RESEARCH_DIAGNOSTIC — u gaugeu je samo descriptive current-state evidence, bez rescue optimizacije.</p><p>Za bonds se i dalje odvojeno čitaju <b>DURATION_PRICE_SUPPORT</b> i <b>REAL_BOND_VALUE</b>. Policy/regulatory headline ne dobiva bodove sam po sebi; bodovi se mijenjaju tek kad se promijene Treasury/Fed/bank/market podaci.</p></div></div>`;
  return html.replace(anchor, `${guide}${anchor}`);
}

async function main() {
  const context = await buildLiquidityContext();
  if (context.version !== 'GMLI_LIQUIDITY_CONTEXT_V1') throw new Error('Unexpected liquidity context version');
  if (context.evidence_tier !== 'RESEARCH_DIAGNOSTIC') throw new Error('Liquidity context evidence tier changed');
  if (context.scoring_effect !== 'NONE' || context.automatic_weight_change !== 0 || context.methodology_effect !== 'NONE') {
    throw new Error('Liquidity context zero-scoring guard failed');
  }

  const accordV1 = await buildAccordWatch();
  if (accordV1.version !== 'GMLI_ACCORD_WATCH_V1') throw new Error('Unexpected Accord Watch v1 version');
  if (accordV1.evidence_tier !== 'RESEARCH_DIAGNOSTIC') throw new Error('Accord Watch v1 evidence tier changed');
  if (accordV1.scoring_effect !== 'NONE' || accordV1.automatic_weight_change !== 0 || accordV1.methodology_effect !== 'NONE') {
    throw new Error('Accord Watch v1 zero-scoring guard failed');
  }

  const accordV2 = await buildAccordWatchV2();
  if (accordV2.version !== 'GMLI_ACCORD_WATCH_V2') throw new Error('Unexpected Accord Watch v2 version');
  if (accordV2.evidence_tier !== 'RESEARCH_DIAGNOSTIC' || accordV2.presentation_score !== true) {
    throw new Error('Accord Watch v2 evidence/presentation contract changed');
  }
  if (accordV2.scoring_effect !== 'NONE' || accordV2.automatic_weight_change !== 0 || accordV2.methodology_effect !== 'NONE') {
    throw new Error('Accord Watch v2 zero-GMLI-scoring guard failed');
  }
  if (!Number.isFinite(Number(accordV2.score)) || Number(accordV2.score) < 0 || Number(accordV2.score) > 100) {
    throw new Error(`Accord Watch v2 score out of range: ${accordV2.score}`);
  }
  const weightTotal = Object.values(accordV2.methodology?.weights || {}).reduce((a, b) => a + Number(b || 0), 0);
  if (weightTotal !== 100) throw new Error(`Accord Watch v2 weights must sum to 100, got ${weightTotal}`);
  if (accordV2.blocks?.private_bank_handoff?.predictive_status !== 'STOP_RESEARCH_DIAGNOSTIC') {
    throw new Error('Closed Fed→Bank predictive status was reopened');
  }
  if (!Array.isArray(accordV2.history) || accordV2.history.length < 12) {
    throw new Error('Accord Watch v2 trend history is insufficient');
  }

  const historyPayload = {
    schema_version: 'gmli-accord-watch-history-v1',
    version: accordV2.version,
    generated_at: accordV2.generated_at,
    evidence_tier: 'RESEARCH_DIAGNOSTIC',
    scoring_effect: 'NONE',
    automatic_weight_change: 0,
    methodology_effect: 'NONE',
    presentation_score: true,
    history: accordV2.history,
    guardrail: 'Historical presentation gauge only; not a probability, GMLI conviction history or asset-return model.'
  };

  await fs.mkdir(API, { recursive: true });
  await fs.writeFile(path.join(API, 'liquidity-context.json'), JSON.stringify(context, null, 2) + '\n');
  await fs.writeFile(path.join(API, 'accord-watch.json'), JSON.stringify(accordV1, null, 2) + '\n');
  await fs.writeFile(path.join(API, 'accord-watch-v2.json'), JSON.stringify(accordV2, null, 2) + '\n');
  await fs.writeFile(path.join(API, 'accord-watch-history.json'), JSON.stringify(historyPayload, null, 2) + '\n');

  const htmlPath = path.join(PAGES, 'index.html');
  const html = await fs.readFile(htmlPath, 'utf8');
  const enhanced = enhanceAccordGuideV2(enhanceAccordWatchV2(enhanceLiquidityGuide(enhanceLiquidityContext(html, context)), accordV2));
  if (!enhanced.includes('id="liquidityContext"') || !enhanced.includes('liquidity-context.json')) {
    throw new Error('Liquidity context UI integration failed');
  }
  if (!enhanced.includes('id="liquidityContextGuide"') || !enhanced.includes('Bank balance-sheet impulse — izračun i rezultati') || !enhanced.includes('Treasury duration mix — izračun i rezultati')) {
    throw new Error('Liquidity context investor guide integration failed');
  }
  if (enhanced.includes('id="bankImpulseDirection">Loading') || enhanced.includes('Loading liquidity context')) {
    throw new Error('Liquidity context must be statically rendered in the published snapshot');
  }
  if (!enhanced.includes('id="accordWatchV2"') || !enhanced.includes('accord-watch-v2.json') || !enhanced.includes('accord-watch-history.json') || !enhanced.includes('id="accordWatchGuideV2"')) {
    throw new Error('Accord Watch v2 static integration failed');
  }
  if (!enhanced.includes('0–100 CLOSENESS GAUGE') || !enhanced.includes('Private bank handoff')) {
    throw new Error('Accord Watch v2 simplified gauge content missing');
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
    accord_watch_v1_version: accordV1.version,
    accord_watch_v2_version: accordV2.version,
    accord_watch_v2_score: accordV2.score,
    accord_watch_v2_band: accordV2.band,
    accord_watch_v2_trend_1m: accordV2.trend?.delta_1m_points,
    accord_watch_v2_trend_3m: accordV2.trend?.delta_3m_points,
    accord_watch_v2_market_conflict: accordV2.market_conflict,
    accord_watch_v2_scoring_effect: accordV2.scoring_effect,
    accord_watch_v2_automatic_weight_change: accordV2.automatic_weight_change,
    accord_watch_v2_history_rows: accordV2.history.length,
    accord_watch_handoff_predictive_status: accordV2.blocks?.private_bank_handoff?.predictive_status,
    pages_accord_watch_v2_ui: true,
    pages_accord_watch_v2_guide: true
  }, null, 2));
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
