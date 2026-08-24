#!/usr/bin/env python3
"""Extend PBOC_OFFICIAL_M2_V2 back through 2014 using the same official HTML navigator.

This is a source-coverage extension only. It does not modify GMLI methodology or
lib/state.js. The 2014 annual Money Supply table must be discoverable through
the official PBoC Statistics hierarchy, contain all 12 months, pass continuity,
and agree with the independently published May-2014 Financial Statistics Report
at the report's rounded precision.
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
CONTRACT_PATH = ROOT / 'research' / 'china-m2-official-v2-contract.json'
OUT_ROOT = ROOT / 'research' / 'china-m2-official-v2' / 'latest'
AUDIT_PATH = ROOT / 'audit' / 'china-m2-official-v2.json'

spec = importlib.util.spec_from_file_location('pboc_v2_base', BASE_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def load_contract():
    data = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    if data.get('start_month') != '2014-01':
        raise ValueError('2014 extension requires contract start_month=2014-01')
    return data


def fetch_2014(contract):
    index_raw, index_meta = base.fetch_bytes(contract['statistics_index'])
    links = base.parse_links(index_raw, contract['statistics_index'])
    pack = base.fetch_year(links, 2014)
    values = pack['values']
    if len(values) != 12 or sorted(values)[0] != '2014-01' or sorted(values)[-1] != '2014-12':
        raise ValueError(f'Official 2014 PBoC Money Supply table is not complete: {sorted(values)}')

    cross = contract.get('historical_cross_check') or {}
    month = cross.get('month')
    report_level = cross.get('reported_level_trn_cny')
    if month and report_level is not None:
        if month not in values:
            raise ValueError(f'2014 cross-check month missing: {month}')
        report_100m = float(report_level) * 10000.0
        diff = float(values[month]) - report_100m
        # Report publishes trillion yuan to 2 decimals, so half a rounding unit is 50 x 100m.
        if abs(diff) > 60:
            raise ValueError(f'2014 PBoC table/report cross-check failed: table={values[month]}, report={report_100m}, diff={diff}')
    else:
        diff = None

    return pack, index_raw, index_meta, diff


def validate(contract):
    pack, index_raw, index_meta, diff = fetch_2014(contract)
    return {
        'status': 'PASS_2014_OFFICIAL_EXTENSION',
        'candidate_version': contract['version'],
        'core_modified': False,
        'legacy_exact_rerun': False,
        'year': 2014,
        'months': 12,
        'first_month': '2014-01',
        'last_month': '2014-12',
        'may_2014_m2_100m': pack['values']['2014-05'],
        'may_2014_report_cross_check_diff_100m': None if diff is None else round(diff, 2),
        'overview_url': pack['overview_url'],
        'supply_url': pack['supply_url'],
        'statistics_index_sha256': base.sha256_bytes(index_raw),
        'overview_sha256': base.sha256_bytes(pack['overview_raw']),
        'supply_sha256': base.sha256_bytes(pack['supply_raw']),
        'next_gate': 'REBUILD_CONTINUOUS_PBOC_V2_2014_CURRENT',
    }


def build(contract):
    # Reuse the already validated base 2015-current builder, then prepend the
    # official 2014 source year and recompute derived China YoY fields.
    base_contract = dict(contract)
    base_contract['start_month'] = '2015-01'
    base_manifest = base.build_full(base_contract)
    pack, index_raw, index_meta, diff = fetch_2014(contract)

    csv_path = OUT_ROOT / 'china_m2_100m.csv'
    existing = list(csv.DictReader(io.StringIO(csv_path.read_text(encoding='utf-8'))))
    values = {row['month']: float(row['m2_100m']) for row in existing}
    values.update(pack['values'])
    months = sorted(values)
    if months[0] != '2014-01':
        raise ValueError(f'Unexpected extended start month {months[0]}')

    provenance_path = OUT_ROOT / 'provenance.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    raw_root = OUT_ROOT / 'raw'
    overview_name = '2014-money-banking-overview.html'
    supply_name = '2014-money-supply.html'
    (raw_root / overview_name).write_bytes(pack['overview_raw'])
    (raw_root / supply_name).write_bytes(pack['supply_raw'])
    supply_sha = base.sha256_bytes(pack['supply_raw'])
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    for month in sorted(pack['values']):
        provenance[month] = {
            'source_type': 'PBOC_OFFICIAL_MONEY_SUPPLY_HTML',
            'source_url': pack['supply_url'],
            'raw_file': f'raw/{supply_name}',
            'raw_sha256': supply_sha,
            'retrieved_at': retrieved_at,
            'unit': 'RMB 100 million',
        }
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
        w = csv.DictWriter(f, fieldnames=['month','m2_100m','derived_yoy_pct','source_type','source_url','raw_sha256'])
        w.writeheader(); w.writerows(rows)

    manifest_path = OUT_ROOT / 'manifest.lock.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.update({
        'status': 'PASS_CONTINUOUS_OFFICIAL_V2_SOURCE',
        'built_at': retrieved_at,
        'start_month': '2014-01',
        'months': len(months),
        'missing_months': [],
        'historical_2014_extension': {
            'status': 'PASS',
            'months': 12,
            'overview_url': pack['overview_url'],
            'supply_url': pack['supply_url'],
            'overview_sha256': base.sha256_bytes(pack['overview_raw']),
            'supply_sha256': supply_sha,
            'may_2014_report_cross_check_diff_100m': None if diff is None else round(diff, 2),
        },
        'promotion_allowed': False,
        'next_gate': 'REBUILD_GLOBAL_MONEY_V2_WITH_2015_SIGNAL_START_THEN_FIXED_TRANSMISSION_TRANSFER_TEST',
        'note': 'Official PBoC V2 source now starts 2014-01, enabling China YoY from 2015-01. Historical v1.8b exact-rerun status remains unchanged.'
    })
    manifest['years'] = sorted(
        [y for y in manifest.get('years', []) if y.get('year') != 2014] + [{
            'year': 2014,
            'months': 12,
            'first_month': '2014-01',
            'last_month': '2014-12',
            'overview_url': pack['overview_url'],
            'supply_url': pack['supply_url'],
            'overview_sha256': base.sha256_bytes(pack['overview_raw']),
            'supply_sha256': supply_sha,
        }], key=lambda x: x['year'])
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    AUDIT_PATH.parent.mkdir(exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--validate-only', action='store_true')
    g.add_argument('--build-full', action='store_true')
    args = p.parse_args()
    contract = load_contract()
    try:
        result = validate(contract) if args.validate_only else build(contract)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'status':'FAIL','candidate_version':contract.get('version'),'core_modified':False,'error':str(exc)}, ensure_ascii=False, indent=2))
        return 1

if __name__ == '__main__':
    sys.exit(main())
