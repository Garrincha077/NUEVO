import fs from 'node:fs';

// Reproducible data-availability correction only.
// The pre-specified short rules are left unchanged; the ICE BofA HY OAS series
// exposed through fredgraph.csv only returned 2023-08 onward in the audit run.
// Replace that unavailable long-history input with FRED BAA10Y, a long-history
// Baa corporate spread versus 10Y Treasury credit-stress proxy.
// Network retry/backoff changes transport robustness only; model/data rules stay fixed.
let src=fs.readFileSync('research/monthly-radar-short-macro-backtest.mjs','utf8')
  .replaceAll('BAMLH0A0HYM2','BAA10Y')
  .replaceAll('US HY OAS','US Baa-Treasury credit spread proxy')
  .replaceAll('await fetch(', 'await fetchRetry(');

const retryHelper=`async function fetchRetry(url,opts={},attempts=5){
  let last;
  for(let i=0;i<attempts;i++){
    try{
      const r=await globalThis.fetch(url,opts);
      if(r.ok || r.status<500 || r.status===429)return r;
      last=new Error(\`HTTP \${r.status}\`);
    }catch(e){last=e;}
    if(i<attempts-1)await new Promise(resolve=>setTimeout(resolve,1000*(2**i)));
  }
  throw last||new Error('fetch failed after retries');
}\n`;
src=src.replace("const ASSETS={", retryHelper+"\nconst ASSETS={");

const tmp='research/.monthly-radar-short-macro-baa.tmp.mjs';
fs.writeFileSync(tmp,src);
try{
  await import(`./.monthly-radar-short-macro-baa.tmp.mjs?run=${Date.now()}`);
} finally {
  try{fs.unlinkSync(tmp)}catch{}
}
