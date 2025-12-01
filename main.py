#!/usr/bin/env python3
# coding: utf-8
import sys
import csv
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


def process_directory(directory: Path, out_csv: Path):
    """Process all .pdf/.PDF files in `directory` (non-recursive) and write results to out_csv."""
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
                # expect res to be a dict with keys 'mawb' and 'total'
                mawb = res.get('mawb') if isinstance(res, dict) else None
                total = res.get('total') if isinstance(res, dict) else None
            except Exception as e:
                # on error, log to stderr and write empty values
                print(f"Error processing {p}: {e}", file=sys.stderr)
                mawb = None
                total = None
            writer.writerow({'filename': str(p), 'mawb': mawb or '', 'total': total or ''})


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

    if not directory.exists() or not directory.is_dir():
        print(f"Directory not found: {directory}", file=sys.stderr)
        return 2

    process_directory(directory, out_csv)
    print(f"Wrote results to {out_csv}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
