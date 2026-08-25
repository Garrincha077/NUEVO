import { MONEY_NOWCAST as VERIFIED } from './nowcast-state.js';
import { ACTIVE_MONEY_V2 } from './money-v2-active.js';

const COMPARISON_REFERENCE = '2026-02-28';
const TTL_MS = 30 * 60 * 1000;
let CACHE = null;

function clone(x) {
  return JSON.parse(JSON.stringify(x));
}

export function summarizeLiveNowcast(state) {
  const blocks = Object.values(state?.blocks || {});
  const usable = blocks.filter(x => Number.isFinite(x.latest_yoy_pct));
  const comp = usable.filter(x => Number.isFinite(x.core_reference_yoy_pct));
  const accelerating = comp.filter(x => x.direction_vs_core === 'ACCELERATING').length;
  const decelerating = comp.filter(x => x.direction_vs_core === 'DECELERATING').length;
  const stable = comp.filter(x => x.direction_vs_core === 'STABLE').length;
  const expanding = usable.filter(x => x.expanding_yoy === true).length;
  const tilt = accelerating >= 3 && expanding === usable.length
    ? 'SUPPORTIVE_MIXED'
    : decelerating >= 3
      ? 'DETERIORATING'
      : accelerating >= decelerating
        ? 'NEUTRAL_TO_SUPPORTIVE'
        : 'MIXED';

  return {
    label: accelerating >= 3
      ? 'BROADLY_EXPANDING_MIXED_ACCELERATION'
      : decelerating >= 3
        ? 'BROADLY_DECELERATING'
        : 'MIXED',
    tilt,
    score: null,
    score_status: 'NOT_COMPUTED',
    coverage: `${usable.length}/4`,
    comparisons_available: `${comp.length}/4`,
    accelerating,
    stable,
    decelerating,
    expanding_yoy: expanding,
    methodology: 'Unweighted directional freshness overlay versus the preserved February 2026 historical comparison reference. The active promoted Money Core is Money V2; this reference is used only for nowcast acceleration comparisons.'
  };
}

export function moneyNowcastFreshness(blocks) {
  const names = { us: 'US', euro_area: 'EA', japan: 'JP', china: 'CN' };
  return Object.entries(blocks || {})
    .map(([k, v]) => `${names[k] || k} ${v.latest_date || 'n/a'}*`)
    .join('; ');
}

function buildVerifiedSnapshot() {
  const blocks = clone(VERIFIED.blocks || {});
  for (const block of Object.values(blocks)) {
    block.evidence_tier = 'RESEARCH';
    block.status = 'FALLBACK_LAST_VERIFIED';
  }

  const state = {
    version: 'GMLI Current Money Nowcast v1.3 VERIFIED',
    as_of: new Date().toISOString(),
    evidence_tier: 'RESEARCH',
    role: 'FRESHNESS_OVERLAY_ONLY',
    source_mode: 'LAST_VERIFIED_REQUEST_SAFE',
    runtime_mode: 'VALIDATED_SNAPSHOT',
    live_attempted: false,
    validated_reference: {
      date: COMPARISON_REFERENCE,
      role: 'HISTORICAL_COMPARISON_REFERENCE_ONLY',
      active_core_date: ACTIVE_MONEY_V2.available_date,
      active_core_version: 'GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL',
      methodology_status: 'FROZEN_V2_SPEC',
      guardrail: 'Freshness data do not change country weights, FX-neutral methodology, lags, horizons, thresholds, train/validation split or FDR rules and never auto-promote or replace the Money Core.'
    },
    blocks,
    usd_translation: {
      ...clone(VERIFIED.usd_translation || {}),
      evidence_tier: 'RESEARCH',
      status: 'FALLBACK_LAST_VERIFIED'
    }
  };

  const nowcast = summarizeLiveNowcast(state);
  state.nowcast = nowcast;
  state.interpretation = {
    engine_fact: `The active promoted Money Core is GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL, available ${ACTIVE_MONEY_V2.available_date}. The ${COMPARISON_REFERENCE} vintage is retained only as the historical reference for nowcast acceleration comparisons.`,
    current_research_inference: `${nowcast.tilt}: verified monthly snapshots are US ${blocks.us?.latest_date}, EA ${blocks.euro_area?.latest_date}, JP ${blocks.japan?.latest_date}, CN ${blocks.china?.latest_date}. Request-time live parsing is disabled; scheduled validated refresh is the intended path.`
  };
  return state;
}

export async function getLiveMoneyNowcast() {
  if (CACHE && (Date.now() - CACHE.at) < TTL_MS) return CACHE.value;
  const value = buildVerifiedSnapshot();
  CACHE = { at: Date.now(), value };
  return value;
}
