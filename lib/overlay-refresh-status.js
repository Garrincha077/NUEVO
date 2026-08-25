export const OVERLAY_REFRESH_STATUS = {
  funding: {
    evidence_tier: 'OVERLAY',
    version: 'GMLI_FUNDING_V2_EFFECTIVE_CONDITIONS',
    last_good_date: '2026-07-31',
    automation_status: 'ACTIVE_GUARDED_REFRESH',
    refreshable: true,
    blocker: null,
    methodology_provenance: 'FROZEN_FUNDING_V2_WITH_RAW_SOURCE_ARCHIVE_AND_FAIL_CLOSED_GUARDS',
    promotion_status: 'PASS_FUNDING_V2_PRODUCTION_PROMOTION',
    usefulness_scope: 'DBC 6M/12M fixed directional gate passed; SPY/QQQ/GLD diagnostics do not define promotion or universal return claims.',
    prospective_archive: {
      status: 'ACTIVE',
      manifest: 'research/funding-v2/latest/manifest.lock.json',
      raw_series: ['ANFCI', 'DFII10', 'THREEFYTP10', 'WRESBAL'],
      hashes_preserved: true,
      last_good_policy: 'Fail closed and retain the previous validated snapshot if source, direction, provenance or date-regression guards fail.'
    },
    historical_reference: {
      version: 'GMLI_FUNDING_LEGACY_JULY_2026',
      available_date: '2026-07-31',
      score: 36.035410932024234,
      status: 'OVERLAY_HISTORICAL_REFERENCE',
      historical_blocker: 'BLOCKED_BASELINE_MISMATCH'
    },
    guardrail: 'Funding V2 remains a bounded conviction overlay and never overrides Money Core.'
  },
  credit: {
    evidence_tier: 'OVERLAY',
    last_good_date: '2026-07-31',
    automation_status: 'BLOCKED_MISSING_FROZEN_CONSTRUCTION_PROVENANCE',
    refreshable: false,
    blocker: 'Production preserves the July 2026 Credit/Velocity score, but the exact frozen component construction and source lineage are not available in the current repository or recovered research artifacts. Do not infer or redesign the formula.',
    methodology_provenance: 'MISSING_EXACT_FROZEN_CONSTRUCTION',
    guardrail: 'Credit/Velocity remains a research transmission overlay and cannot be silently redesigned.'
  },
  fiscal: {
    evidence_tier: 'OVERLAY',
    version: 'GMLI_FISCAL_V2_DEFICIT_IMPULSE',
    last_good_date: '2026-07-31',
    automation_status: 'ACTIVE_GUARDED_REFRESH',
    refreshable: true,
    blocker: null,
    methodology_provenance: 'FROZEN_FISCAL_V2_WITH_RAW_SOURCE_ARCHIVE_AND_FAIL_CLOSED_GUARDS',
    promotion_status: 'PASS_FISCAL_V2_PRODUCTION_PROMOTION',
    usefulness_scope: 'SPY 12M fixed train/OOS directional gate passed; QQQ/DBC diagnostics do not define promotion or universal-return claims.',
    prospective_archive: {
      status: 'ACTIVE',
      manifest: 'research/fiscal-v2/latest/manifest.lock.json',
      raw_series: ['MTSDS133FMS', 'GDP', 'GFDEBTN', 'A091RC1Q027SBEA', 'FGRECPT', 'FGEXPND'],
      hashes_preserved: true,
      last_good_policy: 'Fail closed and retain the previous validated Fiscal V2 snapshot if source, provenance, construction, usefulness or date-regression guards fail.'
    },
    historical_reference: {
      version: 'GMLI_FISCAL_LEGACY_JULY_2026',
      available_date: '2026-07-31',
      score: 52.539556447652046,
      status: 'OVERLAY_HISTORICAL_REFERENCE',
      historical_blocker: 'BLOCKED_MISSING_EXACT_HISTORICAL_STRICT_RELEASE_RUNNER'
    },
    guardrail: 'Fiscal V2 is a refreshable OVERLAY with zero automatic global conviction weight; Money Core and Funding V2 remain unchanged.'
  }
};
