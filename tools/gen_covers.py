# -*- coding: utf-8 -*-
"""Render page 1 of each catalog PDF into assets/covers/{id}.jpg
so the homepage can show static <img> covers instead of downloading
the whole PDF via pdf.js (24MB -> a few hundred KB)."""
import json
from pathlib import Path

import pymupdf  # PyMuPDF
from PIL import Image

BASE = Path(r"C:\oemkitchenware")
CATALOGS = json.loads((BASE / "catalogs.json").read_text(encoding="utf-8"))
OUT = BASE / "assets" / "covers"
WIDTH = 640          # ~2x the largest on-page card width
QUALITY = 76


SQ_MIN_BAND = 0.03   # a band narrower than 3% of the width is a border, not a band
SQ_MAX_BAND = 0.22   # wider than this and it is content we must not cut
SQUARE = 720


def busy_profile(im):
    """Per-column pixel spread: near zero on a flat panel, large on a photo."""
    g = im.convert("L")
    w, h = g.size
    px = g.load()
    step = max(1, h // 160)
    prof = []
    for x in range(w):
        vals = [px[x, y] for y in range(0, h, step)]
        n = len(vals)
        if n < 2:
            prof.append(0.0)
            continue
        mean = sum(vals) / n
        prof.append((sum((v - mean) ** 2 for v in vals) / n) ** 0.5)
    return prof


def photo_region(im):
    """Bounding box of the longest busy run of columns, or None if it is all flat."""
    prof = busy_profile(im)
    w = len(prof)
    thr = max(12.0, max(prof) * 0.35)
    best = (0, 0)
    run_start = None
    gap = 0
    for x, v in enumerate(prof):
        if v >= thr:
            if run_start is None:
                run_start = x
            gap = 0
        elif run_start is not None:
            gap += 1
            if gap > 10:                      # tolerate a thin divider inside the photo
                if x - gap - run_start > best[1] - best[0]:
                    best = (run_start, x - gap)
                run_start = None
    if run_start is not None and w - run_start > best[1] - best[0]:
        best = (run_start, w)
    x0, x1 = best
    if x1 - x0 < w * 0.25:                    # no clear panel split: keep the page
        return None
    return (x0, 0, x1, im.size[1])


def square_fill(im, anchor="centre"):
    """Largest square that fits, taken where the subject is."""
    w, h = im.size
    if w == h:
        return im
    side = min(w, h)
    if anchor == "top":
        top = 0
    elif anchor == "bottom":
        top = h - side
    else:
        top = (h - side) // 2
    left = (w - side) // 2
    return im.crop((left, top, left + side, top + side))


for cat in CATALOGS:
    pdf_path = BASE / cat["pdf"]
    out = OUT / (cat["id"] + ".jpg")
    # A catalogue can carry a designed cover instead of page 1 of its PDF; then
    # the artwork is installed with tools/set_cover.py and left untouched here.
    if cat.get("coverLocked"):
        print(f"{cat['id']:8s} cover locked, keeping {out.name}")
        continue
    if not pdf_path.exists():
        print("MISSING PDF:", pdf_path)
        continue
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    rect = page.rect
    zoom = 1000 / max(rect.width, 1)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    box = photo_region(im)
    if box:
        im = im.crop(box)
    im = square_fill(im, anchor="top" if rect.height > rect.width else "centre")
    im = im.resize((SQUARE, SQUARE), Image.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"")
    im.save(out, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    print(f"{cat['id']:8s} {im.size[0]}x{im.size[1]} -> {out.name} {out.stat().st_size//1024} KB")
    doc.close()

# assets/page1/{id}.jpg - the reader paints this the instant a catalog opens, so
# there is something on screen while pdf.js streams the document in. Always the
# real first page of the PDF, even for a catalog whose card cover is a designed
# piece of artwork.
P1 = BASE / "assets" / "page1"
# 760 px was fine as a quick placeholder, but this still is also what the reader
# shows full-bleed behind the loading spinner and what page 1 paints until its
# real image arrives - and on a 2200-2320 px page area that is a 3x upscale, i.e.
# visibly blurred cover. At 1800 it is roughly the size the reader actually draws
# and still lands near the page image it replaces (~200 KB vs ~116 KB).
P1_W, P1_Q = 1800, 80
for cat in CATALOGS:
    pdf_path = BASE / cat["pdf"]
    if not pdf_path.exists():
        print("MISSING PDF:", pdf_path)
        continue
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    rect = page.rect
    zoom = P1_W / max(rect.width, 1)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    P1.mkdir(parents=True, exist_ok=True)
    out = P1 / (cat["id"] + ".jpg")
    out.write_bytes(pix.tobytes("jpeg", jpg_quality=P1_Q))
    print(f"{cat['id']:8s} page1 -> {out.name} {out.stat().st_size//1024} KB "
          f"({pix.width}x{pix.height})")
    doc.close()

# assets/covers/{id}-400.jpg - the smaller candidate the homepage card and the
# nav dropdown pick on phones (srcset). Derived from whatever cover is actually
# in place, so a designed (locked) cover and a rendered page 1 both stay in sync.
# These used to be made by hand: the 2023 catalog shipped with a srcset entry
# pointing at a 404, and a failed candidate makes the card run coverFallback()
# and download the entire PDF just to draw its thumbnail.
THUMB_W, THUMB_Q = 400, 82
for cat in CATALOGS:
    src = OUT / (cat["id"] + ".jpg")
    if not src.exists():
        print(f"{cat['id']:8s} no cover to shrink")
        continue
    im = Image.open(src).convert("RGB")
    th = max(1, int(round(im.height * THUMB_W / max(im.width, 1))))
    im = im.resize((THUMB_W, th), Image.LANCZOS)
    out = OUT / (cat["id"] + "-400.jpg")
    im.save(out, "JPEG", quality=THUMB_Q, optimize=True, progressive=True)
    print(f"{cat['id']:8s} thumb -> {out.name} {out.stat().st_size//1024} KB ({THUMB_W}x{th})")
