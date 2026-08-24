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

  const rubric = {
    money_freshness: {
      score: freshnessScore,
      max: 2,
      reason: coreStale
        ? candidate
          ? `Validated Core vintage is ${FROZEN_STATE.money.available_date}, but a 7/7 production-source candidate is available ${candidate.available_date}; frozen refers to specification, not permanent data.`
          : `Validated Core vintage is stale (${FROZEN_STATE.money.available_date}).`
        : `Validated Core current (${FROZEN_STATE.money.available_date}).`
    },
    usd_fxn_agreement: {
      score: agreement.agreement === 'AGREE' ? 2 : 0,
      max: 2,
      reason: `${agreement.usd_regime} vs ${agreement.fx_neutral_regime}`
    },
    transmission_evidence: {
      score: 2,
      max: 2,
      reason: 'Six frozen/promoted asset-transmission relationships remain the primary allocation priors'
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

  return {
    schema_version: 'gmli-decision-v3.2',
    engine_version: 'GMLI 2.3.1',
    as_of: new Date().toISOString().slice(0, 10),
    methodology: {
      status: FROZEN_STATE.methodology?.status || 'FROZEN_SPEC',
      note: 'Frozen means methodology is locked. Data vintages advance only through an explicit promotion gate.'
    },
    regime: {
      label: 'NEUTRAL',
      score: null,
      score_status: 'NOT_COMPUTED',
      provisional: true,
      tilt: 'MILD_POSITIVE',
      basis: 'VALIDATED_MONEY_CORE_FIRST_WITH_CURRENT_RESEARCH_CONFIRMATION',
      note: 'No synthetic USD/FX-neutral composite Core score. USD and FX-neutral are interpreted separately.'
    },
    conviction: { score: convictionScore, max: 10, label: `${convictionScore}/10`, rubric },
    money: {
      status: FROZEN_STATE.money.status,
      role: 'LAST_FORMALLY_VALIDATED_CORE_VINTAGE',
      methodology_status: FROZEN_STATE.money.methodology_status,
      data_vintage_status: FROZEN_STATE.money.data_vintage_status,
      usd_score: Number(FROZEN_STATE.money.usd_score.toFixed(1)),
      usd_regime: agreement.usd_regime,
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
    money_nowcast: {
      status: liveMoney.evidence_tier,
      tilt: nowcast.tilt,
      coverage: nowcast.coverage,
      accelerating: `${nowcast.accelerating}/4`,
      expanding_yoy: `${nowcast.expanding_yoy}/4`,
      blocks: Object.fromEntries(Object.entries(liveMoney.blocks || {}).map(([k, v]) => [k, v.latest_date || null])),
      details: '/api/money-nowcast',
      current_research_inference: liveMoney.interpretation.current_research_inference
    },
    funding: { status: 'OVERLAY', regime: fundingRegime, score: Number(fundingScore.toFixed(1)), available_date: FROZEN_STATE.funding.available_date },
    market_confirmation: { status: 'RESEARCH', ...market },
    opportunity_overlay: { status: 'RESEARCH', details: '/api/opportunity', method: 'Strategic Eligibility first; Entry Quality second.' },
    freshness: {
      validated_core: FROZEN_STATE.money.available_date,
      production_candidate: candidate?.available_date || null,
      money_nowcast: moneyNowcastFreshness(liveMoney.blocks),
      overlays: FROZEN_STATE.funding.available_date,
      warning: 'The specification is frozen; the validated Core vintage is stale. Candidate/nowcast improve current inference but do not silently replace CORE.'
    },
    promotion_gate: FROZEN_STATE.money.promotion_gate,
    evidence_tiers: { money: 'CORE', money_candidate: 'RESEARCH', money_nowcast: 'RESEARCH', funding: 'OVERLAY', credit: 'OVERLAY', fiscal: 'OVERLAY' },
    key_reasons: [
      'Validated Money Core is divergent: USD Risk-On, FX-neutral Neutral.',
      candidate ? `Newer production-source Money candidate is USD ${candidate.usd_score.toFixed(1)} / FX-neutral ${candidate.fxn_score.toFixed(1)} as available ${candidate.available_date}.` : 'No newer production candidate is available.',
      `Freshness overlay is ${nowcast.tilt}: ${nowcast.accelerating}/4 blocks accelerated and ${nowcast.expanding_yoy}/4 are expanding YoY.`,
      `Funding remains ${fundingRegime.toLowerCase()}, limiting conviction.`,
      `${market.positive}/${market.total || 4} primary market turns are currently positive.`
    ],
    invalidation_triggers: [
      'Fresh broad-money data deteriorate across multiple major blocks.',
      'FX-neutral Money weakens further while the USD translation headwind rises.',
      'Market confirmation turns broadly negative across the promoted transmission assets.'
    ]
  };
}
