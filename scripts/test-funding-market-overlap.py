#!/usr/bin/env python3
import argparse
import csv
import importlib.util
import io
import json
import math
from pathlib import Path

import numpy as np
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'research' / 'signal-role-taxonomy' / 'OVERLAP_SPEC.json'
FUNDING = ROOT / 'research' / 'funding-v2' / 'latest' / 'history.csv'
HELPERS_PATH = ROOT / 'scripts' / 'test-global-money-v2-transmission.py'
ASSETS = ['SPY','QQQ','GLD','DBC']


def load_module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def validate_spec():
    s=json.loads(SPEC.read_text(encoding='utf-8'))
    assert s['study_version']=='GMLI_FUNDING_MARKET_CONFIRMATION_OVERLAP_V1'
    assert s['status']=='FROZEN_BEFORE_EMPIRICAL_RUN'
    assert all(v is False for v in s['no_search'].values())
    assert s['production_modified'] is False and s['automatic_weight_change']==0
    return s


def load_funding(helpers):
    rows=list(csv.DictReader(io.StringIO(FUNDING.read_text(encoding='utf-8'))))
    out={}
    for r in rows:
        try:
            score=float(r['effective_score'])
        except (ValueError,KeyError):
            continue
        available=(r.get('available_date') or '')[:7]
        if not available:
            available=helpers.add_months(r['observation_month'],1)
        rubric=2 if score>60 else 0 if score<40 else 1
        out[available]={'score':score,'rubric':rubric,'observation_month':r['observation_month']}
    return out


def market_scores(prices):
    common=sorted(set.intersection(*[set(prices[a]) for a in ASSETS]))
    out={}
    for month in common:
        per=[]
        for a in ASSETS:
            months=sorted(m for m in prices[a] if m<=month)
            if len(months)<13: break
            vals=[prices[a][m] for m in months]
            last=vals[-1]
            ma10=sum(vals[-10:])/10
            r3=last/vals[-4]-1
            per.append(last>ma10 or r3>0)
        if len(per)!=4: continue
        positive=sum(per)
        score=2 if positive>=3 else 1 if positive==2 else 0
        out[month]={'score':score,'positive':positive}
    return out


def ranks(vals):
    order=sorted(range(len(vals)),key=lambda i: vals[i]); out=[0.0]*len(vals); i=0
    while i<len(order):
        j=i+1
        while j<len(order) and vals[order[j]]==vals[order[i]]: j+=1
        rank=(i+1+j)/2.0
        for k in range(i,j): out[order[k]]=rank
        i=j
    return out


def corr(x,y):
    if len(x)<3:return None
    mx=sum(x)/len(x); my=sum(y)/len(y)
    dx=[v-mx for v in x]; dy=[v-my for v in y]
    den=math.sqrt(sum(v*v for v in dx)*sum(v*v for v in dy))
    return None if den==0 else sum(a*b for a,b in zip(dx,dy))/den


def metric_pair(x,y):
    return {'pearson':round(corr(x,y),6),'spearman':round(corr(ranks(x),ranks(y)),6),'n':len(x)}


def hac_regression(rows):
    y=np.array([r['forward_spy_12m'] for r in rows],dtype=float)
    market=np.array([r['market_score'] for r in rows],dtype=float)
    funding=np.array([r['funding_score'] for r in rows],dtype=float)
    base=sm.OLS(y,sm.add_constant(market)).fit(cov_type='HAC',cov_kwds={'maxlags':12})
    full=sm.OLS(y,sm.add_constant(np.column_stack([market,funding]))).fit(cov_type='HAC',cov_kwds={'maxlags':12})
    return {
        'n':len(rows),
        'baseline_r_squared':round(float(base.rsquared),6),
        'full_r_squared':round(float(full.rsquared),6),
        'delta_r_squared':round(float(full.rsquared-base.rsquared),6),
        'funding_coef_per_score_point':round(float(full.params[2]),8),
        'funding_hac_p_value':round(float(full.pvalues[2]),6),
        'market_coef':round(float(full.params[1]),8),
        'market_hac_p_value':round(float(full.pvalues[1]),6),
        'hac_maxlags':12,
    }


def run(as_of):
    spec=validate_spec(); helpers=load_module(HELPERS_PATH,'gmli_overlap_helpers')
    funding=load_funding(helpers)
    prices={}; meta={}
    for a in ASSETS:
        prices[a],_,meta[a]=helpers.fetch_price(a)
    market=market_scores(prices)
    rows=[]
    for m in sorted(set(funding).intersection(market)):
        end=helpers.add_months(m,12)
        p0=prices['SPY'].get(m); p1=prices['SPY'].get(end)
        if p0 is None or p1 is None: continue
        rows.append({
            'month':m,
            'funding_score':funding[m]['score'],
            'funding_rubric':funding[m]['rubric'],
            'market_score':market[m]['score'],
            'market_positive':market[m]['positive'],
            'forward_spy_12m':math.log(p1/p0),
        })
    fr=[r['funding_score'] for r in rows]; frr=[r['funding_rubric'] for r in rows]; mr=[r['market_score'] for r in rows]
    contingency={str(f):{str(m):0 for m in [0,1,2]} for f in [0,1,2]}
    for r in rows: contingency[str(r['funding_rubric'])][str(r['market_score'])]+=1
    exact=sum(1 for r in rows if r['funding_rubric']==r['market_score'])/len(rows)
    result={
        'status':'INFORMATIONAL_FUNDING_MARKET_OVERLAP_COMPLETE',
        'study_version':spec['study_version'],
        'evidence_tier':'RESEARCH',
        'as_of':as_of,
        'production_implication':'NONE',
        'automatic_weight_change':0,
        'sample':{'n':len(rows),'first_month':rows[0]['month'],'last_month':rows[-1]['month']},
        'funding_raw_vs_market_score':metric_pair(fr,mr),
        'funding_rubric_vs_market_score':metric_pair(frr,mr),
        'exact_rubric_score_agreement_rate':round(exact,6),
        'contingency_funding_rows_market_cols':contingency,
        'forward_spy_12m_hac':hac_regression(rows),
        'price_sources':meta,
        'guardrail':'Overlap diagnostic only. No conviction weight or score changes are allowed from this result.'
    }
    return result


def main():
    p=argparse.ArgumentParser(); p.add_argument('--as-of',default='2026-08-25'); p.add_argument('--output',default='')
    args=p.parse_args(); r=run(args.as_of); text=json.dumps(r,indent=2)
    if args.output: Path(args.output).write_text(text+'\n',encoding='utf-8')
    print(text); return 0

if __name__=='__main__': raise SystemExit(main())
