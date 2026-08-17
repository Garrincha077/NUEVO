import fs from 'node:fs';

const UNIVERSE = {
  SPY:'SPY', QQQ:'QQQ', IWM:'IWM', GLD:'GLD', SLV:'SLV', DBC:'DBC', USO:'USO', CPER:'CPER', DBA:'DBA',
  TLT:'TLT', IEF:'IEF', FXY:'FXY', HYG:'HYG', VNQ:'VNQ', EEM:'EEM', VEA:'VEA', BTC:'BTC-USD'
};
const H=[3,6,12];

const ym = d => `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}`;
function mean(xs){const a=xs.filter(Number.isFinite);return a.length?a.reduce((s,x)=>s+x,0)/a.length:null;}
function median(xs){const a=xs.filter(Number.isFinite).sort((a,b)=>a-b);if(!a.length)return null;const m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;}
function sd(xs){const a=xs.filter(Number.isFinite);if(a.length<2)return null;const m=mean(a);return Math.sqrt(a.reduce((s,x)=>s+(x-m)**2,0)/(a.length-1));}
function fmt(x,d=1){return x==null?null:Number(x.toFixed(d));}

async function yahooMax(sym){
  const url=`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?range=max&interval=1mo&events=history`;
  const r=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 GMLI-price-backtest/1.0'}});
  if(!r.ok) throw new Error(`Yahoo ${sym} ${r.status}`);
  const j=await r.json(); const z=j.chart?.result?.[0]; if(!z) throw new Error(`Yahoo ${sym} empty`);
  const ts=z.timestamp||[], adj=z.indicators?.adjclose?.[0]?.adjclose||[], close=z.indicators?.quote?.[0]?.close||[];
  const by=new Map();
  for(let i=0;i<ts.length;i++){const k=ym(new Date(ts[i]*1000));const v=Number.isFinite(adj[i])?adj[i]:close[i];if(Number.isFinite(v)&&v>0)by.set(k,v);}
  const months=[...by.keys()].sort(); return {months,values:months.map(k=>by.get(k))};
}

function rollingZ(v,i,window=60){
  if(i+1<window)return null;const w=v.slice(i-window+1,i+1).map(Math.log);const m=mean(w),s=sd(w);return s>0?(w.at(-1)-m)/s:null;
}
function stageAt(v,i){
  if(i<12)return null;
  const last=v[i];
  const ma10=mean(v.slice(i-9,i+1));
  const prior10=mean(v.slice(i-12,i-2));
  const r3=last/v[i-3]-1;
  const slope=ma10/prior10-1;
  if(last>ma10&&r3>0&&slope>0)return'CONFIRMED_UP';
  if(r3>0)return'EARLY_UP';
  if(last<ma10&&r3<0&&slope<0)return'CONFIRMED_DOWN';
  if(r3<0)return'EARLY_DOWN';
  return'MIXED';
}
function relSeries(p,b){
  const bm=new Map(b.months.map((m,i)=>[m,b.values[i]]));const months=[],values=[];
  for(let i=0;i<p.months.length;i++){const bv=bm.get(p.months[i]);if(Number.isFinite(bv)&&bv>0){months.push(p.months[i]);values.push(p.values[i]/bv);}}
  return{months,values};
}
function forwardRet(v,i,h){return i+h<v.length?v[i+h]/v[i]-1:null;}
function eventStarts(flags){const out=[];for(let i=0;i<flags.length;i++)if(flags[i]&&!(i>0&&flags[i-1]))out.push(i);return out;}
function stats(events,side='LONG'){
  const out={n:events.length};
  for(const h of H){const r=events.map(e=>e[`r${h}`]).filter(Number.isFinite);const signed=side==='SHORT'?r.map(x=>-x):r;out[`${h}m`]={n:r.length,mean_pct:fmt(100*mean(signed)),median_pct:fmt(100*median(signed)),hit_rate_pct:r.length?fmt(100*signed.filter(x=>x>0).length/r.length):null};}
  return out;
}

const prices={};
for(const [k,s] of Object.entries(UNIVERSE)){
  try{prices[k]=await yahooMax(s);console.log(`FETCH ${k} ${prices[k].months[0]}..${prices[k].months.at(-1)} n=${prices[k].months.length}`);}catch(e){console.error(`FETCH_FAIL ${k}`,e.message);}
}
if(!prices.SPY)throw new Error('SPY required');

const rawEvents=[];
const perAsset={};
for(const [asset,p] of Object.entries(prices)){
  const rs=asset==='SPY'?null:relSeries(p,prices.SPY);
  const rsMap=rs?new Map(rs.months.map((m,i)=>[m,{i,v:rs.values[i]}])):null;
  const rows=[];
  for(let i=0;i<p.values.length;i++){
    const stage=stageAt(p.values,i);const z=rollingZ(p.values,i);let rstage=null,rz=null;
    if(rsMap?.has(p.months[i])){const ri=rsMap.get(p.months[i]).i;rstage=stageAt(rs.values,ri);rz=rollingZ(rs.values,ri);}
    rows.push({month:p.months[i],i,stage,z,rstage,rz});
  }
  const defs={
    EARLY_UP:r=>r.stage==='EARLY_UP', CONFIRMED_UP:r=>r.stage==='CONFIRMED_UP', EARLY_DOWN:r=>r.stage==='EARLY_DOWN', CONFIRMED_DOWN:r=>r.stage==='CONFIRMED_DOWN',
    CHEAP_EARLY_UP:r=>r.z!=null&&r.z<=-1&&r.stage==='EARLY_UP', CHEAP_CONFIRMED_UP:r=>r.z!=null&&r.z<=-1&&r.stage==='CONFIRMED_UP',
    RICH_EARLY_DOWN:r=>r.z!=null&&r.z>=1&&r.stage==='EARLY_DOWN', RICH_CONFIRMED_DOWN:r=>r.z!=null&&r.z>=1&&r.stage==='CONFIRMED_DOWN',
    REL_CHEAP_EARLY_UP:r=>r.rz!=null&&r.rz<=-1&&r.stage==='EARLY_UP'&&(r.rstage==='EARLY_UP'||r.rstage==='CONFIRMED_UP'),
    REL_RICH_EARLY_DOWN:r=>r.rz!=null&&r.rz>=1&&r.stage==='EARLY_DOWN'&&(r.rstage==='EARLY_DOWN'||r.rstage==='CONFIRMED_DOWN')
  };
  perAsset[asset]={};
  for(const [signal,fn] of Object.entries(defs)){
    if(asset==='SPY'&&signal.startsWith('REL_'))continue;
    const starts=eventStarts(rows.map(fn));
    const side=signal.includes('DOWN')?'SHORT':'LONG';
    const events=starts.map(i=>({asset,signal,side,month:p.months[i],z:fmt(rows[i].z,2),rz:fmt(rows[i].rz,2),...Object.fromEntries(H.map(h=>[`r${h}`,forwardRet(p.values,i,h)]))})).filter(e=>H.some(h=>Number.isFinite(e[`r${h}`])));
    rawEvents.push(...events);perAsset[asset][signal]=stats(events,side);
  }
}

const signals=[...new Set(rawEvents.map(e=>e.signal))];
const pooled={};
for(const s of signals){const ev=rawEvents.filter(e=>e.signal===s);const side=s.includes('DOWN')?'SHORT':'LONG';pooled[s]=stats(ev,side);}

// Unconditional event-start baseline: one observation every 3 months per asset after 60M warmup.
const baseline=[];
for(const [asset,p] of Object.entries(prices))for(let i=59;i<p.values.length;i+=3)baseline.push({asset,...Object.fromEntries(H.map(h=>[`r${h}`,forwardRet(p.values,i,h)]))});
const baselineStats=stats(baseline,'LONG');

const result={
  generated_at:new Date().toISOString(),
  design:{
    status:'RESEARCH_PRICE_ONLY_NO_PARAMETER_SEARCH',
    universe:Object.keys(prices),
    price:'Yahoo adjusted monthly close; max available history',
    event_rule:'Only first month entering a state/combination counts as an event start; repeated months in same episode are not double-counted.',
    trend_rule:'Current Radar rule: 3M return + 10M MA + 3M change in 10M MA.',
    dislocation_rule:'60M rolling z-score of log adjusted price. Relative variants use asset/SPY price ratio. These are price-only research proxies, not production strategic dislocation models.',
    horizons:'Forward simple total return at 3, 6, 12 months. SHORT results are sign-inverted.',
    caveats:['Overlapping forward horizons can remain across distinct signal episodes/assets.','No transaction costs, taxes, slippage or execution lag.','No historical Money/CFTC conditioning in this first test.','ETF survivorship/launch-date differences remain.','Descriptive validation only; no p-value/FDR or threshold search.']
  },
  unconditional_3m_spaced_baseline:baselineStats,
  pooled,
  per_asset:perAsset,
  events:rawEvents
};
fs.mkdirSync('research/results',{recursive:true});
fs.writeFileSync('research/results/monthly-radar-price-backtest.json',JSON.stringify(result,null,2));

console.log('\n=== POOLED EVENT-START RESULTS (signed to trade direction) ===');
for(const s of signals){const x=pooled[s];console.log(`${s.padEnd(25)} n=${String(x.n).padStart(3)} | 3M ${String(x['3m'].mean_pct).padStart(6)}% hit ${String(x['3m'].hit_rate_pct).padStart(5)} | 6M ${String(x['6m'].mean_pct).padStart(6)}% hit ${String(x['6m'].hit_rate_pct).padStart(5)} | 12M ${String(x['12m'].mean_pct).padStart(6)}% hit ${String(x['12m'].hit_rate_pct).padStart(5)}`);}
console.log('\nBASELINE long, every 3 months:',JSON.stringify(baselineStats));
console.log('RESULT_JSON research/results/monthly-radar-price-backtest.json');
