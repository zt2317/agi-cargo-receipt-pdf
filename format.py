#!/usr/bin/env python3
# coding: utf-8
import sys
import re
from pathlib import Path
from typing import Union

# Import the read function from the sibling module
try:
    from read import read
except Exception:
    # fallback: try import via importlib if direct import fails
    import importlib.util
    spec = importlib.util.spec_from_file_location('rmod', Path(__file__).parent / 'read.py')
    rmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rmod)
    read = getattr(rmod, 'read')


def find(path: Path):
    """Read PDF via read(path) and find first xxx-xxxxxxxx pattern on page 1.

    Also search the whole document for the first occurrence of 'total: <amount>' and
    return both results.

    Returns a tuple (code_result, total_result) where:
      - code_result is (match_string, line_number, line_text) or None
      - total_result is (amount_string, page_number, line_number, line_text) or None
    """
    pages = read(path)
    if not pages:
        return (None, None)

    # find code on first page
    code_result = None
    first_page = pages[0]
    # MAWB format: first 3 and last 8 must be digits (e.g. 123-12345678)
    code_pattern = re.compile(r"\b\d{3}-\d{8}\b")
    for idx, line in enumerate(first_page, start=1):
        if not isinstance(line, str):
            continue
        m = code_pattern.search(line)
        if m:
            code_result = (m.group(), idx, line)
            break

    # find total anywhere in document
    total_result = None
    # First capture everything after 'total:' on a line (match whole word 'total' to avoid 'subtotal')
    total_line_pattern = re.compile(r"\btotal\b\s*:\s*(.+)$", re.I)
    # Use named groups to capture optional symbol, numeric part and optional currency code
    amount_inner_pattern = re.compile(r"(?P<symbol>[€£¥$])?\s*(?P<number>[0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?P<code>[A-Za-z]{3})?", re.I)

    for pno, page in enumerate(pages, start=1):
        for lno, line in enumerate(page, start=1):
            if not isinstance(line, str):
                continue
            tlm = total_line_pattern.search(line)
            if tlm:
                rest = tlm.group(1)
                am = amount_inner_pattern.search(rest)
                if am:
                    num = am.group('number')
                    # remove thousand separators
                    num_clean = num.replace(',', '')
                    # keep two decimals if present, else return integer form
                    amt = num_clean
                else:
                    # fallback: if no numeric found in rest, use trimmed rest entirely
                    amt = rest.strip()
                total_result = (amt, pno, lno, line)
                break
        if total_result:
            break

    return (code_result, total_result)

def format(filename: Union[str, Path]):
    """Read the PDF at `filename` and return a dict {'mawb': ..., 'total': ...}.

    - 'mawb' is the first xxx-xxxxxxxx found on page 1 (string) or None
    - 'total' is the amount string extracted (e.g. '273.52') or None
    """
    # Accept either Path or string
    p = Path(filename)
    mawb_res, total_res = find(p)
    mawb_val = mawb_res[0] if mawb_res is not None else None
    total = total_res[0] if total_res is not None else None
    return {'mawb': mawb_val, 'total': total}
