#!/usr/bin/env python3
import argparse
import csv
import importlib.util
import io
import json
import math
from pathlib import Path

import numpy as np
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'research' / 'signal-role-taxonomy' / 'RESEARCH_SPEC.json'
MONEY_CSV = ROOT / 'research' / 'global-money-v2' / 'latest' / 'global_money_v2.csv'
HELPERS_PATH = ROOT / 'scripts' / 'test-global-money-v2-transmission.py'
LAGS = [1, 3, 6]
EXCLUDE_START = '2020-03'
EXCLUDE_END = '2021-12'
RELATIONS = [
    {'asset':'SPY','channel':'usd','transform':'accel3','horizon_m':12},
    {'asset':'QQQ','channel':'usd','transform':'accel3','horizon_m':12},
    {'asset':'GLD','channel':'fxn','transform':'accel3','horizon_m':12},
    {'asset':'DBC','channel':'usd','transform':'level','horizon_m':12},
]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_spec():
    s = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    assert s['study_version'] == 'GMLI_SIGNAL_ROLE_TAXONOMY_V1'
    assert s['status'] == 'FROZEN_BEFORE_MONEY_DIRECTION_TEST'
    assert s['money_direction_protocol']['lags_months'] == LAGS
    assert all(v is False for v in s['no_search'].values())
    assert s['production_modified'] is False
    assert s['automatic_weight_change'] == 0
    return s


def load_money(helpers):
    rows = list(csv.DictReader(io.StringIO(MONEY_CSV.read_text(encoding='utf-8'))))
    by_month = {}
    for r in rows:
        try:
            by_month[r['month']] = {
                'usd': float(r['gbm_usd_yoy_pct']),
                'fxn': float(r['gbm_fxn_yoy_pct']),
                'available_date': r['available_date'],
            }
        except (KeyError, ValueError):
            continue
    if not by_month:
        raise RuntimeError('Money V2 history missing')
    out = {}
    for rel in RELATIONS:
        key = f"{rel['channel']}_{rel['transform']}"
        series = {}
        for month in sorted(by_month):
            level = by_month[month][rel['channel']]
            if rel['transform'] == 'level':
                x = level
            else:
                prior = helpers.add_months(month, -3)
                if prior not in by_month:
                    continue
                x = level - by_month[prior][rel['channel']]
            available_month = helpers.add_months(month, 1)
            series[available_month] = {'x': x, 'observation_month': month}
        out[key] = series
    return out


def monthly_returns(price, helpers):
    months = sorted(price)
    r = {}
    for m in months:
        prior = helpers.add_months(m, -1)
        if prior in price and price[prior] > 0 and price[m] > 0:
            r[m] = math.log(price[m] / price[prior])
    return r


def holm(pvals):
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    adj = [None] * n
    running = 0.0
    for rank, idx in enumerate(order):
        candidate = min(1.0, (n - rank) * pvals[idx])
        running = max(running, candidate)
        adj[idx] = running
    return adj


def adf_info(values):
    vals = [float(x) for x in values if math.isfinite(float(x))]
    if len(vals) < 20:
        return {'n':len(vals),'p_value':None,'stationary_5pct':False}
    stat, p, usedlag, nobs, crit, _ = adfuller(vals, autolag='AIC')
    return {
        'n': len(vals),
        'stat': round(float(stat), 6),
        'p_value': round(float(p), 6),
        'used_lag': int(usedlag),
        'stationary_5pct': bool(p < 0.05),
        'critical_5pct': round(float(crit['5%']), 6),
    }


def aligned(signal, returns, exclude_pandemic=False):
    months = sorted(set(signal).intersection(returns))
    if exclude_pandemic:
        months = [m for m in months if not (EXCLUDE_START <= m <= EXCLUDE_END)]
    return months, np.array([[returns[m], signal[m]['x']] for m in months], dtype=float)


def granger_pair(signal, returns, exclude_pandemic=False, only_lag=None):
    months, data = aligned(signal, returns, exclude_pandemic=exclude_pandemic)
    lags = [only_lag] if only_lag else LAGS
    if len(data) < max(lags) + 20:
        return {'n':len(data),'tests':[]}
    fwd_raw = []
    rev_raw = []
    for lag in lags:
        # statsmodels tests whether column 2 Granger-causes column 1.
        fwd = grangercausalitytests(data, maxlag=[lag], verbose=False)[lag][0]['ssr_ftest'][1]
        reverse_data = data[:, [1, 0]]
        rev = grangercausalitytests(reverse_data, maxlag=[lag], verbose=False)[lag][0]['ssr_ftest'][1]
        fwd_raw.append(float(fwd)); rev_raw.append(float(rev))
    fwd_adj = holm(fwd_raw); rev_adj = holm(rev_raw)
    tests = []
    for i, lag in enumerate(lags):
        tests.append({
            'lag_months': lag,
            'money_to_asset_raw_p': round(fwd_raw[i], 6),
            'money_to_asset_holm_p': round(fwd_adj[i], 6),
            'money_to_asset_sig_5pct': bool(fwd_adj[i] < 0.05),
            'asset_to_money_raw_p': round(rev_raw[i], 6),
            'asset_to_money_holm_p': round(rev_adj[i], 6),
            'asset_to_money_sig_5pct': bool(rev_adj[i] < 0.05),
        })
    return {'n':len(data),'first_month':months[0] if months else None,'last_month':months[-1] if months else None,'tests':tests}


def lead_lag(signal, price, rel, helpers):
    rows = []
    h = rel['horizon_m']
    for available_month in sorted(signal):
        obs = signal[available_month]['observation_month']
        x = signal[available_month]['x']
        start = available_month
        end = helpers.add_months(start, h)
        trailing_start = helpers.add_months(start, -h)
        if start not in price or end not in price or trailing_start not in price:
            continue
        rows.append((x, math.log(price[end]/price[start]), math.log(price[start]/price[trailing_start]), obs))
    if len(rows) < 3:
        return {'n':len(rows)}
    xs=[r[0] for r in rows]; fw=[r[1] for r in rows]; tr=[r[2] for r in rows]
    return {
        'n':len(rows),
        'first_signal_month':rows[0][3],
        'last_signal_month':rows[-1][3],
        'forward_12m_pearson':round(helpers.pearson(xs,fw),6),
        'trailing_12m_pearson':round(helpers.pearson(xs,tr),6),
        'forward_minus_trailing_abs':round(abs(helpers.pearson(xs,fw))-abs(helpers.pearson(xs,tr)),6),
    }


def run(as_of):
    spec = validate_spec()
    helpers = load_module(HELPERS_PATH, 'gmli_money_role_helpers')
    money = load_money(helpers)
    results=[]
    reverse_dominance_assets=0
    money_precedence_assets=0
    for rel in RELATIONS:
        price, _, meta = helpers.fetch_price(rel['asset'])
        returns = monthly_returns(price, helpers)
        key=f"{rel['channel']}_{rel['transform']}"
        signal=money[key]
        full=granger_pair(signal, returns)
        ex=granger_pair(signal, returns, exclude_pandemic=True, only_lag=3)
        full_money_any=any(t['money_to_asset_sig_5pct'] for t in full['tests'])
        full_reverse_any=any(t['asset_to_money_sig_5pct'] for t in full['tests'])
        ex_money_any=any(t['money_to_asset_sig_5pct'] for t in ex['tests'])
        ex_reverse_any=any(t['asset_to_money_sig_5pct'] for t in ex['tests'])
        if full_reverse_any and ex_reverse_any and not (full_money_any or ex_money_any):
            reverse_dominance_assets += 1
        if (full_money_any or ex_money_any) and not (full_reverse_any and ex_reverse_any):
            money_precedence_assets += 1
        results.append({
            **rel,
            'signal_key':key,
            'signal_stationarity':adf_info([signal[m]['x'] for m in sorted(signal)]),
            'monthly_direction_full':full,
            'monthly_direction_ex_pandemic_fixed_3m':ex,
            'lead_lag_12m':lead_lag(signal, price, rel, helpers),
            'price_source':meta,
        })
    majority = len(RELATIONS)//2 + 1
    if reverse_dominance_assets >= majority:
        money_role='MIXED'
        reason='Broad market-to-Money dominance appears across a majority of fixed promoted assets, so Money cannot be labelled purely leading despite promoted forward transmission.'
    else:
        money_role='LEADING'
        reason='Promoted forward transmission remains the primary evidence and the fixed directional diagnostics do not show robust market-to-Money dominance across a majority of fixed promoted assets.'
    return {
        'status':'INFORMATIONAL_SIGNAL_ROLE_TAXONOMY_COMPLETE',
        'study_version':spec['study_version'],
        'evidence_tier':'RESEARCH',
        'as_of':as_of,
        'production_implication':'NONE',
        'automatic_weight_change':0,
        'money_core_modified':False,
        'funding_v2_modified':False,
        'fiscal_v2_modified':False,
        'money_role':money_role,
        'money_role_reason':reason,
        'reverse_dominance_assets':reverse_dominance_assets,
        'money_precedence_assets':money_precedence_assets,
        'fixed_assets_tested':len(RELATIONS),
        'funding_role':'REACTIVE_CONFIRMATION',
        'funding_role_basis':'Reverse overlay research found robust SPY/QQQ -> Funding precedence, 0/6 reverse full-sample tests, persistence ex-pandemic, and attenuation after VIX control.',
        'fiscal_role':'MIXED',
        'fiscal_role_basis':'Fiscal has positive fixed 12M forward usefulness but weak/control-sensitive and regime-dependent predictive-precedence evidence, with some reverse SPY -> Fiscal evidence in the full sample.',
        'market_confirmation_role':'REACTIVE_CONFIRMATION',
        'market_confirmation_basis':'Preassigned by construction as contemporaneous/price confirmation.',
        'money_results':results,
        'guardrail':'Interpretation taxonomy only; no production score, weight, threshold, evidence tier or promoted relationship changed.',
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--as-of', default='2026-08-25')
    p.add_argument('--output', default='')
    args=p.parse_args()
    result=run(args.as_of)
    text=json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(text+'\n', encoding='utf-8')
    print(text)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
