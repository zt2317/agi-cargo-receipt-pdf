#!/usr/bin/env python3
# coding: utf-8
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


def _normalize_text(s: str) -> str:
    """Normalize text for more robust regex matching:
    - convert to str if bytes
    - replace various hyphen/minus characters with ASCII '-'
    - replace non-breaking spaces / zero-width chars with normal space or removed
    - collapse repeated whitespace to single space
    """
    if isinstance(s, bytes):
        s = s.decode('utf-8', errors='replace')
    elif not isinstance(s, str):
        s = str(s)
    # replace common non-breaking or invisible spaces
    s = s.replace('\u00A0', ' ').replace('\u200B', '').replace('\uFEFF', '')
    # replace various hyphen/minus characters with ASCII hyphen
    for ch in ('\u2010', '\u2011', '\u2012', '\u2013', '\u2014', '\u2015', '\u2212'):
        s = s.replace(ch, '-')
    # normalize other dash characters explicitly
    s = s.replace('\u2014', '-').replace('\u2013', '-')
    # collapse whitespace
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def _extract_mawb_from_text(text: str) -> Union[str, None]:
    """Implement the user's 4-step MAWB rule on a single text block:
    1) Check whether text contains '-'
    2) For each numeric-left - numeric-right group, check right has >=8 digits
    3) Check left has >=3 digits
    4) If satisfied, return left[-3:]-right[:8]

    Returns the MAWB string (xxx-xxxxxxxx) or None.
    """
    if not text:
        return None
    if '-' not in text:
        return None
    # find numeric-left - numeric-right occurrences
    # require hyphen to be directly between digits (no spaces): e.g. 60701180-50446970
    for m in re.finditer(r'([0-9]+)-([0-9]+)', text):
        left = re.sub(r'\D', '', m.group(1))
        right = re.sub(r'\D', '', m.group(2))
        # step 2 and 3: require right has >=8 digits and left has >=3 digits
        if len(right) >= 8 and len(left) >= 3:
            # step 4: take last 3 digits from left and first 8 digits from right
            return f"{left[-3:]}-{right[:8]}"
    return None


def find(path: Path):
    """Read PDF via read(path) and find MAWB (per user's steps) and total.

    Returns (code_result, total_result) where
      - code_result is (mawb_string, line_number, line_text) or None
      - total_result is (amount_string, page_number, line_number, line_text) or None
    """
    pages = read(path)
    if not pages:
        return (None, None)

    code_result = None
    # 1) Prefer checking page 1 line-by-line
    if len(pages) >= 1:
        first_page = pages[0]
        for idx, line in enumerate(first_page, start=1):
            if not isinstance(line, str):
                continue
            norm = _normalize_text(line)
            if not norm:
                continue
            mawb = _extract_mawb_from_text(norm)
            if mawb:
                code_result = (mawb, idx, line)
                break
    # 2) Fallback: scan whole document (page by page, joined per page)
    if code_result is None:
        for pno, page in enumerate(pages, start=1):
            # check lines first
            for idx, line in enumerate(page, start=1):
                if not isinstance(line, str):
                    continue
                norm = _normalize_text(line)
                if not norm:
                    continue
                mawb = _extract_mawb_from_text(norm)
                if mawb:
                    # keep shape (mawb, line_number, original_line_text)
                    code_result = (mawb, idx, line)
                    break
            if code_result:
                break

    # find total anywhere in document (normalized)
    total_result = None
    total_line_pattern = re.compile(r"\btotal\b\s*[:\-]?\s*(.+)$", re.I)
    amount_inner_pattern = re.compile(
        r"(?P<symbol>[€£¥$])?\s*(?P<number>[0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?P<code>[A-Za-z]{3})?",
        re.I,
    )

    for pno, page in enumerate(pages, start=1):
        for lno, line in enumerate(page, start=1):
            if not isinstance(line, str):
                continue
            norm = _normalize_text(line)
            if not norm:
                continue
            tlm = total_line_pattern.search(norm)
            if tlm:
                rest = tlm.group(1)
                am = amount_inner_pattern.search(rest)
                if am:
                    num = am.group('number')
                    num_clean = num.replace(',', '')
                    amt = num_clean
                else:
                    amt = rest.strip()
                total_result = (amt, pno, lno, line)
                break
        if total_result:
            break

    return (code_result, total_result)


def format(filename: Union[str, Path]):
    """Read the PDF at `filename` and return a dict {'mawb': ..., 'total': ...}.

    - 'mawb' is the first found per user's 4-step rule (string) or None
    - 'total' is the amount string extracted (e.g. '273.52') or None
    """
    p = Path(filename)
    mawb_res, total_res = find(p)
    mawb_val = mawb_res[0] if mawb_res is not None else None
    total = total_res[0] if total_res is not None else None
    return {'mawb': mawb_val, 'total': total}
