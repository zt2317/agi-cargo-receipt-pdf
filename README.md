read.py - extract PDF text by lines and split by separators

Usage:

1. (Optional) create a virtualenv and install requirements:

   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Run the script (defaults to file.pdf in the same directory):

   python3 read.py file.pdf

Options:
  -s, --separators   Separator characters to split lines with (default: ",;|\t")
  --no-lines         Do not print raw lines, only tokens after splitting
  --no-tokens        Do not print tokens, only raw lines

Example:

  python3 read.py file.pdf -s ",;|\t"

