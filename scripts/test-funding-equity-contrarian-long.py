#!/usr/bin/env python3
import argparse
import csv
import importlib.util
import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
TRANSFER_RUNNER = ROOT / 'scripts' / 'test-global-money-v2-transmission.py'
FUNDING_HISTORY = ROOT / 'research' / 'funding-v2' / 'latest' / 'history.csv'
CONTRACT = ROOT / 'research' / 'funding-equity-contrarian-long-contract.json'
VERSION = 'GMLI_FUNDING_EQUITY_CONTRARIAN_LONG_V1'
ASSETS = ['SPY', 'QQQ']
HORIZON = 12
MIN_KNOWN_DRIFT = 36


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_contract():
    c = json.loads(CONTRACT.read_text(encoding='utf-8'))
    assert c['test_version'] == VERSION
    assert c['status'] == 'FROZEN_BEFORE_EMPIRICAL_RUN'
    assert c['assets'] == ASSETS
    assert c['horizon_months'] == HORIZON
    assert c['publication_lag_months'] == 1
    assert c['signal']['transform'] == '100 - effective_score'
    assert all(v is False for v in c['no_search'].values())
    assert c['promotion_allowed_by_this_test'] is False
    return c


def load_funding_history():
    rows = []
    with FUNDING_HISTORY.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            score = float(row['effective_score'])
            rows.append({
                'observation_month': row['observation_month'],
                'available_date': row['available_date'],
                'effective_score': score,
                'inverted_funding': 100.0 - score,
                'regime': row['regime'],
            })
    return rows


def build_observations(funding, price, transfer):
    rows = []
    for f in funding:
        month = f['observation_month']
        start = transfer.add_months(month, 1)
        end = transfer.add_months(start, HORIZON)
        p0 = price.get(start)
        p1 = price.get(end)
        if p0 is None or p1 is None or p0 <= 0 or p1 <= 0:
            continue
        rows.append({
            **f,
            'price_start_month': start,
            'price_end_month': end,
            'forward_log_return': math.log(p1 / p0),
        })
    rows.sort(key=lambda x: x['observation_month'])

    # Positive-market-drift control using only previously completed 12M labels.
    for row in rows:
        known = [
            x['forward_log_return'] for x in rows
            if x['price_end_month'] <= row['observation_month']
        ]
        if len(known) >= MIN_KNOWN_DRIFT:
            baseline = sum(known) / len(known)
            row['known_drift_n'] = len(known)
            row['known_drift_baseline'] = baseline
            row['drift_excess_return'] = row['forward_log_return'] - baseline
        else:
            row['known_drift_n'] = len(known)
            row['known_drift_baseline'] = None
            row['drift_excess_return'] = None
    return rows


def corr_metrics(rows, y_field, transfer):
    valid = [r for r in rows if r.get(y_field) is not None and math.isfinite(r[y_field])]
    xs = [r['inverted_funding'] for r in valid]
    ys = [r[y_field] for r in valid]
    if len(valid) < 3:
        return {'n': len(valid), 'pearson_r': None, 'spearman_rho': None}
    return {
        'n': len(valid),
        'pearson_r': round(transfer.pearson(xs, ys), 6),
        'spearman_rho': round(transfer.spearman(xs, ys), 6),
    }


def hac_regression(rows, y_field):
    valid = [r for r in rows if r.get(y_field) is not None and math.isfinite(r[y_field])]
    if len(valid) < 15:
        return {'n': len(valid), 'slope': None, 'p_value': None, 't_value': None}
    x = np.asarray([r['inverted_funding'] for r in valid], dtype=float)
    y = np.asarray([r[y_field] for r in valid], dtype=float)
    X = sm.add_constant(x)
    fit = sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': 12})
    return {
        'n': len(valid),
        'slope': round(float(fit.params[1]), 8),
        'p_value': round(float(fit.pvalues[1]), 6),
        't_value': round(float(fit.tvalues[1]), 4),
    }


def median(values):
    return float(np.median(np.asarray(values, dtype=float))) if values else None


def tercile_metrics(rows, y_field):
    valid = [r for r in rows if r.get(y_field) is not None and math.isfinite(r[y_field])]
    if len(valid) < 9:
        return {'n': len(valid)}
    sig = np.asarray([r['inverted_funding'] for r in valid], dtype=float)
    q1, q2 = np.quantile(sig, [1/3, 2/3])
    low = [r[y_field] for r in valid if r['inverted_funding'] <= q1]
    high = [r[y_field] for r in valid if r['inverted_funding'] >= q2]
    all_y = [r[y_field] for r in valid]
    low_mean = sum(low) / len(low)
    high_mean = sum(high) / len(high)
    uncond_mean = sum(all_y) / len(all_y)
    low_median = median(low)
    high_median = median(high)
    uncond_median = median(all_y)
    return {
        'n': len(valid),
        'q33_inverted_funding': round(float(q1), 4),
        'q67_inverted_funding': round(float(q2), 4),
        'low_n': len(low),
        'high_n': len(high),
        'unconditional_mean': round(uncond_mean, 6),
        'unconditional_median': round(uncond_median, 6),
        'low_mean': round(low_mean, 6),
        'high_mean': round(high_mean, 6),
        'high_minus_low_mean': round(high_mean - low_mean, 6),
        'high_minus_unconditional_mean': round(high_mean - uncond_mean, 6),
        'low_median': round(low_median, 6),
        'high_median': round(high_median, 6),
        'high_minus_low_median': round(high_median - low_median, 6),
        'high_minus_unconditional_median': round(high_median - uncond_median, 6),
    }


def window_metrics(rows, start, end, transfer):
    sub = [r for r in rows if start <= r['observation_month'] <= end]
    return {
        'start': start,
        'end': end,
        'raw': corr_metrics(sub, 'forward_log_return', transfer),
        'drift_adjusted': corr_metrics(sub, 'drift_excess_return', transfer),
        'raw_terciles': tercile_metrics(sub, 'forward_log_return'),
    }


def leaveout_metrics(rows, episode, transfer):
    sub = [
        r for r in rows
        if not (episode['exclude_start'] <= r['observation_month'] <= episode['exclude_end'])
    ]
    out = corr_metrics(sub, 'forward_log_return', transfer)
    out.update(episode)
    return out


def yearly_diagnostics(rows, transfer):
    years = sorted({r['observation_month'][:4] for r in rows})
    out = []
    for year in years:
        sub = [r for r in rows if r['observation_month'].startswith(year)]
        m = corr_metrics(sub, 'forward_log_return', transfer)
        if m['n'] >= 6:
            out.append({'year': year, **m})
    return out


def asset_result(asset, funding, transfer, contract):
    price, _, price_meta = transfer.fetch_price(asset)
    rows = build_observations(funding, price, transfer)
    full_raw = corr_metrics(rows, 'forward_log_return', transfer)
    full_excess = corr_metrics(rows, 'drift_excess_return', transfer)
    raw_hac = hac_regression(rows, 'forward_log_return')
    excess_hac = hac_regression(rows, 'drift_excess_return')
    raw_terciles = tercile_metrics(rows, 'forward_log_return')
    excess_terciles = tercile_metrics(rows, 'drift_excess_return')

    subperiods = {
        w['id']: window_metrics(rows, w['start'], w['end'], transfer)
        for w in contract['fixed_subperiods']
    }
    leaveouts = {
        e['id']: leaveout_metrics(rows, e, transfer)
        for e in contract['fixed_leaveout_episodes']
    }
    positive_subperiods = sum(
        1 for v in subperiods.values()
        if v['raw']['pearson_r'] is not None and v['raw']['pearson_r'] > 0
    )

    checks = {
        'raw_pearson_positive': full_raw['pearson_r'] is not None and full_raw['pearson_r'] > 0,
        'raw_spearman_positive': full_raw['spearman_rho'] is not None and full_raw['spearman_rho'] > 0,
        'raw_hac_positive_p_lt_010': raw_hac['slope'] is not None and raw_hac['slope'] > 0 and raw_hac['p_value'] < 0.10,
        'raw_tercile_mean_spread_positive': raw_terciles.get('high_minus_low_mean', 0) > 0,
        'raw_tercile_median_spread_positive': raw_terciles.get('high_minus_low_median', 0) > 0,
        'drift_excess_pearson_positive': full_excess['pearson_r'] is not None and full_excess['pearson_r'] > 0,
        'drift_excess_spearman_positive': full_excess['spearman_rho'] is not None and full_excess['spearman_rho'] > 0,
        'drift_excess_tercile_mean_spread_positive': excess_terciles.get('high_minus_low_mean', 0) > 0,
        'all_fixed_leaveouts_positive': all(
            v['pearson_r'] is not None and v['pearson_r'] > 0 for v in leaveouts.values()
        ),
        'at_least_two_of_three_subperiods_positive': positive_subperiods >= 2,
    }
    passed = all(checks.values())
    return {
        'asset': asset,
        'status': 'PASS_RESEARCH_ROBUSTNESS' if passed else 'FAIL_RESEARCH_ROBUSTNESS',
        'price_source': price_meta,
        'first_signal_month': rows[0]['observation_month'] if rows else None,
        'last_signal_month': rows[-1]['observation_month'] if rows else None,
        'raw': full_raw,
        'raw_hac': raw_hac,
        'raw_terciles': raw_terciles,
        'drift_adjusted': full_excess,
        'drift_adjusted_hac': excess_hac,
        'drift_adjusted_terciles': excess_terciles,
        'subperiods': subperiods,
        'fixed_leaveouts': leaveouts,
        'positive_subperiods': positive_subperiods,
        'yearly_diagnostics': yearly_diagnostics(rows, transfer),
        'checks': checks,
        'observations': rows,
    }


def pct_from_log(x):
    return None if x is None else 100.0 * (math.exp(x) - 1.0)


def markdown_report(manifest):
    lines = [
        '# GMLI Funding Equity Contrarian Long-Horizon Test',
        '',
        f"Status: **{manifest['status']}**",
        '',
        'This is a RESEARCH-only test. It does not modify Money Core, Funding Core, production scoring, thresholds, or decision logic.',
        '',
        'Signal: `100 - Funding V2 effective score` (higher = more restrictive Funding). Assets and horizon were frozen before the empirical run: SPY 12M and QQQ 12M only.',
        '',
        '## Positive-market-drift control',
        '',
        '- High-minus-low inverted-Funding tercile spread compares conditional returns within the same sample, so common positive equity drift cancels.',
        '- Known-drift excess subtracts an expanding mean 12M forward return using only earlier observations whose 12M outcome was already completed by the current signal month.',
        '- HAC/Newey-West maxlags=12 addresses overlapping 12M forward returns.',
        '',
        '## Results',
        '',
        '| Asset | N | Raw Pearson | Raw Spearman | HAC p | High-low mean | High-low median | Drift-excess Pearson | Drift-excess high-low mean | Result |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|',
    ]
    for r in manifest['results']:
        rt = r['raw_terciles']
        et = r['drift_adjusted_terciles']
        lines.append(
            f"| {r['asset']} | {r['raw']['n']} | {r['raw']['pearson_r']:.3f} | {r['raw']['spearman_rho']:.3f} | "
            f"{r['raw_hac']['p_value']:.4f} | {pct_from_log(rt['high_minus_low_mean']):+.1f}% | "
            f"{pct_from_log(rt['high_minus_low_median']):+.1f}% | {r['drift_adjusted']['pearson_r']:.3f} | "
            f"{pct_from_log(et['high_minus_low_mean']):+.1f}% | {r['status']} |"
        )
    lines += ['', '## Guardrails', '', '- No asset, horizon, lag, transform, threshold, or parameter search.', '- No FDR claim.', '- Promotion is not allowed by this test alone.', '']
    return '\n'.join(lines)


def run(as_of, build_full=False, output_dir='research/funding-equity-contrarian-long/latest'):
    contract = load_contract()
    transfer = load_module(TRANSFER_RUNNER, 'gmli_money_v2_transfer_helpers_long_contrarian')
    funding = load_funding_history()
    results = [asset_result(asset, funding, transfer, contract) for asset in ASSETS]
    overall = all(r['status'].startswith('PASS_') for r in results)
    manifest = {
        'status': 'PASS_LONG_HORIZON_EQUITY_CONTRARIAN_RESEARCH' if overall else 'FAIL_LONG_HORIZON_EQUITY_CONTRARIAN_RESEARCH',
        'test_version': VERSION,
        'evidence_tier': 'RESEARCH',
        'as_of': as_of.isoformat(),
        'production_modified': False,
        'money_core_modified': False,
        'funding_core_modified': False,
        'promotion_allowed': False,
        'positive_market_drift_explicitly_controlled': True,
        'contract': contract,
        'results': [{k: v for k, v in r.items() if k != 'observations'} for r in results],
    }
    if build_full:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / 'result.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        (out / 'REPORT.md').write_text(markdown_report(manifest), encoding='utf-8')
        with (out / 'observations.csv').open('w', newline='', encoding='utf-8') as f:
            fields = [
                'asset', 'observation_month', 'available_date', 'effective_score', 'inverted_funding', 'regime',
                'price_start_month', 'price_end_month', 'forward_log_return', 'known_drift_n',
                'known_drift_baseline', 'drift_excess_return'
            ]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in results:
                for obs in r['observations']:
                    w.writerow({'asset': r['asset'], **obs})
    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--as-of', default=date.today().isoformat())
    p.add_argument('--build-full', action='store_true')
    p.add_argument('--output-dir', default='research/funding-equity-contrarian-long/latest')
    args = p.parse_args()
    result = run(date.fromisoformat(args.as_of), build_full=args.build_full, output_dir=args.output_dir)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
