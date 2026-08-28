#!/usr/bin/env python3
import hashlib
import json
import math
import time
from datetime import datetime, timezone

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


def checked_in_price(asset):
    path = rg.ROOT / "research" / "global-money-v2" / "transfer" / "latest" / "raw" / f"{asset}-yahoo-monthly.json"
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    z = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not z:
        raise RuntimeError(f"Checked-in Yahoo {asset} result missing")
    ts = z.get("timestamp") or []
    adj = (((z.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose") or [])
    close = (((z.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    prices = {}
    for i, t in enumerate(ts):
        v = adj[i] if i < len(adj) and adj[i] is not None else close[i] if i < len(close) else None
        if v is None or not math.isfinite(float(v)) or float(v) <= 0:
            continue
        month = datetime.fromtimestamp(int(t), tz=timezone.utc).strftime("%Y-%m")
        if month == current_month:
            continue
        prices[month] = float(v)
    if len(prices) < 150:
        raise RuntimeError(f"Checked-in Yahoo {asset} history too short: {len(prices)}")
    meta = {
        "source": "Yahoo Finance monthly adjusted close — checked-in promoted transmission snapshot",
        "file": str(path.relative_to(rg.ROOT)),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "months": len(prices),
        "first_month": min(prices),
        "last_month": max(prices),
        "current_incomplete_month_excluded": current_month,
    }
    return prices, meta


rg.retry_get = bounded_retry_get
rg.fetch_monthly_price = checked_in_price
rg.main()
