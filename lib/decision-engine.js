import { FROZEN_STATE, regimeFromScore } from './state.js';
import { getLiveMoneyNowcast, summarizeLiveNowcast, moneyNowcastFreshness } from './live-money-nowcast.js';
import { yahooMonthly, priceTurn } from './opportunity-data.js';

function moneyAgreement() {
  const u = regimeFromScore(FROZEN_STATE.money.usd_score);
  const f = regimeFromScore(FROZEN_STATE.money.fxn_score);
  return { usd_regime: u, fx_neutral_regime: f, agreement: u === f ? 'AGREE' : 'DIVERGENT' };
}

function freshness(dateString, now = new Date()) {
  const d = new Date(`${dateString}T00:00:00Z`);
  const days = Math.max(0, Math.floor((now - d) / 86400000));
  return { days, label: days <= 35 ? 'FRESH' : days <= 60 ? 'AGING' : 'STALE' };
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
  const agreement = moneyAgreement();
  const market = await coreMarketConfirmationFromOpportunity(opportunity);
  const moneyFreshness = freshness(FROZEN_STATE.money.available_date);
  const freshnessScore = moneyFreshness.label === 'FRESH' ? 2 : moneyFreshness.label === 'AGING' ? 1 : 0;

  const rubric = {
    money_freshness: {
      score: freshnessScore,
      max: 2,
      reason: `Active Money V2 is ${moneyFreshness.label.toLowerCase()} (${FROZEN_STATE.money.available_date}; ${moneyFreshness.days}d).`
    },
    usd_fxn_agreement: {
      score: agreement.agreement === 'AGREE' ? 2 : 0,
      max: 2,
      reason: `${agreement.usd_regime} vs ${agreement.fx_neutral_regime}`
    },
    transmission_evidence: {
      score: 2,
      max: 2,
      reason: 'Money V2 passed the fixed 6/6 transfer gate on the six promoted relationships without retuning.'
    },
    funding_confirmation: {
      score: fundingRegime === 'SUPPORTIVE' ? 2 : fundingRegime === 'NEUTRAL' ? 1 : 0,
      max: 2,
      reason: `Funding V2 ${fundingRegime.toLowerCase()} (${fundingScore.toFixed(1)}); bounded conviction overlay, strongest fixed empirical usefulness DBC 6M/12M.`
    },
    market_confirmation: {
      score: market.score_0_2,
      max: 2,
      reason: `${market.positive}/${market.total || 4} core assets have positive completed-month turn`
    }
  };
  const convictionScore = Object.values(rubric).reduce((a, x) => a + x.score, 0);
  const baseLabel = agreement.agreement === 'AGREE' ? agreement.usd_regime : 'NEUTRAL';

  return {
    schema_version: 'gmli-decision-v4.1',
    engine_version: 'GMLI 2.4.0',
    as_of: new Date().toISOString().slice(0, 10),
    methodology: {
      status: FROZEN_STATE.methodology?.status || 'FROZEN_V2_SPEC',
      note: 'Money V2 methodology is frozen. Funding V2 is a separately promoted frozen OVERLAY. New data vintages may advance only through their promoted fail-closed source contracts.'
    },
    regime: {
      label: baseLabel,
      score: null,
      score_status: 'DUAL_CHANNEL_NO_SYNTHETIC_COMPOSITE',
      provisional: false,
      tilt: nowcast.tilt === 'SUPPORTIVE_MIXED' && market.score_0_2 >= 1 ? 'MILD_POSITIVE' : 'NEUTRAL',
      basis: 'ACTIVE_PROMOTED_MONEY_CORE_V2_WITH_OVERLAY_CONFIRMATION',
      note: 'USD and FX-neutral Money are interpreted separately; no synthetic composite Core score is invented.'
    },
    conviction: { score: convictionScore, max: 10, label: `${convictionScore}/10`, rubric },
    money: {
      status: FROZEN_STATE.money.status,
      role: 'ACTIVE_PROMOTED_MONEY_CORE_V2',
      version: FROZEN_STATE.money.version,
      methodology_status: FROZEN_STATE.money.methodology_status,
      data_vintage_status: FROZEN_STATE.money.data_vintage_status,
      observation_month: FROZEN_STATE.money.observation_month,
      usd_yoy_pct: FROZEN_STATE.money.usd_yoy_pct,
      usd_score: Number(FROZEN_STATE.money.usd_score.toFixed(1)),
      usd_regime: agreement.usd_regime,
      fx_neutral_yoy_pct: FROZEN_STATE.money.fx_neutral_yoy_pct,
      fx_neutral_score: Number(FROZEN_STATE.money.fxn_score.toFixed(1)),
      fx_neutral_regime: agreement.fx_neutral_regime,
      agreement: agreement.agreement,
      available_date: FROZEN_STATE.money.available_date,
      freshness: moneyFreshness.label,
      age_days: moneyFreshness.days,
      promotion_status: FROZEN_STATE.money.promotion_gate?.status || null
    },
    money_candidate: null,
    money_history: {
      historical_core_reference: FROZEN_STATE.money.historical_reference,
      historical_v18b_candidate: FROZEN_STATE.money.historical_v18b_candidate
    },
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
    funding: {
      status: 'OVERLAY',
      role: 'ACTIVE_PROMOTED_FUNDING_V2',
      version: FROZEN_STATE.funding.version,
      methodology_status: FROZEN_STATE.funding.methodology_status,
      data_vintage_status: FROZEN_STATE.funding.data_vintage_status,
      observation_month: FROZEN_STATE.funding.observation_month,
      regime: fundingRegime,
      score: Number(fundingScore.toFixed(1)),
      structural_support_score: Number(FROZEN_STATE.funding.structural_support_score.toFixed(1)),
      observed_conditions_score: Number(FROZEN_STATE.funding.observed_conditions_score.toFixed(1)),
      available_date: FROZEN_STATE.funding.available_date,
      promotion_status: FROZEN_STATE.funding.promotion_gate?.status || null,
      empirical_scope: 'Fixed DBC 6M/12M usefulness gate passed; not a universal SPY/QQQ/GLD return signal.',
      guardrail: 'Funding modifies conviction only and never overrides Money Core.'
    },
    market_confirmation: { status: 'RESEARCH', ...market },
    opportunity_overlay: { status: 'RESEARCH', details: '/api/opportunity', method: 'Strategic Eligibility first; Entry Quality second.' },
    freshness: {
      active_money_core: FROZEN_STATE.money.available_date,
      active_money_core_status: moneyFreshness.label,
      active_money_core_age_days: moneyFreshness.days,
      historical_core_reference: FROZEN_STATE.money.historical_reference?.available_date || null,
      money_nowcast: moneyNowcastFreshness(liveMoney.blocks),
      overlays: FROZEN_STATE.funding.available_date,
      warning: moneyFreshness.label === 'STALE'
        ? 'Active Money V2 data are stale; methodology remains Core but conviction must fall until the promoted refresh contract advances.'
        : 'Active Money V2 is current under the promoted official-source contract. Funding V2 is a separate bounded overlay; the old Money v1.8b blocker is historical audit context only.'
    },
    promotion_gate: FROZEN_STATE.money.promotion_gate,
    evidence_tiers: { money: 'CORE', money_nowcast: 'RESEARCH', funding: 'OVERLAY', credit: 'OVERLAY', fiscal: 'OVERLAY' },
    key_reasons: [
      `Active Money V2 agrees across channels: USD ${agreement.usd_regime} (${FROZEN_STATE.money.usd_score.toFixed(1)}) and FX-neutral ${agreement.fx_neutral_regime} (${FROZEN_STATE.money.fxn_score.toFixed(1)}).`,
      `Money V2 is ${moneyFreshness.label.toLowerCase()} and passed the fixed 6/6 transmission-transfer gate without retuning.`,
      `Freshness overlay is ${nowcast.tilt}: ${nowcast.accelerating}/4 blocks accelerated and ${nowcast.expanding_yoy}/4 are expanding YoY.`,
      `Promoted Funding V2 is ${fundingRegime.toLowerCase()} (${fundingScore.toFixed(1)}), limiting a stronger risk-on conclusion; its strongest fixed empirical usefulness is DBC 6M/12M.`,
      `${market.positive}/${market.total || 4} primary market turns are currently positive.`
    ],
    invalidation_triggers: [
      'Active Money V2 decelerates enough to push both USD and FX-neutral channels into Risk-Off territory.',
      'Funding V2 remains restrictive while current market confirmation turns broadly negative.',
      'A promoted Money V2 or Funding V2 source-refresh contract fails validation or stops advancing, causing decision-critical freshness to deteriorate.'
    ]
  };
}
