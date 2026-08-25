#!/usr/bin/env python3
"""Robust launcher for the frozen reverse-overlay research runner.

Only source transport is hardened here. The statistical specification and tests
remain exactly those frozen in RESEARCH_SPEC.json.
"""
import argparse
import importlib.util
import io
import math
import time
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'scripts' / 'test-reverse-overlay-mechanism.py'
UA = 'GMLI-Reverse-Overlay-Mechanism/1.0 fixed-no-search'


def load_target():
    spec = importlib.util.spec_from_file_location('gmli_reverse_overlay', TARGET)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def robust_unrate():
    urls = [
        'https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE&cosd=2000-01-01&coed=2026-08-25',
        'https://fred.stlouisfed.org/graph/fredgraph.csv?cosd=2000-01-01&coed=2026-08-25&id=UNRATE',
    ]
    last = None
    for attempt in range(4):
        url = urls[attempt % len(urls)]
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/csv,*/*'})
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()
            df = pd.read_csv(io.BytesIO(raw))
            value_cols = [c for c in df.columns if c != 'observation_date']
            if not value_cols:
                raise RuntimeError('UNRATE CSV has no value column')
            value_col = value_cols[0]
            out = {}
            for _, row in df.iterrows():
                try:
                    v = float(row[value_col])
                except Exception:
                    continue
                month = str(row['observation_date'])[:7]
                if math.isfinite(v):
                    out[month] = v
            if len(out) < 200:
                raise RuntimeError(f'UNRATE history unexpectedly short: {len(out)}')
            return out
        except Exception as exc:
            last = exc
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f'UNRATE transport failed after frozen-source retries: {last}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--as-of', default=date.today().isoformat())
    p.add_argument('--output', required=True)
    args = p.parse_args()
    mod = load_target()
    mod.fetch_unrate = robust_unrate
    result = mod.run(date.fromisoformat(args.as_of))
    import json
    text = json.dumps(result, indent=2)
    Path(args.output).write_text(text + '\n', encoding='utf-8')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
