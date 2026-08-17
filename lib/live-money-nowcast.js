import { MONEY_NOWCAST as VERIFIED } from './nowcast-state.js';

const CORE_REFERENCE = '2026-02-28';
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
    methodology: 'Unweighted directional freshness overlay versus frozen February reference. Request path uses last-verified current monthly releases; live parser promotion is disabled until source parsers pass validation.'
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
    core_reference: {
      date: CORE_REFERENCE,
      guardrail: 'Does not alter frozen Money Core, weights, FX-neutral method, lags, horizons or thresholds.'
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
    engine_fact: `Frozen USD and FX-neutral Money Core remain dated ${CORE_REFERENCE}.`,
    current_research_inference: `${nowcast.tilt}: verified monthly snapshots are US ${blocks.us?.latest_date}, EA ${blocks.euro_area?.latest_date}, JP ${blocks.japan?.latest_date}, CN ${blocks.china?.latest_date}. Live request-path parsing is disabled until parser validation is complete.`
  };
  return state;
}

export async function getLiveMoneyNowcast() {
  if (CACHE && (Date.now() - CACHE.at) < TTL_MS) return CACHE.value;
  const value = buildVerifiedSnapshot();
  CACHE = { at: Date.now(), value };
  return value;
}
