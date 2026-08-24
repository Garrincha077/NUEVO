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
      ...(decision.money.agreement === 'DIVERGENT' ? [{ type:'MONEY_DIVERGENCE', detail:`Active Money V2: USD ${decision.money.usd_score} ${decision.money.usd_regime} vs FX-neutral ${decision.money.fx_neutral_score} ${decision.money.fx_neutral_regime}.` }] : []),
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
          `Money V2 is the active promoted Core (${FROZEN_STATE.money.version}), currently available ${FROZEN_STATE.money.available_date}.`,
          'The 2026-02-28 pre-V2 Core is preserved only as a historical reference.',
          'Historical v1.8b remains BLOCKED_MISSING_FROZEN_INPUT_BYTES as an audit fact; it does not block the separately versioned and promoted Money V2 contract.'
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
          money_nowcast:decision.money_nowcast,
          funding:decision.funding,
          structural_market_confirmation:decision.market_confirmation,
          current_market_confirmation:currentMarket
        },
        conviction:decision.conviction,
        freshness:decision.freshness
      },
      current_market_confirmation:currentMarket,
      money_promotion_gate: decision.promotion_gate,
      money_history: decision.money_history,
      opportunity_summary:bs,
      assets,
      conflicts,
      historical_audit:{
        pre_v2_core_reference:FROZEN_STATE.money.historical_reference,
        v18b_migration_candidate:FROZEN_STATE.money.historical_v18b_candidate
      },
      research_gaps:[
        'Historical v1.8b exact rerun remains impossible without the original frozen Aug-15 bytes; this is closed as historical audit context and is not an active V2 blocker.',
        'Funding exact production baseline mismatch remains unresolved; Funding stays an overlay and cannot override Money Core.',
        'Credit/Velocity exact old construction provenance remains incomplete; do not infer the old formula.',
        'HYG, BTC and VNQ/VEA asset-specific models remain secondary to maintaining the promoted Money V2 refresh contract.'
      ]
    });
  } catch(e) {
    return res.status(500).json({ error:e.message, endpoint:'/api/report' });
  }
}
