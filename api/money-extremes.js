import historyHandler from './history.js';

async function buildCanonicalHistory() {
  let statusCode = 200;
  let body;
  const res = {
    setHeader() {},
    status(code) { statusCode = code; return this; },
    json(value) { body = value; return this; },
    send(value) { body = value; return this; },
    end(value) { if (value !== undefined) body = value; return this; }
  };
  await historyHandler({ method: 'GET', query: {}, headers: {} }, res);
  if (statusCode < 200 || statusCode >= 300 || body?.error) {
    throw new Error(`Canonical history failed: HTTP ${statusCode} ${body?.error || ''}`.trim());
  }
  return body;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'public, max-age=0, must-revalidate');
  try {
    const [{ buildMoneyExtremes }, history] = await Promise.all([
      import('../scripts/pages-extremes-guide.mjs'),
      buildCanonicalHistory()
    ]);
    return res.status(200).json(buildMoneyExtremes(history));
  } catch (e) {
    return res.status(500).json({ error: e.message, endpoint: '/api/money-extremes' });
  }
}
