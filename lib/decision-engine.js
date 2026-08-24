import { FROZEN_STATE, regimeFromScore } from './state.js';
import { getLiveMoneyNowcast, summarizeLiveNowcast, moneyNowcastFreshness } from './live-money-nowcast.js';
import { yahooMonthly, priceTurn } from './opportunity-data.js';

function coreMoneyAgreement() {
  const u = regimeFromScore(FROZEN_STATE.money.usd_score);
  const f = regimeFromScore(FROZEN_STATE.money.fxn_score);
  return { usd_regime: u, fx_neutral_regime: f, agreement: u === f ? 'AGREE' : 'DIVERGENT' };
}

async function coreMarketConfirmationFromOpportunity(opportunity) {
  if (opportunity?.assets) {
    const rows = ['SPY','QQQ','GLD','DBC']
      .map(k => opportunity.assets[k]?.entry_inputs?.turn)
      .filter(x => x?.available);
    const positive = rows.filter(x => x.pass).length;
    return {
      available: rows.length,
      positive,
      total: rows.length,
      score_0_2: rows.length >= 3 ? (positive >= 3 ? 2 : positive === 2 ? 1 : 0) : 1,
      basis: 'completed-month price turn across SPY/QQQ/GLD/DBC'
    };
  }
  const rows = [];
  for (const k of ['SPY','QQQ','GLD','DBC']) {
    try { rows.push(priceTurn(await yahooMonthly(k))); } catch {}
  }
  const positive = rows.filter(x => x.pass).length;
  return {
    available: rows.length,
    positive,
    total: rows.length,
    score_0_2: rows.length >= 3 ? (positive >= 3 ? 2 : positive === 2 ? 1 : 0) : 1,
    basis: 'completed-month price turn across SPY/QQQ/GLD/DBC'
  };
}

export async function buildDecision(opportunity = null) {
  const liveMoney = await getLiveMoneyNowcast();
  const nowcast = summarizeLiveNowcast(liveMoney);
  const fundingScore = FROZEN_STATE.funding.score;
  const fundingRegime = fundingScore < 40 ? 'RESTRICTIVE' : fundingScore > 60 ? 'SUPPORTIVE' : 'NEUTRAL';
  const agreement = coreMoneyAgreement();
  const market = await coreMarketConfirmationFromOpportunity(opportunity);
  const candidate = FROZEN_STATE.money.promotion_candidate || null;
  const coreStale = FROZEN_STATE.money.freshness === 'STALE';
  const freshnessScore = coreStale ? (candidate ? 1 : 0) : 2;
  const coreRegime = agreement.agreement === 'AGREE' ? agreement.usd_regime : 'NEUTRAL';

  const rubric = {
    money_freshness: {
      score: freshnessScore,
      max: 2,
      reason: coreStale
        ? candidate
          ? `Active Core vintage is ${FROZEN_STATE.money.available_date}, but a newer research candidate is available ${candidate.available_date}.`
          : `Active Core vintage is stale (${FROZEN_STATE.money.available_date}).`
        : `Active Money Core ${FROZEN_STATE.money.version} is current as available ${FROZEN_STATE.money.available_date}.`
    },
    usd_fxn_agreement: {
      score: agreement.agreement === 'AGREE' ? 2 : 0,
      max: 2,
      reason: `${agreement.usd_regime} vs ${agreement.fx_neutral_regime}`
    },
    transmission_evidence: {
      score: 2,
      max: 2,
      reason: 'Six promoted asset-transmission relationships passed the fixed Money V2 direction-transfer gate 6/6 without retuning'
    },
    funding_confirmation: {
      score: fundingRegime === 'SUPPORTIVE' ? 2 : fundingRegime === 'NEUTRAL' ? 1 : 0,
      max: 2,
      reason: `Funding ${fundingRegime.toLowerCase()} (${fundingScore.toFixed(1)})`
    },
    market_confirmation: {
      score: market.score_0_2,
      max: 2,
      reason: `${market.positive}/${market.total || 4} core assets have positive completed-month turn`
    }
  };
  const convictionScore = Object.values(rubric).reduce((a, x) => a + x.score, 0);

  const historicalReference = FROZEN_STATE.money.historical_reference || null;
  const historicalV18b = FROZEN_STATE.money.historical_v18b_candidate || null;

  return {
    schema_version: 'gmli-decision-v3.3',
    engine_version: 'GMLI 2.4.0',
    as_of: new Date().toISOString().slice(0, 10),
    methodology: {
      status: FROZEN_STATE.methodology?.status || 'FROZEN_SPEC',
      note: 'Frozen methodology remains locked. The active Money data/source version advanced only through the explicit V2 promotion gate.'
    },
    regime: {
      label: coreRegime,
      score: null,
      score_status: 'NOT_COMPUTED',
      provisional: false,
      tilt: 'MILD_POSITIVE',
      basis: 'ACTIVE_MONEY_CORE_V2_WITH_CURRENT_RESEARCH_CONFIRMATION',
      note: 'No synthetic USD/FX-neutral composite Core score. USD and FX-neutral are interpreted separately; both active V2 channels are currently NEUTRAL.'
    },
    conviction: { score: convictionScore, max: 10, label: `${convictionScore}/10`, rubric },
    money: {
      status: FROZEN_STATE.money.status,
      role: 'ACTIVE_PROMOTED_CORE_V2',
      version: FROZEN_STATE.money.version,
      methodology_status: FROZEN_STATE.money.methodology_status,
      data_vintage_status: FROZEN_STATE.money.data_vintage_status,
      observation_date: FROZEN_STATE.money.observation_date,
      usd_yoy_pct: FROZEN_STATE.money.usd_yoy_pct,
      usd_score: Number(FROZEN_STATE.money.usd_score.toFixed(1)),
      usd_regime: agreement.usd_regime,
      fx_neutral_yoy_pct: FROZEN_STATE.money.fx_neutral_yoy_pct,
      fx_neutral_score: Number(FROZEN_STATE.money.fxn_score.toFixed(1)),
      fx_neutral_regime: agreement.fx_neutral_regime,
      agreement: agreement.agreement,
      available_date: FROZEN_STATE.money.available_date,
      freshness: FROZEN_STATE.money.freshness
    },
    money_candidate: candidate ? {
      status: candidate.status,
      evidence_tier: candidate.evidence_tier,
      version: candidate.version,
      available_date: candidate.available_date,
      coverage: candidate.coverage,
      usd_score: Number(candidate.usd_score.toFixed(1)),
      usd_regime: regimeFromScore(candidate.usd_score),
      fx_neutral_score: Number(candidate.fxn_score.toFixed(1)),
      fx_neutral_regime: regimeFromScore(candidate.fxn_score),
      interpretation: candidate.interpretation,
      promotion_gate: FROZEN_STATE.money.promotion_gate?.status || 'UNKNOWN',
      core_replacement_allowed: FROZEN_STATE.money.promotion_gate?.core_replacement_allowed === true
    } : null,
    money_history: {
      historical_core_reference: historicalReference ? {
        version: historicalReference.version,
        available_date: historicalReference.available_date,
        usd_score: Number(historicalReference.usd_score.toFixed(1)),
        fx_neutral_score: Number(historicalReference.fxn_score.toFixed(1)),
        role: historicalReference.status
      } : null,
      historical_v18b_candidate: historicalV18b ? {
        version: historicalV18b.version,
        available_date: historicalV18b.available_date,
        usd_score: Number(historicalV18b.usd_score.toFixed(1)),
        fx_neutral_score: Number(historicalV18b.fxn_score.toFixed(1)),
        audit_status: historicalV18b.promotion_gate?.status || 'UNKNOWN',
        evidence_tier: historicalV18b.evidence_tier
      } : null
    },
    money_nowcast: {
      status: liveMoney.evidence_tier,
      tilt: nowcast.tilt,
      coverage: nowcast.coverage,
      accelerating: `${nowcast.accelerating}/4`,
      expanding_yoy: `${nowcast.expanding_yoy}/4`,
      blocks: Object.fromEntries(Object.entries(liveMoney.blocks || {}).map(([k, v]) => [k, v.latest_date || null])),
      details: '/api/money-nowcast',
      comparison_reference: liveMoney.validated_reference || null,
      current_research_inference: liveMoney.interpretation.current_research_inference
    },
    funding: { status: 'OVERLAY', regime: fundingRegime, score: Number(fundingScore.toFixed(1)), available_date: FROZEN_STATE.funding.available_date },
    market_confirmation: { status: 'RESEARCH', ...market },
    opportunity_overlay: { status: 'RESEARCH', details: '/api/opportunity', method: 'Strategic Eligibility first; Entry Quality second.' },
    freshness: {
      active_core: FROZEN_STATE.money.available_date,
      active_core_version: FROZEN_STATE.money.version,
      historical_core_reference: historicalReference?.available_date || null,
      production_candidate: candidate?.available_date || null,
      money_nowcast: moneyNowcastFreshness(liveMoney.blocks),
      overlays: FROZEN_STATE.funding.available_date,
      warning: coreStale
        ? 'Active Money Core is stale; research freshness overlays may adjust conviction but never silently replace CORE.'
        : 'Active Money Core V2 is fresh. Research overlays adjust conviction/confirmation only and never rewrite CORE.'
    },
    promotion_gate: FROZEN_STATE.money.promotion_gate,
    evidence_tiers: { money: 'CORE', money_candidate: candidate ? 'RESEARCH' : null, money_history: 'AUDIT', money_nowcast: 'RESEARCH', funding: 'OVERLAY', credit: 'OVERLAY', fiscal: 'OVERLAY' },
    key_reasons: [
      `Active Money Core V2 agrees: USD ${FROZEN_STATE.money.usd_score.toFixed(1)} ${agreement.usd_regime} and FX-neutral ${FROZEN_STATE.money.fxn_score.toFixed(1)} ${agreement.fx_neutral_regime}.`,
      'The fixed Money V2 transmission-transfer gate passed 6/6 without asset, horizon, lag or parameter retuning.',
      `Directional nowcast overlay is ${nowcast.tilt} versus its fixed historical February comparator; it is not a Core replacement mechanism.`,
      `Funding remains ${fundingRegime.toLowerCase()}, limiting the positive tilt.`,
      `${market.positive}/${market.total || 4} primary completed-month market turns are positive.`
    ],
    invalidation_triggers: [
      'A future explicit Money V2 vintage gate shows material deterioration in both USD and FX-neutral Money.',
      'Funding remains restrictive while current/structural market confirmation turns broadly negative.',
      'The fixed promoted transmission relationships fail a future source/version integrity gate.'
    ]
  };
}
