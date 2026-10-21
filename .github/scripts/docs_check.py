#!/usr/bin/env python3
"""Checks that keep the README and guide usable.

- Every relative link in a Markdown file points to a file that exists.
- Every placeholder the skills use is one that install.sh fills in.
"""
import pathlib
import re
import subprocess
import sys

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
PLACEHOLDER = re.compile(r"\{\{[A-Z_]+\}\}")
# The placeholders install.sh fills in are the ones it names.
KNOWN = set(PLACEHOLDER.findall(pathlib.Path("install.sh").read_text(encoding="utf-8")))

errors = 0
files = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split()

for path in (f for f in files if f.endswith(".md")):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    in_code = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        if in_code:
            continue
        for target in LINK.findall(line):
            if re.match(r"[a-z]+:|#", target) or "{{" in target or "<" in target:
                continue
            dest = (pathlib.Path(path).parent / target.split("#")[0]).resolve()
            if not dest.exists():
                print("::error file=%s,line=%d::broken link: %s" % (path, n, target))
                errors += 1

for path in (f for f in files if f.startswith("claude-code/")):
    for n, line in enumerate(pathlib.Path(path).read_text(encoding="utf-8").splitlines(), 1):
        for p in PLACEHOLDER.findall(line):
            if p not in KNOWN:
                print("::error file=%s,line=%d::placeholder %s isn't filled in by install.sh" % (path, n, p))
                errors += 1

if errors:
    sys.exit(1)
print("Docs check passed.")
