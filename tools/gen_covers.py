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
    if not pdf_path.exists():
        print("MISSING PDF:", pdf_path)
        continue
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    rect = page.rect
    zoom = WIDTH / max(rect.width, 1)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_bytes(pix.tobytes("jpeg", jpg_quality=QUALITY))
    print(f"{cat['id']:8s} page={rect.width:.0f}x{rect.height:.0f}pt "
          f"-> {out.name} {out.stat().st_size//1024} KB "
          f"({pix.width}x{pix.height})")
    doc.close()
