import fs from 'node:fs';

const ASSETS={
 SPY:{sym:'SPY',money:'accel3',dislocation:'absolute',cftc:'SPY'},
 QQQ:{sym:'QQQ',money:'accel3',dislocation:'absolute',cftc:'QQQ'},
 GLD:{sym:'GLD',money:'accel3',dislocation:'real',cftc:'GLD'},
 DBC:{sym:'DBC',money:'level',dislocation:'real',cftc:'DBC'}
};
const H=[3,6,12], FRED='https://fred.stlouisfed.org/graph/fredgraph.csv';
const CFTC='https://publicreporting.cftc.gov',TFF='gpe5-46if',DIS='72hh-3qpy';
const cutoff=(()=>{const d=new Date();d.setUTCDate(1);d.setUTCMonth(d.getUTCMonth()-1);return `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}`})();
const ym=d=>`${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}`;
const addMonths=(m,n)=>{const[y,mo]=m.split('-').map(Number),d=new Date(Date.UTC(y,mo-1+n,1));return ym(d)};
const mean=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
const med=a=>{a=[...a].sort((x,y)=>x-y);if(!a.length)return null;const i=Math.floor(a.length/2);return a.length%2?a[i]:(a[i-1]+a[i])/2};
const pct=(xs,x)=>{xs=xs.filter(Number.isFinite).sort((a,b)=>a-b);return xs.length&&Number.isFinite(x)?100*xs.filter(v=>v<=x).length/xs.length:null};
const round=(x,n=2)=>x==null?null:Number(x.toFixed(n));
function zAt(vals,i,useLog=true,window=60,min=60){const a=vals.slice(Math.max(0,i-window+1),i+1).filter(Number.isFinite);if(a.length<min)return null;const v=a.map(x=>useLog?Math.log(x):x);if(v.some(x=>!Number.isFinite(x)))return null;const mu=mean(v),sd=Math.sqrt(mean(v.map(x=>(x-mu)**2)));return sd>0?(v.at(-1)-mu)/sd:null}
function stage(vals,i){if(i<12)return'MIXED';const last=vals[i],ma=mean(vals.slice(i-9,i+1)),prior=mean(vals.slice(i-12,i-2)),r3=last/vals[i-3]-1,s=prior?ma/prior-1:null;if(last>ma&&r3>0&&s>0)return'CONFIRMED_UP';if(r3>0)return'EARLY_UP';if(last<ma&&r3<0&&s<0)return'CONFIRMED_DOWN';if(r3<0)return'EARLY_DOWN';return'MIXED'}
function csvRows(t){const lines=t.trim().split(/\r?\n/);if(lines.length<2)return[];const h=lines[0].split(',');return lines.slice(1).map(l=>{const c=l.split(',');return Object.fromEntries(h.map((k,i)=>[k,c[i]]))})}
async function fred(id,start='2003-01-01'){const r=await fetch(`${FRED}?id=${id}&cosd=${start}`,{headers:{'User-Agent':'GMLI-research/2.0'}});if(!r.ok)throw new Error(`FRED ${id} ${r.status}`);return csvRows(await r.text()).map(x=>({month:String(x.observation_date||x.DATE||Object.values(x)[0]).slice(0,7),value:Number(x[id])})).filter(x=>x.month&&Number.isFinite(x.value)).sort((a,b)=>a.month.localeCompare(b.month))}
async function yahoo(sym){const r=await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?range=max&interval=1mo&events=history`,{headers:{'User-Agent':'Mozilla/5.0 GMLI-research/2.0'}});if(!r.ok)throw new Error(`Yahoo ${sym} ${r.status}`);const j=await r.json(),z=j.chart?.result?.[0],by=new Map(),ts=z?.timestamp||[],adj=z?.indicators?.adjclose?.[0]?.adjclose||[],cl=z?.indicators?.quote?.[0]?.close||[];for(let i=0;i<ts.length;i++){const m=ym(new Date(ts[i]*1000)),v=Number.isFinite(adj[i])?adj[i]:cl[i];if(Number.isFinite(v)&&v>0&&m<=cutoff)by.set(m,v)}const months=[...by.keys()].sort();return{months,values:months.map(m=>by.get(m))}}
async function metadata(id){const r=await fetch(`${CFTC}/api/views/${id}`,{headers:{'User-Agent':'GMLI-research/2.0'}});if(!r.ok)throw new Error(`CFTC meta ${id} ${r.status}`);const cols=(await r.json()).columns||[];const find=(...cs)=>{for(const c of cs){const k=c.toLowerCase(),x=cols.find(q=>String(q.name||'').toLowerCase()===k||String(q.fieldName||'').toLowerCase()===k);if(x)return x.fieldName}for(const c of cs){const k=c.toLowerCase(),x=cols.find(q=>String(q.name||'').toLowerCase().includes(k)||String(q.fieldName||'').toLowerCase().includes(k));if(x)return x.fieldName}return null};return{find}}
async function cftcRows(id,kind){const m=await metadata(id),date=m.find('Report_Date_as_YYYY_MM_DD','report_date_as_yyyy_mm_dd'),market=m.find('Market_and_Exchange_Names','market_and_exchange_names','Contract_Market_Name'),commodity=m.find('Commodity Name','commodity_name'),oi=m.find('Open_Interest_All','open_interest_all'),lo=kind==='tff'?m.find('Lev_Money_Positions_Long_All','lev_money_positions_long_all'):m.find('M_Money_Positions_Long_All','m_money_positions_long_all'),sh=kind==='tff'?m.find('Lev_Money_Positions_Short_All','lev_money_positions_short_all'):m.find('M_Money_Positions_Short_All','m_money_positions_short_all');if(![date,market,oi,lo,sh].every(Boolean))throw new Error(`CFTC ${kind} fields`);const fields=[date,market,commodity,oi,lo,sh].filter(Boolean),out=[];for(let off=0;;off+=50000){const u=new URL(`${CFTC}/resource/${id}.json`);u.searchParams.set('$select',fields.join(','));u.searchParams.set('$where',`${date} >= '2012-01-01T00:00:00.000'`);u.searchParams.set('$order',`${date} ASC`);u.searchParams.set('$limit','50000');u.searchParams.set('$offset',String(off));const r=await fetch(u,{headers:{'User-Agent':'GMLI-research/2.0'}});if(!r.ok)throw new Error(`CFTC ${kind} ${r.status}`);const a=await r.json();for(const x of a){const O=Number(x[oi]),L=Number(x[lo]),S=Number(x[sh]);if(Number.isFinite(O)&&O>0&&Number.isFinite(L)&&Number.isFinite(S))out.push({date:String(x[date]).slice(0,10),market:String(x[market]||''),commodity:commodity?String(x[commodity]||''):'',oi:O,long:L,short:S})}if(a.length<50000)break}return out}
const has=(x,terms)=>terms.some(t=>String(x).toUpperCase().includes(t));
function aggregate(rows,terms){const m=new Map();for(const r of rows){if(!has(`${r.market} ${r.commodity}`,terms))continue;const x=m.get(r.date)||{oi:0,long:0,short:0};x.oi+=r.oi;x.long+=r.long;x.short+=r.short;m.set(r.date,x)}return[...m.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([date,x])=>({date,value:(x.long-x.short)/x.oi}))}
function percentileAt(series,month){const end=`${month}-31`,cur=[...series].reverse().find(x=>x.date<=end);if(!cur)return null;const d=new Date(`${cur.date}T00:00:00Z`);d.setUTCFullYear(d.getUTCFullYear()-3);const start=d.toISOString().slice(0,10),w=series.filter(x=>x.date>=start&&x.date<=cur.date).map(x=>x.value);return w.length>=100?pct(w,cur.value):null}
function dbcPct(parts,month){const xs=parts.map(s=>percentileAt(s,month)).filter(Number.isFinite);return xs.length>=2?mean(xs):null}
function moneySignal(moneyMap,month,mode){const lag=addMonths(month,-1),v=moneyMap.get(lag);if(!Number.isFinite(v))return null;if(mode==='accel3'){const p=moneyMap.get(addMonths(lag,-3));return Number.isFinite(p)?v-p:null}const months=[...moneyMap.keys()].filter(m=>m<=lag).sort(),vals=months.map(m=>moneyMap.get(m)),i=months.indexOf(lag);return i>=0?zAt(vals,i,false,120,36):null}
function priceDislocation(p,cpiMap,i,type){if(i<59)return null;if(type==='absolute')return zAt(p.values,i,true,60,60);const real=[],months=[];for(let k=0;k<=i;k++){const m=p.months[k],cv=cpiMap.get(addMonths(m,-1)),pv=p.values[k];if(Number.isFinite(cv)&&cv>0&&Number.isFinite(pv)){real.push(pv/cv);months.push(m)}}return zAt(real,real.length-1,true,60,60)}
function eventStats(events,side,base){const o={n:events.length};for(const h of H){const a=events.filter(e=>Number.isFinite(e[`r${h}`])).map(e=>side==='SHORT'?-e[`r${h}`]:e[`r${h}`]);const b=events.filter(e=>Number.isFinite(e[`r${h}`])&&base[e.asset]?.[h]).map(e=>side==='SHORT'?-base[e.asset][h].mean:base[e.asset][h].mean);o[`${h}m`]={n:a.length,mean_pct:round(100*mean(a),1),median_pct:round(100*med(a),1),hit_rate_pct:round(100*mean(a.map(x=>x>0?1:0)),1),asset_matched_baseline_mean_pct:round(100*mean(b),1),edge_pp:round(100*(mean(a)-mean(b)),1)}}return o}
function baseline(p){const o={};for(const h of H){const a=[];for(let i=59;i+h<p.values.length;i+=3)a.push(p.values[i+h]/p.values[i]-1);o[h]={mean:mean(a),hit:mean(a.map(x=>x>0?1:0))}}return o}

const money=await fred('OECDMABMM301GYSAM','2003-01-01'),moneyMap=new Map(money.map(x=>[x.month,x.value])),cpi=await fred('CPIAUCSL','2003-01-01'),cpiMap=new Map(cpi.map(x=>[x.month,x.value]));
const [tff,dis]=await Promise.all([cftcRows(TFF,'tff'),cftcRows(DIS,'disagg')]);
const cftc={
 SPY:aggregate(tff,['S&P 500','E-MINI S&P','MICRO E-MINI S&P']),
 QQQ:aggregate(tff,['NASDAQ-100','NASDAQ 100','E-MINI NASDAQ','MICRO E-MINI NASDAQ']),
 GLD:aggregate(dis,['GOLD'])
};
const dbcParts=[aggregate(dis,['CRUDE OIL','WTI']),aggregate(dis,['COPPER']),aggregate(dis,['CORN']),aggregate(dis,['WHEAT'])];
const prices={},base={};for(const[a,c]of Object.entries(ASSETS)){prices[a]=await yahoo(c.sym);base[a]=baseline(prices[a])}
const defs={
 EARLY_UP:{side:'LONG',f:x=>x.stage==='EARLY_UP'},
 EARLY_UP_MONEY:{side:'LONG',f:x=>x.stage==='EARLY_UP'&&x.moneyLong},
 EARLY_UP_MONEY_CHEAP:{side:'LONG',f:x=>x.stage==='EARLY_UP'&&x.moneyLong&&x.cheap},
 EARLY_UP_MONEY_WASHED:{side:'LONG',f:x=>x.stage==='EARLY_UP'&&x.moneyLong&&x.washed},
 EARLY_UP_RADAR:{side:'LONG',f:x=>x.stage==='EARLY_UP'&&x.moneyLong&&(x.cheap||x.washed)},
 CONFIRMED_UP_RADAR:{side:'LONG',f:x=>x.stage==='CONFIRMED_UP'&&x.moneyLong&&(x.cheap||x.washed)},
 EARLY_DOWN:{side:'SHORT',f:x=>x.stage==='EARLY_DOWN'},
 EARLY_DOWN_MONEY:{side:'SHORT',f:x=>x.stage==='EARLY_DOWN'&&x.moneyShort},
 EARLY_DOWN_MONEY_RICH:{side:'SHORT',f:x=>x.stage==='EARLY_DOWN'&&x.moneyShort&&x.rich},
 EARLY_DOWN_MONEY_CROWDED:{side:'SHORT',f:x=>x.stage==='EARLY_DOWN'&&x.moneyShort&&x.crowded},
 EARLY_DOWN_RADAR:{side:'SHORT',f:x=>x.stage==='EARLY_DOWN'&&x.moneyShort&&(x.rich||x.crowded)},
 CONFIRMED_DOWN_RADAR:{side:'SHORT',f:x=>x.stage==='CONFIRMED_DOWN'&&x.moneyShort&&(x.rich||x.crowded)}
};
const events=[];
for(const[a,c]of Object.entries(ASSETS)){const p=prices[a],states=[];for(let i=59;i<p.values.length;i++){const month=p.months[i];if(month<'2015-01'||month>money.at(-1).month)continue;const st=stage(p.values,i),ms=moneySignal(moneyMap,month,c.money),dz=priceDislocation(p,cpiMap,i,c.dislocation),cp=a==='DBC'?dbcPct(dbcParts,month):percentileAt(cftc[a],month);states.push({i,month,stage:st,money:ms,moneyLong:Number.isFinite(ms)&&ms>0,moneyShort:Number.isFinite(ms)&&ms<0,cheap:Number.isFinite(dz)&&dz<=-1,rich:Number.isFinite(dz)&&dz>=1,washed:Number.isFinite(cp)&&cp<=25,crowded:Number.isFinite(cp)&&cp>=75,dislocation_z:dz,cftc_pct:cp})}for(const[name,d]of Object.entries(defs)){let prev=false;for(const x of states){const on=d.f(x);if(on&&!prev){const e={asset:a,signal:name,side:d.side,month:x.month,money_signal:round(x.money,3),dislocation_z:round(x.dislocation_z,2),cftc_percentile:round(x.cftc_pct,1)};for(const h of H)e[`r${h}`]=x.i+h<p.values.length?p.values[x.i+h]/p.values[x.i]-1:null;events.push(e)}prev=on}}}
function pack(filter=()=>true){const out={};for(const[name,d]of Object.entries(defs)){const e=events.filter(x=>x.signal===name&&filter(x));out[name]=eventStats(e,d.side,base)}return out}
const result={
 generated_at:new Date().toISOString(),status:'RESEARCH_ONLY_NO_CORE_CHANGE',design:{universe:Object.keys(ASSETS),period:'2015+',price:'Yahoo adjusted monthly close',money_proxy:'OECD M3 YoY OECDMABMM301GYSAM; current-vintage research proxy, not preserved frozen seven-region bytes',publication_lag_months:1,money_rules:{SPY:'3M change in lagged OECD M3 YoY proxy',QQQ:'3M change in lagged OECD M3 YoY proxy',GLD:'3M change in lagged OECD M3 YoY proxy (closest available long-history FX-neutral proxy)',DBC:'120M z-score of lagged OECD M3 YoY proxy, min 36'},cftc:'same 3Y percentile thresholds as Radar: <=25 washed, >=75 crowded',dislocation:'same price thresholds: z<=-1 cheap, z>=+1 rich; GLD/DBC use CPI-lagged real price',episode_rule:'first month entering each complete condition only',guardrails:['no parameter search','no Core retuning','Money proxy is explicitly not exact frozen GMLI history']},full:pack(),train_2015_2022:pack(e=>e.month<='2022-12'),post_2023:pack(e=>e.month>='2023-01'),events};
fs.mkdirSync('research/results',{recursive:true});fs.writeFileSync('research/results/monthly-radar-money-cftc-backtest.json',JSON.stringify(result,null,2));
console.log('=== FULL ===');for(const[name,x]of Object.entries(result.full))console.log(name.padEnd(30),`N=${String(x.n).padStart(3)} 3M=${x['3m'].mean_pct}% edge=${x['3m'].edge_pp}pp | 6M=${x['6m'].mean_pct}% edge=${x['6m'].edge_pp}pp | 12M=${x['12m'].mean_pct}% edge=${x['12m'].edge_pp}pp hit=${x['12m'].hit_rate_pct}%`);
console.log('\n=== POST 2023 ===');for(const[name,x]of Object.entries(result.post_2023))console.log(name.padEnd(30),`N=${String(x.n).padStart(3)} 6M=${x['6m'].mean_pct}% edge=${x['6m'].edge_pp}pp | 12M=${x['12m'].mean_pct}% edge=${x['12m'].edge_pp}pp`);
