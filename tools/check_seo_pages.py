# -*- coding: utf-8 -*-
"""One-off audit of the generated product/ + guides/ pages: meta lengths,
one h1, canonical, JSON-LD validity and that every internal link resolves."""
import html as _html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
pages = sorted(list((ROOT / "product").glob("*/index.html")) +
               list((ROOT / "guides").glob("*/index.html")) +
               list((ROOT / "catalog").glob("*/index.html")) +
               list((ROOT / "catalog").glob("*/*/index.html")) +
               [ROOT / "product" / "index.html", ROOT / "guides" / "index.html",
                ROOT / "index.html"])
print("pages to check:", len(pages))

TAG = re.compile(r"<(title|meta|h1|link)\b[^>]*>", re.I)
HREF = re.compile(r'href="([^"]+)"')
bad_ld = []
long_title = []
long_desc = []
multi_h1 = []
no_canon = []
broken = []
for p in pages:
    h = p.read_text(encoding="utf-8")
    t = re.search(r"<title>(.*?)</title>", h, re.S)
    t = t.group(1) if t else ""
    d = re.search(r'<meta name="description" content="(.*?)">', h, re.S)
    d = _html.unescape(d.group(1)) if d else ""
    t = _html.unescape(t)
    if len(t) > 65:
        long_title.append((str(p.relative_to(ROOT)), len(t), t))
    if len(d) > 160:
        long_desc.append((str(p.relative_to(ROOT)), len(d)))
    if len(re.findall(r"<h1[ >]", h, re.I)) != 1:
        multi_h1.append((str(p.relative_to(ROOT)), len(re.findall(r"<h1[ >]", h, re.I))))
    if 'rel="canonical"' not in h:
        no_canon.append(str(p.relative_to(ROOT)))
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            json.loads(block)
        except Exception as exc:
            bad_ld.append((str(p.relative_to(ROOT)), str(exc)[:80]))
    for href in HREF.findall(h):
        if href.startswith(("http", "mailto:", "#", "/?", "?")):
            continue
        # the homepage builds some hrefs in JS ("'+ mail +'") - not a real path
        if "'+" in href or href.startswith("javascript:"):
            continue
        clean = href.split("#")[0].split("?")[0]
        if not clean:
            continue
        target = ROOT / clean.strip("/")
        if clean.endswith("/"):
            target = ROOT / clean.strip("/") / "index.html"
        if not target.exists():
            broken.append((str(p.relative_to(ROOT)), href))

for name, rows in (("title > 65 chars", long_title), ("description > 160 chars", long_desc),
                   ("not exactly one h1", multi_h1), ("missing canonical", no_canon),
                   ("invalid JSON-LD", bad_ld), ("broken internal links", broken)):
    print("\n== %s: %d" % (name, len(rows)))
    for r in rows[:8]:
        print("   ", r)
