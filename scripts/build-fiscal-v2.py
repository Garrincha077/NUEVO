#!/usr/bin/env python3
import argparse
import calendar
import csv
import json
import math
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / 'research' / 'fiscal-v2-candidate-1-contract.json'
INPUT_DIR = ROOT / 'research' / 'fiscal-prospective' / 'latest'
MANIFEST_PATH = INPUT_DIR / 'manifest.json'
VERSION = 'GMLI_FISCAL_V2_CANDIDATE_1'
LEGACY = {
    'available_date': '2026-07-31',
    'score': 52.539556447652046,
    'z': 0.1523733868591229,
    'regime': 'NEUTRAL',
    'mode': 'STRICT_ACTUAL_RELEASE',
}


def add_months_ym(ym, months):
    y, m = map(int, ym.split('-'))
    idx = y * 12 + (m - 1) + months
    return f'{idx // 12:04d}-{idx % 12 + 1:02d}'


def month_end(ym):
    y, m = map(int, ym.split('-'))
    return date(y, m, calendar.monthrange(y, m)[1])


def score_available_date(observation_month):
    return month_end(add_months_ym(observation_month, 1)).isoformat()


def gdp_available_date(observation_month):
    return month_end(add_months_ym(observation_month, 3)).isoformat()


def score_from_z(z):
    return max(0.0, min(100.0, 50.0 + (50.0 / 3.0) * z))


def regime(score):
    if score < 40:
        return 'RESTRICTIVE'
    if score > 60:
        return 'SUPPORTIVE'
    return 'NEUTRAL'


def read_series(series_id):
    path = INPUT_DIR / f'{series_id}.csv'
    rows = []
    with path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = row.get('observation_date') or row.get('DATE') or row.get('date')
            raw = row.get(series_id)
            if not d or raw in (None, '', '.'):
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            rows.append({'date': d, 'month': d[:7], 'value': value})
    rows.sort(key=lambda x: x['date'])
    if not rows:
        raise RuntimeError(f'no numeric observations for {series_id}')
    return rows


def validate_contract():
    contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    assert contract['candidate_version'] == VERSION
    assert contract['status'] == 'FROZEN_RESEARCH_CANDIDATE'
    assert contract['production_replacement_allowed'] is False
    assert contract['money_core_modified'] is False
    assert contract['funding_v2_modified'] is False
    assert contract['standardization']['window_months'] == 120
    assert contract['standardization']['minimum_months'] == 24
    assert contract['standardization']['ddof'] == 0
    assert contract['aggregation']['components'][0] == {'id': 'DEFICIT_LEVEL_Z', 'weight': 0.5}
    assert contract['aggregation']['components'][1] == {'id': 'FISCAL_IMPULSE_Z', 'weight': 0.5}
    assert all(v is False for v in contract['no_search'].values())
    return contract


def rolling_z(values, current, window=120, minimum=24):
    usable = [x for x in values[-window:] if x is not None and math.isfinite(x)]
    if len(usable) < minimum:
        return None
    mean = sum(usable) / len(usable)
    var = sum((x - mean) ** 2 for x in usable) / len(usable)
    sd = math.sqrt(var)
    z = 0.0 if sd == 0 else (current - mean) / sd
    return max(-3.0, min(3.0, z))


def build(as_of):
    contract = validate_contract()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    if manifest.get('contract') != 'GMLI prospective Fiscal raw capture v1':
        raise RuntimeError('unexpected prospective Fiscal manifest contract')
    if manifest.get('production_state_modified') is not False:
        raise RuntimeError('prospective Fiscal archive must not modify production state')

    mts = read_series('MTSDS133FMS')
    gdp = read_series('GDP')
    mts_map = {x['month']: x['value'] for x in mts}
    gdp_with_availability = [
        {**x, 'available_date': gdp_available_date(x['month'])}
        for x in gdp
    ]

    ratio_rows = []
    for x in mts:
        month = x['month']
        months = [add_months_ym(month, -i) for i in range(11, -1, -1)]
        if any(m not in mts_map for m in months):
            continue
        available_date = score_available_date(month)
        eligible_gdp = [g for g in gdp_with_availability if g['available_date'] <= available_date]
        if not eligible_gdp:
            continue
        latest_gdp = eligible_gdp[-1]
        ttm_deficit_billions = -sum(mts_map[m] for m in months) / 1000.0
        deficit_pct_gdp = 100.0 * ttm_deficit_billions / latest_gdp['value']
        ratio_rows.append({
            'observation_month': month,
            'available_date': available_date,
            'ttm_deficit_billions': ttm_deficit_billions,
            'gdp_observation_month': latest_gdp['month'],
            'gdp_available_date': latest_gdp['available_date'],
            'gdp_billions_saar': latest_gdp['value'],
            'deficit_pct_gdp': deficit_pct_gdp,
        })

    ratio_by_month = {x['observation_month']: x for x in ratio_rows}
    component_rows = []
    for row in ratio_rows:
        prior = ratio_by_month.get(add_months_ym(row['observation_month'], -12))
        if not prior:
            continue
        component_rows.append({
            **row,
            'fiscal_impulse_pp': row['deficit_pct_gdp'] - prior['deficit_pct_gdp'],
        })

    history = []
    level_values = []
    impulse_values = []
    for row in component_rows:
        level_values.append(row['deficit_pct_gdp'])
        impulse_values.append(row['fiscal_impulse_pp'])
        level_z = rolling_z(level_values, row['deficit_pct_gdp'])
        impulse_z = rolling_z(impulse_values, row['fiscal_impulse_pp'])
        if level_z is None or impulse_z is None:
            continue
        composite_z = 0.5 * level_z + 0.5 * impulse_z
        score = score_from_z(composite_z)
        history.append({
            **row,
            'deficit_level_z': level_z,
            'fiscal_impulse_z': impulse_z,
            'composite_z': composite_z,
            'score': score,
            'regime': regime(score),
        })

    eligible = [x for x in history if date.fromisoformat(x['available_date']) <= as_of]
    if not eligible:
        raise RuntimeError('no eligible Fiscal V2 candidate history')
    latest = eligible[-1]
    by_month = {x['observation_month']: x for x in history}
    sanity_contract = contract['fixed_initial_gates']['pandemic_support_sanity']
    sanity_row = by_month.get(sanity_contract['observation_month'])
    sanity_pass = bool(sanity_row and sanity_row['regime'] == sanity_contract['expected_regime'])
    construction_status = 'PASS_FIXED_CONSTRUCTION_SANITY' if sanity_pass else 'FAIL_FIXED_CONSTRUCTION_SANITY'

    latest_vs_legacy = {
        **LEGACY,
        'candidate_available_date': latest['available_date'],
        'candidate_score': latest['score'],
        'candidate_regime': latest['regime'],
        'regime_match': latest['regime'] == LEGACY['regime'],
        'score_delta': latest['score'] - LEGACY['score'],
        'forced_match_required': False,
    }

    sources = {
        series_id: {
            'latest_observation_date': meta.get('latest_observation_date'),
            'raw_sha256': meta.get('raw_sha256'),
            'retrieved_at': meta.get('retrieved_at'),
            'role': meta.get('role'),
        }
        for series_id, meta in (manifest.get('series') or {}).items()
    }

    return {
        'status': construction_status,
        'candidate_version': VERSION,
        'evidence_tier': 'RESEARCH',
        'target_role': 'FISCAL_CONVICTION_OVERLAY_CANDIDATE',
        'as_of': as_of.isoformat(),
        'production_modified': False,
        'money_core_modified': False,
        'funding_v2_modified': False,
        'legacy_fiscal_modified': False,
        'legacy_reproduction_decision': 'STOP_LEGACY_REVERSE_ENGINEERING_BUILD_VERSIONED_V2',
        'historical_data_semantics': contract['historical_data_semantics'],
        'no_search': contract['no_search'],
        'latest_eligible': latest,
        'legacy_current_comparator': latest_vs_legacy,
        'pandemic_support_sanity': {
            **sanity_contract,
            'actual_regime': sanity_row['regime'] if sanity_row else None,
            'actual_score': sanity_row['score'] if sanity_row else None,
            'pass': sanity_pass,
        },
        'promotion_eligible': False,
        'promotion_blocker': 'NARROW_USEFULNESS_GATE_NOT_RUN' if sanity_pass else 'FAIL_FIXED_CONSTRUCTION_SANITY',
        'history_start': history[0]['observation_month'],
        'history_end': history[-1]['observation_month'],
        'history_rows': len(history),
        'sources': sources,
        'contract': contract,
        'history': history,
    }


def write_outputs(result, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = {k: v for k, v in result.items() if k != 'history'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    fields = [
        'observation_month', 'available_date', 'score', 'regime', 'composite_z',
        'deficit_level_z', 'fiscal_impulse_z', 'deficit_pct_gdp', 'fiscal_impulse_pp',
        'ttm_deficit_billions', 'gdp_observation_month', 'gdp_available_date', 'gdp_billions_saar',
    ]
    with (out / 'history.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in result['history']:
            writer.writerow({
                'observation_month': row['observation_month'],
                'available_date': row['available_date'],
                'score': f"{row['score']:.8f}",
                'regime': row['regime'],
                'composite_z': f"{row['composite_z']:.8f}",
                'deficit_level_z': f"{row['deficit_level_z']:.8f}",
                'fiscal_impulse_z': f"{row['fiscal_impulse_z']:.8f}",
                'deficit_pct_gdp': f"{row['deficit_pct_gdp']:.8f}",
                'fiscal_impulse_pp': f"{row['fiscal_impulse_pp']:.8f}",
                'ttm_deficit_billions': f"{row['ttm_deficit_billions']:.8f}",
                'gdp_observation_month': row['gdp_observation_month'],
                'gdp_available_date': row['gdp_available_date'],
                'gdp_billions_saar': f"{row['gdp_billions_saar']:.8f}",
            })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', default=date.today().isoformat())
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--build-full', action='store_true')
    parser.add_argument('--output-dir', default='research/fiscal-v2/candidate-1-latest')
    args = parser.parse_args()
    result = build(date.fromisoformat(args.as_of))
    if args.build_full and not args.validate_only:
        write_outputs(result, args.output_dir)
    summary = {k: v for k, v in result.items() if k != 'history'}
    print(json.dumps(summary, indent=2))
    return 0 if result['status'].startswith('PASS_') else 2


if __name__ == '__main__':
    raise SystemExit(main())
