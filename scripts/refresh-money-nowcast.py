#!/usr/bin/env python3
import csv
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
UA = 'GMLI-Research-Copilot/2.3 scheduled-refresh'


def fetch_bytes(url, timeout=25, accept='*/*'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_text(url, timeout=25, accept='*/*'):
    raw = fetch_bytes(url, timeout, accept)
    for enc in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    raise ValueError('Unable to decode response')


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


def apply_block(state, key, new_date, new_yoy, source, source_url):
    old = state['blocks'][key]
    validate_block(old, new_date, new_yoy)
    ref = float(old['core_reference_yoy_pct'])
    d, delta = direction(float(new_yoy), ref)
    changed = new_date != old['latest_date'] or abs(float(new_yoy) - float(old['latest_yoy_pct'])) > 1e-6
    if changed:
        old.update({
            'latest_date': new_date,
            'latest_yoy_pct': round(float(new_yoy), 4),
            'direction_vs_core': d,
            'delta_vs_core_pp': delta,
            'expanding_yoy': float(new_yoy) > 0,
            'source': source,
            'source_url': source_url,
            'status': 'OK_VERIFIED_SCHEDULED'
        })
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
    # Official BOJ API launched in 2026. MD02\'MAM1YAM2M2MO is M2 YoY.
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
    old = state['usd_translation']
    changed = latest_d.isoformat() != old.get('latest_verified') or abs(pct - float(old.get('pct_change_since_core', 0))) > 1e-6
    if changed:
        old.update({
            'status': 'RESEARCH_VERIFIED_SCHEDULED',
            'latest_verified': latest_d.isoformat(),
            'pct_change_since_core': round(pct, 2),
            'translation': 'TAILWIND_WEAKER_USD' if pct < -1 else 'HEADWIND_STRONGER_USD' if pct > 1 else 'NEUTRAL',
            'source': 'Federal Reserve / FRED Broad Dollar Index DTWEXBGS',
            'source_url': 'https://fred.stlouisfed.org/series/DTWEXBGS'
        })
    return changed


def main():
    original, state = load_state()
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
            results[name] = {'status': 'PRESERVED_LAST_VERIFIED', 'error': str(e)[:500]}

    # China remains explicitly preserved until a stable official machine-readable parser is validated.
    results['china'] = {'status': 'PRESERVED_LAST_VERIFIED', 'reason': 'Stable official PBoC current-value machine parser not yet validated.'}

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    audit = {'attempted_at': now, 'changed': changed, 'results': results}
    (AUDIT_DIR / 'money-refresh-result.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')

    if changed:
        state.setdefault('refresh', {})['last_verified_at'] = now
        state['refresh']['last_result'] = results
        dump_state(original, state)

    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
