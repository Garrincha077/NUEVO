#!/usr/bin/env python3
"""Stable provider-normalization entry point for Global Money V2.

Provider-native date/layout conventions differ across official sources. This
wrapper normalizes transport formats and preserves the documented split between
accounting levels and official comparable growth signals. The Global Money
aggregation itself is unchanged.
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
_base_yoy = mod.yoy
_base_ecb_m2 = mod.ecb_m2
MONS = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}


class EALevels(dict):
    """Marker type: ECB M2 stock levels are used for prior-year USD weights."""


_EA_GROWTH = {}


def provider_ym(value):
    s = str(value or '').strip()
    if re.fullmatch(r'20\d{4}', s):
        return f'{s[:4]}-{s[4:6]}'
    m = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
    if m:
        return f'{int(m.group(3)):04d}-{int(m.group(2)):02d}'
    m = re.fullmatch(r'\d{1,2}\s+([A-Za-z]{3})\s+(\d{2}|\d{4})', s)
    if m and m.group(1).lower() in MONS:
        y = int(m.group(2))
        if y < 100:
            y += 2000 if y < 70 else 1900
        return f'{y:04d}-{MONS[m.group(1).lower()]:02d}'
    m = re.fullmatch(r'([A-Za-z]{3})[- ](\d{2}|\d{4})', s)
    if m and m.group(1).lower() in MONS:
        y = int(m.group(2))
        if y < 100:
            y += 2000 if y < 70 else 1900
        return f'{y:04d}-{MONS[m.group(1).lower()]:02d}'
    m = re.fullmatch(r'\d{1,2}[- ]([A-Za-z]{3})[- ](\d{2}|\d{4})', s)
    if m and m.group(1).lower() in MONS:
        y = int(m.group(2))
        if y < 100:
            y += 2000 if y < 70 else 1900
        return f'{y:04d}-{MONS[m.group(1).lower()]:02d}'
    return _base_ym(value)


def ecb_m2_level_and_signal():
    levels, level_raw, level_meta = _base_ecb_m2()
    # Documented v1.8 construction: the stock series is the accounting/weight
    # input, while the official comparable annual-growth series is the signal.
    key = 'M.U2.Y.V.M20.X.I.U2.2300.Z01.A'
    url = f'https://data-api.ecb.europa.eu/service/data/BSI/{key}?startPeriod=2014-01&format=csvdata'
    growth_raw, growth_meta = mod.fetch(url, 'text/csv', 60)
    rows = list(csv.DictReader(io.StringIO(mod.decode(growth_raw))))
    growth = {}
    for row in rows:
        md = provider_ym(row.get('TIME_PERIOD') or row.get('TIME_PERIOD_START') or row.get('TIME_PERIOD_END'))
        try:
            value = float(row.get('OBS_VALUE', ''))
        except ValueError:
            continue
        if md:
            growth[md] = value
    if not growth:
        raise ValueError('No official ECB M2 annual-growth observations')
    _EA_GROWTH.clear()
    _EA_GROWTH.update(growth)
    # Preserve both source payloads in the build audit without changing the
    # base function signature: attach the growth provenance to the level meta.
    level_meta = dict(level_meta)
    level_meta['signal_url'] = growth_meta['url']
    level_meta['signal_sha256'] = growth_meta['sha256']
    level_meta['signal_bytes'] = growth_meta['bytes']
    return EALevels(levels), level_raw, level_meta


def signal_yoy(levels, month):
    if isinstance(levels, EALevels):
        return _EA_GROWTH.get(month)
    return _base_yoy(levels, month)


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
            value = float(str(row.get('LPMAUYN', '')).replace(',', '').strip())
        except ValueError:
            continue
        if md:
            out[md] = value / 1000.0  # sterling millions -> GBP bn
    if not out:
        raise ValueError('No BoE LPMAUYN observations from official TN export')
    return out, raw, meta


def rba_series_fullscan(url, code):
    raw, meta = mod.fetch(url, 'text/csv', 60)
    rows = list(csv.reader(io.StringIO(mod.decode(raw))))
    code_row = code_col = None
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            if code in str(cell).strip():
                code_row, code_col = ri, ci
                break
        if code_col is not None:
            break
    if code_col is None:
        raise ValueError(f'RBA series code {code} not found in full provider CSV')

    out = {}
    for row in rows[code_row + 1:]:
        if len(row) <= code_col:
            continue
        md = None
        for cell in row[:min(6, len(row))]:
            md = provider_ym(cell)
            if md:
                break
        if not md:
            continue
        try:
            value = float(str(row[code_col]).replace(',', '').strip())
        except ValueError:
            continue
        out[md] = value
    if not out:
        sample = [row[:min(8, len(row))] for row in rows[max(0, code_row-2):min(len(rows), code_row+8)]]
        raise ValueError(f'No RBA observations for {code}; code_row={code_row}, code_col={code_col}, sample={sample!r}')
    return out, raw, meta


mod.ym = provider_ym
mod.ecb_m2 = ecb_m2_level_and_signal
mod.yoy = signal_yoy
mod.boe_m4 = boe_m4_clean
mod.rba_series = rba_series_fullscan

if __name__ == '__main__':
    sys.exit(mod.main())
