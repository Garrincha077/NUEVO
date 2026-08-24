export const FROZEN_STATE = {
  as_of: '2026-08-24',
  methodology: {
    status: 'FROZEN_V2_SPEC',
    meaning: 'The promoted Money V2 construction is locked: regions, weighting, publication lag, z-score window, FX-neutral methodology, transmission horizons and evaluation rules do not change during data refreshes.',
    core_auto_update: true,
    data_refresh_rule: 'New vintages may advance automatically only through the promoted Money V2 official-source contract and its fail-closed guards.'
  },
  money: {
    status: 'CORE',
    version: 'GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL',
    methodology_status: 'FROZEN_V2_SPEC',
    data_vintage_status: 'VALIDATED_CORE_ACTIVE',
    observation_month: '2026-06',
    available_date: '2026-07-31',
    usd_yoy_pct: 7.956975,
    fx_neutral_yoy_pct: 5.946277,
    fx_effect_pp: 2.010698,
    usd_z: 0.306729,
    usd_score: 55.1121,
    fxn_z: -0.330721,
    fxn_score: 44.4880,
    freshness: 'AUTO_FROM_AVAILABLE_DATE',
    source_contract: 'PBOC_OFFICIAL_M2_V2 + seven-region official-source Global Money V2',
    source_manifest: 'research/global-money-v2/latest/manifest.lock.json',
    note: 'Money V2 passed the explicit source/convention gate and the fixed 6/6 transmission-transfer gate. Data may refresh prospectively under the same frozen V2 contract; methodology may not silently change.',
    promotion_gate: {
      status: 'PASS_MONEY_V2_PRODUCTION_PROMOTION',
      core_replacement_allowed: true,
      promoted_version: 'GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL',
      promotion_date: '2026-08-24',
      promotion_report: 'research/global-money-v2/GMLI_GLOBAL_MONEY_V2_PROMOTION_REPORT.md',
      may_2026_bridge_regression: {
        status: 'PASS',
        legacy_usd_yoy_pct: 9.3258,
        v2_usd_yoy_pct: 9.341915,
        usd_delta_pp: 0.016115,
        legacy_fxn_yoy_pct: 6.1275,
        v2_fxn_yoy_pct: 6.153468,
        fxn_delta_pp: 0.025968
      },
      fixed_transmission_transfer: {
        status: 'PASS_6_OF_6',
        asset_search: false,
        horizon_search: false,
        lag_search: false,
        parameter_search: false,
        new_fdr_claim: false
      }
    },
    historical_reference: {
      status: 'CORE_HISTORICAL_REFERENCE',
      version: 'GMLI_PRE_V2_VALIDATED_CORE',
      available_date: '2026-02-28',
      usd_z: 0.9421742066088,
      usd_score: 65.70290344348,
      fxn_z: -0.4191532308133366,
      fxn_score: 43.01411281977772,
      note: 'Last formally validated pre-V2 Core. Preserved for audit/comparison; no longer the active production Money vintage after V2 promotion.'
    },
    historical_v18b_candidate: {
      status: 'RESEARCH_BLOCKED_HISTORICAL',
      version: 'v1.8b-production-money-migration',
      observation_date: '2026-05-31',
      available_date: '2026-06-30',
      coverage: '7/7',
      usd_yoy_pct: 9.325796746551328,
      fx_neutral_yoy_pct: 6.1275189367599765,
      fx_effect_pp: 3.1982778097913513,
      usd_z: 0.5811506179874022,
      usd_score: 59.68584363312337,
      fxn_z: -0.2809735803930439,
      fxn_score: 45.31710699344927,
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
        exact_frozen_v12_rerun: {
          status: 'NOT_EXECUTED_MISSING_PRESERVED_INPUTS',
          executed: false,
          reason: 'Original Aug-15 frozen input bytes were not preserved. Current/revised public data are never substituted and called an exact rerun.'
        }
      }
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
    freshness: 'STALE_BECAUSE_LEGACY_MONEY_REFERENCE'
  },
  transmission: {
    status: 'FROZEN_PROMOTED_RELATIONSHIPS',
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
