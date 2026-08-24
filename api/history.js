import { getMoneyHistory } from '../lib/money-history.js';
import { FROZEN_STATE } from '../lib/state.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'public, max-age=0, must-revalidate');
  try {
    const history = getMoneyHistory();
    const latest = history.rows.at(-1);
    const core = FROZEN_STATE.money;
    if (latest.available_date !== core.available_date) {
      throw new Error(`History/Core date mismatch: ${latest.available_date} vs ${core.available_date}`);
    }
    const checks = [
      [latest.usd_yoy_pct, core.usd_yoy_pct, 'USD YoY'],
      [latest.fx_neutral_yoy_pct, core.fx_neutral_yoy_pct, 'FX-neutral YoY'],
      [latest.usd_score, core.usd_score, 'USD score'],
      [latest.fx_neutral_score, core.fxn_score, 'FX-neutral score']
    ];
    for (const [a, b, label] of checks) {
      if (a == null || b == null || Math.abs(a - b) > 0.0002) {
        throw new Error(`${label} history/Core mismatch`);
      }
    }
    return res.status(200).json(history);
  } catch (e) {
    return res.status(500).json({ error: e.message, endpoint: '/api/history' });
  }
}
