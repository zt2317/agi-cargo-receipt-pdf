#!/usr/bin/env python3
# coding: utf-8
import sys
import csv
import re
from pathlib import Path
from typing import Optional

# Import the format function from format.py; avoid using the name `format` directly
try:
    from format import format as parse_pdf
except Exception:
    # fallback import using importlib if needed
    import importlib.util
    spec = importlib.util.spec_from_file_location('fmt', Path(__file__).parent / 'format.py')
    fmt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fmt)
    parse_pdf = getattr(fmt, 'format')


def _safe_parse_amount(s: Optional[str]) -> Optional[float]:
    """Try to parse an amount string into float. Returns None on failure.
    Strips currency symbols and commas; keeps digits, dot and minus.
    """
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if s == "":
        return None
    # remove common currency symbols and spaces, keep digits, dot and minus
    cleaned = re.sub(r"[^0-9.\-]", "", s)
    # guard: there should be at most one dot
    if cleaned.count('.') > 1:
        # try to keep last dot as decimal separator
        parts = cleaned.split('.')
        cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
    try:
        return float(cleaned)
    except Exception:
        return None


def process_directory(directory: Path, out_csv: Path):
    """Process all .pdf/.PDF files in `directory` (non-recursive) and write results to out_csv.

    Behavior change: if `parse_pdf(p)` returns a dict with 'mawb' containing a list,
    write one CSV row per MAWB. The 'total' value (if numeric) will be divided evenly
    among the MAWB entries. If parsing of the total fails, each row will have an empty
    total cell.
    """
    files = []
    files.extend(sorted(directory.glob('*.pdf')))
    files.extend(sorted(directory.glob('*.PDF')))
    # remove duplicates while preserving order
    seen = set()
    pdfs = []
    for p in files:
        sp = str(p)
        if sp not in seen:
            seen.add(sp)
            pdfs.append(p)

    fieldnames = ['filename', 'mawb', 'total']
    with out_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in pdfs:
            try:
                res = parse_pdf(p)
                # Debug: print the raw result from format for this file
                print(f"format result for {p}: {res}")
                # expect res to be a dict with keys 'mawb' and 'total'
                if isinstance(res, dict):
                    mawb_field = res.get('mawb')
                    total_field = res.get('total')
                else:
                    mawb_field = None
                    total_field = None
            except Exception as e:
                # on error, log to stderr and write empty values
                print(f"Error processing {p}: {e}", file=sys.stderr)
                mawb_field = None
                total_field = None
            # normalize mawb_field into a list of strings
            mawbs = []
            if mawb_field is None:
                mawbs = []
            elif isinstance(mawb_field, list):
                # ensure strings
                mawbs = [str(m).strip() for m in mawb_field if str(m).strip() != '']
            else:
                # single string value
                s = str(mawb_field).strip()
                if s != '':
                    mawbs = [s]

            # parse total to numeric if possible
            total_value = _safe_parse_amount(total_field)

            if mawbs:
                # if numeric total available, divide evenly; otherwise leave blank
                per_value = None
                if total_value is not None:
                    try:
                        per_value = total_value / len(mawbs)
                    except Exception:
                        per_value = None
                # format per_value as string with 2 decimals if numeric
                per_str = f"{per_value:.2f}" if isinstance(per_value, float) else ''
                for m in mawbs:
                    writer.writerow({'filename': str(p), 'mawb': m, 'total': per_str})
            else:
                # no mawbs found: write a single row with empty mawb and original total (or parsed)
                total_str = ''
                if total_value is not None:
                    total_str = f"{total_value:.2f}"
                elif total_field:
                    total_str = str(total_field)
                writer.writerow({'filename': str(p), 'mawb': '', 'total': total_str})


def process_path(path: Path, out_csv: Path):
    """Process a Path which may be a directory or a single PDF file."""
    if path.is_file():
        # single file
        fieldnames = ['filename', 'mawb', 'total']
        with out_csv.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            p = path
            try:
                res = parse_pdf(p)
                print(f"format result for {p}: {res}")
                if isinstance(res, dict):
                    mawb_field = res.get('mawb')
                    total_field = res.get('total')
                else:
                    mawb_field = None
                    total_field = None
            except Exception as e:
                print(f"Error processing {p}: {e}", file=sys.stderr)
                mawb_field = None
                total_field = None

            mawbs = []
            if mawb_field is None:
                mawbs = []
            elif isinstance(mawb_field, list):
                mawbs = [str(m).strip() for m in mawb_field if str(m).strip() != '']
            else:
                s = str(mawb_field).strip()
                if s:
                    mawbs = [s]

            total_value = _safe_parse_amount(total_field)
            if mawbs:
                per_value = None
                if total_value is not None:
                    try:
                        per_value = total_value / len(mawbs)
                    except Exception:
                        per_value = None
                per_str = f"{per_value:.2f}" if isinstance(per_value, float) else ''
                for m in mawbs:
                    writer.writerow({'filename': str(p), 'mawb': m, 'total': per_str})
            else:
                total_str = ''
                if total_value is not None:
                    total_str = f"{total_value:.2f}"
                elif total_field:
                    total_str = str(total_field)
                writer.writerow({'filename': str(p), 'mawb': '', 'total': total_str})
        return
    # otherwise treat as directory
    return process_directory(path, out_csv)


def main(argv: Optional[list] = None):
    argv = argv or sys.argv[1:]
    if len(argv) >= 1:
        directory = Path(argv[0])
    else:
        directory = Path('.')
    if len(argv) >= 2:
        out_csv = Path(argv[1])
    else:
        out_csv = directory / 'summary.csv'

    if not directory.exists():
        print(f"Path not found: {directory}", file=sys.stderr)
        return 2

    process_path(directory, out_csv)
    print(f"Wrote results to {out_csv}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
