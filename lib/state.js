export const FROZEN_STATE = {
  as_of: '2026-08-15',
  money: {
    status: 'CORE',
    available_date: '2026-02-28',
    usd_z: 0.9421742066088,
    usd_score: 65.70290344348,
    fxn_z: -0.4191532308133366,
    fxn_score: 43.01411281977772,
    freshness: 'STALE'
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
