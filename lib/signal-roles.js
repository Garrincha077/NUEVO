export const SIGNAL_ROLE_TAXONOMY = {
  version: 'GMLI_SIGNAL_ROLE_TAXONOMY_V1',
  evidence_tier: 'RESEARCH',
  scoring_effect: 'NONE',
  automatic_weight_change: 0,
  money_core: {
    role: 'LEADING',
    interpretation: 'Upstream 3-12M Money/liquidity regime signal; not a structural-causality or monthly-timing claim.',
    evidence: 'Promoted fixed Money transmission remains 6/6; fixed directional follow-up shows no robust market-to-Money dominance across stationary promoted transforms.'
  },
  funding_v2: {
    role: 'REACTIVE_CONFIRMATION',
    interpretation: 'Financial-conditions/friction overlay. Market/volatility stress tends to precede changes in Funding, so use primarily as current-state confirmation and conviction context.',
    evidence: 'SPY/QQQ -> Funding 6/6 Holm-significant fixed 1/3/6M tests; Funding -> equities 0/6; effect persists ex-pandemic and is largely VIX-mediated.'
  },
  fiscal_v2: {
    role: 'MIXED',
    interpretation: 'Fiscal/policy context with positive fixed SPY 12M usefulness but weak, regime-dependent temporal precedence; not a clean leading factor.',
    evidence: 'Fixed SPY 12M usefulness PASS; reverse SPY -> Fiscal appears in full sample but disappears ex-pandemic/common-driver controls; automatic weight remains 0.'
  },
  market_confirmation: {
    role: 'REACTIVE_CONFIRMATION',
    interpretation: 'Completed-month cross-asset price-turn confirmation; validates or contradicts the upstream regime rather than creating it.'
  },
  overlap_note: {
    funding_vs_market_confirmation: 'LOW_DIRECT_SCORE_OVERLAP',
    funding_rubric_market_pearson: 0.128075,
    funding_rubric_market_spearman: 0.086631,
    exact_score_agreement_rate: 0.22973,
    implication: 'Both are reactive but measure materially different state channels; no frozen rubric change is justified by the overlap diagnostic.'
  },
  guardrail: 'Interpretation metadata only. No score, threshold, promoted relationship, evidence tier or 10-point conviction weight is changed. Any role-based reweighting requires a separately frozen decision-engine candidate.',
  research: 'research/signal-role-taxonomy/RESULT_SUMMARY.json'
};
