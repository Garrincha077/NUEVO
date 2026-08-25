#!/usr/bin/env python3
"""Guarded refresh for promoted Fiscal V2.

Fiscal V2 may advance only the active data snapshot. The frozen construction,
promotion evidence and zero automatic global-conviction weight cannot change in
a refresh. Source bytes are verified against the prospective Fiscal manifest,
available-date regression fails closed, and production files are written only
after every guard passes.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import pathlib
import re
import shutil
import sys
import tempfile
from datetime import date, datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
CANDIDATE_RUNNER = ROOT / 'scripts' / 'build-fiscal-v2.py'
ACTIVE_PATH = ROOT / 'lib' / 'fiscal-v2-active.js'
PROSPECTIVE_DIR = ROOT / 'research' / 'fiscal-prospective' / 'latest'
PROSPECTIVE_MANIFEST = PROSPECTIVE_DIR / 'manifest.json'
LATEST_DIR = ROOT / 'research' / 'fiscal-v2' / 'latest'
PROMOTION = ROOT / 'research' / 'fiscal-v2' / 'promotion.lock.json'
CANDIDATE_RESULT = ROOT / 'research' / 'fiscal-v2' / 'CANDIDATE_1_RESULT.json'
USEFULNESS_RESULT = ROOT / 'research' / 'fiscal-v2' / 'USEFULNESS_RESULT.json'
VERSION = 'GMLI_FISCAL_V2_DEFICIT_IMPULSE'
CANDIDATE = 'GMLI_FISCAL_V2_CANDIDATE_1'
LEGACY_AVAILABLE_DATE = '2026-07-31'
REQUIRED_SERIES = (
    'MTSDS133FMS', 'GDP', 'GFDEBTN',
    'A091RC1Q027SBEA', 'FGRECPT', 'FGEXPND'
)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_available_date():
    if not ACTIVE_PATH.exists():
        return LEGACY_AVAILABLE_DATE
    match = re.search(r"available_date:\s*'([^']+)'", ACTIVE_PATH.read_text(encoding='utf-8'))
    return match.group(1) if match else LEGACY_AVAILABLE_DATE


def validate_static_promotion():
    promotion = read_json(PROMOTION)
    candidate_result = read_json(CANDIDATE_RESULT)
    usefulness = read_json(USEFULNESS_RESULT)
    errors = []

    if promotion.get('status') != 'PASS_FISCAL_V2_PRODUCTION_PROMOTION':
        errors.append('promotion lock not PASS')
    if promotion.get('promoted_version') != VERSION or promotion.get('candidate_version') != CANDIDATE:
        errors.append('promotion version mismatch')
    if promotion.get('money_core_modified') is not False or promotion.get('funding_v2_modified') is not False:
        errors.append('promotion must not modify Money Core or Funding V2')
    if promotion.get('global_conviction_rubric_modified') is not False:
        errors.append('global conviction rubric must remain unchanged')
    if promotion.get('automatic_global_conviction_weight') != 0:
        errors.append('Fiscal automatic global conviction weight must remain zero')
    if promotion.get('universal_asset_return_claim') is not False:
        errors.append('universal return claim must remain false')

    if candidate_result.get('decision') != 'PASS_FIXED_CONSTRUCTION_SANITY':
        errors.append('frozen Candidate 1 construction result not PASS')
    if candidate_result.get('candidate_version') != CANDIDATE:
        errors.append('frozen Candidate 1 version mismatch')
    sanity = candidate_result.get('pandemic_support_sanity') or {}
    if sanity.get('pass') is not True:
        errors.append('frozen pandemic construction sanity not PASS')

    if usefulness.get('decision') != 'PASS_NARROW_FISCAL_USEFULNESS':
        errors.append('frozen narrow usefulness result not PASS')
    primary = usefulness.get('primary_results') or []
    if len(primary) != 1 or primary[0].get('id') != 'SPY_FISCAL_V2_12M' or primary[0].get('direction_pass') is not True:
        errors.append('frozen SPY 12M usefulness gate not 1/1 PASS')
    no_search = usefulness.get('no_search') or {}
    for key in ('asset_search', 'horizon_search', 'lag_search', 'parameter_search', 'threshold_search', 'subperiod_search', 'fdr_claim'):
        if no_search.get(key) is not False:
            errors.append(f'usefulness no-search contract changed: {key}')

    if errors:
        raise ValueError('; '.join(errors))
    return promotion, candidate_result, usefulness


def validate_prospective_sources(candidate):
    manifest = read_json(PROSPECTIVE_MANIFEST)
    if manifest.get('contract') != 'GMLI prospective Fiscal raw capture v1':
        raise ValueError('unexpected prospective Fiscal manifest contract')
    if manifest.get('production_state_modified') is not False:
        raise ValueError('prospective Fiscal archive claims production modification')

    series = manifest.get('series') or {}
    candidate_sources = candidate.get('sources') or {}
    verified = {}
    for series_id in REQUIRED_SERIES:
        meta = series.get(series_id) or {}
        candidate_meta = candidate_sources.get(series_id) or {}
        path = PROSPECTIVE_DIR / f'{series_id}.csv'
        if not path.exists():
            raise ValueError(f'missing prospective Fiscal raw file {series_id}')
        expected = meta.get('raw_sha256')
        actual = sha256(path)
        if not expected or actual != expected:
            raise ValueError(f'prospective source hash mismatch for {series_id}: {actual} != {expected}')
        if candidate_meta.get('raw_sha256') != expected:
            raise ValueError(f'candidate/source manifest hash mismatch for {series_id}')
        verified[series_id] = {
            'file': f'research/fiscal-prospective/latest/{series_id}.csv',
            'raw_sha256': actual,
            'bytes': path.stat().st_size,
            'latest_observation_date': meta.get('latest_observation_date'),
            'retrieved_at': meta.get('retrieved_at'),
            'role': meta.get('role')
        }
    return manifest, verified


def validate_candidate(candidate, old_date):
    errors = []
    if candidate.get('status') != 'PASS_FIXED_CONSTRUCTION_SANITY':
        errors.append('Candidate 1 fixed construction sanity not PASS')
    if candidate.get('candidate_version') != CANDIDATE:
        errors.append('candidate version mismatch')
    if candidate.get('production_modified') is not False:
        errors.append('candidate claims production modification')
    if candidate.get('money_core_modified') is not False or candidate.get('funding_v2_modified') is not False:
        errors.append('candidate must not modify Money/Funding')
    if any(v is not False for v in (candidate.get('no_search') or {}).values()):
        errors.append('candidate no-search contract changed')

    latest = candidate.get('latest_eligible') or {}
    required = (
        'observation_month', 'available_date', 'ttm_deficit_billions',
        'gdp_observation_month', 'deficit_pct_gdp', 'fiscal_impulse_pp',
        'deficit_level_z', 'fiscal_impulse_z', 'composite_z', 'score', 'regime'
    )
    if any(latest.get(k) is None for k in required):
        errors.append('latest eligible Fiscal V2 row incomplete')
    new_date = latest.get('available_date')
    if old_date and new_date and new_date < old_date:
        errors.append(f'available-date regression {old_date} -> {new_date}')
    score = latest.get('score')
    if not isinstance(score, (int, float)) or not (0 <= score <= 100):
        errors.append('Fiscal V2 score sanity failure')
    if latest.get('regime') not in ('RESTRICTIVE', 'NEUTRAL', 'SUPPORTIVE'):
        errors.append('Fiscal V2 regime invalid')
    sanity = candidate.get('pandemic_support_sanity') or {}
    if sanity.get('pass') is not True:
        errors.append('pandemic construction sanity not PASS')

    if errors:
        raise ValueError('; '.join(errors))
    return latest


def render_active(latest, refreshed_at):
    return f"""// Generated/refreshable data snapshot for promoted Fiscal V2.\n// Frozen methodology and promotion evidence live under research/fiscal-v2;\n// refreshes may update only validated data-vintage fields.\nexport const ACTIVE_FISCAL_V2 = {{\n  version: '{VERSION}',\n  observation_month: '{latest['observation_month']}',\n  available_date: '{latest['available_date']}',\n  z: {latest['composite_z']},\n  score: {latest['score']},\n  regime: '{latest['regime']}',\n  ttm_deficit_billions: {latest['ttm_deficit_billions']},\n  deficit_pct_gdp: {latest['deficit_pct_gdp']},\n  fiscal_impulse_pp: {latest['fiscal_impulse_pp']},\n  deficit_level_z: {latest['deficit_level_z']},\n  fiscal_impulse_z: {latest['fiscal_impulse_z']},\n  gdp_observation_month: '{latest['gdp_observation_month']}',\n  source_manifest: 'research/fiscal-v2/latest/manifest.lock.json',\n  refreshed_at: '{refreshed_at}'\n}};\n"""


def write_history(path, history):
    fields = [
        'observation_month', 'available_date', 'score', 'regime', 'composite_z',
        'deficit_level_z', 'fiscal_impulse_z', 'deficit_pct_gdp', 'fiscal_impulse_pp',
        'ttm_deficit_billions', 'gdp_observation_month', 'gdp_available_date', 'gdp_billions_saar'
    ]
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in history:
            writer.writerow({
                'observation_month': row['observation_month'],
                'available_date': row['available_date'],
                'score': f"{row['score']:.10f}",
                'regime': row['regime'],
                'composite_z': f"{row['composite_z']:.10f}",
                'deficit_level_z': f"{row['deficit_level_z']:.10f}",
                'fiscal_impulse_z': f"{row['fiscal_impulse_z']:.10f}",
                'deficit_pct_gdp': f"{row['deficit_pct_gdp']:.10f}",
                'fiscal_impulse_pp': f"{row['fiscal_impulse_pp']:.10f}",
                'ttm_deficit_billions': f"{row['ttm_deficit_billions']:.10f}",
                'gdp_observation_month': row['gdp_observation_month'],
                'gdp_available_date': row['gdp_available_date'],
                'gdp_billions_saar': f"{row['gdp_billions_saar']:.10f}"
            })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', default=date.today().isoformat())
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of)

    try:
        promotion, candidate_result, usefulness = validate_static_promotion()
        candidate_module = load_module(CANDIDATE_RUNNER, 'gmli_fiscal_v2_refresh_candidate')
        candidate = candidate_module.build(as_of)
        old_date = current_available_date()
        latest = validate_candidate(candidate, old_date)
        _, verified_sources = validate_prospective_sources(candidate)
        new_date = latest['available_date']
        archive_missing = not (LATEST_DIR / 'manifest.lock.json').exists()
        active_missing = not ACTIVE_PATH.exists()
        changed = old_date != new_date or archive_missing or active_missing
        refreshed_at = now_iso()

        if args.apply and changed:
            with tempfile.TemporaryDirectory(prefix='gmli-fiscal-v2-') as tmp:
                stage = pathlib.Path(tmp)
                raw_dir = stage / 'raw'
                raw_dir.mkdir(parents=True)
                for series_id in REQUIRED_SERIES:
                    shutil.copy2(PROSPECTIVE_DIR / f'{series_id}.csv', raw_dir / f'{series_id}.csv')
                write_history(stage / 'history.csv', candidate['history'])
                manifest = {
                    'status': 'PASS_ACTIVE_FISCAL_V2_REFRESH_GUARDS',
                    'version': VERSION,
                    'candidate_version': CANDIDATE,
                    'built_at': refreshed_at,
                    'as_of': as_of.isoformat(),
                    'previous_available_date': old_date,
                    'latest_eligible': latest,
                    'candidate_construction_gate': candidate_result['decision'],
                    'frozen_usefulness_gate': usefulness['decision'],
                    'promotion_lock': promotion['status'],
                    'money_core_modified': False,
                    'funding_v2_modified': False,
                    'global_conviction_rubric_modified': False,
                    'automatic_global_conviction_weight': 0,
                    'methodology_modified': False,
                    'sources': verified_sources,
                    'raw_archive': {
                        sid: {
                            'file': f'raw/{sid}.csv',
                            'sha256': verified_sources[sid]['raw_sha256'],
                            'bytes': verified_sources[sid]['bytes']
                        }
                        for sid in REQUIRED_SERIES
                    },
                    'history_rows': len(candidate['history']),
                    'history_start': candidate['history_start'],
                    'history_end': candidate['history_end'],
                    'guardrail': 'Fiscal V2 is an OVERLAY. Fixed SPY 12M usefulness passed, but automatic global conviction weight remains zero pending a separately versioned decision-engine test.'
                }
                (stage / 'manifest.lock.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

                # Replace last-good files only after all static, candidate and source guards pass.
                if LATEST_DIR.exists():
                    shutil.rmtree(LATEST_DIR)
                shutil.copytree(stage, LATEST_DIR)
                ACTIVE_PATH.write_text(render_active(latest, refreshed_at), encoding='utf-8')

        print(json.dumps({
            'status': 'PASS_ACTIVE_FISCAL_V2_REFRESH_GUARDS',
            'version': VERSION,
            'candidate_version': CANDIDATE,
            'previous_available_date': old_date,
            'new_available_date': new_date,
            'observation_month': latest['observation_month'],
            'score': latest['score'],
            'regime': latest['regime'],
            'construction_gate': candidate_result['decision'],
            'usefulness_gate': usefulness['decision'],
            'promotion_lock': promotion['status'],
            'global_conviction_rubric_modified': False,
            'automatic_global_conviction_weight': 0,
            'changed': changed,
            'applied': args.apply,
            'money_core_modified': False,
            'funding_v2_modified': False
        }, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            'status': 'FAIL_ACTIVE_FISCAL_V2_REFRESH_GUARDS',
            'error': str(exc),
            'production_files_written': False,
            'last_good_preserved': True,
            'money_core_modified': False,
            'funding_v2_modified': False,
            'global_conviction_rubric_modified': False
        }, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
