const WINDOW_MONTHS = 120;
const MIN_MONTHS = 36;

function addMonths(month, n) {
  const [y, m] = String(month).split('-').map(Number);
  const total = y * 12 + (m - 1) + n;
  const yy = Math.floor(total / 12);
  const mm = total % 12;
  return `${String(yy).padStart(4, '0')}-${String(mm + 1).padStart(2, '0')}`;
}

function finite(v) {
  return Number.isFinite(Number(v)) ? Number(v) : null;
}

function rollingStats(rows, index, key) {
  const start = Math.max(0, index - WINDOW_MONTHS + 1);
  const vals = rows.slice(start, index + 1).map(r => r[key]).filter(Number.isFinite);
  const current = rows[index][key];
  if (!Number.isFinite(current) || vals.length < MIN_MONTHS) return null;
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  const variance = vals.reduce((a, b) => a + (b - mean) ** 2, 0) / vals.length;
  const sd = Math.sqrt(variance);
  if (!(sd > 0)) return null;
  const z = (current - mean) / sd;
  const less = vals.filter(v => v < current).length;
  const equal = vals.filter(v => v === current).length;
  const percentile = 100 * (less + 0.5 * equal) / vals.length;
  return { z, percentile, n: vals.length, mean, sd };
}

function band(z) {
  if (!Number.isFinite(z)) return 'INSUFFICIENT_HISTORY';
  if (z >= 2) return 'EXTREME_HIGH';
  if (z >= 1) return 'ELEVATED_HIGH';
  if (z <= -2) return 'EXTREME_LOW';
  if (z <= -1) return 'ELEVATED_LOW';
  return 'NORMAL';
}

export function buildMoneyExtremes(history) {
  const sourceRows = (history?.rows || []).map(r => ({
    month: r.month,
    available_date: r.available_date,
    usd_yoy_pct: finite(r.usd_yoy_pct),
    fx_neutral_yoy_pct: finite(r.fx_neutral_yoy_pct)
  })).filter(r => /^\d{4}-\d{2}$/.test(String(r.month)));

  const byMonth = new Map(sourceRows.map(r => [r.month, r]));
  const raw = sourceRows.map(r => {
    const prior = byMonth.get(addMonths(r.month, -3));
    return {
      ...r,
      usd_accel3_pp: prior && Number.isFinite(r.usd_yoy_pct) && Number.isFinite(prior.usd_yoy_pct)
        ? r.usd_yoy_pct - prior.usd_yoy_pct : null,
      fx_neutral_accel3_pp: prior && Number.isFinite(r.fx_neutral_yoy_pct) && Number.isFinite(prior.fx_neutral_yoy_pct)
        ? r.fx_neutral_yoy_pct - prior.fx_neutral_yoy_pct : null
    };
  });

  const metrics = [
    ['usd_yoy_pct', 'usd_level'],
    ['fx_neutral_yoy_pct', 'fx_neutral_level'],
    ['usd_accel3_pp', 'usd_accel3'],
    ['fx_neutral_accel3_pp', 'fx_neutral_accel3']
  ];

  const rows = raw.map((r, i) => {
    const out = { ...r };
    for (const [key, prefix] of metrics) {
      const s = rollingStats(raw, i, key);
      out[`${prefix}_z`] = s ? s.z : null;
      out[`${prefix}_percentile`] = s ? s.percentile : null;
      out[`${prefix}_window_n`] = s ? s.n : 0;
    }
    return out;
  }).filter(r => metrics.some(([, prefix]) => Number.isFinite(r[`${prefix}_z`])));

  const last = rows.at(-1);
  if (!last) throw new Error('Money Historical Extremes has insufficient history');

  const latest = {
    month: last.month,
    available_date: last.available_date,
    usd_level: {
      value_pct: last.usd_yoy_pct,
      z: last.usd_level_z,
      percentile: last.usd_level_percentile,
      band: band(last.usd_level_z)
    },
    fx_neutral_level: {
      value_pct: last.fx_neutral_yoy_pct,
      z: last.fx_neutral_level_z,
      percentile: last.fx_neutral_level_percentile,
      band: band(last.fx_neutral_level_z)
    },
    usd_accel3: {
      value_pp: last.usd_accel3_pp,
      z: last.usd_accel3_z,
      percentile: last.usd_accel3_percentile,
      band: band(last.usd_accel3_z)
    },
    fx_neutral_accel3: {
      value_pp: last.fx_neutral_accel3_pp,
      z: last.fx_neutral_accel3_z,
      percentile: last.fx_neutral_accel3_percentile,
      band: band(last.fx_neutral_accel3_z)
    }
  };

  return {
    schema_version: 'gmli-money-extremes-v1',
    version: 'GMLI_MONEY_HISTORICAL_EXTREMES_V1',
    evidence_tier: 'RESEARCH_DIAGNOSTIC',
    scoring_effect: 'NONE',
    automatic_weight_change: 0,
    source: 'api/history promoted Global Money V2 history',
    construction: {
      frequency: 'MONTHLY',
      rolling_window_months: WINDOW_MONTHS,
      minimum_months: MIN_MONTHS,
      ddof: 0,
      lookahead: false,
      clipping: false,
      accel3_definition: 'YoY(t) - YoY(t-3), matching the promoted accel3 transform semantics',
      percentile: 'mid-rank empirical percentile within the same trailing rolling window',
      interpretation_only: true
    },
    guardrail: 'Diagnostic historical context only. It does not alter Money Core, transmission gates, Funding/Fiscal overlays, Signal Role Taxonomy or the frozen 10-point conviction rubric.',
    latest,
    rows
  };
}

function fmtZ(v) {
  return Number.isFinite(v) ? `${v >= 0 ? '+' : ''}${v.toFixed(2)}` : '—';
}

function fmtPct(v) {
  return Number.isFinite(v) ? `${v.toFixed(0)}th pct` : '—';
}

function fmtValue(v, unit) {
  return Number.isFinite(v) ? `${v >= 0 ? '+' : ''}${v.toFixed(2)}${unit}` : '—';
}

function bandHr(v) {
  const map = {
    EXTREME_HIGH: 'ekstremno visoko',
    ELEVATED_HIGH: 'povišeno visoko',
    NORMAL: 'normalno područje',
    ELEVATED_LOW: 'povišeno nisko',
    EXTREME_LOW: 'ekstremno nisko',
    INSUFFICIENT_HISTORY: 'nedovoljno povijesti'
  };
  return map[v] || String(v || '—');
}

function fmtMonth(month) {
  const [y, m] = String(month).split('-');
  return `${m}/${y}`;
}

function zChart(rows, specs, id) {
  const rr = rows.slice(-60);
  const W = 920, H = 270, p = { l: 48, r: 18, t: 16, b: 32 };
  const pw = W - p.l - p.r, ph = H - p.t - p.b;
  const vals = [];
  for (const r of rr) for (const s of specs) if (Number.isFinite(r[s.key])) vals.push(r[s.key]);
  let maxAbs = Math.max(2.5, ...vals.map(v => Math.abs(v)));
  maxAbs = Math.ceil(maxAbs * 2) / 2;
  const x = i => p.l + (rr.length === 1 ? 0 : i / (rr.length - 1) * pw);
  const y = v => p.t + (maxAbs - v) / (2 * maxAbs) * ph;
  let out = '';
  for (const v of [-2, -1, 0, 1, 2]) {
    if (Math.abs(v) > maxAbs) continue;
    const yy = y(v);
    out += `<line x1="${p.l}" y1="${yy}" x2="${W-p.r}" y2="${yy}" stroke="${v === 0 ? '#607789' : '#263d50'}" stroke-width="1" ${v === 0 ? '' : 'stroke-dasharray="5 5"'}/>`;
    out += `<text x="${p.l-7}" y="${yy+4}" text-anchor="end" fill="#7890a2" font-size="11">${v > 0 ? '+' : ''}${v}</text>`;
  }
  const idxs = [0, Math.round((rr.length - 1) * .25), Math.round((rr.length - 1) * .5), Math.round((rr.length - 1) * .75), rr.length - 1];
  for (const i of [...new Set(idxs)]) {
    if (!rr[i]) continue;
    out += `<text x="${x(i)}" y="${H-8}" text-anchor="middle" fill="#7890a2" font-size="11">${fmtMonth(rr[i].month)}</text>`;
  }
  for (const s of specs) {
    let d = '', open = false;
    rr.forEach((r, i) => {
      const v = r[s.key];
      if (Number.isFinite(v)) {
        d += `${open ? ' L ' : ' M '}${x(i)} ${y(v)}`;
        open = true;
      } else {
        open = false;
      }
    });
    out += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2.3" vector-effect="non-scaling-stroke"/>`;
  }
  return `<svg class="extChart" id="${id}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-label="${id}">${out}</svg>`;
}

function summaryCard(tag, obj, raw, unit) {
  return `<div class="extCard"><div class="tag">${tag}</div><div class="extValue">${fmtZ(obj?.z)}</div><div class="extMeta">${fmtPct(obj?.percentile)} · ${bandHr(obj?.band)}<br>${fmtValue(raw, unit)}</div></div>`;
}

const STYLE = `<style>
.extHead{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap}.extSummary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}.extCard{padding:13px 14px;border:1px solid #21384b;border-radius:12px;background:#08141e}.extCard .extValue{font-size:26px;font-weight:750;letter-spacing:-.02em;margin:5px 0}.extMeta{font-size:12px;color:#9db2c2;line-height:1.45}.extChart{width:100%;height:270px;display:block;overflow:visible}.guideGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.guideCard{padding:15px;border:1px solid #21384b;border-radius:12px;background:#08141e;line-height:1.55}.guideCard h3{margin:0 0 8px;font-size:15px}.guideCard p,.guideCard li{font-size:13px;color:#b6c7d3}.guideCard ul{margin:8px 0 0;padding-left:19px}.guideFlow{display:grid;grid-template-columns:repeat(6,1fr);gap:7px;margin:14px 0}.guideFlow>div{padding:10px 8px;border:1px solid #274156;border-radius:10px;text-align:center;font-size:11px;color:#b8c9d5}.guideWarn{padding:13px 14px;border:1px solid #4d5963;border-radius:10px;background:#0a151d;font-size:12px;color:#b9c9d4;line-height:1.55}@media(max-width:900px){.extSummary{grid-template-columns:repeat(2,1fr)}.guideFlow{grid-template-columns:repeat(3,1fr)}}@media(max-width:600px){.extSummary,.guideGrid{grid-template-columns:1fr}.guideFlow{grid-template-columns:repeat(2,1fr)}.extChart{height:240px}}
</style>`;

const GUIDE = `<section id="investorGuide" class="section">
<h2>Kako čitati GMLI — vodič za investitore</h2>
<p class="muted">GMLI je prvenstveno 3–12M liquidity/regime okvir. Ne pokušava predvidjeti svaki mjesečni pomak cijene i nijedan pojedinačni broj nije samostalni buy/sell signal.</p>
<div class="guideFlow"><div><b>1. MONEY</b><br>LEADING baseline</div><div><b>2. TRANSMISSION</b><br>asset-specific evidence</div><div><b>3. FUNDING</b><br>financial friction</div><div><b>4. FISCAL</b><br>policy context</div><div><b>5. MARKET</b><br>confirmation/divergence</div><div><b>6. RADAR</b><br>entry asymmetry</div></div>
<div class="guideGrid">
<div class="guideCard"><h3>Money Core [LEADING]</h3><p>Baseline globalne likvidnosti. USD-translated uključuje FX translation; FX-neutral pokušava izolirati underlying monetarnu ekspanziju. Viši score je povoljniji liquidity režim, ali score nije očekivani prinos.</p><ul><li><b>Level</b> govori koliko je Money rast snažan.</li><li><b>Accel3</b> govori ubrzava li se ili usporava taj rast.</li><li>Promovirani odnosi: SPY/QQQ — USD accel3 12M; GLD — FX-neutral accel3 12M; DBC — USD level 6M/12M i FX-neutral level 6M.</li></ul></div>
<div class="guideCard"><h3>Historical Extremes: z-score + percentile</h3><p>Z-score stavlja aktualnu vrijednost u vlastiti povijesni kontekst. Oko 0 je normalno; +1/-1 je povišeno odstupanje; iznad +2 ili ispod -2 je rijetko. Percentile je intuitivniji rang: 90th znači da je vrijednost viša od otprilike 90% opažanja u trailing prozoru.</p><ul><li>Visok <b>level z</b> = likvidnost je povijesno snažna.</li><li>Visok <b>accel3 z</b> = likvidnost se neuobičajeno brzo poboljšava.</li><li>Visok level + negativan accel3 = još dobro stanje, ali momentum likvidnosti slabi.</li></ul></div>
<div class="guideCard"><h3>Funding [REACTIVE_CONFIRMATION]</h3><p>Mjeri financijske uvjete i trenje kroz ANFCI, realni prinos, term premium i rezerve. Restrictive Funding znači da financijski uvjeti otežavaju prijenos likvidnosti. Reverse research pokazuje da equity/volatility stress često prethodi promjeni Fundinga, zato ga ne čitamo kao čist leading equity signal.</p><ul><li>Najkorisniji je za <b>conviction i risk sizing</b>.</li><li>Promovirana uska asset-veza ostaje DBC 6M/12M.</li><li>Supportive Funding ne može sam prepisati slab Money Core.</li></ul></div>
<div class="guideCard"><h3>Fiscal V2 [MIXED]</h3><p>Kombinira deficit/GDP level i 12M fiscal impulse kroz vlastite rolling z-scoreove. Koristan je kao policy/context overlay, ali temporalni direction nije dovoljno čist da bude Core.</p><ul><li>&lt;40 restrictive, 40–60 neutral, &gt;60 supportive.</li><li>Fiksni SPY 12M usefulness gate je prošao.</li><li>Automatska težina u 10-point convictionu ostaje <b>0</b>.</li></ul></div>
<div class="guideCard"><h3>Market Confirmation [REACTIVE_CONFIRMATION]</h3><p>SPY/QQQ/GLD/DBC price structure pokazuje potvrđuje li tržište upstream liquidity priču. Dobar Money uz slabu tržišnu potvrdu nije isto što i dobar Money uz široku potvrdu.</p><ul><li>Koristi za razlikovanje <b>thesis</b> od <b>timinga</b>.</li><li>Divergencija često znači strpljenje, postupno pozicioniranje ili manji risk.</li><li>Radar je zaseban RESEARCH sloj za SETUP/EARLY/CONFIRMED/MATURE faze.</li></ul></div>
<div class="guideCard"><h3>Conviction 0–10</h3><p>Conviction nije probability forecast ni očekivani return. Ocjenjuje freshness i slaganje Moneyja, transmissiona, Fundinga i tržišne potvrde. Fiscal i Historical Extremes trenutno ne dodaju automatske bodove.</p><ul><li>Viši conviction = više međusobno usklađenih dokaza.</li><li>Niski conviction = više konflikata ili slabija svježina.</li><li>Uvijek čitaj zajedno s asset-specific transmissionom.</li></ul></div>
<div class="guideCard"><h3>Potencijalna primjena u portfelju</h3><p>GMLI je najkorisniji za <b>allocation/risk bias</b>, ne za precizan entry.</p><ul><li>Supportive Money + pozitivna transmisija + potvrda može opravdati veći interes za odgovarajući risk asset.</li><li>Supportive Money uz restrictive Funding ili slabu potvrdu sugerira više selektivnosti i postupno pozicioniranje.</li><li>Slabljenje Money impulsa dok je tržište euforično može biti razlog da se ne chasea i da se strože upravlja rizikom.</li><li>Ekstremni z-score je kontekst za asimetriju; ekstrem sam po sebi nije contrarian signal.</li></ul></div>
<div class="guideCard"><h3>Što ovaj dashboard ne tvrdi</h3><p>Promovirani odnosi su empirijske forward veze pod frozen pravilima, a ne dokazi strukturne uzročnosti. Funding/Fiscal history koristi definirane availability lagove; dio istraživačke povijesti temelji se na revidiranim javnim serijama.</p><ul><li>Ne koristi score kao očekivani % prinosa.</li><li>Ne tretiraj z &gt; 2 kao automatski short niti z &lt; -2 kao automatski long.</li><li>Ne generaliziraj SPY/QQQ/GLD/DBC odnose na sve assete.</li></ul></div>
</div>
<div class="guideWarn"><b>Praktični redoslijed:</b> prvo Money režim → zatim promovirani asset transmission → Funding/Fiscal kontekst → market confirmation → Historical Extremes kao kontekst → Radar za entry asymmetry. Time se izbjegava da zanimljiv sekundarni indikator nadglasa frozen Core.</div>
</section>`;

function req(html, old, replacement, label) {
  if (!html.includes(old)) throw new Error(`Pages extremes/guide marker missing: ${label}`);
  return html.replace(old, replacement);
}

export function enhanceExtremesGuide(input, data) {
  const l = data.latest;
  const levelChart = zChart(data.rows, [
    { key: 'usd_level_z', color: '#64b5f6' },
    { key: 'fx_neutral_level_z', color: '#81c784' }
  ], 'moneyLevelZChart');
  const accelChart = zChart(data.rows, [
    { key: 'usd_accel3_z', color: '#64b5f6' },
    { key: 'fx_neutral_accel3_z', color: '#81c784' }
  ], 'moneyAccelZChart');
  const section = `<section id="moneyExtremes" class="section">
<div class="extHead"><div><h2>Money Historical Extremes <span class="info" title="RESEARCH diagnostic. Rolling 120M z-score i percentile koriste samo podatke dostupne do svakog mjeseca; ne mijenjaju Money Core ili conviction.">i</span></h2><p class="muted">Koliko su današnji Money level i 3M impuls neuobičajeni u odnosu na vlastitu povijest.</p></div><div class="tag">LATEST ${l.month} · available ${l.available_date}</div></div>
<div class="extSummary">${summaryCard('USD LEVEL Z', l.usd_level, l.usd_level.value_pct, '% YoY')}${summaryCard('FX-NEUTRAL LEVEL Z', l.fx_neutral_level, l.fx_neutral_level.value_pct, '% YoY')}${summaryCard('USD ACCEL3 Z', l.usd_accel3, l.usd_accel3.value_pp, ' pp / 3M')}${summaryCard('FX-NEUTRAL ACCEL3 Z', l.fx_neutral_accel3, l.fx_neutral_accel3.value_pp, ' pp / 3M')}</div>
<div class="chartGrid"><article class="card"><div class="tag">Money level z-score · zadnjih 5Y</div><div class="legend"><span style="--c:#64b5f6">USD YoY level</span><span style="--c:#81c784">FX-neutral YoY level</span></div><div class="chartBox">${levelChart}</div><div class="sourceNote">0 = trailing prosjek; ±1 = povišeno odstupanje; ±2 = povijesno neuobičajeno. Z-score nije forecast prinosa.</div></article><article class="card"><div class="tag">Money accel3 z-score · zadnjih 5Y</div><div class="legend"><span style="--c:#64b5f6">USD accel3</span><span style="--c:#81c784">FX-neutral accel3</span></div><div class="chartBox">${accelChart}</div><div class="sourceNote">Accel3 = promjena YoY rasta u 3 mjeseca. Pozitivan ekstrem znači snažno ubrzavanje, negativan snažno usporavanje.</div></article></div>
<div class="sourceNote">Method: trailing 120M, minimum 36M, population SD (ddof=0), bez clippinga i bez look-aheada. Percentile je mid-rank unutar istog trailing prozora. Evidence tier: RESEARCH_DIAGNOSTIC; scoring effect: NONE. <a href="./api/money-extremes.json">Full diagnostic history</a>.</div>
</section>`;

  let html = input;
  html = req(html, '</head>', `${STYLE}\n</head>`, 'head');
  html = req(html, '<a href="#moneyTrend">MONEY TREND</a>', '<a href="#moneyTrend">MONEY TREND</a><a href="#moneyExtremes">EXTREMES</a>', 'money nav');
  html = req(html, '</nav>', '<a href="#investorGuide">GUIDE</a></nav>', 'guide nav');
  html = req(html, '<section id="market"', `${section}\n<section id="market"`, 'extremes section');
  html = req(html, '</main>', `${GUIDE}\n</main>`, 'investor guide');
  return html;
}
