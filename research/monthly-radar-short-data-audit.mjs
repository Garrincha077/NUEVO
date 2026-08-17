const FRED='https://fred.stlouisfed.org/graph/fredgraph.csv';
const cutoff=(()=>{const d=new Date();d.setUTCDate(1);d.setUTCMonth(d.getUTCMonth()-1);return `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}`})();
function csvRows(t){const lines=t.trim().split(/\r?\n/);if(lines.length<2)return[];const h=lines[0].split(',');return lines.slice(1).map(l=>{const c=l.split(',');return Object.fromEntries(h.map((k,i)=>[k,c[i]]))})}
async function fredMonthlyLast(id,start='2003-01-01'){const r=await fetch(`${FRED}?id=${id}&cosd=${start}`,{headers:{'User-Agent':'GMLI-short-audit/1.1'}});if(!r.ok)throw new Error(`FRED ${id} ${r.status}`);const rows=csvRows(await r.text()),by=new Map();for(const x of rows){const date=String(x.observation_date||x.DATE||Object.values(x)[0]),m=date.slice(0,7),v=Number(x[id]);if(m&&Number.isFinite(v)&&m<=cutoff)by.set(m,v)}return by}
const ids=['DFII10','DTWEXBGS','BAA10Y','NFCI','CPIAUCSL'];
const maps={};
for(const id of ids){maps[id]=await fredMonthlyLast(id);const ks=[...maps[id].keys()].sort();console.log(id,{n:ks.length,first:ks[0],last:ks.at(-1),sample2019:maps[id].get('2019-12'),sample2020:maps[id].get('2020-03'),sample2022:maps[id].get('2022-12')});}
const common=[...maps.DFII10.keys()].filter(m=>maps.DTWEXBGS.has(m)&&maps.BAA10Y.has(m)&&maps.NFCI.has(m)).sort();
console.log('COMMON_4',{n:common.length,first:common[0],last:common.at(-1),pre2023:common.filter(m=>m<'2023-01').length,post2023:common.filter(m=>m>='2023-01').length});
