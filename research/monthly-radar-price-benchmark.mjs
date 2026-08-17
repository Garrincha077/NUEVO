import fs from 'node:fs';

const P='research/results/monthly-radar-price-backtest.json';
const d=JSON.parse(fs.readFileSync(P,'utf8'));
const H=[3,6,12];
const SYMBOLS={SPY:'SPY',QQQ:'QQQ',IWM:'IWM',GLD:'GLD',SLV:'SLV',DBC:'DBC',USO:'USO',CPER:'CPER',DBA:'DBA',TLT:'TLT',IEF:'IEF',FXY:'FXY',HYG:'HYG',VNQ:'VNQ',EEM:'EEM',VEA:'VEA',BTC:'BTC-USD'};
const ym=x=>{const q=new Date(x*1000);return `${q.getUTCFullYear()}-${String(q.getUTCMonth()+1).padStart(2,'0')}`};
const mean=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
const med=a=>{a=[...a].sort((x,y)=>x-y);if(!a.length)return null;let i=Math.floor(a.length/2);return a.length%2?a[i]:(a[i-1]+a[i])/2};
const f=x=>x==null?null:Number(x.toFixed(1));

async function price(sym){const r=await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?range=max&interval=1mo&events=history`,{headers:{'User-Agent':'Mozilla/5.0 GMLI-benchmark/1.0'}});if(!r.ok)throw new Error(`${sym} ${r.status}`);const j=await r.json(),z=j.chart?.result?.[0],by=new Map();const ts=z?.timestamp||[],adj=z?.indicators?.adjclose?.[0]?.adjclose||[],cl=z?.indicators?.quote?.[0]?.close||[];for(let i=0;i<ts.length;i++){const v=Number.isFinite(adj[i])?adj[i]:cl[i];if(Number.isFinite(v)&&v>0)by.set(ym(ts[i]),v);}const months=[...by.keys()].sort();return{months,values:months.map(m=>by.get(m))};}
function baseStats(p){const o={};for(const h of H){const a=[];for(let i=59;i+h<p.values.length;i+=3)a.push(p.values[i+h]/p.values[i]-1);o[h]={mean:mean(a),median:med(a),hit:mean(a.map(x=>x>0?1:0))};}return o;}

const base={};
for(const [a,s] of Object.entries(SYMBOLS)){try{base[a]=baseStats(await price(s));}catch(e){console.error('BASE_FAIL',a,e.message);}}

function signalStats(events,side){const o={n:events.length};for(const h of H){const vals=events.map(e=>e[`r${h}`]).filter(Number.isFinite).map(x=>side==='SHORT'?-x:x);const matched=events.filter(e=>Number.isFinite(e[`r${h}`])&&base[e.asset]?.[h]).map(e=>side==='SHORT'?-base[e.asset][h].mean:base[e.asset][h].mean);const matchedHit=events.filter(e=>Number.isFinite(e[`r${h}`])&&base[e.asset]?.[h]).map(e=>side==='SHORT'?1-base[e.asset][h].hit:base[e.asset][h].hit);o[`${h}m`]={n:vals.length,mean_pct:f(100*mean(vals)),median_pct:f(100*med(vals)),hit_rate_pct:f(100*mean(vals.map(x=>x>0?1:0))),asset_matched_baseline_mean_pct:f(100*mean(matched)),edge_vs_asset_baseline_pp:f(100*(mean(vals)-mean(matched))),asset_matched_baseline_hit_pct:f(100*mean(matchedHit))};}return o;}

const signals=[...new Set(d.events.map(e=>e.signal))];
const matched={},recent_2018={};
for(const s of signals){const side=s.includes('DOWN')?'SHORT':'LONG';matched[s]=signalStats(d.events.filter(e=>e.signal===s),side);recent_2018[s]=signalStats(d.events.filter(e=>e.signal===s&&e.month>='2018-01'),side);}

d.asset_matched_control={method:'Signal return compared with 3-month-spaced unconditional forward return of the same asset; SHORT benchmark is sign-inverted.',matched,recent_2018};
fs.writeFileSync(P,JSON.stringify(d,null,2));
console.log('\n=== ASSET-MATCHED EDGE ===');
for(const s of signals){const x=matched[s];console.log(`${s.padEnd(25)} 3M edge ${String(x['3m'].edge_vs_asset_baseline_pp).padStart(6)}pp | 6M ${String(x['6m'].edge_vs_asset_baseline_pp).padStart(6)}pp | 12M ${String(x['12m'].edge_vs_asset_baseline_pp).padStart(6)}pp`);}
console.log('\n=== 2018+ ===');
for(const s of signals){const x=recent_2018[s];console.log(`${s.padEnd(25)} n=${String(x.n).padStart(3)} | 6M mean ${String(x['6m'].mean_pct).padStart(6)} edge ${String(x['6m'].edge_vs_asset_baseline_pp).padStart(6)} | 12M mean ${String(x['12m'].mean_pct).padStart(6)} edge ${String(x['12m'].edge_vs_asset_baseline_pp).padStart(6)}`);}
