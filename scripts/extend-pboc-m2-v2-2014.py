#!/usr/bin/env python3
"""Build the China V2 2014 comparable-base accounting seed.

2015+ accounting levels come from precise official PBoC Money Supply HTML tables.
To preserve the 2015-01 signal/train start without guessing a dead 2014 source,
this script constructs ONLY the prior-year comparable accounting base required
for 2015 from two official PBoC components for each month:

    implied_2014_base = precise_2015_level / (1 + published_2015_yoy/100)

The implied 2014 rows are ACCOUNTING_SEED_ONLY. They are not observed 2014 stock
values and are never described as recovered frozen bytes. No proxy source is used.
The script never modifies lib/state.js.
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
        raise ValueError('Comparable-base seed requires contract start_month=2014-01')
    return data


def exact_2015_report(month):
    report = nowcast.find_pbc_report(2015, month)
    expected = f'2015-{month:02d}'
    if report.get('report_month') != expected:
        raise ValueError(f'PBoC exact-month mismatch: expected={expected}, got={report.get("report_month")}')

    article_raw, article_meta = base.fetch_bytes(report['url'], timeout=40)
    parsed = nowcast.parse_pbc_m2_report(base.decode_bytes(article_raw), 2015, month)
    level_trn = float(parsed['level_trn_cny'])
    yoy_pct = float(parsed['yoy_pct'])
    if abs(level_trn - float(report['level_trn_cny'])) > 1e-9 or abs(yoy_pct - float(report['yoy_pct'])) > 1e-9:
        raise ValueError(f'{expected} semantic refetch mismatch')
    return {
        'month': expected,
        'article_url': report['url'],
        'article_raw': article_raw,
        'article_sha256': base.sha256_bytes(article_raw),
        'article_http_status': article_meta.get('http_status'),
        'reported_level_trn_cny': level_trn,
        'published_yoy_pct': yoy_pct,
        'search_url': report['search_url'],
    }


def build_seed(contract):
    # First rebuild the precision 2015-current official HTML history.
    base_contract = dict(contract)
    base_contract['start_month'] = '2015-01'
    base.build_full(base_contract)

    csv_path = OUT_ROOT / 'china_m2_100m.csv'
    existing_rows = list(csv.DictReader(io.StringIO(csv_path.read_text(encoding='utf-8'))))
    precision = {row['month']: float(row['m2_100m']) for row in existing_rows}
    if not all(f'2015-{m:02d}' in precision for m in range(1, 13)):
        raise ValueError('Precision 2015 PBoC HTML history is incomplete')

    reports = [exact_2015_report(month) for month in range(1, 13)]
    seen_hashes = {}
    seeds = {}
    seed_manifest = []
    raw_root = OUT_ROOT / 'raw'
    raw_root.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

    for record in reports:
        h = record['article_sha256']
        if h in seen_hashes:
            raise ValueError(f'Duplicate 2015 PBoC article for {seen_hashes[h]} and {record["month"]}')
        seen_hashes[h] = record['month']

        current_month = record['month']
        current_100m = precision[current_month]
        # Rounded Financial Statistics report level must agree with precision HTML level.
        report_100m = record['reported_level_trn_cny'] * 10000.0
        if abs(current_100m - report_100m) > 60.0:
            raise ValueError(f'{current_month} precision HTML/report level mismatch: precise={current_100m}, report={report_100m}')

        yoy = record['published_yoy_pct']
        if not (-20.0 < yoy < 30.0):
            raise ValueError(f'{current_month} implausible published M2 YoY: {yoy}')
        prior_month = f'2014-{current_month[5:7]}'
        implied = current_100m / (1.0 + yoy / 100.0)
        seeds[prior_month] = implied

        # Round-trip must recover the exact official published YoY by construction.
        roundtrip = (current_100m / implied - 1.0) * 100.0
        if abs(roundtrip - yoy) > 1e-9:
            raise ValueError(f'{current_month} comparable-base round-trip failed: {roundtrip} vs {yoy}')

        article_name = f'{current_month}-financial-statistics-growth.html'
        (raw_root / article_name).write_bytes(record['article_raw'])
        seed_manifest.append({
            'seed_month': prior_month,
            'source_month': current_month,
            'implied_comparable_base_100m': round(implied, 6),
            'precision_current_level_100m': round(current_100m, 2),
            'published_yoy_pct': yoy,
            'reported_level_trn_cny': record['reported_level_trn_cny'],
            'article_url': record['article_url'],
            'article_sha256': record['article_sha256'],
            'search_url': record['search_url'],
        })

    anchor = (contract.get('published_growth_anchor') or {}).get('2015-01_yoy_pct')
    if anchor is not None:
        jan = next(r for r in reports if r['month'] == '2015-01')
        if abs(jan['published_yoy_pct'] - float(anchor)) > 1e-9:
            raise ValueError(f'2015-01 published growth anchor mismatch: {jan["published_yoy_pct"]} vs {anchor}')

    provenance_path = OUT_ROOT / 'provenance.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    for item in seed_manifest:
        seed_month = item['seed_month']
        source_month = item['source_month']
        provenance[seed_month] = {
            'source_type': 'PBOC_IMPLIED_COMPARABLE_BASE_FROM_OFFICIAL_2015_LEVEL_AND_YOY',
            'source_url': item['article_url'],
            'raw_file': f'raw/{source_month}-financial-statistics-growth.html',
            'raw_sha256': item['article_sha256'],
            'retrieved_at': retrieved_at,
            'unit': 'RMB 100 million',
            'role': 'ACCOUNTING_SEED_ONLY',
            'observed_stock': False,
            'formula': 'precise_2015_level / (1 + official_2015_yoy/100)',
            'source_month': source_month,
        }
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    values = dict(precision)
    values.update(seeds)
    months = sorted(values)
    if months[0] != '2014-01' or not all(f'2014-{m:02d}' in values for m in range(1, 13)):
        raise ValueError('Comparable-base accounting seed is incomplete')

    rows = []
    for month in months:
        prior = f'{int(month[:4])-1:04d}-{month[5:7]}'
        derived_yoy = (values[month] / values[prior] - 1.0) * 100.0 if prior in values else None
        p = provenance[month]
        rows.append({
            'month': month,
            'm2_100m': round(values[month], 6 if month.startswith('2014-') else 2),
            'derived_yoy_pct': None if derived_yoy is None else round(derived_yoy, 6),
            'source_type': p['source_type'],
            'source_url': p['source_url'],
            'raw_sha256': p['raw_sha256'],
        })

    # Every 2015 derived YoY must reproduce the official published exact-month report.
    report_yoy = {r['month']: r['published_yoy_pct'] for r in reports}
    for row in rows:
        if row['month'].startswith('2015-'):
            if abs(float(row['derived_yoy_pct']) - report_yoy[row['month']]) > 0.000001:
                raise ValueError(f'{row["month"]} derived YoY does not reproduce official published growth')

    with csv_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['month','m2_100m','derived_yoy_pct','source_type','source_url','raw_sha256'])
        writer.writeheader(); writer.writerows(rows)

    manifest_path = OUT_ROOT / 'manifest.lock.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.update({
        'status': 'PASS_CONTINUOUS_OFFICIAL_V2_SOURCE_WITH_COMPARABLE_BASE_SEED',
        'built_at': retrieved_at,
        'start_month': '2014-01',
        'end_month': months[-1],
        'months': len(months),
        'missing_months': [],
        'historical_2014_extension': None,
        'comparable_base_seed_2014': {
            'status': 'PASS_OFFICIAL_COMPONENT_DERIVATION',
            'months': 12,
            'role': 'ACCOUNTING_SEED_ONLY',
            'observed_stock': False,
            'source_precision_history': '2015 current-month level uses precise PBoC Money Supply HTML values',
            'source_growth': 'exact-month official 2015 PBoC Financial Statistics Report YoY',
            'formula': 'implied_2014_base = precise_2015_level / (1 + published_2015_yoy/100)',
            'sources': seed_manifest,
        },
        'promotion_allowed': False,
        'next_gate': 'REBUILD_GLOBAL_MONEY_V2_THEN_FIXED_TRANSMISSION_TRANSFER_TEST',
        'note': '2014 rows are explicit comparable-base accounting seeds derived only from official PBoC 2015 level+growth components; they are not observed 2014 stocks and not recovered frozen bytes.'
    })
    manifest['years'] = sorted(
        [y for y in manifest.get('years', []) if y.get('year') != 2014] + [{
            'year': 2014,
            'months': 12,
            'first_month': '2014-01',
            'last_month': '2014-12',
            'source_type': 'PBOC_IMPLIED_COMPARABLE_BASE_FROM_OFFICIAL_2015_LEVEL_AND_YOY',
            'role': 'ACCOUNTING_SEED_ONLY',
            'observed_stock': False,
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
        result = build_seed(contract)
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
