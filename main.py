#!/usr/bin/env python3
# coding: utf-8
import sys
import csv
import re
import subprocess
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


def _is_ignored(p: Path) -> bool:
    """Skip files that should never be processed:
    - AppleDouble sidecar files ('._name.pdf') created by macOS on non-HFS volumes
    - hidden files/dirs (name starts with '.'), including anything inside
      '.Trashes' (deleted files on USB/network volumes live there and would
      otherwise be picked up again by the recursive scan)
    """
    for part in p.parts:
        if part.startswith('.'):
            return True
    return False


def process_directory(directory: Path, out_csv: Path):
    """Process all .pdf/.PDF files under `directory` recursively (including all
    subdirectories) and write results to out_csv.

    Behavior change: if `parse_pdf(p)` returns a dict with 'mawb' containing a list,
    write one CSV row per MAWB. The 'total' value (if numeric) will be divided evenly
    among the MAWB entries. If parsing of the total fails, each row will have an empty
    total cell.
    """
    files = []
    files.extend(sorted(directory.rglob('*.pdf')))
    files.extend(sorted(directory.rglob('*.PDF')))
    # remove duplicates while preserving order; skip hidden/AppleDouble/Trash files
    seen = set()
    pdfs = []
    for p in files:
        sp = str(p)
        if sp not in seen and not _is_ignored(p):
            seen.add(sp)
            pdfs.append(p)

    fieldnames = ['filename', 'mawb', 'total', 'path']
    with out_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in pdfs:
            # path shown relative to the selected directory so files in
            # subdirectories can be located
            try:
                rel_path = str(p.relative_to(directory))
            except ValueError:
                rel_path = str(p)
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
                    writer.writerow({'filename': p.name, 'mawb': m, 'total': per_str, 'path': rel_path})
            else:
                # no mawbs found: write a single row with empty mawb and original total (or parsed)
                total_str = ''
                if total_value is not None:
                    total_str = f"{total_value:.2f}"
                elif total_field:
                    total_str = str(total_field)
                writer.writerow({'filename': p.name, 'mawb': '', 'total': total_str, 'path': rel_path})


def process_path(path: Path, out_csv: Path):
    """Process a Path which may be a directory or a single PDF file."""
    if path.is_file():
        # single file; refuse macOS AppleDouble sidecar files ('._x.pdf'),
        # which are not real PDFs
        if path.name.startswith('._'):
            print(f"Skipping AppleDouble sidecar file: {path}", file=sys.stderr)
            fieldnames = ['filename', 'mawb', 'total', 'path']
            with out_csv.open('w', newline='', encoding='utf-8') as f:
                csv.DictWriter(f, fieldnames=fieldnames).writeheader()
            return
        # single file
        fieldnames = ['filename', 'mawb', 'total', 'path']
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
                    writer.writerow({'filename': p.name, 'mawb': m, 'total': per_str, 'path': str(p)})
            else:
                total_str = ''
                if total_value is not None:
                    total_str = f"{total_value:.2f}"
                elif total_field:
                    total_str = str(total_field)
                writer.writerow({'filename': p.name, 'mawb': '', 'total': total_str, 'path': str(p)})
        return
    # otherwise treat as directory
    return process_directory(path, out_csv)


def _exe_dir() -> Path:
    """Return the directory of the executable (PyInstaller frozen) or the script."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _as_escape(s: str) -> str:
    """Escape a string for use inside an AppleScript double-quoted string."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


def _choose_folder_dialog() -> Optional[Path]:
    """Show a native macOS folder picker via osascript.
    Returns the chosen Path, or None if the user cancelled or osascript failed."""
    try:
        result = subprocess.run(
            ['osascript', '-e',
             'POSIX path of (choose folder with prompt "请选择存放 PDF 的文件夹")'],
            capture_output=True, text=True)
    except FileNotFoundError:
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip())


def _show_dialog(message: str, title: str = "cargo_parser"):
    """Show a native macOS dialog with the given message."""
    try:
        subprocess.run(
            ['osascript', '-e',
             f'display dialog "{_as_escape(message)}" with title "{_as_escape(title)}" '
             'buttons {"好"} default button "好"'],
            capture_output=True, text=True)
    except FileNotFoundError:
        pass


def main(argv: Optional[list] = None):
    argv = argv if argv is not None else sys.argv[1:]
    interactive = False
    if len(argv) >= 1:
        directory = Path(argv[0]).expanduser()
    elif sys.stdin.isatty():
        # double-clicked from Finder: no arguments, show a native folder picker
        interactive = True
        directory = _choose_folder_dialog()
        if directory is None:
            print("已取消选择，退出。")
            return 2
    else:
        directory = Path('.')
    if len(argv) >= 2:
        out_csv = Path(argv[1]).expanduser()
    else:
        out_csv = _exe_dir() / 'summary.csv'

    if not directory.exists():
        print(f"Path not found: {directory}", file=sys.stderr)
        if interactive:
            _show_dialog(f"路径不存在：{directory}", title="处理失败")
        return 2

    try:
        process_path(directory, out_csv)
    except Exception as e:
        print(f"处理失败: {e}", file=sys.stderr)
        if interactive:
            _show_dialog(f"处理失败：{e}", title="处理失败")
        return 1
    print(f"Wrote results to {out_csv}")
    if interactive:
        _show_dialog(f"处理完成！\n结果已保存到：{out_csv}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
