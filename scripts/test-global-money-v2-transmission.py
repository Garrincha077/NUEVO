#!/usr/bin/env python3
"""Fixed GMLI Global Money V2 transmission-transfer gate.

This intentionally tests ONLY the six already-promoted relationships. There is
no asset, horizon, lag, mode or threshold search. It is a directional transfer
gate for the new official-source Money V2 candidate, not a fresh model search.

Frozen protocol reused here:
- signal observation train: 2015-01..2022-12; OOS: 2023-01+
- mandatory publication lag: 1 month
- forward log total return from exact-ticker monthly adjusted prices
- accel3 = 3-month change in the relevant broad-money YoY series
- level = relevant broad-money YoY level

A relation transfers direction only when train Pearson, OOS Pearson and OOS
Spearman are all positive. Correlation magnitudes and sample sizes are reported,
but no new magnitude threshold is invented. No FDR claim is made here because
this is a fixed six-relation family, not the historical 56/9-hypothesis family.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import pathlib
import statistics
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
MONEY_CSV = ROOT / 'research' / 'global-money-v2' / 'latest' / 'global_money_v2.csv'
OUT_ROOT = ROOT / 'research' / 'global-money-v2' / 'transfer' / 'latest'
AUDIT_PATH = ROOT / 'audit' / 'global-money-v2-transmission-transfer.json'
UA = 'GMLI-Money-V2-Transfer/1.0 fixed-six-no-search'
TRAIN_END = '2022-12'
OOS_START = '2023-01'

RELATIONS = [
    {'id':'SPY_USD_ACCEL3_12M','asset':'SPY','channel':'usd','mode':'accel3','horizon_m':12,'legacy':'SPY 12M accel3'},
    {'id':'QQQ_USD_ACCEL3_12M','asset':'QQQ','channel':'usd','mode':'accel3','horizon_m':12,'legacy':'QQQ 12M accel3'},
    {'id':'GLD_FXN_ACCEL3_12M','asset':'GLD','channel':'fxn','mode':'accel3','horizon_m':12,'legacy':'GLD FX-neutral 12M'},
    {'id':'DBC_USD_LEVEL_6M','asset':'DBC','channel':'usd','mode':'level','horizon_m':6,'legacy':'DBC USD 6M'},
    {'id':'DBC_USD_LEVEL_12M','asset':'DBC','channel':'usd','mode':'level','horizon_m':12,'legacy':'DBC USD 12M'},
    {'id':'DBC_FXN_LEVEL_6M','asset':'DBC','channel':'fxn','mode':'level','horizon_m':6,'legacy':'DBC FX-neutral 6M'},
]

# Historical exact-ticker reference is descriptive only; it is never used as a
# tuning target. Values below are the published v1.2 rows where available.
LEGACY_REFERENCE = {
    'SPY_USD_ACCEL3_12M': {'train_pearson':0.435414, 'oos_pearson':0.386020, 'oos_spearman':0.356174},
    'QQQ_USD_ACCEL3_12M': {'train_pearson':0.387003, 'oos_pearson':0.559583, 'oos_spearman':0.552419},
    'GLD_FXN_ACCEL3_12M': {'train_pearson':0.102476, 'oos_pearson':0.675166, 'oos_spearman':0.649597},
    'DBC_USD_LEVEL_6M': {'train_pearson':0.561634, 'oos_pearson':0.553945, 'oos_spearman':0.487516},
    'DBC_USD_LEVEL_12M': {'train_pearson':0.622280, 'oos_pearson':0.585314, 'oos_spearman':0.585887},
    'DBC_FXN_LEVEL_6M': {'historical_direction':'positive train and OOS; marginal FDR in v1.2, retained direction in v1.8b'},
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def add_months(month, n):
    y, m = map(int, month.split('-'))
    total = y * 12 + (m - 1) + n
    yy, mm0 = divmod(total, 12)
    return f'{yy:04d}-{mm0+1:02d}'


def fetch_price(asset):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{asset}?range=max&interval=1mo&events=history&includeAdjustedClose=true'
    req = urllib.request.Request(url, headers={'User-Agent':UA, 'Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=45) as response:
        raw = response.read()
        final_url = response.geturl()
    data = json.loads(raw.decode('utf-8'))
    result = ((data.get('chart') or {}).get('result') or [None])[0]
    if not result:
        raise ValueError(f'Yahoo returned no chart result for {asset}')
    ts = result.get('timestamp') or []
    adj_blocks = ((result.get('indicators') or {}).get('adjclose') or [])
    if not adj_blocks:
        raise ValueError(f'Yahoo adjusted close missing for {asset}')
    vals = adj_blocks[0].get('adjclose') or []
    if len(ts) != len(vals):
        raise ValueError(f'Yahoo timestamp/adjusted length mismatch for {asset}')
    out = {}
    for t, v in zip(ts, vals):
        if not isinstance(v, (int,float)) or not math.isfinite(v) or v <= 0:
            continue
        month = datetime.fromtimestamp(int(t), tz=timezone.utc).strftime('%Y-%m')
        out[month] = float(v)
    if len(out) < 100:
        raise ValueError(f'Implausibly short adjusted-price history for {asset}: {len(out)} months')
    return out, raw, {'url':url,'final_url':final_url,'sha256':sha256(raw),'bytes':len(raw),'months':len(out),'first_month':min(out),'last_month':max(out)}


def load_money():
    if not MONEY_CSV.exists():
        raise FileNotFoundError(f'Global Money V2 CSV missing: {MONEY_CSV}')
    raw = MONEY_CSV.read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
    by_month = {}
    for row in rows:
        try:
            usd = float(row['gbm_usd_yoy_pct'])
            fxn = float(row['gbm_fxn_yoy_pct'])
        except (KeyError, ValueError):
            continue
        by_month[row['month']] = {'usd':usd,'fxn':fxn}
    if not by_month or min(by_month) > '2015-01':
        raise ValueError(f'Global Money V2 does not preserve 2015 signal start; first={min(by_month) if by_month else None}')
    return by_month, raw


def pearson(xs, ys):
    n = len(xs)
    if n != len(ys) or n < 3:
        return None
    mx = sum(xs)/n; my = sum(ys)/n
    dx = [x-mx for x in xs]; dy = [y-my for y in ys]
    den = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    if den == 0:
        return None
    return sum(x*y for x,y in zip(dx,dy))/den


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0]*len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i,j):
            out[order[k]] = rank
        i = j
    return out


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    return pearson(ranks(xs), ranks(ys))


def predictor(money, month, channel, mode):
    if month not in money:
        return None
    level = money[month][channel]
    if mode == 'level':
        return level
    if mode == 'accel3':
        prior = add_months(month, -3)
        if prior not in money:
            return None
        return level - money[prior][channel]
    raise ValueError(f'Unknown mode {mode}')


def observations(money, price, relation):
    rows = []
    h = relation['horizon_m']
    for month in sorted(money):
        x = predictor(money, month, relation['channel'], relation['mode'])
        if x is None or not math.isfinite(x):
            continue
        # Money observation t becomes investable only after the mandatory 1M lag.
        start = add_months(month, 1)
        end = add_months(start, h)
        p0 = price.get(start); p1 = price.get(end)
        if p0 is None or p1 is None or p0 <= 0 or p1 <= 0:
            continue
        y = math.log(p1/p0)
        rows.append({'signal_month':month,'price_start_month':start,'price_end_month':end,'x':x,'forward_log_return':y})
    return rows


def metrics(rows):
    xs = [r['x'] for r in rows]; ys = [r['forward_log_return'] for r in rows]
    return {
        'n':len(rows),
        'first_signal_month':rows[0]['signal_month'] if rows else None,
        'last_signal_month':rows[-1]['signal_month'] if rows else None,
        'pearson_r':None if len(rows)<3 else round(pearson(xs,ys),6),
        'spearman_rho':None if len(rows)<3 else round(spearman(xs,ys),6),
    }


def test_relation(money, price, relation):
    rows = observations(money, price, relation)
    train = [r for r in rows if '2015-01' <= r['signal_month'] <= TRAIN_END]
    oos = [r for r in rows if r['signal_month'] >= OOS_START]
    tm = metrics(train); om = metrics(oos)
    direction_pass = (
        tm['pearson_r'] is not None and tm['pearson_r'] > 0 and
        om['pearson_r'] is not None and om['pearson_r'] > 0 and
        om['spearman_rho'] is not None and om['spearman_rho'] > 0
    )
    return {
        **relation,
        'effective_lag_m':1,
        'train':tm,
        'oos':om,
        'direction_transfer_pass':direction_pass,
        'legacy_reference':LEGACY_REFERENCE.get(relation['id']),
    }


def run(build_full=False):
    money, money_raw = load_money()
    prices = {}; price_meta = {}; price_raw = {}
    for asset in sorted(set(r['asset'] for r in RELATIONS)):
        prices[asset], price_raw[asset], price_meta[asset] = fetch_price(asset)

    results = [test_relation(money, prices[r['asset']], r) for r in RELATIONS]
    passed = sum(1 for r in results if r['direction_transfer_pass'])
    status = 'PASS_FIXED_TRANSMISSION_DIRECTION_TRANSFER' if passed == len(results) else 'FAIL_FIXED_TRANSMISSION_DIRECTION_TRANSFER'
    manifest = {
        'status':status,
        'candidate_version':'GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL',
        'evidence_tier':'RESEARCH_PROMOTION_CANDIDATE',
        'built_at':now_iso(),
        'core_modified':False,
        'parameter_search':False,
        'lag_search':False,
        'horizon_search':False,
        'asset_search':False,
        'fdr_claim':False,
        'protocol':{
            'relations':len(RELATIONS),
            'train_signal_months':'2015-01..2022-12',
            'oos_signal_months':'2023-01+',
            'publication_lag_months':1,
            'return':'forward log return from Yahoo monthly adjusted close',
            'level':'relevant Global Money V2 YoY level',
            'accel3':'3-month change in relevant Global Money V2 YoY level',
            'gate':'positive train Pearson AND positive OOS Pearson AND positive OOS Spearman for all six preselected relations',
        },
        'money_source':{
            'file':str(MONEY_CSV.relative_to(ROOT)),
            'sha256':sha256(money_raw),
            'first_month':min(money),
            'last_month':max(money),
            'months':len(money),
        },
        'price_sources':price_meta,
        'passed_relations':passed,
        'total_relations':len(results),
        'results':results,
        'promotion_allowed':False,
        'next_gate':'PROMOTION_REPORT_AND_PRODUCTION_INTEGRATION_REVIEW' if passed == len(results) else 'INVESTIGATE_DIRECTION_TRANSFER_FAILURE_WITHOUT_RETUNING',
        'note':'Direction transfer is deliberately narrower than historical FDR validation. Historical v1.8b audit status is unchanged.',
    }

    if build_full:
        OUT_ROOT.mkdir(parents=True, exist_ok=True)
        raw_root = OUT_ROOT / 'raw'; raw_root.mkdir(exist_ok=True)
        for asset, raw in price_raw.items():
            (raw_root / f'{asset}-yahoo-monthly.json').write_bytes(raw)
        (OUT_ROOT / 'transfer.lock.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        AUDIT_PATH.parent.mkdir(exist_ok=True)
        AUDIT_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--validate-only', action='store_true')
    group.add_argument('--build-full', action='store_true')
    args = parser.parse_args()
    try:
        result = run(build_full=args.build_full)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'].startswith('PASS_') else 2
    except Exception as exc:
        print(json.dumps({'status':'FAIL','core_modified':False,'parameter_search':False,'error':str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
