export const CONTEXT_ASSETS = ['SPY','QQQ','GLD','DBC'];

function parseCsv(text) {
  const lines = String(text || '').trim().split(/\r?\n/).filter(Boolean);
  if (!lines.length) return [];
  const headers = lines[0].split(',');
  return lines.slice(1).map(line => {
    const cells = line.split(',');
    return Object.fromEntries(headers.map((h, i) => [h, cells[i] ?? '']));
  });
}

function finite(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function round(value, digits = 4) {
  return Number.isFinite(value) ? Number(value.toFixed(digits)) : null;
}

function fundingRows(text) {
  return parseCsv(text).map(r => ({
    observation_month: r.observation_month,
    available_date: r.available_date,
    score: finite(r.effective_score),
    regime: r.regime,
    structural_support_score: finite(r.structural_support_score),
    observed_conditions_score: finite(r.observed_conditions_score)
  })).filter(r => r.observation_month && r.available_date && r.score != null);
}

function fiscalRows(text) {
  return parseCsv(text).map(r => ({
    observation_month: r.observation_month,
    available_date: r.available_date,
    score: finite(r.score),
    regime: r.regime,
    deficit_pct_gdp: finite(r.deficit_pct_gdp),
    fiscal_impulse_pp: finite(r.fiscal_impulse_pp)
  })).filter(r => r.observation_month && r.available_date && r.score != null);
}

function archivedMonthlyPrice(data, asset) {
  const result = data?.chart?.result?.[0];
  const timestamps = result?.timestamp || [];
  const adjusted = result?.indicators?.adjclose?.[0]?.adjclose || [];
  if (!timestamps.length || timestamps.length !== adjusted.length) {
    throw new Error(`Context history archived monthly price malformed for ${asset}`);
  }
  const out = {};
  for (let i = 0; i < timestamps.length; i++) {
    const value = finite(adjusted[i]);
    if (value == null || value <= 0) continue;
    const month = new Date(Number(timestamps[i]) * 1000).toISOString().slice(0, 7);
    out[month] = value;
  }
  if (Object.keys(out).length < 100) throw new Error(`Context history archived monthly price too short for ${asset}`);
  return out;
}

function average(values) {
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function buildMarketRows(prices, cutoffMonth) {
  const common = [...Object.keys(prices[CONTEXT_ASSETS[0]])].filter(month => CONTEXT_ASSETS.every(a => prices[a][month] != null)).sort();
  const rows = [];
  for (const month of common) {
    if (cutoffMonth && month > cutoffMonth) continue;
    const perAsset = {};
    let valid = true;
    for (const asset of CONTEXT_ASSETS) {
      const months = Object.keys(prices[asset]).filter(m => m <= month).sort();
      if (months.length < 13) { valid = false; break; }
      const values = months.map(m => prices[asset][m]);
      const last = values.at(-1);
      const ma10 = average(values.slice(-10));
      const r3 = last / values.at(-4) - 1;
      perAsset[asset] = Boolean(last > ma10 || r3 > 0);
    }
    if (!valid) continue;
    const positive = CONTEXT_ASSETS.filter(a => perAsset[a]).length;
    rows.push({
      month,
      positive,
      total: 4,
      score_0_2: positive >= 3 ? 2 : positive === 2 ? 1 : 0,
      assets_positive: perAsset
    });
  }
  return rows;
}

export function buildContextHistoryFromInputs(report, inputs) {
  const funding = report?.regime?.current_research_inference?.funding || {};
  const fiscal = report?.regime?.current_research_inference?.fiscal || {};
  const roles = report?.signal_role_taxonomy || {};
  const fundingCutoff = funding.available_date || null;
  const fiscalCutoff = fiscal.available_date || null;
  if (!fundingCutoff || !fiscalCutoff) {
    throw new Error('Context history requires active Funding and Fiscal available_date cutoffs from canonical report');
  }

  const allFundingRows = fundingRows(inputs?.funding_csv);
  const allFiscalRows = fiscalRows(inputs?.fiscal_csv);
  const prices = Object.fromEntries(CONTEXT_ASSETS.map(asset => [asset, archivedMonthlyPrice(inputs?.price_json?.[asset], asset)]));

  const fundingFiltered = allFundingRows.filter(r => r.available_date <= fundingCutoff);
  const fiscalFiltered = allFiscalRows.filter(r => r.available_date <= fiscalCutoff);
  const marketHealth = report?.data_health?.items?.find(x => x.key === 'market_structure');
  const marketCutoff = String(marketHealth?.available_date || '').slice(0, 7) || null;
  const marketRows = buildMarketRows(prices, marketCutoff);

  return {
    schema_version: 'gmli-pages-context-history-v1',
    generated_at: report?.generated_at || new Date().toISOString(),
    source: 'VERIFIED_REPOSITORY_HISTORY_AND_ARCHIVED_MONTHLY_PRICE_INPUTS',
    scoring_effect: 'NONE',
    availability_policy: 'ONLY_ROWS_AVAILABLE_ON_OR_BEFORE_ACTIVE_CANONICAL_REPORT_VINTAGE',
    funding: {
      evidence_tier: 'OVERLAY',
      version: funding.version,
      role: roles?.funding_v2?.role || 'REACTIVE_CONFIRMATION',
      active_available_date: fundingCutoff,
      source_file: 'research/funding-v2/latest/history.csv',
      excluded_future_rows: allFundingRows.length - fundingFiltered.length,
      rows: fundingFiltered.map(r => ({
        ...r,
        score: round(r.score),
        structural_support_score: round(r.structural_support_score),
        observed_conditions_score: round(r.observed_conditions_score)
      }))
    },
    fiscal: {
      evidence_tier: 'OVERLAY',
      version: fiscal.version,
      role: roles?.fiscal_v2?.role || 'MIXED',
      active_available_date: fiscalCutoff,
      source_file: 'research/fiscal-v2/latest/history.csv',
      excluded_future_rows: allFiscalRows.length - fiscalFiltered.length,
      historical_caveat: 'Revised FRED history with frozen conservative publication lags; not exact historical release-time vintages.',
      rows: fiscalFiltered.map(r => ({
        ...r,
        score: round(r.score),
        deficit_pct_gdp: round(r.deficit_pct_gdp),
        fiscal_impulse_pp: round(r.fiscal_impulse_pp)
      }))
    },
    market_confirmation: {
      evidence_tier: 'RESEARCH',
      role: roles?.market_confirmation?.role || 'REACTIVE_CONFIRMATION',
      source_files: CONTEXT_ASSETS.map(a => `research/global-money-v2/transfer/latest/raw/${a}-yahoo-monthly.json`),
      methodology: 'Completed-month positive turn per asset = adjusted close above 10M average OR positive 3M return; score 2 for 3-4 positive assets, 1 for 2, else 0. Same fixed definition used by the Funding/Market overlap diagnostic.',
      cutoff_month: marketCutoff,
      rows: marketRows
    },
    signal_role_chain: {
      evidence_tier: 'RESEARCH',
      version: roles.version,
      scoring_effect: roles.scoring_effect || 'NONE',
      historical_series: false,
      note: 'Role taxonomy is categorical interpretation metadata, not a numeric historical signal. No synthetic history is created.'
    }
  };
}
