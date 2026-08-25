import fs from 'node:fs';
import path from 'node:path';

const SOURCE_REL = 'research/global-money-v2/latest/global_money_v2.csv';
const SOURCE = path.join(process.cwd(), 'research/global-money-v2/latest/global_money_v2.csv');

function numberOrNull(value) {
  if (value == null || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export function getMoneyHistory() {
  const text = fs.readFileSync(SOURCE, 'utf8').trim();
  const lines = text.split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) throw new Error('Global Money v2 history is empty');
  const headers = lines[0].split(',');
  const rows = lines.slice(1).map(line => {
    const cols = line.split(',');
    const raw = Object.fromEntries(headers.map((h, i) => [h, cols[i] ?? '']));
    return {
      month: raw.month,
      available_date: raw.available_date,
      usd_yoy_pct: numberOrNull(raw.gbm_usd_yoy_pct),
      fx_neutral_yoy_pct: numberOrNull(raw.gbm_fxn_yoy_pct),
      fx_effect_pp: numberOrNull(raw.fx_effect_pp),
      usd_score: numberOrNull(raw.usd_score),
      fx_neutral_score: numberOrNull(raw.fxn_score)
    };
  }).filter(x => x.month && x.available_date && x.usd_yoy_pct != null && x.fx_neutral_yoy_pct != null);

  if (!rows.length) throw new Error('Global Money v2 history has no valid rows');
  const latest = rows.at(-1);
  return {
    schema_version: 'gmli-money-history-v1.0',
    engine_version: 'GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL',
    evidence_tier: 'CORE_HISTORY',
    frequency: 'monthly',
    source_of_truth: SOURCE_REL,
    source_note: 'Same promoted official-source Global Money V2 pipeline used by the active Money Core; no separate database is required.',
    score_note: 'Score is a normalized historical position, not a percentage return or forecast. Bands: 0-25 strong risk-off, 25-40 risk-off, 40-60 neutral, 60-75 risk-on, 75-100 strong risk-on.',
    yoy_note: 'YoY is annual global broad-money growth. USD-translated includes currency translation; FX-neutral isolates underlying local-currency money growth as defined by the frozen V2 methodology.',
    start_month: rows[0].month,
    latest_month: latest.month,
    latest_available_date: latest.available_date,
    rows
  };
}
