#!/usr/bin/env python3
import io
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy import stats

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)

BANK_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TLAACBW027SBOG"
TREASURY_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/debt/mspd/mspd_table_1"
ASSETS = ["SPY", "QQQ", "GLD", "DBC"]
HORIZONS = [3, 6, 12]
UA = {"User-Agent": "GMLI-liquidity-context-backtest/1.0"}


def get_text(url, params=None, timeout=45):
    r = requests.get(url, params=params, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.text


def get_json(url, params=None, timeout=45):
    r = requests.get(url, params=params, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.json()


def pct_change(a, b):
    if not np.isfinite(a) or not np.isfinite(b) or b == 0:
        return np.nan
    return (a / b - 1.0) * 100.0


def bank_signals():
    text = get_text(BANK_URL)
    df = pd.read_csv(io.StringIO(text))
    date_col = df.columns[0]
    val_col = df.columns[1]
    df = df.rename(columns={date_col: "date", val_col: "value"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().sort_values("date").reset_index(drop=True)
    if len(df) < 200:
        raise RuntimeError(f"Insufficient bank history: {len(df)}")

    dates = df["date"].to_numpy(dtype="datetime64[ns]")
    vals = df["value"].to_numpy(float)

    def nearest_value(target):
        idx = np.searchsorted(dates, np.datetime64(target), side="right") - 1
        if idx < 0:
            return np.nan
        return vals[idx]

    monthly = df.groupby(df["date"].dt.to_period("M"), as_index=False).tail(1).copy()
    rows = []
    for r in monthly.itertuples(index=False):
        t13 = r.date - pd.Timedelta(days=91)
        t26 = r.date - pd.Timedelta(days=182)
        v13 = nearest_value(t13)
        v26 = nearest_value(t26)
        cur = pct_change(r.value, v13)
        prior = pct_change(v13, v26)
        impulse = cur - prior if np.isfinite(cur) and np.isfinite(prior) else np.nan
        if np.isfinite(impulse):
            rows.append({
                "indicator": "BANK_IMPULSE_13W_MINUS_PRIOR13W",
                "observation_date": r.date,
                "available_date": r.date + pd.Timedelta(days=14),
                "signal": impulse,
                "current_13w_pct": cur,
                "prior_13w_pct": prior,
            })
    out = pd.DataFrame(rows).sort_values("available_date").reset_index(drop=True)
    if len(out) < 100:
        raise RuntimeError(f"Insufficient bank monthly signals: {len(out)}")
    return out


def treasury_class(label):
    x = str(label or "").strip().lower()
    if x == "bills" or x.startswith("treasury bills"):
        return "bills"
    if x == "notes" or x.startswith("treasury notes"):
        return "notes"
    if x == "bonds" or x.startswith("treasury bonds"):
        return "bonds"
    if "inflation-protected" in x:
        return "tips"
    if "floating rate" in x:
        return "frns"
    return None


def fetch_treasury_rows():
    page_size = 10000
    page = 1
    all_rows = []
    while True:
        params = {
            "fields": "record_date,security_type_desc,security_class_desc,debt_held_public_mil_amt",
            "filter": "security_type_desc:eq:Marketable",
            "sort": "record_date",
            "format": "json",
            "page[number]": page,
            "page[size]": page_size,
        }
        payload = get_json(TREASURY_URL, params=params)
        data = payload.get("data") or []
        all_rows.extend(data)
        meta = payload.get("meta") or {}
        total_pages = int(meta.get("total-pages") or meta.get("total_pages") or 1)
        if page >= total_pages or not data:
            break
        page += 1
        if page > 50:
            raise RuntimeError("Treasury pagination guard exceeded")
    if len(all_rows) < 500:
        # Fallback without API filter because historical labeling can vary.
        page = 1
        all_rows = []
        while True:
            params = {
                "fields": "record_date,security_type_desc,security_class_desc,debt_held_public_mil_amt",
                "sort": "record_date",
                "format": "json",
                "page[number]": page,
                "page[size]": page_size,
            }
            payload = get_json(TREASURY_URL, params=params)
            data = payload.get("data") or []
            all_rows.extend(data)
            meta = payload.get("meta") or {}
            total_pages = int(meta.get("total-pages") or meta.get("total_pages") or 1)
            if page >= total_pages or not data:
                break
            page += 1
            if page > 50:
                raise RuntimeError("Treasury fallback pagination guard exceeded")
    return all_rows


def treasury_signals():
    raw = fetch_treasury_rows()
    df = pd.DataFrame(raw)
    if df.empty:
        raise RuntimeError("Treasury API returned no rows")
    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")
    df["value"] = pd.to_numeric(df["debt_held_public_mil_amt"], errors="coerce")
    df["class"] = df["security_class_desc"].map(treasury_class)
    df["marketable"] = df["security_type_desc"].astype(str).str.strip().str.lower().eq("marketable")
    df = df[df["marketable"] & df["class"].notna() & df["record_date"].notna() & df["value"].notna()].copy()
    if df.empty:
        raise RuntimeError("Treasury API returned no usable marketable rows")

    piv = df.pivot_table(index="record_date", columns="class", values="value", aggfunc="sum", fill_value=0).sort_index()
    for c in ["bills", "notes", "bonds", "tips", "frns"]:
        if c not in piv.columns:
            piv[c] = 0.0
    denom = piv[["bills", "notes", "bonds", "tips", "frns"]].sum(axis=1)
    piv = piv[denom > 0].copy()
    piv["short_share"] = (piv["bills"] + piv["frns"]) / denom.loc[piv.index] * 100.0
    piv["period"] = piv.index.to_period("M")
    # One observation per month; MSPD record dates are normally month-end.
    piv = piv.reset_index().sort_values("record_date").groupby("period", as_index=False).tail(1).set_index("period")

    rows = []
    for period, r in piv.iterrows():
        prior_period = period - 3
        if prior_period not in piv.index:
            continue
        prior_share = float(piv.loc[prior_period, "short_share"])
        signal = float(r["short_share"] - prior_share)
        rows.append({
            "indicator": "TREASURY_SHORT_FLOATING_SHARE_3M_DELTA",
            "observation_date": pd.Timestamp(r["record_date"]),
            "available_date": pd.Timestamp(r["record_date"]) + pd.Timedelta(days=7),
            "signal": signal,
            "short_share_pct": float(r["short_share"]),
            "prior_3m_short_share_pct": prior_share,
        })
    out = pd.DataFrame(rows).sort_values("available_date").reset_index(drop=True)
    if len(out) < 100:
        raise RuntimeError(f"Insufficient Treasury monthly signals: {len(out)}")
    return out


def stooq_monthly(asset):
    url = f"https://stooq.com/q/d/l/?s={asset.lower()}.us&i=m&d1=19900101&d2=20261231"
    text = get_text(url)
    if "No data" in text or len(text.splitlines()) < 10:
        raise RuntimeError(f"No Stooq monthly data for {asset}")
    df = pd.read_csv(io.StringIO(text))
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna(subset=["Date", "Close"]).sort_values("Date").drop_duplicates("Date")
    if len(df) < 100:
        raise RuntimeError(f"Insufficient Stooq history for {asset}: {len(df)}")
    df["period"] = df["Date"].dt.to_period("M")
    return df[["Date", "period", "Close"]].reset_index(drop=True)


def align_and_forward(signal_df, price_df, horizon):
    prices = price_df.sort_values("Date").reset_index(drop=True)
    periods = prices["period"].tolist()
    period_to_close = dict(zip(periods, prices["Close"].astype(float)))
    period_to_date = dict(zip(periods, prices["Date"]))

    rows = []
    for s in signal_df.itertuples(index=False):
        available = pd.Timestamp(s.available_date)
        # First actual monthly price date at or after availability.
        idx = prices["Date"].searchsorted(available, side="left")
        if idx >= len(prices):
            continue
        base_period = periods[idx]
        target_period = base_period + horizon
        if target_period not in period_to_close:
            continue
        base_close = float(prices.iloc[idx]["Close"])
        target_close = float(period_to_close[target_period])
        if not (base_close > 0 and target_close > 0):
            continue
        rows.append({
            "available_date": available,
            "base_date": pd.Timestamp(prices.iloc[idx]["Date"]),
            "target_date": pd.Timestamp(period_to_date[target_period]),
            "signal": float(s.signal),
            "forward_return_pct": (target_close / base_close - 1.0) * 100.0,
        })
    return pd.DataFrame(rows).sort_values("available_date").drop_duplicates("base_date", keep="last").reset_index(drop=True)


def safe_corr(x, y, kind="pearson"):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 8 or np.nanstd(x) == 0 or np.nanstd(y) == 0:
        return np.nan, np.nan
    if kind == "pearson":
        r = stats.pearsonr(x, y)
    else:
        r = stats.spearmanr(x, y)
    return float(r.statistic), float(r.pvalue)


def bh_qvalues(pvals):
    arr = np.asarray(pvals, dtype=float)
    q = np.full(len(arr), np.nan)
    valid = np.where(np.isfinite(arr))[0]
    if len(valid) == 0:
        return q
    order = valid[np.argsort(arr[valid])]
    m = len(order)
    running = 1.0
    for rank_rev, idx in enumerate(order[::-1], start=1):
        rank = m - rank_rev + 1
        raw = arr[idx] * m / rank
        running = min(running, raw)
        q[idx] = min(1.0, running)
    return q


def evaluate(indicator_name, signal_df, asset, price_df, horizon):
    aligned = align_and_forward(signal_df, price_df, horizon)
    n = len(aligned)
    if n < 30:
        return None
    split = max(20, int(math.floor(n * 0.70)))
    split = min(split, n - 10)
    train = aligned.iloc[:split]
    oos = aligned.iloc[split:]

    train_p, _ = safe_corr(train["signal"], train["forward_return_pct"], "pearson")
    oos_p, oos_pval = safe_corr(oos["signal"], oos["forward_return_pct"], "pearson")
    full_p, full_pval = safe_corr(aligned["signal"], aligned["forward_return_pct"], "pearson")
    oos_s, _ = safe_corr(oos["signal"], oos["forward_return_pct"], "spearman")
    full_s, _ = safe_corr(aligned["signal"], aligned["forward_return_pct"], "spearman")

    pos = oos[oos["signal"] > 0]["forward_return_pct"]
    nonpos = oos[oos["signal"] <= 0]["forward_return_pct"]
    pos_mean = float(pos.mean()) if len(pos) else np.nan
    nonpos_mean = float(nonpos.mean()) if len(nonpos) else np.nan
    diff = pos_mean - nonpos_mean if np.isfinite(pos_mean) and np.isfinite(nonpos_mean) else np.nan

    checks = [train_p > 0, oos_p > 0, oos_s > 0, diff > 0]
    score = sum(bool(x) for x in checks)
    classification = "PASS_STRONG" if score == 4 else "PASS_WEAK" if score >= 3 else "FAIL"

    return {
        "indicator": indicator_name,
        "asset": asset,
        "horizon_m": horizon,
        "n": n,
        "train_n": len(train),
        "oos_n": len(oos),
        "start_available": aligned["available_date"].min().date().isoformat(),
        "end_available": aligned["available_date"].max().date().isoformat(),
        "train_pearson": train_p,
        "oos_pearson": oos_p,
        "oos_pearson_p": oos_pval,
        "full_pearson": full_p,
        "full_pearson_p": full_pval,
        "oos_spearman": oos_s,
        "full_spearman": full_s,
        "oos_pos_signal_n": int(len(pos)),
        "oos_nonpos_signal_n": int(len(nonpos)),
        "oos_pos_mean_return_pct": pos_mean,
        "oos_nonpos_mean_return_pct": nonpos_mean,
        "oos_mean_diff_pct": diff,
        "directional_checks_positive": score,
        "classification": classification,
    }


def fnum(x, digits=3):
    if x is None or not np.isfinite(float(x)):
        return "—"
    return f"{float(x):+.{digits}f}"


def main():
    print("Fetching fixed Liquidity Context inputs...")
    bank = bank_signals()
    treasury = treasury_signals()
    prices = {a: stooq_monthly(a) for a in ASSETS}

    bank.to_csv(OUT / "bank_signals.csv", index=False)
    treasury.to_csv(OUT / "treasury_signals.csv", index=False)

    results = []
    for indicator, sig in [
        ("BANK_IMPULSE", bank),
        ("TREASURY_DURATION_MIX", treasury),
    ]:
        for asset in ASSETS:
            for h in HORIZONS:
                row = evaluate(indicator, sig, asset, prices[asset], h)
                if row:
                    results.append(row)

    if len(results) != 24:
        raise RuntimeError(f"Expected 24 fixed tests, got {len(results)}")

    res = pd.DataFrame(results)
    res["full_pearson_q_bh24"] = bh_qvalues(res["full_pearson_p"].to_numpy())
    res = res.sort_values(["indicator", "asset", "horizon_m"]).reset_index(drop=True)
    res.to_csv(OUT / "RESULTS.csv", index=False)

    counts = res["classification"].value_counts().to_dict()
    fdr05 = int((res["full_pearson_q_bh24"] <= 0.05).sum())
    positive_oos = int((res["oos_pearson"] > 0).sum())
    positive_diff = int((res["oos_mean_diff_pct"] > 0).sum())

    summary = {
        "schema_version": "gmli-liquidity-context-backtest-v1",
        "evidence_tier": "RESEARCH_DIAGNOSTIC",
        "scoring_effect": "NONE",
        "methodology_effect": "NONE",
        "automatic_weight_change": 0,
        "fixed_tests": 24,
        "classification_counts": counts,
        "full_sample_bh_q_le_0_05": fdr05,
        "oos_pearson_positive_tests": positive_oos,
        "oos_conditional_diff_positive_tests": positive_diff,
        "bank_signal_start": bank["available_date"].min().date().isoformat(),
        "bank_signal_end": bank["available_date"].max().date().isoformat(),
        "treasury_signal_start": treasury["available_date"].min().date().isoformat(),
        "treasury_signal_end": treasury["available_date"].max().date().isoformat(),
        "guardrail": "Research only. No production scoring, weight, tier or methodology change is permitted from this run.",
    }
    (OUT / "RESULT_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Liquidity Context fixed backtest v1 — result summary",
        "",
        "Status: **RESEARCH_DIAGNOSTIC / NOT PROMOTED**",
        "",
        f"Fixed family: 24 tests. PASS_STRONG={counts.get('PASS_STRONG',0)}, PASS_WEAK={counts.get('PASS_WEAK',0)}, FAIL={counts.get('FAIL',0)}.",
        f"OOS Pearson positive: {positive_oos}/24. OOS positive-vs-nonpositive conditional return spread positive: {positive_diff}/24. Full-sample Pearson BH q<=0.05: {fdr05}/24.",
        "",
        "## Fixed results",
        "",
        "| Indicator | Asset | H | N | Train r | OOS r | OOS rho | OOS +signal − <=0 return | BH q | Class |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in res.itertuples(index=False):
        lines.append(
            f"| {r.indicator} | {r.asset} | {r.horizon_m}M | {r.n} | {fnum(r.train_pearson)} | {fnum(r.oos_pearson)} | {fnum(r.oos_spearman)} | {fnum(r.oos_mean_diff_pct,2)} pp | {fnum(r.full_pearson_q_bh24)} | {r.classification} |"
        )

    strong = res[res["classification"] == "PASS_STRONG"].sort_values("oos_pearson", ascending=False)
    weak = res[res["classification"] == "PASS_WEAK"].sort_values("oos_pearson", ascending=False)
    lines += ["", "## Interpretation guard", ""]
    if len(strong):
        lines.append("Strong directional survivors: " + ", ".join(f"{r.indicator}/{r.asset}/{int(r.horizon_m)}M" for r in strong.itertuples()) + ".")
    else:
        lines.append("No fixed test met all four predeclared directional robustness checks.")
    if len(weak):
        lines.append("Weak directional survivors: " + ", ".join(f"{r.indicator}/{r.asset}/{int(r.horizon_m)}M" for r in weak.itertuples()) + ".")
    lines += [
        "",
        "Do not promote from this run. H.8 uses revised current history rather than exact real-time vintages; MSPD uses a conservative fixed availability lag; Stooq returns are price-only. Any candidate use in GMLI would require a separately frozen promotion protocol and stronger return/source validation.",
        "",
    ]
    md = "\n".join(lines)
    (OUT / "RESULT_SUMMARY.md").write_text(md, encoding="utf-8")
    print(md)
    print("\nJSON_SUMMARY=" + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
