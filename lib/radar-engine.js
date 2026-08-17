import { buildOpportunity } from './opportunity-engine.js';
import { buildDecision } from './decision-engine.js';
import { yahooMonthly, relativeTurn } from './opportunity-data.js';

const SYMBOLS = {
  SPY:'SPY', QQQ:'QQQ', GLD:'GLD', DBC:'DBC', TLT:'TLT', HYG:'HYG',
  VNQ:'VNQ', EEM:'EEM', VEA:'VEA', BTC:'BTC-USD'
};

const UP = new Set(['EARLY_UP','CONFIRMED_UP']);
const DOWN = new Set(['EARLY_DOWN','CONFIRMED_DOWN']);

function shortDislocation(asset) {
  const d = asset?.strategic_inputs?.dislocation;
  const mode = asset?.strategic_inputs?.strategic_mode;
  if (!d?.available || !Number.isFinite(d.z60m)) return false;
  if (mode === 'RESEARCH_DISLOCATION_PRIMARY' || mode === 'RESEARCH_DATA_INCOMPLETE') return d.z60m <= -1;
  return d.z60m >= 1;
}

function asymmetry(parts, adverse=false) {
  const vals = Object.values(parts).filter(v => typeof v === 'boolean');
  const passes = vals.filter(Boolean).length;
  const core = parts.macro === true && parts.contrarian === true && parts.turn === true;
  const rsOpposes = parts.relative_strength === false;
  const label = core && !adverse && !rsOpposes ? 'HIGH' : (core || passes >= 2) ? 'MEDIUM' : 'LOW';
  return { label, evidence: `${passes}/${vals.length}`, adverse_cap:adverse || rsOpposes, components: parts };
}

function phaseFor({macroLong,macroShort,longContrarian,shortContrarian,trend}) {
  if (macroLong && longContrarian && trend === 'EARLY_UP') return 'EARLY_LONG';
  if (macroShort && shortContrarian && trend === 'EARLY_DOWN') return 'EARLY_SHORT';
  if (macroLong && longContrarian && trend === 'CONFIRMED_UP') return 'CONFIRMED_LONG';
  if (macroShort && shortContrarian && trend === 'CONFIRMED_DOWN') return 'CONFIRMED_SHORT';
  if (macroLong && longContrarian && ['MIXED','EARLY_DOWN','CONFIRMED_DOWN'].includes(trend)) return 'SETUP_LONG';
  if (macroShort && shortContrarian && ['MIXED','EARLY_UP','CONFIRMED_UP'].includes(trend)) return 'SETUP_SHORT';
  if (trend === 'CONFIRMED_UP' && shortContrarian) return 'MATURE_LONG_DONT_CHASE';
  if (trend === 'CONFIRMED_DOWN' && longContrarian) return 'MATURE_SHORT_DONT_CHASE';
  if (trend === 'CONFIRMED_UP') return 'TREND_UP_NO_CONTRARIAN_EDGE';
  if (trend === 'CONFIRMED_DOWN') return 'TREND_DOWN_NO_CONTRARIAN_EDGE';
  return 'WATCH';
}

function rank(x) {
  const a = x.best_asymmetry === 'HIGH' ? 3 : x.best_asymmetry === 'MEDIUM' ? 2 : 1;
  const p = x.phase.startsWith('EARLY_') ? 4 : x.phase.startsWith('SETUP_') ? 3 : x.phase.startsWith('CONFIRMED_') ? 2 : 0;
  return a * 10 + p;
}

async function relativeStrengthPack(opportunity) {
  const out = {};
  let spy = null;
  try { spy = await yahooMonthly('SPY'); } catch {}
  if (!spy) return out;
  const keys = Object.keys(opportunity.assets || {}).filter(k => k !== 'SPY' && SYMBOLS[k]);
  const rows = await Promise.allSettled(keys.map(async k => [k, relativeTurn(await yahooMonthly(SYMBOLS[k]), spy)]));
  for (const r of rows) if (r.status === 'fulfilled') out[r.value[0]] = r.value[1];
  out.SPY = { available:false, pass:false, benchmark:'SELF', note:'SPY is the radar reference for relative strength.' };
  return out;
}

export async function buildRadar() {
  const opportunity = await buildOpportunity();
  const decision = await buildDecision(opportunity);
  const rsPack = await relativeStrengthPack(opportunity);
  const assets = {};

  for (const [key, x] of Object.entries(opportunity.assets || {})) {
    const t = x.strategic_inputs?.transmission || {};
    const d = x.strategic_inputs?.dislocation || {};
    const p = x.entry_inputs?.positioning || {};
    const turn = x.entry_inputs?.turn || {};
    const rs = rsPack[key] || {available:false,pass:false};
    const trend = turn.stage || 'MIXED';

    const macroLong = t.pass === true;
    const macroShort = t.available === true && t.pass === false;
    const cheap = d.pass === true;
    const expensive = shortDislocation(x);
    const washed = p.available === true && p.pass === true;
    const crowded = p.available === true && p.crowded === true;
    const longContrarian = cheap || washed;
    const shortContrarian = expensive || crowded;
    const turnLong = UP.has(trend);
    const turnShort = DOWN.has(trend);
    const rsLong = rs.available ? UP.has(rs.stage) : null;
    const rsShort = rs.available ? DOWN.has(rs.stage) : null;

    const longAsym = asymmetry({ macro:macroLong, contrarian:longContrarian, turn:turnLong, relative_strength:rsLong }, expensive || crowded);
    const shortAsym = asymmetry({ macro:macroShort, contrarian:shortContrarian, turn:turnShort, relative_strength:rsShort }, cheap || washed);
    const phase = phaseFor({macroLong,macroShort,longContrarian,shortContrarian,trend});
    const longEligible = macroLong && longContrarian;
    const shortEligible = macroShort && shortContrarian;
    const preferredSide = longEligible && !shortEligible ? 'LONG'
      : shortEligible && !longEligible ? 'SHORT'
      : longEligible && shortEligible && longAsym.label === 'HIGH' && shortAsym.label !== 'HIGH' ? 'LONG'
      : longEligible && shortEligible && shortAsym.label === 'HIGH' && longAsym.label !== 'HIGH' ? 'SHORT'
      : 'NONE';
    const bestAsymmetry = preferredSide === 'LONG' ? longAsym.label : preferredSide === 'SHORT' ? shortAsym.label : 'LOW';

    const conflicts = [];
    if (longEligible && expensive) conflicts.push('Long contrarian evidence conflicts with an expensive/stretched price dislocation.');
    if (longEligible && crowded) conflicts.push('Long case conflicts with crowded positioning.');
    if (longEligible && rsLong === false) conflicts.push('Long case conflicts with weakening relative strength versus SPY.');
    if (shortEligible && cheap) conflicts.push('Short case conflicts with a cheap long-side dislocation.');
    if (shortEligible && washed) conflicts.push('Short case conflicts with washed-out positioning.');
    if (shortEligible && rsShort === false) conflicts.push('Short case conflicts with improving relative strength versus SPY.');

    const reasons = [];
    if (macroLong) reasons.push('Money/transmission context supports the long side.');
    if (macroShort) reasons.push('Money/transmission context is not supportive and can support the short side.');
    if (cheap) reasons.push('Contrarian long dislocation threshold is met.');
    if (expensive) reasons.push('Opposite-side dislocation is stretched enough to support a contrarian short watch.');
    if (washed) reasons.push('CFTC positioning is in the contrarian-friendly lower quartile.');
    if (crowded) reasons.push('CFTC positioning is crowded in the upper quartile.');
    if (trend === 'EARLY_UP' || trend === 'EARLY_DOWN') reasons.push(`Price is in an ${trend === 'EARLY_UP' ? 'early upside' : 'early downside'} turn rather than a mature confirmed trend.`);
    if (rs.available && (UP.has(rs.stage) || DOWN.has(rs.stage))) reasons.push(`Relative strength versus SPY is ${UP.has(rs.stage) ? 'improving' : 'weakening'}.`);

    assets[key] = {
      asset_class:x.asset_class,
      evidence_tier:'RESEARCH_RADAR_OVERLAY',
      core_transmission:x.transmission_relationship?.evidence_tier === 'CORE',
      phase,
      preferred_side:preferredSide,
      best_asymmetry:bestAsymmetry,
      long_asymmetry:longAsym,
      short_asymmetry:shortAsym,
      macro:{ long_support:macroLong, short_support:macroShort, basis:t.money_basis, score:t.score, freshness_turn:t.freshness_turn },
      contrarian:{ cheap_long:cheap, expensive_short:expensive, positioning_washed:washed, positioning_crowded:crowded, dislocation_z:d.z60m ?? null, positioning_percentile:p.percentile_3y ?? null },
      trend:{ stage:trend, price:turn.price ?? null, ma10:turn.ma10 ?? null, ma10_slope_3m_pct:turn.ma10_slope_3m_pct ?? null, return_3m_pct:turn.return_3m_pct ?? null, return_6m_pct:turn.return_6m_pct ?? null, relative_strength_vs_spy:rs },
      conflicts,
      mechanical_reasons:reasons.slice(0,5),
      invalidation:x.triggers?.downgrade || [],
      freshness:{ price:x.price_as_of, positioning:p.as_of || null, money:t.core_date || null }
    };
  }

  const rows = Object.entries(assets).map(([asset,x]) => ({asset,...x})).sort((a,b)=>rank(b)-rank(a));
  const pick = phase => rows.filter(x => x.phase === phase && x.preferred_side !== 'NONE').map(x => ({asset:x.asset,asset_class:x.asset_class,asymmetry:x.best_asymmetry,preferred_side:x.preferred_side,conflicts:x.conflicts,why:x.mechanical_reasons.slice(0,3)}));

  return {
    schema_version:'gmli-radar-v1.1',
    engine_version:'GMLI 2.4.1 Radar Research Overlay',
    as_of:new Date().toISOString(),
    status:'RESEARCH_OVERLAY_NOT_CORE',
    purpose:'Find asymmetric contrarian setups and early 3–12M trend turns without retuning the frozen Money Core.',
    regime_context:{ label:decision.regime.label, tilt:decision.regime.tilt, conviction:decision.conviction.label, funding:decision.funding.regime, money:decision.money, money_candidate:decision.money_candidate, money_nowcast:decision.money_nowcast },
    buckets:{
      early_longs:pick('EARLY_LONG'),
      early_shorts:pick('EARLY_SHORT'),
      setup_longs:pick('SETUP_LONG'),
      setup_shorts:pick('SETUP_SHORT'),
      confirmed_longs:pick('CONFIRMED_LONG'),
      confirmed_shorts:pick('CONFIRMED_SHORT'),
      mature_dont_chase:rows.filter(x=>x.phase.includes('DONT_CHASE')).map(x=>({asset:x.asset,phase:x.phase,conflicts:x.conflicts}))
    },
    assets,
    research_design:{
      principles:[
        'Liquidity/Money is a prior, not a standalone trade signal.',
        'Contrarian dislocation and positioning create asymmetry; trend/relative-strength confirmation reduces the risk of fighting a persistent move.',
        'Early turn is distinct from confirmed trend so the radar can surface candidates before a mature move.',
        'Conflicting stretch or relative-strength evidence caps asymmetry rather than being averaged away.',
        'Missing or unsupported data never count as a pass.',
        'No new parameter search, FDR sweep or Core retuning is performed by this radar.'
      ],
      external_evidence:[
        {study:'Asness, Moskowitz & Pedersen — Value and Momentum Everywhere',finding:'Value and momentum premia appear jointly across multiple asset classes; combining contrarian and momentum information is economically plausible.'},
        {study:'Moskowitz, Ooi & Pedersen — Time Series Momentum',finding:'Return persistence is documented over roughly 1–12 month horizons across equity index, currency, commodity and bond futures.'},
        {study:'Goyal & Jegadeesh — Time Series Momentum: Is It There?',finding:'Evidence for asset-by-asset time-series predictability is weaker than simple trend narratives imply; radar therefore treats trend as confirmation rather than a standalone forecast.'},
        {study:'CFTC Commitments of Traders',finding:'TFF Leveraged Money and Disaggregated Managed Money are used as positioning context; categories are not treated as causal timing signals.'}
      ]
    },
    copilot_contract:{
      mechanical_radar_is_not_final_opinion:true,
      current_research_required:true,
      instruction:'After reading /api/radar, independently check current macro/policy changes, asset-specific catalysts, market structure and material divergences. State the resulting COPILOT VIEW separately from ENGINE FACT and RADAR FACT. The Copilot may disagree with a mechanical ranking, but must explain the conflict and may not silently promote RESEARCH/OVERLAY to CORE.',
      default_output:['EARLY LONG','EARLY SHORT','SETUP WATCH','MATURE / DO NOT CHASE','COPILOT VIEW','WHAT WOULD INVALIDATE IT']
    }
  };
}
