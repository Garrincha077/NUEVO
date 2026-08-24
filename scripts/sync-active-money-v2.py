#!/usr/bin/env python3
"""Synchronize only the refreshable active Money V2 data snapshot.

The frozen methodology is never edited here. A new vintage can advance only if:
- Global Money V2 official-source build passes its May bridge convention gate,
- history still begins 2015-01,
- fixed six-relation transmission transfer remains 6/6 PASS,
- the new available_date never regresses,
- scalar values pass broad sanity checks.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MONEY_MANIFEST = ROOT / 'research' / 'global-money-v2' / 'latest' / 'manifest.lock.json'
TRANSFER_MANIFEST = ROOT / 'research' / 'global-money-v2' / 'transfer' / 'latest' / 'transfer.lock.json'
ACTIVE_PATH = ROOT / 'lib' / 'money-v2-active.js'
VERSION = 'GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def current_available_date():
    if not ACTIVE_PATH.exists():
        return None
    m = re.search(r"available_date:\s*'([^']+)'", ACTIVE_PATH.read_text(encoding='utf-8'))
    return m.group(1) if m else None


def validate():
    money = read_json(MONEY_MANIFEST)
    transfer = read_json(TRANSFER_MANIFEST)
    errors = []
    if money.get('status') != 'PASS_GLOBAL_MONEY_V2_HEADLINE': errors.append('money build not PASS')
    if money.get('candidate_version') != VERSION: errors.append('money version mismatch')
    if (money.get('history') or {}).get('start_month') != '2015-01': errors.append('history start is not 2015-01')
    if (money.get('may_2026_bridge_regression') or {}).get('status') != 'PASS': errors.append('May bridge regression not PASS')
    if transfer.get('status') != 'PASS_FIXED_TRANSMISSION_DIRECTION_TRANSFER': errors.append('transfer gate not PASS')
    if transfer.get('passed_relations') != 6 or transfer.get('total_relations') != 6: errors.append('transfer gate not 6/6')
    for flag in ('parameter_search','lag_search','horizon_search','asset_search','fdr_claim'):
        if transfer.get(flag) is not False: errors.append(f'{flag} must remain false')
    latest = money.get('latest_eligible') or {}
    required = ['month','available_date','gbm_usd_yoy_pct','gbm_fxn_yoy_pct','fx_effect_pp','usd_z','usd_score','fxn_z','fxn_score']
    if any(latest.get(k) is None for k in required): errors.append('latest eligible row incomplete')
    old_date = current_available_date()
    new_date = latest.get('available_date')
    if old_date and new_date and new_date < old_date: errors.append(f'date regression {old_date} -> {new_date}')
    for k in ('usd_score','fxn_score'):
        v = latest.get(k)
        if not isinstance(v, (int,float)) or not (-25 <= v <= 125): errors.append(f'{k} sanity failure')
    for k in ('gbm_usd_yoy_pct','gbm_fxn_yoy_pct'):
        v = latest.get(k)
        if not isinstance(v, (int,float)) or not (-30 <= v <= 40): errors.append(f'{k} sanity failure')
    if errors:
        raise ValueError('; '.join(errors))
    return money, transfer, latest, old_date


def render(latest, built_at):
    return f"""// Generated/refreshable data snapshot for the promoted Money V2 methodology.\n// Methodology lives in the frozen contract; scheduled refreshes may update only\n// these validated data-vintage fields after source + transfer guards pass.\nexport const ACTIVE_MONEY_V2 = {{\n  observation_month: '{latest['month']}',\n  available_date: '{latest['available_date']}',\n  usd_yoy_pct: {latest['gbm_usd_yoy_pct']},\n  fx_neutral_yoy_pct: {latest['gbm_fxn_yoy_pct']},\n  fx_effect_pp: {latest['fx_effect_pp']},\n  usd_z: {latest['usd_z']},\n  usd_score: {latest['usd_score']},\n  fxn_z: {latest['fxn_z']},\n  fxn_score: {latest['fxn_score']},\n  source_manifest: 'research/global-money-v2/latest/manifest.lock.json',\n  refreshed_at: '{built_at}'\n}};\n"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    try:
        money, transfer, latest, old_date = validate()
        changed = False
        if args.apply:
            text = render(latest, money.get('built_at'))
            old = ACTIVE_PATH.read_text(encoding='utf-8') if ACTIVE_PATH.exists() else ''
            changed = text != old
            if changed:
                ACTIVE_PATH.write_text(text, encoding='utf-8')
        print(json.dumps({
            'status':'PASS_ACTIVE_MONEY_V2_SYNC_GUARDS',
            'version':VERSION,
            'previous_available_date':old_date,
            'new_available_date':latest['available_date'],
            'observation_month':latest['month'],
            'usd_score':latest['usd_score'],
            'fxn_score':latest['fxn_score'],
            'transfer_gate':f"{transfer['passed_relations']}/{transfer['total_relations']}",
            'changed':changed,
            'applied':args.apply
        }, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'status':'FAIL_ACTIVE_MONEY_V2_SYNC_GUARDS','error':str(exc)}, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
