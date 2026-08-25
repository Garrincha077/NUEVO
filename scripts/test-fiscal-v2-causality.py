#!/usr/bin/env python3
"""Exploratory Fiscal V2 predictive-precedence diagnostics.

RESEARCH ONLY. This script does not alter production, scoring, promotion status,
Money Core, Funding V2, or the 10-point conviction rubric. Granger causality is
used only as a predictive-precedence diagnostic, not as structural causal proof.
"""
import argparse
import importlib.util
import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'research' / 'fiscal-v2' / 'CAUSALITY_RESEARCH_SPEC.json'
CANDIDATE_RUNNER = ROOT / 'scripts' / 'build-fiscal-v2.py'
HELPERS_PATH = ROOT / 'scripts' / 'test-global-money-v2-transmission.py'
VERSION = 'GMLI_FISCAL_V2_CAUSALITY_RESEARCH_V1'
LAGS = [1, 3, 6]
ALPHA = 0.05


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    assert spec['study_version'] == VERSION
    assert spec['status'] == 'FROZEN_BEFORE_EXPLORATORY_RUN'
    assert spec['evidence_tier'] == 'RESEARCH'
    assert spec['production_implication'] == 'NONE'
    assert spec['granger']['fixed_lags_months'] == LAGS
    assert spec['granger']['alpha'] == ALPHA
    assert all(v is False for v in spec['no_search'].values())
    assert spec['automatic_global_conviction_weight_change'] == 0
    assert spec['production_modified'] is False
    assert spec['money_core_modified'] is False
    assert spec['funding_v2_modified'] is False
    return spec


def holm_adjust(pvals):
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    adjusted = [None] * n
    running = 0.0
    for rank, idx in enumerate(order):
        adj = min(1.0, (n - rank) * pvals[idx])
        running = max(running, adj)
        adjusted[idx] = running
    return adjusted


def adf_summary(values, name):
    x = pd.Series(values).dropna().astype(float)
    stat, pvalue, usedlag, nobs, crit, _ = adfuller(x, autolag='AIC')
    return {
        'series': name,
        'n': int(nobs),
        'adf_stat': round(float(stat), 6),
        'p_value': round(float(pvalue), 6),
        'used_lag': int(usedlag),
        'stationary_at_5pct': bool(pvalue < 0.05),
        'critical_5pct': round(float(crit['5%']), 6),
    }


def build_monthly_frame(fiscal_history, spy, helpers):
    fiscal_by_available = {}
    for row in fiscal_history:
        score = row.get('score')
        if score is None or not math.isfinite(score):
            continue
        avail = row['available_date'][:7]
        fiscal_by_available[avail] = float(score)

    months = sorted(set(fiscal_by_available) & set(spy))
    rows = []
    for month in months:
        prior = helpers.add_months(month, -1)
        if prior not in spy:
            continue
        rows.append({
            'month': month,
            'fiscal_score': fiscal_by_available[month],
            'spy_1m_return': math.log(spy[month] / spy[prior]),
        })
    df = pd.DataFrame(rows).sort_values('month').reset_index(drop=True)
    df['delta_fiscal_score'] = df['fiscal_score'].diff()
    return df.dropna().reset_index(drop=True)


def granger_direction(df, target, predictor):
    data = df[[target, predictor]].dropna().astype(float)
    raw = grangercausalitytests(data, maxlag=max(LAGS), verbose=False)
    pvals = [float(raw[lag][0]['ssr_ftest'][1]) for lag in LAGS]
    adjusted = holm_adjust(pvals)
    out = []
    for lag, p, adj in zip(LAGS, pvals, adjusted):
        out.append({
            'lag_months': lag,
            'raw_p_value': round(p, 6),
            'holm_p_value': round(adj, 6),
            'significant_5pct_after_holm': bool(adj < ALPHA),
        })
    return {
        'target': target,
        'predictor': predictor,
        'n': int(len(data)),
        'tests': out,
        'any_holm_significant_5pct': any(x['significant_5pct_after_holm'] for x in out),
    }


def forward_regression_rows(fiscal_history, spy, helpers):
    rows = []
    for f in fiscal_history:
        score = f.get('score')
        if score is None or not math.isfinite(score):
            continue
        obs = f['observation_month']
        avail = f['available_date'][:7]
        start = helpers.add_months(obs, 2)
        end = helpers.add_months(start, 12)
        trailing_start = helpers.add_months(avail, -12)
        needed = [avail, start, end, trailing_start]
        if any(m not in spy for m in needed):
            continue
        rows.append({
            'signal_month': obs,
            'available_month': avail,
            'fiscal_score': float(score),
            'trailing_12m_spy': math.log(spy[avail] / spy[trailing_start]),
            'forward_12m_spy': math.log(spy[end] / spy[start]),
        })
    return pd.DataFrame(rows)


def hac_regression(df):
    y = df['forward_12m_spy'].astype(float)
    baseline_x = sm.add_constant(df[['trailing_12m_spy']].astype(float), has_constant='add')
    full_x = sm.add_constant(df[['fiscal_score', 'trailing_12m_spy']].astype(float), has_constant='add')
    baseline = sm.OLS(y, baseline_x).fit(cov_type='HAC', cov_kwds={'maxlags': 12})
    full = sm.OLS(y, full_x).fit(cov_type='HAC', cov_kwds={'maxlags': 12})
    coef = float(full.params['fiscal_score'])
    pval = float(full.pvalues['fiscal_score'])
    return {
        'n': int(len(df)),
        'fiscal_coef_per_score_point': round(coef, 8),
        'fiscal_coef_per_10_score_points_log_return': round(coef * 10.0, 6),
        'fiscal_hac_p_value': round(pval, 6),
        'fiscal_positive': bool(coef > 0),
        'fiscal_significant_5pct': bool(pval < ALPHA),
        'baseline_r_squared': round(float(baseline.rsquared), 6),
        'full_r_squared': round(float(full.rsquared), 6),
        'delta_r_squared': round(float(full.rsquared - baseline.rsquared), 6),
        'hac_maxlags': 12,
    }


def lead_lag_placebo(df):
    forward = float(df['fiscal_score'].corr(df['forward_12m_spy']))
    trailing = float(df['fiscal_score'].corr(df['trailing_12m_spy']))
    return {
        'n': int(len(df)),
        'forward_12m_pearson': round(forward, 6),
        'trailing_12m_pearson': round(trailing, 6),
        'forward_minus_trailing': round(forward - trailing, 6),
        'forward_association_stronger': bool(forward > trailing),
    }


def classify(forward_granger, reverse_granger, hac, placebo):
    g = forward_granger['any_holm_significant_5pct']
    reverse = reverse_granger['any_holm_significant_5pct']
    h = hac['fiscal_positive'] and hac['fiscal_significant_5pct']
    p = placebo['forward_association_stronger']
    if g and not reverse and h:
        return 'SUPPORTIVE_PREDICTIVE_PRECEDENCE'
    if g or h or p:
        return 'MIXED_OR_WEAK_PREDICTIVE_PRECEDENCE'
    return 'NO_PREDICTIVE_PRECEDENCE'


def run(as_of):
    spec = validate_spec()
    candidate_module = load_module(CANDIDATE_RUNNER, 'gmli_fiscal_candidate')
    helpers = load_module(HELPERS_PATH, 'gmli_helpers')
    candidate = candidate_module.build(as_of)
    if candidate['status'] != 'PASS_FIXED_CONSTRUCTION_SANITY':
        raise RuntimeError('Fiscal V2 construction sanity must remain PASS')

    spy, _, price_meta = helpers.fetch_price('SPY')
    monthly = build_monthly_frame(candidate['history'], spy, helpers)
    if len(monthly) < 60:
        raise RuntimeError(f'Insufficient monthly observations for causality diagnostics: {len(monthly)}')

    stationarity = [
        adf_summary(monthly['fiscal_score'], 'fiscal_score_level'),
        adf_summary(monthly['delta_fiscal_score'], 'delta_fiscal_score'),
        adf_summary(monthly['spy_1m_return'], 'spy_1m_log_return'),
    ]
    forward_granger = granger_direction(monthly, 'spy_1m_return', 'delta_fiscal_score')
    reverse_granger = granger_direction(monthly, 'delta_fiscal_score', 'spy_1m_return')

    reg_df = forward_regression_rows(candidate['history'], spy, helpers)
    if len(reg_df) < 50:
        raise RuntimeError(f'Insufficient 12M regression observations: {len(reg_df)}')
    hac = hac_regression(reg_df)
    placebo = lead_lag_placebo(reg_df)
    conclusion = classify(forward_granger, reverse_granger, hac, placebo)

    return {
        'status': 'INFORMATIONAL_CAUSALITY_RESEARCH_COMPLETE',
        'study_version': VERSION,
        'evidence_tier': 'RESEARCH',
        'as_of': as_of.isoformat(),
        'conclusion': conclusion,
        'causal_claim_allowed': False,
        'production_implication': 'NONE',
        'automatic_global_conviction_weight_change': 0,
        'production_modified': False,
        'money_core_modified': False,
        'funding_v2_modified': False,
        'candidate_version': candidate['candidate_version'],
        'candidate_latest_eligible': candidate['latest_eligible'],
        'price_source': price_meta,
        'sample': {
            'granger_first_month': monthly['month'].iloc[0],
            'granger_last_month': monthly['month'].iloc[-1],
            'granger_n': int(len(monthly)),
            'regression_first_signal_month': reg_df['signal_month'].iloc[0],
            'regression_last_signal_month': reg_df['signal_month'].iloc[-1],
            'regression_n': int(len(reg_df)),
        },
        'stationarity': stationarity,
        'granger_fiscal_to_spy': forward_granger,
        'granger_spy_to_fiscal': reverse_granger,
        'incremental_12m_hac_regression': hac,
        'lead_lag_placebo': placebo,
        'interpretation_guardrail': 'Granger causality means predictive precedence, not structural economic causality. HAC regression and lead/lag asymmetry are complementary diagnostics only. Revised FRED history and a short post-2017 sample limit inference.',
        'spec': spec,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', default=date.today().isoformat())
    parser.add_argument('--output', default='')
    args = parser.parse_args()
    result = run(date.fromisoformat(args.as_of))
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding='utf-8')
    print(text, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
