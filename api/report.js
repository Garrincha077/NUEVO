import { buildOpportunity } from '../lib/opportunity-engine.js';
import { buildDecision } from '../lib/decision-engine.js';
import { buildFreshnessHealth } from '../lib/freshness-health.js';
import { buildCurrentMarketConfirmation } from '../lib/current-market.js';
import { FROZEN_STATE } from '../lib/state.js';

function buckets(assets) {
  const accumulate = [], watch = [], dont_chase = [], limited = [];
  for (const [k, x] of Object.entries(assets || {})) {
    const row = { asset:k, asset_class:x.asset_class, evidence_tier:x.evidence_tier, strategic:x.strategic_eligibility.label, entry:x.entry_quality.label, action:x.action };
    if (/ACCUMULATE|SCALE-IN|SCALE IN SMALL/.test(x.action)) accumulate.push(row);
    else if (/DO NOT CHASE/.test(x.action)) dont_chase.push(row);
    else if (/INSUFFICIENT|NO VALIDATED/.test(x.action)) limited.push(row);
    else watch.push(row);
  }
  return { accumulate, watch, dont_chase, limited };
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin','*');
  res.setHeader('Cache-Control','public, max-age=0, must-revalidate');
  try {
    const generatedAt = new Date();
    const opportunity = await buildOpportunity();
    const [decision,currentMarket] = await Promise.all([
      buildDecision(opportunity),
      buildCurrentMarketConfirmation(opportunity)
    ]);
    const dataHealth = buildFreshnessHealth(decision, opportunity, generatedAt);
    const bs = buckets(opportunity.assets);
    const assets = Object.fromEntries(Object.entries(opportunity.assets).map(([k,x]) => [k, {
      asset_class:x.asset_class,
      evidence_tier:x.evidence_tier,
      transmission:x.transmission_relationship,
      strategic_eligibility:x.strategic_eligibility,
      dislocation:x.strategic_inputs.dislocation,
      positioning:x.entry_inputs.positioning,
      turn:x.entry_inputs.turn,
      current_market:currentMarket.assets?.[k] || null,
      entry_quality:x.entry_quality,
      action:x.action,
      triggers:x.triggers,
      backtest:x.backtest,
      freshness:{ money:FROZEN_STATE.money.available_date, price:x.price_as_of, positioning:x.entry_inputs.positioning?.as_of || null, current_market:currentMarket.assets?.[k]?.latest_completed_session || null }
    }]));

    const conflicts = [
      ...(decision.money.agreement === 'DIVERGENT' ? [{ type:'MONEY_DIVERGENCE', detail:`Active Core: USD ${decision.money.usd_score} ${decision.money.usd_regime} vs FX-neutral ${decision.money.fx_neutral_score} ${decision.money.fx_neutral_regime}.` }] : []),
      ...(currentMarket.divergences || []).map(x => ({ type:'CURRENT_MARKET_DIVERGENCE', detail:`${x.asset}: ${x.type} versus completed-month structure.` })),
      ...(opportunity.positioning.error ? [{ type:'POSITIONING_SOURCE', detail:opportunity.positioning.error }] : [])
    ];

    return res.status(200).json({
      schema_version:'gmli-report-v1.4',
      engine_version:'GMLI 2.4.0',
      generated_at:generatedAt.toISOString(),
      meta:{
        canonical:true,
        purpose:'Primary ChatGPT/analyst decision contract',
        raw_endpoints:['/api/status','/api/decision','/api/opportunity','/api/positioning','/api/money-nowcast','/api/current-market'],
        warnings:[
          `Active Money Core is ${FROZEN_STATE.money.version}, observation ${FROZEN_STATE.money.observation_date}, available ${FROZEN_STATE.money.available_date}; future data vintages still require an explicit promotion gate.`,
          `The prior validated Core (${FROZEN_STATE.money.historical_reference?.available_date}) is retained as historical audit reference, not as the active decision vintage.`,
          `Historical v1.8b exact-rerun audit remains ${FROZEN_STATE.money.historical_v18b_candidate?.promotion_gate?.status}; that blocker does not invalidate the explicitly versioned V2 promotion.`,
          'Funding/Credit/Fiscal remain OVERLAY and retain their existing fail-closed refreshability guardrails.'
        ]
      },
      data_health:dataHealth,
      methodology: decision.methodology,
      regime:{
        engine_fact:{ money:decision.money },
        current_research_inference:{
          label:decision.regime.label,
          tilt:decision.regime.tilt,
          provisional:decision.regime.provisional,
          money_candidate:decision.money_candidate,
          money_nowcast:decision.money_nowcast,
          funding:decision.funding,
          structural_market_confirmation:decision.market_confirmation,
          current_market_confirmation:currentMarket
        },
        conviction:decision.conviction,
        freshness:decision.freshness
      },
      money_history:decision.money_history,
      current_market_confirmation:currentMarket,
      money_promotion_gate: decision.promotion_gate,
      opportunity_summary:bs,
      assets,
      conflicts,
      audit_history:{
        prior_core:FROZEN_STATE.money.historical_reference,
        historical_v18b_candidate:FROZEN_STATE.money.historical_v18b_candidate
      },
      research_gaps:[
        'Historical v1.8b exact rerun remains blocked by missing preserved Aug-15 frozen input bytes. This is an audit/history fact, not a blocker on the explicitly versioned and separately validated Money V2 Core.',
        'Active Money V2 does not auto-refresh into CORE: future vintages still need an explicit source/integrity promotion gate before replacing the active data vintage.',
        'HYG needs a reproducible long-history credit-spread series for the pre-specified 60M test.',
        'VNQ/VEA need better fundamental dislocation models; current relative-price measures are context-only.',
        'BTC needs a validated BTC-specific dislocation model before any accumulation label.'
      ]
    });
  } catch(e) {
    return res.status(500).json({ error:e.message, endpoint:'/api/report' });
  }
}
