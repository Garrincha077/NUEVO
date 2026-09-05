#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'audit' / 'pages-refresh-status.json'

LAYERS = [
    {
        'name': 'money_core',
        'paths': [
            'research/china-m2-official-v2/latest',
            'research/global-money-v2/latest',
            'research/global-money-v2/transfer/latest',
            'lib/money-v2-active.js',
        ],
        'commands': [
            ['python', 'scripts/extend-pboc-m2-v2-2014.py', '--build-full'],
            ['python', 'scripts/run-global-money-v2.py', '--build-full'],
            ['python', 'scripts/test-global-money-v2-transmission.py', '--build-full'],
            ['python', 'scripts/sync-active-money-v2.py', '--apply'],
        ],
    },
    {
        'name': 'money_nowcast',
        'paths': ['lib/nowcast-state.js'],
        'commands': [['python', 'scripts/refresh-money-nowcast.py']],
    },
    {
        'name': 'funding_v2',
        'paths': ['research/funding-v2/latest', 'lib/funding-v2-active.js'],
        'commands': [['python', 'scripts/refresh-funding-v2.py', '--apply']],
    },
    {
        'name': 'fiscal_v2',
        'paths': [
            'research/fiscal-prospective/latest',
            'research/fiscal-v2/latest',
            'lib/fiscal-v2-active.js',
        ],
        'commands': [
            ['python', 'scripts/capture-prospective-fiscal-inputs.py'],
            ['python', 'scripts/refresh-fiscal-v2.py', '--apply'],
        ],
    },
    {
        'name': 'cftc_positioning',
        'paths': ['research/cftc-positioning/latest'],
        'commands': [['python', 'scripts/refresh-cftc-positioning.py', '--apply']],
    },
]


def run(cmd):
    p = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
    )
    return p.returncode, p.stdout


def rollback(paths):
    subprocess.run(
        ['git', 'restore', '--source=HEAD', '--staged', '--worktree', '--', *paths],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    subprocess.run(
        ['git', 'clean', '-fd', '--', *paths],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def changed(paths):
    p = subprocess.run(
        ['git', 'status', '--porcelain', '--', *paths],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return bool(p.stdout.strip())


def tail(text, limit=2400):
    text = (text or '').strip()
    return text[-limit:] if len(text) > limit else text


def main():
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    result = {
        'schema_version': 'gmli-pages-refresh-v1',
        'started_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'policy': 'FETCH_FIRST_WITH_PER_LAYER_LAST_GOOD_FALLBACK',
        'production_state_commit': False,
        'layers': {},
        'current_market': {
            'status': 'LIVE_DURING_REPORT_BUILD',
            'source': 'Yahoo daily SPY/QQQ/GLD/DBC through lib/current-market.js',
        },
    }

    for layer in LAYERS:
        name = layer['name']
        outputs = []
        ok = True
        failed_command = None
        for cmd in layer['commands']:
            code, output = run(cmd)
            outputs.append({'command': ' '.join(cmd), 'exit_code': code, 'output_tail': tail(output)})
            if code != 0:
                ok = False
                failed_command = ' '.join(cmd)
                break

        if ok:
            result['layers'][name] = {
                'status': 'REFRESH_OK',
                'working_tree_changed': changed(layer['paths']),
                'paths': layer['paths'],
                'commands': outputs,
            }
        else:
            rollback(layer['paths'])
            result['layers'][name] = {
                'status': 'LAST_GOOD_FALLBACK',
                'failed_command': failed_command,
                'working_tree_changed': False,
                'paths': layer['paths'],
                'commands': outputs,
            }

    statuses = [x['status'] for x in result['layers'].values()]
    result['status'] = 'PASS_FETCH_FIRST' if all(x == 'REFRESH_OK' for x in statuses) else 'PASS_WITH_LAST_GOOD_FALLBACK'
    result['completed_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    AUDIT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
