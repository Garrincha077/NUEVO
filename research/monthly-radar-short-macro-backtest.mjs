import fs from 'node:fs';

const ASSETS={
  SPY:{sym:'SPY',dislocation:'absolute',cftc:'SPY'},
  QQQ:{sym:'QQQ',dislocation:'absolute',cftc:'QQQ'},
  IWM:{sym:'IWM',dislocation:'relative',cftc:'IWM'},
  GLD:{sym:'GLD',dislocation:'real',cftc:'GLD'},
  DBC:{sym:'DBC',dislocation:'real',cftc:'DBC'},
  USO:{sym:'USO',dislocation:'real',cftc:'USO'},
  CPER:{sym:'CPER',dislocation:'real',cftc:'CPER'},
  DBA:{sym:'DBA',dislocation:'real',cftc:'DBA'}
};
const H=[3,6,12];
const FRED='https://fred.stlouisfed.org/graph/fredgraph.csv';
const CFTC='https://publicreporting.cftc.gov',TFF='gpe5-46if',DIS='72hh-3qpy';
const cutoff=(()=>{const d=new Date();d.setUTCDate(1);d.setUTCMonth(d.getUTCMonth()-1);return `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}`})();
const ym=d=>`${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}`;
const mean=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
const med=a=>{a=[...a].sort((x,y)=>x-y);if(!a.length)return null;const i=Math.floor(a.length/2);return a.length%2?a[i]:(a[i-1]+a[i])/2};
const pct=(xs,x)=>{xs=xs.filter(Number.isFinite).sort((a,b)=>a-b);return xs.length&&Number.isFinite(x)?100*xs.filter(v=>v<=x).length/xs.length:null};
const round=(x,n=2)=>x==null?null:Number(x.toFixed(n));
function zAt(vals,i,useLog=true,window=60,min=60){const a=vals.slice(Math.max(0,i-window+1),i+1).filter(Number.isFinite);if(a.length<min)return null;const v=a.map(x=>useLog?Math.log(x):x);if(v.some(x=>!Number.isFinite(x)))return null;const mu=mean(v),sd=Math.sqrt(mean(v.map(x=>(x-mu)**2)));return sd>0?(v.at(-1)-mu)/sd:null}
function stage(vals,i){if(i<12)return'MIXED';const last=vals[i],ma=mean(vals.slice(i-9,i+1)),prior=mean(vals.slice(i-12,i-2)),r3=last/vals[i-3]-1,s=prior?ma/prior-1:null;if(last>ma&&r3>0&&s>0)return'CONFIRMED_UP';if(r3>0)return'EARLY_UP';if(last<ma&&r3<0&&s<0)return'CONFIRMED_DOWN';if(r3<0)return'EARLY_DOWN';return'MIXED'}
function csvRows(t){const lines=t.trim().split(/\r?\n/);if(lines.length<2)return[];const h=lines[0].split(',');return lines.slice(1).map(l=>{const c=l.split(',');return Object.fromEntries(h.map((k,i)=>[k,c[i]]))})}
async function fredMonthlyLast(id,start='2003-01-01'){const r=await fetch(`${FRED}?id=${id}&cosd=${start}`,{headers:{'User-Agent':'GMLI-short-research/1.0'}});if(!r.ok)throw new Error(`FRED ${id} ${r.status}`);const rows=csvRows(await r.text()),by=new Map();for(const x of rows){const date=String(x.observation_date||x.DATE||Object.values(x)[0]),m=date.slice(0,7),v=Number(x[id]);if(m&&Number.isFinite(v)&&m<=cutoff)by.set(m,{date,value:v})}return new Map([...by.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([m,x])=>[m,x.value]))}
async function yahoo(sym){const r=await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?range=max&interval=1mo&events=history`,{headers:{'User-Agent':'Mozilla/5.0 GMLI-short-research/1.0'}});if(!r.ok)throw new Error(`Yahoo ${sym} ${r.status}`);const j=await r.json(),z=j.chart?.result?.[0],by=new Map(),ts=z?.timestamp||[],adj=z?.indicators?.adjclose?.[0]?.adjclose||[],cl=z?.indicators?.quote?.[0]?.close||[];for(let i=0;i<ts.length;i++){const m=ym(new Date(ts[i]*1000)),v=Number.isFinite(adj[i])?adj[i]:cl[i];if(Number.isFinite(v)&&v>0&&m<=cutoff)by.set(m,v)}const months=[...by.keys()].sort();return{months,values:months.map(m=>by.get(m))}}
async function metadata(id){const r=await fetch(`${CFTC}/api/views/${id}`,{headers:{'User-Agent':'GMLI-short-research/1.0'}});if(!r.ok)throw new Error(`CFTC meta ${id} ${r.status}`);const cols=(await r.json()).columns||[];const find=(...cs)=>{for(const c of cs){const k=c.toLowerCase(),x=cols.find(q=>String(q.name||'').toLowerCase()===k||String(q.fieldName||'').toLowerCase()===k);if(x)return x.fieldName}for(const c of cs){const k=c.toLowerCase(),x=cols.find(q=>String(q.name||'').toLowerCase().includes(k)||String(q.fieldName||'').toLowerCase().includes(k));if(x)return x.fieldName}return null};return{find}}
async function cftcRows(id,kind){const m=await metadata(id),date=m.find('Report_Date_as_YYYY_MM_DD','report_date_as_yyyy_mm_dd'),market=m.find('Market_and_Exchange_Names','market_and_exchange_names','Contract_Market_Name'),commodity=m.find('Commodity Name','commodity_name'),oi=m.find('Open_Interest_All','open_interest_all'),lo=kind==='tff'?m.find('Lev_Money_Positions_Long_All','lev_money_positions_long_all'):m.find('M_Money_Positions_Long_All','m_money_positions_long_all'),sh=kind==='tff'?m.find('Lev_Money_Positions_Short_All','lev_money_positions_short_all'):m.find('M_Money_Positions_Short_All','m_money_positions_short_all');if(![date,market,oi,lo,sh].every(Boolean))throw new Error(`CFTC ${kind} fields`);const fields=[date,market,commodity,oi,lo,sh].filter(Boolean),out=[];for(let off=0;;off+=50000){const u=new URL(`${CFTC}/resource/${id}.json`);u.searchParams.set('$select',fields.join(','));u.searchParams.set('$where',`${date} >= '2012-01-01T00:00:00.000'`);u.searchParams.set('$order',`${date} ASC`);u.searchParams.set('$limit','50000');u.searchParams.set('$offset',String(off));const r=await fetch(u,{headers:{'User-Agent':'GMLI-short-research/1.0'}});if(!r.ok)throw new Error(`CFTC ${kind} ${r.status}`);const a=await r.json();for(const x of a){const O=Number(x[oi]),L=Number(x[lo]),S=Number(x[sh]);if(Number.isFinite(O)&&O>0&&Number.isFinite(L)&&Number.isFinite(S))out.push({date:String(x[date]).slice(0,10),market:String(x[market]||''),commodity:commodity?String(x[commodity]||''):'',oi:O,long:L,short:S})}if(a.length<50000)break}return out}
const has=(x,terms)=>terms.some(t=>String(x).toUpperCase().includes(t));
function aggregate(rows,terms){const m=new Map();for(const r of rows){if(!has(`${r.market} ${r.commodity}`,terms))continue;const x=m.get(r.date)||{oi:0,long:0,short:0};x.oi+=r.oi;x.long+=r.long;x.short+=r.short;m.set(r.date,x)}return[...m.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([date,x])=>({date,value:(x.long-x.short)/x.oi}))}
function percentileAt(series,month){const end=`${month}-31`,cur=[...series].reverse().find(x=>x.date<=end);if(!cur)return null;const d=new Date(`${cur.date}T00:00:00Z`);d.setUTCFullYear(d.getUTCFullYear()-3);const start=d.toISOString().slice(0,10),w=series.filter(x=>x.date>=start&&x.date<=cur.date).map(x=>x.value);return w.length>=100?pct(w,cur.value):null}
function basketPct(parts,month,min=2){const xs=parts.map(s=>percentileAt(s,month)).filter(Number.isFinite);return xs.length>=min?mean(xs):null}
function realZ(p,cpiMap,i){const real=[];for(let k=0;k<=i;k++){const m=p.months[k],cv=cpiMap.get(m),pv=p.values[k];if(Number.isFinite(cv)&&cv>0&&Number.isFinite(pv))real.push(pv/cv)}return zAt(real,real.length-1,true,60,60)}
function relativeZ(p,spy,i){const bm=new Map(spy.months.map((m,j)=>[m,spy.values[j]])),rel=[];for(let k=0;k<=i;k++){const m=p.months[k],b=bm.get(m),v=p.values[k];if(Number.isFinite(v)&&v>0&&Number.isFinite(b)&&b>0)rel.push(v/b)}return zAt(rel,rel.length-1,true,60,60)}
function dislocationZ(asset,p,spy,cpiMap,i,type){if(i<59)return null;if(type==='absolute')return zAt(p.values,i,true,60,60);if(type==='relative')return relativeZ(p,spy,i);return realZ(p,cpiMap,i)}
function macroState(month,maps){const def={real_yield:maps.realYield,usd:maps.usd,credit:maps.credit,nfci:maps.nfci},flags={},changes={};for(const[k,map]of Object.entries(def)){const v=map.get(month),months=[...map.keys()].filter(m=>m<=month).sort(),idx=months.indexOf(month),pm=idx>=3?months[idx-3]:null,p=pm?map.get(pm):null;const delta=Number.isFinite(v)&&Number.isFinite(p)?v-p:null;changes[k]=delta;flags[k]=Number.isFinite(delta)?delta>0:null}const known=Object.values(flags).filter(x=>x!==null).length,count=Object.values(flags).filter(Boolean).length;return{known,count,restrictive:known===4&&count>=3,flags,changes}}
function baseline(p){const o={};for(const h of H){const a=[];for(let i=59;i+h<p.values.length;i+=3)a.push(p.values[i+h]/p.values[i]-1);o[h]={mean:mean(a),hit:mean(a.map(x=>x>0?1:0))}}return o}
function stats(events,base){const o={n:events.length};for(const h of H){const a=events.filter(e=>Number.isFinite(e[`r${h}`])).map(e=>-e[`r${h}`]);const b=events.filter(e=>Number.isFinite(e[`r${h}`])&&base[e.asset]?.[h]).map(e=>-base[e.asset][h].mean);o[`${h}m`]={n:a.length,mean_pct:round(100*mean(a),1),median_pct:round(100*med(a),1),hit_rate_pct:round(100*mean(a.map(x=>x>0?1:0)),1),asset_matched_baseline_mean_pct:round(100*mean(b),1),edge_pp:round(100*(mean(a)-mean(b)),1)}}return o}

const [realYield,usd,credit,nfci,cpi]=await Promise.all([
  fredMonthlyLast('DFII10','2003-01-01'),
  fredMonthlyLast('DTWEXBGS','2003-01-01'),
  fredMonthlyLast('BAMLH0A0HYM2','2003-01-01'),
  fredMonthlyLast('NFCI','2003-01-01'),
  fredMonthlyLast('CPIAUCSL','2003-01-01')
]);
const maps={realYield,usd,credit,nfci};
const [tff,dis]=await Promise.all([cftcRows(TFF,'tff'),cftcRows(DIS,'disagg')]);
const series={
  SPY:aggregate(tff,['S&P 500','E-MINI S&P','MICRO E-MINI S&P']),
  QQQ:aggregate(tff,['NASDAQ-100','NASDAQ 100','E-MINI NASDAQ','MICRO E-MINI NASDAQ']),
  IWM:aggregate(tff,['RUSSELL 2000','E-MINI RUSSELL','MICRO E-MINI RUSSELL']),
  GLD:aggregate(dis,['GOLD']),
  USO:aggregate(dis,['CRUDE OIL','WTI']),
  CPER:aggregate(dis,['COPPER'])
};
const agriParts=[aggregate(dis,['CORN']),aggregate(dis,['WHEAT']),aggregate(dis,['SOYBEAN']),aggregate(dis,['SUGAR']),aggregate(dis,['COFFEE'])];
const dbcParts=[series.USO,series.CPER,aggregate(dis,['CORN']),aggregate(dis,['WHEAT'])];
const prices={},base={};for(const[a,c]of Object.entries(ASSETS)){prices[a]=await yahoo(c.sym);base[a]=baseline(prices[a])}
const spy=prices.SPY;
const defs={
  EARLY_DOWN:{f:x=>x.stage==='EARLY_DOWN'},
  EARLY_DOWN_MACRO3:{f:x=>x.stage==='EARLY_DOWN'&&x.macro3},
  EARLY_DOWN_MACRO3_RICH:{f:x=>x.stage==='EARLY_DOWN'&&x.macro3&&x.rich},
  EARLY_DOWN_MACRO3_CROWDED:{f:x=>x.stage==='EARLY_DOWN'&&x.macro3&&x.crowded},
  EARLY_DOWN_SHORT_MODEL:{f:x=>x.stage==='EARLY_DOWN'&&x.macro3&&(x.rich||x.crowded)},
  CONFIRMED_DOWN_SHORT_MODEL:{f:x=>x.stage==='CONFIRMED_DOWN'&&x.macro3&&(x.rich||x.crowded)}
};
const events=[];
for(const[a,c]of Object.entries(ASSETS)){
  const p=prices[a],states=[];
  for(let i=59;i<p.values.length;i++){
    const month=p.months[i];if(month<'2015-01')continue;
    const macro=macroState(month,maps);if(macro.known<4)continue;
    const st=stage(p.values,i),dz=dislocationZ(a,p,spy,cpi,i,c.dislocation);
    let cp=null;if(a==='DBC')cp=basketPct(dbcParts,month,2);else if(a==='DBA')cp=basketPct(agriParts,month,3);else cp=percentileAt(series[a],month);
    states.push({i,month,stage:st,macro3:macro.restrictive,macro_count:macro.count,macro_flags:macro.flags,macro_changes:macro.changes,rich:Number.isFinite(dz)&&dz>=1,crowded:Number.isFinite(cp)&&cp>=75,dislocation_z:dz,cftc_pct:cp});
  }
  for(const[name,d]of Object.entries(defs)){
    let prev=false;
    for(const x of states){const on=d.f(x);if(on&&!prev){const e={asset:a,signal:name,month:x.month,macro_headwinds:x.macro_count,macro_flags:x.macro_flags,macro_changes:Object.fromEntries(Object.entries(x.macro_changes).map(([k,v])=>[k,round(v,3)])),dislocation_z:round(x.dislocation_z,2),cftc_percentile:round(x.cftc_pct,1)};for(const h of H)e[`r${h}`]=x.i+h<p.values.length?p.values[x.i+h]/p.values[x.i]-1:null;events.push(e)}prev=on}
  }
}
function pack(filter=()=>true){const out={};for(const name of Object.keys(defs)){const e=events.filter(x=>x.signal===name&&filter(x));out[name]=stats(e,base)}return out}
const main=events.filter(e=>e.signal==='EARLY_DOWN_SHORT_MODEL');
const byAsset=Object.fromEntries(Object.keys(ASSETS).map(a=>[a,main.filter(e=>e.asset===a).length]));
const leaveOneOut={};for(const a of Object.keys(ASSETS)){const e=main.filter(x=>x.asset!==a);leaveOneOut[a]=stats(e,base)}
const result={
  generated_at:new Date().toISOString(),
  status:'RESEARCH_ONLY_NO_CORE_OR_RADAR_CHANGE',
  design:{
    universe:Object.keys(ASSETS),period:'2015+',price:'Yahoo adjusted monthly close',
    macro_headwind_rule:'At least 3 of 4 contemporaneous monthly market/conditions indicators deteriorating over 3 months: DFII10 higher, DTWEXBGS higher, BAMLH0A0HYM2 higher, NFCI higher.',
    macro_series:{real_yield:'FRED DFII10 — 10Y TIPS real yield',usd:'FRED DTWEXBGS — broad trade-weighted USD',credit:'FRED BAMLH0A0HYM2 — US HY OAS',funding:'FRED NFCI — Chicago Fed National Financial Conditions Index'},
    contrarian_rule:'rich if 60M price z >= +1; crowded if historical 3Y CFTC percentile >=75; main short model accepts rich OR crowded',
    trend_rule:'existing monthly Radar stage: 3M momentum + 10M MA + 3M 10M-MA slope',
    episode_rule:'first month entering the complete condition only',
    cftc:'historical as-of each month, trailing 3Y percentile; TFF Leveraged Money for equity indexes, Disaggregated Managed Money for gold/commodities',
    guardrails:['3-of-4 macro threshold pre-specified before results','no parameter or horizon search','no Core retuning','no production Radar change','missing data never counts as a pass']
  },
  full:pack(),train_2015_2022:pack(e=>e.month<='2022-12'),post_2023:pack(e=>e.month>='2023-01'),
  main_model_diagnostics:{by_asset:byAsset,leave_one_asset_out:leaveOneOut},events
};
fs.mkdirSync('research/results',{recursive:true});fs.writeFileSync('research/results/monthly-radar-short-macro-backtest.json',JSON.stringify(result,null,2));
console.log('=== SHORT MACRO TEST — FULL ===');for(const[name,x]of Object.entries(result.full))console.log(`${name.padEnd(32)} N=${String(x.n).padStart(3)} | 3M ${String(x['3m'].mean_pct).padStart(6)}% edge ${String(x['3m'].edge_pp).padStart(6)}pp | 6M ${String(x['6m'].mean_pct).padStart(6)}% edge ${String(x['6m'].edge_pp).padStart(6)}pp | 12M ${String(x['12m'].mean_pct).padStart(6)}% edge ${String(x['12m'].edge_pp).padStart(6)}pp hit ${String(x['12m'].hit_rate_pct).padStart(5)}%`);
console.log('\n=== POST 2023 ===');for(const[name,x]of Object.entries(result.post_2023))console.log(`${name.padEnd(32)} N=${String(x.n).padStart(3)} | 6M ${String(x['6m'].mean_pct).padStart(6)}% edge ${String(x['6m'].edge_pp).padStart(6)}pp | 12M ${String(x['12m'].mean_pct).padStart(6)}% edge ${String(x['12m'].edge_pp).padStart(6)}pp`);
console.log('\nMAIN BY ASSET',JSON.stringify(byAsset));
console.log('RESULT_JSON research/results/monthly-radar-short-macro-backtest.json');
