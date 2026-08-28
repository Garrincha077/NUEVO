#!/usr/bin/env python3
import csv
import hashlib
import io
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
MONEY_CSV = ROOT / "research" / "global-money-v2" / "latest" / "global_money_v2.csv"
H8_DDP_URL = (
    "https://www.federalreserve.gov/datadownload/Output.aspx?"
    "filetype=csv&from=&label=include&lastobs=&layout=seriescolumn&rel=H8&"
    "series=fce2318909bacbc8ce268096deddd180&to=&type=package"
)
UA = {"User-Agent": "GMLI-bank-impulse-GLD6M-incremental/1.0 fixed-no-search"}
TRAIN_END = "2022-12"
OOS_START = "2023-01"
HORIZON_M = 6
HAC_MAXLAGS = 5


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def retry_get(url, params=None, timeout=120):
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


def add_months(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    total = y * 12 + (m - 1) + n
    yy, mm0 = divmod(total, 12)
    return f"{yy:04d}-{mm0 + 1:02d}"


def month_index(month: str) -> int:
    y, m = map(int, month.split("-"))
    return y * 12 + (m - 1)


def pct_change(a, b):
    if not np.isfinite(a) or not np.isfinite(b) or b == 0:
        return np.nan
    return (a / b - 1.0) * 100.0


def fetch_bank_impulse():
    r = retry_get(H8_DDP_URL)
    raw = r.content
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    header_idx = None
    for i, row in enumerate(rows):
        if row and row[0].strip().lower() == "time period":
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("Federal Reserve H8 DDP header not found")
    header = [c.strip().strip('"') for c in rows[header_idx]]
    if "B1151NCBA" not in header:
        raise RuntimeError("Federal Reserve H8 DDP B1151NCBA missing")
    value_idx = header.index("B1151NCBA")

    data = []
    for row in rows[header_idx + 1 :]:
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
    out = []
    for row in monthly.itertuples(index=False):
        v13 = nearest_value(row.date - pd.Timedelta(days=91))
        v26 = nearest_value(row.date - pd.Timedelta(days=182))
        cur = pct_change(row.value, v13)
        prior = pct_change(v13, v26)
        impulse = cur - prior if np.isfinite(cur) and np.isfinite(prior) else np.nan
        if not np.isfinite(impulse):
            continue
        available = row.date + pd.Timedelta(days=14)
        decision_month = str(available.to_period("M"))
        out.append(
            {
                "bank_observation_date": row.date,
                "bank_available_date": available,
                "decision_month": decision_month,
                "bank_impulse": float(impulse),
                "bank_current_13w_pct": float(cur),
                "bank_prior_13w_pct": float(prior),
            }
        )
    result = pd.DataFrame(out).sort_values("bank_available_date").drop_duplicates("decision_month", keep="last").reset_index(drop=True)
    if len(result) < 300:
        raise RuntimeError(f"Insufficient monthly bank impulse history: {len(result)}")
    meta = {
        "source": "Federal Reserve H8 Data Download Program",
        "series": "B1151NCBA",
        "url": H8_DDP_URL,
        "sha256": sha256(raw),
        "bytes": len(raw),
        "weekly_rows": len(df),
        "monthly_signals": len(result),
        "first_observation": result["bank_observation_date"].min().date().isoformat(),
        "last_observation": result["bank_observation_date"].max().date().isoformat(),
    }
    return result, meta


def load_money():
    raw = MONEY_CSV.read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    by_month = {}
    for row in rows:
        try:
            fxn = float(row["gbm_fxn_yoy_pct"])
        except Exception:
            continue
        if np.isfinite(fxn):
            by_month[row["month"]] = fxn
    if not by_month or min(by_month) > "2015-01":
        raise RuntimeError(f"Global Money V2 history insufficient: first={min(by_month) if by_month else None}")

    def accel3(month):
        prior = add_months(month, -3)
        if month not in by_month or prior not in by_month:
            return np.nan
        return float(by_month[month] - by_month[prior])

    meta = {
        "file": str(MONEY_CSV.relative_to(ROOT)),
        "sha256": sha256(raw),
        "months": len(by_month),
        "first_month": min(by_month),
        "last_month": max(by_month),
        "channel": "fxn",
        "transform": "accel3",
        "availability_lag_months": 1,
    }
    return accel3, meta


def fetch_gld_monthly():
    last_exc = None
    for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
        url = f"https://{host}/v8/finance/chart/GLD?range=max&interval=1mo&events=history&includeAdjustedClose=true"
        try:
            r = retry_get(url, timeout=90)
            raw = r.content
            payload = r.json()
            z = ((payload.get("chart") or {}).get("result") or [None])[0]
            if not z:
                raise RuntimeError("Yahoo GLD empty result")
            ts = z.get("timestamp") or []
            adj_blocks = ((z.get("indicators") or {}).get("adjclose") or [])
            if not adj_blocks:
                raise RuntimeError("Yahoo GLD adjusted close missing")
            vals = adj_blocks[0].get("adjclose") or []
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            prices = {}
            for t, v in zip(ts, vals):
                if not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
                    continue
                month = datetime.fromtimestamp(int(t), tz=timezone.utc).strftime("%Y-%m")
                if month == current_month:
                    continue
                prices[month] = float(v)
            if len(prices) < 200:
                raise RuntimeError(f"Yahoo GLD history too short: {len(prices)}")
            meta = {
                "source": "Yahoo Finance monthly adjusted close",
                "url": url,
                "sha256": sha256(raw),
                "bytes": len(raw),
                "months": len(prices),
                "first_month": min(prices),
                "last_month": max(prices),
                "current_incomplete_month_excluded": current_month,
            }
            return prices, meta
        except Exception as exc:
            last_exc = exc
    raise last_exc


def build_dataset(bank, money_accel3, prices):
    rows = []
    for r in bank.itertuples(index=False):
        base = str(r.decision_month)
        money_month = add_months(base, -1)
        end = add_months(base, HORIZON_M)
        money_x = money_accel3(money_month)
        p0 = prices.get(base)
        p1 = prices.get(end)
        if not np.isfinite(money_x) or p0 is None or p1 is None or p0 <= 0 or p1 <= 0:
            continue
        rows.append(
            {
                "money_signal_month": money_month,
                "decision_month": base,
                "end_month": end,
                "bank_observation_date": r.bank_observation_date.date().isoformat(),
                "bank_available_date": r.bank_available_date.date().isoformat(),
                "money_fxn_accel3": float(money_x),
                "bank_impulse": float(r.bank_impulse),
                "gld_forward_log_return_6m": float(math.log(p1 / p0)),
                "phase_mod6": month_index(base) % 6,
            }
        )
    df = pd.DataFrame(rows).sort_values("money_signal_month").drop_duplicates("decision_month", keep="last").reset_index(drop=True)
    if len(df) < 100:
        raise RuntimeError(f"Aligned dataset too short: {len(df)}")
    return df


def safe_corr(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a = a[ok]
    b = b[ok]
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def standardize_train(train, oos, col):
    mean = float(train[col].mean())
    sd = float(train[col].std(ddof=0))
    if not np.isfinite(sd) or sd <= 0:
        raise RuntimeError(f"Zero/invalid train standard deviation for {col}")
    return (train[col].to_numpy(float) - mean) / sd, (oos[col].to_numpy(float) - mean) / sd, mean, sd


def run_models(df):
    train = df[(df["money_signal_month"] >= "2015-01") & (df["money_signal_month"] <= TRAIN_END)].copy()
    oos = df[df["money_signal_month"] >= OOS_START].copy()
    if len(train) < 60 or len(oos) < 18:
        raise RuntimeError(f"Insufficient fixed split: train={len(train)} oos={len(oos)}")

    money_tr, money_oo, money_mean, money_sd = standardize_train(train, oos, "money_fxn_accel3")
    bank_tr, bank_oo, bank_mean, bank_sd = standardize_train(train, oos, "bank_impulse")
    y_tr = train["gld_forward_log_return_6m"].to_numpy(float)
    y_oo = oos["gld_forward_log_return_6m"].to_numpy(float)

    xb_tr = sm.add_constant(np.column_stack([money_tr]), has_constant="add")
    xb_oo = sm.add_constant(np.column_stack([money_oo]), has_constant="add")
    xc_tr = sm.add_constant(np.column_stack([money_tr, bank_tr]), has_constant="add")
    xc_oo = sm.add_constant(np.column_stack([money_oo, bank_oo]), has_constant="add")

    baseline = sm.OLS(y_tr, xb_tr).fit()
    candidate = sm.OLS(y_tr, xc_tr).fit()
    candidate_hac = candidate.get_robustcov_results(cov_type="HAC", maxlags=HAC_MAXLAGS)

    pred_b = baseline.predict(xb_oo)
    pred_c = candidate.predict(xc_oo)
    err_b = y_oo - pred_b
    err_c = y_oo - pred_c
    sse_b = float(np.sum(err_b ** 2))
    sse_c = float(np.sum(err_c ** 2))
    incremental_r2 = float(1.0 - sse_c / sse_b) if sse_b > 0 else None
    corr_b = safe_corr(pred_b, y_oo)
    corr_c = safe_corr(pred_c, y_oo)

    phases = []
    for phase in range(6):
        mask = oos["phase_mod6"].to_numpy(int) == phase
        n = int(mask.sum())
        if n == 0:
            phases.append({"phase": phase, "n": 0, "sse_baseline": None, "sse_candidate": None, "incremental_r2": None, "candidate_better": False})
            continue
        pb = pred_b[mask]
        pc = pred_c[mask]
        yy = y_oo[mask]
        sb = float(np.sum((yy - pb) ** 2))
        sc = float(np.sum((yy - pc) ** 2))
        r2i = float(1.0 - sc / sb) if sb > 0 else None
        phases.append({"phase": phase, "n": n, "sse_baseline": sb, "sse_candidate": sc, "incremental_r2": r2i, "candidate_better": bool(sc < sb)})

    valid_phase_r2 = [p["incremental_r2"] for p in phases if p["incremental_r2"] is not None and np.isfinite(p["incremental_r2"])]
    phase_wins = sum(1 for p in phases if p["candidate_better"])
    phase_median = float(np.median(valid_phase_r2)) if valid_phase_r2 else None

    bank_beta = float(candidate.params[2])
    bank_hac_p = float(candidate_hac.pvalues[2])
    checks = {
        "bank_train_beta_positive": bool(bank_beta > 0),
        "bank_hac_p_lt_0_10": bool(bank_hac_p < 0.10),
        "oos_incremental_r2_positive": bool(incremental_r2 is not None and incremental_r2 > 0),
        "oos_prediction_corr_not_worse": bool(corr_b is not None and corr_c is not None and corr_c >= corr_b),
        "phase_robustness_4of6_and_median_positive": bool(phase_wins >= 4 and phase_median is not None and phase_median > 0),
    }
    passed = all(checks.values())

    return {
        "classification": "PROMOTION_CANDIDATE" if passed else "STOP_RESEARCH_DIAGNOSTIC",
        "train_n": int(len(train)),
        "oos_n": int(len(oos)),
        "train_money_signal_start": str(train["money_signal_month"].min()),
        "train_money_signal_end": str(train["money_signal_month"].max()),
        "oos_money_signal_start": str(oos["money_signal_month"].min()),
        "oos_money_signal_end": str(oos["money_signal_month"].max()),
        "standardization": {
            "money_train_mean": money_mean,
            "money_train_sd": money_sd,
            "bank_train_mean": bank_mean,
            "bank_train_sd": bank_sd,
        },
        "baseline_train": {
            "params": [float(x) for x in baseline.params],
            "r2": float(baseline.rsquared),
        },
        "candidate_train": {
            "params": [float(x) for x in candidate.params],
            "r2": float(candidate.rsquared),
            "bank_beta_standardized": bank_beta,
            "bank_hac_pvalue": bank_hac_p,
            "hac_maxlags": HAC_MAXLAGS,
        },
        "oos": {
            "sse_baseline": sse_b,
            "sse_candidate": sse_c,
            "rmse_baseline": float(np.sqrt(np.mean(err_b ** 2))),
            "rmse_candidate": float(np.sqrt(np.mean(err_c ** 2))),
            "incremental_r2_vs_baseline": incremental_r2,
            "prediction_pearson_baseline": corr_b,
            "prediction_pearson_candidate": corr_c,
        },
        "nonoverlap_phase_robustness": {
            "phase_wins_candidate": phase_wins,
            "phase_total": 6,
            "median_incremental_r2": phase_median,
            "phases": phases,
        },
        "gate_checks": checks,
        "gate_pass": passed,
    }


def fmt(x, digits=4):
    if x is None or not np.isfinite(float(x)):
        return "—"
    return f"{float(x):+.{digits}f}"


def main():
    bank, bank_meta = fetch_bank_impulse()
    money_accel3, money_meta = load_money()
    prices, price_meta = fetch_gld_monthly()
    dataset = build_dataset(bank, money_accel3, prices)
    model = run_models(dataset)

    result = {
        "schema_version": "gmli-bank-impulse-gld6m-incremental-v1",
        "evidence_tier": "RESEARCH_DIAGNOSTIC",
        "status": model["classification"],
        "scoring_effect": "NONE",
        "automatic_weight_change": 0,
        "methodology_effect": "NONE",
        "core_modified": False,
        "parameter_search": False,
        "asset_search": False,
        "horizon_search": False,
        "lag_search": False,
        "target": "GLD_6M_FORWARD_LOG_ADJUSTED_RETURN",
        "baseline": "Money_FXN_accel3",
        "candidate_addition": "Bank_Impulse_13W_minus_prior13W",
        "sources": {"bank": bank_meta, "money": money_meta, "gld": price_meta},
        "model": model,
        "guardrail": "PROMOTION_CANDIDATE is not production promotion. No score, weight, evidence-tier or methodology change occurs from this run.",
    }

    dataset.to_csv(OUT / "ALIGNED_DATA.csv", index=False)
    (OUT / "RESULT_SUMMARY.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    oos = model["oos"]
    phase = model["nonoverlap_phase_robustness"]
    checks = model["gate_checks"]
    md = [
        "# Bank Impulse → GLD 6M incremental robustness gate v1",
        "",
        f"Status: **{model['classification']}**",
        "",
        "Evidence tier: **RESEARCH_DIAGNOSTIC**. Scoring effect: **NONE**. Automatic weight change: **0**.",
        "",
        "## Fixed model comparison",
        "",
        f"- Train n: {model['train_n']} | OOS n: {model['oos_n']}",
        f"- Candidate standardized Bank beta: {fmt(model['candidate_train']['bank_beta_standardized'])}",
        f"- Bank Newey-West/HAC p-value (maxlags=5): {model['candidate_train']['bank_hac_pvalue']:.4f}",
        f"- OOS RMSE baseline: {oos['rmse_baseline']:.6f}",
        f"- OOS RMSE candidate: {oos['rmse_candidate']:.6f}",
        f"- OOS incremental R² vs baseline: {fmt(oos['incremental_r2_vs_baseline'])}",
        f"- OOS prediction Pearson baseline: {fmt(oos['prediction_pearson_baseline'])}",
        f"- OOS prediction Pearson candidate: {fmt(oos['prediction_pearson_candidate'])}",
        f"- Non-overlap phase wins: {phase['phase_wins_candidate']}/6",
        f"- Median phase incremental R²: {fmt(phase['median_incremental_r2'])}",
        "",
        "## Frozen gate checks",
        "",
    ]
    for k, v in checks.items():
        md.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    md += [
        "",
        "## Six fixed non-overlapping OOS phases",
        "",
        "| Phase | N | Incremental R² | Candidate better SSE? |",
        "|---:|---:|---:|---|",
    ]
    for p in phase["phases"]:
        md.append(f"| {p['phase']} | {p['n']} | {fmt(p['incremental_r2'])} | {'YES' if p['candidate_better'] else 'NO'} |")
    md += [
        "",
        "## Decision rule",
        "",
        "`PROMOTION_CANDIDATE` requires all predeclared checks to pass. Any failure forces `STOP_RESEARCH_DIAGNOSTIC`.",
        "",
        "Even a promotion-candidate result does not change production. A separate versioned promotion protocol would still be required.",
    ]
    (OUT / "RESULT_SUMMARY.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("\n".join(md))
    print("JSON_SUMMARY=" + json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
