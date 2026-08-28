#!/usr/bin/env python3
import time
import requests

import run_gate as rg


def bounded_retry_get(url, params=None, timeout=120):
    last = None
    effective_timeout = min(float(timeout), 30.0)
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=rg.UA, timeout=effective_timeout)
            r.raise_for_status()
            return r
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise last


rg.retry_get = bounded_retry_get
rg.main()
