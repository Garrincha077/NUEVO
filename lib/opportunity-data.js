const FRED_BASE = 'https://fred.stlouisfed.org/graph/fredgraph.csv';
const ym = d => `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
function previousCompletedMonth(){ const d=new Date(); d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth()-1); return ym(d); }
function zscore(values,useLog=true){ const clean=values.filter(Number.isFinite); if(clean.length<60)return null; const w=clean.slice(-60).map(x=>useLog?Math.log(x):x); if(w.some(x=>!Number.isFinite(x)))return null; const mean=w.reduce((a,b)=>a+b,0)/w.length; const variance=w.reduce((a,b)=>a+(b-mean)**2,0)/(w.length-1); const sd=Math.sqrt(variance); return sd>0?(w.at(-1)-mean)/sd:null; }
function csvRows(text){ const lines=text.trim().split(/\r?\n/); if(lines.length<2)return[]; const headers=lines[0].split(','); return lines.slice(1).map(line=>{const cells=line.split(',');return Object.fromEntries(headers.map((h,i)=>[h,cells[i]]));}); }
export async function yahooMonthly(sym){ const url=`https://query1.finance.yahoo.com/v8/finance/chart/${sym}?range=10y&interval=1mo&events=history`; const r=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0'}}); if(!r.ok)throw new Error(`Yahoo ${sym} ${r.status}`); const j=await r.json(); const z=j.chart?.result?.[0]; if(!z)throw new Error(`Yahoo ${sym} empty result`); const timestamps=z.timestamp||[]; const adj=z.indicators?.adjclose?.[0]?.adjclose||[]; const close=z.indicators?.quote?.[0]?.close||[]; const cutoff=previousCompletedMonth(); const byMonth=new Map(); for(let i=0;i<timestamps.length;i++){const d=new Date(timestamps[i]*1000);const key=ym(d);const value=Number.isFinite(adj[i])?adj[i]:close[i];if(Number.isFinite(value)&&key<=cutoff)byMonth.set(key,value);} const months=[...byMonth.keys()].sort();const values=months.map(k=>byMonth.get(k));if(values.length<12)throw new Error(`Yahoo ${sym} insufficient monthly history`);return{months,values,as_of:months.at(-1),last:values.at(-1)}; }
export async function fredMonthly(id,start='2014-01-01'){ const url=`${FRED_BASE}?id=${encodeURIComponent(id)}&cosd=${start}`; const r=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0'}});if(!r.ok)throw new Error(`FRED ${id} ${r.status}`);const rows=csvRows(await r.text());const byMonth=new Map();for(const row of rows){const dateKey=Object.keys(row)[0];const d=new Date(`${row[dateKey]}T00:00:00Z`);const key=ym(d);const v=Number(row[id]);if(Number.isFinite(v))byMonth.set(key,v);}const months=[...byMonth.keys()].sort();return{months,map:byMonth,as_of:months.at(-1)||null}; }
function turnFromValues(v,asOf,rulePrefix='completed-month adjusted price'){
  if(v.length<13)return{pass:false,available:false,as_of:asOf||null};
  const last=v.at(-1);
  const ma10=v.slice(-10).reduce((a,b)=>a+b,0)/10;
  const prior10=v.slice(-13,-3);
  const ma10prior=prior10.reduce((a,b)=>a+b,0)/10;
  const r3=last/v.at(-4)-1;
  const r6=v.length>=7?last/v.at(-7)-1:null;
  const slope=ma10prior>0?ma10/ma10prior-1:null;
  let stage='MIXED';
  if(last>ma10&&r3>0&&slope>0)stage='CONFIRMED_UP';
  else if(r3>0)stage='EARLY_UP';
  else if(last<ma10&&r3<0&&slope<0)stage='CONFIRMED_DOWN';
  else if(r3<0)stage='EARLY_DOWN';
  return{
    available:true,
    pass:last>ma10||r3>0,
    stage,
    price:Number(last.toFixed(4)),
    ma10:Number(ma10.toFixed(4)),
    ma10_slope_3m_pct:slope==null?null:Number((100*slope).toFixed(1)),
    return_3m_pct:Number((100*r3).toFixed(1)),
    return_6m_pct:r6==null?null:Number((100*r6).toFixed(1)),
    as_of:asOf,
    rule:`${rulePrefix} > 10M MA OR 3M return > 0; stage also uses 3M return and 10M-MA 3M slope`
  };
}
export function priceTurn(price){ return turnFromValues(price.values,price.as_of,'completed-month adjusted price'); }
export function relativeTurn(price,benchmark){
  const bmap=new Map(benchmark.months.map((m,i)=>[m,benchmark.values[i]]));
  const ratios=[],months=[];
  for(let i=0;i<price.months.length;i++){
    const m=price.months[i],pv=price.values[i],bv=bmap.get(m);
    if(Number.isFinite(pv)&&pv>0&&Number.isFinite(bv)&&bv>0){months.push(m);ratios.push(pv/bv);}
  }
  if(ratios.length<13)return{available:false,pass:false,benchmark:'SPY'};
  return{...turnFromValues(ratios,months.at(-1),'relative price versus SPY'),benchmark:'SPY'};
}
export function absolutePriceDislocation(price){const z=zscore(price.values,true);return{available:z!=null,pass:z!=null?z<=-1:false,z60m:z==null?null:Number(z.toFixed(2)),as_of:price.as_of,rule:'60M log adjusted-price z <= -1'};}
export function realPriceDislocation(price,cpi){const real=[],usedMonths=[];for(let i=0;i<price.months.length;i++){const m=price.months[i];const[y,mo]=m.split('-').map(Number);const d=new Date(Date.UTC(y,mo-2,1));const prior=ym(d);const cv=cpi.map.get(prior);const pv=price.values[i];if(Number.isFinite(cv)&&cv>0&&Number.isFinite(pv)){real.push(pv/cv);usedMonths.push(m);}}const z=zscore(real,true);return{available:z!=null,pass:z!=null?z<=-1:false,z60m:z==null?null:Number(z.toFixed(2)),as_of:usedMonths.at(-1)||null,cpi_as_of:cpi.as_of,rule:'60M log real-price z <= -1; CPI lagged one month for publication timing'};}
export function relativePriceDislocation(price,benchmark){const bmap=new Map(benchmark.months.map((m,i)=>[m,benchmark.values[i]]));const rel=[],usedMonths=[];for(let i=0;i<price.months.length;i++){const m=price.months[i],pv=price.values[i],bv=bmap.get(m);if(Number.isFinite(pv)&&pv>0&&Number.isFinite(bv)&&bv>0){rel.push(pv/bv);usedMonths.push(m);}}const z=zscore(rel,true);return{available:z!=null,pass:z!=null?z<=-1:false,z60m:z==null?null:Number(z.toFixed(2)),as_of:usedMonths.at(-1)||null,benchmark:'SPY',rule:'60M log relative-price z <= -1 versus SPY'};}
export function levelHighDislocation(series,priceAsOf){const months=series.months.filter(m=>m<=priceAsOf);const vals=months.map(m=>series.map.get(m)).filter(Number.isFinite);const z=zscore(vals,false);return{available:z!=null,pass:z!=null?z>=1:false,z60m:z==null?null:Number(z.toFixed(2)),level:vals.length?Number(vals.at(-1).toFixed(2)):null,as_of:months.at(-1)||null,rule:'60M level z >= +1'};}
