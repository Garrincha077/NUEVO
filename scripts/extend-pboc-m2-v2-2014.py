#!/usr/bin/env python3
"""Extend PBOC_OFFICIAL_M2_V2 through 2014 using official monthly PBoC reports.

2014 is a rounded seed year only, used to make 2015 China YoY computable.
2015+ remains the precision PBoC Money Supply HTML history. This script never
reconstructs the dead 2014 HTML target and never modifies lib/state.js.
"""
import argparse
import csv
import importlib.util
import io
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / 'scripts' / 'build-pboc-m2-official-v2.py'
NOWCAST_PATH = ROOT / 'scripts' / 'refresh-money-nowcast.py'
CONTRACT_PATH = ROOT / 'research' / 'china-m2-official-v2-contract.json'
OUT_ROOT = ROOT / 'research' / 'china-m2-official-v2' / 'latest'
AUDIT_PATH = ROOT / 'audit' / 'china-m2-official-v2.json'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = load_module('pboc_v2_base', BASE_PATH)
nowcast = load_module('pboc_nowcast_parser', NOWCAST_PATH)


def load_contract():
    data = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    if data.get('start_month') != '2014-01':
        raise ValueError('2014 extension requires contract start_month=2014-01')
    return data


def parse_month_level(clean, month):
    patterns = [
        rf'{month}月末[，,\s]*[^。]{{0,280}}?广义货币\s*\(?M2\)?\s*余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元',
        rf'{month}月末[，,\s]*[^。]{{0,280}}?M2[^。]{{0,120}}?余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元',
        r'广义货币\s*\(?M2\)?\s*余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元',
    ]
    for pattern in patterns:
        m = re.search(pattern, clean, flags=re.I)
        if m:
            level = float(m.group(1))
            if not (50 <= level <= 300):
                raise ValueError(f'2014-{month:02d} M2 level sanity failure: {level} tn CNY')
            return level
    raise ValueError(f'No M2 balance sentence for 2014-{month:02d}')


def fetch_month_report(month):
    year = 2014
    search_url = nowcast.pbc_search_url(year, month)
    search_raw, search_meta = base.fetch_bytes(search_url, timeout=45)
    candidates = nowcast.central_pbc_urls(base.decode_bytes(search_raw))
    if not candidates:
        raise ValueError(f'No central PBoC search candidates for 2014-{month:02d}')

    errors = []
    for url in candidates[:15]:
        try:
            article_raw, article_meta = base.fetch_bytes(url, timeout=40)
            clean = nowcast.strip_html(base.decode_bytes(article_raw)).replace('（', '(').replace('）', ')')
            if '2014' not in clean or '金融统计' not in clean:
                raise ValueError('not a 2014 financial-statistics article')
            level_trn = parse_month_level(clean, month)
            return {
                'month': f'2014-{month:02d}',
                'level_trn_cny': level_trn,
                'm2_100m': round(level_trn * 10000.0, 2),
                'search_url': search_url,
                'article_url': url,
                'search_raw': search_raw,
                'article_raw': article_raw,
                'search_sha256': base.sha256_bytes(search_raw),
                'article_sha256': base.sha256_bytes(article_raw),
                'search_http_status': search_meta.get('http_status'),
                'article_http_status': article_meta.get('http_status'),
            }
        except Exception as exc:
            errors.append(f'{url}: {str(exc)[:160]}')
    raise ValueError(f'No official 2014-{month:02d} PBoC report passed: ' + ' | '.join(errors[:5]))


def fetch_2014_reports(contract):
    records = [fetch_month_report(month) for month in range(1, 13)]
    values = {r['month']: r['m2_100m'] for r in records}
    expected = [f'2014-{m:02d}' for m in range(1, 13)]
    if sorted(values) != expected:
        raise ValueError(f'2014 monthly report seed is incomplete: {sorted(values)}')

    ordered = [values[m] for m in expected]
    for i in range(1, len(ordered)):
        ratio = ordered[i] / ordered[i - 1]
        if not (0.90 <= ratio <= 1.10):
            raise ValueError(f'2014 monthly-report seed continuity failure at {expected[i]}: ratio={ratio:.4f}')

    seed = contract.get('seed_validation') or {}
    check_month = seed.get('month')
    expected_trn = seed.get('reported_level_trn_cny')
    if check_month and expected_trn is not None:
        actual = values.get(check_month)
        target = float(expected_trn) * 10000.0
        if actual is None or abs(actual - target) > 0.01:
            raise ValueError(f'2014 seed anchor mismatch at {check_month}: actual={actual}, expected={target}')

    return records, values


def validate(contract):
    records, values = fetch_2014_reports(contract)
    return {
        'status': 'PASS_2014_OFFICIAL_MONTHLY_REPORT_SEED',
        'candidate_version': contract['version'],
        'core_modified': False,
        'legacy_exact_rerun': False,
        'source_contract': 'PBOC_OFFICIAL_MONTHLY_REPORT_SEED_2014',
        'year': 2014,
        'months': 12,
        'first_month': '2014-01',
        'last_month': '2014-12',
        'may_2014_m2_100m': values['2014-05'],
        'precision_note': '2014 balances are rounded to 0.01 trillion CNY in monthly reports; 2015+ remains precision HTML history.',
        'article_urls': [r['article_url'] for r in records],
        'next_gate': 'REBUILD_CONTINUOUS_PBOC_V2_2014_CURRENT',
    }


def build(contract):
    base_contract = dict(contract)
    base_contract['start_month'] = '2015-01'
    base.build_full(base_contract)
    records, seed_values = fetch_2014_reports(contract)

    csv_path = OUT_ROOT / 'china_m2_100m.csv'
    existing = list(csv.DictReader(io.StringIO(csv_path.read_text(encoding='utf-8'))))
    values = {row['month']: float(row['m2_100m']) for row in existing}
    values.update(seed_values)
    months = sorted(values)
    if months[0] != '2014-01':
        raise ValueError(f'Unexpected extended start month {months[0]}')

    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    provenance_path = OUT_ROOT / 'provenance.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    raw_root = OUT_ROOT / 'raw'
    seed_manifest = []
    for record in records:
        month = record['month']
        search_name = f'{month}-search.html'
        article_name = f'{month}-financial-statistics.html'
        (raw_root / search_name).write_bytes(record['search_raw'])
        (raw_root / article_name).write_bytes(record['article_raw'])
        provenance[month] = {
            'source_type': 'PBOC_OFFICIAL_MONTHLY_FINANCIAL_STATISTICS_REPORT_SEED',
            'source_url': record['article_url'],
            'raw_file': f'raw/{article_name}',
            'raw_sha256': record['article_sha256'],
            'search_url': record['search_url'],
            'search_raw_file': f'raw/{search_name}',
            'search_sha256': record['search_sha256'],
            'retrieved_at': retrieved_at,
            'unit': 'RMB 100 million',
            'source_precision': '0.01 trillion CNY (100 RMB 100-million units)',
            'role': 'SEED_YEAR_ONLY',
        }
        seed_manifest.append({
            'month': month,
            'm2_100m': record['m2_100m'],
            'article_url': record['article_url'],
            'article_sha256': record['article_sha256'],
            'search_url': record['search_url'],
            'search_sha256': record['search_sha256'],
        })
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    rows = []
    for month in months:
        prior = f'{int(month[:4])-1:04d}-{month[5:7]}'
        yoy = (values[month] / values[prior] - 1) * 100 if prior in values else None
        p = provenance[month]
        rows.append({
            'month': month,
            'm2_100m': round(values[month], 2),
            'derived_yoy_pct': None if yoy is None else round(yoy, 6),
            'source_type': p['source_type'],
            'source_url': p['source_url'],
            'raw_sha256': p['raw_sha256'],
        })
    with csv_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['month','m2_100m','derived_yoy_pct','source_type','source_url','raw_sha256'])
        writer.writeheader()
        writer.writerows(rows)

    manifest_path = OUT_ROOT / 'manifest.lock.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.update({
        'status': 'PASS_CONTINUOUS_OFFICIAL_V2_SOURCE',
        'built_at': retrieved_at,
        'start_month': '2014-01',
        'months': len(months),
        'missing_months': [],
        'historical_2014_extension': {
            'status': 'PASS_OFFICIAL_MONTHLY_REPORT_SEED',
            'months': 12,
            'role': 'SEED_YEAR_ONLY',
            'precision': '0.01 trillion CNY per monthly Financial Statistics Report',
            'may_2014_m2_100m': seed_values['2014-05'],
            'sources': seed_manifest,
        },
        'promotion_allowed': False,
        'next_gate': 'REBUILD_GLOBAL_MONEY_V2_WITH_2015_SIGNAL_START_THEN_FIXED_TRANSMISSION_TRANSFER_TEST',
        'note': 'Official PBoC V2 starts 2014-01. 2014 is a rounded official-report seed year; 2015+ is precision Money Supply HTML history. No dead historical source is reconstructed.'
    })
    manifest['years'] = sorted(
        [y for y in manifest.get('years', []) if y.get('year') != 2014] + [{
            'year': 2014,
            'months': 12,
            'first_month': '2014-01',
            'last_month': '2014-12',
            'source_type': 'PBOC_OFFICIAL_MONTHLY_FINANCIAL_STATISTICS_REPORT_SEED',
            'precision': '0.01 trillion CNY',
        }], key=lambda x: x['year'])
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    AUDIT_PATH.parent.mkdir(exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--validate-only', action='store_true')
    group.add_argument('--build-full', action='store_true')
    args = parser.parse_args()
    contract = load_contract()
    try:
        result = validate(contract) if args.validate_only else build(contract)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            'status': 'FAIL',
            'candidate_version': contract.get('version'),
            'core_modified': False,
            'legacy_exact_rerun': False,
            'error': str(exc),
        }, ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
