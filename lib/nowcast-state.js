export const MONEY_NOWCAST = {
  version: 'GMLI Current Money Nowcast v1.2',
  evidence_tier: 'RESEARCH',
  role: 'FRESHNESS_OVERLAY_ONLY',
  core_reference: {
    date: '2026-02-28',
    guardrail: 'Does not alter frozen Money Core, weights, FX-neutral method, lags, horizons or thresholds.'
  },
  blocks: {
    us: {
      name: 'United States', aggregate: 'M2', latest_date: '2026-06', latest_yoy_pct: 5.5258,
      core_reference_date: '2026-02', core_reference_yoy_pct: 4.6887,
      direction_vs_core: 'ACCELERATING', delta_vs_core_pp: 0.84, expanding_yoy: true,
      source: 'Federal Reserve / FRED M2SL', source_url: 'https://fred.stlouisfed.org/series/M2SL', status: 'OK'
    },
    euro_area: {
      name: 'Euro area', aggregate: 'M3', latest_date: '2026-06', latest_yoy_pct: 3.3,
      core_reference_date: '2026-02', core_reference_yoy_pct: 2.82,
      direction_vs_core: 'ACCELERATING', delta_vs_core_pp: 0.48, expanding_yoy: true,
      source: 'ECB monetary developments', source_url: 'https://www.ecb.europa.eu/press/stats/md/html/ecb.md2606~5ad5ef1f2a.en.html', status: 'OK'
    },
    japan: {
      name: 'Japan', aggregate: 'M2', latest_date: '2026-07', latest_yoy_pct: 2.2,
      core_reference_date: '2026-02', core_reference_yoy_pct: 1.7,
      direction_vs_core: 'ACCELERATING', delta_vs_core_pp: 0.5, expanding_yoy: true,
      source: 'Bank of Japan Time-Series Data Search', source_url: 'https://www.stat-search.boj.or.jp/ssi/mtshtml/md02_m_1_en.html', status: 'OK',
      note: 'Last-verified fallback updated to July 2026. Live parser remains the primary freshness source.'
    },
    china: {
      name: 'China', aggregate: 'M2', latest_date: '2026-07', latest_yoy_pct: 7.7,
      core_reference_date: '2026-02', core_reference_yoy_pct: 9.0,
      direction_vs_core: 'DECELERATING', delta_vs_core_pp: -1.3, expanding_yoy: true,
      source: 'PBoC-attributed current reporting', status: 'OK_VERIFIED_SECONDARY',
      note: 'Official July release was not indexed in the central-bank listing when checked; value was cross-checked against current PBoC-attributed reporting.'
    }
  },
  usd_translation: {
    status: 'RESEARCH', latest_verified: '2026-08-07', pct_change_since_core: 1.05,
    translation: 'HEADWIND_STRONGER_USD', note: 'Translation overlay only; not frozen FX-neutral Money methodology.'
  }
};

export function summarizeNowcast() {
  const blocks = Object.values(MONEY_NOWCAST.blocks);
  const accelerating = blocks.filter(x => x.direction_vs_core === 'ACCELERATING').length;
  const decelerating = blocks.filter(x => x.direction_vs_core === 'DECELERATING').length;
  const stable = blocks.length - accelerating - decelerating;
  const expanding = blocks.filter(x => x.expanding_yoy).length;
  const tilt = accelerating >= 3 && expanding === blocks.length ? 'SUPPORTIVE_MIXED' : accelerating >= decelerating ? 'NEUTRAL_TO_SUPPORTIVE' : 'DETERIORATING';
  return {
    label: accelerating >= 3 ? 'BROADLY_EXPANDING_MIXED_ACCELERATION' : 'MIXED',
    tilt,
    score: null,
    score_status: 'NOT_COMPUTED',
    coverage: `${blocks.length}/${blocks.length}`,
    comparisons_available: `${blocks.length}/${blocks.length}`,
    accelerating,
    stable,
    decelerating,
    expanding_yoy: expanding,
    methodology: 'Unweighted directional freshness overlay versus frozen February reference.'
  };
}
