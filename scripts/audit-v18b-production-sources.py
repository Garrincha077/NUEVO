#!/usr/bin/env python3
import csv, io, json, re, urllib.parse, urllib.request, pathlib, datetime, html

OUT=pathlib.Path('audit'); OUT.mkdir(exist_ok=True)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36 GMLI-v18b-audit'
EXPECTED={'US':5.58,'CN':8.56,'EA':3.20,'JP':2.45,'GB':3.97,'CA':4.35,'AU':7.90}

def get(url,timeout=45,headers=None):
    h={'User-Agent':UA,'Accept':'text/csv,application/json,text/html,*/*','Referer':'https://www.bankofengland.co.uk/'}; h.update(headers or {})
    req=urllib.request.Request(url,headers=h)
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()

def text(url,**kw):
    raw=get(url,**kw)
    for e in ('utf-8-sig','utf-8','cp1252','latin-1'):
        try:return raw.decode(e)
        except UnicodeDecodeError:pass
    raise ValueError('decode')

def ym(s):
    s=str(s or '').strip().replace('/','-')
    m=re.search(r'(20\d{2})[-]?(0[1-9]|1[0-2])',s)
    if m:return f'{m.group(1)}-{m.group(2)}'
    for f in ('%d %b %y','%d-%b-%Y','%d/%m/%Y'):
        try:
            d=datetime.datetime.strptime(str(s).strip(),f);return f'{d.year:04d}-{d.month:02d}'
        except:pass
    return None

def fred(id,start='2014-01-01'):
    u=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={urllib.parse.quote(id)}&cosd={start}'
    rows={}
    for r in csv.reader(io.StringIO(text(u))):
        if len(r)<2:continue
        m=ym(r[0])
        try:v=float(r[1])
        except:continue
        if m:rows[m]=v
    return rows

def yoy(levels,m):
    y,mo=map(int,m.split('-')); p=f'{y-1:04d}-{mo:02d}'
    if m in levels and p in levels and levels[p]!=0:return (levels[m]/levels[p]-1)*100

def ecb(key,start='2014-01'):
    u=f'https://data-api.ecb.europa.eu/service/data/BSI/{key}?startPeriod={start}&format=csvdata'
    rows=list(csv.DictReader(io.StringIO(text(u,timeout=60,headers={'Accept':'text/csv'}))))
    out={}
    for r in rows:
        m=ym(r.get('TIME_PERIOD') or r.get('TIME_PERIOD_START') or r.get('TIME_PERIOD_END'))
        try:v=float(r.get('OBS_VALUE',''))
        except:continue
        if m:out[m]=v
    return out

def boc(series='V41552796'):
    u=f'https://www.bankofcanada.ca/valet/observations/{series}/json?start_date=2014-01-01'
    j=json.loads(text(u,timeout=60,headers={'Accept':'application/json'})); out={}
    for r in j.get('observations',[]):
        m=ym(r.get('d')); cell=r.get(series,{})
        try:v=float(cell.get('v'))
        except:continue
        if m:out[m]=v
    return out

def boe(code='LPMAUYN'):
    qs={'csv.x':'yes','Datefrom':'01/Jan/2014','Dateto':'31/Jul/2026','SeriesCodes':code,'CSVF':'TN','UsingCodes':'Y','VPD':'Y','VFD':'N'}
    urls=[
      'https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?'+urllib.parse.urlencode(qs),
      'https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp?'+urllib.parse.urlencode({**qs,'CSVF':'TT','DAT':'RNG','FD':'1','FM':'Jan','FY':'2014','TD':'31','TM':'Jul','TY':'2026','html.x':'66','html.y':'26'})
    ]
    errors=[]
    for u in urls:
        try:raw=text(u,timeout=60)
        except Exception as e:errors.append(repr(e));continue
        out={}
        for r in csv.reader(io.StringIO(raw)):
            if len(r)<2:continue
            m=ym(r[0])
            try:v=float(r[-1].replace(',',''))
            except:continue
            if m:out[m]=v
        if out:return out,raw[:1500],u,errors
    raise RuntimeError('BoE endpoints failed: '+repr(errors))

def boj(code):
    params=urllib.parse.urlencode({'format':'json','lang':'en','db':'MD02','startDate':'201401','code':code})
    u='https://www.stat-search.boj.or.jp/api/v1/getDataCode?'+params
    j=json.loads(text(u,timeout=60,headers={'Accept':'application/json'})); out={}
    for rs in j.get('RESULTSET') or []:
        vals=rs.get('VALUES') or {}; ds=vals.get('SURVEY_DATES') or []; vs=vals.get('VALUES') or []
        for d,v in zip(ds,vs):
            m=ym(d)
            try:fv=float(v)
            except:continue
            if m:out[m]=fv
    return out,j.get('STATUS'),j.get('MESSAGE') or j.get('MESSAGEID')

def rba_csv(table):
    u=f'https://www.rba.gov.au/statistics/tables/csv/{table}-data.csv'; raw=get(u,timeout=60); s=None
    for e in ('utf-8-sig','utf-8','cp1252','latin-1'):
        try:s=raw.decode(e);break
        except:pass
    return list(csv.reader(io.StringIO(s))),u

def rba_series(rows,series_id):
    hit=None
    for ri,row in enumerate(rows):
        for ci,c in enumerate(row):
            if c.strip()==series_id:hit=(ri,ci);break
        if hit:break
    if not hit:return {}
    hr,col=hit; out={}; fmts=('%d/%m/%Y','%d-%b-%Y','%Y-%m-%d')
    for row in rows[hr+1:]:
        if len(row)<=col:continue
        m=None
        for c in row[:3]:
            for f in fmts:
                try:d=datetime.datetime.strptime(c.strip(),f);m=f'{d.year:04d}-{d.month:02d}';break
                except:pass
            if m:break
        if not m:continue
        try:v=float(row[col].replace(',',''))
        except:continue
        out[m]=v
    return out

def discover_rba_d1(rows):
    sr=None
    for i,row in enumerate(rows):
        if row and row[0].strip()=='Series ID':sr=i;break
    if sr is None:return []
    ids=rows[sr]; hits=[]
    for ci in range(1,len(ids)):
        meta=' | '.join((rows[r][ci] if ci<len(rows[r]) else '') for r in range(max(0,sr-10),sr+1))
        if re.search(r'broad\s*money',meta,re.I):
            sid=ids[ci].strip(); vals=rba_series(rows,sid)
            hits.append({'column':ci,'series_id':sid,'metadata':meta,'may_2026':vals.get('2026-05'),'jun_2026':vals.get('2026-06'),'n':len(vals)})
    return hits

def strip_html(s):
    s=re.sub(r'<script[\s\S]*?</script>',' ',s,flags=re.I);s=re.sub(r'<style[\s\S]*?</style>',' ',s,flags=re.I);s=re.sub(r'<[^>]+>',' ',s);return re.sub(r'\s+',' ',html.unescape(s)).strip()

def pbc_report(year,month):
    q=f'{year}年{month}月金融统计数据报告'
    search_url='https://wzdig.pbc.gov.cn/search/pcRender?'+urllib.parse.urlencode({'pNo':'1','pageId':'c177a85bd02b4114bebebd210809f691','q':q,'sr':'date desc'})
    search=text(search_url,timeout=35); decoded=html.unescape(search)
    candidates=[]
    candidates += re.findall(r'https?://(?:www\.)?pbc\.gov\.cn/[^"\'<> ]+/index\.html',decoded)
    for href in re.findall(r'(?:href|url)=["\']([^"\']+index\.html[^"\']*)',decoded,re.I):
        candidates.append(urllib.parse.urljoin('https://www.pbc.gov.cn/',href))
    for href in re.findall(r'["\'](/[^"\']+index\.html)["\']',decoded):
        candidates.append(urllib.parse.urljoin('https://www.pbc.gov.cn/',href))
    seen=[]
    for x in candidates:
        x=x.replace('http://','https://')
        if x not in seen:seen.append(x)
    for page in seen[:25]:
        try:t=strip_html(text(page,timeout=25))
        except:continue
        if f'{year}年{month}月' not in t or ('金融统计' not in t and '货币' not in t):continue
        pats=[r'广义货币(?:增长)?\s*([0-9]+(?:\.[0-9]+)?)%',r'广义货币\s*\(M2\)[^。]{0,200}?同比增长\s*([0-9]+(?:\.[0-9]+)?)%',r'M2[^。]{0,200}?同比增长\s*([0-9]+(?:\.[0-9]+)?)%']
        for p in pats:
            m=re.search(p,t)
            if m:return {'yoy':float(m.group(1)),'url':page,'candidate_count':len(seen),'snippet':t[:1200]}
    return {'yoy':None,'search_url':search_url,'candidate_count':len(seen),'search_head':strip_html(decoded)[:1200]}

def main():
    res={'expected_may_2026_yoy':EXPECTED,'checks':{},'errors':{}}
    def run(k,fn):
        try:res['checks'][k]=fn()
        except Exception as e:res['errors'][k]=repr(e)
    run('US',lambda:(lambda x:{'may_yoy':yoy(x,'2026-05'),'level_may':x.get('2026-05'),'level_may_2025':x.get('2025-05')})(fred('M2SL')))
    run('EA',lambda:(lambda x:{'may_yoy_level_derived':yoy(x,'2026-05'),'may_level':x.get('2026-05'),'may_2025_level':x.get('2025-05'),'n':len(x)})(ecb('M.U2.Y.V.M20.X.1.U2.2300.Z01.E')))
    run('CA',lambda:(lambda x:{'may_yoy':yoy(x,'2026-05'),'may_level':x.get('2026-05'),'n':len(x)})(boc()))
    run('GB',lambda:(lambda z:{'may_yoy':yoy(z[0],'2026-05'),'apr_yoy':yoy(z[0],'2026-04'),'may_level':z[0].get('2026-05'),'apr_level':z[0].get('2026-04'),'apr_2025_level':z[0].get('2025-04'),'n':len(z[0]),'endpoint':z[2],'prior_errors':z[3],'head':z[1]})(boe()))
    run('JP',lambda:(lambda z:{'may_yoy_level_derived':yoy(z[0],'2026-05'),'may_level':z[0].get('2026-05'),'may_2025_level':z[0].get('2025-05'),'n':len(z[0]),'status':z[1]})(boj('MAM1NAM2M2MO')))
    run('JP_published_yoy',lambda:(lambda z:{'may_yoy':z[0].get('2026-05'),'n':len(z[0]),'status':z[1]})(boj('MAM1YAM2M2MO')))
    run('CN_may',lambda:pbc_report(2026,5))
    rows,u=rba_csv('d3'); run('AU_D3',lambda:(lambda x:{'may_level':x.get('2026-05'),'jun_level':x.get('2026-06'),'may_raw_yoy':yoy(x,'2026-05'),'jun_raw_yoy':yoy(x,'2026-06'),'n':len(x),'source':u})(rba_series(rows,'DMABMS')))
    d1,u1=rba_csv('d1'); res['checks']['AU_D1_discovery']={'source':u1,'broad_money_candidates':discover_rba_d1(d1)}
    values={
      'US':res['checks'].get('US',{}).get('may_yoy'),
      'EA':res['checks'].get('EA',{}).get('may_yoy_level_derived'),
      'CA':res['checks'].get('CA',{}).get('may_yoy'),
      'GB':res['checks'].get('GB',{}).get('may_yoy') or res['checks'].get('GB',{}).get('apr_yoy'),
      'JP':res['checks'].get('JP',{}).get('may_yoy_level_derived'),
      'CN':res['checks'].get('CN_may',{}).get('yoy') if isinstance(res['checks'].get('CN_may'),dict) else None,
      'AU':next((x.get('may_2026') for x in res['checks'].get('AU_D1_discovery',{}).get('broad_money_candidates',[]) if x.get('series_id')=='DGFABM12'),None)
    }
    res['snapshot_values']=values
    res['snapshot_deltas']={k:(None if values[k] is None else values[k]-EXPECTED[k]) for k in EXPECTED}
    known=[abs(res['snapshot_deltas'][k])<=0.25 for k in EXPECTED if res['snapshot_deltas'][k] is not None]
    res['source_snapshot_partial_pass']=bool(known) and all(known)
    res['known_snapshot_blocks']=sum(v is not None for v in values.values())
    pathlib.Path('audit/v18b-source-audit.json').write_text(json.dumps(res,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(res,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
