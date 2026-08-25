#!/usr/bin/env python3
import argparse
import csv
import importlib.util
import json
from datetime import date
from pathlib import Path

VERSION = 'GMLI_FUNDING_V2_CANDIDATE_2'
ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = ROOT / 'scripts' / 'build-funding-v2.py'
CANDIDATE1_RESULT = ROOT / 'research' / 'funding-v2' / 'CANDIDATE_1_RESULT.json'
LEGACY = {'available_date': '2026-07-31', 'score': 36.035410932024234, 'regime': 'RESTRICTIVE'}
STRESS_WINDOWS = {'2008-10': 'RESTRICTIVE', '2020-03': 'RESTRICTIVE'}


def load_base_runner():
    spec = importlib.util.spec_from_file_location('gmli_funding_v2_candidate1_runner', BASE_RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def score_from_z(z):
    return max(0.0, min(100.0, 50.0 + (50.0 / 3.0) * z))


def regime(score):
    if score < 40:
        return 'RESTRICTIVE'
    if score > 60:
        return 'SUPPORTIVE'
    return 'NEUTRAL'


def assert_candidate1_frozen():
    result = json.loads(CANDIDATE1_RESULT.read_text(encoding='utf-8'))
    if result.get('candidate_version') != 'GMLI_FUNDING_V2_CANDIDATE_1':
        raise RuntimeError('Candidate 1 audit result missing or changed')
    if result.get('decision') != 'REJECTED_FOR_PROMOTION':
        raise RuntimeError('Candidate 1 must remain rejected for promotion')
    if result.get('gate') != 'FAIL_FIXED_DIRECTIONAL_SANITY':
        raise RuntimeError('Candidate 1 frozen failure gate changed')
    return result


def build(as_of):
    candidate1_audit = assert_candidate1_frozen()
    base = load_base_runner().build(as_of)
    history = []
    for row in base['history']:
        structural_score = row['score']
        observed_conditions_z = row['component_supportive_z']['ANFCI']
        observed_conditions_score = score_from_z(observed_conditions_z)
        effective_score = min(structural_score, observed_conditions_score)
        history.append({
            'observation_month': row['observation_month'],
            'available_date': row['available_date'],
            'effective_score': effective_score,
            'regime': regime(effective_score),
            'structural_support_score': structural_score,
            'observed_conditions_score': observed_conditions_score,
            'structural_support_z': row['composite_supportive_z'],
            'observed_conditions_z': observed_conditions_z,
            'component_supportive_z': row['component_supportive_z'],
            'raw': row['raw'],
        })

    eligible = [x for x in history if date.fromisoformat(x['available_date']) <= as_of]
    if not eligible:
        raise RuntimeError('no eligible Candidate 2 history')
    latest = eligible[-1]
    by_month = {x['observation_month']: x for x in history}
    current_match = latest['available_date'] == LEGACY['available_date'] and latest['regime'] == LEGACY['regime']
    stress = {}
    for m, expected in STRESS_WINDOWS.items():
        got = by_month.get(m)
        stress[m] = {
            'expected': expected,
            'actual': got['regime'] if got else None,
            'effective_score': got['effective_score'] if got else None,
            'structural_support_score': got['structural_support_score'] if got else None,
            'observed_conditions_score': got['observed_conditions_score'] if got else None,
            'pass': bool(got and got['regime'] == expected),
        }
    directional_gate_pass = current_match and all(x['pass'] for x in stress.values())

    return {
        'candidate_version': VERSION,
        'evidence_tier': 'RESEARCH',
        'role': 'EFFECTIVE_FUNDING_CONDITIONS_OVERLAY_CANDIDATE',
        'as_of': as_of.isoformat(),
        'aggregation_rule': 'effective_score=min(structural_support_score, observed_ANFCI_conditions_score)',
        'tuned_override_parameter': False,
        'production_modified': False,
        'money_core_modified': False,
        'parameter_search': False,
        'candidate1_frozen_decision': candidate1_audit['decision'],
        'latest_eligible': latest,
        'legacy_current_comparator': {**LEGACY, 'direction_match': current_match},
        'stress_window_sanity': stress,
        'directional_gate_pass': directional_gate_pass,
        'promotion_eligible': False,
        'promotion_blocker': 'NARROW_USEFULNESS_CONVICTION_GATE_NOT_RUN' if directional_gate_pass else 'FAIL_FIXED_DIRECTIONAL_SANITY',
        'history_start': history[0]['observation_month'],
        'history_end': history[-1]['observation_month'],
        'history_rows': len(history),
        'sources': base['sources'],
        'history': history,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', default=date.today().isoformat())
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--build-full', action='store_true')
    parser.add_argument('--output-dir', default='research/funding-v2/candidate-2-latest')
    args = parser.parse_args()
    result = build(date.fromisoformat(args.as_of))
    summary = {k: v for k, v in result.items() if k != 'history'}
    if args.build_full:
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        with (out / 'history.csv').open('w', newline='', encoding='utf-8') as f:
            fields = [
                'observation_month', 'available_date', 'effective_score', 'regime',
                'structural_support_score', 'observed_conditions_score',
                'structural_support_z', 'observed_conditions_z',
                'anfci_z', 'real_yield_z', 'term_premium_z', 'reserves_z',
                'anfci', 'dfii10', 'term_premium', 'reserves_3m_pct',
            ]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for x in result['history']:
                writer.writerow({
                    'observation_month': x['observation_month'],
                    'available_date': x['available_date'],
                    'effective_score': f"{x['effective_score']:.8f}",
                    'regime': x['regime'],
                    'structural_support_score': f"{x['structural_support_score']:.8f}",
                    'observed_conditions_score': f"{x['observed_conditions_score']:.8f}",
                    'structural_support_z': f"{x['structural_support_z']:.8f}",
                    'observed_conditions_z': f"{x['observed_conditions_z']:.8f}",
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
