export const OVERLAY_REFRESH_STATUS = {
  funding: {
    evidence_tier: 'OVERLAY',
    last_good_date: '2026-07-31',
    automation_status: 'BLOCKED_BASELINE_MISMATCH',
    refreshable: false,
    blocker: 'Published frozen 5/5 Funding July 2026 reading is z -0.796 / score 36.73, while production baseline is z -0.8378753440785458 / score 36.035410932024234. Do not automate until the exact production July baseline is reproduced from preserved inputs and transforms.',
    methodology_provenance: 'FROZEN_CONSTRUCTION_DOCUMENTED_BASELINE_REGRESSION_PENDING',
    guardrail: 'Funding remains a conviction overlay and never overrides Money Core.'
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
    automation_status: 'BASELINE_MATCHED_IMPLEMENTATION_PENDING',
    refreshable: false,
    blocker: 'Strict actual-release formula and July baseline are reproduced in the research documentation, but a production refresh runner with preserved vintage/release-date inputs has not yet been implemented and regression-tested.',
    methodology_provenance: 'FROZEN_STRICT_ACTUAL_RELEASE_CONSTRUCTION_DOCUMENTED',
    baseline: {
      z: 0.1523733868591229,
      score: 52.539556447652046,
      mode: 'STRICT_ACTUAL_RELEASE'
    },
    guardrail: 'Only an exact strict-actual-release refresh may advance this overlay; current-revised substitutions are not allowed.'
  }
};
