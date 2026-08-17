import fs from 'node:fs';

// Reproducible data-availability correction only.
// The pre-specified short rules are left unchanged; the ICE BofA HY OAS series
// exposed through fredgraph.csv only returned 2023-08 onward in the audit run.
// Replace that unavailable long-history input with FRED BAA10Y, a long-history
// Baa corporate spread versus 10Y Treasury credit-stress proxy.
const src=fs.readFileSync('research/monthly-radar-short-macro-backtest.mjs','utf8')
  .replaceAll('BAMLH0A0HYM2','BAA10Y')
  .replaceAll('US HY OAS','US Baa-Treasury credit spread proxy');
const tmp='research/.monthly-radar-short-macro-baa.tmp.mjs';
fs.writeFileSync(tmp,src);
try{
  await import(`./.monthly-radar-short-macro-baa.tmp.mjs?run=${Date.now()}`);
} finally {
  try{fs.unlinkSync(tmp)}catch{}
}
