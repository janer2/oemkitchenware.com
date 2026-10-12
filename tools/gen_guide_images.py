#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cut one product shot per catalogue item for the buyer-guide pages.

The guides list products by their printed code, and a code is printed right
under its own photo on the catalogue page - so the code's position in the text
layer marks where its product sits. Find the code, crop a cell-sized box above
it, and the result is the real product photo. No geometry is guessed per page:
a page can hold one row or two, a full grid or a single group card, and the
crop follows the code either way. Only the cell width comes from the layout
(4 columns on a landscape deck, 3 on a portrait one).

Measured on 2026-10-12: every code sampled across the six catalogues was found
in its page's text layer, and the crops framed exactly one product.

Each crop is then trimmed to the product itself, so the frame is the product
and not the page around it. Aspect ratio is preserved everywhere - the cards
show the photo at its own proportions instead of squashing it into a square.

Output
    assets/guide-images/<CODE>.webp    480 px long side: hero + gallery cards
    assets/guide-images/t/<CODE>.webp  128 px long side: the item-table rows
    assets/guide-images/index.json     which codes got an image, and the
                                       per-guide shortlist the page renders

Usage
    python tools/gen_guide_images.py            # incremental
    python tools/gen_guide_images.py --force    # re-cut everything
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_seo_pages as G  # noqa: E402  (same folder, single source of truth)

ROOT = G.ROOT
PAGES = ROOT / "assets" / "pages"
OUT = ROOT / "assets" / "guide-images"
BIG, THUMB = 480, 128     # long side; both keep the crop's own aspect ratio
CELL_SCALE = 1.02         # a little wider than the column so nothing is clipped


def fit(im, long_side):
    """Scale so the longer edge is `long_side`. Never distort the aspect."""
    w, h = im.size
    sc = long_side / float(max(w, h))
    return im.resize((max(1, round(w * sc)), max(1, round(h * sc))), Image.LANCZOS)


def trim(im, tol=18, min_keep=0.30):
    """Trim the page background off a crop so the product is what you see.

    The background is read per row from that row's own outer pixels, so a page
    with a vertical gradient is handled as well as a plain white one. If the
    result would throw away most of the crop the detection was wrong (the
    product probably touches the frame), so the crop is returned untouched.
    """
    a = np.asarray(im.convert("RGB"), dtype=np.int16)
    h, w, _ = a.shape
    edge = max(3, int(min(h, w) * 0.02))
    bg = (a[:, :edge].mean(axis=1) + a[:, -edge:].mean(axis=1)) / 2.0
    ink = np.abs(a - bg[:, None, :]).max(axis=2) > tol
    rows = np.where(ink.mean(axis=1) > 0.01)[0]
    if not len(rows):
        return im
    y0, y1 = int(rows[0]), int(rows[-1]) + 1
    sub = a[y0:y1]
    bg2 = (sub[:edge].mean(axis=0) + sub[-edge:].mean(axis=0)) / 2.0
    ink2 = np.abs(sub - bg2[None, :, :]).max(axis=2) > tol
    cols = np.where(ink2.mean(axis=0) > 0.01)[0]
    if not len(cols):
        return im
    x0, x1 = int(cols[0]), int(cols[-1]) + 1
    if (y1 - y0) * (x1 - x0) < min_keep * h * w:
        return im
    px, py = max(2, int((x1 - x0) * 0.04)), max(2, int((y1 - y0) * 0.04))
    return im.crop((max(0, x0 - px), max(0, y0 - py), min(w, x1 + px), min(h, y1 + py)))


def norm(s):
    return re.sub(r"[\s\-]", "", s or "").upper()


def page_text_lines(pdf_path, pn):
    """Every text line on the page as (bbox, text), in PDF points."""
    doc = pymupdf.open(pdf_path)
    page = doc[pn - 1]
    lines = []
    for blk in page.get_text("dict").get("blocks", []):
        for ln in blk.get("lines", []):
            txt = "".join(sp.get("text", "") for sp in ln.get("spans", [])).strip()
            if txt:
                lines.append((tuple(ln["bbox"]), txt))
    rect = page.rect
    doc.close()
    return lines, rect.width, rect.height


def code_box(lines, code):
    """Where this code is printed on the page (PDF points)."""
    want = norm(code)
    for bb, txt in lines:
        t = norm(txt)
        if t == want or (len(want) >= 5 and want in t):
            return bb
    return None


def content_top(rendered, x0, x1, y_bottom):
    """Top edge of the photo that belongs to this code.

    A landscape deck prints on white, so the page's own ink says which band is
    the photo: a product shot is a tall dense block (~330-420 px at this render
    width), a line of type is a thin one (~25-70 px), and the page header is
    thin too. So the photo is the last tall block above the code - that skips
    the name/code lines directly above it and everything from the row above.
    Measured on 2026-10-12 across new2026 and 2023: block heights 327-416 px for
    photos against 24-79 px for text.
    """
    strip = np.asarray(rendered.convert("L").crop((x0, 0, x1, y_bottom)), dtype=np.uint8)
    ink = (strip < 246).mean(axis=1) > 0.02
    bands, start = [], None
    for i, on in enumerate(ink):
        if on and start is None:
            start = i
        elif not on and start is not None:
            bands.append((start, i))
            start = None
    if start is not None:
        bands.append((start, len(ink)))
    tall = [b for b in bands if b[1] - b[0] >= 150]
    near = [b for b in (tall or bands) if b[1] <= y_bottom + 2]
    if not near:
        return None
    return max(max(near, key=lambda b: b[1])[0] - 4, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    cats = {c["id"]: c for c in G.CATS}
    products = G.load_products()
    wanted = {}                      # code -> product row
    per_guide = {}
    for guide in G.GUIDES_DATA:
        rows = G.guide_matches(products, guide, limit=20)
        per_guide[guide["slug"]] = [p["code"] for p in rows]
        for p in rows:
            wanted.setdefault(p["code"], p)
    print("guides:", len(per_guide), " codes referenced:", len(wanted))

    (OUT / "t").mkdir(parents=True, exist_ok=True)
    index = {}
    done = skipped = missing = 0
    for code, p in sorted(wanted.items()):
        big, small = OUT / ("%s.webp" % code), OUT / "t" / ("%s.webp" % code)
        if not args.force and big.exists() and small.exists():
            index[code] = {"c": p["cid"], "p": p["pn"], "n": p["name"]}
            skipped += 1
            continue
        src = PAGES / p["cid"] / ("%d.webp" % p["pn"])
        if not src.exists():
            missing += 1
            continue
        cat = cats.get(p["cid"])
        pdf = ROOT / cat["pdf"] if cat else None
        if not pdf or not pdf.exists():
            missing += 1
            continue
        try:
            lines, pw, ph = page_text_lines(pdf, p["pn"])
        except Exception:
            missing += 1
            continue
        rendered = Image.open(src)
        landscape = rendered.width > rendered.height
        bb = code_box(lines, code)
        if not bb:
            missing += 1
            continue
        sc = rendered.width / pw
        cellw = (rendered.width / (4 if landscape else 3)) * CELL_SCALE
        cx = ((bb[0] + bb[2]) / 2) * sc
        left, right = int(cx - cellw / 2), int(cx + cellw / 2)
        bottom = int(bb[1] * sc) - 3
        top = content_top(rendered, max(left, 0), min(right, rendered.width), bottom) \
            if landscape else bottom - int(cellw)
        if top is None:
            top = max(bottom - int(cellw), 0)
        box = (max(left, 0), max(top, 0), min(right, rendered.width), min(bottom, rendered.height))
        if box[2] - box[0] < 60 or box[3] - box[1] < 60:
            missing += 1
            continue
        im = trim(rendered.crop(box).convert("RGB"))
        fit(im, BIG).save(big, "WEBP", quality=80, method=5)
        fit(im, THUMB).save(small, "WEBP", quality=78, method=5)
        index[code] = {"c": p["cid"], "p": p["pn"], "n": p["name"]}
        done += 1

    (OUT / "index.json").write_text(
        json.dumps({"codes": index, "guides": per_guide}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    size = sum(f.stat().st_size for f in OUT.glob("*.webp"))
    size += sum(f.stat().st_size for f in (OUT / "t").glob("*.webp"))
    print("cut %d, reused %d, no image %d; %d KB on disk" % (done, skipped, missing, size // 1024))
    for slug, codes in per_guide.items():
        got = sum(1 for c in codes if c in index)
        print("  %-46s %2d/%2d images" % (slug, got, len(codes)))


if __name__ == "__main__":
    main()
