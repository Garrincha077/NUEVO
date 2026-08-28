#!/usr/bin/env python3
import csv
import io
import time

import numpy as np
import pandas as pd
import requests

import run_backtest as rb

UA = {"User-Agent": "GMLI-liquidity-context-backtest/1.2"}
H8_DDP_URL = (
    "https://www.federalreserve.gov/datadownload/Output.aspx?"
    "filetype=csv&from=&label=include&lastobs=&layout=seriescolumn&rel=H8&"
    "series=fce2318909bacbc8ce268096deddd180&to=&type=package"
)


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
    return _retry_get(url, params=params, timeout=timeout).text


def get_json(url, params=None, timeout=120):
    return _retry_get(url, params=params, timeout=timeout).json()


def bank_signals_ddp():
    text = _retry_get(H8_DDP_URL, timeout=120).text
    rows = list(csv.reader(io.StringIO(text)))
    header_idx = None
    for i, row in enumerate(rows):
        if row and row[0].strip().lower() == "time period":
            header_idx = i
            break
    if header_idx is None:
        preview = " | ".join(",".join(r[:3]) for r in rows[:8])
        raise RuntimeError(f"Could not locate DDP Time Period header; preview={preview[:800]}")
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


rb.get_text = get_text
rb.get_json = get_json
rb.bank_signals = bank_signals_ddp
rb.main()
