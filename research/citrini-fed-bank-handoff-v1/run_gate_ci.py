#!/usr/bin/env python3
import hashlib
import json
import math
import time
from datetime import datetime, timezone

import requests

import run_gate as rg

H41_DDP_URL = (
    "https://www.federalreserve.gov/datadownload/Output.aspx?"
    "filetype=csv&from=&label=include&lastobs=&layout=seriescolumn&rel=H41&"
    "series=17398fbf71bc6a47df150bceebdea2bc&to=&type=package"
)


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


def official_h41_total_assets():
    r = bounded_retry_get(H41_DDP_URL)
    raw = r.content
    rows = list(rg.csv.reader(rg.io.StringIO(raw.decode("utf-8-sig"))))
    header_idx = next((i for i, row in enumerate(rows) if row and row[0].strip().lower() == "time period"), None)
    if header_idx is None:
        raise RuntimeError("Federal Reserve H41 DDP Time Period header not found")
    header = [c.strip().strip('"') for c in rows[header_idx]]
    candidates = [i for i, c in enumerate(header) if c == "RESPPA_N.WW" or c.endswith("/RESPPA_N.WW")]
    if not candidates:
        raise RuntimeError(f"H41 total-assets RESPPA_N.WW missing from header: {header[:40]}")
    value_idx = candidates[0]
    data = []
    for row in rows[header_idx + 1 :]:
        if len(row) <= value_idx:
            continue
        d = rg.pd.to_datetime(row[0], errors="coerce")
        try:
            v = float(row[value_idx])
        except Exception:
            continue
        if rg.pd.notna(d) and rg.np.isfinite(v):
            data.append((rg.pd.Timestamp(d), v))
    df = rg.pd.DataFrame(data, columns=["date", "value"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    if len(df) < 1000:
        raise RuntimeError(f"Insufficient H41 total-assets history: {len(df)}")
    return df, raw


def official_build_handoff_states():
    bank_df, bank_raw = rg.parse_h8_ddp()
    fed_df, fed_raw = official_h41_total_assets()
    bank_m = rg.monthly_13w(bank_df, "bank")
    fed_m = rg.monthly_13w(fed_df, "fed")
    x = bank_m.merge(fed_m, on="signal_month", how="inner").sort_values("signal_month").reset_index(drop=True)
    if len(x) < 200:
        raise RuntimeError(f"Insufficient aligned Fed-bank monthly history: {len(x)}")
    x["state"] = [rg.state_name(f, b) for f, b in zip(x["fed_13w_pct"], x["bank_13w_pct"])]
    x["private_handoff"] = (x["state"] == "PRIVATE_HANDOFF").astype(int)
    x["decision_month"] = x["signal_month"].map(lambda m: rg.add_months(m, 1))
    meta = {
        "fed": {
            "source": "Federal Reserve H.4.1 Data Download Program",
            "series": "RESPPA_N.WW",
            "description": "Assets: Total Assets: Total assets: Wednesday level",
            "url": H41_DDP_URL,
            "sha256": hashlib.sha256(fed_raw).hexdigest(),
            "bytes": len(fed_raw),
            "weekly_rows": len(fed_df),
            "first_observation": fed_df["date"].min().date().isoformat(),
            "last_observation": fed_df["date"].max().date().isoformat(),
        },
        "bank": {
            "source": "Federal Reserve H8 Data Download Program",
            "series": "B1151NCBA",
            "url": rg.H8_DDP_URL,
            "sha256": hashlib.sha256(bank_raw).hexdigest(),
            "bytes": len(bank_raw),
            "weekly_rows": len(bank_df),
            "first_observation": bank_df["date"].min().date().isoformat(),
            "last_observation": bank_df["date"].max().date().isoformat(),
        },
        "aligned_months": len(x),
        "first_signal_month": str(x["signal_month"].min()),
        "last_signal_month": str(x["signal_month"].max()),
        "availability_lag_months": 1,
    }
    return x, meta


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
rg.build_handoff_states = official_build_handoff_states
rg.fetch_monthly_price = checked_in_price
rg.main()
