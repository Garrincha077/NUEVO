#!/usr/bin/env python3
import argparse
import importlib.util
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / 'scripts' / 'test-reverse-overlay-mechanism.py'
ROBUST_PATH = ROOT / 'scripts' / 'run-reverse-overlay-mechanism.py'
SPEC_PATH = ROOT / 'research' / 'reverse-overlay-mechanism' / 'FOLLOWUP_SPEC.json'
FUNDING_PATH = ROOT / 'research' / 'funding-v2' / 'latest' / 'history.csv'
VERSION = 'GMLI_REVERSE_OVERLAY_MECHANISM_FOLLOWUP_V1'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validate_spec():
    s = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    assert s['study_version'] == VERSION
    assert s['status'] == 'FROZEN_BEFORE_FOLLOWUP_RUN'
    assert s['tests']['raw_funding_input_attribution']['funding_inputs'] == ['anfci','dfii10','term_premium','reserves_3m_pct']
    assert s['tests']['dbc_bidirectional_precedence']['lags_months'] == [1,3,6]
    assert s['tests']['post_2022_equity_to_funding']['start'] == '2022-01'
    assert all(v is False for v in s['no_search'].values())
    assert s['production_modified'] is False and s['automatic_weight_change'] == 0
    return s


def nested_common_driver(base, funding, spy_ret, vix_change, unrate):
    du = base.map_diff(unrate)
    specs = [
        ('base_only', []),
        ('base_plus_VIX', ['vix']),
        ('base_plus_UNRATE', ['unrate']),
        ('base_plus_VIX_plus_UNRATE', ['vix','unrate']),
    ]
    out = []
    for name, controls in specs:
        needed = [set(funding), set(spy_ret)]
        if 'vix' in controls: needed.append(set(vix_change))
        if 'unrate' in controls: needed.append(set(du))
        months = sorted(set.intersection(*needed))
        df = pd.DataFrame(index=months)
        df['y'] = [funding[m] for m in months]
        df['spy'] = [spy_ret[m] for m in months]
        if 'vix' in controls: df['vix'] = [vix_change[m] for m in months]
        if 'unrate' in controls: df['unrate'] = [du[m] for m in months]
        sources = ['y','spy'] + controls
        for src in sources:
            for lag in range(1,4):
                df[f'{src}_l{lag}'] = df[src].shift(lag)
        cols = [f'y_l{i}' for i in range(1,4)] + [f'spy_l{i}' for i in range(1,4)]
        for c in controls:
            cols += [f'{c}_l{i}' for i in range(1,4)]
        d = df[['y']+cols].dropna()
        X = sm.add_constant(d[cols], has_constant='add')
        fit = sm.OLS(d['y'], X).fit(cov_type='HAC', cov_kwds={'maxlags':3})
        names = list(X.columns)
        R = np.zeros((3, len(names)))
        for j, lag in enumerate(range(1,4)):
            R[j, names.index(f'spy_l{lag}')] = 1.0
        ft = fit.f_test(R)
        p = float(np.asarray(ft.pvalue).squeeze())
        out.append({
            'control_set': name,
            'n': len(d),
            'r_squared': round(float(fit.rsquared),6),
            'joint_spy_lags_p_value': round(p,6),
            'joint_spy_lags_significant_5pct': bool(p < 0.05),
            'spy_lag_coefficients': {f'spy_l{i}': round(float(fit.params[f"spy_l{i}"]),8) for i in range(1,4)},
        })
    return out


def run(as_of):
    s = validate_spec()
    base = load(BASE_PATH, 'gmli_reverse_base')
    robust = load(ROBUST_PATH, 'gmli_reverse_robust')
    base.fetch_unrate = robust.robust_unrate

    raw = pd.read_csv(FUNDING_PATH, dtype={'observation_month':str, 'available_date':str})
    for c in ['effective_score','anfci','dfii10','term_premium','reserves_3m_pct']:
        raw[c] = pd.to_numeric(raw[c], errors='coerce')
    funding_tf, funding_meta = base.stationary_transform(raw, 'effective_score')
    funding = base.series_dict(funding_tf)

    prices = {a: base.fetch_yahoo_monthly(a) for a in ['SPY','QQQ','DBC']}
    rets = {a: base.monthly_returns(p) for a,p in prices.items()}

    # 1) Fixed raw Funding-input attribution: SPY/QQQ -> each raw input, lag 3.
    input_rows = []
    input_transforms = {}
    for col in ['anfci','dfii10','term_premium','reserves_3m_pct']:
        tf, meta = base.stationary_transform(raw, col)
        input_transforms[col] = meta
        target = base.series_dict(tf)
        for asset in ['SPY','QQQ']:
            r = base.granger_one(target, rets[asset], 3)
            r.update({'asset':asset, 'funding_input':col, 'direction':'market_to_input'})
            input_rows.append(r)
    base.apply_holm(input_rows)

    # 2) DBC <-> Funding, fixed lags, full and pandemic-excluded.
    dbc = {}
    for label, exclude in [('full',False), ('exclude_pandemic',True)]:
        to_funding=[]; from_funding=[]
        for lag in [1,3,6]:
            a=base.granger_one(funding, rets['DBC'], lag, exclude)
            a.update({'sample':label,'direction':'DBC_to_Funding'})
            to_funding.append(a)
            b=base.granger_one(rets['DBC'], funding, lag, exclude)
            b.update({'sample':label,'direction':'Funding_to_DBC'})
            from_funding.append(b)
        base.apply_holm(to_funding); base.apply_holm(from_funding)
        dbc[label]={'DBC_to_Funding':to_funding,'Funding_to_DBC':from_funding}

    # 3) Post-2022 equity <-> Funding, fixed lag 3.
    post_to=[]; post_from=[]
    for asset in ['SPY','QQQ']:
        a=base.granger_one(funding, rets[asset], 3, start='2022-01')
        a.update({'asset':asset,'direction':'market_to_Funding','start':'2022-01'})
        post_to.append(a)
        b=base.granger_one(rets[asset], funding, 3, start='2022-01')
        b.update({'asset':asset,'direction':'Funding_to_market','start':'2022-01'})
        post_from.append(b)
    base.apply_holm(post_to); base.apply_holm(post_from)

    # 4) Nested common-driver blocks, fixed before this run.
    vix_change = base.monthly_log_changes(base.fetch_yahoo_monthly('^VIX'))
    unrate = robust.robust_unrate()
    nested = nested_common_driver(base, funding, rets['SPY'], vix_change, unrate)

    return {
        'status':'INFORMATIONAL_REVERSE_OVERLAY_FOLLOWUP_COMPLETE',
        'study_version':VERSION,
        'evidence_tier':'RESEARCH',
        'as_of':as_of.isoformat(),
        'production_implication':'NONE',
        'causal_claim_allowed':False,
        'production_modified':False,
        'funding_v2_modified':False,
        'fiscal_v2_modified':False,
        'decision_engine_modified':False,
        'automatic_weight_change':0,
        'funding_stationarity':funding_meta,
        'raw_funding_input_attribution':{'tests':input_rows,'transforms':input_transforms},
        'dbc_bidirectional_precedence':dbc,
        'post_2022_equity_funding_precedence':{'market_to_Funding':post_to,'Funding_to_market':post_from},
        'nested_common_driver_attribution':nested,
        'interpretation_guardrail':'This is a frozen follow-up attribution study generated by V1. Significance identifies predictive precedence, not structural causality or a production trading rule.',
        'spec':s,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--as-of',default=date.today().isoformat())
    p.add_argument('--output',required=True)
    a=p.parse_args()
    result=run(date.fromisoformat(a.as_of))
    text=json.dumps(result,indent=2)
    Path(a.output).write_text(text+'\n',encoding='utf-8')
    print(text)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
