const H41_TOTAL_ASSETS_URL = 'https://www.federalreserve.gov/datadownload/Output.aspx?filetype=csv&from=&label=include&lastobs=&layout=seriescolumn&rel=H41&series=17398fbf71bc6a47df150bceebdea2bc&to=&type=package';
const H41_TABLE1_URL = 'https://www.federalreserve.gov/datadownload/Output.aspx?filetype=csv&from=&label=include&lastobs=&layout=seriescolumn&rel=H41&series=bf254044496631c2a1c54617dd265a95&to=&type=package';
const FRED_BANK_ASSETS_URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=TLAACBW027SBOG';
const TREASURY_MSPD_BASE = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/debt/mspd/mspd_table_1';
const TREASURY_REAL_YIELD_BASE = 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_real_yield_curve&field_tdr_date_value=';
const FED_TERM_PREMIUM_URL = 'https://www.federalreserve.gov/data/yield-curve-tables/feds200533.csv';

const round = (value, digits = 2) => Number.isFinite(value) ? Number(value.toFixed(digits)) : null;

async function fetchText(url, timeoutMs = 30000) {
  const res = await fetch(url, {
    headers: { 'user-agent': 'GMLI-accord-watch-v2/1.0' },
    signal: AbortSignal.timeout(timeoutMs)
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return res.text();
}

async function fetchJson(url, timeoutMs = 30000) {
  const res = await fetch(url, {
    headers: { 'user-agent': 'GMLI-accord-watch-v2/1.0' },
    signal: AbortSignal.timeout(timeoutMs)
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return res.json();
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

function dateMinusMonths(date, months) {
  const d = new Date(`${date}T00:00:00Z`);
  const day = d.getUTCDate();
  d.setUTCDate(1);
  d.setUTCMonth(d.getUTCMonth() - months);
  const lastDay = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
  d.setUTCDate(Math.min(day, lastDay));
  return d.toISOString().slice(0, 10);
}

function monthEnd(date) {
  const d = new Date(`${date}T00:00:00Z`);
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).toISOString().slice(0, 10);
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

function parseH41Series(csv, wanted) {
  const rows = csv.split(/\r?\n/).filter(Boolean).map(parseCsvRow);
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

function parseFredSeries(csv) {
  const lines = csv.trim().split(/\r?\n/);
  const rows = lines.slice(1).map(line => {
    const [date, raw] = line.split(',');
    return { date, value: Number(raw) };
  }).filter(x => /^\d{4}-\d{2}-\d{2}$/.test(x.date) && Number.isFinite(x.value));
  rows.sort((a, b) => a.date.localeCompare(b.date));
  if (rows.length < 100) throw new Error(`Insufficient FRED history: ${rows.length}`);
  return rows;
}

function treasuryClassKey(label) {
  const x = String(label || '').trim().toLowerCase();
  if (x === 'bills' || x.startsWith('treasury bills')) return 'bills';
  if (x === 'notes' || x.startsWith('treasury notes')) return 'notes';
  if (x === 'bonds' || x.startsWith('treasury bonds')) return 'bonds';
  if (x.includes('inflation-protected')) return 'tips';
  if (x.includes('floating rate')) return 'frns';
  return null;
}

function summarizeTreasury(rows, date) {
  const values = { bills: 0, notes: 0, bonds: 0, tips: 0, frns: 0 };
  for (const row of rows) {
    if (row.record_date !== date) continue;
    const key = treasuryClassKey(row.security_class_desc);
    const value = Number(row.debt_held_public_mil_amt);
    if (key && Number.isFinite(value)) values[key] += value;
  }
  const marketable = Object.values(values).reduce((a, b) => a + b, 0);
  if (!(marketable > 0)) return null;
  const shortFloating = values.bills + values.frns;
  const fixedDuration = values.notes + values.bonds + values.tips;
  return {
    date,
    values,
    marketable_mil: marketable,
    short_floating_mil: shortFloating,
    fixed_duration_mil: fixedDuration,
    short_or_floating_share_pct: shortFloating / marketable * 100,
    fixed_duration_share_pct: fixedDuration / marketable * 100
  };
}

async function fetchTreasuryRows() {
  const common = 'fields=record_date,security_type_desc,security_class_desc,debt_held_public_mil_amt&sort=-record_date&format=json&page%5Bnumber%5D=1&page%5Bsize%5D=1000';
  const urls = [
    `${TREASURY_MSPD_BASE}?${common}&filter=security_type_desc:eq:Marketable`,
    `${TREASURY_MSPD_BASE}?${common}`
  ];
  let lastError;
  for (const url of urls) {
    try {
      const payload = await fetchJson(url);
      const rows = Array.isArray(payload?.data) ? payload.data : [];
      const usable = rows.filter(row => String(row.security_type_desc || '').trim().toLowerCase() === 'marketable' && treasuryClassKey(row.security_class_desc));
      if (usable.length) return usable;
      lastError = new Error(`No usable MSPD marketable rows from ${url}`);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error('MSPD unavailable');
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
  const years = [year - 2, year - 1, year];
  const payloads = await Promise.all(years.map(y => fetchText(`${TREASURY_REAL_YIELD_BASE}${y}`)));
  const rows = payloads.flatMap(parseRealYieldXml).sort((a, b) => a.date.localeCompare(b.date));
  if (rows.length < 200) throw new Error(`Insufficient Treasury real-yield history: ${rows.length}`);
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

function treasuryBlock(raw, cutoffDate) {
  try {
    const dates = [...new Set(raw.treasuryRows.map(x => x.record_date).filter(date => date && date <= cutoffDate))].sort();
    if (dates.length < 4) throw new Error('Insufficient MSPD dates for v2 Treasury block');
    const latestDate = dates.at(-1);
    const previousDate = dates.at(-2);
    const threeMonthTarget = dateMinusMonths(latestDate, 3);
    const prior3mDate = [...dates].reverse().find(date => date <= threeMonthTarget);
    if (!prior3mDate) throw new Error('No MSPD 3M comparison date');
    const latest = summarizeTreasury(raw.treasuryRows, latestDate);
    const previous = summarizeTreasury(raw.treasuryRows, previousDate);
    const prior3m = summarizeTreasury(raw.treasuryRows, prior3mDate);
    if (!latest || !previous || !prior3m) throw new Error('Could not summarize MSPD rows');

    const fixedShareChange = latest.fixed_duration_share_pct - prior3m.fixed_duration_share_pct;
    const shortNetMil = latest.short_floating_mil - previous.short_floating_mil;
    const fixedNetMil = latest.fixed_duration_mil - previous.fixed_duration_mil;
    const compositionSupportive = fixedShareChange < 0;
    const flowSupportive = shortNetMil >= fixedNetMil;
    const compositionPoints = compositionSupportive ? 12.5 : 0;
    const flowPoints = flowSupportive ? 12.5 : 0;

    return {
      status: 'AVAILABLE',
      source: 'U.S. Treasury Fiscal Data — MSPD Table 1',
      latest_date: latestDate,
      comparison_3m_date: prior3mDate,
      previous_month_date: previousDate,
      fixed_duration_share_pct: round(latest.fixed_duration_share_pct),
      fixed_duration_share_change_3m_pp: round(fixedShareChange),
      short_or_floating_share_pct: round(latest.short_or_floating_share_pct),
      short_floating_net_change_bn: round(shortNetMil / 1000, 1),
      fixed_duration_net_change_bn: round(fixedNetMil / 1000, 1),
      composition_supportive: compositionSupportive,
      flow_supportive: flowSupportive,
      composition_points: compositionPoints,
      flow_points: flowPoints,
      points: compositionPoints + flowPoints,
      max_points: 25,
      direction: compositionSupportive && flowSupportive ? 'SUPPORTIVE' : compositionSupportive || flowSupportive ? 'MIXED_SUPPORT' : 'RESTRICTIVE',
      interpretation: 'Treasury v2 combines the frozen V1 3M composition check with a monthly net-outstanding-change supply proxy. The flow proxy is not auction-level DV01/WAM/buyback accounting.'
    };
  } catch (error) {
    return {
      status: 'UNAVAILABLE',
      direction: 'UNAVAILABLE',
      points: 0,
      max_points: 25,
      error: String(error?.message || error),
      interpretation: 'Missing Treasury evidence contributes zero gauge points.'
    };
  }
}

function fedReserveBlock(raw, cutoffDate) {
  try {
    const a0 = nearestOnOrBefore(raw.fedAssets, cutoffDate);
    const r0 = nearestOnOrBefore(raw.reserves, cutoffDate);
    if (!a0 || !r0) throw new Error('No current H.4.1 row');
    const latestDate = a0.date < r0.date ? a0.date : r0.date;
    const priorTarget = dateMinusDays(latestDate, 91);
    const a1 = nearestOnOrBefore(raw.fedAssets, priorTarget);
    const r1 = nearestOnOrBefore(raw.reserves, priorTarget);
    const a = nearestOnOrBefore(raw.fedAssets, latestDate);
    const r = nearestOnOrBefore(raw.reserves, latestDate);
    if (!a1 || !r1 || !a || !r) throw new Error('Missing H.4.1 13W comparison');
    const asset13w = pctChange(a.value, a1.value);
    const reserve13w = pctChange(r.value, r1.value);
    if (!Number.isFinite(asset13w) || !Number.isFinite(reserve13w)) throw new Error('Invalid H.4.1 change');

    let direction;
    let points;
    if (asset13w >= 0 && reserve13w >= 0) { direction = 'SUPPORTIVE'; points = 25; }
    else if (asset13w < 0 && reserve13w >= 0) { direction = 'RESERVE_CUSHION'; points = 20; }
    else if (asset13w >= 0 && reserve13w < 0) { direction = 'MIXED'; points = 10; }
    else { direction = 'RESTRICTIVE'; points = 0; }

    return {
      status: 'AVAILABLE',
      source: 'Federal Reserve H.4.1 Data Download Program',
      latest_date: latestDate,
      total_assets_13w_pct: round(asset13w),
      reserve_balances_13w_pct: round(reserve13w),
      total_assets_latest_mil: round(a.value, 0),
      reserve_balances_latest_mil: round(r.value, 0),
      direction,
      points,
      max_points: 25,
      interpretation: 'Frozen V1 13W Fed-assets / reserve-balance state, mapped to transparent v2 presentation points.'
    };
  } catch (error) {
    return {
      status: 'UNAVAILABLE', direction: 'UNAVAILABLE', points: 0, max_points: 25,
      error: String(error?.message || error),
      interpretation: 'Missing Fed/reserve evidence contributes zero gauge points.'
    };
  }
}

function handoffBlock(raw, fedBlock, cutoffDate) {
  try {
    if (fedBlock.status !== 'AVAILABLE') throw new Error('Fed block unavailable');
    const b0 = nearestOnOrBefore(raw.bankAssets, cutoffDate);
    if (!b0) throw new Error('No H.8 bank-assets row');
    const b1 = nearestOnOrBefore(raw.bankAssets, dateMinusDays(b0.date, 91));
    if (!b1) throw new Error('No H.8 13W comparison row');
    const bank13w = pctChange(b0.value, b1.value);
    const fed13w = Number(fedBlock.total_assets_13w_pct);
    if (!Number.isFinite(bank13w) || !Number.isFinite(fed13w)) throw new Error('Invalid handoff changes');

    let state;
    let points;
    if (fed13w < 0 && bank13w > 0) { state = 'PRIVATE_HANDOFF'; points = 25; }
    else if (fed13w >= 0 && bank13w > 0) { state = 'BROAD_EASING'; points = 15; }
    else if (fed13w >= 0 && bank13w <= 0) { state = 'FED_OFFSET'; points = 5; }
    else { state = 'TRUE_TIGHTENING'; points = 0; }

    return {
      status: 'AVAILABLE',
      source: 'Federal Reserve H.4.1 + H.8 via FRED',
      latest_date: b0.date < fedBlock.latest_date ? b0.date : fedBlock.latest_date,
      fed_total_assets_13w_pct: round(fed13w),
      bank_total_assets_13w_pct: round(bank13w),
      state,
      points,
      max_points: 25,
      predictive_status: 'STOP_RESEARCH_DIAGNOSTIC',
      interpretation: 'Descriptive reuse only. The frozen predictive family gate failed and is not reopened or retuned.'
    };
  } catch (error) {
    return {
      status: 'UNAVAILABLE', state: 'UNAVAILABLE', points: 0, max_points: 25,
      predictive_status: 'STOP_RESEARCH_DIAGNOSTIC',
      error: String(error?.message || error),
      interpretation: 'Missing handoff evidence contributes zero gauge points; no predictive rescue search is allowed.'
    };
  }
}

function marketBlock(raw, cutoffDate) {
  try {
    const real0 = nearestOnOrBefore(raw.realYields, cutoffDate);
    const term0 = nearestOnOrBefore(raw.termPremium, cutoffDate);
    if (!real0 || !term0) throw new Error('No current market rows');
    const latestDate = real0.date < term0.date ? real0.date : term0.date;
    const target = dateMinusDays(latestDate, 91);
    const real = nearestOnOrBefore(raw.realYields, latestDate);
    const term = nearestOnOrBefore(raw.termPremium, latestDate);
    const real1 = nearestOnOrBefore(raw.realYields, target);
    const term1 = nearestOnOrBefore(raw.termPremium, target);
    if (!real || !term || !real1 || !term1) throw new Error('Missing 3M market comparison');
    const realChange = real.value - real1.value;
    const termChange = term.value - term1.value;

    let direction;
    let points;
    if (realChange <= 0 && termChange <= 0) { direction = 'CONFIRM'; points = 25; }
    else if (realChange > 0 && termChange > 0) { direction = 'REJECT'; points = 0; }
    else { direction = 'MIXED'; points = 12.5; }

    return {
      status: 'AVAILABLE',
      latest_date: latestDate,
      treasury_real_yield_source: 'U.S. Treasury Daily Treasury Par Real Yield Curve Rates',
      term_premium_source: 'Federal Reserve Board three-factor nominal term-structure model (staff research product)',
      real_yield_10y_pct: round(real.value),
      real_yield_10y_change_3m_pp: round(realChange),
      term_premium_10y_pct: round(term.value),
      term_premium_10y_change_3m_pp: round(termChange),
      direction,
      points,
      max_points: 25,
      interpretation: 'Frozen V1 market verdict mapped to v2 presentation points. REJECT remains an explicit conflict.'
    };
  } catch (error) {
    return {
      status: 'UNAVAILABLE', direction: 'UNAVAILABLE', points: 0, max_points: 25,
      error: String(error?.message || error),
      interpretation: 'Missing market evidence contributes zero gauge points.'
    };
  }
}

function bandForScore(score) {
  if (score >= 85) return 'ACCORD_LIKE';
  if (score >= 70) return 'EMERGING';
  if (score >= 50) return 'DEVELOPING';
  if (score >= 25) return 'SETUP';
  return 'DISTANT';
}

function buildAssetMap(score, treasury, fed, market) {
  const band = bandForScore(score);
  const high = score >= 70;
  const mid = score >= 50;
  const setup = score >= 25;
  const marketConfirm = market.direction === 'CONFIRM';
  const marketReject = market.direction === 'REJECT';
  const durationSupport = marketConfirm && treasury.points >= 12.5
    ? (high ? 'STRONG' : 'MODERATE')
    : setup ? 'WATCH' : 'NONE';
  const realBondValue = market.status !== 'AVAILABLE' || !Number.isFinite(market.real_yield_10y_pct)
    ? 'UNAVAILABLE'
    : market.real_yield_10y_pct < 0 ? 'NEGATIVE_REAL_YIELD'
      : market.real_yield_10y_pct > 0 ? 'POSITIVE_REAL_YIELD' : 'ZERO_REAL_YIELD';

  return {
    band,
    bond_read: {
      duration_price_support: durationSupport,
      real_bond_value: realBondValue,
      long_duration_warning: marketReject ? 'YIELD_PRESSURE_NOT_CONFIRMING' : null,
      note: 'Tactical nominal-bond price support and structural real bond value stay separate.'
    },
    assets: {
      GLD: score >= 85 ? 'STRONGLY_POSITIVE' : high ? 'POSITIVE' : mid ? 'WATCH_POSITIVE' : 'NO_ACCORD_TILT',
      TIPS: score >= 85 ? 'STRONGLY_POSITIVE' : high ? 'POSITIVE' : mid ? 'WATCH_POSITIVE' : 'NO_ACCORD_TILT',
      'UST_2_5Y': fed.points >= 20 && !marketReject ? 'POSITIVE' : setup ? 'WATCH' : 'NO_ACCORD_TILT',
      'UST_10_30Y': marketConfirm && treasury.points >= 12.5 ? 'TACTICALLY_POSITIVE' : marketReject ? 'CAUTION_YIELD_PRESSURE' : setup ? 'WATCH' : 'NO_ACCORD_TILT',
      QQQ: marketConfirm && mid ? 'POSITIVE_REAL_YIELD_SENSITIVE' : setup ? 'WATCH' : 'NO_ACCORD_TILT',
      SPY: marketConfirm && mid ? 'MODERATELY_POSITIVE' : setup ? 'WATCH' : 'NO_ACCORD_TILT',
      BTC: score >= 85 ? 'RESEARCH_STRONGLY_POSITIVE' : high ? 'RESEARCH_POSITIVE' : mid ? 'RESEARCH_WATCH' : 'NO_ACCORD_TILT',
      DBC: mid ? 'CONDITIONAL_REFLATION_REQUIRED' : 'NO_ACCORD_TILT',
      USD: high ? 'WATCH_NEGATIVE' : 'NO_ACCORD_TILT'
    },
    interpretation_only: true,
    promoted_money_transmission_unchanged: ['SPY', 'QQQ', 'GLD', 'DBC']
  };
}

function evaluate(raw, cutoffDate) {
  const treasury = treasuryBlock(raw, cutoffDate);
  const fed = fedReserveBlock(raw, cutoffDate);
  const handoff = handoffBlock(raw, fed, cutoffDate);
  const market = marketBlock(raw, cutoffDate);
  const score = round((treasury.points || 0) + (fed.points || 0) + (handoff.points || 0) + (market.points || 0), 1);
  const availableBlocks = [treasury, fed, handoff, market].filter(x => x.status === 'AVAILABLE').length;
  const band = bandForScore(score);
  const repressionRisk = score >= 85 && market.status === 'AVAILABLE' && Number(market.real_yield_10y_pct) < 0;
  return {
    cutoff_date: cutoffDate,
    score,
    band,
    repression_risk: repressionRisk,
    market_conflict: market.direction === 'REJECT',
    coverage: { available_blocks: availableBlocks, total_blocks: 4 },
    blocks: {
      treasury_duration_pressure: treasury,
      fed_reserve_support: fed,
      private_bank_handoff: handoff,
      market_yield_suppression: market
    },
    asset_map: buildAssetMap(score, treasury, fed, market)
  };
}

function endOfPreviousMonths(today, count) {
  const out = [];
  for (let i = count; i >= 1; i -= 1) {
    const d = new Date(`${today}T00:00:00Z`);
    d.setUTCDate(1);
    d.setUTCMonth(d.getUTCMonth() - i + 1);
    d.setUTCDate(0);
    out.push(d.toISOString().slice(0, 10));
  }
  return out;
}

function trendArrow(delta) {
  if (!Number.isFinite(delta) || delta === 0) return '→';
  return delta > 0 ? '↑' : '↓';
}

async function fetchRawInputs() {
  const [assetsCsv, reservesCsv, bankCsv, treasuryRows, realYields, termCsv] = await Promise.all([
    fetchText(H41_TOTAL_ASSETS_URL),
    fetchText(H41_TABLE1_URL),
    fetchText(FRED_BANK_ASSETS_URL),
    fetchTreasuryRows(),
    fetchRealYieldRows(),
    fetchText(FED_TERM_PREMIUM_URL)
  ]);
  return {
    fedAssets: parseH41Series(assetsCsv, 'RESPPA_N.WW'),
    reserves: parseH41Series(reservesCsv, 'RESH4R_N.WW'),
    bankAssets: parseFredSeries(bankCsv),
    treasuryRows,
    realYields,
    termPremium: parseTermPremiumCsv(termCsv)
  };
}

export async function buildAccordWatchV2() {
  const raw = await fetchRawInputs();
  const today = new Date().toISOString().slice(0, 10);
  const current = evaluate(raw, today);
  const oneMonth = evaluate(raw, dateMinusDays(today, 30));
  const threeMonths = evaluate(raw, dateMinusDays(today, 91));
  const delta1m = round(current.score - oneMonth.score, 1);
  const delta3m = round(current.score - threeMonths.score, 1);

  const monthlyCutoffs = endOfPreviousMonths(today, 12);
  const history = monthlyCutoffs.map(cutoff => {
    const x = evaluate(raw, cutoff);
    return {
      date: cutoff,
      score: x.score,
      band: x.band,
      available_blocks: x.coverage.available_blocks,
      treasury_points: x.blocks.treasury_duration_pressure.points,
      fed_reserve_points: x.blocks.fed_reserve_support.points,
      handoff_points: x.blocks.private_bank_handoff.points,
      market_points: x.blocks.market_yield_suppression.points
    };
  });
  history.push({
    date: today,
    score: current.score,
    band: current.band,
    available_blocks: current.coverage.available_blocks,
    treasury_points: current.blocks.treasury_duration_pressure.points,
    fed_reserve_points: current.blocks.fed_reserve_support.points,
    handoff_points: current.blocks.private_bank_handoff.points,
    market_points: current.blocks.market_yield_suppression.points
  });

  return {
    schema_version: 'gmli-accord-watch-v2',
    version: 'GMLI_ACCORD_WATCH_V2',
    generated_at: new Date().toISOString(),
    evidence_tier: 'RESEARCH_DIAGNOSTIC',
    presentation_score: true,
    scoring_effect: 'NONE',
    automatic_weight_change: 0,
    methodology_effect: 'NONE',
    purpose: '0–100 closeness gauge for the hypothesized Treasury–Fed Accord 2.0 / financial-repression setup. It is not a probability, GMLI regime score or allocation weight.',
    score: current.score,
    band: current.band,
    repression_risk: current.repression_risk,
    market_conflict: current.market_conflict,
    coverage: current.coverage,
    trend: {
      arrow: trendArrow(delta1m),
      delta_1m_points: delta1m,
      delta_3m_points: delta3m,
      score_1m_ago: oneMonth.score,
      score_3m_ago: threeMonths.score,
      interpretation: delta1m > 0 ? 'MOVING_CLOSER' : delta1m < 0 ? 'MOVING_AWAY' : 'UNCHANGED'
    },
    blocks: current.blocks,
    asset_map: current.asset_map,
    history,
    methodology: {
      weights: {
        treasury_duration_pressure: 25,
        fed_reserve_support: 25,
        private_bank_handoff: 25,
        market_yield_suppression: 25
      },
      treasury_subweights: { composition: 12.5, net_supply_flow_proxy: 12.5 },
      bands: { DISTANT: '0-24', SETUP: '25-49', DEVELOPING: '50-69', EMERGING: '70-84', ACCORD_LIKE: '85-100' },
      frozen_spec: 'docs/GMLI_ACCORD_WATCH_V2.md',
      v1_preserved: true,
      handoff_predictive_status: 'STOP_RESEARCH_DIAGNOSTIC'
    },
    guardrail: 'RESEARCH_DIAGNOSTIC / presentation score only. No GMLI conviction points, CORE/OVERLAY changes, automatic allocation weights or predictive rescue optimization.'
  };
}

function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function signed(value) {
  if (value == null || !Number.isFinite(Number(value))) return 'n/a';
  const n = Number(value);
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}`;
}

export function accordWatchV2Html(accord) {
  const a = accord || {};
  const t = a.blocks?.treasury_duration_pressure || {};
  const f = a.blocks?.fed_reserve_support || {};
  const h = a.blocks?.private_bank_handoff || {};
  const m = a.blocks?.market_yield_suppression || {};
  const b = a.asset_map?.bond_read || {};
  const score = Number.isFinite(Number(a.score)) ? Number(a.score) : 0;
  const stateClass = score >= 70 ? 'good' : score >= 25 ? 'neutral' : 'wait';
  const best = Object.entries(a.asset_map?.assets || {})
    .filter(([, v]) => /POSITIVE/.test(v) && !/CONDITIONAL|CAUTION/.test(v))
    .map(([k]) => k)
    .slice(0, 5)
    .join(', ') || 'none';

  return `<div id="accordWatchV2" class="card accordGaugeCard" style="grid-column:1/-1"><div class="tag">CITRINI / ACCORD WATCH v2 · 0–100 CLOSENESS GAUGE</div><div class="accordGaugeWrap"><div class="accordGauge"><svg viewBox="0 0 200 112" role="img" aria-label="Accord closeness ${esc(score)} out of 100"><path class="accordGaugeBase" pathLength="100" d="M20 100 A80 80 0 0 1 180 100"/><path class="accordGaugeFill" pathLength="100" stroke-dasharray="${esc(score)} 100" d="M20 100 A80 80 0 0 1 180 100"/></svg><div class="accordGaugeValue ${stateClass}">${esc(score.toFixed(1))}<span>/100</span></div><div class="accordGaugeBand">${esc(a.band || 'UNAVAILABLE')}</div></div><div class="accordGaugeSummary"><div class="score ${stateClass}" style="font-size:24px">${esc(a.trend?.arrow || '→')} ${esc(a.trend?.interpretation || 'UNAVAILABLE')}</div><div class="marketMeta"><b>1M:</b> ${esc(signed(a.trend?.delta_1m_points))} pts · <b>3M:</b> ${esc(signed(a.trend?.delta_3m_points))} pts<br><b>Treasury:</b> ${esc(t.points ?? 0)}/25 · ${esc(t.direction || 'UNAVAILABLE')}<br><b>Fed/reserves:</b> ${esc(f.points ?? 0)}/25 · ${esc(f.direction || 'UNAVAILABLE')}<br><b>Private bank handoff:</b> ${esc(h.points ?? 0)}/25 · ${esc(h.state || 'UNAVAILABLE')}<br><b>Market verdict:</b> ${esc(m.points ?? 0)}/25 · ${esc(m.direction || 'UNAVAILABLE')}</div></div></div><div class="marketMeta" style="margin-top:10px"><b>Treasury flow:</b> short/floating ${esc(signed(t.short_floating_net_change_bn))}bn vs fixed duration ${esc(signed(t.fixed_duration_net_change_bn))}bn · fixed-share 3M ${esc(signed(t.fixed_duration_share_change_3m_pp))} pp<br><b>Fed→Bank:</b> Fed assets 13W ${esc(signed(h.fed_total_assets_13w_pct))}% · bank assets 13W ${esc(signed(h.bank_total_assets_13w_pct))}% · predictive gate remains STOP_RESEARCH_DIAGNOSTIC<br><b>Market:</b> 10Y real yield ${esc(m.real_yield_10y_pct == null ? 'n/a' : `${Number(m.real_yield_10y_pct).toFixed(2)}%`)} (${esc(signed(m.real_yield_10y_change_3m_pp))} pp/3M) · term premium ${esc(m.term_premium_10y_pct == null ? 'n/a' : `${Number(m.term_premium_10y_pct).toFixed(2)}%`)} (${esc(signed(m.term_premium_10y_change_3m_pp))} pp/3M)<br><b>Bonds:</b> duration price support ${esc(b.duration_price_support || 'UNAVAILABLE')} · ${esc(b.real_bond_value || 'UNAVAILABLE')}<br><b>Scenario beneficiaries now:</b> ${esc(best)}</div><div class="small muted" style="margin-top:8px">Presentation score only — not probability, not GMLI conviction, weight 0 · <a href="./api/accord-watch-v2.json">accord-watch-v2.json</a> · <a href="./api/accord-watch-history.json">trend history</a></div></div>`;
}
