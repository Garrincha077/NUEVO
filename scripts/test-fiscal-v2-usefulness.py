#!/usr/bin/env python3
import argparse
import csv
import importlib.util
import json
import math
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_RUNNER = ROOT / 'scripts' / 'build-fiscal-v2.py'
TRANSFER_HELPERS = ROOT / 'scripts' / 'test-global-money-v2-transmission.py'
GATE_CONTRACT = ROOT / 'research' / 'fiscal-v2-usefulness-gate.json'
VERSION = 'GMLI_FISCAL_V2_USEFULNESS_GATE_V1'
TRAIN_END = '2022-12'
OOS_START = '2023-01'

PRIMARY = [
    {'id': 'SPY_FISCAL_V2_12M', 'asset': 'SPY', 'horizon_m': 12, 'primary': True},
]
SECONDARY = [
    {'id': 'QQQ_FISCAL_V2_12M', 'asset': 'QQQ', 'horizon_m': 12, 'primary': False},
    {'id': 'DBC_FISCAL_V2_12M', 'asset': 'DBC', 'horizon_m': 12, 'primary': False},
]
RELATIONS = PRIMARY + SECONDARY


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_contract():
    contract = json.loads(GATE_CONTRACT.read_text(encoding='utf-8'))
    assert contract['gate_version'] == VERSION
    assert contract['status'] == 'FROZEN_BEFORE_EMPIRICAL_RUN'
    assert contract['candidate_version'] == 'GMLI_FISCAL_V2_CANDIDATE_1'
    assert [x['id'] for x in contract['primary_fixed_relations']] == [x['id'] for x in PRIMARY]
    assert [x['id'] for x in contract['secondary_diagnostics_not_in_gate']] == [x['id'] for x in SECONDARY]
    assert all(v is False for v in contract['no_search'].values())
    assert contract['production_modified'] is False
    assert contract['money_core_modified'] is False
    assert contract['funding_v2_modified'] is False
    return contract


def observations(fiscal_history, price, relation, helpers):
    rows = []
    h = relation['horizon_m']
    for f in fiscal_history:
        month = f['observation_month']
        score = f['score']
        if score is None or not math.isfinite(score):
            continue
        start = helpers.add_months(month, 2)
        end = helpers.add_months(start, h)
        p0 = price.get(start)
        p1 = price.get(end)
        if p0 is None or p1 is None or p0 <= 0 or p1 <= 0:
            continue
        rows.append({
            'relation_id': relation['id'],
            'signal_month': month,
            'signal_available_date': f['available_date'],
            'price_start_month': start,
            'price_end_month': end,
            'fiscal_score': score,
            'forward_log_return': math.log(p1 / p0),
        })
    return rows


def metrics(rows, helpers):
    xs = [x['fiscal_score'] for x in rows]
    ys = [x['forward_log_return'] for x in rows]
    return {
        'n': len(rows),
        'first_signal_month': rows[0]['signal_month'] if rows else None,
        'last_signal_month': rows[-1]['signal_month'] if rows else None,
        'pearson_r': None if len(rows) < 3 else round(helpers.pearson(xs, ys), 6),
        'spearman_rho': None if len(rows) < 3 else round(helpers.spearman(xs, ys), 6),
    }


def test_relation(fiscal_history, price, relation, helpers):
    rows = observations(fiscal_history, price, relation, helpers)
    train = [x for x in rows if x['signal_month'] <= TRAIN_END]
    oos = [x for x in rows if x['signal_month'] >= OOS_START]
    tm = metrics(train, helpers)
    om = metrics(oos, helpers)
    passed = (
        tm['pearson_r'] is not None and tm['pearson_r'] > 0 and
        om['pearson_r'] is not None and om['pearson_r'] > 0 and
        om['spearman_rho'] is not None and om['spearman_rho'] > 0
    )
    return {
        **relation,
        'effective_lag_m': 2,
        'train': tm,
        'oos': om,
        'direction_pass': passed,
        'observations': rows,
    }


def run(as_of, build_full=False, output_dir='research/fiscal-v2/usefulness-latest'):
    contract = validate_contract()
    candidate_module = load_module(CANDIDATE_RUNNER, 'gmli_fiscal_v2_candidate1')
    helpers = load_module(TRANSFER_HELPERS, 'gmli_transfer_helpers')
    candidate = candidate_module.build(as_of)
    if candidate['status'] != 'PASS_FIXED_CONSTRUCTION_SANITY':
        raise RuntimeError('Fiscal V2 Candidate 1 fixed construction sanity is not PASS')

    assets = sorted(set(x['asset'] for x in RELATIONS))
    prices = {}
    price_meta = {}
    for asset in assets:
        prices[asset], _, price_meta[asset] = helpers.fetch_price(asset)

    tested = [test_relation(candidate['history'], prices[x['asset']], x, helpers) for x in RELATIONS]
    primary = [x for x in tested if x['primary']]
    primary_pass = all(x['direction_pass'] for x in primary)
    status = 'PASS_NARROW_FISCAL_USEFULNESS' if primary_pass else 'FAIL_NARROW_FISCAL_USEFULNESS'

    result = {
        'status': status,
        'gate_version': VERSION,
        'candidate_version': candidate['candidate_version'],
        'evidence_tier': 'RESEARCH',
        'as_of': as_of.isoformat(),
        'production_modified': False,
        'money_core_modified': False,
        'funding_v2_modified': False,
        'asset_search': False,
        'horizon_search': False,
        'lag_search': False,
        'parameter_search': False,
        'threshold_search': False,
        'subperiod_search': False,
        'fdr_claim': False,
        'protocol': {
            'train_signal_months': f'candidate start..{TRAIN_END}',
            'oos_signal_months': f'{OOS_START}+',
            'signal_availability': 'observation t available at month-end t+1',
            'return_start': 'exact-ticker adjusted close in t+2',
            'return': '12M forward log total return from Yahoo monthly adjusted close',
            'primary_gate': 'SPY 12M requires positive train Pearson, positive OOS Pearson and positive OOS Spearman',
            'secondary_diagnostics': 'QQQ and DBC 12M are report-only and cannot change PASS/FAIL',
        },
        'candidate_latest_eligible': candidate['latest_eligible'],
        'candidate_construction_status': candidate['status'],
        'candidate_source_provenance': candidate['sources'],
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
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        fields = [
            'relation_id', 'signal_month', 'signal_available_date', 'price_start_month',
            'price_end_month', 'fiscal_score', 'forward_log_return',
        ]
        with (out / 'observations.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for relation in tested:
                writer.writerows(relation['observations'])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', default=date.today().isoformat())
    parser.add_argument('--build-full', action='store_true')
    parser.add_argument('--output-dir', default='research/fiscal-v2/usefulness-latest')
    args = parser.parse_args()
    result = run(date.fromisoformat(args.as_of), build_full=args.build_full, output_dir=args.output_dir)
    print(json.dumps(result, indent=2))
    return 0 if result['status'].startswith('PASS_') else 2


if __name__ == '__main__':
    raise SystemExit(main())
