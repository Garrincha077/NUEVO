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
      freshness:{ money:FROZEN_STATE.money.available_date, funding:FROZEN_STATE.funding.available_date, fiscal:FROZEN_STATE.fiscal.available_date, price:x.price_as_of, positioning:x.entry_inputs.positioning?.as_of || null, current_market:currentMarket.assets?.[k]?.latest_completed_session || null }
    }]));

    const conflicts = [
      ...(decision.money.agreement === 'DIVERGENT' ? [{ type:'MONEY_DIVERGENCE', detail:`Active Money V2: USD ${decision.money.usd_score} ${decision.money.usd_regime} vs FX-neutral ${decision.money.fx_neutral_score} ${decision.money.fx_neutral_regime}.` }] : []),
      ...(currentMarket.divergences || []).map(x => ({ type:'CURRENT_MARKET_DIVERGENCE', detail:`${x.asset}: ${x.type} versus completed-month structure.` })),
      ...(opportunity.positioning.error ? [{ type:'POSITIONING_SOURCE', detail:opportunity.positioning.error }] : [])
    ];

    return res.status(200).json({
      schema_version:'gmli-report-v1.5',
      engine_version:'GMLI 2.4.0',
      generated_at:generatedAt.toISOString(),
      meta:{
        canonical:true,
        purpose:'Primary ChatGPT/analyst decision contract',
        raw_endpoints:['/api/status','/api/decision','/api/opportunity','/api/positioning','/api/money-nowcast','/api/current-market'],
        warnings:[
          `Money V2 is the active promoted Core (${FROZEN_STATE.money.version}), currently available ${FROZEN_STATE.money.available_date}.`,
          `Funding V2 is the active promoted OVERLAY (${FROZEN_STATE.funding.version}), currently available ${FROZEN_STATE.funding.available_date}; it is a bounded conviction modifier and never overrides Money Core.`,
          'Funding V2 empirical promotion strength is narrow: fixed DBC 6M/12M relations passed; SPY/QQQ/GLD diagnostics are not universal return claims.',
          `Fiscal V2 is the active promoted OVERLAY (${FROZEN_STATE.fiscal.version}), currently available ${FROZEN_STATE.fiscal.available_date}; its fixed SPY 12M usefulness gate passed but its automatic global conviction weight is 0.`,
          'Fiscal V2 historical research uses revised FRED history with conservative publication lags and is not represented as exact historical release-time data; QQQ/DBC diagnostics are not promotion claims.',
          'The pre-V2 Money Core and July-2026 legacy Funding/Fiscal readings are preserved only as historical references.',
          'Historical Money v1.8b remains BLOCKED_MISSING_FROZEN_INPUT_BYTES as an audit fact; it does not block the separately versioned and promoted Money V2 contract.'
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
          fiscal:decision.fiscal,
          structural_market_confirmation:decision.market_confirmation,
          current_market_confirmation:currentMarket
        },
        conviction:decision.conviction,
        freshness:decision.freshness
      },
      current_market_confirmation:currentMarket,
      money_promotion_gate: decision.promotion_gate,
      funding_promotion_gate: FROZEN_STATE.funding.promotion_gate,
      fiscal_promotion_gate: FROZEN_STATE.fiscal.promotion_gate,
      money_history: decision.money_history,
      funding_history: {
        historical_reference:FROZEN_STATE.funding.historical_reference
      },
      fiscal_history: {
        historical_reference:FROZEN_STATE.fiscal.historical_reference
      },
      opportunity_summary:bs,
      assets,
      conflicts,
      historical_audit:{
        pre_v2_core_reference:FROZEN_STATE.money.historical_reference,
        v18b_migration_candidate:FROZEN_STATE.money.historical_v18b_candidate,
        legacy_funding_reference:FROZEN_STATE.funding.historical_reference,
        legacy_fiscal_reference:FROZEN_STATE.fiscal.historical_reference
      },
      research_gaps:[
        'Historical Money v1.8b exact rerun remains impossible without the original frozen Aug-15 bytes; this is closed as historical audit context and is not an active V2 blocker.',
        'Funding V2 is promoted as a bounded OVERLAY, not a universal asset-return signal; its strongest fixed empirical usefulness is DBC 6M/12M.',
        'Fiscal V2 is promoted as a refreshable confirmation OVERLAY after the fixed SPY 12M gate passed; it carries zero automatic global conviction weight and is not a universal return signal.',
        'Credit/Velocity exact old construction provenance remains incomplete; do not infer the old formula.',
        'HYG, BTC and VNQ/VEA asset-specific models remain secondary to maintaining the promoted Money V2, Funding V2 and Fiscal V2 refresh contracts.'
      ]
    });
  } catch(e) {
    return res.status(500).json({ error:e.message, endpoint:'/api/report' });
  }
}
