export function enhanceSignalRoleUi(html) {
  const style = `<style>
.contextChain{font-size:18px;line-height:1.35}.contextRole{margin-top:7px;font-size:11px;color:#8fb1c9;text-transform:uppercase;letter-spacing:.06em}.contextNote{margin-top:5px;font-size:12px;color:#9fb1c1;line-height:1.45}.contextHistoryHead{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-top:18px}.contextHistoryHead h3{margin:0 0 4px}.contextRangeBtns{display:flex;gap:6px}.contextRangeBtn{background:#0b1722;border:1px solid #2c455a;color:#b9ccda;border-radius:999px;padding:6px 11px;font-size:12px;cursor:pointer}.contextRangeBtn.active{background:#18324a;color:#fff;border-color:#5f87a7}.contextHistoryGrid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.contextHistoryGrid .marketWide{grid-column:1/-1}.contextChartBox{position:relative;min-height:230px}.contextChart{width:100%;height:230px;display:block;overflow:visible}.contextTip{position:absolute;display:none;pointer-events:none;background:#06111a;border:1px solid #38536a;border-radius:9px;padding:8px 10px;font-size:12px;line-height:1.45;box-shadow:0 8px 28px rgba(0,0,0,.35);z-index:3;min-width:165px}.contextLegend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:#a9bdcc;margin:6px 0}.contextLegend span:before{content:'';display:inline-block;width:15px;height:3px;border-radius:3px;margin-right:6px;vertical-align:3px;background:var(--c)}@media(max-width:900px){.contextHistoryGrid{grid-template-columns:1fr}.contextHistoryGrid .marketWide{grid-column:auto}}@media(max-width:520px){.contextChart,.contextChartBox{height:210px;min-height:210px}}
</style>`;

  const section = `<section id="contextLayers" class="section"><h2>Context Layers</h2><p class="muted">Upstream signal i confirmation slojevi su odvojeni. Ovaj blok ne mijenja frozen 10-point scoring.</p><div class="grid">
<article class="card"><div class="tag">FUNDING</div><div class="score" id="contextFundingScore">…</div><div class="contextRole" id="contextFundingRole"></div><div class="contextNote" id="contextFundingMeta"></div></article>
<article class="card"><div class="tag">FISCAL V2</div><div class="score" id="contextFiscalScore">…</div><div class="contextRole" id="contextFiscalRole"></div><div class="contextNote" id="contextFiscalMeta"></div></article>
<article class="card"><div class="tag">SIGNAL ROLE CHAIN</div><div class="score contextChain" id="contextRoles">…</div><div class="contextRole">INTERPRETATION ONLY · SCORE EFFECT NONE</div><div class="contextNote" id="contextRolesMeta"></div></article>
<article class="card"><div class="tag">MARKET CONFIRMATION</div><div class="score" id="contextMarketScore">…</div><div class="contextRole" id="contextMarketRole"></div><div class="contextNote" id="contextMarketMeta"></div></article>
</div>
<div class="contextHistoryHead"><div><h3>Context History</h3><div class="muted small">Funding i Fiscal koriste vlastite verificirane history serije. Market je completed-month RESEARCH confirmation. Signal Role Chain nema synthetic history jer nije numeric score.</div></div><div class="contextRangeBtns"><button class="contextRangeBtn" data-context-range="3Y">3Y</button><button class="contextRangeBtn active" data-context-range="5Y">5Y</button><button class="contextRangeBtn" data-context-range="MAX">MAX</button></div></div>
<div class="contextHistoryGrid">
<article class="card"><div class="tag">FUNDING HISTORY · 0–100</div><div class="contextLegend"><span style="--c:#64b5f6">Effective</span><span style="--c:#81c784">Structural</span><span style="--c:#ffb74d">Observed conditions</span></div><div class="contextChartBox"><svg class="contextChart" id="contextFundingHistoryChart" viewBox="0 0 920 230" preserveAspectRatio="none"></svg><div class="contextTip" id="contextFundingHistoryTip"></div></div><div class="contextNote">40/60 su regime granice. Effective score je production Funding V2; ostale linije objašnjavaju cap između structural supporta i observed conditions.</div></article>
<article class="card"><div class="tag">FISCAL V2 HISTORY · 0–100</div><div class="contextLegend"><span style="--c:#ab86ff">Fiscal score</span></div><div class="contextChartBox"><svg class="contextChart" id="contextFiscalHistoryChart" viewBox="0 0 920 230" preserveAspectRatio="none"></svg><div class="contextTip" id="contextFiscalHistoryTip"></div></div><div class="contextNote">40/60 su RESTRICTIVE / NEUTRAL / SUPPORTIVE granice. Povijest koristi revised FRED + frozen publication lags, ne exact historical release-time vintages.</div></article>
<article class="card marketWide"><div class="tag">COMPLETED-MONTH MARKET CONFIRMATION HISTORY · 0–4 POSITIVE ASSETS</div><div class="contextLegend"><span style="--c:#4dd0e1">Positive SPY/QQQ/GLD/DBC</span></div><div class="contextChartBox"><svg class="contextChart" id="contextMarketHistoryChart" viewBox="0 0 920 230" preserveAspectRatio="none"></svg><div class="contextTip" id="contextMarketHistoryTip"></div></div><div class="contextNote">3–4 positive assets = rubric 2/2; 2 = 1/2; 0–1 = 0/2. Ovo je structural completed-month confirmation, ne današnji daily market snapshot.</div></article>
</div><div class="sourceNote">Context history snapshot: <a href="./api/context-history.json">./api/context-history.json</a></div></section>\n`;

  const script = `<script>
(()=>{
  const el=id=>document.getElementById(id);
  const score=x=>Number.isFinite(Number(x))?Number(x).toFixed(1):'—';
  const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
  let contextHistory=null;
  let contextRange='5Y';

  function renderCards(report){
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
  }

  function rangeRows(rows){
    const n=contextRange==='3Y'?36:contextRange==='5Y'?60:rows.length;
    return rows.slice(Math.max(0,rows.length-n));
  }

  function linePath(rows,key,x,y){
    let d=''; let started=false;
    rows.forEach((r,i)=>{
      const v=Number(r[key]);
      if(!Number.isFinite(v)){started=false;return;}
      d+=(started?' L ':'M ')+x(i)+' '+y(v); started=true;
    });
    return d;
  }

  function renderChart(svgId,tipId,rawRows,series,yMin,yMax,thresholds){
    const svg=el(svgId); const tip=el(tipId); if(!svg||!tip)return;
    const rows=rangeRows(rawRows||[]); const W=920,H=230,L=46,R=12,T=12,B=28;
    if(rows.length<2){svg.innerHTML='<text x="46" y="40" fill="#9fb1c1">No history</text>';return;}
    const x=i=>L+(W-L-R)*(i/(rows.length-1));
    const y=v=>T+(H-T-B)*(1-(v-yMin)/(yMax-yMin));
    const parts=[];
    for(let i=0;i<=4;i++){
      const v=yMin+(yMax-yMin)*i/4; const yy=y(v);
      parts.push('<line x1="'+L+'" y1="'+yy+'" x2="'+(W-R)+'" y2="'+yy+'" stroke="#1d3142" stroke-width="1"/>');
      parts.push('<text x="'+(L-7)+'" y="'+(yy+4)+'" fill="#7890a3" font-size="10" text-anchor="end">'+Number(v.toFixed(0))+'</text>');
    }
    (thresholds||[]).forEach(t=>{
      const yy=y(t); parts.push('<line x1="'+L+'" y1="'+yy+'" x2="'+(W-R)+'" y2="'+yy+'" stroke="#587187" stroke-width="1" stroke-dasharray="5 5"/>');
    });
    const ticks=4;
    for(let i=0;i<=ticks;i++){
      const idx=Math.min(rows.length-1,Math.round(i*(rows.length-1)/ticks));
      parts.push('<text x="'+x(idx)+'" y="'+(H-7)+'" fill="#7890a3" font-size="10" text-anchor="middle">'+esc(rows[idx].observation_month||rows[idx].month||'')+'</text>');
    }
    series.forEach(s=>{
      const d=linePath(rows,s.key,x,y); if(d) parts.push('<path d="'+d+'" fill="none" stroke="'+s.color+'" stroke-width="2.2" vector-effect="non-scaling-stroke"/>');
    });
    svg.innerHTML=parts.join('');
    svg.onpointermove=ev=>{
      const rect=svg.getBoundingClientRect();
      const ratio=Math.max(0,Math.min(1,(ev.clientX-rect.left)/rect.width));
      const idx=Math.round(ratio*(rows.length-1)); const row=rows[idx];
      const lines=series.map(s=>s.label+': '+(Number.isFinite(Number(row[s.key]))?Number(row[s.key]).toFixed(1):'—'));
      tip.innerHTML='<b>'+esc(row.observation_month||row.month||'')+'</b><br>'+lines.map(esc).join('<br>');
      tip.style.display='block';
      const left=Math.min(rect.width-180,Math.max(0,ev.clientX-rect.left+12));
      tip.style.left=left+'px'; tip.style.top='16px';
    };
    svg.onpointerleave=()=>{tip.style.display='none';};
  }

  function renderHistory(){
    if(!contextHistory)return;
    renderChart('contextFundingHistoryChart','contextFundingHistoryTip',contextHistory.funding?.rows||[],[
      {key:'score',label:'Effective',color:'#64b5f6'},
      {key:'structural_support_score',label:'Structural',color:'#81c784'},
      {key:'observed_conditions_score',label:'Observed conditions',color:'#ffb74d'}
    ],0,100,[40,60]);
    renderChart('contextFiscalHistoryChart','contextFiscalHistoryTip',contextHistory.fiscal?.rows||[],[
      {key:'score',label:'Fiscal score',color:'#ab86ff'}
    ],0,100,[40,60]);
    renderChart('contextMarketHistoryChart','contextMarketHistoryTip',contextHistory.market_confirmation?.rows||[],[
      {key:'positive',label:'Positive assets',color:'#4dd0e1'}
    ],0,4,[2,3]);
  }

  document.querySelectorAll('[data-context-range]').forEach(btn=>btn.addEventListener('click',()=>{
    contextRange=btn.dataset.contextRange;
    document.querySelectorAll('[data-context-range]').forEach(b=>b.classList.toggle('active',b===btn));
    renderHistory();
  }));

  Promise.all([
    fetch('./api/report.json',{cache:'no-store'}).then(r=>r.json()),
    fetch('./api/context-history.json',{cache:'no-store'}).then(r=>r.json())
  ]).then(([report,history])=>{
    renderCards(report); contextHistory=history; renderHistory();
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
