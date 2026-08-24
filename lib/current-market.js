const SYMBOLS = ['SPY','QQQ','GLD','DBC'];

function nyParts(date = new Date()) {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone:'America/New_York', year:'numeric', month:'2-digit', day:'2-digit',
    hour:'2-digit', minute:'2-digit', hour12:false
  });
  const parts = Object.fromEntries(fmt.formatToParts(date).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
  return {
    date:`${parts.year}-${parts.month}-${parts.day}`,
    minutes:Number(parts.hour) * 60 + Number(parts.minute)
  };
}

function ymdInNy(tsSeconds) {
  const fmt = new Intl.DateTimeFormat('en-CA', {timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'});
  return fmt.format(new Date(tsSeconds * 1000));
}

function avg(xs) { return xs.reduce((a,b)=>a+b,0)/xs.length; }
function pct(v) { return Number((100*v).toFixed(2)); }
function round(v, n=2) { return Number(v.toFixed(n)); }

function trendState(last, ma50, ma200) {
  if (last > ma50 && ma50 > ma200) return 'BULLISH';
  if (last < ma50 && ma50 < ma200) return 'BEARISH';
  if (last > ma200) return 'POSITIVE_MIXED';
  if (last < ma200) return 'NEGATIVE_MIXED';
  return 'MIXED';
}

function directionFromCurrent(state) {
  if (state === 'BULLISH' || state === 'POSITIVE_MIXED') return 'UP';
  if (state === 'BEARISH' || state === 'NEGATIVE_MIXED') return 'DOWN';
  return 'MIXED';
}

function directionFromStructural(stage) {
  if (String(stage||'').includes('UP')) return 'UP';
  if (String(stage||'').includes('DOWN')) return 'DOWN';
  return 'MIXED';
}

function divergence(structural, current) {
  const s = directionFromStructural(structural);
  const c = directionFromCurrent(current);
  if (s === 'UP' && c === 'DOWN') return 'NEGATIVE_DIVERGENCE';
  if (s === 'DOWN' && c === 'UP') return 'POSITIVE_DIVERGENCE';
  if (s !== 'MIXED' && s === c) return 'CONFIRMS';
  return 'MIXED';
}

async function yahooDaily(sym) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${sym}?range=2y&interval=1d&events=history&includeAdjustedClose=true`;
  const r = await fetch(url,{headers:{'User-Agent':'Mozilla/5.0'}});
  if (!r.ok) throw new Error(`Yahoo ${sym} ${r.status}`);
  const j = await r.json();
  const z = j.chart?.result?.[0];
  if (!z) throw new Error(`Yahoo ${sym} empty result`);
  const ts = z.timestamp || [];
  const adj = z.indicators?.adjclose?.[0]?.adjclose || [];
  const close = z.indicators?.quote?.[0]?.close || [];
  const today = nyParts();
  const rows = [];
  for (let i=0;i<ts.length;i++) {
    const value = Number.isFinite(adj[i]) ? adj[i] : close[i];
    if (!Number.isFinite(value)) continue;
    const date = ymdInNy(ts[i]);
    if (date === today.date && today.minutes < 16*60+10) continue;
    rows.push({date,value});
  }
  if (rows.length < 200) throw new Error(`Yahoo ${sym} insufficient daily history`);
  return rows;
}

function summarize(rows, structuralStage) {
  const values = rows.map(x=>x.value);
  const last = values.at(-1);
  const ma50 = avg(values.slice(-50));
  const ma200 = avg(values.slice(-200));
  const r1m = values.length >= 22 ? last / values.at(-22) - 1 : null;
  const state = trendState(last, ma50, ma200);
  return {
    latest_completed_session: rows.at(-1).date,
    price: round(last,4),
    return_1m_pct: r1m == null ? null : pct(r1m),
    ma50: round(ma50,4),
    ma200: round(ma200,4),
    trend: state,
    structural_monthly_stage: structuralStage || 'UNKNOWN',
    divergence_vs_structural: divergence(structuralStage,state),
    evidence_tier:'RESEARCH',
    role:'CURRENT_MARKET_CONFIRMATION_ONLY'
  };
}

export async function buildCurrentMarketConfirmation(opportunity) {
  const settled = await Promise.allSettled(SYMBOLS.map(async sym => {
    const structural = opportunity?.assets?.[sym]?.entry_inputs?.turn?.stage || 'UNKNOWN';
    return [sym, summarize(await yahooDaily(sym), structural)];
  }));
  const assets = {};
  const errors = [];
  for (const r of settled) {
    if (r.status === 'fulfilled') assets[r.value[0]] = r.value[1];
    else errors.push(r.reason?.message || String(r.reason));
  }
  const rows = Object.values(assets);
  const positive = rows.filter(x=>directionFromCurrent(x.trend)==='UP').length;
  const negative = rows.filter(x=>directionFromCurrent(x.trend)==='DOWN').length;
  const divergences = Object.entries(assets).filter(([,x])=>x.divergence_vs_structural.includes('DIVERGENCE')).map(([asset,x])=>({asset,type:x.divergence_vs_structural}));
  return {
    schema_version:'gmli-current-market-v1',
    status: rows.length === SYMBOLS.length ? 'OK' : rows.length ? 'PARTIAL' : 'UNAVAILABLE',
    evidence_tier:'RESEARCH',
    role:'CURRENT_MARKET_CONFIRMATION_ONLY',
    generated_at:new Date().toISOString(),
    coverage:`${rows.length}/${SYMBOLS.length}`,
    positive,
    negative,
    summary: positive >= 3 ? 'BROADLY_POSITIVE' : negative >= 3 ? 'BROADLY_NEGATIVE' : 'MIXED',
    divergences,
    assets,
    errors,
    note:'Current daily market confirmation can raise/lower conviction or highlight divergence; it never rewrites frozen Money Core or completed-month structural signals.'
  };
}
