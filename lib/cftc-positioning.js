import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const CFTC_BASE='https://publicreporting.cftc.gov';
const TFF_DATASET='gpe5-46if';
const DISAGG_DATASET='72hh-3qpy';
const SNAPSHOT_PATH=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..','research','cftc-positioning','latest','positioning.json');
const numeric=x=>{const n=Number(x);return Number.isFinite(n)?n:null;};
function mean(xs){const v=xs.filter(Number.isFinite);return v.length?v.reduce((a,b)=>a+b,0)/v.length:null;}
function std(xs){const v=xs.filter(Number.isFinite);if(v.length<2)return null;const m=mean(v);return Math.sqrt(v.reduce((a,b)=>a+(b-m)**2,0)/(v.length-1));}
function percentileRank(xs,x){const v=xs.filter(Number.isFinite).sort((a,b)=>a-b);if(!v.length||!Number.isFinite(x))return null;return 100*v.filter(y=>y<=x).length/v.length;}
function start3y(){const d=new Date();d.setUTCFullYear(d.getUTCFullYear()-3);d.setUTCMonth(d.getUTCMonth()-1);return d.toISOString().slice(0,10)+'T00:00:00.000';}
async function loadOfficialSnapshot(){try{const j=JSON.parse(await fs.readFile(SNAPSHOT_PATH,'utf8'));if(j?.status==='PASS_CFTC_POSITIONING_REFRESH'&&j?.source_contract==='CFTC_OFFICIAL_HISTORICAL_COMPRESSED_FUTURES_ONLY'&&j?.assets)return{...j,source_mode:'ARCHIVED_OFFICIAL_CFTC_SNAPSHOT'};}catch{}return null;}
async function metadata(id){const r=await fetch(`${CFTC_BASE}/api/views/${id}`,{headers:{'User-Agent':'GMLI/2.5'}});if(!r.ok)throw new Error(`CFTC metadata ${id} ${r.status}`);const j=await r.json();const cols=j.columns||[];const byName=new Map(cols.map(c=>[String(c.name||'').toLowerCase(),c.fieldName]));const byField=new Map(cols.map(c=>[String(c.fieldName||'').toLowerCase(),c.fieldName]));const find=(...candidates)=>{for(const c of candidates){const k=String(c).toLowerCase();if(byName.has(k))return byName.get(k);if(byField.has(k))return byField.get(k);}for(const c of candidates){const k=String(c).toLowerCase();const hit=cols.find(col=>String(col.name||'').toLowerCase().includes(k)||String(col.fieldName||'').toLowerCase().includes(k));if(hit)return hit.fieldName;}return null;};return{find};}
async function fetchDataset(id,kind){const m=await metadata(id);const date=m.find('Report_Date_as_YYYY_MM_DD','report_date_as_yyyy_mm_dd');const market=m.find('Market_and_Exchange_Names','market_and_exchange_names','Contract_Market_Name','contract_market_name');const commodity=m.find('Commodity Name','commodity_name');const oi=m.find('Open_Interest_All','open_interest_all');const long=kind==='tff'?m.find('Lev_Money_Positions_Long_All','lev_money_positions_long_all','lev_money_positions_long'):m.find('M_Money_Positions_Long_All','m_money_positions_long_all','m_money_positions_long');const short=kind==='tff'?m.find('Lev_Money_Positions_Short_All','lev_money_positions_short_all','lev_money_positions_short'):m.find('M_Money_Positions_Short_All','m_money_positions_short_all','m_money_positions_short');if(![date,market,oi,long,short].every(Boolean))throw new Error(`CFTC ${kind} field discovery failed`);const fields=[date,market,commodity,oi,long,short].filter(Boolean);const u=new URL(`${CFTC_BASE}/resource/${id}.json`);u.searchParams.set('$select',fields.join(','));u.searchParams.set('$where',`${date} >= '${start3y()}'`);u.searchParams.set('$order',`${date} ASC`);u.searchParams.set('$limit','50000');const r=await fetch(u,{headers:{'User-Agent':'GMLI/2.5'}});if(!r.ok)throw new Error(`CFTC ${kind} data ${r.status}`);const rows=await r.json();return rows.map(x=>({date:String(x[date]||'').slice(0,10),market:String(x[market]||''),commodity:commodity?String(x[commodity]||''):'',oi:numeric(x[oi]),long:numeric(x[long]),short:numeric(x[short])})).filter(x=>x.date&&Number.isFinite(x.oi)&&x.oi>0&&Number.isFinite(x.long)&&Number.isFinite(x.short));}
function containsAny(text,terms){const s=String(text||'').toUpperCase();return terms.some(t=>s.includes(t));}
function aggregateByDate(rows,match){const m=new Map();for(const r of rows){if(!match(r))continue;const x=m.get(r.date)||{oi:0,long:0,short:0};x.oi+=r.oi;x.long+=r.long;x.short+=r.short;m.set(r.date,x);}return[...m.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([date,x])=>({date,value:x.oi>0?(x.long-x.short)/x.oi:null,oi:x.oi,long:x.long,short:x.short})).filter(x=>Number.isFinite(x.value));}
function summarize(series,label,source){if(!series.length)return{available:false,pass:false,crowded:false,label,source,evidence_tier:'RESEARCH',role:'ENTRY_QUALITY_ONLY',error:'No matching CFTC rows'};const vals=series.map(x=>x.value),cur=series.at(-1),pct=percentileRank(vals,cur.value),sd=std(vals),mu=mean(vals),z=sd&&sd>0?(cur.value-mu)/sd:null;return{available:true,pass:pct!=null&&pct<=25,crowded:pct!=null&&pct>=75,label,as_of:cur.date,net_spec_pct_oi:Number((100*cur.value).toFixed(2)),percentile_3y:pct==null?null:Number(pct.toFixed(1)),z_3y:z==null?null:Number(z.toFixed(2)),evidence_tier:'RESEARCH',role:'ENTRY_QUALITY_ONLY',source,rule:'<=25th percentile contrarian-friendly; >=75th crowded'};}
function commodityComponent(rows,terms,label){return summarize(aggregateByDate(rows,r=>containsAny(`${r.market} ${r.commodity}`,terms)),label,'CFTC Disaggregated Futures Only / Managed Money');}
function compositePositioning(components,label,source,minComponents=2){const available=components.filter(x=>x.available&&Number.isFinite(x.percentile_3y));const pct=mean(available.map(x=>x.percentile_3y));return{available:available.length>=minComponents,pass:pct!=null&&pct<=25,crowded:pct!=null&&pct>=75,label,as_of:available.map(x=>x.as_of).filter(Boolean).sort().at(-1)||null,percentile_3y:pct==null?null:Number(pct.toFixed(1)),components,evidence_tier:'RESEARCH',role:'ENTRY_QUALITY_ONLY',source,rule:'<=25th percentile contrarian; >=75th crowded'};}

export async function buildPositioning(){
  const officialSnapshot=await loadOfficialSnapshot();
  if(officialSnapshot)return officialSnapshot;
  const allKeys=['SPY','QQQ','IWM','GLD','SLV','DBC','USO','CPER','DBA','TLT','IEF','FXY','HYG','VNQ','EEM','VEA','BTC'];
  const result={as_of:new Date().toISOString(),status:'RESEARCH_ASSET_SPECIFIC_POSITIONING',methodology:'Net speculative position / open interest; 3Y percentile; futures-only. Direct futures mappings where available; broad baskets use transparent component averages.',source_mode:'LIVE_PRE_FALLBACK',sources:{tff:`${CFTC_BASE}/resource/${TFF_DATASET}.json`,disaggregated:`${CFTC_BASE}/resource/${DISAGG_DATASET}.json`},assets:{}};
  try{
    const[tff,dis]=await Promise.all([fetchDataset(TFF_DATASET,'tff'),fetchDataset(DISAGG_DATASET,'disagg')]);
    result.assets.SPY=summarize(aggregateByDate(tff,r=>containsAny(r.market,['S&P 500','E-MINI S&P','MICRO E-MINI S&P'])),'S&P 500 leveraged money','CFTC TFF Futures Only / Leveraged Money');
    result.assets.QQQ=summarize(aggregateByDate(tff,r=>containsAny(r.market,['NASDAQ-100','NASDAQ 100','E-MINI NASDAQ','MICRO E-MINI NASDAQ'])),'Nasdaq-100 leveraged money','CFTC TFF Futures Only / Leveraged Money');
    result.assets.IWM=summarize(aggregateByDate(tff,r=>containsAny(r.market,['RUSSELL 2000','E-MINI RUSSELL','MICRO E-MINI RUSSELL'])),'Russell 2000 leveraged money','CFTC TFF Futures Only / Leveraged Money');
    result.assets.TLT=summarize(aggregateByDate(tff,r=>containsAny(r.market,['10-YEAR U.S. TREASURY','10 YEAR U.S. TREASURY','U.S. TREASURY BOND','TREASURY BONDS','ULTRA U.S. TREASURY'])),'US long-duration Treasury leveraged money proxy','CFTC TFF Futures Only / Leveraged Money');
    result.assets.IEF=summarize(aggregateByDate(tff,r=>containsAny(r.market,['5-YEAR U.S. TREASURY','5 YEAR U.S. TREASURY','10-YEAR U.S. TREASURY','10 YEAR U.S. TREASURY'])),'US intermediate Treasury leveraged money proxy','CFTC TFF Futures Only / Leveraged Money');
    result.assets.FXY=summarize(aggregateByDate(tff,r=>containsAny(`${r.market} ${r.commodity}`,['JAPANESE YEN','YEN'])),'Japanese Yen leveraged money','CFTC TFF Futures Only / Leveraged Money');
    result.assets.GLD=commodityComponent(dis,['GOLD'],'Gold managed money');
    result.assets.SLV=commodityComponent(dis,['SILVER'],'Silver managed money');
    result.assets.USO=commodityComponent(dis,['CRUDE OIL','WTI'],'WTI crude managed money');
    result.assets.CPER=commodityComponent(dis,['COPPER'],'Copper managed money');
    const crude=commodityComponent(dis,['CRUDE OIL','WTI'],'Crude');const copper=commodityComponent(dis,['COPPER'],'Copper');const corn=commodityComponent(dis,['CORN'],'Corn');const wheat=commodityComponent(dis,['WHEAT'],'Wheat');
    result.assets.DBC=compositePositioning([crude,copper,corn,wheat],'Broad commodity managed-money proxy','CFTC Disaggregated / crude-copper-corn-wheat percentile average',2);
    const soy=commodityComponent(dis,['SOYBEAN'],'Soybeans');const sugar=commodityComponent(dis,['SUGAR'],'Sugar');const coffee=commodityComponent(dis,['COFFEE'],'Coffee');
    result.assets.DBA=compositePositioning([corn,wheat,soy,sugar,coffee],'Broad agriculture managed-money proxy','CFTC Disaggregated / corn-wheat-soy-sugar-coffee percentile average',3);
    for(const k of ['HYG','VNQ','EEM','VEA','BTC'])result.assets[k]={available:false,pass:false,crowded:false,evidence_tier:'RESEARCH',role:'ENTRY_QUALITY_ONLY',source:'none',note:'No sufficiently direct asset-specific CFTC mapping in current GMLI.'};
    const dates=Object.values(result.assets).map(x=>x.as_of).filter(Boolean).sort();result.latest_report_date=dates.at(-1)||null;
  }catch(e){
    result.error=e.message;
    for(const k of allKeys)result.assets[k]=result.assets[k]||{available:false,pass:false,crowded:false,evidence_tier:'RESEARCH',role:'ENTRY_QUALITY_ONLY',source:'CFTC unavailable',error:e.message};
  }
  return result;
}
