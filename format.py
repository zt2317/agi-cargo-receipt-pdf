#!/usr/bin/env python3
# coding: utf-8
import re
from pathlib import Path
from typing import Union, List

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
    2) For each numeric-left-numeric-right group (no spaces around '-'), check right has >=8 digits
    3) Check left has >=3 digits
    4) If satisfied, return left[-3:]-right[:8]

    Returns the MAWB string (xxx-xxxxxxxx) or None.
    """
    # legacy single-item extractor (kept for backward compatibility)
    if not text:
        return None
    if '-' not in text:
        return None
    for m in re.finditer(r'([0-9]+)-([0-9]+)', text):
        left = re.sub(r'\D', '', m.group(1))
        right = re.sub(r'\D', '', m.group(2))
        if len(right) >= 8 and len(left) >= 3:
            return f"{left[-3:]}-{right[:8]}"
    return None


def _extract_all_mawbs_from_text(text: str) -> List[str]:
    """Return all MAWB candidates found in text following the 4-step rule.
    The returned forms are normalized to xxx-xxxxxxxx.
    """
    out: List[str] = []
    if not text:
        return out

    # normalize various dash-like characters to ASCII hyphen for matching
    norm = text
    for ch in ('\u2010', '\u2011', '\u2012', '\u2013', '\u2014', '\u2015', '\u2212', '\u2017'):
        norm = norm.replace(ch, '-')
    # remove zero-width and BOM
    norm = norm.replace('\u200B', '').replace('\uFEFF', '')

    # 1) Prefer explicit 3-8 matches (allow optional spaces around hyphen)
    pat_3_8 = re.compile(r"(?<!\d)(\d{1,})\s*-\s*(\d{1,})(?!\d)")
    # we'll filter lengths below; this pattern finds digit-digit with hyphen
    for m in pat_3_8.finditer(norm):
        left = re.sub(r"\D", "", m.group(1))
        right = re.sub(r"\D", "", m.group(2))
        # accept if right has >=8 and left has >=3
        if len(right) >= 8 and len(left) >= 3:
            candidate = f"{left[-3:]}-{right[:8]}"
            out.append(candidate)

    # 2) If no hyphen-based candidates found, as a cautious fallback consider
    #    contiguous long digit runs (no hyphen) and take last 11 digits.
    if not out:
        for m in re.finditer(r"\d{11,}", norm):
            digits = m.group(0)
            candidate = f"{digits[-11:-8]}-{digits[-8:]}"
            out.append(candidate)

    # deduplicate preserving order
    seen_local = set()
    res: List[str] = []
    for c in out:
        if c not in seen_local:
            seen_local.add(c)
            res.append(c)
    return res


def _extract_hyphen_mawbs_from_text(text: str) -> List[str]:
    """Extract only hyphen-sourced MAWBs (allow optional spaces around hyphen).
    This is used as the primary strategy; fallback digit-run extraction runs only
    when no hyphen-sourced MAWBs are found in the whole document.
    """
    out: List[str] = []
    if not text:
        return out
    norm = text
    for ch in ('\u2010', '\u2011', '\u2012', '\u2013', '\u2014', '\u2015', '\u2212', '\u2017'):
        norm = norm.replace(ch, '-')
    norm = norm.replace('\u200B', '').replace('\uFEFF', '')
    pat = re.compile(r"(?<!\d)(\d{1,})\s*-\s*(\d{1,})(?!\d)")
    for m in pat.finditer(norm):
        left = re.sub(r"\D", "", m.group(1))
        right = re.sub(r"\D", "", m.group(2))
        if len(right) >= 8 and len(left) >= 3:
            out.append(f"{left[-3:]}-{right[:8]}")
    # dedupe
    seen_local = set()
    res: List[str] = []
    for c in out:
        if c not in seen_local:
            seen_local.add(c)
            res.append(c)
    return res


def find(path: Path):
    """Read PDF via read(path) and find ALL MAWBs (deduplicated) and total.

    Returns (mawb_list, total_result) where
      - mawb_list is List[str] (unique MAWBs in discovery order) or []
      - total_result is (amount_string, page_number, line_number, line_text) or None
    """
    pages = read(path)
    if not pages:
        return ([], None)

    mawb_list: List[str] = []
    seen = set()

    # First pass: collect hyphen-sourced MAWBs from joined page texts and per-line.
    for pno, page in enumerate(pages, start=1):
        joined_space = ' '.join([_normalize_text(l) for l in page if isinstance(l, str)])
        joined_no_space = ''.join([_normalize_text(l) for l in page if isinstance(l, str)])
        for joined in (joined_space, joined_no_space):
            if not joined:
                continue
            for mawb in _extract_hyphen_mawbs_from_text(joined):
                if mawb not in seen:
                    mawb_list.append(mawb)
                    seen.add(mawb)

        for lno, line in enumerate(page, start=1):
            if not isinstance(line, str):
                continue
            norm = _normalize_text(line)
            if not norm:
                continue
            for mawb in _extract_hyphen_mawbs_from_text(norm):
                if mawb not in seen:
                    mawb_list.append(mawb)
                    seen.add(mawb)

    # If no hyphen-sourced MAWBs found, run the cautious fallback (digit-run) across the doc
    if not mawb_list:
        for pno, page in enumerate(pages, start=1):
            joined_space = ' '.join([_normalize_text(l) for l in page if isinstance(l, str)])
            joined_no_space = ''.join([_normalize_text(l) for l in page if isinstance(l, str)])
            for joined in (joined_space, joined_no_space):
                if not joined:
                    continue
                for mawb in _extract_all_mawbs_from_text(joined):
                    if mawb not in seen:
                        mawb_list.append(mawb)
                        seen.add(mawb)
            for lno, line in enumerate(page, start=1):
                if not isinstance(line, str):
                    continue
                norm = _normalize_text(line)
                if not norm:
                    continue
                for mawb in _extract_all_mawbs_from_text(norm):
                    if mawb not in seen:
                        mawb_list.append(mawb)
                        seen.add(mawb)

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

    return (mawb_list, total_result)


def format(filename: Union[str, Path]):
    """Read the PDF at `filename` and return a dict {'mawb': [...], 'total': ...}.

    - 'mawb' is a list of unique xxx-xxxxxxxx strings found in document (may be empty)
    - 'total' is the amount string extracted (e.g. '273.52') or None
    """
    p = Path(filename)
    mawb_res, total_res = find(p)
    mawb_val = mawb_res if mawb_res else []
    total = total_res[0] if total_res is not None else None
    return {'mawb': mawb_val, 'total': total}