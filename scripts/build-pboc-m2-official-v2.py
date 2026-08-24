#!/usr/bin/env python3
"""Build a versioned PBoC-native China M2 level-history candidate.

Primary source: official PBoC Statistics -> yearly Money and Banking Statistics
-> Money Supply HTML tables. This is deliberately a NEW source candidate, not
an attempt to recreate missing historical v1.8b bytes.

The script never modifies lib/state.js.
"""

import argparse
import csv
import hashlib
import html
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / 'research' / 'china-m2-official-v2-contract.json'
OUT_ROOT = ROOT / 'research' / 'china-m2-official-v2' / 'latest'
AUDIT_PATH = ROOT / 'audit' / 'china-m2-official-v2.json'
UA = 'GMLI-PBoC-M2-v2/2.0 official-html-source-candidate'


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def fetch_bytes(url, timeout=40, attempts=3):
    if not isinstance(url, str) or not url.startswith('https://'):
        raise ValueError(f'Only HTTPS sources are allowed: {url!r}')
    last = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': UA,
                'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if len(raw) < 100:
                    raise ValueError(f'Implausibly small payload: {len(raw)} bytes')
                return raw, {
                    'http_status': getattr(r, 'status', None),
                    'content_type': r.headers.get('Content-Type'),
                    'final_url': r.geturl(),
                }
        except Exception as exc:
            last = exc
            if attempt < attempts:
                time.sleep(attempt * 2)
    raise RuntimeError(f'Fetch failed after {attempts} attempts: {last}')


def decode_bytes(raw):
    for enc in ('utf-8-sig', 'utf-8', 'gb18030', 'latin-1'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    raise ValueError('Unable to decode PBoC payload')


def strip_html(raw_or_text):
    s = decode_bytes(raw_or_text) if isinstance(raw_or_text, (bytes, bytearray)) else str(raw_or_text)
    s = re.sub(r'<script[\s\S]*?</script>', ' ', s, flags=re.I)
    s = re.sub(r'<style[\s\S]*?</style>', ' ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = html.unescape(s).replace('\u3000', ' ').replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._href = None
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            self._href = dict(attrs).get('href')
            self._parts = []

    def handle_data(self, data):
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == 'a' and self._href is not None:
            text = re.sub(r'\s+', ' ', ''.join(self._parts)).strip()
            self.links.append((text, self._href))
            self._href = None
            self._parts = []


def parse_links(raw, base_url):
    p = LinkParser()
    p.feed(decode_bytes(raw))
    return [(text, urllib.parse.urljoin(base_url, href)) for text, href in p.links if href]


def load_contract():
    data = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    if data.get('version') != 'PBOC_OFFICIAL_M2_V2':
        raise ValueError('Unexpected China M2 v2 contract version')
    return data


def discover_overview_url(index_links, year):
    year_label = f'{year}年统计数据'
    starts = [i for i, (text, _) in enumerate(index_links) if year_label in text]
    for start in starts:
        for text, url in index_links[start + 1:start + 14]:
            if '货币统计概览' in text or 'Money and Banking Statistics' in text:
                return url
    raise ValueError(f'Official PBoC Money and Banking Statistics link not found for {year}')


def discover_supply_url(overview_raw, overview_url):
    text = decode_bytes(overview_raw)
    patterns = [
        r'货币供应量[\s\S]{0,1200}?href\s*=\s*["\']([^"\']+)["\'][^>]*>\s*htm\s*</a>',
        r'Money\s+Supply[\s\S]{0,1200}?href\s*=\s*["\']([^"\']+)["\'][^>]*>\s*htm\s*</a>',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I)
        if m:
            return urllib.parse.urljoin(overview_url, html.unescape(m.group(1)))
    raise ValueError(f'Official PBoC Money Supply HTML link not found on {overview_url}')


def numeric_levels(segment):
    out = []
    for token in re.findall(r'(?<![\d.])([0-9]{6,8}(?:\.[0-9]{1,2})?)(?![\d.])', segment):
        try:
            value = float(token)
        except ValueError:
            continue
        if 100000 <= value <= 10000000:
            out.append(value)
    return out


def parse_money_supply_html(raw, year):
    text = strip_html(raw).replace('（', '(').replace('）', ')')
    months = []
    for m in re.finditer(fr'{year}\.(0[1-9]|1[0-2])', text):
        month = int(m.group(1))
        if month not in months:
            months.append(month)
        if len(months) == 12:
            break
    if not months:
        raise ValueError(f'{year} Money Supply table has no month headers')

    start = re.search(r'货币和准货币\s*\(M2\)', text, flags=re.I)
    if not start:
        raise ValueError(f'{year} Money Supply table has no M2 row')
    tail = text[start.end():]
    end = re.search(r'Money\s*&\s*Quasi[- ]?money|货币\s*\(M1\)', tail, flags=re.I)
    segment = tail[:end.start()] if end else tail[:2500]
    values = numeric_levels(segment)
    if not values:
        raise ValueError(f'{year} Money Supply M2 row has no numeric levels')
    if len(values) > len(months):
        values = values[:len(months)]

    result = {f'{year:04d}-{month:02d}': round(values[i], 2) for i, month in enumerate(months[:len(values)])}
    ordered = [result[k] for k in sorted(result)]
    for i in range(1, len(ordered)):
        ratio = ordered[i] / ordered[i - 1]
        if not (0.90 <= ratio <= 1.10):
            raise ValueError(f'{year} M2 continuity failure at value {i+1}: ratio={ratio:.4f}')
    return result


def fetch_year(index_links, year):
    overview_url = discover_overview_url(index_links, year)
    overview_raw, overview_meta = fetch_bytes(overview_url)
    supply_url = discover_supply_url(overview_raw, overview_url)
    supply_raw, supply_meta = fetch_bytes(supply_url)
    values = parse_money_supply_html(supply_raw, year)
    return {
        'year': year,
        'overview_url': overview_url,
        'overview_raw': overview_raw,
        'overview_meta': overview_meta,
        'supply_url': supply_url,
        'supply_raw': supply_raw,
        'supply_meta': supply_meta,
        'values': values,
    }


def validate_anchor(series, month, expected, tolerance=0.05):
    if month not in series:
        raise ValueError(f'Missing validation anchor {month}')
    actual = float(series[month])
    if abs(actual - float(expected)) > tolerance:
        raise ValueError(f'{month} anchor mismatch: actual={actual}, expected={expected}, tolerance={tolerance}')


def validate_sources(contract):
    index_url = contract['statistics_index']
    index_raw, index_meta = fetch_bytes(index_url)
    index_links = parse_links(index_raw, index_url)
    current_year = datetime.now(timezone.utc).year
    sample_years = sorted(set([2015, 2018, 2021, 2025, current_year]))
    series = {}
    years = []
    for year in sample_years:
        pack = fetch_year(index_links, year)
        values = pack['values']
        if year < current_year and len(values) != 12:
            raise ValueError(f'{year} expected 12 M2 months, got {len(values)}')
        if year == current_year and len(values) < 1:
            raise ValueError(f'{year} current M2 table is empty')
        series.update(values)
        years.append({
            'year': year,
            'status': 'PASS',
            'months': len(values),
            'first_month': sorted(values)[0],
            'last_month': sorted(values)[-1],
            'overview_url': pack['overview_url'],
            'supply_url': pack['supply_url'],
            'overview_sha256': sha256_bytes(pack['overview_raw']),
            'supply_sha256': sha256_bytes(pack['supply_raw']),
        })

    anchors = contract['validation_anchors']
    for key, expected in anchors.items():
        month = key.split('_100m')[0]
        if month[:4] in {str(y) for y in sample_years}:
            validate_anchor(series, month, expected)

    current = contract['current_cross_check']
    latest_known_month = current['latest_known_month']
    if latest_known_month in series:
        rounded_report_100m = float(current['latest_known_level_trn_cny']) * 10000
        if abs(series[latest_known_month] - rounded_report_100m) > float(current['tolerance_100m']):
            raise ValueError(
                f'Current PBoC table/report cross-check failed: table={series[latest_known_month]}, '
                f'report={rounded_report_100m}'
            )

    return {
        'status': 'PASS',
        'candidate_version': contract['version'],
        'core_modified': False,
        'legacy_exact_rerun': False,
        'source_contract': 'PBOC_OFFICIAL_HTML_MONEY_SUPPLY_TABLES',
        'statistics_index_url': index_url,
        'statistics_index_sha256': sha256_bytes(index_raw),
        'statistics_index_http_status': index_meta['http_status'],
        'validated_years': years,
        'validation_anchor_months': sorted(k.split('_100m')[0] for k in anchors),
        'note': 'Representative official PBoC HTML history tables passed. Full continuous 2015+ capture is the next step.',
    }


def build_full(contract):
    retrieved_at = now_iso()
    index_url = contract['statistics_index']
    index_raw, index_meta = fetch_bytes(index_url)
    index_links = parse_links(index_raw, index_url)
    current_year = datetime.now(timezone.utc).year
    series = {}
    provenance = {}
    source_files = {'statistics-index.html': index_raw}
    year_manifest = []

    for year in range(2015, current_year + 1):
        pack = fetch_year(index_links, year)
        values = pack['values']
        if year < current_year and len(values) != 12:
            raise ValueError(f'{year} expected 12 M2 months, got {len(values)}')
        if year == current_year and len(values) < 1:
            raise ValueError(f'{year} current M2 table is empty')

        overview_name = f'{year}-money-banking-overview.html'
        supply_name = f'{year}-money-supply.html'
        source_files[overview_name] = pack['overview_raw']
        source_files[supply_name] = pack['supply_raw']
        supply_sha = sha256_bytes(pack['supply_raw'])
        for month, value in values.items():
            if month in series:
                raise ValueError(f'Duplicate China M2 month {month}')
            series[month] = value
            provenance[month] = {
                'source_type': 'PBOC_OFFICIAL_MONEY_SUPPLY_HTML',
                'source_url': pack['supply_url'],
                'raw_file': f'raw/{supply_name}',
                'raw_sha256': supply_sha,
                'retrieved_at': retrieved_at,
                'unit': 'RMB 100 million',
            }
        year_manifest.append({
            'year': year,
            'months': len(values),
            'first_month': sorted(values)[0],
            'last_month': sorted(values)[-1],
            'overview_url': pack['overview_url'],
            'supply_url': pack['supply_url'],
            'overview_sha256': sha256_bytes(pack['overview_raw']),
            'supply_sha256': supply_sha,
        })

    months = sorted(series)
    if not months or months[0] != contract['start_month']:
        raise ValueError(f'Unexpected V2 start month: {months[0] if months else None}')
    last_month = months[-1]

    def month_range(start, end):
        sy, sm = map(int, start.split('-'))
        ey, em = map(int, end.split('-'))
        out = []
        y, m = sy, sm
        while (y, m) <= (ey, em):
            out.append(f'{y:04d}-{m:02d}')
            m += 1
            if m == 13:
                y += 1
                m = 1
        return out

    expected = month_range(contract['start_month'], last_month)
    missing = [m for m in expected if m not in series]
    if missing:
        raise ValueError('Continuous official V2 history missing months: ' + ', '.join(missing[:30]))

    anchors = contract['validation_anchors']
    for key, expected_value in anchors.items():
        month = key.split('_100m')[0]
        if month <= last_month:
            validate_anchor(series, month, expected_value)

    current = contract['current_cross_check']
    cross_month = current['latest_known_month']
    if cross_month in series:
        rounded_report_100m = float(current['latest_known_level_trn_cny']) * 10000
        diff = series[cross_month] - rounded_report_100m
        if abs(diff) > float(current['tolerance_100m']):
            raise ValueError(f'Current table/report cross-check failed at {cross_month}: diff={diff}')
    else:
        diff = None

    rows = []
    for month in expected:
        value = series[month]
        prior = f'{int(month[:4])-1:04d}-{month[5:7]}'
        yoy = (value / series[prior] - 1) * 100 if prior in series else None
        rows.append({
            'month': month,
            'm2_100m': round(value, 2),
            'derived_yoy_pct': None if yoy is None else round(yoy, 6),
            'source_type': provenance[month]['source_type'],
            'source_url': provenance[month]['source_url'],
            'raw_sha256': provenance[month]['raw_sha256'],
        })

    raw_root = OUT_ROOT / 'raw'
    raw_root.mkdir(parents=True, exist_ok=True)
    for name, raw in source_files.items():
        (raw_root / name).write_bytes(raw)

    with (OUT_ROOT / 'china_m2_100m.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['month','m2_100m','derived_yoy_pct','source_type','source_url','raw_sha256'])
        writer.writeheader()
        writer.writerows(rows)
    (OUT_ROOT / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    manifest = {
        'status': 'PASS_CONTINUOUS_OFFICIAL_V2_SOURCE',
        'candidate_version': contract['version'],
        'source_contract': 'PBOC_OFFICIAL_HTML_MONEY_SUPPLY_TABLES',
        'evidence_tier': 'RESEARCH_SOURCE_CANDIDATE',
        'built_at': retrieved_at,
        'core_modified': False,
        'legacy_exact_rerun': False,
        'start_month': expected[0],
        'end_month': expected[-1],
        'months': len(expected),
        'missing_months': [],
        'latest': rows[-1],
        'current_report_cross_check_diff_100m': None if diff is None else round(diff, 2),
        'statistics_index': {
            'url': index_url,
            'raw_file': 'raw/statistics-index.html',
            'raw_sha256': sha256_bytes(index_raw),
            'http_status': index_meta['http_status'],
        },
        'years': year_manifest,
        'raw_source_files': [
            {'filename': f'raw/{name}', 'bytes': len(raw), 'sha256': sha256_bytes(raw)}
            for name, raw in sorted(source_files.items())
        ],
        'promotion_allowed': False,
        'next_gate': 'BUILD_GLOBAL_MONEY_V2_CANDIDATE_AND_COMPARE_TRANSFER',
        'note': 'China source provenance is closed for a NEW official-source candidate. Historical v1.8b exact-rerun status remains unchanged.',
    }
    (OUT_ROOT / 'manifest.lock.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
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
        result = validate_sources(contract) if args.validate_only else build_full(contract)
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
