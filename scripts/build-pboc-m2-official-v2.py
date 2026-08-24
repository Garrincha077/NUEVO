#!/usr/bin/env python3
"""Build a versioned PBoC-native China M2 level-history candidate.

This is deliberately NOT the missing historical v1.8b exact rerun. It creates a
new, auditable production-source candidate from official PBoC bytes. Annual
Money Supply tables are preferred for precision; official monthly Financial
Statistics Reports fill years/months where a full annual Money Supply table is
not configured yet.

The script never modifies lib/state.js.
"""

import argparse
import csv
import hashlib
import html
import io
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / 'research' / 'china-m2-official-v2-contract.json'
OUT_ROOT = ROOT / 'research' / 'china-m2-official-v2' / 'latest'
AUDIT_PATH = ROOT / 'audit' / 'china-m2-official-v2.json'
UA = 'GMLI-PBoC-M2-v2/1.0 official-source-candidate'
PBOC_SEARCH_BASE = 'https://wzdig.pbc.gov.cn/search/pcRender'
PBOC_SEARCH_PAGE_ID = 'c177a85bd02b4114bebebd210809f691'


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch_bytes(url, timeout=45, attempts=3, accept='*/*'):
    if not isinstance(url, str) or not url.startswith('https://'):
        raise ValueError(f'Only HTTPS sources are allowed: {url!r}')
    last = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': accept})
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


def strip_html(value):
    s = re.sub(r'<script[\s\S]*?</script>', ' ', str(value), flags=re.I)
    s = re.sub(r'<style[\s\S]*?</style>', ' ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = html.unescape(s).replace('\u3000', ' ').replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def month_tuple(month):
    y, m = map(int, month.split('-'))
    return y, m


def month_range(start, end):
    y, m = month_tuple(start)
    ey, em = month_tuple(end)
    out = []
    while (y, m) <= (ey, em):
        out.append(f'{y:04d}-{m:02d}')
        m += 1
        if m == 13:
            y += 1
            m = 1
    return out


def latest_report_month():
    now = datetime.now(timezone.utc)
    y, m = now.year, now.month - 1
    if m == 0:
        return f'{y-1:04d}-12'
    return f'{y:04d}-{m:02d}'


def load_contract():
    data = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    if data.get('version') != 'PBOC_OFFICIAL_M2_V2':
        raise ValueError('Unexpected China M2 v2 contract version')
    return data


def pdftotext(raw):
    if subprocess.run(['which', 'pdftotext'], capture_output=True).returncode != 0:
        raise RuntimeError('pdftotext is required; install poppler-utils')
    with tempfile.TemporaryDirectory() as td:
        src = pathlib.Path(td) / 'source.pdf'
        src.write_bytes(raw)
        proc = subprocess.run(['pdftotext', '-layout', str(src), '-'], capture_output=True, check=True)
        return proc.stdout.decode('utf-8', errors='replace')


def numeric_tokens(text):
    tokens = []
    for token in re.findall(r'(?<![\d.])([0-9][0-9 ,]*\.?[0-9]{0,2})(?![\d.])', text):
        clean = token.replace(' ', '').replace(',', '')
        try:
            v = float(clean)
        except ValueError:
            continue
        if 100000 <= v <= 10000000:
            tokens.append(v)
    return tokens


def parse_money_supply_pdf(raw, year, expected_months):
    text = pdftotext(raw).replace('（', '(').replace('）', ')')
    month_markers = re.findall(fr'{year}\.?(0[1-9]|1[0-2])', text)
    if len(set(month_markers)) < expected_months:
        raise ValueError(f'{year} PDF has only {len(set(month_markers))} distinct month markers')

    starts = [m.start() for m in re.finditer(r'货币和准货币|Money\s*&\s*Quasi[- ]?money', text, flags=re.I)]
    if not starts:
        raise ValueError(f'{year} M2 label not found')

    candidates = []
    for start in starts:
        segment = text[start:start + 2500]
        stop = re.search(r'货币\s*\(?M1\)?|Currency\s+in\s+Circulation', segment, flags=re.I)
        if stop:
            segment = segment[:stop.start()]
        vals = numeric_tokens(segment)
        if len(vals) >= expected_months:
            candidates.append(vals[:expected_months])
    if not candidates:
        # Some PBoC one-page PDFs place the English M2 label after the values.
        for start in starts:
            vals = numeric_tokens(text[start:start + 5000])
            if len(vals) >= expected_months:
                candidates.append(vals[:expected_months])
    if not candidates:
        raise ValueError(f'{year} M2 values not parsed')

    values = candidates[0]
    if any(v <= 0 for v in values):
        raise ValueError(f'{year} non-positive M2 value')
    return {f'{year:04d}-{i+1:02d}': round(v, 2) for i, v in enumerate(values)}


def pbc_search_url(year, month):
    query = f'{year}年{month}月金融统计数据报告'
    params = urllib.parse.urlencode({
        'dr': 'true', 'pNo': '1', 'pageId': PBOC_SEARCH_PAGE_ID,
        'q': query, 'sr': 'score desc'
    })
    return PBOC_SEARCH_BASE + '?' + params


def central_pbc_urls(search_html):
    decoded = html.unescape(search_html)
    urls = re.findall(r'https?://(?:www\.)?pbc\.gov\.cn/[^"\'<>\s]+/index\.html', decoded, flags=re.I)
    out = []
    for url in urls:
        parsed = urllib.parse.urlparse(url)
        if parsed.hostname not in ('pbc.gov.cn', 'www.pbc.gov.cn'):
            continue
        normalized = urllib.parse.urlunparse(('https', 'www.pbc.gov.cn', parsed.path, '', '', ''))
        if normalized not in out:
            out.append(normalized)
    return out


def parse_report(raw, year, month):
    clean = strip_html(decode_bytes(raw)).replace('（', '(').replace('）', ')').replace('％', '%').replace('，', ',')
    if f'{year}年{month}月' not in clean or '金融统计' not in clean:
        raise ValueError('PBoC report title/month mismatch')
    patterns = [
        r'广义货币\s*\(?M2\)?\s*余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元[^。]{0,160}?同比增长\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%',
        r'M2[^。]{0,80}?余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元[^。]{0,160}?同比增长\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%'
    ]
    for pattern in patterns:
        m = re.search(pattern, clean, flags=re.I)
        if m:
            level = float(m.group(1))
            yoy = float(m.group(2))
            if not (50 <= level <= 1000) or not (-20 <= yoy <= 30):
                raise ValueError(f'PBoC report sanity check failed: level={level}, yoy={yoy}')
            return {'level_trn_cny': level, 'm2_100m': round(level * 10000, 2), 'yoy_pct': yoy}
    raise ValueError('PBoC report M2 balance/YoY sentence not parsed')


def find_report(year, month):
    search_url = pbc_search_url(year, month)
    search_raw, search_meta = fetch_bytes(search_url, timeout=35, accept='text/html')
    candidates = central_pbc_urls(decode_bytes(search_raw))
    if not candidates:
        raise ValueError(f'No central PBoC URL discovered for {year}-{month:02d}')
    errors = []
    for url in candidates[:12]:
        try:
            page_raw, page_meta = fetch_bytes(url, timeout=30, accept='text/html')
            parsed = parse_report(page_raw, year, month)
            return {
                'month': f'{year:04d}-{month:02d}',
                'url': url,
                'search_url': search_url,
                'search_raw': search_raw,
                'page_raw': page_raw,
                'search_sha256': sha256_bytes(search_raw),
                'article_sha256': sha256_bytes(page_raw),
                'search_meta': search_meta,
                'article_meta': page_meta,
                **parsed
            }
        except Exception as exc:
            errors.append(f'{url}: {str(exc)[:180]}')
    raise ValueError(f'PBoC report {year}-{month:02d} failed: ' + ' | '.join(errors[:4]))


def validate_anchor(actual, expected, tolerance, label):
    if abs(float(actual) - float(expected)) > tolerance:
        raise ValueError(f'{label} anchor mismatch: actual={actual}, expected={expected}, tolerance={tolerance}')


def validate_sources(contract):
    annual = []
    for src in contract['annual_tables']:
        raw, meta = fetch_bytes(src['url'], accept='application/pdf')
        values = parse_money_supply_pdf(raw, int(src['year']), int(src['expected_months']))
        anchor = values[src['anchor_month']]
        validate_anchor(anchor, src['anchor_m2'], 0.05, src['anchor_month'])
        annual.append({
            'year': src['year'], 'status': 'PASS', 'months': len(values),
            'anchor_month': src['anchor_month'], 'anchor_m2': anchor,
            'bytes': len(raw), 'sha256': sha256_bytes(raw), 'final_url': meta['final_url']
        })

    samples = []
    sample_months = ['2015-01', '2015-12', '2018-01', '2018-12', '2021-12', latest_report_month()]
    seen = set()
    for month in sample_months:
        if month in seen:
            continue
        seen.add(month)
        y, m = month_tuple(month)
        report = find_report(y, m)
        samples.append({
            'month': month, 'status': 'PASS', 'level_trn_cny': report['level_trn_cny'],
            'm2_100m': report['m2_100m'], 'yoy_pct': report['yoy_pct'],
            'article_sha256': report['article_sha256'], 'url': report['url']
        })

    anchors = contract['validation_anchors']
    by = {x['month']: x for x in samples}
    validate_anchor(by['2015-01']['level_trn_cny'], anchors['2015-01_trn_cny'], 0.011, '2015-01')
    validate_anchor(by['2015-12']['level_trn_cny'], anchors['2015-12_trn_cny_approx'], 0.011, '2015-12')
    validate_anchor(by['2018-01']['level_trn_cny'], anchors['2018-01_trn_cny'], 0.011, '2018-01')
    validate_anchor(by['2018-12']['level_trn_cny'], anchors['2018-12_trn_cny'], 0.011, '2018-12')
    validate_anchor(by['2021-12']['m2_100m'], anchors['2021-12_100m'], 60, '2021-12 rounded report vs exact table')

    return {
        'status': 'PASS',
        'candidate_version': contract['version'],
        'core_modified': False,
        'legacy_exact_rerun': False,
        'annual_tables': annual,
        'monthly_report_samples': samples,
        'note': 'Validation proves official source paths and representative parsing only; full continuous build is a separate capture step.'
    }


def build_full(contract):
    series = {}
    provenance = {}
    raw_files = {}

    for src in contract['annual_tables']:
        year = int(src['year'])
        raw, meta = fetch_bytes(src['url'], accept='application/pdf')
        values = parse_money_supply_pdf(raw, year, int(src['expected_months']))
        validate_anchor(values[src['anchor_month']], src['anchor_m2'], 0.05, src['anchor_month'])
        raw_name = f'annual-{year}.pdf'
        raw_files[raw_name] = raw
        for month, value in values.items():
            series[month] = value
            provenance[month] = {
                'source_type': 'PBOC_ANNUAL_MONEY_SUPPLY_TABLE', 'source_url': src['url'],
                'raw_file': raw_name, 'raw_sha256': sha256_bytes(raw), 'precision': 'official_table_100m'
            }

    cap = latest_report_month()
    for fill in contract['report_fill_ranges']:
        end = min(fill['end'], cap)
        if month_tuple(fill['start']) > month_tuple(end):
            continue
        for month in month_range(fill['start'], end):
            if month in series:
                continue
            y, m = month_tuple(month)
            report = find_report(y, m)
            series[month] = report['m2_100m']
            search_name = f'report-{month}-search.html'
            page_name = f'report-{month}.html'
            raw_files[search_name] = report['search_raw']
            raw_files[page_name] = report['page_raw']
            provenance[month] = {
                'source_type': 'PBOC_MONTHLY_FINANCIAL_STATISTICS_REPORT',
                'source_url': report['url'], 'search_url': report['search_url'],
                'raw_file': page_name, 'raw_sha256': report['article_sha256'],
                'search_raw_file': search_name, 'search_sha256': report['search_sha256'],
                'reported_yoy_pct': report['yoy_pct'], 'precision': 'reported_trillion_2dp_converted_to_100m'
            }

    expected = month_range(contract['start_month'], cap)
    missing = [m for m in expected if m not in series]
    if missing:
        raise ValueError('Continuous official V2 history missing months: ' + ', '.join(missing[:30]))

    # Cross-check rounded 2015 monthly report values against exact Annual Report quarter-end anchors.
    q_anchors = {'2015-03': 1275332.78, '2015-06': 1333375.36, '2015-09': 1359824.06, '2015-12': 1392278.11}
    q_diff = {}
    for month, exact in q_anchors.items():
        diff = series[month] - exact
        if abs(diff) > 60:
            raise ValueError(f'{month} report/annual cross-check too large: {diff} (RMB100m)')
        q_diff[month] = round(diff, 2)

    rows = []
    for month in expected:
        value = series[month]
        prior = f'{int(month[:4])-1:04d}-{month[5:7]}'
        yoy = (value / series[prior] - 1) * 100 if prior in series else None
        rows.append({
            'month': month, 'm2_100m': round(value, 2),
            'derived_yoy_pct': None if yoy is None else round(yoy, 6),
            'source_type': provenance[month]['source_type'],
            'source_url': provenance[month]['source_url'],
            'raw_sha256': provenance[month]['raw_sha256']
        })

    latest = rows[-1]
    lock = {
        'status': 'PASS_CONTINUOUS_OFFICIAL_V2_SOURCE',
        'candidate_version': contract['version'],
        'evidence_tier': 'RESEARCH_SOURCE_CANDIDATE',
        'built_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'core_modified': False,
        'legacy_exact_rerun': False,
        'start_month': expected[0], 'end_month': expected[-1], 'months': len(expected),
        'missing_months': [],
        'latest': latest,
        '2015_quarter_end_rounding_diff_100m': q_diff,
        'raw_source_files': [
            {'filename': name, 'bytes': len(raw), 'sha256': sha256_bytes(raw)}
            for name, raw in sorted(raw_files.items())
        ],
        'promotion_allowed': False,
        'next_gate': 'BUILD_GLOBAL_MONEY_V2_CANDIDATE_AND_COMPARE_TRANSFER',
        'note': 'This closes China source provenance for a NEW official-source candidate. It does not convert the missing historical v1.8b exact rerun into a PASS.'
    }

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    raw_root = OUT_ROOT / 'raw'
    raw_root.mkdir(exist_ok=True)
    for name, raw in raw_files.items():
        (raw_root / name).write_bytes(raw)
    with (OUT_ROOT / 'china_m2_100m.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['month','m2_100m','derived_yoy_pct','source_type','source_url','raw_sha256'])
        w.writeheader(); w.writerows(rows)
    (OUT_ROOT / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT_ROOT / 'manifest.lock.json').write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    AUDIT_PATH.parent.mkdir(exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return lock


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--validate-only', action='store_true')
    p.add_argument('--build-full', action='store_true')
    args = p.parse_args()
    if args.validate_only == args.build_full:
        print(json.dumps({'status':'ERROR','error':'Choose exactly one of --validate-only or --build-full','core_modified':False}, indent=2))
        return 2
    contract = load_contract()
    try:
        result = validate_sources(contract) if args.validate_only else build_full(contract)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'status':'FAIL','candidate_version':contract.get('version'),'core_modified':False,'error':str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
