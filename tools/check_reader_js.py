#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse every inline <script> in index.html with node.

The reader is hand-edited JavaScript inside a 1700-line HTML file, and a typo
there takes the whole flip book down (it has happened). `node --check` catches
that before a push, without needing a browser.

    python tools/check_reader_js.py
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"

html = HTML.read_text(encoding="utf-8")
# JSON-LD blocks are data, not JavaScript - node --check would (rightly) reject
# them, so only real scripts are parsed.
blocks = re.findall(r'<script(?![^>]*\bsrc=)(?![^>]*application/ld\+json)[^>]*>(.*?)</script>',
                    html, re.S)
print("inline script blocks:", len(blocks))

failed = 0
with tempfile.TemporaryDirectory() as tmp:
    for i, body in enumerate(blocks):
        if not body.strip():
            continue
        f = Path(tmp) / ("block%d.js" % i)
        # a browser-only global (`location`) is fine for parsing
        f.write_text(body, encoding="utf-8")
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        if r.returncode:
            failed += 1
            print("\nBLOCK %d FAILED" % i)
            print(r.stderr.strip()[:900])
        else:
            print("  block %d: syntax OK (%d lines)" % (i, body.count("\n")))

print("\nresult:", "FAILED" if failed else "all inline scripts parse")
sys.exit(1 if failed else 0)
