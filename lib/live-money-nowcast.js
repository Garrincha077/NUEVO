import { MONEY_NOWCAST as FALLBACK } from './nowcast-state.js';

const CORE_REFERENCE = '2026-02-28';
const CORE_MONTH = '2026-02';
const TTL_MS = 30 * 60 * 1000;
let CACHE = null;

function ym(x){ return String(x || '').slice(0,7); }
function round(x,n=2){ return Number.isFinite(x) ? Number(x.toFixed(n)) : null; }

async function getText(url, ms=12000, headers={}) {
  const c = new AbortController();
  const timer = setTimeout(() => c.abort(), ms);
  try {
    const r = await fetch(url, {
      headers: { 'user-agent':'GMLI-Research-Copilot/2.3', accept:'text/html,text/csv,application/json,*/*', ...headers },
      signal: c.signal,
      cache: 'no-store'
    });
    if (!r.ok) throw new Error(`HTTP ${r.status} ${url}`);
    return await r.text();
  } finally { clearTimeout(timer); }
}

function compare(latest, ref) {
  if (!Number.isFinite(latest) || !Number.isFinite(ref)) return {direction:'UNKNOWN',delta_vs_core_pp:null};
  const d = latest-ref;
  return {
    direction: d > .25 ? 'ACCELERATING' : d < -.25 ? 'DECELERATING' : 'STABLE',
    delta_vs_core_pp: round(d,2)
  };
}

function block({name,aggregate,source,source_url,latest_date,latest_yoy_pct,core_reference_yoy_pct,status='OK',note=null}) {
  const c = compare(latest_yoy_pct,core_reference_yoy_pct);
  return {
    name, aggregate, evidence_tier:'RESEARCH', status, source, source_url,
    latest_date, latest_yoy_pct:round(latest_yoy_pct,4),
    core_reference_date:CORE_MONTH, core_reference_yoy_pct:round(core_reference_yoy_pct,4),
    direction_vs_core:c.direction, delta_vs_core_pp:c.delta_vs_core_pp,
    expanding_yoy:Number.isFinite(latest_yoy_pct)?latest_yoy_pct>0:null, note
  };
}

function parseFredCsv(csv) {
  const lines = String(csv).trim().split(/\r?\n/);
  const out=[];
  for (const line of lines.slice(1)) {
    const [date,raw] = line.split(',');
    const value=Number(raw);
    if (date && Number.isFinite(value)) out.push({date,value});
  }
  return out;
}
function byMonth(s,m){ return s.find(x=>ym(x.date)===m) || null; }
function last(s){ return s?.length ? s[s.length-1] : null; }
function yoyFromLevels(s,m){
  const cur=byMonth(s,m); if(!cur) return null;
  const [y,mo]=m.split('-').map(Number);
  const prev=byMonth(s,`${y-1}-${String(mo).padStart(2,'0')}`);
  return prev?.value ? ((cur.value/prev.value)-1)*100 : null;
}
async function fredSeries(id,start='2025-01-01'){
  const u=`https://fred.stlouisfed.org/graph/fredgraph.csv?id=${encodeURIComponent(id)}&cosd=${start}`;
  return parseFredCsv(await getText(u,10000,{accept:'text/csv'}));
}
async function usBlock(){
  const s=await fredSeries('M2SL','2025-01-01');
  const l=last(s); if(!l) throw new Error('No US M2');
  const m=ym(l.date);
  return block({name:'United States',aggregate:'M2',source:'Federal Reserve / FRED M2SL',source_url:'https://fred.stlouisfed.org/series/M2SL',latest_date:m,latest_yoy_pct:yoyFromLevels(s,m),core_reference_yoy_pct:yoyFromLevels(s,CORE_MONTH),note:'Live current-vintage monthly M2; YoY calculated from levels.'});
}
function splitCsv(line){const out=[];let cur='',q=false;for(let i=0;i<line.length;i++){const c=line[i];if(c==='"'){if(q&&line[i+1]==='"'){cur+='"';i++;}else q=!q;}else if(c===','&&!q){out.push(cur);cur='';}else cur+=c;}out.push(cur);return out;}
function parseCsvRows(csv){const lines=String(csv).trim().split(/\r?\n/);if(lines.length<2)return[];const h=splitCsv(lines[0]);return lines.slice(1).map(line=>{const v=splitCsv(line),o={};h.forEach((k,i)=>o[k]=v[i]);return o;});}
async function euroBlock(){
  const key='M.U2.Y.V.M30.X.I.U2.2300.Z01.A';
  const url=`https://data-api.ecb.europa.eu/service/data/BSI/${key}?startPeriod=2026-02&format=csvdata`;
  const rows=parseCsvRows(await getText(url,20000,{accept:'text/csv'})).map(r=>({date:r.TIME_PERIOD||r.TIME_PERIOD_START||r.TIME_PERIOD_END,value:Number(r.OBS_VALUE)})).filter(x=>x.date&&Number.isFinite(x.value)).sort((a,b)=>String(a.date).localeCompare(String(b.date)));
  const l=last(rows),ref=rows.find(x=>ym(x.date)===CORE_MONTH);if(!l)throw new Error('No ECB M3');
  return block({name:'Euro area',aggregate:'M3',source:'ECB Data Portal BSI',source_url:'https://data.ecb.europa.eu/data/datasets/BSI/BSI.M.U2.Y.V.M30.X.I.U2.2300.Z01.A',latest_date:ym(l.date),latest_yoy_pct:l.value,core_reference_yoy_pct:ref?.value,note:'Live official ECB annual-growth M3 series.'});
}
function stripHtml(s){return String(s||'').replace(/<script[\s\S]*?<\/script>/gi,' ').replace(/<style[\s\S]*?<\/style>/gi,' ').replace(/<[^>]+>/g,' ').replace(/&nbsp;|&#160;/gi,' ').replace(/&amp;/gi,'&').replace(/\s+/g,' ').trim();}
async function japanBlock(){
  const url='https://www.stat-search.boj.or.jp/ssi/mtshtml/md02_m_1_en.html';
  const text=stripHtml(await getText(url,15000));
  const re=/(20\d{2}\/(?:0[1-9]|1[0-2]))\s+(-?\d+(?:\.\d+)?)/g;const map=new Map();let m;while((m=re.exec(text))){const d=m[1].replace('/','-');if(!map.has(d))map.set(d,Number(m[2]));}
  const rows=[...map.entries()].map(([date,value])=>({date,value})).sort((a,b)=>a.date.localeCompare(b.date));const l=last(rows),ref=rows.find(x=>x.date===CORE_MONTH);if(!l)throw new Error('No BOJ M2');
  return block({name:'Japan',aggregate:'M2',source:'Bank of Japan Time-Series Data Search',source_url:url,latest_date:l.date,latest_yoy_pct:l.value,core_reference_yoy_pct:ref?.value,note:'Live BOJ M2 YoY from the official table.'});
}
function pbcSearchUrl(query){const u=new URL('https://wzdig.pbc.gov.cn/search/pcRender');u.searchParams.set('pNo','1');u.searchParams.set('pageId','c177a85bd02b4114bebebd210809f691');u.searchParams.set('q',query);u.searchParams.set('sr','date desc');return u.toString();}
async function findPbcReport(year,month){const q=`${year}年${month}月金融统计数据报告`;const html=(await getText(pbcSearchUrl(q),8000)).replace(/&amp;/g,'&');const urls=html.match(/https?:\/\/(?:www\.)?pbc\.gov\.cn\/[^"'<> ]+\/index\.html/g)||[];for(const url of urls.slice(0,8)){try{const text=stripHtml(await getText(url,6000));if(text.includes(`${year}年${month}月`)&&text.includes('金融统计')&&(text.includes('广义货币')||text.includes('(M2)'))){const g=text.match(/广义货币(?:增长)?\s*([0-9]+(?:\.[0-9]+)?)%/)||text.match(/广义货币\s*\(M2\)[^。]{0,120}?同比增长\s*([0-9]+(?:\.[0-9]+)?)%/)||text.match(/M2[^。]{0,120}?同比增长\s*([0-9]+(?:\.[0-9]+)?)%/);if(g)return{url,yoy:Number(g[1]),month:`${year}-${String(month).padStart(2,'0')}`};}}}catch{}}return null;}
async function chinaBlock(){const now=new Date();let l=null;for(let back=0;back<4&&!l;back++){const d=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth()-back,1));l=await findPbcReport(d.getUTCFullYear(),d.getUTCMonth()+1);}const ref=await findPbcReport(2026,2);if(!l)throw new Error('Latest PBoC M2 not machine-readable');return block({name:'China',aggregate:'M2',source:'People’s Bank of China Financial Statistics Report',source_url:l.url,latest_date:l.month,latest_yoy_pct:l.yoy,core_reference_yoy_pct:ref?.yoy,note:'Live official PBoC monthly M2 when machine-readable.'});}
async function dollarOverlay(){const s=await fredSeries('DTWEXBGS','2026-02-01');const l=last(s),ref=last(s.filter(x=>x.date<=CORE_REFERENCE));if(!l||!ref)throw new Error('No broad dollar data');const pct=((l.value/ref.value)-1)*100;return{evidence_tier:'RESEARCH',status:'OK',source:'Federal Reserve / FRED Broad Dollar Index DTWEXBGS',source_url:'https://fred.stlouisfed.org/series/DTWEXBGS',core_reference_date:ref.date,latest_date:l.date,pct_change_since_core:round(pct,2),translation:pct < -1?'TAILWIND_WEAKER_USD':pct > 1?'HEADWIND_STRONGER_USD':'NEUTRAL',note:'Live translation overlay only; not frozen FX-neutral methodology.'};}
function fallbackBlock(key,error){const f=FALLBACK.blocks?.[key];if(!f)return{evidence_tier:'RESEARCH',status:'UNAVAILABLE',error:String(error)};return{...f,status:'FALLBACK_LAST_VERIFIED',live_error:String(error),note:`${f.note||''} Live fetch failed; using last verified snapshot.`.trim()};}
export function summarizeLiveNowcast(state){const blocks=Object.values(state?.blocks||{});const usable=blocks.filter(x=>['OK','FALLBACK_LAST_VERIFIED','OK_VERIFIED_SECONDARY'].includes(x.status)&&Number.isFinite(x.latest_yoy_pct));const comp=usable.filter(x=>Number.isFinite(x.core_reference_yoy_pct));const accelerating=comp.filter(x=>x.direction_vs_core==='ACCELERATING').length;const decelerating=comp.filter(x=>x.direction_vs_core==='DECELERATING').length;const stable=comp.filter(x=>x.direction_vs_core==='STABLE').length;const expanding=usable.filter(x=>x.expanding_yoy===true).length;const tilt=accelerating>=3&&expanding===usable.length?'SUPPORTIVE_MIXED':decelerating>=3?'DETERIORATING':accelerating>=decelerating?'NEUTRAL_TO_SUPPORTIVE':'MIXED';return{label:accelerating>=3?'BROADLY_EXPANDING_MIXED_ACCELERATION':decelerating>=3?'BROADLY_DECELERATING':'MIXED',tilt,score:null,score_status:'NOT_COMPUTED',coverage:`${usable.length}/4`,comparisons_available:`${comp.length}/4`,accelerating,stable,decelerating,expanding_yoy:expanding,methodology:'Unweighted directional freshness overlay versus frozen February reference. Live official sources with explicit last-verified fallback.'};}
export function moneyNowcastFreshness(blocks){const names={us:'US',euro_area:'EA',japan:'JP',china:'CN'};return Object.entries(blocks||{}).map(([k,v])=>`${names[k]||k} ${v.latest_date||'n/a'}${v.status==='FALLBACK_LAST_VERIFIED'?'*':''}`).join('; ');}
function inference(state,summary){const parts=Object.values(state.blocks||{}).map(x=>`${x.name||'block'} ${x.direction_vs_core||'UNKNOWN'}`);const usd=state.usd_translation?.translation;return`${summary.tilt}: ${parts.join(', ')}.${usd?` USD translation: ${usd}.`:''}`;}
export async function getLiveMoneyNowcast(){if(CACHE&&(Date.now()-CACHE.at)<TTL_MS)return CACHE.value;const jobs=[['us',usBlock],['euro_area',euroBlock],['japan',japanBlock],['china',chinaBlock]];const entries=await Promise.all(jobs.map(async([k,fn])=>{try{return[k,await fn()];}catch(e){return[k,fallbackBlock(k,e?.message||e)];}}));const blocks=Object.fromEntries(entries);let usd_translation;try{usd_translation=await dollarOverlay();}catch(e){usd_translation={...(FALLBACK.usd_translation||{}),status:'FALLBACK_LAST_VERIFIED',live_error:String(e?.message||e)};}const state={version:'GMLI Current Money Nowcast v1.3 LIVE',as_of:new Date().toISOString(),evidence_tier:'RESEARCH',role:'FRESHNESS_OVERLAY_ONLY',source_mode:'LIVE_OFFICIAL_WITH_LAST_VERIFIED_FALLBACK',core_reference:{date:CORE_REFERENCE,guardrail:'Does not alter frozen Money Core, weights, FX-neutral method, lags, horizons or thresholds.'},blocks,usd_translation};const nowcast=summarizeLiveNowcast(state);state.nowcast=nowcast;state.interpretation={engine_fact:`Frozen USD and FX-neutral Money Core remain dated ${CORE_REFERENCE}.`,current_research_inference:inference(state,nowcast)};CACHE={at:Date.now(),value:state};return state;}
