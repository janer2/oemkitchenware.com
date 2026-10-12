#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Render every catalogue page to a JPEG so the flip reader shows pictures
instead of parsing the PDF.

Why: opening a catalogue used to mean one 17-21 MB PDF request before anything
was readable, and pdf.js cannot be told to fetch only the pages on screen -
`disableAutoFetch` works for a plain URL (1 request, but the whole file), and a
custom PDFDataRangeTransport turns one open into 120-150 serialised requests and
the reader never finishes (the measurements are recorded in index.html). With
one image per page the reader pulls 2-3 files of roughly 50-180 KB per spread,
and the first page is on screen as soon as one small file arrives.

Output
    assets/pages/<id>/<n>.jpg    one page, 1100 px wide by default
    assets/pages/<id>/meta.json  pages, source page box, aspect, wide, toc
    assets/pages/manifest.json   {id: {...}} - the one file the reader fetches

The toc inside meta.json exists so the reader still has a contents sidebar for
a catalogue that has no `toc-<id>.json` (the 2026 deck). Titles are picked the
same way the old in-browser auto-extractor did: the largest text line on a page,
scored, and consecutive repeats merged into one entry.

Usage
    python tools/gen_page_images.py              # incremental (skips fresh pages)
    python tools/gen_page_images.py --force      # re-render everything
    python tools/gen_page_images.py --only kitchen --width 900
"""
import argparse
import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
CATALOGS = json.loads((ROOT / "catalogs.json").read_text(encoding="utf-8"))
OUT = ROOT / "assets" / "pages"
DEFAULT_WIDTH = 1100
DEFAULT_QUALITY = 72

CODE_RE = re.compile(r"^[A-Z]\d*-\d{1,3}$|^[A-Z]{0,2}\d{2,}$|^\d+[A-Z]?$|^No\.\s*\d|^[IVX]+\.?$", re.I)
SIZE_RE = re.compile(r"^\d+[*xX-]\d|^\d+mm|^\d+ml|^\d+g\b|^[()\d\s,.*xX]+$")


def title_score(s):
    """Same scoring the reader used, so the sidebar keeps looking the same."""
    if not s:
        return 0
    v = 0
    if re.search(r"[a-zA-Z]", s):
        v += 5
    if re.search(r"\s", s):
        v += 8
    if len(s) >= 8:
        v += 3
    if len(s) >= 12:
        v += 4
    if re.search(r"[a-z].*[A-Z]|[A-Z].*[a-z]", s):
        v += 3
    if CODE_RE.match(s):
        v -= 20
    if SIZE_RE.match(s):
        v -= 20
    if re.fullmatch(r"\d+", s):
        v -= 20
    if len(s) > 65:
        v -= 10
    if re.match(r"^[A-Z][a-z]+", s):
        v += 2
    return v


def auto_toc(doc):
    """Largest-font line per page, merged when it repeats - a page-title outline."""
    entries = []
    for pno in range(1, doc.page_count):          # the reader skipped page 1 too
        try:
            blocks = doc[pno].get_text("dict").get("blocks", [])
        except Exception:
            continue
        by_size = {}
        for blk in blocks:
            for ln in blk.get("lines", []):
                txt = "".join(sp.get("text", "") for sp in ln.get("spans", [])).strip()
                if not txt:
                    continue
                size = round(max((sp.get("size", 0) for sp in ln.get("spans", [])), default=0), 1)
                by_size.setdefault(size, []).append(txt)
        if not by_size:
            continue
        top = sorted(by_size, reverse=True)[:1]
        best, best_score = None, -999
        for size in top:
            for line in by_size[size]:
                if "@" in line or "www." in line or "http" in line or len(line) < 6:
                    continue
                sc = title_score(line)
                if sc > best_score:
                    best, best_score = line, sc
        if best and best_score > 5:
            entries.append({"title": best, "page": pno + 1})
    merged = []
    for e in entries:
        if merged and merged[-1]["title"] == e["title"]:
            merged[-1]["pageEnd"] = e["page"]
            continue
        merged.append({"title": e["title"], "page": e["page"], "pageEnd": e["page"]})
    return merged


def toc_from_file(cat):
    """The site's own toc-<id>.json, flattened to the shape the sidebar wants."""
    if not cat.get("toc"):
        return None
    raw = json.loads((ROOT / cat["toc"]).read_text(encoding="utf-8"))
    out = []

    def walk(items):
        for it in items:
            if it.get("children"):
                walk(it["children"])
            else:
                out.append({"title": it["title"], "page": int(it["page"]), "pageEnd": int(it["page"])})

    walk(raw)
    for i, e in enumerate(out):
        e["pageEnd"] = out[i + 1]["page"] - 1 if i + 1 < len(out) else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-render pages that are already there")
    ap.add_argument("--only", help="one catalogue id")
    ap.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    ap.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    args = ap.parse_args()

    manifest, total, skipped = {}, 0, 0
    for cat in CATALOGS:
        if args.only and cat["id"] != args.only:
            if (OUT / cat["id"] / "meta.json").exists():
                manifest[cat["id"]] = json.loads(
                    (OUT / cat["id"] / "meta.json").read_text(encoding="utf-8"))
            continue
        pdf = ROOT / cat["pdf"]
        if not pdf.exists():
            print("MISSING PDF:", pdf)
            continue
        doc = pymupdf.open(pdf)
        rect = doc[0].rect
        d = OUT / cat["id"]
        d.mkdir(parents=True, exist_ok=True)
        src_mtime = pdf.stat().st_mtime
        for pno in range(doc.page_count):
            out = d / ("%d.jpg" % (pno + 1))
            if not args.force and out.exists() and out.stat().st_mtime > src_mtime:
                skipped += 1
                continue
            page = doc[pno]
            zoom = args.width / page.rect.width
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            out.write_bytes(pix.tobytes("jpeg", jpg_quality=args.quality))
            total += 1
        toc = toc_from_file(cat) or auto_toc(doc)
        meta = {"pages": doc.page_count, "w": round(rect.width, 2), "h": round(rect.height, 2),
                "aspect": round(rect.width / max(rect.height, 1), 4),
                "wide": rect.width >= rect.height * 1.05,
                "width": args.width, "toc": toc}
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        manifest[cat["id"]] = meta
        size = sum(f.stat().st_size for f in d.glob("*.jpg")) // 1024
        print("%-9s %3d pages%s  %d KB on disk  toc=%d entries"
              % (cat["id"], doc.page_count, " (skipped)" if not args.force else "",
                 size, len(toc)))
        doc.close()

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print("\nrendered %d pages, skipped %d; manifest has %d catalogues"
          % (total, skipped, len(manifest)))


if __name__ == "__main__":
    main()
