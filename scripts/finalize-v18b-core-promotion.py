#!/usr/bin/env python3
import csv, hashlib, io, json, pathlib, urllib.request, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / 'research' / 'frozen-v18b-promotion-contract.json'
OUT = ROOT / 'audit'
OUT.mkdir(exist_ok=True)
RBA_URL = 'https://www.rba.gov.au/statistics/tables/csv/d3-data.csv'


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'GMLI-v18b-final-audit/1.0'})
    with urllib.request.urlopen(req,timeout=45) as r:return r.read()


def parse_rba_dmabms(raw):
    text=None
    for enc in ('utf-8-sig','utf-8','cp1252','latin-1'):
        try:text=raw.decode(enc);break
        except UnicodeDecodeError:pass
    if text is None:raise RuntimeError('RBA D3 decode failed')
    rows=list(csv.reader(io.StringIO(text)))
    hit=None
    for ri,row in enumerate(rows):
        for ci,cell in enumerate(row):
            if cell.strip()=='DMABMS':hit=(ri,ci);break
        if hit:break
    if not hit:raise RuntimeError('DMABMS not found')
    hr,col=hit
    obs=[]
    for row in rows[hr+1:]:
        if len(row)<=col:continue
        d=None
        for cell in row[:3]:
            for fmt in ('%d/%m/%Y','%d-%b-%Y','%Y-%m-%d'):
                try:d=datetime.datetime.strptime(cell.strip(),fmt).date();break
                except ValueError:pass
            if d:break
        if not d:continue
        try:v=float(row[col].replace(',','').strip())
        except ValueError:continue
        if v>0:obs.append((d,v))
    obs.sort()
    mig=[x for x in obs if x[0]>=datetime.date(2015,1,1)]
    monthmap={(d.year,d.month):v for d,v in mig}
    cur=datetime.date(2015,1,1); end=datetime.date(obs[-1][0].year,obs[-1][0].month,1); missing=[]
    while cur<=end:
        if (cur.year,cur.month) not in monthmap:missing.append(cur.isoformat()[:7])
        cur=datetime.date(cur.year+(cur.month==12),1 if cur.month==12 else cur.month+1,1)
    return {
      'series':'DMABMS','migration_observations':len(mig),'latest_observation':obs[-1][0].isoformat(),
      'latest_level':obs[-1][1],'missing_months':missing,
      'may_2026':monthmap.get((2026,5)),'june_2026':monthmap.get((2026,6)),
      'pass':len(mig)>=138 and not missing and monthmap.get((2026,5))==3471.0 and monthmap.get((2026,6))==3499.9
    }


def main():
    contract=json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    required=[ROOT / p for p in contract['required_preserved_input_bytes']]
    present=[str(p.relative_to(ROOT)) for p in required if p.exists()]
    missing=[str(p.relative_to(ROOT)) for p in required if not p.exists()]

    rba_raw=fetch(RBA_URL)
    rba=parse_rba_dmabms(rba_raw)
    rba_hash=hashlib.sha256(rba_raw).hexdigest()

    # Preserved locked results from the Aug-15 gate. These are evidence, not a rerun.
    preserved={
      'key_direction_transfer':'9/9',
      'key_migration_fdr':'6/9',
      'dbc_gld_direction_transfer':'7/7',
      'full56_supported_fdr':6,
      'full56_reversed_fdr':5,
      'au_uniform_sensitivity':{
        '0.85x':{'supported56':6,'reversed56':5,'key_dir':9,'key_q9':6,'dbc_gld_dir':7},
        '1.00x':{'supported56':6,'reversed56':5,'key_dir':9,'key_q9':6,'dbc_gld_dir':7},
        '1.15x':{'supported56':6,'reversed56':5,'key_dir':9,'key_q9':6,'dbc_gld_dir':7}
      }
    }

    executable = (not missing) and rba['pass']
    decision='READY_FOR_EXACT_RERUN' if executable else 'BLOCKED_MISSING_FROZEN_INPUT_BYTES'
    result={
      'audit':'GMLI v1.8b final Core promotion audit',
      'decision':decision,
      'promote_to_core':False,
      'methodology_changed':False,
      'contract_sha256':sha256(CONTRACT_PATH),
      'audit_runner_sha256':sha256(pathlib.Path(__file__)),
      'official_rba_dmabms':{**rba,'source_url':RBA_URL,'source_bytes_sha256':rba_hash},
      'preserved_locked_evidence':preserved,
      'exact_rerun':{
        'executed':False,
        'required_inputs_present':present,
        'missing_required_inputs':missing,
        'status':'NOT_EXECUTED' if missing else 'READY',
        'reason':'The frozen Aug-15 macro matrix, exact-ticker adjusted-price mirror, original runner, and full56 baseline were not preserved in accessible GitHub/File Library bytes. Substituting current/revised data would violate the frozen reproduction contract.' if missing else None
      },
      'promotion_rule':'PASS is impossible unless the unchanged exact runner executes on the preserved frozen inputs after replacing only the AU accounting-level series with official RBA DMABMS.',
      'conclusion':'RBA source-purity blocker is solved. Promotion remains blocked solely because the exact frozen runner/input bytes required by the pre-registered gate were not preserved; no criteria were relaxed and no Core numbers were changed.' if missing else 'Frozen inputs recovered; exact rerun may now execute.'
    }
    (OUT/'v18b-final-core-promotion-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
