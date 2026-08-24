#!/usr/bin/env python3
"""Build the versioned GMLI Global Money V2 headline candidate.

Purpose
-------
Replace only the China source leg with the new fully official PBoC V2 history
while reusing the documented seven-region production construction:

- regions: US, CN, EA, JP, GB, CA, AU
- prior-year USD money-level share weights
- local-money YoY + USD translation
- 1M publication lag
- rolling z: 120 calendar months, minimum 36, population ddof=0
- score: 50 + (50/3) * z

This is a RESEARCH / promotion-candidate builder. It never edits lib/state.js.
The historical v1.8b exact-rerun blocker remains a separate fact.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import pathlib
import re
import statistics
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHINA_CSV = ROOT / 'research' / 'china-m2-official-v2' / 'latest' / 'china_m2_100m.csv'
OUT_ROOT = ROOT / 'research' / 'global-money-v2' / 'latest'
AUDIT_PATH = ROOT / 'audit' / 'global-money-v2-headline.json'
UA = 'GMLI-Global-Money-V2/1.0 official-source-candidate'
START = '2014-01'

# May-2026 v1.8 bridge anchors. These validate conventions, not identity with
# the old China legacy series. Tolerances deliberately allow normal revisions
# and the source-version change while rejecting unit/FX-direction mistakes.
MAY_BRIDGE = {
    'month': '2026-05',
    'weights_pct': {'US':20.99,'CN':43.40,'EA':18.32,'JP':8.41,'GB':4.04,'CA':2.66,'AU':2.18},
    'local_yoy_pct': {'US':5.58,'CN':8.56,'EA':3.20,'JP':2.45,'GB':3.97,'CA':4.35,'AU':7.90},
    'fx_yoy_pct': {'US':0.0,'CN':6.13,'EA':3.61,'JP':-8.39,'GB':1.05,'CA':1.09,'AU':11.70},
    'gbm_usd_yoy_pct': 9.3258,
    'gbm_fxn_yoy_pct': 6.1275,
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch(url, accept='*/*', timeout=45):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if len(raw) < 50:
            raise ValueError(f'Implausibly small response: {len(raw)} bytes from {url}')
        return raw, {'url': url, 'final_url': r.geturl(), 'bytes': len(raw), 'sha256': sha256(raw), 'content_type': r.headers.get('Content-Type')}


def decode(raw):
    for enc in ('utf-8-sig','utf-8','cp1252','latin-1'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    raise ValueError('Unable to decode source bytes')


def ym(value):
    s = str(value or '').strip()
    pats = [
        r'^(20\d{2})-(0[1-9]|1[0-2])',
        r'^(20\d{2})/(0[1-9]|1[0-2])',
        r'^(0[1-9]|1[0-2])/(20\d{2})$',
        r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[- ](20\d{2})$',
    ]
    m = re.match(pats[0], s)
    if m: return f'{m.group(1)}-{m.group(2)}'
    m = re.match(pats[1], s)
    if m: return f'{m.group(1)}-{m.group(2)}'
    m = re.match(pats[2], s)
    if m: return f'{m.group(2)}-{m.group(1)}'
    m = re.match(pats[3], s, re.I)
    if m:
        mons = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
        return f'{int(m.group(2)):04d}-{mons[m.group(1).lower()]:02d}'
    return None


def prior_year(month):
    return f'{int(month[:4])-1:04d}-{month[5:7]}'


def next_month(month):
    y,m = map(int, month.split('-'))
    m += 1
    if m == 13: y,m = y+1,1
    return f'{y:04d}-{m:02d}'


def available_date(month):
    # frozen 1M publication lag represented conservatively as month-end M+1
    y,m = map(int, next_month(month).split('-'))
    import calendar
    return f'{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}'


def parse_simple_csv(raw, value_hint=None):
    rows = list(csv.reader(io.StringIO(decode(raw))))
    out = {}
    for row in rows:
        if len(row) < 2: continue
        date = None
        date_idx = None
        for i, cell in enumerate(row[:4]):
            md = ym(cell)
            if md:
                date, date_idx = md, i
                break
        if not date: continue
        candidates = []
        if value_hint:
            # handled elsewhere when a header can identify the exact column
            pass
        for i, cell in enumerate(row):
            if i == date_idx: continue
            s = str(cell).replace(',','').strip()
            try: v = float(s)
            except ValueError: continue
            candidates.append(v)
        if candidates:
            out[date] = candidates[-1]
    return out


def fred(series):
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={urllib.parse.quote(series)}&cosd=2014-01-01'
    raw, meta = fetch(url, 'text/csv')
    rows = list(csv.reader(io.StringIO(decode(raw))))
    out = {}
    for row in rows[1:]:
        if len(row) < 2: continue
        md = ym(row[0])
        try: v = float(row[1])
        except ValueError: continue
        if md: out[md] = v
    if not out: raise ValueError(f'No FRED data for {series}')
    return out, raw, meta


def china():
    if not CHINA_CSV.exists(): raise FileNotFoundError(CHINA_CSV)
    raw = CHINA_CSV.read_bytes()
    out = {}
    for row in csv.DictReader(io.StringIO(raw.decode('utf-8'))):
        out[row['month']] = float(row['m2_100m']) * 0.1  # 100m CNY -> bn CNY
    return out, raw, {'url': str(CHINA_CSV.relative_to(ROOT)), 'final_url': str(CHINA_CSV.relative_to(ROOT)), 'bytes':len(raw), 'sha256':sha256(raw), 'content_type':'text/csv'}


def ecb_m2():
    key = 'M.U2.Y.V.M20.X.1.U2.2300.Z01.E'
    url = f'https://data-api.ecb.europa.eu/service/data/BSI/{key}?startPeriod=2014-01&format=csvdata'
    raw, meta = fetch(url, 'text/csv', 60)
    rows = list(csv.DictReader(io.StringIO(decode(raw))))
    out = {}
    for r in rows:
        md = ym(r.get('TIME_PERIOD') or r.get('TIME_PERIOD_START') or r.get('TIME_PERIOD_END'))
        try: v = float(r.get('OBS_VALUE',''))
        except ValueError: continue
        if md: out[md] = v / 1000.0  # EUR million -> EUR bn
    if not out: raise ValueError('No ECB M2 level observations')
    return out, raw, meta


def boj_m2():
    params = urllib.parse.urlencode({'format':'json','lang':'en','db':'MD02','startDate':'201401','code':'MAM1NAM2M2MO'})
    url = 'https://www.stat-search.boj.or.jp/api/v1/getDataCode?' + params
    raw, meta = fetch(url, 'application/json', 60)
    j = json.loads(decode(raw))
    if int(j.get('STATUS',0)) != 200: raise ValueError(f'BOJ API status {j.get("STATUS")}: {j.get("MESSAGE") or j.get("MESSAGEID")}')
    sets = j.get('RESULTSET') or []
    if not sets: raise ValueError('BOJ empty RESULTSET')
    values = sets[0].get('VALUES') or {}
    dates = values.get('SURVEY_DATES') or []
    vals = values.get('VALUES') or []
    out = {}
    for d,v in zip(dates, vals):
        md = ym(str(d))
        try: fv = float(v)
        except (TypeError,ValueError): continue
        if md: out[md] = fv * 0.1  # 100m JPY -> bn JPY
    if not out: raise ValueError('No BOJ M2 level data')
    return out, raw, meta


def boe_m4():
    url = 'https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/2014&Dateto=now&SeriesCodes=LPMAUYN&UsingCodes=Y&CSVF=CT&VPD=Y&VFD=N'
    raw, meta = fetch(url, 'text/csv', 60)
    rows = list(csv.reader(io.StringIO(decode(raw))))
    out = {}
    # identify exact series column if present
    header_idx = col_idx = None
    for ri,row in enumerate(rows[:15]):
        for ci,cell in enumerate(row):
            if 'LPMAUYN' in str(cell): header_idx,col_idx = ri,ci
    for row in rows[(header_idx+1 if header_idx is not None else 0):]:
        if len(row) < 2: continue
        md = ym(row[0]) or (ym(row[1]) if len(row)>1 else None)
        if not md: continue
        idx = col_idx if col_idx is not None and col_idx < len(row) else len(row)-1
        try: v = float(str(row[idx]).replace(',','').strip())
        except ValueError: continue
        out[md] = v / 1000.0  # GBP million -> GBP bn
    if not out: raise ValueError('No BoE LPMAUYN observations')
    return out, raw, meta


def boc_m2():
    url = 'https://www.bankofcanada.ca/valet/observations/V41552796/csv?start_date=2014-01-01'
    raw, meta = fetch(url, 'text/csv', 60)
    text = decode(raw)
    rows = list(csv.reader(io.StringIO(text)))
    header_idx = col_idx = None
    for ri,row in enumerate(rows[:30]):
        for ci,cell in enumerate(row):
            if str(cell).strip() == 'V41552796': header_idx,col_idx = ri,ci
    out = {}
    for row in rows[(header_idx+1 if header_idx is not None else 0):]:
        if not row: continue
        md = ym(row[0])
        if not md: continue
        idx = col_idx if col_idx is not None and col_idx < len(row) else len(row)-1
        try: v = float(str(row[idx]).replace(',','').strip())
        except ValueError: continue
        out[md] = v / 1000.0  # CAD million -> CAD bn
    if not out: raise ValueError('No BoC V41552796 observations')
    return out, raw, meta


def rba_series(url, code):
    raw, meta = fetch(url, 'text/csv', 60)
    rows = list(csv.reader(io.StringIO(decode(raw))))
    col = None
    start_row = 0
    for ri,row in enumerate(rows[:40]):
        for ci,cell in enumerate(row):
            if str(cell).strip() == code:
                col, start_row = ci, ri+1
    if col is None: raise ValueError(f'RBA series code {code} not found')
    out = {}
    for row in rows[start_row:]:
        if len(row) <= col: continue
        md = None
        for cell in row[:3]:
            md = ym(cell)
            if md: break
        if not md: continue
        try: v = float(str(row[col]).replace(',','').strip())
        except ValueError: continue
        out[md] = v
    if not out: raise ValueError(f'No RBA observations for {code}')
    return out, raw, meta


def au():
    level, raw3, meta3 = rba_series('https://www.rba.gov.au/statistics/tables/csv/d3-data.csv','DMABMS')
    growth, raw1, meta1 = rba_series('https://www.rba.gov.au/statistics/tables/csv/d1-data.csv','DGFABM12')
    return level, growth, [(raw3,meta3),(raw1,meta1)]


def fx_sources():
    spec = {
        'CN': ('EXCHUS', True),
        'EA': ('EXUSEU', False),
        'JP': ('EXJPUS', True),
        'GB': ('EXUSUK', False),
        'CA': ('EXCAUS', True),
        'AU': ('EXUSAL', False),
    }
    out = {'US': {}}
    raws = []
    for region,(sid,invert) in spec.items():
        vals, raw, meta = fred(sid)
        conv = {}
        for m,v in vals.items():
            if v == 0: continue
            conv[m] = 1.0/v if invert else v  # USD per unit local currency
        out[region] = conv
        raws.append((raw,meta))
    return out, raws


def yoy(levels, month):
    p = prior_year(month)
    if month not in levels or p not in levels or levels[p] == 0: return None
    return (levels[month] / levels[p] - 1.0) * 100.0


def fx_yoy(fx, month):
    return yoy(fx, month)


def rolling_z(values, idx, window=120, min_n=36):
    start = max(0, idx-window+1)
    xs = [x for x in values[start:idx+1] if x is not None and math.isfinite(x)]
    if len(xs) < min_n: return None
    mean = sum(xs)/len(xs)
    var = sum((x-mean)**2 for x in xs)/len(xs)
    sd = math.sqrt(var)
    if sd == 0: return None
    return (values[idx]-mean)/sd


def score(z):
    return None if z is None else 50.0 + (50.0/3.0)*z


def build():
    sources = {}
    raw_records = []
    us,raw,meta = fred('M2SL'); sources['US']=us; raw_records.append(('us-m2sl.csv',raw,meta))
    cn,raw,meta = china(); sources['CN']=cn; raw_records.append(('cn-pboc-v2.csv',raw,meta))
    ea,raw,meta = ecb_m2(); sources['EA']=ea; raw_records.append(('ea-ecb-m2.csv',raw,meta))
    jp,raw,meta = boj_m2(); sources['JP']=jp; raw_records.append(('jp-boj-m2.json',raw,meta))
    gb,raw,meta = boe_m4(); sources['GB']=gb; raw_records.append(('gb-boe-m4.csv',raw,meta))
    ca,raw,meta = boc_m2(); sources['CA']=ca; raw_records.append(('ca-boc-m2.csv',raw,meta))
    au_level,au_growth,au_raws = au(); sources['AU']=au_level
    raw_records += [('au-rba-d3.csv',au_raws[0][0],au_raws[0][1]),('au-rba-d1.csv',au_raws[1][0],au_raws[1][1])]
    fx, fx_raws = fx_sources()
    for i,(raw,meta) in enumerate(fx_raws): raw_records.append((f'fx-{i+1}.csv',raw,meta))

    regions = ['US','CN','EA','JP','GB','CA','AU']
    # candidate months require current+prior-year local level and FX for every region
    possible = sorted(set.intersection(*[set(sources[r]) for r in regions]))
    months = []
    rows = []
    for month in possible:
        if month < '2015-01': continue
        p = prior_year(month)
        if any(p not in sources[r] for r in regions): continue
        if any(month not in fx[r] or p not in fx[r] for r in regions if r!='US'): continue
        local = {}
        fxy = {}
        usd_level_prior = {}
        for r in regions:
            local[r] = au_growth.get(month) if r == 'AU' else yoy(sources[r],month)
            if local[r] is None: break
            fxy[r] = 0.0 if r == 'US' else fx_yoy(fx[r],month)
            if fxy[r] is None: break
            prior_fx = 1.0 if r == 'US' else fx[r][p]
            usd_level_prior[r] = sources[r][p] * prior_fx
        if len(local) != 7 or len(fxy) != 7: continue
        total = sum(usd_level_prior.values())
        weights = {r:usd_level_prior[r]/total for r in regions}
        translated = {r:((1+local[r]/100.0)*(1+fxy[r]/100.0)-1)*100.0 for r in regions}
        gbm_fxn = sum(weights[r]*local[r] for r in regions)
        gbm_usd = sum(weights[r]*translated[r] for r in regions)
        months.append(month)
        rows.append({
            'month':month,
            'gbm_usd_yoy_pct':gbm_usd,
            'gbm_fxn_yoy_pct':gbm_fxn,
            'fx_effect_pp':gbm_usd-gbm_fxn,
            'weights':weights,
            'local_yoy':local,
            'fx_yoy':fxy,
            'usd_translated_yoy':translated,
        })

    if len(rows) < 36: raise ValueError(f'Insufficient full-coverage history: {len(rows)} months')
    usd_series=[r['gbm_usd_yoy_pct'] for r in rows]
    fxn_series=[r['gbm_fxn_yoy_pct'] for r in rows]
    for i,r in enumerate(rows):
        r['usd_z']=rolling_z(usd_series,i)
        r['fxn_z']=rolling_z(fxn_series,i)
        r['usd_score']=score(r['usd_z'])
        r['fxn_score']=score(r['fxn_z'])
        r['available_date']=available_date(r['month'])

    by_month={r['month']:r for r in rows}
    if MAY_BRIDGE['month'] not in by_month: raise ValueError('May-2026 regression month unavailable')
    may=by_month[MAY_BRIDGE['month']]
    reg={'status':'PASS','month':'2026-05','checks':[]}
    def check(label,actual,expected,tol):
        delta=actual-expected
        ok=abs(delta)<=tol
        reg['checks'].append({'label':label,'actual':round(actual,6),'expected':expected,'delta':round(delta,6),'tolerance':tol,'pass':ok})
        if not ok: reg['status']='FAIL'
    # Convention checks: wide enough for version/revision differences, tight enough to catch unit/direction errors.
    for r in regions:
        check(f'weight_{r}_pct',100*may['weights'][r],MAY_BRIDGE['weights_pct'][r],1.5)
        check(f'local_{r}_yoy_pct',may['local_yoy'][r],MAY_BRIDGE['local_yoy_pct'][r],1.0 if r=='CN' else 0.65)
        check(f'fx_{r}_yoy_pct',may['fx_yoy'][r],MAY_BRIDGE['fx_yoy_pct'][r],0.35)
    check('gbm_usd_yoy_pct',may['gbm_usd_yoy_pct'],MAY_BRIDGE['gbm_usd_yoy_pct'],1.0)
    check('gbm_fxn_yoy_pct',may['gbm_fxn_yoy_pct'],MAY_BRIDGE['gbm_fxn_yoy_pct'],0.7)
    if reg['status']!='PASS':
        failed=[x for x in reg['checks'] if not x['pass']]
        raise ValueError('May-2026 bridge convention regression failed: '+json.dumps(failed,ensure_ascii=False))

    # frozen 1M lag: as of current date, only rows whose available_date has passed are decision-eligible.
    today=datetime.now(timezone.utc).date().isoformat()
    eligible=[r for r in rows if r['available_date']<=today]
    latest=eligible[-1]
    preview=rows[-1]
    manifest={
        'status':'PASS_GLOBAL_MONEY_V2_HEADLINE',
        'candidate_version':'GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL',
        'evidence_tier':'RESEARCH_PROMOTION_CANDIDATE',
        'built_at':now_iso(),
        'core_modified':False,
        'legacy_exact_rerun':False,
        'methodology':{
            'regions':regions,'publication_lag_months':1,'weighting':'prior-year USD money-level share',
            'zscore':'rolling 120 calendar months, min 36, population ddof=0','score':'50 + (50/3)*z',
            'china_source':'PBOC_OFFICIAL_M2_V2'
        },
        'history':{'start_month':rows[0]['month'],'end_month':rows[-1]['month'],'full_coverage_months':len(rows)},
        'may_2026_bridge_regression':reg,
        'latest_eligible':serialize_row(latest),
        'latest_source_preview':serialize_row(preview),
        'promotion_allowed':False,
        'next_gate':'FIXED_TRANSMISSION_TRANSFER_TEST',
        'note':'This is a new versioned production-source candidate. It does not rewrite the historical v1.8b exact-rerun failure.'
    }
    return manifest, rows, raw_records


def serialize_row(r):
    return {
        'month':r['month'],'available_date':r['available_date'],
        'gbm_usd_yoy_pct':round(r['gbm_usd_yoy_pct'],6),'gbm_fxn_yoy_pct':round(r['gbm_fxn_yoy_pct'],6),'fx_effect_pp':round(r['fx_effect_pp'],6),
        'usd_z':None if r['usd_z'] is None else round(r['usd_z'],6),'usd_score':None if r['usd_score'] is None else round(r['usd_score'],4),
        'fxn_z':None if r['fxn_z'] is None else round(r['fxn_z'],6),'fxn_score':None if r['fxn_score'] is None else round(r['fxn_score'],4),
        'weights_pct':{k:round(100*v,4) for k,v in r['weights'].items()},
        'local_yoy_pct':{k:round(v,4) for k,v in r['local_yoy'].items()},
        'fx_yoy_pct':{k:round(v,4) for k,v in r['fx_yoy'].items()},
    }


def write_output(manifest,rows,raw_records):
    OUT_ROOT.mkdir(parents=True,exist_ok=True)
    raw_root=OUT_ROOT/'raw'; raw_root.mkdir(exist_ok=True)
    for name,raw,meta in raw_records: (raw_root/name).write_bytes(raw)
    with (OUT_ROOT/'global_money_v2.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['month','available_date','gbm_usd_yoy_pct','gbm_fxn_yoy_pct','fx_effect_pp','usd_z','usd_score','fxn_z','fxn_score']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:
            w.writerow({k:r.get(k) for k in fields})
    manifest['raw_sources']=[{'filename':f'raw/{name}','bytes':len(raw),'sha256':sha256(raw),'source_url':meta['url']} for name,raw,meta in raw_records]
    (OUT_ROOT/'manifest.lock.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    AUDIT_PATH.parent.mkdir(exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--validate-only',action='store_true')
    p.add_argument('--build-full',action='store_true')
    args=p.parse_args()
    if not (args.validate_only or args.build_full): p.error('choose --validate-only or --build-full')
    try:
        manifest,rows,raw_records=build()
        if args.build_full: write_output(manifest,rows,raw_records)
        print(json.dumps(manifest,ensure_ascii=False,indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'status':'FAIL','candidate_version':'GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL','core_modified':False,'error':str(exc)},ensure_ascii=False,indent=2))
        return 1

if __name__=='__main__':
    sys.exit(main())
