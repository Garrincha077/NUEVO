(() => {
  'use strict';

  if (document.getElementById('contextLayers') && document.getElementById('moneyExtremes') && document.getElementById('investorGuide')) return;

  const $ = id => document.getElementById(id);
  const num = v => Number.isFinite(Number(v)) ? Number(v) : null;
  const score = v => num(v) == null ? '—' : num(v).toFixed(1);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));

  function addStyle(text, key) {
    if (!text || document.querySelector(`style[data-gmli-parity="${key}"]`)) return;
    const style = document.createElement('style');
    style.dataset.gmliParity = key;
    style.textContent = text;
    document.head.appendChild(style);
  }

  function parseCsv(text) {
    const lines = String(text || '').trim().split(/\r?\n/).filter(Boolean);
    if (lines.length < 2) return [];
    const headers = lines[0].split(',');
    return lines.slice(1).map(line => {
      const cells = line.split(',');
      return Object.fromEntries(headers.map((h, i) => [h, cells[i] ?? '']));
    });
  }

  function ensureNavLink(href, label, beforeHref) {
    const nav = document.querySelector('.nav');
    if (!nav || nav.querySelector(`a[href="${href}"]`)) return;
    const a = document.createElement('a');
    a.href = href;
    a.textContent = label;
    const before = beforeHref ? nav.querySelector(`a[href="${beforeHref}"]`) : null;
    if (before) nav.insertBefore(a, before); else nav.appendChild(a);
  }

  function installInfoDelegation() {
    if (document.documentElement.dataset.gmliParityInfo === '1') return;
    document.documentElement.dataset.gmliParityInfo = '1';
    const getPop = () => {
      let pop = $('infoPopover');
      if (!pop) {
        document.body.insertAdjacentHTML('beforeend', '<div id="infoPopover" class="infoPopover" role="status" aria-live="polite"><button id="infoPopoverClose" class="infoPopoverClose" aria-label="Zatvori">×</button><div id="infoPopoverText"></div></div>');
        pop = $('infoPopover');
        $('infoPopoverClose').onclick = () => pop.classList.remove('show');
      }
      return pop;
    };
    const show = el => {
      const msg = el?.getAttribute?.('title');
      if (!msg) return;
      const pop = getPop();
      $('infoPopoverText').textContent = msg;
      pop.classList.add('show');
    };
    document.addEventListener('click', e => {
      const info = e.target.closest?.('.info');
      if (info) { e.preventDefault(); e.stopPropagation(); show(info); return; }
      const pop = $('infoPopover');
      if (pop?.classList.contains('show') && !pop.contains(e.target)) pop.classList.remove('show');
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') $('infoPopover')?.classList.remove('show');
      const info = e.target.closest?.('.info');
      if (info && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); show(info); }
    });
    document.querySelectorAll('.info').forEach(el => { el.tabIndex = 0; el.setAttribute('role','button'); el.setAttribute('aria-label','Više informacija'); });
  }

  function contextRangeRows(rows, range) {
    const n = range === '3Y' ? 36 : range === '5Y' ? 60 : rows.length;
    return rows.slice(Math.max(0, rows.length - n));
  }

  function contextLinePath(rows, key, x, y) {
    let d = '', started = false;
    rows.forEach((r, i) => {
      const v = Number(r[key]);
      if (!Number.isFinite(v)) { started = false; return; }
      d += (started ? ' L ' : 'M ') + x(i) + ' ' + y(v);
      started = true;
    });
    return d;
  }

  function drawContextChart(svgId, tipId, rawRows, series, yMin, yMax, thresholds, range) {
    const svg = $(svgId), tip = $(tipId);
    if (!svg || !tip) return;
    const rows = contextRangeRows(rawRows || [], range);
    const W = 920, H = 230, L = 46, R = 12, T = 12, B = 28;
    if (rows.length < 2) { svg.innerHTML = '<text x="46" y="40" fill="#9fb1c1">No history</text>'; return; }
    const x = i => L + (W-L-R) * (i/(rows.length-1));
    const y = v => T + (H-T-B) * (1-(v-yMin)/(yMax-yMin));
    const parts = [];
    for (let i=0;i<=4;i++) {
      const v = yMin + (yMax-yMin)*i/4, yy = y(v);
      parts.push(`<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" stroke="#1d3142" stroke-width="1"/>`);
      parts.push(`<text x="${L-7}" y="${yy+4}" fill="#7890a3" font-size="10" text-anchor="end">${Number(v.toFixed(0))}</text>`);
    }
    (thresholds || []).forEach(t => parts.push(`<line x1="${L}" y1="${y(t)}" x2="${W-R}" y2="${y(t)}" stroke="#587187" stroke-width="1" stroke-dasharray="5 5"/>`));
    for (let i=0;i<=4;i++) {
      const idx = Math.min(rows.length-1, Math.round(i*(rows.length-1)/4));
      parts.push(`<text x="${x(idx)}" y="${H-7}" fill="#7890a3" font-size="10" text-anchor="middle">${esc(rows[idx].observation_month || rows[idx].month || '')}</text>`);
    }
    series.forEach(s => {
      const d = contextLinePath(rows, s.key, x, y);
      if (d) parts.push(`<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2.2" vector-effect="non-scaling-stroke"/>`);
    });
    svg.innerHTML = parts.join('');
    svg.onpointermove = ev => {
      const rect = svg.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (ev.clientX-rect.left)/rect.width));
      const row = rows[Math.round(ratio*(rows.length-1))];
      const lines = series.map(s => `${s.label}: ${Number.isFinite(Number(row[s.key])) ? Number(row[s.key]).toFixed(1) : '—'}`);
      tip.innerHTML = `<b>${esc(row.observation_month || row.month || '')}</b><br>${lines.map(esc).join('<br>')}`;
      tip.style.display = 'block';
      tip.style.left = Math.min(rect.width-180, Math.max(0, ev.clientX-rect.left+12)) + 'px';
      tip.style.top = '16px';
    };
    svg.onpointerleave = () => { tip.style.display = 'none'; };
  }

  function renderContextCards(report) {
    const inf = report?.regime?.current_research_inference || {};
    const roles = report?.signal_role_taxonomy || {};
    const conviction = report?.regime?.conviction || {};
    const funding = inf.funding || {}, fiscal = inf.fiscal || {};
    const market = report?.current_market_confirmation || {};
    const structural = inf.structural_market_confirmation || {};
    if ($('contextFundingScore')) $('contextFundingScore').textContent = score(funding.score);
    if ($('contextFundingRole')) $('contextFundingRole').textContent = (roles.funding_v2?.role || 'REACTIVE_CONFIRMATION').replaceAll('_',' ');
    if ($('contextFundingMeta')) $('contextFundingMeta').textContent = (funding.regime || '—') + ' · bounded confirmation; ne prepisuje Money Core';
    if ($('contextFiscalScore')) $('contextFiscalScore').textContent = score(fiscal.score);
    if ($('contextFiscalRole')) $('contextFiscalRole').textContent = (roles.fiscal_v2?.role || 'MIXED').replaceAll('_',' ');
    if ($('contextFiscalMeta')) $('contextFiscalMeta').textContent = (fiscal.regime || '—') + ' · automatic conviction weight ' + String(conviction.fiscal_v2_automatic_weight ?? 0);
    if ($('contextRoles')) $('contextRoles').textContent = 'Money → Funding → Fiscal → Market';
    if ($('contextRolesMeta')) $('contextRolesMeta').textContent = (roles.money_core?.role || 'LEADING') + ' → ' + (roles.funding_v2?.role || 'REACTIVE_CONFIRMATION') + ' → ' + (roles.fiscal_v2?.role || 'MIXED') + ' → ' + (roles.market_confirmation?.role || 'REACTIVE_CONFIRMATION');
    const total = Object.keys(market.assets || {}).length || market.coverage?.split('/')?.[1] || '—';
    if ($('contextMarketScore')) $('contextMarketScore').textContent = String(market.positive ?? '—') + '/' + String(total);
    if ($('contextMarketRole')) $('contextMarketRole').textContent = (roles.market_confirmation?.role || 'REACTIVE_CONFIRMATION').replaceAll('_',' ');
    if ($('contextMarketMeta')) $('contextMarketMeta').textContent = (market.summary || '—') + ' · structural ' + String(structural.positive ?? '—') + '/' + String(structural.total ?? '—');
  }

  function renderContextHistory(history) {
    let range = '5Y';
    const render = () => {
      drawContextChart('contextFundingHistoryChart','contextFundingHistoryTip',history?.funding?.rows || [],[
        {key:'score',label:'Effective',color:'#64b5f6'},
        {key:'structural_support_score',label:'Structural',color:'#81c784'},
        {key:'observed_conditions_score',label:'Observed conditions',color:'#ffb74d'}
      ],0,100,[40,60],range);
      drawContextChart('contextFiscalHistoryChart','contextFiscalHistoryTip',history?.fiscal?.rows || [],[
        {key:'score',label:'Fiscal score',color:'#ab86ff'}
      ],0,100,[40,60],range);
      drawContextChart('contextMarketHistoryChart','contextMarketHistoryTip',history?.market_confirmation?.rows || [],[
        {key:'positive',label:'Positive assets',color:'#4dd0e1'}
      ],0,4,[2,3],range);
    };
    document.querySelectorAll('[data-context-range]').forEach(btn => btn.addEventListener('click', () => {
      range = btn.dataset.contextRange;
      document.querySelectorAll('[data-context-range]').forEach(b => b.classList.toggle('active', b === btn));
      render();
    }));
    render();
  }

  async function canonicalSections(report, moneyHistory) {
    const [roleMod, extMod] = await Promise.all([
      import('/scripts/pages-signal-role-ui.mjs'),
      import('/scripts/pages-extremes-guide.mjs')
    ]);

    const contextDummy = '<!doctype html><html><head></head><body><main><nav class="nav"><a href="#now">REGIME</a><a href="#moneyTrend">MONEY TREND</a></nav><section id="moneyTrend"></section></main></body></html>';
    const contextHtml = roleMod.enhanceSignalRoleUi(contextDummy);
    const contextDoc = new DOMParser().parseFromString(contextHtml, 'text/html');
    contextDoc.querySelectorAll('style').forEach((s, i) => addStyle(s.textContent, `context-${i}`));
    const contextSection = contextDoc.getElementById('contextLayers');
    if (contextSection) {
      const source = contextSection.querySelector('.sourceNote a');
      if (source) { source.href = '/api/context-history'; source.textContent = '/api/context-history'; }
    }

    const extremes = extMod.buildMoneyExtremes(moneyHistory);
    const extDummy = '<!doctype html><html><head></head><body><main><nav class="nav"><a href="#moneyTrend">MONEY TREND</a></nav><section id="market"></section></main></body></html>';
    const extHtml = extMod.enhanceExtremesGuide(extDummy, extremes);
    const extDoc = new DOMParser().parseFromString(extHtml, 'text/html');
    extDoc.querySelectorAll('style').forEach((s, i) => addStyle(s.textContent, `extremes-${i}`));
    const extremesSection = extDoc.getElementById('moneyExtremes');
    const guideSection = extDoc.getElementById('investorGuide');
    if (extremesSection) {
      const source = extremesSection.querySelector('.sourceNote a');
      if (source) { source.href = '/api/money-extremes'; source.textContent = 'Full diagnostic history'; }
    }
    return { contextSection, extremesSection, guideSection };
  }

  async function initParity() {
    try {
      const moneyTrend = $('moneyTrend');
      const market = $('market');
      const main = document.querySelector('main');
      if (!moneyTrend || !market || !main) return;

      const [report, moneyHistory, contextHistory] = await Promise.all([
        fetch('/api/report', {cache:'no-store'}).then(r => { if(!r.ok) throw new Error('report '+r.status); return r.json(); }),
        fetch('/api/history', {cache:'no-store'}).then(r => { if(!r.ok) throw new Error('history '+r.status); return r.json(); }),
        fetch('/api/context-history', {cache:'no-store'}).then(r => { if(!r.ok) throw new Error('context-history '+r.status); return r.json(); })
      ]);

      const { contextSection, extremesSection, guideSection } = await canonicalSections(report, moneyHistory);
      if (contextSection && !$('contextLayers')) moneyTrend.insertAdjacentElement('beforebegin', contextSection);
      if (extremesSection && !$('moneyExtremes')) market.insertAdjacentElement('beforebegin', extremesSection);
      if (guideSection && !$('investorGuide')) main.appendChild(guideSection);

      ensureNavLink('#contextLayers','CONTEXT','#moneyTrend');
      ensureNavLink('#moneyExtremes','EXTREMES','#market');
      ensureNavLink('#investorGuide','GUIDE',null);

      renderContextCards(report);
      renderContextHistory(contextHistory);
      installInfoDelegation();
      document.querySelectorAll('.info').forEach(el => { el.tabIndex = 0; el.setAttribute('role','button'); el.setAttribute('aria-label','Više informacija'); });
      document.documentElement.dataset.gmliUiParity = 'pages-live-v1';
    } catch (e) {
      console.error('GMLI Pages/Vercel UI parity failed', e);
    }
  }

  initParity();
})();
