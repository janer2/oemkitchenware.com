# -*- coding: utf-8 -*-
"""Add an invisible text layer to an image-only catalog PDF with RapidOCR.

The deck is a picture-per-page export, so nothing is searchable. OCR each page
and write the recognised lines back as invisible text (render mode 3) at their
own positions: the pages look identical, but text extraction, the site search
index and copy/paste all work.

Usage:
    python tools/ocr_text_layer.py --limit 1        # smoke test on page 1
    python tools/ocr_text_layer.py                  # whole file
"""
import argparse
import re
import sys
import time
from pathlib import Path

import numpy as np
import pymupdf

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "catalog-2026new.pdf"
DST = ROOT / "assets" / "_catalog-2026new.ocr.pdf"

ZOOM = 2.0          # raster scale used for OCR
MIN_SCORE = 0.50    # drop low-confidence lines
ASCII = re.compile(r"[^\x20-\x7e]+")


def clean(text):
    """Keep what the built-in fonts can encode; the deck itself is English.

    Tight display type comes back glued together ("Knives&CuttingBoards"), which
    would break multi-word search, so split those boundaries back out.
    """
    t = ASCII.sub(" ", text)
    t = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t)
    t = re.sub(r"\s*&\s*", " & ", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--src", default=str(SRC))
    ap.add_argument("--dst", default=str(DST))
    args = ap.parse_args()

    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()

    doc = pymupdf.open(args.src)
    total = doc.page_count
    limit = args.limit or total
    print("pages:", total, "processing:", limit, flush=True)

    written = 0
    for pno in range(limit):
        page = doc[pno]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = img[:, :, :3]
        t0 = time.time()
        result, _ = ocr(img)
        lines = 0
        if result:
            s = 1.0 / ZOOM
            for box, text, score in result:
                if score is not None and score < MIN_SCORE:
                    continue
                txt = clean(text)
                if len(txt) < 2:
                    continue
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                x0, x1 = min(xs) * s, max(xs) * s
                y0, y1 = min(ys) * s, max(ys) * s
                h = max(1.0, y1 - y0)
                size = max(3.5, min(26.0, h * 0.78))
                page.insert_text((x0, y1 - h * 0.22), txt, fontsize=size,
                                 fontname="helv", render_mode=3)
                lines += 1
                written += 1
        print("page %d/%d  lines=%d  %.1fs" % (pno + 1, limit, lines, time.time() - t0), flush=True)

    doc.save(args.dst, garbage=4, deflate=True)
    print("wrote", args.dst, "lines total:", written)

    # smoke check: the layer must be extractable
    chk = pymupdf.open(args.dst)
    for p in (0, 4, 26):
        if p < chk.page_count:
            t = " ".join(chk[p].get_text().split())
            print("extract p%d: %s" % (p + 1, t[:200]))


if __name__ == "__main__":
    sys.exit(main())
