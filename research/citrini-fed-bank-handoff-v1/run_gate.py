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
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
MONEY_CSV = ROOT / "research" / "global-money-v2" / "latest" / "global_money_v2.csv"

H8_DDP_URL = (
    "https://www.federalreserve.gov/datadownload/Output.aspx?"
    "filetype=csv&from=&label=include&lastobs=&layout=seriescolumn&rel=H8&"
    "series=fce2318909bacbc8ce268096deddd180&to=&type=package"
)
WALCL_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WALCL&cosd=2002-01-01"
UA = {"User-Agent": "Mozilla/5.0 GMLI-citrini-fed-bank-handoff/1.0 fixed-no-search"}
TRAIN_START = "2015-01"
TRAIN_END = "2022-12"
OOS_START = "2023-01"

RELATIONS = [
    {"id": "SPY_USD_ACCEL3_12M", "asset": "SPY", "channel": "usd", "mode": "accel3", "horizon_m": 12},
    {"id": "QQQ_USD_ACCEL3_12M", "asset": "QQQ", "channel": "usd", "mode": "accel3", "horizon_m": 12},
    {"id": "GLD_FXN_ACCEL3_12M", "asset": "GLD", "channel": "fxn", "mode": "accel3", "horizon_m": 12},
    {"id": "DBC_USD_LEVEL_6M", "asset": "DBC", "channel": "usd", "mode": "level", "horizon_m": 6},
    {"id": "DBC_USD_LEVEL_12M", "asset": "DBC", "channel": "usd", "mode": "level", "horizon_m": 12},
    {"id": "DBC_FXN_LEVEL_6M", "asset": "DBC", "channel": "fxn", "mode": "level", "horizon_m": 6},
]


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def retry_get(url, params=None, timeout=120):
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


def nearest_value(dates, vals, target):
    idx = np.searchsorted(dates, np.datetime64(target), side="right") - 1
    return np.nan if idx < 0 else vals[idx]


def parse_h8_ddp():
    r = retry_get(H8_DDP_URL)
    raw = r.content
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    header_idx = next((i for i, row in enumerate(rows) if row and row[0].strip().lower() == "time period"), None)
    if header_idx is None:
        raise RuntimeError("Federal Reserve H8 DDP Time Period header not found")
    header = [c.strip().strip('"') for c in rows[header_idx]]
    if "B1151NCBA" not in header:
        raise RuntimeError(f"B1151NCBA missing from H8 DDP header: {header[:40]}")
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
    return df, raw


def parse_walcl():
    r = retry_get(WALCL_URL)
    raw = r.content
    df = pd.read_csv(io.BytesIO(raw))
    if len(df.columns) < 2:
        raise RuntimeError(f"Unexpected WALCL CSV columns: {list(df.columns)}")
    df = df.rename(columns={df.columns[0]: "date", df.columns[1]: "value"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().drop_duplicates("date").sort_values("date").reset_index(drop=True)
    if len(df) < 500:
        raise RuntimeError(f"Insufficient WALCL history: {len(df)}")
    return df, raw


def monthly_13w(df, prefix):
    dates = df["date"].to_numpy(dtype="datetime64[ns]")
    vals = df["value"].to_numpy(float)
    monthly = df.groupby(df["date"].dt.to_period("M"), as_index=False).tail(1).copy()
    rows = []
    for r in monthly.itertuples(index=False):
        prior = nearest_value(dates, vals, r.date - pd.Timedelta(days=91))
        chg = pct_change(r.value, prior)
        if np.isfinite(chg):
            rows.append({
                "signal_month": str(r.date.to_period("M")),
                f"{prefix}_observation_date": r.date.date().isoformat(),
                f"{prefix}_value": float(r.value),
                f"{prefix}_13w_pct": float(chg),
            })
    return pd.DataFrame(rows).sort_values("signal_month").drop_duplicates("signal_month", keep="last").reset_index(drop=True)


def state_name(fed, bank):
    if fed > 0 and bank > 0:
        return "BROAD_EASING"
    if fed < 0 and bank > 0:
        return "PRIVATE_HANDOFF"
    if fed < 0 and bank < 0:
        return "TRUE_TIGHTENING"
    if fed > 0 and bank < 0:
        return "FED_OFFSET"
    return "MIXED_FLAT"


def build_handoff_states():
    bank_df, bank_raw = parse_h8_ddp()
    fed_df, fed_raw = parse_walcl()
    bank_m = monthly_13w(bank_df, "bank")
    fed_m = monthly_13w(fed_df, "fed")
    x = bank_m.merge(fed_m, on="signal_month", how="inner").sort_values("signal_month").reset_index(drop=True)
    if len(x) < 200:
        raise RuntimeError(f"Insufficient aligned Fed-bank monthly history: {len(x)}")
    x["state"] = [state_name(f, b) for f, b in zip(x["fed_13w_pct"], x["bank_13w_pct"])]
    x["private_handoff"] = (x["state"] == "PRIVATE_HANDOFF").astype(int)
    x["decision_month"] = x["signal_month"].map(lambda m: add_months(m, 1))
    meta = {
        "fed": {
            "source": "FRED",
            "series": "WALCL",
            "url": WALCL_URL,
            "sha256": sha256(fed_raw),
            "bytes": len(fed_raw),
            "weekly_rows": len(fed_df),
            "first_observation": fed_df["date"].min().date().isoformat(),
            "last_observation": fed_df["date"].max().date().isoformat(),
        },
        "bank": {
            "source": "Federal Reserve H8 Data Download Program",
            "series": "B1151NCBA",
            "url": H8_DDP_URL,
            "sha256": sha256(bank_raw),
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


def load_money():
    raw = MONEY_CSV.read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    by_month = {}
    for row in rows:
        try:
            usd = float(row["gbm_usd_yoy_pct"])
            fxn = float(row["gbm_fxn_yoy_pct"])
        except Exception:
            continue
        if np.isfinite(usd) and np.isfinite(fxn):
            by_month[row["month"]] = {"usd": usd, "fxn": fxn}
    if not by_month or min(by_month) > TRAIN_START:
        raise RuntimeError(f"Global Money V2 history insufficient: first={min(by_month) if by_month else None}")
    meta = {
        "file": str(MONEY_CSV.relative_to(ROOT)),
        "sha256": sha256(raw),
        "months": len(by_month),
        "first_month": min(by_month),
        "last_month": max(by_month),
        "availability_lag_months": 1,
    }
    return by_month, meta


def money_predictor(money, month, channel, mode):
    if month not in money:
        return np.nan
    level = money[month][channel]
    if mode == "level":
        return float(level)
    if mode == "accel3":
        prior = add_months(month, -3)
        if prior not in money:
            return np.nan
        return float(level - money[prior][channel])
    raise ValueError(f"Unknown Money mode {mode}")


def fetch_monthly_price(asset):
    last = None
    for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
        url = f"https://{host}/v8/finance/chart/{asset}"
        params = {
            "period1": "631152000",
            "period2": str(int(time.time()) + 86400),
            "interval": "1mo",
            "events": "history",
            "includeAdjustedClose": "true",
        }
        try:
            r = retry_get(url, params=params, timeout=120)
            raw = r.content
            payload = r.json()
            z = ((payload.get("chart") or {}).get("result") or [None])[0]
            if not z:
                raise RuntimeError(f"Yahoo {asset} empty result")
            ts = z.get("timestamp") or []
            adj = (((z.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose") or [])
            close = (((z.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            prices = {}
            for i, t in enumerate(ts):
                v = adj[i] if i < len(adj) and adj[i] is not None else close[i] if i < len(close) else None
                if v is None or not np.isfinite(float(v)) or float(v) <= 0:
                    continue
                month = datetime.fromtimestamp(int(t), tz=timezone.utc).strftime("%Y-%m")
                if month == current_month:
                    continue
                prices[month] = float(v)
            if len(prices) < 150:
                raise RuntimeError(f"Yahoo {asset} history too short: {len(prices)}")
            meta = {
                "source": "Yahoo Finance monthly adjusted close",
                "url": r.url,
                "sha256": sha256(raw),
                "bytes": len(raw),
                "months": len(prices),
                "first_month": min(prices),
                "last_month": max(prices),
                "current_incomplete_month_excluded": current_month,
            }
            return prices, meta
        except Exception as exc:
            last = exc
    raise last


def safe_corr(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def fit_relation(relation, states, money, prices):
    rows = []
    h = relation["horizon_m"]
    for r in states.itertuples(index=False):
        signal_month = str(r.signal_month)
        if signal_month not in money:
            continue
        x = money_predictor(money, signal_month, relation["channel"], relation["mode"])
        start = add_months(signal_month, 1)
        end = add_months(start, h)
        p0, p1 = prices.get(start), prices.get(end)
        if not np.isfinite(x) or p0 is None or p1 is None or p0 <= 0 or p1 <= 0:
            continue
        rows.append({
            "relation": relation["id"],
            "asset": relation["asset"],
            "channel": relation["channel"],
            "mode": relation["mode"],
            "horizon_m": h,
            "signal_month": signal_month,
            "decision_month": start,
            "end_month": end,
            "money_x": float(x),
            "private_handoff": int(r.private_handoff),
            "state": str(r.state),
            "fed_13w_pct": float(r.fed_13w_pct),
            "bank_13w_pct": float(r.bank_13w_pct),
            "forward_log_return": float(math.log(p1 / p0)),
            "phase": month_index(start) % h,
        })
    df = pd.DataFrame(rows).sort_values("signal_month").reset_index(drop=True)
    train = df[(df["signal_month"] >= TRAIN_START) & (df["signal_month"] <= TRAIN_END)].copy()
    oos = df[df["signal_month"] >= OOS_START].copy()
    if len(train) < 60 or len(oos) < 18:
        raise RuntimeError(f"{relation['id']} fixed split too short: train={len(train)} oos={len(oos)}")
    if train["private_handoff"].nunique() < 2:
        raise RuntimeError(f"{relation['id']} train has no private-handoff variation")

    money_mean = float(train["money_x"].mean())
    money_sd = float(train["money_x"].std(ddof=0))
    if not np.isfinite(money_sd) or money_sd <= 0:
        raise RuntimeError(f"{relation['id']} invalid Money train sd")
    m_tr = (train["money_x"].to_numpy(float) - money_mean) / money_sd
    m_oo = (oos["money_x"].to_numpy(float) - money_mean) / money_sd
    hand_tr = train["private_handoff"].to_numpy(float)
    hand_oo = oos["private_handoff"].to_numpy(float)
    y_tr = train["forward_log_return"].to_numpy(float)
    y_oo = oos["forward_log_return"].to_numpy(float)

    xb_tr = sm.add_constant(np.column_stack([m_tr]), has_constant="add")
    xb_oo = sm.add_constant(np.column_stack([m_oo]), has_constant="add")
    xc_tr = sm.add_constant(np.column_stack([m_tr, hand_tr]), has_constant="add")
    xc_oo = sm.add_constant(np.column_stack([m_oo, hand_oo]), has_constant="add")

    baseline = sm.OLS(y_tr, xb_tr).fit()
    candidate = sm.OLS(y_tr, xc_tr).fit()
    hac_lags = h - 1
    candidate_hac = candidate.get_robustcov_results(cov_type="HAC", maxlags=hac_lags)
    pred_b = baseline.predict(xb_oo)
    pred_c = candidate.predict(xc_oo)
    sse_b = float(np.sum((y_oo - pred_b) ** 2))
    sse_c = float(np.sum((y_oo - pred_c) ** 2))
    rmse_b = float(math.sqrt(sse_b / len(y_oo)))
    rmse_c = float(math.sqrt(sse_c / len(y_oo)))
    incr = float(1.0 - sse_c / sse_b) if sse_b > 0 else None
    corr_b = safe_corr(pred_b, y_oo)
    corr_c = safe_corr(pred_c, y_oo)

    phase_rows = []
    for phase in range(h):
        mask = oos["phase"].to_numpy(int) == phase
        n = int(mask.sum())
        if n == 0:
            continue
        yy, pb, pc = y_oo[mask], pred_b[mask], pred_c[mask]
        sb = float(np.sum((yy - pb) ** 2))
        sc = float(np.sum((yy - pc) ** 2))
        pi = float(1.0 - sc / sb) if sb > 0 else None
        phase_rows.append({
            "relation": relation["id"],
            "phase": phase,
            "n": n,
            "sse_baseline": sb,
            "sse_candidate": sc,
            "incremental_r2": pi,
            "candidate_better": bool(sc < sb),
        })

    ph = oos[oos["private_handoff"] == 1]["forward_log_return"]
    other = oos[oos["private_handoff"] == 0]["forward_log_return"]
    ph_mean = float(ph.mean()) if len(ph) else None
    other_mean = float(other.mean()) if len(other) else None

    result = {
        **relation,
        "train_n": int(len(train)),
        "oos_n": int(len(oos)),
        "train_private_handoff_n": int(train["private_handoff"].sum()),
        "oos_private_handoff_n": int(oos["private_handoff"].sum()),
        "train_start": str(train["signal_month"].min()),
        "train_end": str(train["signal_month"].max()),
        "oos_start": str(oos["signal_month"].min()),
        "oos_end": str(oos["signal_month"].max()),
        "money_train_mean": money_mean,
        "money_train_sd": money_sd,
        "baseline_train_r2": float(baseline.rsquared),
        "candidate_train_r2": float(candidate.rsquared),
        "private_handoff_beta": float(candidate.params[2]),
        "private_handoff_hac_pvalue": float(candidate_hac.pvalues[2]),
        "hac_maxlags": hac_lags,
        "oos_sse_baseline": sse_b,
        "oos_sse_candidate": sse_c,
        "oos_rmse_baseline": rmse_b,
        "oos_rmse_candidate": rmse_c,
        "oos_incremental_r2": incr,
        "oos_prediction_pearson_baseline": corr_b,
        "oos_prediction_pearson_candidate": corr_c,
        "oos_private_handoff_mean_return": ph_mean,
        "oos_other_states_mean_return": other_mean,
        "oos_private_handoff_minus_other_return": None if ph_mean is None or other_mean is None else ph_mean - other_mean,
        "phase_total": len(phase_rows),
        "phase_wins_candidate": int(sum(1 for p in phase_rows if p["candidate_better"])),
        "phase_median_incremental_r2": float(np.median([p["incremental_r2"] for p in phase_rows if p["incremental_r2"] is not None])) if phase_rows else None,
    }
    return result, phase_rows, df


def fnum(x, digits=4):
    if x is None or not np.isfinite(float(x)):
        return "—"
    return f"{float(x):+.{digits}f}"


def build_markdown(summary):
    rels = summary["relations"]
    g = summary["gate"]
    lines = [
        "# Citrini Fed → Bank Handoff v1 — result summary",
        "",
        f"Status: **{summary['status']}**",
        "",
        "Evidence tier: **RESEARCH_DIAGNOSTIC** · scoring effect **NONE** · automatic weight **0**.",
        "",
        "## Fixed family gate",
        "",
        f"- Positive train PRIVATE_HANDOFF beta: **{g['positive_train_beta_relations']}/6**",
        f"- Positive OOS incremental R²: **{g['positive_oos_incremental_r2_relations']}/6**",
        f"- Median OOS incremental R²: **{fnum(g['median_oos_incremental_r2'])}**",
        f"- OOS prediction correlation not worse: **{g['corr_not_worse_relations']}/6**",
        f"- Non-overlap phase wins: **{g['phase_wins']}/{g['phase_total']}**",
        f"- Median non-overlap phase incremental R²: **{fnum(g['median_phase_incremental_r2'])}**",
        "",
        "Gate checks:",
    ]
    for k, v in g["checks"].items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "",
        "## Fixed relation results",
        "",
        "| Relation | Train β handoff | HAC p | OOS incr R² | Corr baseline → candidate | Phase wins | OOS handoff − other return |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rels:
        corr = f"{fnum(r['oos_prediction_pearson_baseline'])} → {fnum(r['oos_prediction_pearson_candidate'])}"
        lines.append(
            f"| {r['id']} | {fnum(r['private_handoff_beta'])} | {r['private_handoff_hac_pvalue']:.4f} | "
            f"{fnum(r['oos_incremental_r2'])} | {corr} | {r['phase_wins_candidate']}/{r['phase_total']} | "
            f"{fnum(r['oos_private_handoff_minus_other_return'])} |"
        )
    lines += [
        "",
        "## Interpretation guard",
        "",
        "This is a fixed incremental-value test of the Citrini-style PRIVATE_HANDOFF state, not a new liquidity composite. The state must add stable OOS value beyond promoted Money baselines to justify any further promotion work.",
        "",
        "If status is `STOP_RESEARCH_DIAGNOSTIC`, do not retune windows, thresholds, lags, signs, assets or subperiods to rescue it. It may remain descriptive Liquidity Context only.",
        "",
        "Even `PROMOTION_CANDIDATE` would not change production without a separately frozen promotion protocol.",
    ]
    return "\n".join(lines) + "\n"


def main():
    print("Fetching fixed Fed-bank handoff inputs...")
    states, handoff_meta = build_handoff_states()
    money, money_meta = load_money()
    prices = {}
    price_meta = {}
    for asset in sorted(set(r["asset"] for r in RELATIONS)):
        prices[asset], price_meta[asset] = fetch_monthly_price(asset)
        print(f"Market {asset}: {price_meta[asset]['first_month']}..{price_meta[asset]['last_month']} n={price_meta[asset]['months']}")

    states.to_csv(OUT / "HANDOFF_STATES.csv", index=False)
    relation_results = []
    all_phases = []
    all_aligned = []
    for relation in RELATIONS:
        result, phases, aligned = fit_relation(relation, states, money, prices[relation["asset"]])
        relation_results.append(result)
        all_phases.extend(phases)
        all_aligned.append(aligned)

    pd.DataFrame(relation_results).to_csv(OUT / "RELATION_RESULTS.csv", index=False)
    pd.DataFrame(all_phases).to_csv(OUT / "PHASE_RESULTS.csv", index=False)
    pd.concat(all_aligned, ignore_index=True).to_csv(OUT / "ALIGNED_DATA.csv", index=False)

    positive_beta = sum(1 for r in relation_results if r["private_handoff_beta"] > 0)
    positive_incr = sum(1 for r in relation_results if r["oos_incremental_r2"] is not None and r["oos_incremental_r2"] > 0)
    median_incr = float(np.median([r["oos_incremental_r2"] for r in relation_results if r["oos_incremental_r2"] is not None]))
    corr_not_worse = sum(
        1 for r in relation_results
        if r["oos_prediction_pearson_baseline"] is not None
        and r["oos_prediction_pearson_candidate"] is not None
        and r["oos_prediction_pearson_candidate"] >= r["oos_prediction_pearson_baseline"]
    )
    phase_valid = [p for p in all_phases if p["incremental_r2"] is not None and np.isfinite(p["incremental_r2"])]
    phase_wins = sum(1 for p in phase_valid if p["candidate_better"])
    phase_total = len(phase_valid)
    median_phase = float(np.median([p["incremental_r2"] for p in phase_valid])) if phase_valid else None

    checks = {
        "positive_train_beta_at_least_4of6": positive_beta >= 4,
        "positive_oos_incremental_r2_at_least_4of6": positive_incr >= 4,
        "median_oos_incremental_r2_positive": median_incr > 0,
        "prediction_corr_not_worse_at_least_4of6": corr_not_worse >= 4,
        "nonoverlap_phase_majority_and_median_positive": phase_total > 0 and phase_wins > phase_total / 2 and median_phase is not None and median_phase > 0,
    }
    passed = all(checks.values())
    status = "PROMOTION_CANDIDATE" if passed else "STOP_RESEARCH_DIAGNOSTIC"
    state_counts_full = {k: int(v) for k, v in states["state"].value_counts().to_dict().items()}
    state_counts_train = {k: int(v) for k, v in states[(states["signal_month"] >= TRAIN_START) & (states["signal_month"] <= TRAIN_END)]["state"].value_counts().to_dict().items()}
    state_counts_oos = {k: int(v) for k, v in states[states["signal_month"] >= OOS_START]["state"].value_counts().to_dict().items()}

    summary = {
        "schema_version": "gmli-citrini-fed-bank-handoff-v1",
        "status": status,
        "evidence_tier": "RESEARCH_DIAGNOSTIC",
        "scoring_effect": "NONE",
        "automatic_weight_change": 0,
        "methodology_effect": "NONE",
        "core_modified": False,
        "parameter_search": False,
        "asset_search": False,
        "horizon_search": False,
        "lag_search": False,
        "threshold_search": False,
        "sign_search": False,
        "train_signal_months": f"{TRAIN_START}..{TRAIN_END}",
        "oos_signal_months": f"{OOS_START}+",
        "candidate": "PRIVATE_HANDOFF = Fed 13W < 0 AND Bank 13W > 0",
        "state_counts": {"full": state_counts_full, "train": state_counts_train, "oos": state_counts_oos},
        "sources": {"handoff": handoff_meta, "money": money_meta, "prices": price_meta},
        "gate": {
            "positive_train_beta_relations": positive_beta,
            "positive_oos_incremental_r2_relations": positive_incr,
            "median_oos_incremental_r2": median_incr,
            "corr_not_worse_relations": corr_not_worse,
            "phase_wins": phase_wins,
            "phase_total": phase_total,
            "median_phase_incremental_r2": median_phase,
            "checks": checks,
            "pass": passed,
        },
        "relations": relation_results,
        "guardrail": "No production change. STOP forbids rescue retuning; PROMOTION_CANDIDATE would still require a separate versioned promotion protocol.",
    }
    (OUT / "RESULT_SUMMARY.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = build_markdown(summary)
    (OUT / "RESULT_SUMMARY.md").write_text(md, encoding="utf-8")
    print(md)
    print("JSON_SUMMARY=" + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
