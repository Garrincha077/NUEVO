export function enhanceSignalRoleUi(html) {
  const style = `<style>
.contextChain{font-size:18px;line-height:1.35}.contextRole{margin-top:7px;font-size:11px;color:#8fb1c9;text-transform:uppercase;letter-spacing:.06em}.contextNote{margin-top:5px;font-size:12px;color:#9fb1c1;line-height:1.45}
</style>`;

  const section = `<section id="contextLayers" class="section"><h2>Context Layers</h2><p class="muted">Upstream signal i confirmation slojevi su odvojeni. Ovaj blok ne mijenja frozen 10-point scoring.</p><div class="grid">
<article class="card"><div class="tag">FUNDING</div><div class="score" id="contextFundingScore">…</div><div class="contextRole" id="contextFundingRole"></div><div class="contextNote" id="contextFundingMeta"></div></article>
<article class="card"><div class="tag">FISCAL V2</div><div class="score" id="contextFiscalScore">…</div><div class="contextRole" id="contextFiscalRole"></div><div class="contextNote" id="contextFiscalMeta"></div></article>
<article class="card"><div class="tag">SIGNAL ROLE CHAIN</div><div class="score contextChain" id="contextRoles">…</div><div class="contextRole">INTERPRETATION ONLY · SCORE EFFECT NONE</div><div class="contextNote" id="contextRolesMeta"></div></article>
<article class="card"><div class="tag">MARKET CONFIRMATION</div><div class="score" id="contextMarketScore">…</div><div class="contextRole" id="contextMarketRole"></div><div class="contextNote" id="contextMarketMeta"></div></article>
</div></section>\n`;

  const script = `<script>
(()=>{
  const el=id=>document.getElementById(id);
  const score=x=>Number.isFinite(Number(x))?Number(x).toFixed(1):'—';
  fetch('./api/report.json',{cache:'no-store'}).then(r=>r.json()).then(report=>{
    const inf=report?.regime?.current_research_inference||{};
    const roles=report?.signal_role_taxonomy||{};
    const conviction=report?.regime?.conviction||{};
    const funding=inf.funding||{};
    const fiscal=inf.fiscal||{};
    const market=report?.current_market_confirmation||{};
    const structural=inf.structural_market_confirmation||{};

    el('contextFundingScore').textContent=score(funding.score);
    el('contextFundingRole').textContent=(roles.funding_v2?.role||'REACTIVE_CONFIRMATION').replaceAll('_',' ');
    el('contextFundingMeta').textContent=(funding.regime||'—')+' · bounded confirmation; ne prepisuje Money Core';

    el('contextFiscalScore').textContent=score(fiscal.score);
    el('contextFiscalRole').textContent=(roles.fiscal_v2?.role||'MIXED').replaceAll('_',' ');
    el('contextFiscalMeta').textContent=(fiscal.regime||'—')+' · automatic conviction weight '+String(conviction.fiscal_v2_automatic_weight??0);

    el('contextRoles').textContent='Money → Funding → Fiscal → Market';
    el('contextRolesMeta').textContent=(roles.money_core?.role||'LEADING')+' → '+(roles.funding_v2?.role||'REACTIVE_CONFIRMATION')+' → '+(roles.fiscal_v2?.role||'MIXED')+' → '+(roles.market_confirmation?.role||'REACTIVE_CONFIRMATION');

    const total=Object.keys(market.assets||{}).length||market.coverage?.split('/')?.[1]||'—';
    el('contextMarketScore').textContent=String(market.positive??'—')+'/'+String(total);
    el('contextMarketRole').textContent=(roles.market_confirmation?.role||'REACTIVE_CONFIRMATION').replaceAll('_',' ');
    el('contextMarketMeta').textContent=(market.summary||'—')+' · structural '+String(structural.positive??'—')+'/'+String(structural.total??'—');
  }).catch(err=>{
    for(const id of ['contextFundingMeta','contextFiscalMeta','contextRolesMeta','contextMarketMeta']) if(el(id)) el(id).textContent='Snapshot unavailable: '+err.message;
  });
})();
</script>`;

  return html
    .replace('</head>', style + '\n</head>')
    .replace('<a href="#now">REGIME</a>', '<a href="#now">REGIME</a><a href="#contextLayers">CONTEXT</a>')
    .replace('<section id="moneyTrend"', section + '<section id="moneyTrend"')
    .replace('</body>', script + '\n</body>');
}
