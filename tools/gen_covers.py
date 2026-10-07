# -*- coding: utf-8 -*-
"""Render page 1 of each catalog PDF into assets/covers/{id}.jpg
so the homepage can show static <img> covers instead of downloading
the whole PDF via pdf.js (24MB -> a few hundred KB)."""
import json
from pathlib import Path

import pymupdf  # PyMuPDF

BASE = Path(r"C:\oemkitchenware")
CATALOGS = json.loads((BASE / "catalogs.json").read_text(encoding="utf-8"))
OUT = BASE / "assets" / "covers"
WIDTH = 640          # ~2x the largest on-page card width
QUALITY = 76

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
    # A landscape cover is a wide poster with its title on the left; showing the
    # whole thing in a portrait card leaves that text unreadably small, so the
    # card gets the left portion instead (the full page is still in the reader).
    clip = None
    if rect.width > rect.height * 1.3:
        clip = pymupdf.Rect(rect.x0, rect.y0, rect.x0 + rect.width * 0.56, rect.y1)
    src = clip or rect
    zoom = WIDTH / max(src.width, 1)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False, clip=clip)
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_bytes(pix.tobytes("jpeg", jpg_quality=QUALITY))
    print(f"{cat['id']:8s} page={rect.width:.0f}x{rect.height:.0f}pt "
          f"-> {out.name} {out.stat().st_size//1024} KB "
          f"({pix.width}x{pix.height})")
    doc.close()

# assets/page1/{id}.jpg - the reader paints this the instant a catalog opens, so
# there is something on screen while pdf.js streams the document in. Always the
# real first page of the PDF, even for a catalog whose card cover is a designed
# piece of artwork.
P1 = BASE / "assets" / "page1"
P1_W, P1_Q = 760, 80
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
