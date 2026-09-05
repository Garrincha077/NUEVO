#!/usr/bin/env python3
import argparse
import calendar
import csv
import hashlib
import io
import json
import statistics
import sys
import urllib.request
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'research' / 'cftc-positioning' / 'latest'
USER_AGENT = 'GMLI/2.5 (+https://github.com/Garrincha077/NUEVO)'
SOURCE_TEMPLATES = {
    'tff': 'https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip',
    'disagg': 'https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip',
}
ALL_KEYS = ['SPY','QQQ','IWM','GLD','SLV','DBC','USO','CPER','DBA','TLT','IEF','FXY','HYG','VNQ','EEM','VEA','BTC']


def month_buffer_start(today: date) -> date:
    # Preserve the existing CFTC source lookback: three years plus one month of buffer.
    year = today.year - 3
    month = today.month - 1
    if month == 0:
        year -= 1
        month = 12
    day = min(today.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': USER_AGENT,
            'Accept': 'application/zip,application/octet-stream,*/*',
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        if getattr(resp, 'status', 200) != 200:
            raise RuntimeError(f'CFTC source HTTP {getattr(resp, "status", "?")}: {url}')
        return resp.read()


def numeric(value):
    if value is None:
        return None
    s = str(value).strip().replace(',', '')
    if not s or s == '.':
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_date(row, kind):
    candidates = []
    if kind == 'disagg':
        candidates.extend([
            row.get('As_of_Date_Form_YYYY-MM-DD'),
            row.get('Report_Date_as_YYYY_MM_DD'),
        ])
    else:
        candidates.extend([
            row.get('Report_Date_as_MM_DD_YYYY'),
            row.get('Report_Date_as_YYYY_MM_DD'),
        ])
    candidates.append(row.get('As_of_Date_In_Form_YYMMDD'))
    for raw in candidates:
        s = str(raw or '').strip()
        if not s:
            continue
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%y%m%d'):
            try:
                return datetime.strptime(s, fmt).date().isoformat()
            except ValueError:
                pass
    return None


def normalized_row(row):
    return {str(k or '').strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def parse_zip(blob: bytes, kind: str, source_url: str):
    sha = hashlib.sha256(blob).hexdigest()
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = [n for n in zf.namelist() if not n.endswith('/')]
        text_names = [n for n in names if n.lower().endswith(('.txt', '.csv'))]
        if not text_names:
            raise RuntimeError(f'No text/CSV member in {source_url}')
        inner = sorted(text_names, key=lambda n: (len(n), n))[0]
        raw = zf.read(inner)
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('latin-1')
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for original in reader:
        row = normalized_row(original)
        d = parse_date(row, kind)
        market = str(row.get('Market_and_Exchange_Names') or '').strip()
        oi = numeric(row.get('Open_Interest_All'))
        if kind == 'tff':
            long_v = numeric(row.get('Lev_Money_Positions_Long_All'))
            short_v = numeric(row.get('Lev_Money_Positions_Short_All'))
        else:
            long_v = numeric(row.get('M_Money_Positions_Long_All'))
            short_v = numeric(row.get('M_Money_Positions_Short_All'))
        if d and market and oi is not None and oi > 0 and long_v is not None and short_v is not None:
            rows.append({'date': d, 'market': market, 'oi': oi, 'long': long_v, 'short': short_v})
    if not rows:
        raise RuntimeError(f'No usable {kind} rows parsed from {source_url} / {inner}')
    return rows, {
        'kind': kind,
        'url': source_url,
        'sha256': sha,
        'zip_bytes': len(blob),
        'member': inner,
        'member_bytes': len(raw),
        'usable_rows': len(rows),
    }


def contains_any(text, terms):
    s = str(text or '').upper()
    return any(term.upper() in s for term in terms)


def aggregate_by_date(rows, terms):
    grouped = {}
    for row in rows:
        if not contains_any(row['market'], terms):
            continue
        x = grouped.setdefault(row['date'], {'oi': 0.0, 'long': 0.0, 'short': 0.0})
        x['oi'] += row['oi']
        x['long'] += row['long']
        x['short'] += row['short']
    out = []
    for d in sorted(grouped):
        x = grouped[d]
        if x['oi'] > 0:
            out.append({'date': d, 'value': (x['long'] - x['short']) / x['oi']})
    return out


def percentile_rank(values, current):
    vals = sorted(v for v in values if isinstance(v, (int, float)))
    if not vals:
        return None
    return 100.0 * sum(v <= current for v in vals) / len(vals)


def summarize(series, label, source):
    if not series:
        return {
            'available': False, 'pass': False, 'crowded': False, 'label': label,
            'source': source, 'evidence_tier': 'RESEARCH', 'role': 'ENTRY_QUALITY_ONLY',
            'error': 'No matching CFTC rows',
        }
    vals = [x['value'] for x in series]
    cur = series[-1]
    pct = percentile_rank(vals, cur['value'])
    mu = statistics.fmean(vals)
    sd = statistics.stdev(vals) if len(vals) >= 2 else None
    z = (cur['value'] - mu) / sd if sd and sd > 0 else None
    return {
        'available': True,
        'pass': pct is not None and pct <= 25,
        'crowded': pct is not None and pct >= 75,
        'label': label,
        'as_of': cur['date'],
        'net_spec_pct_oi': round(100 * cur['value'], 2),
        'percentile_3y': None if pct is None else round(pct, 1),
        'z_3y': None if z is None else round(z, 2),
        'evidence_tier': 'RESEARCH',
        'role': 'ENTRY_QUALITY_ONLY',
        'source': source,
        'rule': '<=25th percentile contrarian-friendly; >=75th crowded',
    }


def component(rows, terms, label):
    return summarize(
        aggregate_by_date(rows, terms),
        label,
        'CFTC official Historical Compressed Disaggregated Futures Only / Managed Money',
    )


def composite(components, label, source, min_components=2):
    available = [x for x in components if x.get('available') and isinstance(x.get('percentile_3y'), (int, float))]
    pct = statistics.fmean(x['percentile_3y'] for x in available) if available else None
    dates = sorted(x.get('as_of') for x in available if x.get('as_of'))
    return {
        'available': len(available) >= min_components,
        'pass': pct is not None and pct <= 25,
        'crowded': pct is not None and pct >= 75,
        'label': label,
        'as_of': dates[-1] if dates else None,
        'percentile_3y': None if pct is None else round(pct, 1),
        'components': components,
        'evidence_tier': 'RESEARCH',
        'role': 'ENTRY_QUALITY_ONLY',
        'source': source,
        'rule': '<=25th percentile contrarian; >=75th crowded',
    }


def build(today: date):
    start = month_buffer_start(today)
    years = list(range(start.year, today.year + 1))
    rows = {'tff': [], 'disagg': []}
    source_manifest = []
    for kind, template in SOURCE_TEMPLATES.items():
        for year in years:
            url = template.format(year=year)
            blob = fetch_bytes(url)
            parsed, audit = parse_zip(blob, kind, url)
            rows[kind].extend(x for x in parsed if x['date'] >= start.isoformat())
            source_manifest.append(audit)

    tff = rows['tff']
    dis = rows['disagg']
    assets = {}
    tff_source = 'CFTC official Historical Compressed TFF Futures Only / Leveraged Money'
    assets['SPY'] = summarize(aggregate_by_date(tff, ['S&P 500','E-MINI S&P','MICRO E-MINI S&P']), 'S&P 500 leveraged money', tff_source)
    assets['QQQ'] = summarize(aggregate_by_date(tff, ['NASDAQ-100','NASDAQ 100','E-MINI NASDAQ','MICRO E-MINI NASDAQ']), 'Nasdaq-100 leveraged money', tff_source)
    assets['IWM'] = summarize(aggregate_by_date(tff, ['RUSSELL 2000','E-MINI RUSSELL','MICRO E-MINI RUSSELL']), 'Russell 2000 leveraged money', tff_source)
    assets['TLT'] = summarize(aggregate_by_date(tff, ['10-YEAR U.S. TREASURY','10 YEAR U.S. TREASURY','U.S. TREASURY BOND','TREASURY BONDS','ULTRA U.S. TREASURY']), 'US long-duration Treasury leveraged money proxy', tff_source)
    assets['IEF'] = summarize(aggregate_by_date(tff, ['5-YEAR U.S. TREASURY','5 YEAR U.S. TREASURY','10-YEAR U.S. TREASURY','10 YEAR U.S. TREASURY']), 'US intermediate Treasury leveraged money proxy', tff_source)
    assets['FXY'] = summarize(aggregate_by_date(tff, ['JAPANESE YEN','YEN']), 'Japanese Yen leveraged money', tff_source)

    assets['GLD'] = component(dis, ['GOLD'], 'Gold managed money')
    assets['SLV'] = component(dis, ['SILVER'], 'Silver managed money')
    assets['USO'] = component(dis, ['CRUDE OIL','WTI'], 'WTI crude managed money')
    assets['CPER'] = component(dis, ['COPPER'], 'Copper managed money')

    crude = component(dis, ['CRUDE OIL','WTI'], 'Crude')
    copper = component(dis, ['COPPER'], 'Copper')
    corn = component(dis, ['CORN'], 'Corn')
    wheat = component(dis, ['WHEAT'], 'Wheat')
    assets['DBC'] = composite(
        [crude, copper, corn, wheat],
        'Broad commodity managed-money proxy',
        'CFTC official Historical Compressed / crude-copper-corn-wheat percentile average',
        2,
    )

    soy = component(dis, ['SOYBEAN'], 'Soybeans')
    sugar = component(dis, ['SUGAR'], 'Sugar')
    coffee = component(dis, ['COFFEE'], 'Coffee')
    assets['DBA'] = composite(
        [corn, wheat, soy, sugar, coffee],
        'Broad agriculture managed-money proxy',
        'CFTC official Historical Compressed / corn-wheat-soy-sugar-coffee percentile average',
        3,
    )

    for key in ['HYG','VNQ','EEM','VEA','BTC']:
        assets[key] = {
            'available': False, 'pass': False, 'crowded': False,
            'evidence_tier': 'RESEARCH', 'role': 'ENTRY_QUALITY_ONLY', 'source': 'none',
            'note': 'No sufficiently direct asset-specific CFTC mapping in current GMLI.',
        }

    dates = sorted(x.get('as_of') for x in assets.values() if x.get('as_of'))
    latest = dates[-1] if dates else None
    if not latest:
        raise RuntimeError('No CFTC report date survived the refresh')
    age_days = (today - datetime.strptime(latest, '%Y-%m-%d').date()).days
    if age_days < 0 or age_days > 14:
        raise RuntimeError(f'CFTC latest report is outside freshness guard: {latest} ({age_days}d)')
    missing_core = [k for k in ['SPY','QQQ','GLD','DBC'] if not assets.get(k, {}).get('available')]
    if missing_core:
        raise RuntimeError(f'Direct/core CFTC mappings unavailable after refresh: {missing_core}')

    refreshed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    result = {
        'status': 'PASS_CFTC_POSITIONING_REFRESH',
        'as_of': refreshed_at,
        'refreshed_at': refreshed_at,
        'latest_report_date': latest,
        'latest_report_age_days': age_days,
        'window_start': start.isoformat(),
        'methodology': 'Net speculative position / open interest; existing 3Y percentile semantics with one-month source buffer; futures-only. Direct mappings unchanged; broad baskets retain transparent component averages.',
        'source_contract': 'CFTC_OFFICIAL_HISTORICAL_COMPRESSED_FUTURES_ONLY',
        'evidence_tier': 'RESEARCH',
        'role': 'ENTRY_QUALITY_ONLY',
        'assets': assets,
    }
    manifest = {
        'status': 'PASS_CFTC_POSITIONING_SOURCE_GUARDS',
        'source_contract': result['source_contract'],
        'refreshed_at': refreshed_at,
        'window_start': start.isoformat(),
        'latest_report_date': latest,
        'latest_report_age_days': age_days,
        'years': years,
        'sources': source_manifest,
        'core_mapping_guard': 'PASS_SPY_QQQ_GLD_DBC',
        'methodology_changed': False,
        'scoring_effect': 'NONE',
        'automatic_weight_change': 0,
    }
    return result, manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    today = datetime.now(timezone.utc).date()
    result, manifest = build(today)
    if args.apply:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / 'positioning.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        (OUT_DIR / 'manifest.lock.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': result['status'],
        'source_guard': manifest['status'],
        'latest_report_date': result['latest_report_date'],
        'latest_report_age_days': result['latest_report_age_days'],
        'window_start': result['window_start'],
        'core_mapping_guard': manifest['core_mapping_guard'],
        'applied': args.apply,
        'methodology_changed': False,
        'scoring_effect': 'NONE',
        'automatic_weight_change': 0,
    }, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({'status': 'FAIL_CFTC_POSITIONING_REFRESH', 'error': str(exc)}), file=sys.stderr)
        sys.exit(1)
