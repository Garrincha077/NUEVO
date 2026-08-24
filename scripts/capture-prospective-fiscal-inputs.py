#!/usr/bin/env python3
import argparse
import csv
import hashlib
import io
import json
import pathlib
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
LATEST_DIR = ROOT / 'research' / 'fiscal-prospective' / 'latest'
AUDIT_DIR = ROOT / 'audit'
UA = 'GMLI-Research-Copilot/2.5 fiscal-prospective-capture'
START_DATE = '2014-01-01'

SERIES = {
    'MTSDS133FMS': 'monthly_federal_surplus_deficit',
    'GDP': 'nominal_gdp',
    'GFDEBTN': 'federal_debt_total',
    'A091RC1Q027SBEA': 'federal_interest_payments',
    'FGRECPT': 'federal_government_current_receipts',
    'FGEXPND': 'federal_government_current_expenditures',
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def fred_url(series_id):
    q = urllib.parse.urlencode({'id': series_id, 'cosd': START_DATE})
    return 'https://fred.stlouisfed.org/graph/fredgraph.csv?' + q


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/csv'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return raw, int(r.status), r.headers.get('Content-Type', '')


def parse_latest(raw, series_id):
    text = raw.decode('utf-8-sig')
    rows = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 2 or row[0].lower() in ('date', 'observation_date'):
            continue
        try:
            value = float(row[1])
        except (ValueError, TypeError):
            continue
        rows.append((row[0], value))
    if not rows:
        raise ValueError(f'No numeric observations for {series_id}')
    rows.sort(key=lambda x: x[0])
    return rows[-1], len(rows)


def read_previous_manifest():
    path = LATEST_DIR / 'manifest.json'
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def validate_date_regression(previous, series_id, latest_date):
    old = ((previous.get('series') or {}).get(series_id) or {}).get('latest_observation_date')
    if old and latest_date < old:
        raise ValueError(f'Refusing fiscal date regression for {series_id}: {old} -> {latest_date}')


def capture(validate_only=False):
    retrieved_at = now_iso()
    previous = read_previous_manifest()
    results = {}
    raw_payloads = {}

    for series_id, role in SERIES.items():
        url = fred_url(series_id)
        raw, http_status, content_type = fetch(url)
        if http_status != 200 or len(raw) < 50:
            raise ValueError(f'Invalid FRED response for {series_id}: HTTP {http_status}, {len(raw)} bytes')
        (latest_date, latest_value), observation_count = parse_latest(raw, series_id)
        validate_date_regression(previous, series_id, latest_date)
        prior = ((previous.get('series') or {}).get(series_id) or {})
        first_observed_at = prior.get('first_observed_at') if prior.get('latest_observation_date') == latest_date else retrieved_at
        results[series_id] = {
            'role': role,
            'source': 'Federal Reserve Bank of St. Louis / FRED',
            'source_url': url,
            'retrieved_at': retrieved_at,
            'first_observed_at': first_observed_at or retrieved_at,
            'latest_observation_date': latest_date,
            'latest_value': latest_value,
            'observation_count': observation_count,
            'raw_bytes': len(raw),
            'raw_sha256': sha256(raw),
            'http_status': http_status,
            'content_type': content_type,
        }
        raw_payloads[series_id] = raw

    manifest = {
        'contract': 'GMLI prospective Fiscal raw capture v1',
        'evidence_tier': 'OVERLAY_RESEARCH_SUPPORT',
        'retrieved_at': retrieved_at,
        'source_start_date': START_DATE,
        'production_state_modified': False,
        'strict_release_ready': False,
        'purpose': 'Preserve future source bytes prospectively so release/vintage provenance is not lost again.',
        'guardrail': 'This capture does not compute, backfill or advance the production Fiscal score. Current revised history is not an exact substitute for the missing historical strict-release runner/vintages.',
        'series': results,
    }

    if validate_only:
        return {'status': 'PASS', 'state_modified': False, **manifest}

    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    for series_id, raw in raw_payloads.items():
        (LATEST_DIR / f'{series_id}.csv').write_bytes(raw)
    (LATEST_DIR / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    audit = {'status': 'PASS', **manifest}
    (AUDIT_DIR / 'fiscal-prospective-capture.json').write_text(json.dumps(audit, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return audit


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--validate-only', action='store_true')
    args = p.parse_args()
    result = capture(validate_only=args.validate_only)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
