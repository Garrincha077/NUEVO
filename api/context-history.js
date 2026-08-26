import reportHandler from './report.js';

const ASSETS = ['SPY','QQQ','GLD','DBC'];

async function buildCanonicalReport() {
  let statusCode = 200;
  let body;
  const res = {
    setHeader() {},
    status(code) { statusCode = code; return this; },
    json(value) { body = value; return this; },
    send(value) { body = value; return this; },
    end(value) { if (value !== undefined) body = value; return this; }
  };
  await reportHandler({ method: 'GET', query: {}, headers: {} }, res);
  if (statusCode < 200 || statusCode >= 300 || body?.error) {
    throw new Error(`Canonical report failed: HTTP ${statusCode} ${body?.error || ''}`.trim());
  }
  return body;
}

async function checkedFetch(url, type = 'text') {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Static context input failed: ${response.status} ${url}`);
  return type === 'json' ? response.json() : response.text();
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'public, max-age=0, must-revalidate');
  try {
    const host = req?.headers?.['x-forwarded-host'] || req?.headers?.host || 'gmli-fred-dashboard.vercel.app';
    const proto = req?.headers?.['x-forwarded-proto'] || 'https';
    const base = `${proto}://${host}`;
    const [{ buildContextHistoryFromInputs }, report, fundingCsv, fiscalCsv, pricePairs] = await Promise.all([
      import('../scripts/context-history-core.mjs'),
      buildCanonicalReport(),
      checkedFetch(`${base}/research/funding-v2/latest/history.csv`),
      checkedFetch(`${base}/research/fiscal-v2/latest/history.csv`),
      Promise.all(ASSETS.map(async asset => [
        asset,
        await checkedFetch(`${base}/research/global-money-v2/transfer/latest/raw/${asset}-yahoo-monthly.json`, 'json')
      ]))
    ]);
    const history = buildContextHistoryFromInputs(report, {
      funding_csv: fundingCsv,
      fiscal_csv: fiscalCsv,
      price_json: Object.fromEntries(pricePairs)
    });
    return res.status(200).json(history);
  } catch (e) {
    return res.status(500).json({ error: e.message, endpoint: '/api/context-history' });
  }
}
