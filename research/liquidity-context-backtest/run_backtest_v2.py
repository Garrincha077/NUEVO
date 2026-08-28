#!/usr/bin/env python3
import time
import requests

import run_backtest as rb

UA = {"User-Agent": "GMLI-liquidity-context-backtest/1.1"}


def _retry_get(url, params=None, timeout=120):
    last = None
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as exc:
            last = exc
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise last


def get_text(url, params=None, timeout=120):
    # Limit the H.8 transfer to the period relevant for ETF/MSPD overlap.
    if "fredgraph.csv" in url and "TLAACBW027SBOG" in url and "cosd=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}cosd=1999-01-01"
    return _retry_get(url, params=params, timeout=timeout).text


def get_json(url, params=None, timeout=120):
    return _retry_get(url, params=params, timeout=timeout).json()


rb.get_text = get_text
rb.get_json = get_json
rb.main()
