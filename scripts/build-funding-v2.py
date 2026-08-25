#!/usr/bin/env python3
import argparse
import csv
import io
import json
import math
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

VERSION = 'GMLI_FUNDING_V2_CANDIDATE_1'
DEFAULT_AS_OF = date.today()

SERIES = {
    'ANFCI': {'aggregation': 'mean', 'sign': -1.0, 'role': 'broad_financial_conditions'},
    'DFII10': {'aggregation': 'mean', 'sign': -1.0, 'role': 'real_discount_rate'},
    'THREEFYTP10': {'aggregation': 'mean', 'sign': -1.0, 'role': 'term_premium'},
    'WRESBAL': {'aggregation': 'last', 'sign': 1.0, 'role': 'reserve_liquidity_3m_impulse'},
}

LEGACY = {'available_date': '2026-07-31', 'score': 36.035410932024234, 'regime': 'RESTRICTIVE'}
STRESS_WINDOWS = {'2008-10': 'RESTRICTIVE', '2020-03': 'RESTRICTIVE'}


def month_key(d):
    return f'{d.year:04d}-{d.month:02d}'


def month_add(m, n):
    y, mo = map(int, m.split('-'))
    idx = y * 12 + (mo - 1) + n
    return f'{idx // 12:04d}-{idx % 12 + 1:02d}'


def available_date_for_observation_month(m):
    y, mo = map(int, m.split('-'))
    if mo == 12:
        first_after = date(y + 1, 2, 1)
    else:
        nm = mo + 1
        if nm == 12:
            first_after = date(y + 1, 1, 1)
        else:
            first_after = date(y, nm + 1, 1)
    return first_after - timedelta(days=1)


def fetch_series(series_id):
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}'
    req = urllib.request.Request(url, headers={'User-Agent': 'gmli-funding-v2/1.0'})
    with urllib.request.urlopen(req, timeout=45) as response:
        raw = response.read()
    text = raw.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        ds = row.get('DATE') or row.get('observation_date') or next(iter(row.values()))
        vs = row.get(series_id)
        if vs in (None, '', '.'):
            continue
        try:
            rows.append((date.fromisoformat(ds), float(vs)))
        except (ValueError, TypeError):
            continue
    if not rows:
        raise RuntimeError(f'no usable observations for {series_id}')
    return url, raw, rows


def aggregate_monthly(rows, method):
    buckets = defaultdict(list)
    for d, v in rows:
        buckets[month_key(d)].append((d, v))
    out = {}
    for m, vals in buckets.items():
        vals.sort()
        if method == 'mean':
            out[m] = sum(v for _, v in vals) / len(vals)
        elif method == 'last':
            out[m] = vals[-1][1]
        else:
            raise ValueError(method)
    return out


def rolling_z(values, window=120, min_periods=36):
    out = {}
    ordered = sorted(values)
    for i, m in enumerate(ordered):
        start = max(0, i - window + 1)
        sample = [values[x] for x in ordered[start:i + 1] if values.get(x) is not None]
        if len(sample) < min_periods:
            continue
        mu = sum(sample) / len(sample)
        var = sum((x - mu) ** 2 for x in sample) / len(sample)
        sd = math.sqrt(var)
        if sd <= 0:
            continue
        out[m] = (values[m] - mu) / sd
    return out


def regime(score):
    if score < 40:
        return 'RESTRICTIVE'
    if score > 60:
        return 'SUPPORTIVE'
    return 'NEUTRAL'


def build(as_of):
    monthly = {}
    source_meta = {}
    for sid, spec in SERIES.items():
        url, raw, rows = fetch_series(sid)
        monthly[sid] = aggregate_monthly(rows, spec['aggregation'])
        source_meta[sid] = {
            'url': url,
            'bytes': len(raw),
            'first_observation': rows[0][0].isoformat(),
            'last_observation': rows[-1][0].isoformat(),
            'last_value': rows[-1][1],
        }

    reserves_level = monthly['WRESBAL']
    reserve_impulse = {}
    for m, level in reserves_level.items():
        prev = month_add(m, -3)
        if prev in reserves_level and reserves_level[prev] > 0:
            reserve_impulse[m] = 100.0 * (level / reserves_level[prev] - 1.0)

    transformed = {
        'ANFCI': monthly['ANFCI'],
        'DFII10': monthly['DFII10'],
        'THREEFYTP10': monthly['THREEFYTP10'],
        'WRESBAL_3M_PCT': reserve_impulse,
    }
    component_specs = {
        'ANFCI': SERIES['ANFCI'],
        'DFII10': SERIES['DFII10'],
        'THREEFYTP10': SERIES['THREEFYTP10'],
        'WRESBAL_3M_PCT': SERIES['WRESBAL'],
    }
    zmaps = {k: rolling_z(v) for k, v in transformed.items()}
    months = sorted(set.intersection(*(set(z.keys()) for z in zmaps.values())))
    history = []
    for m in months:
        zs = {}
        for key, zmap in zmaps.items():
            raw_z = zmap[m] * component_specs[key]['sign']
            zs[key] = max(-3.0, min(3.0, raw_z))
        composite_z = sum(zs.values()) / len(zs)
        score = max(0.0, min(100.0, 50.0 + (50.0 / 3.0) * composite_z))
        avail = available_date_for_observation_month(m)
        history.append({
            'observation_month': m,
            'available_date': avail.isoformat(),
            'score': score,
            'regime': regime(score),
            'composite_supportive_z': composite_z,
            'component_supportive_z': zs,
            'raw': {k: transformed[k][m] for k in transformed},
        })

    eligible = [x for x in history if date.fromisoformat(x['available_date']) <= as_of]
    if not eligible:
        raise RuntimeError('no eligible Funding V2 history as of requested date')
    latest = eligible[-1]
    by_month = {x['observation_month']: x for x in history}
    legacy_direction_match = latest['available_date'] == LEGACY['available_date'] and latest['regime'] == LEGACY['regime']
    stress = {}
    for m, expected in STRESS_WINDOWS.items():
        got = by_month.get(m)
        stress[m] = {
            'expected': expected,
            'actual': got['regime'] if got else None,
            'score': got['score'] if got else None,
            'pass': bool(got and got['regime'] == expected),
        }

    return {
        'candidate_version': VERSION,
        'evidence_tier': 'RESEARCH',
        'role': 'FUNDING_CONDITIONS_OVERLAY_CANDIDATE',
        'as_of': as_of.isoformat(),
        'methodology_frozen_candidate': True,
        'production_modified': False,
        'parameter_search': False,
        'latest_eligible': latest,
        'legacy_current_comparator': {**LEGACY, 'direction_match': legacy_direction_match},
        'stress_window_sanity': stress,
        'directional_gate_pass': legacy_direction_match and all(x['pass'] for x in stress.values()),
        'promotion_eligible': False,
        'promotion_blocker': 'NARROW_USEFULNESS_CONVICTION_GATE_NOT_RUN',
        'history_start': history[0]['observation_month'],
        'history_end': history[-1]['observation_month'],
        'history_rows': len(history),
        'sources': source_meta,
        'history': history,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', default=DEFAULT_AS_OF.isoformat())
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--build-full', action='store_true')
    parser.add_argument('--output-dir', default='research/funding-v2/latest')
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of)
    result = build(as_of)
    summary = {k: v for k, v in result.items() if k != 'history'}
    if args.build_full:
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        with (out / 'history.csv').open('w', newline='', encoding='utf-8') as f:
            fields = [
                'observation_month', 'available_date', 'score', 'regime', 'composite_supportive_z',
                'anfci_z', 'real_yield_z', 'term_premium_z', 'reserves_z',
                'anfci', 'dfii10', 'term_premium', 'reserves_3m_pct',
            ]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for x in result['history']:
                writer.writerow({
                    'observation_month': x['observation_month'],
                    'available_date': x['available_date'],
                    'score': f"{x['score']:.8f}",
                    'regime': x['regime'],
                    'composite_supportive_z': f"{x['composite_supportive_z']:.8f}",
                    'anfci_z': f"{x['component_supportive_z']['ANFCI']:.8f}",
                    'real_yield_z': f"{x['component_supportive_z']['DFII10']:.8f}",
                    'term_premium_z': f"{x['component_supportive_z']['THREEFYTP10']:.8f}",
                    'reserves_z': f"{x['component_supportive_z']['WRESBAL_3M_PCT']:.8f}",
                    'anfci': x['raw']['ANFCI'],
                    'dfii10': x['raw']['DFII10'],
                    'term_premium': x['raw']['THREEFYTP10'],
                    'reserves_3m_pct': x['raw']['WRESBAL_3M_PCT'],
                })
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
