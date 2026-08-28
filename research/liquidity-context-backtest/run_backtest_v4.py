#!/usr/bin/env python3
import csv
import io
import time

import numpy as np
import pandas as pd
import requests

import run_backtest as rb

UA = {"User-Agent": "Mozilla/5.0 GMLI-liquidity-context-backtest/1.3"}
H8_DDP_URL = (
    "https://www.federalreserve.gov/datadownload/Output.aspx?"
    "filetype=csv&from=&label=include&lastobs=&layout=seriescolumn&rel=H8&"
    "series=fce2318909bacbc8ce268096deddd180&to=&type=package"
)


def _retry_get(url, params=None, timeout=120):
    last = None
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as exc:
            last = exc
            if attempt < 4:
                time.sleep(2 ** attempt)
    raise last


def get_text(url, params=None, timeout=120):
    return _retry_get(url, params=params, timeout=timeout).text


def get_json(url, params=None, timeout=120):
    return _retry_get(url, params=params, timeout=timeout).json()


def bank_signals_ddp():
    text = _retry_get(H8_DDP_URL, timeout=120).text
    rows = list(csv.reader(io.StringIO(text)))
    header_idx = next((i for i, row in enumerate(rows) if row and row[0].strip().lower() == "time period"), None)
    if header_idx is None:
        raise RuntimeError("Could not locate Federal Reserve DDP Time Period header")
    header = [c.strip().strip('"') for c in rows[header_idx]]
    try:
        value_idx = header.index("B1151NCBA")
    except ValueError as exc:
        raise RuntimeError(f"B1151NCBA missing from DDP header: {header[:50]}") from exc

    data = []
    for row in rows[header_idx + 1:]:
        if len(row) <= value_idx:
            continue
        d = pd.to_datetime(row[0], errors="coerce")
        try:
            v = float(row[value_idx])
        except Exception:
            continue
        if pd.notna(d) and np.isfinite(v):
            data.append((pd.Timestamp(d), v))
    df = pd.DataFrame(data, columns=["date", "value"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    if len(df) < 1000:
        raise RuntimeError(f"Insufficient H8 DDP history: {len(df)}")

    dates = df["date"].to_numpy(dtype="datetime64[ns]")
    vals = df["value"].to_numpy(float)

    def nearest_value(target):
        idx = np.searchsorted(dates, np.datetime64(target), side="right") - 1
        return np.nan if idx < 0 else vals[idx]

    monthly = df.groupby(df["date"].dt.to_period("M"), as_index=False).tail(1).copy()
    out_rows = []
    for r in monthly.itertuples(index=False):
        v13 = nearest_value(r.date - pd.Timedelta(days=91))
        v26 = nearest_value(r.date - pd.Timedelta(days=182))
        cur = rb.pct_change(r.value, v13)
        prior = rb.pct_change(v13, v26)
        impulse = cur - prior if np.isfinite(cur) and np.isfinite(prior) else np.nan
        if np.isfinite(impulse):
            out_rows.append({
                "indicator": "BANK_IMPULSE_13W_MINUS_PRIOR13W",
                "observation_date": r.date,
                "available_date": r.date + pd.Timedelta(days=14),
                "signal": impulse,
                "current_13w_pct": cur,
                "prior_13w_pct": prior,
            })
    out = pd.DataFrame(out_rows).sort_values("available_date").reset_index(drop=True)
    if len(out) < 100:
        raise RuntimeError(f"Insufficient bank monthly signals: {len(out)}")
    print(f"H8 source=Federal Reserve DDP B1151NCBA rows={len(df)} monthly_signals={len(out)}")
    return out


def yahoo_monthly(asset):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{asset}"
    params = {
        "period1": "631152000",  # 1990-01-01 UTC
        "period2": str(int(time.time()) + 86400),
        "interval": "1mo",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    payload = get_json(url, params=params, timeout=120)
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        err = (payload.get("chart") or {}).get("error")
        raise RuntimeError(f"Yahoo {asset} empty result: {err}")
    z = result[0]
    ts = z.get("timestamp") or []
    adj = (((z.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose") or [])
    close = (((z.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
    data = []
    for i, t in enumerate(ts):
        v = adj[i] if i < len(adj) and adj[i] is not None else close[i] if i < len(close) else None
        if v is None or not np.isfinite(float(v)):
            continue
        stamp = pd.to_datetime(int(t), unit="s", utc=True).tz_convert(None)
        period = stamp.to_period("M")
        # Monthly Yahoo bars can be timestamped near the start of their month; label them at
        # calendar month-end so the availability alignment cannot use that month's close early.
        date = period.to_timestamp(how="end").normalize()
        data.append((date, period, float(v)))
    df = pd.DataFrame(data, columns=["Date", "period", "Close"]).sort_values("Date").drop_duplicates("period", keep="last")
    # Drop the current potentially incomplete calendar month.
    current_period = pd.Timestamp.utcnow().tz_localize(None).to_period("M")
    df = df[df["period"] < current_period].reset_index(drop=True)
    if len(df) < 100:
        raise RuntimeError(f"Yahoo {asset} insufficient monthly adjusted history: {len(df)}")
    print(f"Market source=Yahoo adjusted monthly {asset} rows={len(df)} start={df.Date.min().date()} end={df.Date.max().date()}")
    return df[["Date", "period", "Close"]]


rb.get_text = get_text
rb.get_json = get_json
rb.bank_signals = bank_signals_ddp
rb.stooq_monthly = yahoo_monthly
rb.main()
