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
    last_good_date: '2026-07-31',
    automation_status: 'PROSPECTIVE_SOURCE_CAPTURE_ACTIVE_SCORE_REFRESH_BLOCKED',
    refreshable: false,
    blocker: 'Prospective raw FRED source capture is active and preserves future bytes/hashes, but the exact historical strict-release runner/vintages were not recovered. Production Fiscal score must remain locked until a strict-release transform reproduces the July 2026 baseline exactly under CI.',
    methodology_provenance: 'FROZEN_STRICT_ACTUAL_RELEASE_CONSTRUCTION_DOCUMENTED_PROSPECTIVE_BYTES_ACTIVE',
    prospective_capture: {
      status: 'ACTIVE',
      first_capture_at: '2026-08-24T08:51:52Z',
      manifest: 'research/fiscal-prospective/latest/manifest.json',
      series_count: 6,
      strict_release_ready: false
    },
    baseline: {
      z: 0.1523733868591229,
      score: 52.539556447652046,
      mode: 'STRICT_ACTUAL_RELEASE'
    },
    guardrail: 'Only an exact strict-actual-release refresh may advance this overlay; current-revised substitutions are not allowed.'
  }
};
