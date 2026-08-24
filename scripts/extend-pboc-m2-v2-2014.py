#!/usr/bin/env python3
"""Extend PBOC_OFFICIAL_M2_V2 through 2014 using official monthly PBoC reports.

2014 is a rounded seed year only, used to make 2015 China YoY computable.
2015+ remains the precision PBoC Money Supply HTML history. Every 2014 month
must pass the same exact year+month Financial Statistics Report validation used
by the production China nowcast parser. This script never reconstructs the dead
2014 HTML target and never modifies lib/state.js.
"""
import argparse
import csv
import importlib.util
import io
import json
import pathlib
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


def fetch_month_report(month):
    year = 2014
    # Reuse the production-validated parser. find_pbc_report rejects a candidate
    # unless its text contains the exact YYYY年M月 token and its M2 balance/YoY
    # sentence parses. This prevents a quarterly/adjacent-month article from
    # silently seeding the requested month.
    report = nowcast.find_pbc_report(year, month)
    expected = f'{year}-{month:02d}'
    if report.get('report_month') != expected:
        raise ValueError(f'PBoC exact-month mismatch: expected={expected}, got={report.get("report_month")}')
    level_trn = float(report['level_trn_cny'])
    yoy_pct = float(report['yoy_pct'])
    if not (50 <= level_trn <= 300):
        raise ValueError(f'{expected} M2 level sanity failure: {level_trn} tn CNY')

    # Re-fetch the exact accepted search/article payloads so the seed archive
    # preserves the bytes actually captured. PBoC search pages can change bytes
    # between requests, so raw-byte equality across two separate HTTP calls is
    # not an invariant. Instead, re-parse the accepted article and require the
    # same exact month semantics and economic values.
    search_raw, search_meta = base.fetch_bytes(report['search_url'], timeout=45)
    article_raw, article_meta = base.fetch_bytes(report['url'], timeout=40)
    parsed_again = nowcast.parse_pbc_m2_report(base.decode_bytes(article_raw), year, month)
    if abs(float(parsed_again['level_trn_cny']) - level_trn) > 1e-9:
        raise ValueError(f'{expected} PBoC M2 level changed across capture: {level_trn} -> {parsed_again["level_trn_cny"]}')
    if abs(float(parsed_again['yoy_pct']) - yoy_pct) > 1e-9:
        raise ValueError(f'{expected} PBoC M2 YoY changed across capture: {yoy_pct} -> {parsed_again["yoy_pct"]}')

    return {
        'month': expected,
        'level_trn_cny': level_trn,
        'yoy_pct': yoy_pct,
        'm2_100m': round(level_trn * 10000.0, 2),
        'search_url': report['search_url'],
        'article_url': report['url'],
        'search_raw': search_raw,
        'article_raw': article_raw,
        'search_sha256': base.sha256_bytes(search_raw),
        'article_sha256': base.sha256_bytes(article_raw),
        'search_http_status': search_meta.get('http_status'),
        'article_http_status': article_meta.get('http_status'),
    }


def fetch_2014_reports(contract):
    records = [fetch_month_report(month) for month in range(1, 13)]
    values = {r['month']: r['m2_100m'] for r in records}
    expected = [f'2014-{m:02d}' for m in range(1, 13)]
    if sorted(values) != expected:
        raise ValueError(f'2014 monthly report seed is incomplete: {sorted(values)}')

    # Adjacent-month sanity only; exact-month validation above is the primary guard.
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

    # Duplicate accepted article hashes across different seed months are forbidden.
    # A monthly report can be republished/migrated, but one exact article must not
    # silently stand in for two different months.
    seen = {}
    for record in records:
        h = record['article_sha256']
        if h in seen:
            raise ValueError(f'Duplicate PBoC monthly article for {seen[h]} and {record["month"]}: {h}')
        seen[h] = record['month']
    return records, values


def validate(contract):
    records, values = fetch_2014_reports(contract)
    return {
        'status': 'PASS_2014_OFFICIAL_MONTHLY_REPORT_SEED',
        'candidate_version': contract['version'],
        'core_modified': False,
        'legacy_exact_rerun': False,
        'source_contract': 'PBOC_OFFICIAL_MONTHLY_REPORT_SEED_2014_EXACT_MONTH',
        'year': 2014,
        'months': 12,
        'first_month': '2014-01',
        'last_month': '2014-12',
        'may_2014_m2_100m': values['2014-05'],
        'precision_note': '2014 balances are rounded to 0.01 trillion CNY in monthly reports; 2015+ remains precision HTML history.',
        'months_preview': [{'month':r['month'],'m2_100m':r['m2_100m'],'yoy_pct':r['yoy_pct'],'article_url':r['article_url'],'article_sha256':r['article_sha256']} for r in records],
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
            'exact_month_validated': True,
            'semantic_refetch_validated': True,
        }
        seed_manifest.append({
            'month': month,
            'm2_100m': record['m2_100m'],
            'yoy_pct': record['yoy_pct'],
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
            'status': 'PASS_OFFICIAL_MONTHLY_REPORT_SEED_EXACT_MONTH',
            'months': 12,
            'role': 'SEED_YEAR_ONLY',
            'precision': '0.01 trillion CNY per monthly Financial Statistics Report',
            'exact_month_validation': True,
            'semantic_refetch_validation': True,
            'may_2014_m2_100m': seed_values['2014-05'],
            'sources': seed_manifest,
        },
        'promotion_allowed': False,
        'next_gate': 'REBUILD_GLOBAL_MONEY_V2_WITH_2015_SIGNAL_START_THEN_FIXED_TRANSMISSION_TRANSFER_TEST',
        'note': 'Official PBoC V2 starts 2014-01. Every 2014 seed month passed exact year+month report validation and semantic refetch validation; 2015+ is precision Money Supply HTML history. No dead historical source is reconstructed.'
    })
    manifest['years'] = sorted(
        [y for y in manifest.get('years', []) if y.get('year') != 2014] + [{
            'year': 2014,
            'months': 12,
            'first_month': '2014-01',
            'last_month': '2014-12',
            'source_type': 'PBOC_OFFICIAL_MONTHLY_FINANCIAL_STATISTICS_REPORT_SEED',
            'precision': '0.01 trillion CNY',
            'exact_month_validation': True,
            'semantic_refetch_validation': True,
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
