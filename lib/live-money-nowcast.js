import { MONEY_NOWCAST as FALLBACK } from './nowcast-state.js';

const CORE_REFERENCE = '2026-02-28';
const CORE_MONTH = '2026-02';
const TTL_MS = 30 * 60 * 1000;
const HARD_DEADLINE_MS = 3500;
let CACHE = null;

const sleepReject = (ms, label) => new Promise((_, reject) => {
  const t = setTimeout(() => reject(new Error(`${label} timeout after ${ms}ms`)), ms);
  t.unref?.();
});

function ym(x) { return String(x || '').slice(0, 7); }
function round(x, n = 2) { return Number.isFinite(x) ? Number(x.toFixed(n)) : null; }
function last(xs) { return xs?.length ? xs[xs.length - 1] : null; }
function byMonth(xs, m) { return xs.find(x => ym(x.date) === m) || null; }

async function getText(url, timeoutMs = 1500, headers = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  timer.unref?.();
  try {
    const r = await fetch(url, {
      headers: {
        'user-agent': 'GMLI-Research-Copilot/2.3',
        accept: 'text/html,text/csv,application/json,*/*',
        ...headers
      },
      signal: controller.signal,
      cache: 'no-store'
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.text();
  } finally {
    clearTimeout(timer);
  }
}

function compare(latest, ref) {
  if (!Number.isFinite(latest) || !Number.isFinite(ref)) {
    return { direction: 'UNKNOWN', delta_vs_core_pp: null };
  }
  const d = latest - ref;
  return {
    direction: d > 0.25 ? 'ACCELERATING' : d < -0.25 ? 'DECELERATING' : 'STABLE',
    delta_vs_core_pp: round(d, 2)
  };
}

function normalizeBlock(base, overrides = {}) {
  const latest = overrides.latest_yoy_pct ?? base.latest_yoy_pct;
  const ref = overrides.core_reference_yoy_pct ?? base.core_reference_yoy_pct;
  const c = compare(latest, ref);
  return {
    ...base,
    evidence_tier: 'RESEARCH',
    ...overrides,
    latest_yoy_pct: round(latest, 4),
    core_reference_yoy_pct: round(ref, 4),
    direction_vs_core: c.direction,
    delta_vs_core_pp: c.delta_vs_core_pp,
    expanding_yoy: Number.isFinite(latest) ? latest > 0 : null
  };
}

function fallbackBlock(key, reason) {
  const base = FALLBACK.blocks?.[key];
  if (!base) return { evidence_tier: 'RESEARCH', status: 'UNAVAILABLE', live_error: String(reason) };
  return normalizeBlock(base, {
    status: 'FALLBACK_LAST_VERIFIED',
    live_error: String(reason),
    note: `${base.note || ''} Live refresh unavailable inside request deadline; using last verified snapshot.`.trim()
  });
}

function parseFredCsv(csv) {
  const rows = String(csv || '').trim().split(/\r?\n/).slice(1);
  return rows.map(line => {
    const [date, raw] = line.split(',');
    return { date, value: Number(raw) };
  }).filter(x => x.date && Number.isFinite(x.value));
}

function yoyFromLevels(xs, m) {
  const cur = byMonth(xs, m);
  if (!cur) return null;
  const [y, mo] = m.split('-').map(Number);
  const prev = byMonth(xs, `${y - 1}-${String(mo).padStart(2, '0')}`);
  return prev?.value ? ((cur.value / prev.value) - 1) * 100 : null;
}

async function fredSeries(id, start) {
  const url = `https://fred.stlouisfed.org/graph/fredgraph.csv?id=${encodeURIComponent(id)}&cosd=${start}`;
  return parseFredCsv(await getText(url, 1300, { accept: 'text/csv' }));
}

async function usLive() {
  const base = FALLBACK.blocks.us;
  const xs = await fredSeries('M2SL', '2025-01-01');
  const l = last(xs);
  if (!l) throw new Error('No US M2');
  const m = ym(l.date);
  const latest = yoyFromLevels(xs, m);
  const ref = yoyFromLevels(xs, CORE_MONTH);
  if (!Number.isFinite(latest)) throw new Error('US M2 YoY unavailable');
  return normalizeBlock(base, {
    status: 'OK',
    source: 'Federal Reserve / FRED M2SL',
    source_url: 'https://fred.stlouisfed.org/series/M2SL',
    latest_date: m,
    latest_yoy_pct: latest,
    core_reference_yoy_pct: Number.isFinite(ref) ? ref : base.core_reference_yoy_pct,
    note: 'Live current-vintage monthly M2; YoY calculated from levels.'
  });
}

function splitCsv(line) {
  const out = []; let cur = ''; let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') {
      if (quoted && line[i + 1] === '"') { cur += '"'; i++; }
      else quoted = !quoted;
    } else if (c === ',' && !quoted) { out.push(cur); cur = ''; }
    else cur += c;
  }
  out.push(cur);
  return out;
}

function parseCsvRows(csv) {
  const lines = String(csv || '').trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const h = splitCsv(lines[0]);
  return lines.slice(1).map(line => {
    const v = splitCsv(line); const o = {};
    h.forEach((k, i) => { o[k] = v[i]; });
    return o;
  });
}

async function euroLive() {
  const base = FALLBACK.blocks.euro_area;
  const key = 'M.U2.Y.V.M30.X.I.U2.2300.Z01.A';
  const url = `https://data-api.ecb.europa.eu/service/data/BSI/${key}?startPeriod=2026-02&format=csvdata`;
  const rows = parseCsvRows(await getText(url, 1600, { accept: 'text/csv' }))
    .map(r => ({ date: r.TIME_PERIOD || r.TIME_PERIOD_START || r.TIME_PERIOD_END, value: Number(r.OBS_VALUE) }))
    .filter(x => x.date && Number.isFinite(x.value))
    .sort((a, b) => String(a.date).localeCompare(String(b.date)));
  const l = last(rows);
  const ref = rows.find(x => ym(x.date) === CORE_MONTH);
  if (!l) throw new Error('No ECB M3');
  return normalizeBlock(base, {
    status: 'OK',
    source: 'ECB Data Portal BSI',
    source_url: 'https://data.ecb.europa.eu/data/datasets/BSI/BSI.M.U2.Y.V.M30.X.I.U2.2300.Z01.A',
    latest_date: ym(l.date),
    latest_yoy_pct: l.value,
    core_reference_yoy_pct: Number.isFinite(ref?.value) ? ref.value : base.core_reference_yoy_pct,
    note: 'Live official ECB annual-growth M3 series.'
  });
}

function stripHtml(s) {
  return String(s || '')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;|&#160;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/\s+/g, ' ')
    .trim();
}

async function japanLive() {
  const base = FALLBACK.blocks.japan;
  const url = 'https://www.stat-search.boj.or.jp/ssi/mtshtml/md02_m_1_en.html';
  const text = stripHtml(await getText(url, 1500));
  const re = /(20\d{2}\/(?:0[1-9]|1[0-2]))\s+(-?\d+(?:\.\d+)?)/g;
  const map = new Map(); let m;
  while ((m = re.exec(text))) {
    const d = m[1].replace('/', '-');
    if (!map.has(d)) map.set(d, Number(m[2]));
  }
  const rows = [...map.entries()].map(([date, value]) => ({ date, value })).sort((a, b) => a.date.localeCompare(b.date));
  const l = last(rows);
  const ref = rows.find(x => x.date === CORE_MONTH);
  if (!l) throw new Error('No BOJ M2');
  return normalizeBlock(base, {
    status: 'OK',
    source: 'Bank of Japan Time-Series Data Search',
    source_url: url,
    latest_date: l.date,
    latest_yoy_pct: l.value,
    core_reference_yoy_pct: Number.isFinite(ref?.value) ? ref.value : base.core_reference_yoy_pct,
    note: 'Live BOJ M2 YoY from the official table.'
  });
}

async function dollarLive() {
  const xs = await fredSeries('DTWEXBGS', '2026-02-01');
  const l = last(xs);
  const ref = last(xs.filter(x => x.date <= CORE_REFERENCE));
  if (!l || !ref) throw new Error('No broad dollar data');
  const pct = ((l.value / ref.value) - 1) * 100;
  return {
    evidence_tier: 'RESEARCH',
    status: 'OK',
    source: 'Federal Reserve / FRED Broad Dollar Index DTWEXBGS',
    source_url: 'https://fred.stlouisfed.org/series/DTWEXBGS',
    core_reference_date: ref.date,
    latest_date: l.date,
    pct_change_since_core: round(pct, 2),
    translation: pct < -1 ? 'TAILWIND_WEAKER_USD' : pct > 1 ? 'HEADWIND_STRONGER_USD' : 'NEUTRAL',
    note: 'Live translation overlay only; not frozen FX-neutral methodology.'
  };
}

export function summarizeLiveNowcast(state) {
  const blocks = Object.values(state?.blocks || {});
  const usable = blocks.filter(x => ['OK', 'FALLBACK_LAST_VERIFIED', 'OK_VERIFIED_SECONDARY'].includes(x.status) && Number.isFinite(x.latest_yoy_pct));
  const comp = usable.filter(x => Number.isFinite(x.core_reference_yoy_pct));
  const accelerating = comp.filter(x => x.direction_vs_core === 'ACCELERATING').length;
  const decelerating = comp.filter(x => x.direction_vs_core === 'DECELERATING').length;
  const stable = comp.filter(x => x.direction_vs_core === 'STABLE').length;
  const expanding = usable.filter(x => x.expanding_yoy === true).length;
  const tilt = accelerating >= 3 && expanding === usable.length
    ? 'SUPPORTIVE_MIXED'
    : decelerating >= 3 ? 'DETERIORATING'
      : accelerating >= decelerating ? 'NEUTRAL_TO_SUPPORTIVE' : 'MIXED';
  return {
    label: accelerating >= 3 ? 'BROADLY_EXPANDING_MIXED_ACCELERATION' : decelerating >= 3 ? 'BROADLY_DECELERATING' : 'MIXED',
    tilt,
    score: null,
    score_status: 'NOT_COMPUTED',
    coverage: `${usable.length}/4`,
    comparisons_available: `${comp.length}/4`,
    accelerating,
    stable,
    decelerating,
    expanding_yoy: expanding,
    methodology: 'Unweighted directional freshness overlay versus frozen February reference. Fast live official refresh with explicit last-verified fallback.'
  };
}

export function moneyNowcastFreshness(blocks) {
  const names = { us: 'US', euro_area: 'EA', japan: 'JP', china: 'CN' };
  return Object.entries(blocks || {})
    .map(([k, v]) => `${names[k] || k} ${v.latest_date || 'n/a'}${v.status === 'FALLBACK_LAST_VERIFIED' ? '*' : ''}`)
    .join('; ');
}

function fallbackSnapshot(reason = 'hard deadline') {
  const blocks = Object.fromEntries(Object.entries(FALLBACK.blocks || {}).map(([k]) => [k, fallbackBlock(k, reason)]));
  const state = {
    version: 'GMLI Current Money Nowcast v1.3 LIVE',
    as_of: new Date().toISOString(),
    evidence_tier: 'RESEARCH',
    role: 'FRESHNESS_OVERLAY_ONLY',
    source_mode: 'LIVE_OFFICIAL_WITH_LAST_VERIFIED_FALLBACK',
    runtime_mode: 'HARD_DEADLINE_FAILSAFE',
    core_reference: {
      date: CORE_REFERENCE,
      guardrail: 'Does not alter frozen Money Core, weights, FX-neutral method, lags, horizons or thresholds.'
    },
    blocks,
    usd_translation: {
      ...(FALLBACK.usd_translation || {}),
      evidence_tier: 'RESEARCH',
      status: 'FALLBACK_LAST_VERIFIED',
      live_error: String(reason)
    }
  };
  const nowcast = summarizeLiveNowcast(state);
  state.nowcast = nowcast;
  state.interpretation = {
    engine_fact: `Frozen USD and FX-neutral Money Core remain dated ${CORE_REFERENCE}.`,
    current_research_inference: `${nowcast.tilt}: live refresh exceeded request budget, so last-verified current snapshots are used.`
  };
  return state;
}

async function buildLiveSnapshot() {
  const jobs = [
    ['us', usLive],
    ['euro_area', euroLive],
    ['japan', japanLive]
  ];
  const entries = await Promise.all(jobs.map(async ([key, fn]) => {
    try { return [key, await fn()]; }
    catch (e) { return [key, fallbackBlock(key, e?.message || e)]; }
  }));

  // China stays on the current verified July snapshot in-request. The PBoC search
  // endpoint is too slow/fragile for a serverless request path and previously caused timeouts.
  entries.push(['china', fallbackBlock('china', 'PBoC live parser intentionally excluded from request path')]);
  const blocks = Object.fromEntries(entries);

  let usd_translation;
  try { usd_translation = await dollarLive(); }
  catch (e) {
    usd_translation = {
      ...(FALLBACK.usd_translation || {}),
      evidence_tier: 'RESEARCH',
      status: 'FALLBACK_LAST_VERIFIED',
      live_error: String(e?.message || e)
    };
  }

  const state = {
    version: 'GMLI Current Money Nowcast v1.3 LIVE',
    as_of: new Date().toISOString(),
    evidence_tier: 'RESEARCH',
    role: 'FRESHNESS_OVERLAY_ONLY',
    source_mode: 'LIVE_OFFICIAL_WITH_LAST_VERIFIED_FALLBACK',
    runtime_mode: 'FAST_REQUEST_SAFE',
    core_reference: {
      date: CORE_REFERENCE,
      guardrail: 'Does not alter frozen Money Core, weights, FX-neutral method, lags, horizons or thresholds.'
    },
    blocks,
    usd_translation
  };
  const nowcast = summarizeLiveNowcast(state);
  state.nowcast = nowcast;
  const parts = Object.values(blocks).map(x => `${x.name || 'block'} ${x.direction_vs_core || 'UNKNOWN'}`);
  state.interpretation = {
    engine_fact: `Frozen USD and FX-neutral Money Core remain dated ${CORE_REFERENCE}.`,
    current_research_inference: `${nowcast.tilt}: ${parts.join(', ')}. USD translation: ${usd_translation.translation || 'UNKNOWN'}.`
  };
  return state;
}

export async function getLiveMoneyNowcast() {
  if (CACHE && (Date.now() - CACHE.at) < TTL_MS) return CACHE.value;
  let value;
  try {
    value = await Promise.race([
      buildLiveSnapshot(),
      sleepReject(HARD_DEADLINE_MS, 'live money refresh')
    ]);
  } catch (e) {
    value = fallbackSnapshot(e?.message || e);
  }
  CACHE = { at: Date.now(), value };
  return value;
}
