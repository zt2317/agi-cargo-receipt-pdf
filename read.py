#!/usr/bin/env python3
# coding: utf-8

import sys
import re
import json
from pathlib import Path
from typing import List, Union

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None


def extract_text_from_pdf(path: Path):
    """Extract text from each page of a PDF and return a list of page texts."""
    if PdfReader is None:
        raise RuntimeError("PyPDF2 is not available. Please install it: pip install PyPDF2")

    reader = PdfReader(str(path))
    texts = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
        except Exception:
            text = None
        if text is None:
            text = ""
        texts.append(text)
    return texts


def split_line_by_separators(line: str, separators: str):
    """Split a line by a set of separator characters. separators is a string where each char is a sep.
    Example: separators=",;|\t" will split on comma, semicolon, pipe and tab.

    Returns a list of stripped tokens (no surrounding whitespace) and excludes empty/whitespace-only tokens.
    """
    if not separators:
        return [line.strip()] if line.strip() != "" else []
    # build a character class for regex, escape special regex chars
    escaped = ''.join(re.escape(ch) for ch in separators)
    pattern = f"[{escaped}]"
    # split, strip each token and filter out empty/whitespace-only tokens
    tokens = [t.strip() for t in re.split(pattern, line)]
    tokens = [t for t in tokens if t != ""]
    return tokens


def read_pdf_to_array(path: Union[str, Path], separators: str = None, split_tokens: bool = False) -> List:
    """Read a PDF and return its content as an array.

    Returns: List[page], where each page is:
      - if split_tokens is False: List[str] (lines)
      - if split_tokens is True: List[List[str]] (tokens per line)

    separators: string of characters to treat as separators when split_tokens=True. If None, defaults to ",;|\t".
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"file not found: {p}")

    pages_text = extract_text_from_pdf(p)
    pages_out = []
    sep = separators if separators is not None else ",;|\t"

    for page_text in pages_text:
        if page_text.strip() == "":
            pages_out.append([])
            continue
        lines = page_text.splitlines()
        if split_tokens:
            page_lines = [split_line_by_separators(line, sep) for line in lines]
        else:
            page_lines = lines
        pages_out.append(page_lines)

    return pages_out


def read(path: Union[str, Path]) -> List:
    """Read PDF at `path` and return a list of pages, each page is a list of lines.

    This function is minimal: it accepts a file path and returns the structured data
    (pages -> lines). No tokenization is performed.
    """
    return read_pdf_to_array(path, separators=None, split_tokens=False)
