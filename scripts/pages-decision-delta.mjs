function finite(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function round(value, digits = 2) {
  return Number.isFinite(value) ? Number(value.toFixed(digits)) : null;
}

function moneyRegime(score) {
  if (score < 25) return 'STRONG RISK-OFF';
  if (score < 40) return 'RISK-OFF';
  if (score < 60) return 'NEUTRAL';
  if (score < 75) return 'RISK-ON';
  return 'STRONG RISK-ON';
}

function overlayRegime(score) {
  if (score < 40) return 'RESTRICTIVE';
  if (score > 60) return 'SUPPORTIVE';
  return 'NEUTRAL';
}

function direction(delta, epsilon = 0.05) {
  if (!Number.isFinite(delta) || Math.abs(delta) < epsilon) return 'FLAT';
  return delta > 0 ? 'IMPROVING' : 'DETERIORATING';
}

function arrow(dir) {
  return dir === 'IMPROVING' ? '↑' : dir === 'DETERIORATING' ? '↓' : '→';
}

function pair(rows) {
  const clean = (rows || []).filter(Boolean);
  if (clean.length < 2) return { current: clean.at(-1) || null, previous: null };
  return { current: clean.at(-1), previous: clean.at(-2) };
}

function moneyChannel(current, previous, key) {
  const now = finite(current?.[key]);
  const before = finite(previous?.[key]);
  const delta = now != null && before != null ? now - before : null;
  const currentRegime = now != null ? moneyRegime(now) : null;
  const previousRegime = before != null ? moneyRegime(before) : null;
  const dir = direction(delta);
  return {
    current: round(now, 2),
    previous: round(before, 2),
    delta: round(delta, 2),
    direction: dir,
    arrow: arrow(dir),
    current_regime: currentRegime,
    previous_regime: previousRegime,
    regime_changed: Boolean(currentRegime && previousRegime && currentRegime !== previousRegime)
  };
}

function overlayLayer(current, previous) {
  const now = finite(current?.score);
  const before = finite(previous?.score);
  const delta = now != null && before != null ? now - before : null;
  const currentRegime = current?.regime || (now != null ? overlayRegime(now) : null);
  const previousRegime = previous?.regime || (before != null ? overlayRegime(before) : null);
  const dir = direction(delta);
  return {
    current: round(now, 2),
    previous: round(before, 2),
    delta: round(delta, 2),
    direction: dir,
    arrow: arrow(dir),
    current_regime: currentRegime,
    previous_regime: previousRegime,
    regime_changed: Boolean(currentRegime && previousRegime && currentRegime !== previousRegime),
    current_available_date: current?.available_date || null,
    previous_available_date: previous?.available_date || null
  };
}

function fundingPoints(regime) {
  return regime === 'SUPPORTIVE' ? 2 : regime === 'NEUTRAL' ? 1 : 0;
}

function reconstructedPreviousConviction(previousMoney, previousFunding, previousMarket) {
  if (!previousMoney || !previousFunding || !previousMarket) return null;
  const usd = moneyRegime(previousMoney.usd_score);
  const fxn = moneyRegime(previousMoney.fx_neutral_score);
  const rubric = {
    money_freshness: 2,
    usd_fxn_agreement: usd === fxn ? 2 : 0,
    transmission_evidence: 2,
    funding_confirmation: fundingPoints(previousFunding.regime || overlayRegime(previousFunding.score)),
    market_confirmation: finite(previousMarket.score_0_2)
  };
  if (!Number.isFinite(rubric.market_confirmation)) return null;
  return {
    score: Object.values(rubric).reduce((a, b) => a + b, 0),
    max: 10,
    rubric,
    status: 'RECONSTRUCTED_FIXED_RUBRIC_PROXY',
    note: 'Proxy uses the unchanged 10-point rubric at the previous verified component rows. Money freshness is fixed at 2 at the prior promoted available date. This is not an archived historical live decision.'
  };
}

function strongestAssets(report) {
  const accumulate = report?.opportunity_summary?.accumulate || [];
  const watch = report?.opportunity_summary?.watch || [];
  const source = accumulate.length ? accumulate : watch;
  return source.slice(0, 3).map(x => ({
    asset: x.asset,
    action: x.action,
    evidence_tier: x.evidence_tier,
    source_bucket: accumulate.length ? 'ACCUMULATE' : 'WATCH'
  }));
}

function mainRisk(report) {
  const funding = report?.regime?.current_research_inference?.funding;
  const money = report?.regime?.engine_fact?.money;
  const currentMarket = report?.current_market_confirmation;
  if (money?.agreement === 'DIVERGENT') {
    return `Money channels diverge: USD ${money.usd_regime} vs FX-neutral ${money.fx_neutral_regime}.`;
  }
  if (funding?.regime === 'RESTRICTIVE') {
    return `Funding V2 remains RESTRICTIVE (${Number(funding.score).toFixed(1)}), capping a stronger risk-on conclusion.`;
  }
  if ((currentMarket?.divergences || []).length) {
    return `${currentMarket.divergences.length} current-market divergence(s) versus completed-month structure.`;
  }
  return report?.data_health?.status === 'HEALTHY'
    ? 'No new decision-critical conflict; monitor promoted source freshness and market confirmation.'
    : `Data health is ${report?.data_health?.status || 'UNKNOWN'}; inspect refresh-status before increasing conviction.`;
}

export function buildDecisionDelta(report, moneyHistory, contextHistory) {
  const moneyPair = pair(moneyHistory?.rows);
  const fundingPair = pair(contextHistory?.funding?.rows);
  const fiscalPair = pair(contextHistory?.fiscal?.rows);
  const marketPair = pair(contextHistory?.market_confirmation?.rows);

  if (!moneyPair.current || !moneyPair.previous || !fundingPair.current || !fundingPair.previous || !fiscalPair.current || !fiscalPair.previous || !marketPair.current || !marketPair.previous) {
    throw new Error('Decision Delta requires at least two verified rows for Money, Funding, Fiscal and Market Confirmation');
  }

  const usd = moneyChannel(moneyPair.current, moneyPair.previous, 'usd_score');
  const fxn = moneyChannel(moneyPair.current, moneyPair.previous, 'fx_neutral_score');
  const funding = overlayLayer(fundingPair.current, fundingPair.previous);
  const fiscal = overlayLayer(fiscalPair.current, fiscalPair.previous);
  const marketDelta = finite(marketPair.current.score_0_2) - finite(marketPair.previous.score_0_2);
  const marketDirection = direction(marketDelta, 0.01);
  const previousConviction = reconstructedPreviousConviction(moneyPair.previous, fundingPair.previous, marketPair.previous);
  const currentConviction = finite(report?.regime?.conviction?.score);
  const convictionDelta = currentConviction != null && previousConviction ? currentConviction - previousConviction.score : null;

  const decisionDelta = {
    schema_version: 'gmli-decision-delta-v1',
    status: 'AVAILABLE',
    evidence_tier: 'RESEARCH_DIAGNOSTIC',
    scoring_effect: 'NONE',
    automatic_weight_change: 0,
    methodology_effect: 'NONE',
    generated_at: report?.generated_at || new Date().toISOString(),
    comparison_basis: 'CURRENT_VERIFIED_COMPONENT_ROW_VS_IMMEDIATELY_PREVIOUS_VERIFIED_COMPONENT_ROW',
    caveat: 'Component rows can have different publication dates. This layer summarizes change only; it does not create a synthetic Core score or modify frozen weights.',
    money: {
      evidence_tier: 'CORE',
      role: report?.signal_role_taxonomy?.money_core?.role || 'LEADING',
      current_available_date: moneyPair.current.available_date,
      previous_available_date: moneyPair.previous.available_date,
      usd,
      fx_neutral: fxn
    },
    funding: {
      evidence_tier: 'OVERLAY',
      role: report?.signal_role_taxonomy?.funding_v2?.role || 'REACTIVE_CONFIRMATION',
      ...funding
    },
    fiscal: {
      evidence_tier: 'OVERLAY',
      role: report?.signal_role_taxonomy?.fiscal_v2?.role || 'MIXED',
      ...fiscal
    },
    market_confirmation: {
      evidence_tier: 'RESEARCH',
      role: report?.signal_role_taxonomy?.market_confirmation?.role || 'REACTIVE_CONFIRMATION',
      current_month: marketPair.current.month,
      previous_month: marketPair.previous.month,
      current_positive: marketPair.current.positive,
      previous_positive: marketPair.previous.positive,
      current_score_0_2: marketPair.current.score_0_2,
      previous_score_0_2: marketPair.previous.score_0_2,
      delta_score_0_2: round(marketDelta, 2),
      direction: marketDirection,
      arrow: arrow(marketDirection)
    },
    conviction: {
      current: currentConviction,
      max: 10,
      previous_proxy: previousConviction?.score ?? null,
      delta_vs_previous_proxy: round(convictionDelta, 2),
      direction: direction(convictionDelta, 0.01),
      arrow: arrow(direction(convictionDelta, 0.01)),
      previous_proxy_detail: previousConviction,
      fiscal_v2_automatic_weight: 0
    }
  };

  const regimeInference = report?.regime?.current_research_inference || {};
  const strongest = strongestAssets(report);
  const whatChanged = [
    `Money USD ${usd.arrow} ${usd.delta >= 0 ? '+' : ''}${usd.delta ?? 'n/a'} pts to ${usd.current} (${usd.current_regime})`,
    `Money FX-neutral ${fxn.arrow} ${fxn.delta >= 0 ? '+' : ''}${fxn.delta ?? 'n/a'} pts to ${fxn.current} (${fxn.current_regime})`,
    `Funding ${funding.arrow} ${funding.delta >= 0 ? '+' : ''}${funding.delta ?? 'n/a'} pts to ${funding.current} (${funding.current_regime})`,
    `Fiscal ${fiscal.arrow} ${fiscal.delta >= 0 ? '+' : ''}${fiscal.delta ?? 'n/a'} pts to ${fiscal.current} (${fiscal.current_regime})`,
    `Market confirmation ${decisionDelta.market_confirmation.arrow} ${marketPair.previous.positive}/4 → ${marketPair.current.positive}/4 positive`,
    previousConviction
      ? `Conviction ${previousConviction.score}/10 proxy → ${currentConviction}/10 current`
      : `Conviction current ${currentConviction}/10; no comparable prior proxy`
  ];

  const brief = {
    schema_version: 'gmli-decision-brief-v1',
    status: 'AVAILABLE',
    scoring_effect: 'NONE',
    generated_at: report?.generated_at || new Date().toISOString(),
    regime: regimeInference.label || 'NEUTRAL',
    tilt: regimeInference.tilt || 'NEUTRAL',
    conviction: `${currentConviction}/10`,
    strongest_assets: strongest,
    main_risk: mainRisk(report),
    what_changed: whatChanged,
    action_note: strongest.length
      ? `Current opportunity emphasis: ${strongest.map(x => `${x.asset} ${x.action}`).join(' · ')}.`
      : 'No validated accumulate/watch emphasis is available from the current opportunity layer.',
    guardrail: 'Decision Brief is a presentation layer only. CORE / OVERLAY / RESEARCH separation and the frozen 10-point rubric are unchanged.'
  };

  return { decision_delta: decisionDelta, decision_brief: brief };
}

const STYLE = `<style>
.decisionGrid{display:grid;grid-template-columns:1.1fr .9fr;gap:12px}.decisionBriefHero{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px}.decisionMetric{padding:12px;border:1px solid #1f3446;border-radius:12px;background:#08141e}.decisionMetric b{display:block;font-size:20px;margin-top:4px}.decisionChangeList{margin:8px 0 0;padding-left:20px;color:#c8d6e1}.decisionChangeList li{margin:6px 0}.decisionAssets{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px}@media(max-width:900px){.decisionGrid{grid-template-columns:1fr}.decisionBriefHero{grid-template-columns:repeat(2,1fr)}}@media(max-width:520px){.decisionBriefHero{grid-template-columns:1fr}}
</style>`;

const SECTION = `<section id="decisionBrief" class="section">
<div class="trendHead"><div><h2>Decision Brief <span class="info" title="Sažetak postojećeg GMLI enginea i verificiranih promjena. Ne uvodi novi score niti mijenja CORE / OVERLAY / RESEARCH hijerarhiju.">i</span></h2><p class="muted">Što sada kaže engine, što se promijenilo i gdje je glavni rizik.</p></div><span class="pill">scoring effect: NONE</span></div>
<div class="decisionGrid">
<article class="card">
<div class="tag">GMLI NOW</div>
<div class="decisionBriefHero">
<div class="decisionMetric"><span class="muted small">Regime</span><b id="briefRegime">…</b></div>
<div class="decisionMetric"><span class="muted small">Tilt</span><b id="briefTilt">…</b></div>
<div class="decisionMetric"><span class="muted small">Conviction</span><b id="briefConviction">…</b></div>
<div class="decisionMetric"><span class="muted small">Main risk</span><b id="briefRisk" style="font-size:14px;line-height:1.35">…</b></div>
</div>
<div class="tag" style="margin-top:14px">Strongest now</div><div id="briefAssets" class="decisionAssets"></div>
</article>
<article class="card">
<div class="tag">WHAT CHANGED <span class="info" title="Usporedba zadnjeg verificiranog retka sa neposredno prethodnim retkom po svakom sloju. Prior conviction je označen kao reconstructed fixed-rubric proxy, ne kao arhivirani live decision.">i</span></div>
<ul id="decisionChanges" class="decisionChangeList"><li>Loading…</li></ul>
<div class="small muted" id="decisionDeltaNote"></div>
</article>
</div>
</section>`;

const SCRIPT = `<script>
(function(){
  window.renderDecisionBrief=function(r){
    const b=r?.decision_brief,d=r?.decision_delta;
    if(!b||!d)return;
    const set=(id,v)=>{const el=document.getElementById(id);if(el)el.textContent=v??'n/a'};
    set('briefRegime',b.regime);set('briefTilt',b.tilt);set('briefConviction',b.conviction);set('briefRisk',b.main_risk);
    const a=document.getElementById('briefAssets');if(a)a.innerHTML=(b.strongest_assets||[]).length?(b.strongest_assets||[]).map(x=>'<span class="pill"><b>'+esc(x.asset)+'</b> · '+esc(x.action)+'</span>').join(''):'<span class="muted small">No current emphasis</span>';
    const c=document.getElementById('decisionChanges');if(c)c.innerHTML=(b.what_changed||[]).map(x=>'<li>'+esc(x)+'</li>').join('');
    const n=document.getElementById('decisionDeltaNote');if(n)n.textContent='Comparison: '+(d.comparison_basis||'n/a')+' · '+(d.caveat||'');
  };
})();
</script>`;

function req(html, old, replacement, label) {
  if (!html.includes(old)) throw new Error(`Decision Delta UI marker missing: ${label}`);
  return html.replace(old, replacement);
}

export function enhanceDecisionDeltaUi(input) {
  let html = req(input, '</head>', `${STYLE}\n</head>`, 'head');
  html = req(html, '<nav class="nav"><a href="#now">REGIME</a><a href="#moneyTrend">MONEY TREND</a>', '<nav class="nav"><a href="#now">REGIME</a><a href="#decisionBrief">DECISION</a><a href="#moneyTrend">MONEY TREND</a>', 'nav');
  html = req(html, '<section id="moneyTrend"', `${SECTION}\n<section id="moneyTrend"`, 'section');
  html = req(html, '<script src="/money-ui-live.js', `${SCRIPT}\n<script src="/money-ui-live.js`, 'script');
  html = req(html, 'marketGrid.innerHTML=marketCards(cm);', 'renderDecisionBrief(r);marketGrid.innerHTML=marketCards(cm);', 'render call');
  return html;
}
