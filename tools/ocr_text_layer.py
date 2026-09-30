# -*- coding: utf-8 -*-
"""Add an invisible text layer to an image-only catalog PDF with RapidOCR.

The decks are picture-per-page exports, so nothing is searchable. OCR each page
and write the recognised lines back as invisible text (render mode 3) at their
own positions: the pages look identical, but text extraction, the site search
index and copy/paste all work.

Two things keep this from being a full re-run every time a deck changes:

* **Skip if there is nothing to do.** A file that already carries a text layer is
  left alone instead of being OCR'd a second time.
* **Per-page cache.** The recognised runs are stored under the hash of each
  page's images, so a re-run only OCRs pages whose picture actually changed. Add
  a divider page to a 124-page deck and 1 page is processed, not 124. The cache
  lives in .ocr-cache/ (git-ignored) and is keyed on the images, which is why
  writing a text layer into the file does not invalidate it.

Recognition is CPU-bound and onnxruntime already uses several cores per call, so
the default is one process. Raising --jobs on a small machine just makes it
slower: measured on this 124-page deck, 3.2s/page sequentially versus 4.0s/page
with 6 workers fighting for the same cores.

Usage:
    python tools/ocr_text_layer.py --limit 1            # smoke test on page 1
    python tools/ocr_text_layer.py                      # whole file, cached
    python tools/ocr_text_layer.py --src in.pdf --dst out.pdf
    python tools/ocr_text_layer.py --no-cache           # ignore the cache
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "catalog-2026new.pdf"
DST = ROOT / "assets" / "_catalog-2026new.ocr.pdf"
CACHE_DIR = ROOT / ".ocr-cache"

ZOOM = 2.0          # raster scale used for OCR
MIN_SCORE = 0.50    # drop low-confidence lines
TEXT_PAGE_RATIO = 0.8   # above this share of text pages, assume a layer exists
ASCII = re.compile(r"[^\x20-\x7e]+")

_W = {}


def clean(text):
    """Keep what the built-in fonts can encode; the decks themselves are English.

    Tight display type comes back glued together ("Knives&CuttingBoards"), which
    would break multi-word search, so split those boundaries back out.
    """
    t = ASCII.sub(" ", text)
    t = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t)
    t = re.sub(r"\s*&\s*", " & ", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def page_key(doc, page):
    """Fingerprint of what a page *looks* like: its images, not its text layer."""
    h = hashlib.sha1()
    rect = page.rect
    h.update(("%.1fx%.1f" % (rect.width, rect.height)).encode())
    for img in page.get_images(full=True):
        xref = img[0]
        try:
            h.update(doc.xref_stream_raw(xref) or b"")
        except Exception:
            h.update(("xref%d" % xref).encode())
    return h.hexdigest()


def text_pages(doc):
    return sum(1 for i in range(doc.page_count) if len(doc[i].get_text().strip()) > 20)


def cache_path(cache_id):
    return CACHE_DIR / ("%s.json" % cache_id)


def load_cache(cache_id):
    p = cache_path(cache_id)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache_id, cache):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path(cache_id).write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def _init_worker(src, zoom, min_score):
    _W["doc"] = pymupdf.open(src)
    _W["zoom"] = zoom
    _W["min"] = min_score
    from rapidocr_onnxruntime import RapidOCR
    _W["ocr"] = RapidOCR()


def _ocr_page(pno):
    """Recognise one page; returns the runs to insert, in PDF points."""
    doc, ocr, zoom, min_score = _W["doc"], _W["ocr"], _W["zoom"], _W["min"]
    page = doc[pno]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    import numpy as np
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    t0 = time.time()
    result, _ = ocr(img)
    runs = []
    if result:
        s = 1.0 / zoom
        for box, text, score in result:
            if score is not None and score < min_score:
                continue
            txt = clean(text)
            if len(txt) < 2:
                continue
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x0, y1 = min(xs) * s, max(ys) * s
            h = max(1.0, (max(ys) - min(ys)) * s)
            runs.append({"t": txt, "x": round(x0, 1), "y": round(y1 - h * 0.22, 1),
                         "s": round(max(3.5, min(26.0, h * 0.78)), 2)})
    return runs, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--src", default=str(SRC))
    ap.add_argument("--dst", default=str(DST))
    ap.add_argument("--cache-id", default="")
    ap.add_argument("--jobs", type=int, default=1,
                    help="parallel OCR processes; 1 is fastest on most machines "
                         "(onnxruntime already threads each call)")
    ap.add_argument("--no-cache", action="store_true", help="ignore cached pages")
    args = ap.parse_args()

    cache_id = args.cache_id or Path(args.src).stem
    doc = pymupdf.open(args.src)
    total = doc.page_count
    limit = args.limit or total

    have = text_pages(doc)
    if have >= total * TEXT_PAGE_RATIO and not args.no_cache:
        print("nothing to do: %d/%d pages already carry text (%s)"
              % (have, total, Path(args.src).name), flush=True)
        doc.close()
        return 0

    keys = {pno: page_key(doc, doc[pno]) for pno in range(limit)}
    doc.close()

    cache = {} if args.no_cache else load_cache(cache_id)
    todo = [pno for pno in range(limit) if keys[pno] not in cache]
    reused = limit - len(todo)
    print("pages: %d   cached: %d   to OCR: %d" % (limit, reused, len(todo)), flush=True)

    if todo:
        jobs = args.jobs or min(6, os.cpu_count() or 1)
        done = 0
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=jobs, initializer=_init_worker,
                                 initargs=(args.src, ZOOM, MIN_SCORE)) as pool:
            futures = {pool.submit(_ocr_page, pno): pno for pno in todo}
            for fut in as_completed(futures):
                pno = futures[fut]
                try:
                    runs, secs = fut.result()
                except Exception as exc:                      # keep going
                    print("page %d FAILED: %s" % (pno + 1, exc), flush=True)
                    continue
                cache[keys[pno]] = runs
                done += 1
                print("  %3d/%d  page %3d  runs=%3d  %.1fs"
                      % (done, len(todo), pno + 1, len(runs), secs), flush=True)
        save_cache(cache_id, cache)
        print("OCR done in %.0fs (%d pages, %d workers)"
              % (time.time() - t0, len(todo), jobs), flush=True)

    # Write the layer in the main process: PyMuPDF edits are not shared safely.
    doc = pymupdf.open(args.src)
    written = 0
    for pno in range(limit):
        runs = cache.get(keys[pno]) or []
        if not runs:
            continue
        page = doc[pno]
        for r in runs:
            page.insert_text((r["x"], r["y"]), r["t"], fontsize=r["s"],
                             fontname="helv", render_mode=3)
            written += 1
    doc.save(args.dst, garbage=4, deflate=True)
    doc.close()
    print("wrote %s  lines=%d  size=%.1f MB"
          % (args.dst, written, os.path.getsize(args.dst) / 1048576.0), flush=True)

    chk = pymupdf.open(args.dst)
    for p in (0, 4, 26):
        if p < chk.page_count:
            t = " ".join(chk[p].get_text().split())
            print("extract p%d: %s" % (p + 1, t[:200]))
    chk.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
