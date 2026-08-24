#!/usr/bin/env python3
import argparse
import csv
import hashlib
import html
import io
import json
import pathlib
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / 'lib' / 'nowcast-state.js'
AUDIT_DIR = ROOT / 'audit'
AUDIT_DIR.mkdir(exist_ok=True)

PREFIX = 'export const MONEY_NOWCAST = '
SUFFIX = ';\n\nexport function summarizeNowcast()'
UA = 'GMLI-Research-Copilot/2.4 scheduled-refresh'
PBOC_SEARCH_BASE = 'https://wzdig.pbc.gov.cn/search/pcRender'
PBOC_SEARCH_PAGE_ID = 'c177a85bd02b4114bebebd210809f691'


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch_bytes(url, timeout=25, accept='*/*'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def decode_bytes(raw):
    for enc in ('utf-8-sig', 'utf-8', 'gb18030', 'cp1252', 'latin-1'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    raise ValueError('Unable to decode response')


def fetch_text(url, timeout=25, accept='*/*'):
    return decode_bytes(fetch_bytes(url, timeout, accept))


def strip_html(value):
    s = re.sub(r'<script[\s\S]*?</script>', ' ', str(value), flags=re.I)
    s = re.sub(r'<style[\s\S]*?</style>', ' ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = html.unescape(s)
    s = s.replace('\u3000', ' ').replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def load_state():
    text = STATE_PATH.read_text(encoding='utf-8')
    a = text.index(PREFIX) + len(PREFIX)
    b = text.index(SUFFIX)
    return text, json.loads(text[a:b])


def dump_state(original, state):
    a = original.index(PREFIX) + len(PREFIX)
    b = original.index(SUFFIX)
    payload = json.dumps(state, ensure_ascii=False, indent=2)
    STATE_PATH.write_text(original[:a] + payload + original[b:], encoding='utf-8')


def ym(date_text):
    s = str(date_text).replace('/', '-').strip()
    m = re.match(r'^(20\d{2})[-]?(0[1-9]|1[0-2])', s)
    return f'{m.group(1)}-{m.group(2)}' if m else None


def month_key(s):
    return tuple(map(int, s.split('-')))


def direction(latest, reference):
    d = latest - reference
    return ('ACCELERATING' if d > 0.25 else 'DECELERATING' if d < -0.25 else 'STABLE', round(d, 2))


def validate_block(old, new_date, new_yoy):
    if not new_date or not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', new_date):
        raise ValueError(f'Invalid month {new_date!r}')
    if month_key(new_date) < month_key(old['latest_date']):
        raise ValueError(f'Refusing date regression {old["latest_date"]} -> {new_date}')
    if not isinstance(new_yoy, (int, float)) or not (-20 <= new_yoy <= 30):
        raise ValueError(f'YoY sanity check failed: {new_yoy}')
    if new_date == old['latest_date'] and abs(new_yoy - float(old['latest_yoy_pct'])) > 5:
        raise ValueError(f'Same-month revision too large: {old["latest_yoy_pct"]} -> {new_yoy}')


def apply_block(state, key, new_date, new_yoy, source, source_url, extras=None):
    old = state['blocks'][key]
    validate_block(old, new_date, new_yoy)
    new_yoy = round(float(new_yoy), 4)
    ref = float(old['core_reference_yoy_pct'])
    d, delta = direction(new_yoy, ref)
    payload = {
        'latest_date': new_date,
        'latest_yoy_pct': new_yoy,
        'direction_vs_core': d,
        'delta_vs_core_pp': delta,
        'expanding_yoy': new_yoy > 0,
        'source': source,
        'source_url': source_url,
        'status': 'OK_VERIFIED_SCHEDULED'
    }
    if extras:
        payload.update(extras)
    changed = any(old.get(k) != v for k, v in payload.items())
    if changed:
        old.update(payload)
    return changed


def fred_csv(series_id, start):
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={urllib.parse.quote(series_id)}&cosd={start}'
    rows = []
    for row in csv.reader(io.StringIO(fetch_text(url, accept='text/csv'))):
        if len(row) < 2 or row[0].lower() in ('date', 'observation_date'):
            continue
        try:
            rows.append((row[0], float(row[1])))
        except ValueError:
            pass
    if not rows:
        raise ValueError(f'No FRED rows for {series_id}')
    return rows


def refresh_us(state):
    rows = fred_csv('M2SL', '2025-01-01')
    bym = {ym(d): v for d, v in rows if ym(d)}
    latest = max(bym, key=month_key)
    y, m = month_key(latest)
    prior = f'{y-1:04d}-{m:02d}'
    if prior not in bym:
        raise ValueError('US prior-year M2 level missing')
    yoy = (bym[latest] / bym[prior] - 1) * 100
    return apply_block(state, 'us', latest, yoy, 'Federal Reserve / FRED M2SL', 'https://fred.stlouisfed.org/series/M2SL')


def refresh_ea(state):
    key = 'M.U2.Y.V.M30.X.I.U2.2300.Z01.A'
    url = f'https://data-api.ecb.europa.eu/service/data/BSI/{key}?startPeriod=2026-02&format=csvdata'
    rows = list(csv.DictReader(io.StringIO(fetch_text(url, timeout=35, accept='text/csv'))))
    obs = []
    for r in rows:
        d = ym(r.get('TIME_PERIOD') or r.get('TIME_PERIOD_START') or r.get('TIME_PERIOD_END'))
        try:
            v = float(r.get('OBS_VALUE', ''))
        except ValueError:
            continue
        if d:
            obs.append((d, v))
    if not obs:
        raise ValueError('No ECB M3 observations')
    d, v = sorted(obs, key=lambda x: month_key(x[0]))[-1]
    return apply_block(state, 'euro_area', d, v, 'ECB Data Portal BSI', 'https://data.ecb.europa.eu/data/datasets/BSI/BSI.M.U2.Y.V.M30.X.I.U2.2300.Z01.A')


def refresh_japan(state):
    params = urllib.parse.urlencode({
        'format': 'json', 'lang': 'en', 'db': 'MD02',
        'startDate': '202602', 'code': 'MAM1YAM2M2MO'
    })
    url = 'https://www.stat-search.boj.or.jp/api/v1/getDataCode?' + params
    j = json.loads(fetch_text(url, timeout=30, accept='application/json'))
    if int(j.get('STATUS', 0)) != 200:
        raise ValueError(f'BOJ API status {j.get("STATUS")} {j.get("MESSAGE") or j.get("MESSAGEID")}')
    sets = j.get('RESULTSET') or []
    if not sets:
        raise ValueError('BOJ API empty RESULTSET')
    values = sets[0].get('VALUES') or {}
    dates = values.get('SURVEY_DATES') or []
    vals = values.get('VALUES') or []
    obs = []
    for d, v in zip(dates, vals):
        md = ym(str(d))
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if md:
            obs.append((md, fv))
    if not obs:
        raise ValueError('BOJ API no numeric M2 YoY observations')
    d, v = sorted(obs, key=lambda x: month_key(x[0]))[-1]
    return apply_block(state, 'japan', d, v, 'Bank of Japan Time-Series Data Search API', 'https://www.stat-search.boj.or.jp/api/v1/getDataCode')


def pbc_search_url(year, month):
    query = f'{year}年{month}月金融统计数据报告'
    params = urllib.parse.urlencode({
        'pNo': '1',
        'pageId': PBOC_SEARCH_PAGE_ID,
        'q': query,
        'sr': 'date desc'
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


def parse_pbc_m2_report(text, year, month):
    clean = strip_html(text).replace('（', '(').replace('）', ')').replace('％', '%').replace('，', ',')
    title_token = f'{year}年{month}月'
    if title_token not in clean or '金融统计' not in clean:
        raise ValueError(f'PBoC report title/month mismatch for {year}-{month:02d}')
    patterns = [
        r'广义货币\s*\(?M2\)?\s*余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元[^。]{0,160}?同比增长\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%',
        r'M2[^。]{0,80}?余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元[^。]{0,160}?同比增长\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%'
    ]
    for pattern in patterns:
        m = re.search(pattern, clean, flags=re.I)
        if m:
            level = float(m.group(1))
            yoy = float(m.group(2))
            if not (50 <= level <= 1000):
                raise ValueError(f'PBoC M2 level sanity check failed: {level} trillion yuan')
            if not (-20 <= yoy <= 30):
                raise ValueError(f'PBoC M2 YoY sanity check failed: {yoy}')
            return {'level_trn_cny': level, 'yoy_pct': yoy}
    raise ValueError('PBoC report found but M2 balance/YoY sentence was not parsed')


def find_pbc_report(year, month):
    search_url = pbc_search_url(year, month)
    search_raw = fetch_bytes(search_url, timeout=35, accept='text/html')
    search_text = decode_bytes(search_raw)
    candidates = central_pbc_urls(search_text)
    if not candidates:
        raise ValueError(f'No central PBoC report URL discovered for {year}-{month:02d}')
    errors = []
    for url in candidates[:12]:
        try:
            page_raw = fetch_bytes(url, timeout=30, accept='text/html')
            page_text = decode_bytes(page_raw)
            parsed = parse_pbc_m2_report(page_text, year, month)
            return {
                'report_month': f'{year}-{month:02d}',
                'url': url,
                **parsed,
                'search_url': search_url,
                'search_sha256': sha256_bytes(search_raw),
                'article_sha256': sha256_bytes(page_raw),
                'search_bytes': len(search_raw),
                'article_bytes': len(page_raw)
            }
        except Exception as exc:
            errors.append(f'{url}: {str(exc)[:180]}')
    raise ValueError('PBoC candidates failed validation: ' + ' | '.join(errors[:4]))


def latest_pbc_report(state):
    old = state['blocks']['china']
    now = datetime.now(timezone.utc)
    # A month-M report is normally released during M+1. Begin with the previous month.
    anchor_year = now.year
    anchor_month = now.month - 1
    if anchor_month == 0:
        anchor_month = 12
        anchor_year -= 1
    errors = []
    for back in range(0, 6):
        total = anchor_year * 12 + (anchor_month - 1) - back
        year, month0 = divmod(total, 12)
        month = month0 + 1
        try:
            report = find_pbc_report(year, month)
            validate_block(old, report['report_month'], report['yoy_pct'])
            return report
        except Exception as exc:
            errors.append(f'{year}-{month:02d}: {str(exc)[:250]}')
    raise ValueError('No current official PBoC Financial Statistics Report passed validation: ' + ' | '.join(errors))


def refresh_china(state):
    report = latest_pbc_report(state)
    changed = apply_block(
        state,
        'china',
        report['report_month'],
        report['yoy_pct'],
        'People\'s Bank of China Financial Statistics Report',
        report['url'],
        extras={
            'latest_level_trn_cny': report['level_trn_cny'],
            'source_article_sha256': report['article_sha256'],
            'source_search_sha256': report['search_sha256'],
            'note': 'Official central PBoC monthly Financial Statistics Report; scheduled parser validates report month, M2 balance and YoY before replacing last-good RESEARCH nowcast data.'
        }
    )
    return changed, report


def refresh_usd_translation(state):
    rows = fred_csv('DTWEXBGS', '2026-02-01')
    parsed = []
    for d, v in rows:
        try:
            parsed.append((datetime.fromisoformat(d).date(), v))
        except ValueError:
            pass
    if not parsed:
        raise ValueError('No broad-dollar observations')
    parsed.sort()
    ref_rows = [(d, v) for d, v in parsed if d.isoformat() <= '2026-02-28']
    if not ref_rows:
        raise ValueError('No broad-dollar reference observation')
    latest_d, latest_v = parsed[-1]
    ref_d, ref_v = ref_rows[-1]
    pct = (latest_v / ref_v - 1) * 100
    if not (-30 <= pct <= 30):
        raise ValueError(f'Dollar move sanity check failed: {pct}')
    pct_rounded = round(pct, 2)
    old = state['usd_translation']
    changed = latest_d.isoformat() != old.get('latest_verified') or pct_rounded != round(float(old.get('pct_change_since_core', 0)), 2)
    if changed:
        old.update({
            'status': 'RESEARCH_VERIFIED_SCHEDULED',
            'latest_verified': latest_d.isoformat(),
            'pct_change_since_core': pct_rounded,
            'translation': 'TAILWIND_WEAKER_USD' if pct_rounded < -1 else 'HEADWIND_STRONGER_USD' if pct_rounded > 1 else 'NEUTRAL',
            'source': 'Federal Reserve / FRED Broad Dollar Index DTWEXBGS',
            'source_url': 'https://fred.stlouisfed.org/series/DTWEXBGS'
        })
    return changed


def validate_china_only(state):
    report = latest_pbc_report(state)
    return {
        'status': 'PASS',
        'core_modified': False,
        'state_modified': False,
        'source': 'People\'s Bank of China Financial Statistics Report',
        'report': report
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate-china-only', action='store_true', help='Fetch and validate the latest official PBoC M2 report without modifying state.')
    args = parser.parse_args()

    original, state = load_state()
    if args.validate_china_only:
        print(json.dumps(validate_china_only(state), ensure_ascii=False, indent=2))
        return

    results = {}
    changed = False
    jobs = [
        ('us', refresh_us),
        ('euro_area', refresh_ea),
        ('japan', refresh_japan),
        ('usd_translation', refresh_usd_translation)
    ]
    for name, fn in jobs:
        try:
            did_change = fn(state)
            results[name] = {'status': 'PASS', 'changed': did_change}
            changed = changed or did_change
        except Exception as e:
            results[name] = {'status': 'PRESERVED_LAST_VERIFIED', 'error': str(e)[:1000]}

    try:
        china_changed, china_report = refresh_china(state)
        results['china'] = {
            'status': 'PASS',
            'changed': china_changed,
            'report_month': china_report['report_month'],
            'level_trn_cny': china_report['level_trn_cny'],
            'yoy_pct': china_report['yoy_pct'],
            'source_url': china_report['url'],
            'source_article_sha256': china_report['article_sha256'],
            'source_search_sha256': china_report['search_sha256']
        }
        changed = changed or china_changed
    except Exception as e:
        results['china'] = {'status': 'PRESERVED_LAST_VERIFIED', 'error': str(e)[:1500]}

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    audit = {'attempted_at': now, 'changed': changed, 'results': results}
    (AUDIT_DIR / 'money-refresh-result.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')

    if changed:
        state.setdefault('refresh', {})['last_verified_at'] = now
        state['refresh']['last_result'] = results
        dump_state(original, state)

    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
