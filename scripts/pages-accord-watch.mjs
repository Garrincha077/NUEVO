import { buildLiquidityContext } from './pages-liquidity-context.mjs';

const H41_TOTAL_ASSETS_URL = 'https://www.federalreserve.gov/datadownload/Output.aspx?filetype=csv&from=&label=include&lastobs=&layout=seriescolumn&rel=H41&series=17398fbf71bc6a47df150bceebdea2bc&to=&type=package';
const H41_TABLE1_URL = 'https://www.federalreserve.gov/datadownload/Output.aspx?filetype=csv&from=&label=include&lastobs=&layout=seriescolumn&rel=H41&series=bf254044496631c2a1c54617dd265a95&to=&type=package';
const TREASURY_REAL_YIELD_BASE = 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_real_yield_curve&field_tdr_date_value=';
const FED_TERM_PREMIUM_URL = 'https://www.federalreserve.gov/data/yield-curve-tables/feds200533.csv';

const round = (value, digits = 2) => Number.isFinite(value) ? Number(value.toFixed(digits)) : null;

async function fetchText(url, timeoutMs = 20000) {
  const res = await fetch(url, {
    headers: { 'user-agent': 'GMLI-accord-watch/1.0' },
    signal: AbortSignal.timeout(timeoutMs)
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return res.text();
}

function parseCsvRow(line) {
  const out = [];
  let cur = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') {
        cur += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (ch === ',' && !quoted) {
      out.push(cur);
      cur = '';
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out.map(x => x.trim());
}

function parseDate(raw) {
  const x = String(raw || '').trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(x)) return x.slice(0, 10);
  const m = x.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (m) return `${m[3]}-${m[1].padStart(2, '0')}-${m[2].padStart(2, '0')}`;
  return null;
}

function dateMinusDays(date, days) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

function nearestOnOrBefore(rows, targetDate) {
  let best = null;
  for (const row of rows) {
    if (row.date <= targetDate && (!best || row.date > best.date)) best = row;
  }
  return best;
}

function pctChange(current, prior) {
  if (!Number.isFinite(current) || !Number.isFinite(prior) || prior === 0) return null;
  return (current / prior - 1) * 100;
}

async function buildTreasurySupplyBlock() {
  try {
    const context = await buildLiquidityContext();
    const t = context.treasury_duration_mix || {};
    if (t.status !== 'AVAILABLE') throw new Error(t.error || 'Treasury duration mix unavailable');
    const latest = t.latest || {};
    const fixedLatest = Number(latest.fixed_duration_share_pct);
    const shortDelta = Number(t.short_or_floating_share_change_3m_pp);
    if (!Number.isFinite(fixedLatest) || !Number.isFinite(shortDelta)) throw new Error('Treasury duration mix missing values');
    const fixedDelta = -shortDelta;
    const direction = fixedDelta < 0 ? 'SUPPORTIVE' : fixedDelta > 0 ? 'RESTRICTIVE' : 'NEUTRAL';
    return {
      status: 'AVAILABLE',
      label: 'Treasury duration-supply pressure proxy',
      source: t.source,
      latest_date: t.latest_date,
      comparison_date: t.comparison_date,
      fixed_duration_share_pct: fixedLatest,
      fixed_duration_share_change_3m_pp: round(fixedDelta),
      short_or_floating_share_pct: Number(latest.short_or_floating_share_pct),
      direction,
      interpretation: 'Stock-change composition proxy only. Falling fixed-duration share is supportive for lower private duration pressure; this is not true net issuance, DV01, WAM or buyback flow.'
    };
  } catch (error) {
    return {
      status: 'UNAVAILABLE',
      label: 'Treasury duration-supply pressure proxy',
      direction: 'UNAVAILABLE',
      error: String(error?.message || error),
      interpretation: 'Source failure cannot create Accord support.'
    };
  }
}

function parseH41Series(csv, wanted) {
  const lines = csv.split(/\r?\n/).filter(Boolean);
  const rows = lines.map(parseCsvRow);
  const headerIndex = rows.findIndex(row => String(row[0] || '').trim().toLowerCase() === 'time period');
  if (headerIndex < 0) throw new Error('H.4.1 header not found');
  const header = rows[headerIndex].map(x => String(x).trim().replace(/^H41\/H41\//, ''));
  const idx = header.findIndex(x => x === wanted || x.endsWith(`/${wanted}`));
  if (idx < 0) throw new Error(`H.4.1 series ${wanted} not found`);
  const out = [];
  for (const row of rows.slice(headerIndex + 1)) {
    const date = parseDate(row[0]);
    const value = Number(row[idx]);
    if (date && Number.isFinite(value)) out.push({ date, value });
  }
  out.sort((a, b) => a.date.localeCompare(b.date));
  if (out.length < 100) throw new Error(`Insufficient H.4.1 history for ${wanted}: ${out.length}`);
  return out;
}

async function buildFedReserveBlock() {
  try {
    const [assetsCsv, reservesCsv] = await Promise.all([
      fetchText(H41_TOTAL_ASSETS_URL, 30000),
      fetchText(H41_TABLE1_URL, 30000)
    ]);
    const assets = parseH41Series(assetsCsv, 'RESPPA_N.WW');
    const reserves = parseH41Series(reservesCsv, 'RESH4R_N.WW');
    const latestDate = [assets.at(-1)?.date, reserves.at(-1)?.date].filter(Boolean).sort().at(0);
    if (!latestDate) throw new Error('No aligned H.4.1 latest date');
    const target = dateMinusDays(latestDate, 91);
    const a0 = nearestOnOrBefore(assets, latestDate);
    const a1 = nearestOnOrBefore(assets, target);
    const r0 = nearestOnOrBefore(reserves, latestDate);
    const r1 = nearestOnOrBefore(reserves, target);
    if (!a0 || !a1 || !r0 || !r1) throw new Error('Could not resolve H.4.1 13W comparisons');
    const asset13w = pctChange(a0.value, a1.value);
    const reserve13w = pctChange(r0.value, r1.value);
    if (!Number.isFinite(asset13w) || !Number.isFinite(reserve13w)) throw new Error('Invalid H.4.1 13W changes');

    let direction;
    if (asset13w >= 0 && reserve13w >= 0) direction = 'SUPPORTIVE';
    else if (asset13w < 0 && reserve13w >= 0) direction = 'RESERVE_CUSHION';
    else if (asset13w >= 0 && reserve13w < 0) direction = 'MIXED';
    else direction = 'RESTRICTIVE';

    return {
      status: 'AVAILABLE',
      label: 'Fed / reserve support',
      source: 'Federal Reserve H.4.1 Data Download Program',
      total_assets_series: 'RESPPA_N.WW',
      reserve_balances_series: 'RESH4R_N.WW',
      latest_date: latestDate,
      total_assets_13w_pct: round(asset13w),
      reserve_balances_13w_pct: round(reserve13w),
      total_assets_latest_mil: round(a0.value, 0),
      reserve_balances_latest_mil: round(r0.value, 0),
      direction,
      supportive_for_state: direction === 'SUPPORTIVE' || direction === 'RESERVE_CUSHION',
      interpretation: 'SUPPORTIVE requires non-shrinking Fed assets and reserves. RESERVE_CUSHION allows Fed assets to shrink while reserve balances are non-shrinking.'
    };
  } catch (error) {
    return {
      status: 'UNAVAILABLE',
      label: 'Fed / reserve support',
      direction: 'UNAVAILABLE',
      supportive_for_state: false,
      error: String(error?.message || error),
      interpretation: 'Source failure cannot create Accord support.'
    };
  }
}

function parseRealYieldXml(xml) {
  const entries = xml.match(/<entry[\s\S]*?<\/entry>/gi) || [];
  const out = [];
  for (const entry of entries) {
    const dm = entry.match(/<d:NEW_DATE[^>]*>([^<]+)<\/d:NEW_DATE>/i);
    const vm = entry.match(/<d:TC_10YEAR[^>]*>([^<]+)<\/d:TC_10YEAR>/i);
    const date = parseDate(dm?.[1]);
    const value = Number(vm?.[1]);
    if (date && Number.isFinite(value)) out.push({ date, value });
  }
  return out;
}

async function fetchRealYieldRows() {
  const year = new Date().getUTCFullYear();
  const [current, prior] = await Promise.all([
    fetchText(`${TREASURY_REAL_YIELD_BASE}${year}`),
    fetchText(`${TREASURY_REAL_YIELD_BASE}${year - 1}`)
  ]);
  const rows = [...parseRealYieldXml(prior), ...parseRealYieldXml(current)]
    .sort((a, b) => a.date.localeCompare(b.date));
  if (rows.length < 50) throw new Error(`Insufficient Treasury real-yield history: ${rows.length}`);
  return rows;
}

function parseTermPremiumCsv(csv) {
  const rows = csv.split(/\r?\n/).filter(Boolean).map(parseCsvRow);
  const candidates = ['THREEFYTP1000.B', 'THREEFYTP10', 'TP10'];
  const headerIndex = rows.findIndex(row => row.some(x => candidates.includes(String(x).trim().toUpperCase())));
  if (headerIndex < 0) throw new Error('10Y term-premium column not found in Fed CSV');
  const header = rows[headerIndex].map(x => String(x).trim().toUpperCase());
  const tpIdx = candidates.map(x => header.indexOf(x)).find(x => x >= 0);
  const dateIdx = header.indexOf('DATE');
  if (tpIdx == null || tpIdx < 0 || dateIdx < 0) throw new Error('Fed term-premium date/value columns unresolved');
  const out = [];
  for (const row of rows.slice(headerIndex + 1)) {
    const date = parseDate(row[dateIdx]);
    const value = Number(row[tpIdx]);
    if (date && Number.isFinite(value)) out.push({ date, value });
  }
  out.sort((a, b) => a.date.localeCompare(b.date));
  if (out.length < 100) throw new Error(`Insufficient 10Y term-premium history: ${out.length}`);
  return out;
}

async function buildMarketVerdictBlock() {
  try {
    const [realRows, termCsv] = await Promise.all([
      fetchRealYieldRows(),
      fetchText(FED_TERM_PREMIUM_URL, 30000)
    ]);
    const termRows = parseTermPremiumCsv(termCsv);
    const latestDate = [realRows.at(-1)?.date, termRows.at(-1)?.date].filter(Boolean).sort().at(0);
    if (!latestDate) throw new Error('No market-verdict latest date');
    const target = dateMinusDays(latestDate, 91);
    const real0 = nearestOnOrBefore(realRows, latestDate);
    const real1 = nearestOnOrBefore(realRows, target);
    const term0 = nearestOnOrBefore(termRows, latestDate);
    const term1 = nearestOnOrBefore(termRows, target);
    if (!real0 || !real1 || !term0 || !term1) throw new Error('Could not resolve 3M yield comparisons');
    const realChange = real0.value - real1.value;
    const termChange = term0.value - term1.value;
    let direction;
    if (realChange <= 0 && termChange <= 0) direction = 'CONFIRM';
    else if (realChange > 0 && termChange > 0) direction = 'REJECT';
    else direction = 'MIXED';
    return {
      status: 'AVAILABLE',
      label: 'Market yield-suppression verdict',
      latest_date: latestDate,
      treasury_real_yield_source: 'U.S. Treasury Daily Treasury Par Real Yield Curve Rates',
      term_premium_source: 'Federal Reserve Board three-factor nominal term-structure model (staff research product)',
      term_premium_series: 'THREEFYTP1000.B',
      real_yield_10y_pct: round(real0.value),
      real_yield_10y_change_3m_pp: round(realChange),
      term_premium_10y_pct: round(term0.value),
      term_premium_10y_change_3m_pp: round(termChange),
      direction,
      interpretation: 'CONFIRM requires both 10Y real yield and 10Y term premium to be non-rising over approximately 3 months. REJECT requires both to rise.'
    };
  } catch (error) {
    return {
      status: 'UNAVAILABLE',
      label: 'Market yield-suppression verdict',
      direction: 'UNAVAILABLE',
      error: String(error?.message || error),
      interpretation: 'Missing market evidence prevents EMERGING or REPRESSION classification.'
    };
  }
}

function buildAssetMap(state, treasury, fed, market) {
  const emerging = state === 'EMERGING' || state === 'REPRESSION';
  const repression = state === 'REPRESSION';
  const setup = state === 'SETUP';
  const marketConfirm = market.direction === 'CONFIRM';
  const durationSupport = emerging ? 'STRONG' : setup && marketConfirm ? 'MODERATE' : setup ? 'WATCH' : 'NONE';
  const realBondValue = market.status !== 'AVAILABLE' || !Number.isFinite(market.real_yield_10y_pct)
    ? 'UNAVAILABLE'
    : market.real_yield_10y_pct < 0 ? 'NEGATIVE_REAL_YIELD'
      : market.real_yield_10y_pct > 0 ? 'POSITIVE_REAL_YIELD' : 'ZERO_REAL_YIELD';

  return {
    bond_read: {
      duration_price_support: durationSupport,
      real_bond_value: realBondValue,
      note: 'Tactical nominal-bond price support and structural real bond value are intentionally separate.'
    },
    assets: {
      GLD: repression ? 'STRONGLY_POSITIVE' : emerging ? 'POSITIVE' : setup ? 'WATCH_POSITIVE' : 'NO_ACCORD_TILT',
      TIPS: repression ? 'STRONGLY_POSITIVE' : emerging ? 'POSITIVE' : setup ? 'WATCH_POSITIVE' : 'NO_ACCORD_TILT',
      'UST_2_5Y': emerging ? 'POSITIVE' : setup ? 'WATCH_POSITIVE' : 'NO_ACCORD_TILT',
      'UST_10_30Y': emerging ? 'TACTICALLY_POSITIVE_REAL_VALUE_CONDITIONAL' : setup ? 'WATCH' : 'NO_ACCORD_TILT',
      QQQ: emerging ? 'POSITIVE_REAL_YIELD_SENSITIVE' : setup ? 'WATCH_POSITIVE' : 'NO_ACCORD_TILT',
      SPY: emerging ? 'MODERATELY_POSITIVE' : setup ? 'WATCH' : 'NO_ACCORD_TILT',
      BTC: repression ? 'RESEARCH_STRONGLY_POSITIVE' : emerging ? 'RESEARCH_POSITIVE' : setup ? 'RESEARCH_WATCH' : 'NO_ACCORD_TILT',
      DBC: emerging ? 'CONDITIONAL_REFLATION_REQUIRED' : 'NO_ACCORD_TILT',
      USD: repression ? 'CONDITIONAL_NEGATIVE' : emerging ? 'WATCH_NEGATIVE' : 'NO_ACCORD_TILT'
    },
    interpretation_only: true,
    promoted_money_transmission_unchanged: ['SPY', 'QQQ', 'GLD', 'DBC'],
    inputs: {
      treasury_direction: treasury.direction,
      fed_reserve_direction: fed.direction,
      market_direction: market.direction
    }
  };
}

export async function buildAccordWatch() {
  const [treasury, fed, market] = await Promise.all([
    buildTreasurySupplyBlock(),
    buildFedReserveBlock(),
    buildMarketVerdictBlock()
  ]);

  const treasurySupportive = treasury.status === 'AVAILABLE' && treasury.direction === 'SUPPORTIVE';
  const fedSupportive = fed.status === 'AVAILABLE' && fed.supportive_for_state === true;
  const marketConfirm = market.status === 'AVAILABLE' && market.direction === 'CONFIRM';
  const dataComplete = treasury.status === 'AVAILABLE' && fed.status === 'AVAILABLE' && market.status === 'AVAILABLE';

  let state = 'HYPOTHESIS_ONLY';
  if (treasurySupportive || fedSupportive) state = 'SETUP';
  if (dataComplete && treasurySupportive && fedSupportive && marketConfirm) state = 'EMERGING';
  if (state === 'EMERGING' && Number.isFinite(market.real_yield_10y_pct) && market.real_yield_10y_pct < 0) state = 'REPRESSION';

  const marketConflict = market.status === 'AVAILABLE' && market.direction === 'REJECT';
  const assetMap = buildAssetMap(state, treasury, fed, market);

  return {
    schema_version: 'gmli-accord-watch-v1',
    version: 'GMLI_ACCORD_WATCH_V1',
    generated_at: new Date().toISOString(),
    evidence_tier: 'RESEARCH_DIAGNOSTIC',
    scoring_effect: 'NONE',
    automatic_weight_change: 0,
    methodology_effect: 'NONE',
    state,
    hypothesis: 'Treasury–Fed Accord 2.0 / financial-repression setup is a scenario to monitor, not an assumed current regime.',
    data_complete: dataComplete,
    market_conflict: marketConflict,
    blocks: {
      treasury_duration_supply: treasury,
      fed_reserve_support: fed,
      market_yield_suppression: market
    },
    asset_map: assetMap,
    guardrail: 'Research diagnostic only. No GMLI score, conviction points, automatic allocation weights or CORE/OVERLAY promotion. Treasury block is a stock-change proxy, not true issuance flow.'
  };
}

export function accordWatchHtml(accord) {
  const esc = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
  const signed = value => value == null || !Number.isFinite(Number(value)) ? 'n/a' : `${Number(value) > 0 ? '+' : ''}${Number(value).toFixed(2)}`;
  const a = accord || {};
  const t = a.blocks?.treasury_duration_supply || {};
  const f = a.blocks?.fed_reserve_support || {};
  const m = a.blocks?.market_yield_suppression || {};
  const b = a.asset_map?.bond_read || {};
  const stateClass = a.state === 'EMERGING' || a.state === 'REPRESSION' ? 'good' : a.state === 'SETUP' ? 'neutral' : 'wait';
  const best = Object.entries(a.asset_map?.assets || {}).filter(([, v]) => /POSITIVE/.test(v) && !/CONDITIONAL/.test(v)).map(([k]) => k).slice(0, 5).join(', ') || 'none from Accord Watch';
  return `<div id="accordWatch" class="card" style="grid-column:1/-1"><div class="tag">ACCORD WATCH v1 · HYPOTHESIS TRACKER</div><div class="score ${stateClass}">${esc(a.state || 'UNAVAILABLE')}</div><div class="marketMeta"><b>Treasury duration supply:</b> ${esc(t.direction || 'UNAVAILABLE')} · fixed-duration 3M ${esc(signed(t.fixed_duration_share_change_3m_pp))} pp<br><b>Fed / reserves:</b> ${esc(f.direction || 'UNAVAILABLE')} · Fed assets 13W ${esc(signed(f.total_assets_13w_pct))}% · reserves 13W ${esc(signed(f.reserve_balances_13w_pct))}%<br><b>Market verdict:</b> ${esc(m.direction || 'UNAVAILABLE')} · 10Y real yield ${esc(m.real_yield_10y_pct == null ? 'n/a' : `${Number(m.real_yield_10y_pct).toFixed(2)}%`)} (${esc(signed(m.real_yield_10y_change_3m_pp))} pp/3M) · term premium ${esc(m.term_premium_10y_pct == null ? 'n/a' : `${Number(m.term_premium_10y_pct).toFixed(2)}%`)} (${esc(signed(m.term_premium_10y_change_3m_pp))} pp/3M)<br><b>Bonds:</b> duration price support ${esc(b.duration_price_support || 'UNAVAILABLE')} · ${esc(b.real_bond_value || 'UNAVAILABLE')}<br><b>Scenario beneficiaries now:</b> ${esc(best)}</div><div class="small muted" style="margin-top:8px">RESEARCH_DIAGNOSTIC · weight 0 · no conviction points · <a href="./api/accord-watch.json">accord-watch.json</a></div></div>`;
}
