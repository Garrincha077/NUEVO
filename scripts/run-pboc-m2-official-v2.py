#!/usr/bin/env python3
"""Geometry-aware runner for the PBoC M2 official-source v2 builder.

PBoC annual one-page tables sometimes wrap the decimal digits inside a cell
(e.g. 2441488. on one visual line and 90 beneath it). A linear pdftotext parser
can therefore mis-assign months. This wrapper preserves the base builder's
source/report/provenance logic and replaces only annual-PDF extraction with a
bbox/cell parser.
"""

import importlib.util
import pathlib
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
BASE_PATH = HERE / 'build-pboc-m2-official-v2.py'

spec = importlib.util.spec_from_file_location('gmli_pboc_v2_base', BASE_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def _bbox_words(raw):
    if subprocess.run(['which', 'pdftotext'], capture_output=True).returncode != 0:
        raise RuntimeError('pdftotext is required; install poppler-utils')
    with tempfile.TemporaryDirectory() as td:
        src = pathlib.Path(td) / 'source.pdf'
        src.write_bytes(raw)
        proc = subprocess.run(
            ['pdftotext', '-bbox-layout', str(src), '-'],
            capture_output=True,
            check=True,
        )
        xml = proc.stdout.decode('utf-8', errors='replace')
    root = ET.fromstring(xml)
    words = []
    for el in root.iter():
        if not el.tag.lower().endswith('word'):
            continue
        text = ''.join(el.itertext()).strip()
        if not text:
            continue
        try:
            x0, x1 = float(el.attrib['xMin']), float(el.attrib['xMax'])
            y0, y1 = float(el.attrib['yMin']), float(el.attrib['yMax'])
        except (KeyError, ValueError):
            continue
        words.append({
            'text': text,
            'x0': x0, 'x1': x1, 'xc': (x0 + x1) / 2,
            'y0': y0, 'y1': y1, 'yc': (y0 + y1) / 2,
        })
    if not words:
        raise ValueError('PBoC PDF bbox extraction returned no words')
    return words


def _month_headers(words, year, expected_months):
    found = {}
    for w in words:
        s = re.sub(r'\s+', '', w['text']).replace('．', '.').replace('。', '.')
        m = re.fullmatch(fr'{year}[.\-/]?(0[1-9]|1[0-2])', s)
        if not m:
            continue
        month = int(m.group(1))
        if 1 <= month <= expected_months:
            # Header is the uppermost occurrence if a year/month is repeated in a note.
            if month not in found or w['yc'] < found[month]['yc']:
                found[month] = w
    if len(found) < expected_months:
        raise ValueError(
            f'{year} bbox found only {len(found)}/{expected_months} month headers: '
            f'{sorted(found)}'
        )
    return [found[i] for i in range(1, expected_months + 1)]


def _row_y(words, marker, max_x):
    pat = re.compile(marker, re.I)
    candidates = [w for w in words if w['xc'] < max_x and pat.search(w['text'])]
    if not candidates:
        # Parentheses can be split into separate PDF words; search globally as fallback.
        candidates = [w for w in words if pat.search(w['text'])]
    if not candidates:
        raise ValueError(f'PDF row marker not found: {marker}')
    return min(w['yc'] for w in candidates)


def _numeric_fragment(text):
    s = str(text).strip().replace(',', '').replace('，', '').replace(' ', '')
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]*)?', s):
        return None
    return s


def parse_money_supply_pdf_bbox(raw, year, expected_months):
    words = _bbox_words(raw)
    headers = _month_headers(words, year, expected_months)
    centers = [w['xc'] for w in headers]
    first_header_x = centers[0]

    # Prefer explicit M2/M1 markers in the label column. Their vertical positions
    # define the M2 table band irrespective of line wrapping inside numeric cells.
    m2_y = _row_y(words, r'M2', first_header_x)
    m1_y = _row_y(words, r'M1', first_header_x)
    if m1_y <= m2_y:
        m1_candidates = sorted(
            w['yc'] for w in words
            if w['yc'] > m2_y and w['xc'] < first_header_x and re.search(r'M1', w['text'], re.I)
        )
        if not m1_candidates:
            raise ValueError(f'{year} could not locate M1 row below M2')
        m1_y = m1_candidates[0]

    row_height = m1_y - m2_y
    y_top = m2_y - min(22.0, row_height * 0.35)
    y_bottom = (m2_y + m1_y) / 2 + min(8.0, row_height * 0.08)

    bounds = []
    for i, c in enumerate(centers):
        left = (centers[i - 1] + c) / 2 if i else c - (centers[1] - c) / 2
        right = (c + centers[i + 1]) / 2 if i < len(centers) - 1 else c + (c - centers[i - 1]) / 2
        bounds.append((left, right))

    values = []
    debug = []
    for month, (left, right) in enumerate(bounds, start=1):
        cell = []
        for w in words:
            if not (left <= w['xc'] < right and y_top <= w['yc'] < y_bottom):
                continue
            frag = _numeric_fragment(w['text'])
            if frag is not None:
                cell.append((w['yc'], w['xc'], frag))
        cell.sort(key=lambda x: (round(x[0], 2), x[1]))
        parts = [x[2] for x in cell]
        if not parts:
            raise ValueError(f'{year}-{month:02d} bbox M2 cell is empty')

        # A wrapped value commonly appears as ['2441488.', '90']; concatenate.
        joined = ''.join(parts)
        try:
            value = float(joined)
        except ValueError as exc:
            raise ValueError(f'{year}-{month:02d} invalid M2 cell {parts!r}') from exc
        if not (100000 <= value <= 10000000):
            raise ValueError(f'{year}-{month:02d} implausible M2 {value} from {parts!r}')
        values.append(value)
        debug.append({'month': month, 'parts': parts, 'value': value})

    # Broad money should not jump by double digits month-to-month in this sample;
    # this catches column/row leakage without imposing a model assumption.
    for i in range(1, len(values)):
        ratio = values[i] / values[i - 1]
        if not (0.90 <= ratio <= 1.10):
            raise ValueError(
                f'{year}-{i+1:02d} bbox continuity failure: ratio={ratio:.4f}; '
                f'prev={values[i-1]}, cur={values[i]}, cells={debug[max(0,i-1):i+1]}'
            )

    return {f'{year:04d}-{i+1:02d}': round(v, 2) for i, v in enumerate(values)}


# Override only the fragile annual-PDF parser; all other v2 behavior remains in base.
base.parse_money_supply_pdf = parse_money_supply_pdf_bbox

if __name__ == '__main__':
    sys.exit(base.main())
