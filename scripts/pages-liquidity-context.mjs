const FRED_BANK_ASSETS_URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=TLAACBW027SBOG';
const TREASURY_MSPD_BASE = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/debt/mspd/mspd_table_1';

const round = (value, digits = 2) => Number.isFinite(value) ? Number(value.toFixed(digits)) : null;

async function fetchText(url) {
  const res = await fetch(url, {
    headers: { 'user-agent': 'GMLI-liquidity-context/1.0' },
    signal: AbortSignal.timeout(20000)
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return res.text();
}

async function fetchJson(url) {
  const res = await fetch(url, {
    headers: { 'user-agent': 'GMLI-liquidity-context/1.0' },
    signal: AbortSignal.timeout(20000)
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return res.json();
}

function pctChange(current, prior) {
  if (!Number.isFinite(current) || !Number.isFinite(prior) || prior === 0) return null;
  return (current / prior - 1) * 100;
}

function nearestOnOrBefore(rows, targetDate) {
  const target = new Date(`${targetDate}T00:00:00Z`).getTime();
  let best = null;
  for (const row of rows) {
    const t = new Date(`${row.date}T00:00:00Z`).getTime();
    if (t <= target && (!best || t > best.time)) best = { ...row, time: t };
  }
  return best;
}

function dateMinusDays(date, days) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

function dateMinusMonths(date, months) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCMonth(d.getUTCMonth() - months);
  return d.toISOString().slice(0, 10);
}

async function buildBankBalanceSheetImpulse() {
  try {
    const csv = await fetchText(FRED_BANK_ASSETS_URL);
    const lines = csv.trim().split(/\r?\n/);
    const rows = lines.slice(1).map(line => {
      const [date, raw] = line.split(',');
      return { date, value: Number(raw) };
    }).filter(x => /^\d{4}-\d{2}-\d{2}$/.test(x.date) && Number.isFinite(x.value));

    if (rows.length < 60) throw new Error(`Insufficient FRED history: ${rows.length} rows`);
    rows.sort((a, b) => a.date.localeCompare(b.date));
    const latest = rows.at(-1);
    const t13 = nearestOnOrBefore(rows, dateMinusDays(latest.date, 91));
    const t26 = nearestOnOrBefore(rows, dateMinusDays(latest.date, 182));
    const t52 = nearestOnOrBefore(rows, dateMinusDays(latest.date, 364));
    if (!t13 || !t26 || !t52) throw new Error('Could not resolve 13W/26W/52W comparison rows');

    const current13w = pctChange(latest.value, t13.value);
    const prior13w = pctChange(t13.value, t26.value);
    const impulse = Number.isFinite(current13w) && Number.isFinite(prior13w) ? current13w - prior13w : null;
    const yoy = pctChange(latest.value, t52.value);

    return {
      status: 'AVAILABLE',
      label: 'Bank balance-sheet impulse',
      source: 'Federal Reserve H.8 via FRED',
      series_id: 'TLAACBW027SBOG',
      series_name: 'Total Assets, All Commercial Banks',
      frequency: 'WEEKLY_SA',
      units: 'USD billions',
      latest_date: latest.date,
      latest_assets_bn: round(latest.value, 1),
      change_13w_pct: round(current13w),
      prior_13w_change_pct: round(prior13w),
      impulse_acceleration_pp: round(impulse),
      yoy_pct: round(yoy),
      direction: impulse == null ? 'UNAVAILABLE' : impulse > 0 ? 'ACCELERATING' : impulse < 0 ? 'DECELERATING' : 'FLAT',
      interpretation: 'Impulse = latest 13-week asset growth minus the preceding 13-week asset growth. Positive means bank balance-sheet expansion is accelerating; negative means it is decelerating. No GMLI score impact.'
    };
  } catch (error) {
    return {
      status: 'UNAVAILABLE',
      label: 'Bank balance-sheet impulse',
      source: 'Federal Reserve H.8 via FRED',
      series_id: 'TLAACBW027SBOG',
      error: String(error?.message || error),
      interpretation: 'Informational diagnostic only; source failure never changes GMLI scoring.'
    };
  }
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
    ...Object.fromEntries(Object.entries(values).map(([k, v]) => [`${k}_mil`, round(v, 0)])),
    proxy_marketable_mil: round(marketable, 0),
    bills_share_pct: round(values.bills / marketable * 100),
    frns_share_pct: round(values.frns / marketable * 100),
    short_or_floating_share_pct: round(shortFloating / marketable * 100),
    fixed_duration_share_pct: round(fixedDuration / marketable * 100)
  };
}

async function fetchTreasuryRows() {
  const common = 'fields=record_date,security_type_desc,security_class_desc,debt_held_public_mil_amt&sort=-record_date&format=json&page%5Bnumber%5D=1&page%5Bsize%5D=500';
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

async function buildTreasuryDurationMix() {
  try {
    const rows = await fetchTreasuryRows();
    const dates = [...new Set(rows.map(x => x.record_date).filter(Boolean))].sort().reverse();
    if (!dates.length) throw new Error('MSPD returned no record dates');
    const latestDate = dates[0];
    const target = dateMinusMonths(latestDate, 3);
    const priorDate = dates.find(date => date <= target) || dates.at(-1);
    const latest = summarizeTreasury(rows, latestDate);
    const prior = summarizeTreasury(rows, priorDate);
    if (!latest || !prior) throw new Error('Could not summarize current/prior MSPD composition');

    const delta = latest.short_or_floating_share_pct - prior.short_or_floating_share_pct;
    return {
      status: 'AVAILABLE',
      label: 'Treasury duration mix proxy',
      source: 'U.S. Treasury Fiscal Data — Monthly Statement of the Public Debt, Table 1',
      latest_date: latestDate,
      comparison_date: priorDate,
      basis: 'Debt held by the public; standard marketable classes only',
      latest,
      short_or_floating_share_change_3m_pp: round(delta),
      direction: delta > 0 ? 'MORE_SHORT_OR_FLOATING' : delta < 0 ? 'MORE_FIXED_DURATION' : 'UNCHANGED',
      interpretation: 'Short/floating proxy = Bills + FRNs; fixed-duration proxy = Notes + Bonds + TIPS. This is a face-value composition proxy, not DV01, weighted-average maturity or an issuance-flow model. No GMLI score impact.',
      coverage_note: 'Federal Financing Bank securities are excluded from this proxy.'
    };
  } catch (error) {
    return {
      status: 'UNAVAILABLE',
      label: 'Treasury duration mix proxy',
      source: 'U.S. Treasury Fiscal Data — Monthly Statement of the Public Debt, Table 1',
      error: String(error?.message || error),
      interpretation: 'Informational diagnostic only; source failure never changes GMLI scoring.'
    };
  }
}

export async function buildLiquidityContext() {
  const [bank, treasury] = await Promise.all([
    buildBankBalanceSheetImpulse(),
    buildTreasuryDurationMix()
  ]);
  return {
    schema_version: 'gmli-liquidity-context-v1',
    version: 'GMLI_LIQUIDITY_CONTEXT_V1',
    generated_at: new Date().toISOString(),
    evidence_tier: 'RESEARCH_DIAGNOSTIC',
    scoring_effect: 'NONE',
    automatic_weight_change: 0,
    methodology_effect: 'NONE',
    purpose: 'Informational context for bank balance-sheet expansion and U.S. Treasury maturity composition. It cannot override Money Core, Funding, Fiscal, Market Confirmation or the frozen 10-point conviction rubric.',
    bank_balance_sheet_impulse: bank,
    treasury_duration_mix: treasury,
    guardrail: 'Display-only research diagnostic. Any future scoring use requires a separately frozen, versioned candidate and promotion gate.'
  };
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function fmt(value) {
  return value == null || !Number.isFinite(Number(value)) ? 'n/a' : Number(value).toFixed(2);
}

function signed(value) {
  if (value == null || !Number.isFinite(Number(value))) return 'n/a';
  const number = Number(value);
  return `${number > 0 ? '+' : ''}${number.toFixed(2)}`;
}

function scoreClass(direction, positive, negative) {
  if (direction === positive) return 'good';
  if (direction === negative) return 'wait';
  return 'neutral';
}

export function enhanceLiquidityContext(html, context = null) {
  if (html.includes('id="liquidityContext"')) return html;

  const x = context || {};
  const b = x.bank_balance_sheet_impulse || {};
  const t = x.treasury_duration_mix || {};
  const l = t.latest || {};

  const bankAvailable = b.status === 'AVAILABLE';
  const treasuryAvailable = t.status === 'AVAILABLE';
  const bankDirection = bankAvailable ? (b.direction || 'UNAVAILABLE') : 'UNAVAILABLE';
  const treasuryDirection = treasuryAvailable ? (t.direction || 'UNAVAILABLE') : 'UNAVAILABLE';

  const bankMeta = bankAvailable
    ? `As of ${escapeHtml(b.latest_date)} · assets $${escapeHtml(Number(b.latest_assets_bn).toLocaleString('en-US'))}bn<br>13W ${escapeHtml(signed(b.change_13w_pct))}% · prior 13W ${escapeHtml(signed(b.prior_13w_change_pct))}%<br><b>Impulse ${escapeHtml(signed(b.impulse_acceleration_pp))} pp</b> · YoY ${escapeHtml(signed(b.yoy_pct))}%`
    : `Source unavailable · ${escapeHtml(b.error || 'No verified bank snapshot in this build')}`;

  const treasuryMeta = treasuryAvailable
    ? `As of ${escapeHtml(t.latest_date)} · vs ${escapeHtml(t.comparison_date)}<br>Bills ${escapeHtml(fmt(l.bills_share_pct))}% · FRNs ${escapeHtml(fmt(l.frns_share_pct))}%<br><b>Short/floating ${escapeHtml(fmt(l.short_or_floating_share_pct))}%</b> · fixed duration ${escapeHtml(fmt(l.fixed_duration_share_pct))}%<br>3M shift ${escapeHtml(signed(t.short_or_floating_share_change_3m_pp))} pp`
    : `Source unavailable · ${escapeHtml(t.error || 'No verified Treasury snapshot in this build')}`;

  const audit = `Guardrail: ${escapeHtml(x.guardrail || 'Display-only research diagnostic; no GMLI score impact.')}\nBank: ${escapeHtml(b.interpretation || 'Informational diagnostic only.')}\nTreasury: ${escapeHtml(t.interpretation || 'Informational diagnostic only.')}`;

  const section = `\n<section id="liquidityContext" class="section"><h2>Liquidity Context · Informational</h2><p class="muted">RESEARCH_DIAGNOSTIC · scoring effect NONE · automatic weight 0. Bank balance-sheet impulse and Treasury duration mix add context only; they do not change the GMLI regime or conviction.</p><div class="liquidityContextGrid"><article class="card"><div class="tag">BANK BALANCE-SHEET IMPULSE · H.8</div><div class="score ${scoreClass(bankDirection, 'ACCELERATING', 'DECELERATING')}" id="bankImpulseDirection">${escapeHtml(bankDirection)}</div><div class="marketMeta" id="bankImpulseMeta">${bankMeta}</div></article><article class="card"><div class="tag">TREASURY DURATION MIX · MSPD</div><div class="score ${scoreClass(treasuryDirection, 'MORE_SHORT_OR_FLOATING', 'MORE_FIXED_DURATION')}" id="treasuryMixDirection">${escapeHtml(treasuryDirection)}</div><div class="marketMeta" id="treasuryMixMeta">${treasuryMeta}</div></article></div><div class="audit" id="liquidityContextAudit" style="margin-top:12px">${audit}</div><div class="small muted" style="margin-top:8px">Verified static source: <a href="./api/liquidity-context.json">liquidity-context.json</a></div></section>\n`;

  return html
    .replace('</style>', '.liquidityContextGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}@media(max-width:700px){.liquidityContextGrid{grid-template-columns:1fr}}</style>')
    .replace('</nav>', '<a href="#liquidityContext">LIQUIDITY CONTEXT</a></nav>')
    .replace('<section id="research"', `${section}<section id="research"`);
}
