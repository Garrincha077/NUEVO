#!/usr/bin/env python3
"""Build the China V2 comparable-base accounting seed from locked official URLs.

2015+ accounting levels come from precise official PBoC Money Supply HTML tables.
The 2014 rows are ACCOUNTING_SEED_ONLY and are derived from the precise 2015
level plus the same month's official published PBoC M2 YoY:

    implied_2014_base = precise_2015_level / (1 + published_2015_yoy/100)

Historical 2015 growth articles are read only from a static month->official-URL
manifest. PBoC search ranking is never part of this production path.
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
GROWTH_LOCK_PATH = ROOT / 'research' / 'china-m2-official-v2-2015-growth-manifest.json'
OUT_ROOT = ROOT / 'research' / 'china-m2-official-v2' / 'latest'
AUDIT_PATH = ROOT / 'audit' / 'china-m2-official-v2.json'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = load_module('pboc_v2_base', BASE_PATH)
nowcast = load_module('pboc_nowcast_parser', NOWCAST_PATH)

PERIOD_END_TITLE = {
    3: '2015年一季度金融统计数据报告',
    6: '2015年上半年金融统计数据报告',
    9: '2015年前三季度金融统计数据报告',
    12: '2015年金融统计数据报告',
}


def load_contract():
    data = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    if data.get('start_month') != '2014-01':
        raise ValueError('Comparable-base seed requires contract start_month=2014-01')
    return data


def load_growth_lock():
    data = json.loads(GROWTH_LOCK_PATH.read_text(encoding='utf-8'))
    if data.get('contract') != 'PBOC_OFFICIAL_2015_GROWTH_LOCK_V1':
        raise ValueError('Unexpected PBoC growth lock contract')
    records = data.get('records') or []
    if len(records) != 12:
        raise ValueError(f'PBoC growth lock must contain 12 months, got {len(records)}')
    by_month = {r['month']: r for r in records}
    expected = [f'2015-{m:02d}' for m in range(1, 13)]
    if sorted(by_month) != expected:
        raise ValueError('PBoC growth lock month coverage is incomplete')
    for month, row in by_month.items():
        if not str(row.get('url', '')).startswith('https://www.pbc.gov.cn/'):
            raise ValueError(f'{month} is not a locked central PBoC URL')
    return by_month


def parse_growth_article(text, month):
    clean = nowcast.strip_html(text).replace('（', '(').replace('）', ')').replace('％', '%').replace('，', ',')
    exact_title = f'2015年{month}月金融统计数据报告'
    allowed = [exact_title]
    if month in PERIOD_END_TITLE:
        allowed.append(PERIOD_END_TITLE[month])
    if not any(title in clean for title in allowed) or '金融统计' not in clean:
        raise ValueError(f'PBoC report title/month mismatch for 2015-{month:02d}')
    if f'{month}月末' not in clean:
        raise ValueError(f'PBoC report body month mismatch for 2015-{month:02d}')
    patterns = [
        r'广义货币\s*\(?M2\)?\s*余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元[^。]{0,160}?同比增长\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%',
        r'M2[^。]{0,80}?余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元[^。]{0,160}?同比增长\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%'
    ]
    for pattern in patterns:
        match = re.search(pattern, clean, flags=re.I)
        if match:
            level = float(match.group(1))
            yoy = float(match.group(2))
            if 50 <= level <= 1000 and -20 <= yoy <= 30:
                return {'level_trn_cny': level, 'yoy_pct': yoy}
    raise ValueError('PBoC report found but M2 balance/YoY sentence was not parsed')


def locked_report(lock_row):
    month = lock_row['month']
    month_num = int(month[5:7])
    raw, meta = base.fetch_bytes(lock_row['url'], timeout=40)
    parsed = parse_growth_article(base.decode_bytes(raw), month_num)
    expected_level = float(lock_row['level_trn_cny'])
    expected_yoy = float(lock_row['yoy_pct'])
    if abs(parsed['level_trn_cny'] - expected_level) > 1e-9:
        raise ValueError(f'{month} locked PBoC level changed: {parsed["level_trn_cny"]} vs {expected_level}')
    if abs(parsed['yoy_pct'] - expected_yoy) > 1e-9:
        raise ValueError(f'{month} locked PBoC YoY changed: {parsed["yoy_pct"]} vs {expected_yoy}')
    current_hash = base.sha256_bytes(raw)
    return {
        'month': month,
        'article_url': lock_row['url'],
        'article_raw': raw,
        'article_sha256': current_hash,
        'discovery_sha256': lock_row.get('article_sha256'),
        'hash_same_as_discovery': current_hash == lock_row.get('article_sha256'),
        'article_http_status': meta.get('http_status'),
        'reported_level_trn_cny': parsed['level_trn_cny'],
        'published_yoy_pct': parsed['yoy_pct'],
        'title_mode': lock_row['title_mode'],
        'source_contract': 'LOCKED_OFFICIAL_PBOC_URL_SEMANTICALLY_VALIDATED'
    }


def build_seed(contract):
    base_contract = dict(contract)
    base_contract['start_month'] = '2015-01'
    base.build_full(base_contract)

    csv_path = OUT_ROOT / 'china_m2_100m.csv'
    existing_rows = list(csv.DictReader(io.StringIO(csv_path.read_text(encoding='utf-8'))))
    precision = {row['month']: float(row['m2_100m']) for row in existing_rows}
    if not all(f'2015-{m:02d}' in precision for m in range(1, 13)):
        raise ValueError('Precision 2015 PBoC HTML history is incomplete')

    lock = load_growth_lock()
    reports = [locked_report(lock[f'2015-{m:02d}']) for m in range(1, 13)]
    seen_urls = set()
    seeds = {}
    seed_manifest = []
    raw_root = OUT_ROOT / 'raw'
    raw_root.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

    for record in reports:
        if record['article_url'] in seen_urls:
            raise ValueError(f'Duplicate locked PBoC URL at {record["month"]}')
        seen_urls.add(record['article_url'])
        current_month = record['month']
        current_100m = precision[current_month]
        rounded_report_100m = record['reported_level_trn_cny'] * 10000.0
        if abs(current_100m - rounded_report_100m) > 60.0:
            raise ValueError(f'{current_month} precision HTML/report level mismatch: {current_100m} vs {rounded_report_100m}')
        yoy = record['published_yoy_pct']
        prior_month = f'2014-{current_month[5:7]}'
        implied = current_100m / (1.0 + yoy / 100.0)
        seeds[prior_month] = implied
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
            'discovery_sha256': record['discovery_sha256'],
            'hash_same_as_discovery': record['hash_same_as_discovery'],
            'title_mode': record['title_mode'],
            'source_contract': record['source_contract']
        })

    anchor = (contract.get('published_growth_anchor') or {}).get('2015-01_yoy_pct')
    if anchor is not None and abs(reports[0]['published_yoy_pct'] - float(anchor)) > 1e-9:
        raise ValueError('2015-01 published growth anchor mismatch')

    provenance_path = OUT_ROOT / 'provenance.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    for item in seed_manifest:
        provenance[item['seed_month']] = {
            'source_type': 'PBOC_IMPLIED_COMPARABLE_BASE_FROM_LOCKED_OFFICIAL_2015_LEVEL_AND_YOY',
            'source_url': item['article_url'],
            'raw_file': f'raw/{item["source_month"]}-financial-statistics-growth.html',
            'raw_sha256': item['article_sha256'],
            'retrieved_at': retrieved_at,
            'unit': 'RMB 100 million',
            'role': 'ACCOUNTING_SEED_ONLY',
            'observed_stock': False,
            'formula': 'precise_2015_level / (1 + official_2015_yoy/100)',
            'source_month': item['source_month'],
            'title_mode': item['title_mode'],
            'url_lock_manifest': str(GROWTH_LOCK_PATH.relative_to(ROOT))
        }
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    values = dict(precision)
    values.update(seeds)
    months = sorted(values)
    if months[0] != '2014-01' or not all(f'2014-{m:02d}' in values for m in range(1, 13)):
        raise ValueError('Comparable-base seed incomplete')

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
            'raw_sha256': p['raw_sha256']
        })

    report_yoy = {r['month']: r['published_yoy_pct'] for r in reports}
    for row in rows:
        if row['month'].startswith('2015-') and abs(float(row['derived_yoy_pct']) - report_yoy[row['month']]) > 0.000001:
            raise ValueError(f'{row["month"]} derived YoY does not reproduce locked official growth')

    with csv_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['month','m2_100m','derived_yoy_pct','source_type','source_url','raw_sha256'])
        writer.writeheader()
        writer.writerows(rows)

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
            'url_lock_contract': 'PBOC_OFFICIAL_2015_GROWTH_LOCK_V1',
            'url_lock_manifest': str(GROWTH_LOCK_PATH.relative_to(ROOT)),
            'search_ranking_dependency': False,
            'formula': 'implied_2014_base = precise_2015_level / (1 + published_2015_yoy/100)',
            'sources': seed_manifest
        },
        'promotion_allowed': False,
        'next_gate': 'REBUILD_GLOBAL_MONEY_V2_THEN_FIXED_TRANSMISSION_TRANSFER_TEST',
        'note': '2014 rows are accounting seeds derived from official PBoC components; historical 2015 growth URLs are statically locked and semantically validated.'
    })
    manifest['years'] = sorted(
        [y for y in manifest.get('years', []) if y.get('year') != 2014] + [{
            'year': 2014, 'months': 12, 'first_month': '2014-01', 'last_month': '2014-12',
            'source_type': 'PBOC_IMPLIED_COMPARABLE_BASE_FROM_LOCKED_OFFICIAL_2015_LEVEL_AND_YOY',
            'role': 'ACCOUNTING_SEED_ONLY', 'observed_stock': False
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
    try:
        result = build_seed(load_contract())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'status':'FAIL','candidate_version':'PBOC_OFFICIAL_M2_V2','core_modified':False,'legacy_exact_rerun':False,'error':str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
