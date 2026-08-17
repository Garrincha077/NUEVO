#!/usr/bin/env python3
import csv, io, json, re, urllib.parse, urllib.request, pathlib, datetime, html

OUT=pathlib.Path('audit'); OUT.mkdir(exist_ok=True)
UA='GMLI-v18b-frozen-rerun/1.0'
EXPECTED={'US':5.58,'CN':8.56,'EA':3.20,'JP':2.45,'GB':3.97,'CA':4.35,'AU':7.90}

def get(url,timeout=45,headers=None):
    h={'User-Agent':UA,'Accept':'text/csv,application/json,text/html,*/*'}; h.update(headers or {})
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
    return f'{m.group(1)}-{m.group(2)}' if m else None

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
    u='https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?'+urllib.parse.urlencode({'csv.x':'yes','Datefrom':'01/Jan/2014','Dateto':'31/Jul/2026','SeriesCodes':code,'CSVF':'TN','UsingCodes':'Y','VPD':'Y','VFD':'N'})
    raw=text(u,timeout=60)
    out={}
    for r in csv.reader(io.StringIO(raw)):
        if len(r)<2:continue
        m=ym(r[0])
        try:v=float(r[-1].replace(',',''))
        except:continue
        if m:out[m]=v
    return out, raw[:1500]

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
    u=f'https://www.rba.gov.au/statistics/tables/csv/{table}-data.csv'
    raw=get(u,timeout=60); s=None
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
    hr,col=hit; out={}
    fmts=('%d/%m/%Y','%d-%b-%Y','%Y-%m-%d')
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
    # Emit all columns whose metadata contains Broad Money / broad money, with series id, units and recent values.
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
    u='https://wzdig.pbc.gov.cn/search/pcRender?'+urllib.parse.urlencode({'pNo':'1','pageId':'c177a85bd02b4114bebebd210809f691','q':q,'sr':'date desc'})
    search=text(u,timeout=30); urls=re.findall(r'https?://(?:www\.)?pbc\.gov\.cn/[^"\'<> ]+/index\.html',html.unescape(search))
    for page in urls[:12]:
        try:t=strip_html(text(page,timeout=20))
        except:continue
        if f'{year}年{month}月' not in t or '金融统计' not in t:continue
        pats=[r'广义货币(?:增长)?\s*([0-9]+(?:\.[0-9]+)?)%',r'广义货币\s*\(M2\)[^。]{0,160}?同比增长\s*([0-9]+(?:\.[0-9]+)?)%',r'M2[^。]{0,160}?同比增长\s*([0-9]+(?:\.[0-9]+)?)%']
        for p in pats:
            m=re.search(p,t)
            if m:return {'yoy':float(m.group(1)),'url':page,'snippet':t[:1200]}
    return None

def main():
    res={'expected_may_2026_yoy':EXPECTED,'checks':{},'errors':{}}
    def run(k,fn):
        try:res['checks'][k]=fn()
        except Exception as e:res['errors'][k]=repr(e)

    run('US',lambda:(lambda x:{'may_yoy':yoy(x,'2026-05'),'level_may':x.get('2026-05'),'level_may_2025':x.get('2025-05'),'delta_vs_expected':None if yoy(x,'2026-05') is None else yoy(x,'2026-05')-EXPECTED['US']})(fred('M2SL')))
    run('EA',lambda:(lambda x:{'may_value':x.get('2026-05'),'n':len(x),'expected_growth':EXPECTED['EA']})(ecb('M.U2.Y.V.M20.X.1.U2.2300.Z01.E')))
    run('EA_growth_probe',lambda:{'M2_A':ecb('M.U2.Y.V.M20.X.I.U2.2300.Z01.A').get('2026-05'),'M2_E':ecb('M.U2.Y.V.M20.X.1.U2.2300.Z01.E').get('2026-05')})
    run('CA',lambda:(lambda x:{'may_yoy':yoy(x,'2026-05'),'may_level':x.get('2026-05'),'expected_growth':EXPECTED['CA'],'n':len(x)})(boc()))
    run('GB',lambda:(lambda z:{'may_yoy':yoy(z[0],'2026-05'),'apr_yoy':yoy(z[0],'2026-04'),'may_level':z[0].get('2026-05'),'apr_level':z[0].get('2026-04'),'n':len(z[0]),'head':z[1]})(boe()))
    run('JP_level',lambda:(lambda z:{'may_level':z[0].get('2026-05'),'n':len(z[0]),'status':z[1],'message':z[2]})(boj('MAM1NAM2M2MO')))
    run('JP_yoy',lambda:(lambda z:{'may_yoy':z[0].get('2026-05'),'n':len(z[0]),'status':z[1],'message':z[2]})(boj('MAM1YAM2M2MO')))
    run('CN_may',lambda:pbc_report(2026,5))
    rows,u=rba_csv('d3'); run('AU_D3',lambda:(lambda x:{'may_level':x.get('2026-05'),'jun_level':x.get('2026-06'),'may_raw_yoy':yoy(x,'2026-05'),'jun_raw_yoy':yoy(x,'2026-06'),'n':len(x),'source':u})(rba_series(rows,'DMABMS')))
    d1,u1=rba_csv('d1'); res['checks']['AU_D1_discovery']={'source':u1,'broad_money_candidates':discover_rba_d1(d1)}

    # May snapshot tolerance is only a source-definition audit, not the final empirical gate.
    checks=[]
    for k in ('US','CA','GB'):
        v=res['checks'].get(k,{}).get('may_yoy')
        if v is not None:checks.append(abs(v-EXPECTED[k])<=0.20)
    jv=res['checks'].get('JP_yoy',{}).get('may_yoy');
    if jv is not None:checks.append(abs(jv-EXPECTED['JP'])<=0.20)
    cv=(res['checks'].get('CN_may') or {}).get('yoy') if isinstance(res['checks'].get('CN_may'),dict) else None
    if cv is not None:checks.append(abs(cv-EXPECTED['CN'])<=0.20)
    res['source_snapshot_partial_pass']=bool(checks) and all(checks)
    pathlib.Path('audit/v18b-source-audit.json').write_text(json.dumps(res,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(res,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
