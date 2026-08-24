#!/usr/bin/env python3
"""Stable entry point for Global Money V2.

BOJ's provider-native JSON emits monthly SURVEY_DATES as compact YYYYMM values.
The base builder intentionally keeps its generic date parser conservative; this
entry point adds the provider-specific compact-date normalization and then runs
the same builder unchanged.
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


def provider_ym(value):
    s = str(value or '').strip()
    if re.fullmatch(r'20\d{4}', s):
        return f'{s[:4]}-{s[4:6]}'
    return _base_ym(value)


mod.ym = provider_ym

if __name__ == '__main__':
    sys.exit(mod.main())
