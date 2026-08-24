#!/usr/bin/env python3
"""Stable provider-normalization entry point for Global Money V2.

Provider-native date conventions differ across official sources. This wrapper
normalizes only those transport formats (for example BOJ YYYYMM and BoE
'DD Mon YY') before invoking the unchanged Global Money V2 construction.
"""
import importlib.util
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE / 'build-global-money-v2.py'
spec = importlib.util.spec_from_file_location('gmli_global_money_v2_base', BASE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
_base_ym = mod.ym
MONS = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}


def provider_ym(value):
    s = str(value or '').strip()
    if re.fullmatch(r'20\d{4}', s):
        return f'{s[:4]}-{s[4:6]}'
    m = re.fullmatch(r'\d{1,2}\s+([A-Za-z]{3})\s+(\d{2}|\d{4})', s)
    if m and m.group(1).lower() in MONS:
        y = int(m.group(2))
        if y < 100:
            y += 2000 if y < 70 else 1900
        return f'{y:04d}-{MONS[m.group(1).lower()]:02d}'
    return _base_ym(value)


mod.ym = provider_ym

if __name__ == '__main__':
    sys.exit(mod.main())
