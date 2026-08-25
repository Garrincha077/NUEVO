#!/usr/bin/env python3
"""Informational Fiscal/Funding reverse-mechanism research.

Frozen scope: SPY/QQQ, Fiscal V2, Funding V2, fixed 1/3/6M Granger,
fixed controls, fixed component families and fixed subperiods. This script is
RESEARCH only and has no production side effects.
"""
import argparse
import io
import json
import math
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'research' / 'reverse-overlay-mechanism' / 'RESEARCH_SPEC.json'
FISCAL = ROOT / 'research' / 'fiscal-v2' / 'latest' / 'history.csv'
FUNDING = ROOT / 'research' / 'funding-v2' / 'latest' / 'history.csv'
VERSION = 'GMLI_REVERSE_OVERLAY_MECHANISM_V1'
UA = 'GMLI-Reverse-Overlay-Mechanism/1.0 fixed-no-search'
LAGS = [1, 3, 6]
PANDEMIC_START = '2020-03'
PANDEMIC_END = '2021-12'


def add_months(month, n):
    y, m = map(int, month.split('-'))
    total = y * 12 + (m - 1) + n
    yy, mm0 = divmod(total, 12)
    return f'{yy:04d}-{mm0+1:02d}'


def validate_spec():
    spec = json.loads(SPEC.read_text(encoding='utf-8'))
    assert spec['study_version'] == VERSION
    assert spec['status'] == 'FROZEN_BEFORE_EMPIRICAL_RUN'
    assert spec['primary_assets'] == ['SPY', 'QQQ']
    assert spec['tests']['bidirectional_granger']['lags_months'] == LAGS
    assert all(v is False for v in spec['no_search'].values())
    assert spec['production_modified'] is False
    assert spec['automatic_weight_change'] == 0
    return spec


def fetch_yahoo_monthly(symbol):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=max&interval=1mo&events=history&includeAdjustedClose=true'
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
    data = json.loads(raw.decode('utf-8'))
    result = ((data.get('chart') or {}).get('result') or [None])[0]
    if not result:
        raise RuntimeError(f'Yahoo returned no result for {symbol}')
    ts = result.get('timestamp') or []
    indicators = result.get('indicators') or {}
    vals = None
    adj = indicators.get('adjclose') or []
    if adj:
        vals = adj[0].get('adjclose')
    if not vals:
        quote = indicators.get('quote') or []
        vals = quote[0].get('close') if quote else None
    if not vals or len(vals) != len(ts):
        raise RuntimeError(f'Yahoo monthly values malformed for {symbol}')
    out = {}
    for t, v in zip(ts, vals):
        if not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            continue
        month = datetime.fromtimestamp(int(t), tz=timezone.utc).strftime('%Y-%m')
        out[month] = float(v)
    if len(out) < 100:
        raise RuntimeError(f'Implausibly short Yahoo history for {symbol}: {len(out)}')
    return out


def fetch_unrate():
    url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
    df = pd.read_csv(io.BytesIO(raw))
    value_col = [c for c in df.columns if c != 'observation_date'][0]
    out = {}
    for _, row in df.iterrows():
        try:
            v = float(row[value_col])
        except Exception:
            continue
        month = str(row['observation_date'])[:7]
        if math.isfinite(v):
            out[month] = v
    return out


def monthly_returns(price):
    months = sorted(price)
    out = {}
    for i in range(1, len(months)):
        m0, m1 = months[i-1], months[i]
        if add_months(m0, 1) != m1:
            continue
        out[m1] = math.log(price[m1] / price[m0])
    return out


def monthly_log_changes(price):
    return monthly_returns(price)


def read_overlay(path, score_col, components):
    df = pd.read_csv(path, dtype={'observation_month': str, 'available_date': str})
    keep = ['observation_month', 'available_date', score_col] + components
    df = df[keep].copy()
    for c in [score_col] + components:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['observation_month', score_col]).sort_values('observation_month')
    return df


def adf_info(values):
    s = pd.Series(values).dropna().astype(float)
    if len(s) < 20:
        return {'n': len(s), 'p_value': None, 'stationary_at_5pct': None}
    try:
        r = adfuller(s.values, autolag='AIC')
        return {'n': len(s), 'adf_stat': round(float(r[0]), 6), 'p_value': round(float(r[1]), 6), 'used_lag': int(r[2]), 'stationary_at_5pct': bool(r[1] < 0.05)}
    except Exception as exc:
        return {'n': len(s), 'p_value': None, 'stationary_at_5pct': None, 'error': str(exc)}


def stationary_transform(df, col):
    base = df[['observation_month', col]].dropna().copy()
    info_level = adf_info(base[col])
    if info_level.get('stationary_at_5pct'):
        base['value'] = base[col].astype(float)
        return base[['observation_month', 'value']], {'selected': 'level', 'level_adf': info_level, 'difference_adf': None}
    base['value'] = base[col].astype(float).diff()
    diff_info = adf_info(base['value'])
    return base.dropna(subset=['value'])[['observation_month', 'value']], {'selected': 'first_difference', 'level_adf': info_level, 'difference_adf': diff_info}


def series_dict(frame):
    return {str(r['observation_month']): float(r['value']) for _, r in frame.iterrows() if math.isfinite(float(r['value']))}


def aligned_frame(target, predictor, exclude_pandemic=False, start=None, end=None):
    months = sorted(set(target) & set(predictor))
    rows = []
    for m in months:
        if exclude_pandemic and PANDEMIC_START <= m <= PANDEMIC_END:
            continue
        if start and m < start:
            continue
        if end and m > end:
            continue
        rows.append((m, target[m], predictor[m]))
    if not rows:
        return pd.DataFrame(columns=['month', 'target', 'predictor'])
    return pd.DataFrame(rows, columns=['month', 'target', 'predictor'])


def granger_one(target, predictor, lag, exclude_pandemic=False, start=None, end=None):
    df = aligned_frame(target, predictor, exclude_pandemic, start, end)
    n = len(df)
    if n < max(20, 4 * lag + 8):
        return {'n': n, 'lag_months': lag, 'raw_p_value': None, 'error': 'insufficient_sample'}
    try:
        res = grangercausalitytests(df[['target', 'predictor']], maxlag=[lag], verbose=False)
        p = float(res[lag][0]['ssr_ftest'][1])
        return {'n': n, 'lag_months': lag, 'raw_p_value': round(p, 6)}
    except Exception as exc:
        return {'n': n, 'lag_months': lag, 'raw_p_value': None, 'error': str(exc)}


def apply_holm(rows):
    valid = [(i, r['raw_p_value']) for i, r in enumerate(rows) if r.get('raw_p_value') is not None]
    if not valid:
        return rows
    idx, pvals = zip(*valid)
    _, adj, _, _ = multipletests(pvals, alpha=0.05, method='holm')
    for i, p in zip(idx, adj):
        rows[i]['holm_p_value'] = round(float(p), 6)
        rows[i]['significant_5pct_after_holm'] = bool(p < 0.05)
    return rows


def bidirectional(overlays, market_returns, exclude_pandemic=False):
    market_to_overlay = []
    overlay_to_market = []
    for oid, odict in overlays.items():
        for asset, rdict in market_returns.items():
            for lag in LAGS:
                a = granger_one(odict, rdict, lag, exclude_pandemic)
                a.update({'overlay': oid, 'asset': asset, 'direction': 'market_to_overlay'})
                market_to_overlay.append(a)
                b = granger_one(rdict, odict, lag, exclude_pandemic)
                b.update({'overlay': oid, 'asset': asset, 'direction': 'overlay_to_market'})
                overlay_to_market.append(b)
    apply_holm(market_to_overlay)
    apply_holm(overlay_to_market)
    return {'market_to_overlay': market_to_overlay, 'overlay_to_market': overlay_to_market}


def map_diff(values):
    months = sorted(values)
    out = {}
    for i in range(1, len(months)):
        if add_months(months[i-1], 1) == months[i]:
            out[months[i]] = values[months[i]] - values[months[i-1]]
    return out


def common_driver_regression(overlay, spy_ret, vix_change, unrate):
    du = map_diff(unrate)
    months = sorted(set(overlay) & set(spy_ret) & set(vix_change) & set(du))
    base = pd.DataFrame(index=months)
    base['y'] = [overlay[m] for m in months]
    base['spy'] = [spy_ret[m] for m in months]
    base['vix'] = [vix_change[m] for m in months]
    base['unrate'] = [du[m] for m in months]
    for src in ['y', 'spy', 'vix', 'unrate']:
        for lag in range(1, 4):
            base[f'{src}_l{lag}'] = base[src].shift(lag)
    cols = [f'y_l{i}' for i in range(1,4)] + [f'spy_l{i}' for i in range(1,4)] + [f'vix_l{i}' for i in range(1,4)] + [f'unrate_l{i}' for i in range(1,4)]
    d = base[['y'] + cols].dropna()
    if len(d) < 35:
        return {'n': len(d), 'joint_spy_lags_p_value': None, 'error': 'insufficient_sample'}
    X = sm.add_constant(d[cols], has_constant='add')
    fit = sm.OLS(d['y'], X).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
    names = list(X.columns)
    R = np.zeros((3, len(names)))
    for j, lag in enumerate(range(1, 4)):
        R[j, names.index(f'spy_l{lag}')] = 1.0
    ft = fit.f_test(R)
    coefs = {f'spy_l{i}': round(float(fit.params[f'spy_l{i}']), 8) for i in range(1,4)}
    return {
        'n': len(d), 'r_squared': round(float(fit.rsquared), 6),
        'joint_spy_lags_f': round(float(np.asarray(ft.fvalue).squeeze()), 6),
        'joint_spy_lags_p_value': round(float(np.asarray(ft.pvalue).squeeze()), 6),
        'joint_spy_lags_significant_5pct': bool(float(np.asarray(ft.pvalue).squeeze()) < 0.05),
        'spy_lag_coefficients': coefs, 'hac_maxlags': 3,
    }


def component_tests(frames, spy_ret):
    fixed = [
        ('FISCAL_V2', frames['FISCAL_V2'], 'deficit_pct_gdp'),
        ('FISCAL_V2', frames['FISCAL_V2'], 'fiscal_impulse_pp'),
        ('FUNDING_V2', frames['FUNDING_V2'], 'observed_conditions_score'),
        ('FUNDING_V2', frames['FUNDING_V2'], 'structural_support_score'),
    ]
    rows = []
    transforms = {}
    for oid, frame, col in fixed:
        tf, meta = stationary_transform(frame, col)
        transforms[f'{oid}:{col}'] = meta
        r = granger_one(series_dict(tf), spy_ret, 3)
        r.update({'overlay': oid, 'component': col, 'direction': 'SPY_to_component'})
        rows.append(r)
    apply_holm(rows)
    return {'tests': rows, 'transforms': transforms}


def subperiod_tests(overlays, market_returns):
    periods = {
        'FUNDING_V2': [('2006_2012','2006-02','2012-12'), ('2013_2019','2013-01','2019-12'), ('2020_plus','2020-01',None)],
        'FISCAL_V2': [('2018_2019','2018-01','2019-12'), ('2020_plus','2020-01',None)],
    }
    out = []
    for oid, plist in periods.items():
        for label, start, end in plist:
            for asset, market in market_returns.items():
                a = granger_one(overlays[oid], market, 3, start=start, end=end)
                b = granger_one(market, overlays[oid], 3, start=start, end=end)
                out.append({'overlay': oid, 'period': label, 'asset': asset, 'direction': 'market_to_overlay', **a})
                out.append({'overlay': oid, 'period': label, 'asset': asset, 'direction': 'overlay_to_market', **b})
    return out


def pearson(xs, ys):
    if len(xs) < 3:
        return None
    return float(np.corrcoef(np.asarray(xs, float), np.asarray(ys, float))[0,1])


def lead_lag(frame, score_col, prices, invert=False):
    out = {}
    for asset, price in prices.items():
        xs, trailing, forward = [], [], []
        for _, row in frame.iterrows():
            m = str(row['observation_month'])
            avail = str(row['available_date'])[:7]
            decision_month = add_months(avail, 1)
            t0 = add_months(decision_month, -12)
            f1 = add_months(decision_month, 12)
            if decision_month not in price or t0 not in price or f1 not in price:
                continue
            x = float(row[score_col])
            if invert:
                x = 100.0 - x
            xs.append(x)
            trailing.append(math.log(price[decision_month] / price[t0]))
            forward.append(math.log(price[f1] / price[decision_month]))
        tr = pearson(xs, trailing); fw = pearson(xs, forward)
        out[asset] = {
            'n': len(xs),
            'trailing_12m_pearson': None if tr is None else round(tr, 6),
            'forward_12m_pearson': None if fw is None else round(fw, 6),
            'abs_trailing_minus_abs_forward': None if tr is None or fw is None else round(abs(tr)-abs(fw), 6),
            'association_stronger_with_past': None if tr is None or fw is None else bool(abs(tr) > abs(fw)),
        }
    return out


def summarize_mechanism(full, no_pandemic, common):
    def sig(rows, oid, direction):
        return [r for r in rows[direction] if r['overlay']==oid and r.get('significant_5pct_after_holm')]
    summary = {}
    for oid in ['FISCAL_V2', 'FUNDING_V2']:
        fwd = sig(full, oid, 'market_to_overlay')
        rev = sig(full, oid, 'overlay_to_market')
        np_fwd = sig(no_pandemic, oid, 'market_to_overlay')
        ctrl = common[oid].get('joint_spy_lags_significant_5pct') is True
        if fwd and (np_fwd or ctrl) and not rev:
            cls = 'MARKET_PRECEDENCE_SUPPORTED'
        elif fwd or np_fwd or ctrl or rev:
            cls = 'MIXED_OR_REGIME_DEPENDENT'
        else:
            cls = 'NO_REVERSE_PRECEDENCE'
        summary[oid] = {
            'classification': cls,
            'full_market_to_overlay_holm_significant': len(fwd),
            'full_overlay_to_market_holm_significant': len(rev),
            'ex_pandemic_market_to_overlay_holm_significant': len(np_fwd),
            'common_driver_spy_joint_significant': ctrl,
        }
    if any(v['classification']=='MARKET_PRECEDENCE_SUPPORTED' for v in summary.values()):
        overall = 'MARKET_PRECEDENCE_SUPPORTED_FOR_AT_LEAST_ONE_OVERLAY'
    elif any(v['classification']=='MIXED_OR_REGIME_DEPENDENT' for v in summary.values()):
        overall = 'MIXED_OR_REGIME_DEPENDENT'
    else:
        overall = 'NO_REVERSE_PRECEDENCE'
    return overall, summary


def run(as_of):
    spec = validate_spec()
    fiscal = read_overlay(FISCAL, 'score', ['deficit_pct_gdp','fiscal_impulse_pp'])
    funding = read_overlay(FUNDING, 'effective_score', ['observed_conditions_score','structural_support_score'])
    frames = {'FISCAL_V2': fiscal, 'FUNDING_V2': funding}
    f_tf, f_meta = stationary_transform(fiscal, 'score')
    u_tf, u_meta = stationary_transform(funding, 'effective_score')
    overlays = {'FISCAL_V2': series_dict(f_tf), 'FUNDING_V2': series_dict(u_tf)}

    prices = {a: fetch_yahoo_monthly(a) for a in ['SPY','QQQ']}
    market_returns = {a: monthly_returns(p) for a,p in prices.items()}
    vix = fetch_yahoo_monthly('^VIX')
    vix_change = monthly_log_changes(vix)
    unrate = fetch_unrate()

    full = bidirectional(overlays, market_returns, False)
    no_pandemic = bidirectional(overlays, market_returns, True)
    common = {
        oid: common_driver_regression(odict, market_returns['SPY'], vix_change, unrate)
        for oid, odict in overlays.items()
    }
    components = component_tests(frames, market_returns['SPY'])
    subperiods = subperiod_tests(overlays, market_returns)
    leadlag = {
        'FISCAL_V2_score': lead_lag(fiscal, 'score', prices, False),
        'FUNDING_V2_effective_score': lead_lag(funding, 'effective_score', prices, False),
        'FUNDING_V2_inverted_score': lead_lag(funding, 'effective_score', prices, True),
    }
    overall, overlay_summary = summarize_mechanism(full, no_pandemic, common)
    return {
        'status': 'INFORMATIONAL_REVERSE_OVERLAY_RESEARCH_COMPLETE',
        'study_version': VERSION,
        'evidence_tier': 'RESEARCH',
        'as_of': as_of.isoformat(),
        'conclusion': overall,
        'overlay_summary': overlay_summary,
        'causal_claim_allowed': False,
        'production_implication': 'NONE',
        'production_modified': False,
        'money_core_modified': False,
        'funding_v2_modified': False,
        'fiscal_v2_modified': False,
        'decision_engine_modified': False,
        'automatic_weight_change': 0,
        'stationarity': {'FISCAL_V2': f_meta, 'FUNDING_V2': u_meta},
        'bidirectional_granger_full': full,
        'bidirectional_granger_ex_pandemic_2020_03_to_2021_12': no_pandemic,
        'common_driver_regression': common,
        'component_attribution': components,
        'subperiod_stability_lag3_descriptive': subperiods,
        'lead_lag_asymmetry': leadlag,
        'interpretation_guardrail': 'Granger and lag regressions establish predictive precedence only. They do not establish structural economic causality. Revised historical macro data and overlapping regimes limit inference.',
        'spec': spec,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--as-of', default=date.today().isoformat())
    p.add_argument('--output', default=None)
    args = p.parse_args()
    result = run(date.fromisoformat(args.as_of))
    text = json.dumps(result, indent=2)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + '\n', encoding='utf-8')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
