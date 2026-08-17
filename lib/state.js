export const FROZEN_STATE = {
  as_of: '2026-08-17',
  methodology: {
    status: 'FROZEN_SPEC',
    meaning: 'Weights, lags, horizons, thresholds, train/validation split, FX-neutral methodology and FDR rules are frozen. Data vintages may advance only through an explicit promotion gate.',
    core_auto_update: false
  },
  money: {
    status: 'CORE',
    methodology_status: 'FROZEN_SPEC',
    data_vintage_status: 'VALIDATED_CORE_STALE',
    available_date: '2026-02-28',
    usd_z: 0.9421742066088,
    usd_score: 65.70290344348,
    fxn_z: -0.4191532308133366,
    fxn_score: 43.01411281977772,
    freshness: 'STALE',
    note: 'CORE means the last formally validated vintage under the frozen specification; it does not mean the February data are intended to remain permanent.',
    promotion_candidate: {
      status: 'PROMOTION_CANDIDATE_NOT_CORE',
      evidence_tier: 'RESEARCH',
      version: 'v1.8b-production-money-migration',
      observation_date: '2026-05-31',
      available_date: '2026-06-30',
      coverage: '7/7',
      weighted_coverage: 1,
      usd_yoy_pct: 9.325796746551328,
      fx_neutral_yoy_pct: 6.1275189367599765,
      fx_effect_pp: 3.1982778097913513,
      usd_z: 0.5811506179874022,
      usd_score: 59.68584363312337,
      fxn_z: -0.2809735803930439,
      fxn_score: 45.31710699344927,
      interpretation: 'USD Money remains supportive but less stretched than the validated February vintage; FX-neutral Money remains neutral/slightly weak.'
    },
    promotion_gate: {
      status: 'BLOCKED_MISSING_FROZEN_INPUT_BYTES',
      core_replacement_allowed: false,
      methodology_changed: false,
      final_audit_date: '2026-08-17',
      final_audit: {
        decision: 'BLOCKED_MISSING_FROZEN_INPUT_BYTES',
        promote_to_core: false,
        contract_sha256: '0a777dd3f390a4410b409b8b3d650aec125aa59fe5afb749ef9fc34a0f8b0f1f',
        audit_runner_sha256: '31687b1eb40e537042d01a04f34301d31e30caa8f20afbe79224cd2889b1adb9'
      },
      production_source_transfer: {
        key_direction_same: '9/9',
        key_fdr_pass: '6/9',
        dbc_gld_direction_same: '7/7',
        full56_supported_fdr: 6,
        full56_reversed_fdr: 5,
        status: 'PASS_LOCKED_RESULTS'
      },
      australia_source_purity: {
        rba_series: 'DMABMS',
        status: 'PASS',
        migration_months: 138,
        latest_observation: '2026-06-30',
        may_2026_level_aud_bn: 3471.0,
        latest_level_aud_bn: 3499.9,
        june_2026_raw_level_yoy_pct: 7.97828,
        missing_months: 0,
        source_bytes_sha256: 'beb163053d91d6036c032ffbf84d4fac97c418cb13376dfd71ff845871f5b754'
      },
      australia_locked_sensitivity_equivalence: {
        status: 'PASS_WITHIN_LOCKED_15PCT_STRESS_ENVELOPE',
        overlap_months: 135,
        min_rba_over_imf_ratio: 0.8734897778252018,
        max_rba_over_imf_ratio: 1.0096069140211081,
        worst_abs_pct_diff: -12.651022217479824,
        locked_result: '0.85x/1.00x/1.15x all produced supported56=6, reversed56=5, key_dir=9, key_q9=6, dbc_gld_dir=7.'
      },
      exact_frozen_v12_rerun: {
        status: 'NOT_EXECUTED_MISSING_PRESERVED_INPUTS',
        executed: false,
        missing_required_inputs: [
          'v18b-global-money-monthly frozen matrix',
          'v12 exact-ticker adjusted-price frozen mirror',
          'v12 exact-ticker executable runner',
          'v18b full56 migration baseline matrix'
        ],
        reason: 'The exact Aug-15 macro matrix, adjusted-price mirror, original runner and full56 baseline were not preserved as accessible bytes. Current/revised public data cannot be substituted without turning the promotion rerun into a new experiment.'
      },
      next_action: 'Keep the February validated Core as ENGINE FACT and the June v1.8b values as RESEARCH promotion candidate. If the original frozen input bytes are ever recovered, run the checksummed promotion contract once; do not rebuild the missing vintage from revised data and call it an exact rerun.'
    }
  },
  funding: {
    status: 'RESEARCH_REGIME_OVERLAY',
    available_date: '2026-07-31',
    z: -0.8378753440785458,
    score: 36.035410932024234
  },
  credit: {
    status: 'RESEARCH_TRANSMISSION_OVERLAY',
    available_date: '2026-07-31',
    z: 0.2709184631191401,
    score: 54.51530771865234
  },
  fiscal: {
    status: 'RESEARCH_OVERLAY_ONLY',
    available_date: '2026-07-31',
    z: 0.1523733868591229,
    score: 52.539556447652046,
    mode: 'STRICT_ACTUAL_RELEASE'
  },
  research100: {
    status: 'NOT_VALIDATED_CORE',
    available_date: '2026-02-28',
    usd_score: 54.585023951039496,
    fxn_score: 45.50950770155858,
    freshness: 'STALE_BECAUSE_MONEY'
  },
  transmission: {
    status: 'FROZEN_RESEARCH_RELATIONSHIPS',
    priority: [
      'SPY 12M accel3',
      'QQQ 12M accel3',
      'GLD FX-neutral 12M',
      'DBC USD 6M',
      'DBC USD 12M',
      'DBC FX-neutral 6M'
    ]
  }
};

export function regimeFromScore(score) {
  if (score < 25) return 'STRONG RISK-OFF';
  if (score < 40) return 'RISK-OFF';
  if (score < 60) return 'NEUTRAL';
  if (score < 75) return 'RISK-ON';
  return 'STRONG RISK-ON';
}
