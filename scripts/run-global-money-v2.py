#!/usr/bin/env python3
"""Stable provider-normalization entry point for Global Money V2.

Provider-native date conventions differ across official sources. This wrapper
normalizes transport formats only; the Global Money construction is unchanged.
"""
import csv
import importlib.util
import io
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


def boe_m4_clean():
    # Official BoE IADB export; TN produces a stable two-column DATE,LPMAUYN CSV.
    url = ('https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?'
           'csv.x=yes&Datefrom=01/Jan/2014&Dateto=now&SeriesCodes=LPMAUYN&UsingCodes=Y&CSVF=TN&VPD=Y&VFD=N')
    raw, meta = mod.fetch(url, 'text/csv', 60)
    rows = list(csv.DictReader(io.StringIO(mod.decode(raw))))
    out = {}
    for row in rows:
        md = provider_ym(row.get('DATE'))
        try:
            v = float(str(row.get('LPMAUYN', '')).replace(',', '').strip())
        except ValueError:
            continue
        if md:
            out[md] = v / 1000.0  # sterling millions -> GBP bn
    if not out:
        raise ValueError('No BoE LPMAUYN observations from official TN export')
    return out, raw, meta


mod.ym = provider_ym
mod.boe_m4 = boe_m4_clean

if __name__ == '__main__':
    sys.exit(mod.main())
