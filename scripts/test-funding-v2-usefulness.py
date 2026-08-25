#!/usr/bin/env python3
import argparse
import csv
import importlib.util
import json
import math
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_RUNNER = ROOT / 'scripts' / 'build-funding-v2-candidate2.py'
TRANSFER_RUNNER = ROOT / 'scripts' / 'test-global-money-v2-transmission.py'
GATE_CONTRACT = ROOT / 'research' / 'funding-v2-usefulness-gate.json'
VERSION = 'GMLI_FUNDING_V2_USEFULNESS_GATE_V1'
TRAIN_END = '2022-12'
OOS_START = '2023-01'

PRIMARY = [
    {'id': 'DBC_FUNDING_V2_6M', 'asset': 'DBC', 'horizon_m': 6, 'primary': True},
    {'id': 'DBC_FUNDING_V2_12M', 'asset': 'DBC', 'horizon_m': 12, 'primary': True},
]
SECONDARY = [
    {'id': 'SPY_FUNDING_V2_12M', 'asset': 'SPY', 'horizon_m': 12, 'primary': False},
    {'id': 'QQQ_FUNDING_V2_12M', 'asset': 'QQQ', 'horizon_m': 12, 'primary': False},
    {'id': 'GLD_FUNDING_V2_12M', 'asset': 'GLD', 'horizon_m': 12, 'primary': False},
]
RELATIONS = PRIMARY + SECONDARY


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_contract():
    c = json.loads(GATE_CONTRACT.read_text(encoding='utf-8'))
    assert c['gate_version'] == VERSION
    assert c['status'] == 'FROZEN_BEFORE_EMPIRICAL_RUN'
    assert c['candidate_version'] == 'GMLI_FUNDING_V2_CANDIDATE_2'
    assert c['publication_lag_months'] == 1
    assert [x['id'] for x in c['primary_fixed_relations']] == [x['id'] for x in PRIMARY]
    assert [x['id'] for x in c['secondary_diagnostics_not_in_gate']] == [x['id'] for x in SECONDARY]
    assert all(v is False for v in c['no_search'].values())
    return c


def observations(funding_history, price, relation, transfer):
    rows = []
    h = relation['horizon_m']
    for f in funding_history:
        month = f['observation_month']
        if month < '2015-01':
            continue
        x = f['effective_score']
        if x is None or not math.isfinite(x):
            continue
        start = transfer.add_months(month, 1)
        end = transfer.add_months(start, h)
        p0 = price.get(start)
        p1 = price.get(end)
        if p0 is None or p1 is None or p0 <= 0 or p1 <= 0:
            continue
        rows.append({
            'relation_id': relation['id'],
            'signal_month': month,
            'price_start_month': start,
            'price_end_month': end,
            'funding_score': x,
            'forward_log_return': math.log(p1 / p0),
        })
    return rows


def metrics(rows, transfer):
    xs = [x['funding_score'] for x in rows]
    ys = [x['forward_log_return'] for x in rows]
    return {
        'n': len(rows),
        'first_signal_month': rows[0]['signal_month'] if rows else None,
        'last_signal_month': rows[-1]['signal_month'] if rows else None,
        'pearson_r': None if len(rows) < 3 else round(transfer.pearson(xs, ys), 6),
        'spearman_rho': None if len(rows) < 3 else round(transfer.spearman(xs, ys), 6),
    }


def test_relation(funding_history, price, relation, transfer):
    rows = observations(funding_history, price, relation, transfer)
    train = [x for x in rows if '2015-01' <= x['signal_month'] <= TRAIN_END]
    oos = [x for x in rows if x['signal_month'] >= OOS_START]
    tm = metrics(train, transfer)
    om = metrics(oos, transfer)
    passed = (
        tm['pearson_r'] is not None and tm['pearson_r'] > 0 and
        om['pearson_r'] is not None and om['pearson_r'] > 0 and
        om['spearman_rho'] is not None and om['spearman_rho'] > 0
    )
    return {
        **relation,
        'train': tm,
        'oos': om,
        'direction_pass': passed,
        'observations': rows,
    }


def run(as_of, build_full=False, output_dir='research/funding-v2/usefulness-latest'):
    contract = validate_contract()
    candidate = load_module(CANDIDATE_RUNNER, 'gmli_funding_v2_candidate2')
    transfer = load_module(TRANSFER_RUNNER, 'gmli_money_v2_transfer_helpers')
    funding = candidate.build(as_of)
    if not funding['directional_gate_pass']:
        raise RuntimeError('Candidate 2 fixed directional gate is not PASS')

    assets = sorted(set(x['asset'] for x in RELATIONS))
    prices = {}
    price_meta = {}
    for asset in assets:
        prices[asset], _, price_meta[asset] = transfer.fetch_price(asset)

    tested = [test_relation(funding['history'], prices[x['asset']], x, transfer) for x in RELATIONS]
    primary = [x for x in tested if x['primary']]
    primary_pass = all(x['direction_pass'] for x in primary)
    status = 'PASS_NARROW_FUNDING_USEFULNESS' if primary_pass else 'FAIL_NARROW_FUNDING_USEFULNESS'

    manifest = {
        'status': status,
        'gate_version': VERSION,
        'candidate_version': funding['candidate_version'],
        'evidence_tier': 'RESEARCH',
        'as_of': as_of.isoformat(),
        'production_modified': False,
        'money_core_modified': False,
        'asset_search': False,
        'horizon_search': False,
        'lag_search': False,
        'parameter_search': False,
        'threshold_search': False,
        'fdr_claim': False,
        'protocol': {
            'train_signal_months': '2015-01..2022-12',
            'oos_signal_months': '2023-01+',
            'publication_lag_months': 1,
            'return': 'forward log total return from exact-ticker Yahoo monthly adjusted close',
            'primary_gate': 'Both fixed DBC 6M and DBC 12M require positive train Pearson, positive OOS Pearson and positive OOS Spearman',
            'secondary_diagnostics': 'SPY/QQQ/GLD 12M are reported only and cannot change PASS/FAIL',
        },
        'funding_latest_eligible': funding['latest_eligible'],
        'funding_source_provenance': funding['sources'],
        'price_sources': price_meta,
        'primary_passed': sum(1 for x in primary if x['direction_pass']),
        'primary_total': len(primary),
        'promotion_allowed': False,
        'next_gate': 'PRODUCTION_READINESS_REVIEW' if primary_pass else 'KEEP_RESEARCH_DO_NOT_RETUNE',
        'results': [{k: v for k, v in x.items() if k != 'observations'} for x in tested],
        'contract': contract,
    }

    if build_full:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / 'result.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        with (out / 'observations.csv').open('w', newline='', encoding='utf-8') as f:
            fields = ['relation_id', 'signal_month', 'price_start_month', 'price_end_month', 'funding_score', 'forward_log_return']
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for relation in tested:
                writer.writerows(relation['observations'])
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', default=date.today().isoformat())
    parser.add_argument('--build-full', action='store_true')
    parser.add_argument('--output-dir', default='research/funding-v2/usefulness-latest')
    args = parser.parse_args()
    result = run(date.fromisoformat(args.as_of), build_full=args.build_full, output_dir=args.output_dir)
    print(json.dumps(result, indent=2))
    return 0 if result['status'].startswith('PASS_') else 2


if __name__ == '__main__':
    raise SystemExit(main())
