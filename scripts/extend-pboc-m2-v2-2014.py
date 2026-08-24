#!/usr/bin/env python3
"""Build the China V2 2014 comparable-base accounting seed.

2015+ accounting levels come from precise official PBoC Money Supply HTML tables.
To preserve the 2015-01 signal/train start without guessing a dead 2014 source,
this script constructs ONLY the prior-year comparable accounting base required
for 2015 from two official PBoC components for each month:

    implied_2014_base = precise_2015_level / (1 + published_2015_yoy/100)

The implied 2014 rows are ACCOUNTING_SEED_ONLY. They are not observed 2014 stock
values and are never described as recovered frozen bytes. No proxy source is used.
The script never modifies lib/state.js.
"""
import argparse
import csv
import importlib.util
import io
import json
import pathlib
import re
import sys
import urllib.parse
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / 'scripts' / 'build-pboc-m2-official-v2.py'
NOWCAST_PATH = ROOT / 'scripts' / 'refresh-money-nowcast.py'
CONTRACT_PATH = ROOT / 'research' / 'china-m2-official-v2-contract.json'
OUT_ROOT = ROOT / 'research' / 'china-m2-official-v2' / 'latest'
AUDIT_PATH = ROOT / 'audit' / 'china-m2-official-v2.json'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = load_module('pboc_v2_base', BASE_PATH)
nowcast = load_module('pboc_nowcast_parser', NOWCAST_PATH)


def load_contract():
    data = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    if data.get('start_month') != '2014-01':
        raise ValueError('Comparable-base seed requires contract start_month=2014-01')
    return data


PERIOD_END_TITLE = {
    3: '2015年一季度金融统计数据报告',
    6: '2015年上半年金融统计数据报告',
    9: '2015年前三季度金融统计数据报告',
    12: '2015年金融统计数据报告',
}


def pbc_search_url_for_query(query, page_no=1):
    params = urllib.parse.urlencode({
        'dr': 'true', 'pNo': str(page_no), 'pageId': nowcast.PBOC_SEARCH_PAGE_ID,
        'q': query, 'sr': 'score desc'
    })
    return nowcast.PBOC_SEARCH_BASE + '?' + params


def parse_2015_growth_article(text, month):
    clean = nowcast.strip_html(text).replace('（', '(').replace('）', ')').replace('％', '%').replace('，', ',')
    exact_title = f'2015年{month}月金融统计数据报告'
    allowed_titles = [exact_title]
    if month in PERIOD_END_TITLE:
        allowed_titles.append(PERIOD_END_TITLE[month])
    if not any(title in clean for title in allowed_titles) or '金融统计' not in clean:
        raise ValueError(f'PBoC report title/month mismatch for 2015-{month:02d}')
    if f'{month}月末' not in clean:
        raise ValueError(f'PBoC report body month mismatch for 2015-{month:02d}')
    patterns = [
        r'广义货币\s*\(?M2\)?\s*余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元[^。]{0,160}?同比增长\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%',
        r'M2[^。]{0,80}?余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元[^。]{0,160}?同比增长\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%'
    ]
    for pattern in patterns:
        m = re.search(pattern, clean, flags=re.I)
        if m:
            level, yoy = float(m.group(1)), float(m.group(2))
            if not (50 <= level <= 1000) or not (-20 <= yoy <= 30):
                raise ValueError(f'PBoC M2 sanity failure: level={level}, yoy={yoy}')
            return {'level_trn_cny': level, 'yoy_pct': yoy}
    raise ValueError('PBoC report found but M2 balance/YoY sentence was not parsed')


def discover_2015_report(month):
    exact_query = f'2015年{month}月金融统计数据报告'
    queries = [exact_query]
    period_query = PERIOD_END_TITLE.get(month)
    if period_query:
        queries.insert(0, period_query)
    errors, seen_urls = [], set()
    for query in queries:
        for page_no in range(1, 6):
            search_url = pbc_search_url_for_query(query, page_no)
            search_raw = nowcast.fetch_bytes(search_url, timeout=35, accept='text/html')
            for url in nowcast.central_pbc_urls(nowcast.decode_bytes(search_raw)):
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                try:
                    page_raw = nowcast.fetch_bytes(url, timeout=30, accept='text/html')
                    page_text = nowcast.decode_bytes(page_raw)
                    parsed = parse_2015_growth_article(page_text, month)
                    return {
                        'report_month': f'2015-{month:02d}', 'url': url, **parsed,
                        'search_url': search_url, 'search_query': query, 'search_page': page_no,
                        'article_sha256': nowcast.sha256_bytes(page_raw),
                        'title_mode': 'PERIOD_END' if period_query and period_query in nowcast.strip_html(page_text) else 'EXACT_MONTH'
                    }
                except Exception as exc:
                    errors.append(f'{url}: {str(exc)[:140]}')
    raise ValueError('PBoC 2015 candidates failed validation: ' + ' | '.join(errors[:10]))


def exact_2015_report(month):
    report = discover_2015_report(month)
    article_raw, article_meta = base.fetch_bytes(report['url'], timeout=40)
    parsed = parse_2015_growth_article(base.decode_bytes(article_raw), month)
    if abs(float(parsed['level_trn_cny']) - float(report['level_trn_cny'])) > 1e-9 or abs(float(parsed['yoy_pct']) - float(report['yoy_pct'])) > 1e-9:
        raise ValueError(f'2015-{month:02d} semantic refetch mismatch')
    return {
        'month': f'2015-{month:02d}', 'article_url': report['url'], 'article_raw': article_raw,
        'article_sha256': base.sha256_bytes(article_raw), 'article_http_status': article_meta.get('http_status'),
        'reported_level_trn_cny': float(parsed['level_trn_cny']), 'published_yoy_pct': float(parsed['yoy_pct']),
        'search_query': report['search_query'], 'search_page': report['search_page'], 'title_mode': report['title_mode']
    }


def build_seed(contract):
    base_contract = dict(contract); base_contract['start_month'] = '2015-01'; base.build_full(base_contract)
    csv_path = OUT_ROOT / 'china_m2_100m.csv'
    precision = {r['month']: float(r['m2_100m']) for r in csv.DictReader(io.StringIO(csv_path.read_text(encoding='utf-8')))}
    if not all(f'2015-{m:02d}' in precision for m in range(1, 13)):
        raise ValueError('Precision 2015 PBoC HTML history is incomplete')
    reports = [exact_2015_report(m) for m in range(1, 13)]
    seen_hashes, seeds, seed_manifest = {}, {}, []
    raw_root = OUT_ROOT / 'raw'; raw_root.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    for record in reports:
        if record['article_sha256'] in seen_hashes:
            raise ValueError(f'Duplicate PBoC article for {seen_hashes[record["article_sha256"]]} and {record["month"]}')
        seen_hashes[record['article_sha256']] = record['month']
        current_month, current_100m = record['month'], precision[record['month']]
        report_100m = record['reported_level_trn_cny'] * 10000.0
        if abs(current_100m - report_100m) > 60.0:
            raise ValueError(f'{current_month} precision HTML/report mismatch: {current_100m} vs {report_100m}')
        yoy = record['published_yoy_pct']; prior_month = f'2014-{current_month[5:7]}'
        implied = current_100m / (1.0 + yoy / 100.0); seeds[prior_month] = implied
        article_name = f'{current_month}-financial-statistics-growth.html'; (raw_root / article_name).write_bytes(record['article_raw'])
        seed_manifest.append({
            'seed_month': prior_month, 'source_month': current_month, 'implied_comparable_base_100m': round(implied, 6),
            'precision_current_level_100m': round(current_100m, 2), 'published_yoy_pct': yoy,
            'reported_level_trn_cny': record['reported_level_trn_cny'], 'article_url': record['article_url'],
            'article_sha256': record['article_sha256'], 'search_query': record['search_query'],
            'search_page': record['search_page'], 'title_mode': record['title_mode']
        })
    anchor = (contract.get('published_growth_anchor') or {}).get('2015-01_yoy_pct')
    if anchor is not None and abs(reports[0]['published_yoy_pct'] - float(anchor)) > 1e-9:
        raise ValueError('2015-01 growth anchor mismatch')
    provenance_path = OUT_ROOT / 'provenance.json'; provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    for item in seed_manifest:
        provenance[item['seed_month']] = {
            'source_type':'PBOC_IMPLIED_COMPARABLE_BASE_FROM_OFFICIAL_2015_LEVEL_AND_YOY','source_url':item['article_url'],
            'raw_file':f'raw/{item["source_month"]}-financial-statistics-growth.html','raw_sha256':item['article_sha256'],
            'retrieved_at':retrieved_at,'unit':'RMB 100 million','role':'ACCOUNTING_SEED_ONLY','observed_stock':False,
            'formula':'precise_2015_level / (1 + official_2015_yoy/100)','source_month':item['source_month'],'title_mode':item['title_mode']
        }
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    values = dict(precision); values.update(seeds); months = sorted(values)
    if months[0] != '2014-01' or not all(f'2014-{m:02d}' in values for m in range(1,13)):
        raise ValueError('Comparable-base seed incomplete')
    rows=[]
    for month in months:
        prior=f'{int(month[:4])-1:04d}-{month[5:7]}'; dy=(values[month]/values[prior]-1)*100 if prior in values else None; p=provenance[month]
        rows.append({'month':month,'m2_100m':round(values[month],6 if month.startswith('2014-') else 2),'derived_yoy_pct':None if dy is None else round(dy,6),'source_type':p['source_type'],'source_url':p['source_url'],'raw_sha256':p['raw_sha256']})
    report_yoy={r['month']:r['published_yoy_pct'] for r in reports}
    for row in rows:
        if row['month'].startswith('2015-') and abs(float(row['derived_yoy_pct'])-report_yoy[row['month']])>0.000001:
            raise ValueError(f'{row["month"]} derived YoY mismatch')
    with csv_path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['month','m2_100m','derived_yoy_pct','source_type','source_url','raw_sha256']); w.writeheader(); w.writerows(rows)
    manifest_path=OUT_ROOT/'manifest.lock.json'; manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.update({
        'status':'PASS_CONTINUOUS_OFFICIAL_V2_SOURCE','seed_status':'PASS_OFFICIAL_COMPARABLE_BASE_DERIVATION',
        'built_at':retrieved_at,'start_month':'2014-01','end_month':months[-1],'months':len(months),'missing_months':[],
        'historical_2014_extension':None,'comparable_base_seed_2014':{'status':'PASS_OFFICIAL_COMPONENT_DERIVATION','months':12,'role':'ACCOUNTING_SEED_ONLY','observed_stock':False,'formula':'implied_2014_base = precise_2015_level / (1 + published_2015_yoy/100)','sources':seed_manifest},
        'promotion_allowed':False,'next_gate':'REBUILD_GLOBAL_MONEY_V2_THEN_FIXED_TRANSMISSION_TRANSFER_TEST'
    })
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); AUDIT_PATH.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return manifest


def main():
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True); g.add_argument('--validate-only',action='store_true'); g.add_argument('--build-full',action='store_true'); args=p.parse_args(); contract=load_contract()
    try:
        result=build_seed(contract); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    except Exception as exc:
        print(json.dumps({'status':'FAIL','candidate_version':contract.get('version'),'core_modified':False,'legacy_exact_rerun':False,'error':str(exc)},ensure_ascii=False,indent=2)); return 1

if __name__=='__main__': sys.exit(main())
