#!/usr/bin/env python3
"""One-time discovery helper for locking official PBoC 2015 Financial Statistics URLs.

Search ranking is used only to discover candidates. Every accepted URL is validated
semantically by exact/period title, requested month-end token, M2 balance and YoY.
The resulting month->URL map is intended to be committed as a static manifest;
production history must not depend on this helper.
"""
import importlib.util
import json
import pathlib
import re
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
NOWCAST_PATH = ROOT / 'scripts' / 'refresh-money-nowcast.py'

spec = importlib.util.spec_from_file_location('pboc_nowcast_parser', NOWCAST_PATH)
nowcast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nowcast)

PERIOD_END_TITLE = {
    3: '2015年一季度金融统计数据报告',
    6: '2015年上半年金融统计数据报告',
    9: '2015年前三季度金融统计数据报告',
    12: '2015年金融统计数据报告',
}


def search_url(query, page):
    return nowcast.PBOC_SEARCH_BASE + '?' + urllib.parse.urlencode({
        'dr': 'true', 'pNo': str(page), 'pageId': nowcast.PBOC_SEARCH_PAGE_ID,
        'q': query, 'sr': 'score desc'
    })


def parse_article(text, month):
    clean = nowcast.strip_html(text).replace('（','(').replace('）',')').replace('％','%').replace('，',',')
    titles = [f'2015年{month}月金融统计数据报告']
    if month in PERIOD_END_TITLE:
        titles.append(PERIOD_END_TITLE[month])
    if not any(t in clean for t in titles):
        raise ValueError('title mismatch')
    if f'{month}月末' not in clean:
        raise ValueError('body month mismatch')
    patterns = [
        r'广义货币\s*\(?M2\)?\s*余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元[^。]{0,160}?同比增长\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%',
        r'M2[^。]{0,80}?余额\s*([0-9]+(?:\.[0-9]+)?)\s*万亿元[^。]{0,160}?同比增长\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%'
    ]
    for pat in patterns:
        m = re.search(pat, clean, flags=re.I)
        if m:
            level, yoy = float(m.group(1)), float(m.group(2))
            if 50 <= level <= 1000 and -20 <= yoy <= 30:
                return level, yoy
    raise ValueError('M2 sentence mismatch')


def discover(month):
    queries = [f'2015年{month}月金融统计数据报告']
    if month in PERIOD_END_TITLE:
        queries.insert(0, PERIOD_END_TITLE[month])
    seen = set()
    for query in queries:
        for page in range(1, 9):
            s_url = search_url(query, page)
            raw = nowcast.fetch_bytes(s_url, timeout=35, accept='text/html')
            for url in nowcast.central_pbc_urls(nowcast.decode_bytes(raw)):
                if url in seen:
                    continue
                seen.add(url)
                try:
                    a_raw = nowcast.fetch_bytes(url, timeout=30, accept='text/html')
                    level, yoy = parse_article(nowcast.decode_bytes(a_raw), month)
                    return {
                        'month': f'2015-{month:02d}',
                        'url': url,
                        'level_trn_cny': level,
                        'yoy_pct': yoy,
                        'article_sha256': nowcast.sha256_bytes(a_raw),
                        'discovery_query': query,
                        'discovery_page': page,
                        'title_mode': 'PERIOD_END' if query == PERIOD_END_TITLE.get(month) else 'EXACT_MONTH'
                    }
                except Exception:
                    pass
    raise ValueError(f'No validated official PBoC URL for 2015-{month:02d}')


rows = [discover(m) for m in range(1, 13)]
print(json.dumps({
    'status': 'PASS_LOCKABLE_2015_PBOC_GROWTH_URLS',
    'count': len(rows),
    'urls': {r['month']: r['url'] for r in rows},
    'records': rows
}, ensure_ascii=False, indent=2))
