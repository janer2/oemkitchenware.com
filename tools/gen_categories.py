# -*- coding: utf-8 -*-
"""Build categories.json for the homepage "Shop by Category" grid.

Each group = one catalog (kitchen/baby/ladies/balls); items = leaf TOC
entries (title + 1-based PDF page). Cover art is reused from the existing
category landing page at catalog/<cid>/<slug>/cover.jpg.

Run whenever catalogs.json / toc-*.json / gen_pages.py output changes:
    python tools/gen_categories.py
"""
import json
import re
from pathlib import Path

ROOT = Path(r"C:\oemkitchenware")

def slugify(s: str) -> str:
    s = s.lower().replace("&", " and ").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "page"

def leaves(items):
    out = []
    for it in items:
        if it.get("children"):
            out.extend(leaves(it["children"]))
        else:
            out.append({"title": it["title"], "page": int(it["page"])})
    return out

CATALOGS = json.loads((ROOT / "catalogs.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "catalog" / ".genmanifest.json").read_text(encoding="utf-8"))

groups = []
missing = []
for cat in CATALOGS:
    cid = cat["id"]
    toc = ROOT / ("toc-%s.json" % cid)
    if toc.exists():
        items = leaves(json.loads(toc.read_text(encoding="utf-8")))
    else:
        items = [{"title": c["title"], "page": int(c["page"])} for c in manifest[cid]["cats"]]
    for it in items:
        slug = slugify(it["title"])
        cover = ROOT / "catalog" / cid / slug / "cover.jpg"
        if not cover.exists():
            missing.append("%s/%s" % (cid, slug))
        it["slug"] = slug
    groups.append({"id": cid, "name": cat["name"], "items": items})

out = {"groups": groups}
(ROOT / "categories.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
total = sum(len(g["items"]) for g in groups)
print("groups:", [(g["id"], len(g["items"])) for g in groups], "total", total)
print("missing covers:", missing if missing else "none")
