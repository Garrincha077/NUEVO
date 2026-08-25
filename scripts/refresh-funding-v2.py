#!/usr/bin/env python3
"""Guarded refresh for promoted Funding V2.

This script never changes methodology. It can advance only the active monthly
Funding V2 data snapshot after frozen promotion evidence, directional sanity,
source-byte provenance and non-regression checks pass. Any failure exits before
writing production files, preserving the last-good snapshot.
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_RUNNER = ROOT / 'scripts' / 'build-funding-v2.py'
CANDIDATE_RUNNER = ROOT / 'scripts' / 'build-funding-v2-candidate2.py'
ACTIVE_PATH = ROOT / 'lib' / 'funding-v2-active.js'
LATEST_DIR = ROOT / 'research' / 'funding-v2' / 'latest'
PROMOTION = ROOT / 'research' / 'funding-v2' / 'promotion.lock.json'
CANDIDATE1_RESULT = ROOT / 'research' / 'funding-v2' / 'CANDIDATE_1_RESULT.json'
USEFULNESS_RESULT = ROOT / 'research' / 'funding-v2' / 'USEFULNESS_RESULT.json'
VERSION = 'GMLI_FUNDING_V2_EFFECTIVE_CONDITIONS'
CANDIDATE = 'GMLI_FUNDING_V2_CANDIDATE_2'


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def current_available_date():
    if not ACTIVE_PATH.exists():
        return None
    m = re.search(r"available_date:\s*'([^']+)'", ACTIVE_PATH.read_text(encoding='utf-8'))
    return m.group(1) if m else None


def validate_static_promotion():
    promotion = read_json(PROMOTION)
    c1 = read_json(CANDIDATE1_RESULT)
    usefulness = read_json(USEFULNESS_RESULT)
    errors = []
    if promotion.get('status') != 'PASS_FUNDING_V2_PRODUCTION_PROMOTION':
        errors.append('promotion lock not PASS')
    if promotion.get('promoted_version') != VERSION or promotion.get('candidate_version') != CANDIDATE:
        errors.append('promotion version mismatch')
    if promotion.get('money_core_modified') is not False:
        errors.append('promotion must not modify Money Core')
    if promotion.get('bounded_conviction_weight_unchanged') is not True:
        errors.append('Funding conviction weight must remain bounded/unchanged')
    if promotion.get('universal_asset_return_claim') is not False:
        errors.append('universal asset-return claim must remain false')
    if c1.get('decision') != 'REJECTED_FOR_PROMOTION' or c1.get('gate') != 'FAIL_FIXED_DIRECTIONAL_SANITY':
        errors.append('Candidate 1 rejection audit changed')
    if usefulness.get('decision') != 'PASS_NARROW_FUNDING_USEFULNESS':
        errors.append('frozen usefulness gate not PASS')
    primary = usefulness.get('primary_results') or []
    if len(primary) != 2 or not all(x.get('direction_pass') is True for x in primary):
        errors.append('frozen DBC usefulness gate not 2/2')
    no_search = usefulness.get('no_search') or {}
    if any(no_search.get(k) is not False for k in ('asset_search','horizon_search','lag_search','parameter_search','threshold_search','fdr_claim')):
        errors.append('usefulness no-search contract changed')
    if errors:
        raise ValueError('; '.join(errors))
    return promotion, usefulness


def validate_candidate(funding, old_date):
    errors = []
    if funding.get('candidate_version') != CANDIDATE:
        errors.append('candidate version mismatch')
    if funding.get('directional_gate_pass') is not True:
        errors.append('Candidate 2 fixed directional gate not PASS')
    if funding.get('parameter_search') is not False:
        errors.append('parameter search must remain false')
    latest = funding.get('latest_eligible') or {}
    required = ('observation_month','available_date','effective_score','regime','structural_support_score','observed_conditions_score','structural_support_z','observed_conditions_z','component_supportive_z')
    if any(latest.get(k) is None for k in required):
        errors.append('latest eligible row incomplete')
    new_date = latest.get('available_date')
    if old_date and new_date and new_date < old_date:
        errors.append(f'date regression {old_date} -> {new_date}')
    score = latest.get('effective_score')
    if not isinstance(score, (int,float)) or not (0 <= score <= 100):
        errors.append('effective score sanity failure')
    if latest.get('regime') not in ('RESTRICTIVE','NEUTRAL','SUPPORTIVE'):
        errors.append('Funding regime invalid')
    stress = funding.get('stress_window_sanity') or {}
    for m in ('2008-10','2020-03'):
        if (stress.get(m) or {}).get('pass') is not True:
            errors.append(f'stress sanity {m} not PASS')
    if errors:
        raise ValueError('; '.join(errors))
    return latest


def fetch_exact_source_bytes(base, funding, as_of):
    fetched = {}
    with ThreadPoolExecutor(max_workers=len(base.SERIES)) as pool:
        futures = {pool.submit(base.fetch_series, sid, as_of): sid for sid in base.SERIES}
        for future in as_completed(futures):
            sid = futures[future]
            _, url, raw, rows = future.result()
            expected = ((funding.get('sources') or {}).get(sid) or {}).get('sha256')
            actual = hashlib.sha256(raw).hexdigest()
            if expected != actual:
                raise ValueError(f'source bytes changed between calculation and archive for {sid}: {expected} != {actual}')
            fetched[sid] = {'url': url, 'raw': raw, 'sha256': actual, 'rows': rows}
    return fetched


def render_active(latest, refreshed_at):
    z = (latest['effective_score'] - 50.0) * 3.0 / 50.0
    c = latest['component_supportive_z']
    return f"""// Generated/refreshable data snapshot for promoted Funding V2.\n// The frozen methodology and promotion evidence live under research/funding-v2;\n// scheduled refreshes may update only these validated data-vintage fields.\nexport const ACTIVE_FUNDING_V2 = {{\n  version: '{VERSION}',\n  observation_month: '{latest['observation_month']}',\n  available_date: '{latest['available_date']}',\n  z: {z},\n  score: {latest['effective_score']},\n  regime: '{latest['regime']}',\n  structural_support_z: {latest['structural_support_z']},\n  structural_support_score: {latest['structural_support_score']},\n  observed_conditions_z: {latest['observed_conditions_z']},\n  observed_conditions_score: {latest['observed_conditions_score']},\n  component_supportive_z: {{\n    anfci: {c['ANFCI']},\n    real_yield: {c['DFII10']},\n    term_premium: {c['THREEFYTP10']},\n    reserves_3m: {c['WRESBAL_3M_PCT']}\n  }},\n  source_manifest: 'research/funding-v2/latest/manifest.lock.json',\n  refreshed_at: '{refreshed_at}'\n}};\n"""


def write_history(path, history):
    fields = [
        'observation_month','available_date','effective_score','regime',
        'structural_support_score','observed_conditions_score',
        'structural_support_z','observed_conditions_z',
        'anfci_z','real_yield_z','term_premium_z','reserves_z',
        'anfci','dfii10','term_premium','reserves_3m_pct'
    ]
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for x in history:
            w.writerow({
                'observation_month': x['observation_month'],
                'available_date': x['available_date'],
                'effective_score': f"{x['effective_score']:.10f}",
                'regime': x['regime'],
                'structural_support_score': f"{x['structural_support_score']:.10f}",
                'observed_conditions_score': f"{x['observed_conditions_score']:.10f}",
                'structural_support_z': f"{x['structural_support_z']:.10f}",
                'observed_conditions_z': f"{x['observed_conditions_z']:.10f}",
                'anfci_z': f"{x['component_supportive_z']['ANFCI']:.10f}",
                'real_yield_z': f"{x['component_supportive_z']['DFII10']:.10f}",
                'term_premium_z': f"{x['component_supportive_z']['THREEFYTP10']:.10f}",
                'reserves_z': f"{x['component_supportive_z']['WRESBAL_3M_PCT']:.10f}",
                'anfci': x['raw']['ANFCI'],
                'dfii10': x['raw']['DFII10'],
                'term_premium': x['raw']['THREEFYTP10'],
                'reserves_3m_pct': x['raw']['WRESBAL_3M_PCT']
            })


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--as-of', default=date.today().isoformat())
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    as_of = date.fromisoformat(args.as_of)
    try:
        promotion, usefulness = validate_static_promotion()
        candidate = load_module(CANDIDATE_RUNNER, 'gmli_funding_v2_candidate2_refresh')
        base = load_module(BASE_RUNNER, 'gmli_funding_v2_base_refresh')
        funding = candidate.build(as_of)
        old_date = current_available_date()
        latest = validate_candidate(funding, old_date)
        new_date = latest['available_date']
        needs_archive = not (LATEST_DIR / 'manifest.lock.json').exists()
        changed = old_date != new_date or needs_archive
        refreshed_at = now_iso()

        if args.apply and changed:
            # Re-fetch exact source bytes and require hashes to match the payload
            # used by the calculation before any production write occurs.
            source_bytes = fetch_exact_source_bytes(base, funding, as_of)
            with tempfile.TemporaryDirectory(prefix='gmli-funding-v2-') as tmp:
                stage = pathlib.Path(tmp)
                raw_dir = stage / 'raw'
                raw_dir.mkdir(parents=True)
                for sid, x in source_bytes.items():
                    (raw_dir / f'{sid}.csv').write_bytes(x['raw'])
                write_history(stage / 'history.csv', funding['history'])
                manifest = {
                    'status': 'PASS_ACTIVE_FUNDING_V2_REFRESH_GUARDS',
                    'version': VERSION,
                    'candidate_version': CANDIDATE,
                    'built_at': refreshed_at,
                    'as_of': as_of.isoformat(),
                    'previous_available_date': old_date,
                    'latest_eligible': latest,
                    'directional_gate_pass': True,
                    'frozen_usefulness_gate': usefulness['decision'],
                    'promotion_lock': promotion['status'],
                    'money_core_modified': False,
                    'methodology_modified': False,
                    'sources': funding['sources'],
                    'raw_archive': {sid: {'file': f'raw/{sid}.csv', 'sha256': x['sha256'], 'bytes': len(x['raw'])} for sid, x in source_bytes.items()},
                    'history_rows': len(funding['history']),
                    'history_start': funding['history_start'],
                    'history_end': funding['history_end'],
                    'guardrail': 'Funding V2 remains an OVERLAY and bounded conviction modifier; strongest validated transmission use is DBC 6M/12M.'
                }
                (stage / 'manifest.lock.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

                # Only after every source and gate has passed do we replace last-good files.
                if LATEST_DIR.exists():
                    shutil.rmtree(LATEST_DIR)
                shutil.copytree(stage, LATEST_DIR)
                ACTIVE_PATH.write_text(render_active(latest, refreshed_at), encoding='utf-8')

        print(json.dumps({
            'status': 'PASS_ACTIVE_FUNDING_V2_REFRESH_GUARDS',
            'version': VERSION,
            'candidate_version': CANDIDATE,
            'previous_available_date': old_date,
            'new_available_date': new_date,
            'observation_month': latest['observation_month'],
            'score': latest['effective_score'],
            'regime': latest['regime'],
            'directional_gate': 'PASS',
            'usefulness_gate': usefulness['decision'],
            'changed': changed,
            'applied': args.apply,
            'money_core_modified': False
        }, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            'status': 'FAIL_ACTIVE_FUNDING_V2_REFRESH_GUARDS',
            'error': str(exc),
            'production_files_written': False,
            'money_core_modified': False,
            'last_good_preserved': True
        }, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
