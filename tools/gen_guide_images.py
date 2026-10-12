#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cut one product shot per catalogue item for the guide and product pages.

Where the picture is
    A catalogue prints each item's code next to its own photo, so the code's
    position in the page's text layer marks where that product sits, and the
    codes around it mark where its cell ends. Each crop is therefore bounded by
    the neighbouring codes, not by a guessed offset:

      top    = just below the previous item's cell in the same column (or, when
               there is nothing above, one cell height up from this code)
      bottom = this item's own code line

    Inside that band the page's own ink decides the box: the row background is
    read from the band's outer edge columns, and everything that differs from it
    is content. On a portrait page that is the product's white panel - exactly
    the region a buyer would crop by hand - and on a landscape deck it is the
    photo plus its printed name. Nothing from the row above can be picked up,
    because the band never reaches it.

Why it is sharp
    The crop is rendered from the PDF at 1400 px on its long side and then
    resampled down, instead of being cut out of the already-compressed page
    WebP and scaled back up. That removes one whole WebP generation and gives
    the resampler real pixels to work with. The embedded artwork sets the
    ceiling: measured 2026-10-12, a 2023 cell carries 454-722 px, a 2026 cell
    about 480 px (its page is one 1920x1080 raster), a kitchen cell only
    240-300 px, so the portrait catalogues cannot be pushed further than they
    already are.

Output
    assets/guide-images/<CODE>.webp    640 px long side: hero + cards
    assets/guide-images/t/<CODE>.webp  320 px long side: the item grid
    assets/guide-images/index.json     which codes got an image, and the
                                       per-guide shortlist the pages render

Usage
    python tools/gen_guide_images.py             # incremental
    python tools/gen_guide_images.py --force     # re-cut everything
    python tools/gen_guide_images.py --debug     # also write a box-check sheet
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_seo_pages as G  # noqa: E402  (same folder, single source of truth)

ROOT = G.ROOT
PAGES = ROOT / "assets" / "pages"
OUT = ROOT / "assets" / "guide-images"
BIG, THUMB = 640, 320      # long side; the crop's own aspect ratio is kept
RENDER_LONG = 1400         # intermediate render from the PDF, then downsampled
CELL_SCALE = 1.02          # a little wider than the column so nothing is clipped
TOP_ALLOW = {"wide": 0.13, "tall": 0.20}   # of page height, above the code above
INK_TOL = 22               # how far a pixel must differ from the row background
PANEL_MIN = 232            # channel floor for the white product panel
PANEL_NEUTRAL = 14         # channel spread above which it is the page's colour


def fit(im, long_side):
    """Scale so the longer edge is `long_side`. Never distort the aspect."""
    w, h = im.size
    sc = long_side / float(max(w, h))
    return im.resize((max(1, round(w * sc)), max(1, round(h * sc))), Image.LANCZOS)


def trim(im, tol=INK_TOL, min_keep=0.30):
    """Trim uniform page background off the edges of a render.

    The background is read per row from that row's own outer pixels, so a
    leftover band of the page's gradient - which is what leaks in above the
    first row of a portrait page - reads as background and goes. If the result
    would throw away most of the crop the detection misfired, so the crop is
    returned untouched.
    """
    a = np.asarray(im.convert("RGB"), dtype=np.int16)
    h, w, _ = a.shape
    e = max(3, int(min(h, w) * 0.02))
    bg = (a[:, :e].mean(axis=1) + a[:, -e:].mean(axis=1)) / 2.0
    ink = np.abs(a - bg[:, None, :]).max(axis=2) > tol
    rows = np.where(ink.mean(axis=1) > 0.01)[0]
    if not len(rows):
        return im
    y0, y1 = int(rows[0]), int(rows[-1]) + 1
    sub = a[y0:y1]
    bg2 = (sub[:e].mean(axis=0) + sub[-e:].mean(axis=0)) / 2.0
    ink2 = np.abs(sub - bg2[None, :, :]).max(axis=2) > tol
    cols = np.where(ink2.mean(axis=0) > 0.01)[0]
    if not len(cols):
        return im
    x0, x1 = int(cols[0]), int(cols[-1]) + 1
    if (y1 - y0) * (x1 - x0) < min_keep * h * w:
        return im
    return im.crop((x0, y0, x1, y1))


def pad_frac(im, frac=0.04):
    """Put a small white margin back.

    White, not the crop's own corner pixel: on a portrait page that corner is
    the page's peach, and padding with it draws a uniform peach border round all
    four sides of the card - which is what a review screenshot showed.
    """
    w, h = im.size
    dx, dy = max(2, int(w * frac)), max(2, int(h * frac))
    out = Image.new("RGB", (w + 2 * dx, h + 2 * dy), (255, 255, 255))
    out.paste(im, (dx, dy))
    return out


def norm(s):
    return re.sub(r"[\s\-]", "", s or "").upper()


def text_spans(pdf_path, pn):
    """Every text span on the page: (bbox in points, text)."""
    doc = pymupdf.open(pdf_path)
    page = doc[pn - 1]
    spans = []
    for blk in page.get_text("dict").get("blocks", []):
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                if sp.get("text", "").strip():
                    spans.append((tuple(sp["bbox"]), sp["text"]))
    rect = page.rect
    doc.close()
    return spans, rect.width, rect.height


def find_code(spans, code):
    """Where this code is printed, in points."""
    want = norm(code)
    for bb, txt in spans:
        t = norm(txt)
        if t == want or (len(want) >= 5 and want in t):
            return bb
    return None


def row_groups(a, page_h, tol=INK_TOL):
    """Runs of content rows in a band, merged across small gaps.

    The background is read per row from the band's own outer columns, so a page
    with a vertical gradient is handled the same as a plain white one.
    """
    e = max(3, int(a.shape[1] * 0.02))
    bg = (a[:, :e].mean(axis=1) + a[:, -e:].mean(axis=1)) / 2.0
    ink = (np.abs(a - bg[:, None, :]).max(axis=2) > tol).mean(axis=1) > 0.005
    # Small on purpose. A portrait page runs [panel][code][name][bullets], so a
    # wide gap would fuse the panel to the *previous* item's bullets and the
    # crop would open with someone else's spec list - which is what the review
    # screenshots showed. Measured: bullets end 1205 px, the next panel starts
    # 1300 px (95 px apart), while a photo and its own name sit 70 px apart.
    gap = 0.035 * page_h
    out, start = [], None
    for i, on in enumerate(ink):
        if on and start is None:
            start = i
        elif not on and start is not None:
            out.append([start, i])
            start = None
    if start is not None:
        out.append([start, len(ink)])
    merged = []
    for r in out:
        if merged and r[0] - merged[-1][1] < gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return merged


def ink_box(rendered, left, right, code_y, page_h):
    """The product photo's box in page pixels, or None.

    A cell holds one photo and a few lines of type. Going up from the code, the
    photo is the last *tall* content block - that skips the item's own printed
    name and stops dead at the row above, whenever the photo happens to sit
    relative to its code.
    """
    band = (max(int(left), 0), 0, min(int(right), rendered.width), max(int(code_y - 2), 1))
    if band[2] - band[0] < 40 or band[3] - band[1] < 40:
        return None
    a = np.asarray(rendered.crop(band).convert("RGB"), dtype=np.int16)
    groups = row_groups(a, page_h)
    if not groups:
        return None

    def box_of(g0, g1):
        sub = a[g0:g1]
        e = max(3, int(sub.shape[1] * 0.02))
        bg = (sub[:e].mean(axis=0) + sub[-e:].mean(axis=0)) / 2.0
        cols = np.abs(sub - bg[None, :, :]).max(axis=2) > INK_TOL
        xs = np.where(cols.mean(axis=0) > 0.005)[0]
        if not len(xs):
            return None
        return (band[0] + int(xs[0]), band[1] + g0, band[0] + int(xs[-1]) + 1, band[1] + g1)

    def photo_like(box):
        if not box:
            return False
        w, h = box[2] - box[0], box[3] - box[1]
        return h >= 0.05 * page_h and max(w, h) / float(max(min(w, h), 1)) <= 3.5

    tall = [g for g in groups if g[1] - g[0] >= 0.12 * page_h]
    box = box_of(*max(tall or groups, key=lambda g: g[1]))
    if photo_like(box):
        return box
    # A pale product (a clear glass jar on white, say) never forms a tall block,
    # and the nearest group above the code is then just its printed name - a
    # 5:1 strip of type with no product in it. Take the run of groups instead,
    # and refuse the crop entirely if that is still not photo shaped.
    near = [g for g in groups if g[1] <= band[3] and g[0] >= band[3] - 0.45 * page_h]
    if near:
        box = box_of(min(g[0] for g in near), max(g[1] for g in near))
        if photo_like(box):
            return box
    return None


def white_mask(a, lo_min=PANEL_MIN, spread=PANEL_NEUTRAL):
    """Light *and* neutral - the card, not the page's colour artwork.

    Measured on the kitchen pages 2026-10-12: a card is (255,254,255) while the
    page's gradient is (255,231,201), so a chroma test separates them even though
    both are bright. A per-row background test cannot: the gradient varies
    across a row, so nearly every pixel looks like content and the whole column
    comes back as one block.
    """
    lo, hi = a.min(axis=2), a.max(axis=2)
    return (lo >= lo_min) & ((hi - lo) <= spread)


def runs_of(flags, gap):
    """Start/end of each run of True, with short False gaps swallowed."""
    out, start = [], None
    for i, on in enumerate(flags):
        if on and start is None:
            start = i
        elif not on and start is not None:
            out.append([start, i])
            start = None
    if start is not None:
        out.append([start, len(flags)])
    merged = []
    for r in out:
        if merged and r[0] - merged[-1][1] < gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return merged


def extent(fraction, thresh):
    idx = np.where(fraction >= thresh)[0]
    return None if not len(idx) else (int(idx[0]), int(idx[-1]) + 1)


def portrait_box(rendered, spans, left, right, code_y, sc):
    """The photo area of a portrait page's card.

    A portrait cell runs [photo][code][name][bullets], so this item's photo is
    the card above its own code. Two signals bound it: the text layer puts the
    ceiling just below the previous item's last bullet (which is also what keeps
    the row above, and the page heading, out of the crop), and the white-card
    mask says which pixels belong to the card at all - the page's colour artwork
    varies across a row, so a plain background test calls the whole column
    content. Inside that region the product's own pixels set the frame.
    """
    floor = 0.0
    for bb, _ in spans:
        cx = (bb[0] + bb[2]) / 2 * sc
        y0, y1 = bb[1] * sc, bb[3] * sc
        if left <= cx <= right and y1 <= code_y - 4 and y0 < code_y:
            floor = max(floor, y1)
    top = max(floor + 0.015 * rendered.height, code_y - 0.42 * rendered.height, 0)
    band = (max(int(left), 0), int(top), min(int(right), rendered.width), max(int(code_y) - 4, 1))
    if band[2] - band[0] < 60 or band[3] - band[1] < 80:
        return None
    a = np.asarray(rendered.crop(band).convert("RGB"), dtype=np.int16)
    mask = white_mask(a)
    content = ~mask
    rows = runs_of(content.mean(axis=1) >= 0.01, gap=0.06 * rendered.height)
    if not rows:
        return None
    # Union, not the tallest run: a kit photo is one product in several rows.
    ry0 = min(r[0] for r in rows)
    ry1 = max(r[1] for r in rows)
    # Everything is finally clamped to the card's own rectangle. The page's
    # colour artwork counts as "content", so without this the frame grows a
    # peach border down both sides and across the top - which is exactly how a
    # reviewed card came back with the row above it showing.
    card_rows = np.where(mask.mean(axis=1) >= 0.35)[0]
    cr0, cr1 = (int(card_rows[0]), int(card_rows[-1]) + 1) if len(card_rows) else (0, a.shape[0])
    ry0, ry1 = max(ry0, cr0), min(ry1, cr1)
    sliced = mask[ry0:ry1]
    card_cols = np.where(sliced.mean(axis=0) >= 0.35)[0]
    cx = extent(content[ry0:ry1].mean(axis=0), 0.01)
    if not cx:
        return None
    cc0, cc1 = (int(card_cols[0]), int(card_cols[-1]) + 1) if len(card_cols) else (0, a.shape[1])
    cx = (max(cx[0], cc0), min(cx[1], cc1))
    if cx[1] - cx[0] < 40 or (ry1 - ry0) * (cx[1] - cx[0]) < 0.06 * a.shape[0] * a.shape[1]:
        return None                                  # too little found to trust
    # Sit a little inside the card: its corners are rounded, so a frame exactly
    # on the card's edge collects four small triangles of the page's colour.
    inset = int(max(cx[1] - cx[0], ry1 - ry0) * 0.02)
    return (max(band[0] + cc0, band[0] + cx[0] + inset), max(band[1] + cr0, band[1] + ry0 + inset),
            min(band[0] + cc1, band[0] + cx[1] - inset), min(band[1] + cr1, band[1] + ry1 - inset))


def crop_box(rendered, spans, code, cols, pw):
    """The region this item's photo occupies, in page pixels, or None."""
    bb = find_code(spans, code)
    if not bb:
        return None
    sc = rendered.width / pw                       # page pixels per point
    code_x, code_y = ((bb[0] + bb[2]) / 2) * sc, bb[1] * sc
    colw = rendered.width / cols
    # the column this code sits in, rounded so a code printed off-centre still
    # lands in its own column and the neighbour's product stays out of the crop
    col = min(cols - 1, max(0, int(round(code_x / colw - 0.5))))
    inset = colw * 0.015
    left, right = col * colw + inset, (col + 1) * colw - inset
    if rendered.width < rendered.height:              # portrait page: a card
        box = portrait_box(rendered, spans, left, right, code_y, sc)
        if box:
            return box
    return ink_box(rendered, left, right, code_y, rendered.height)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--debug", action="store_true", help="write a box-check sheet")
    args = ap.parse_args()

    cats = {c["id"]: c for c in G.CATS}
    products = G.load_products()
    index = json.loads((ROOT / "search-index.json").read_text(encoding="utf-8"))
    wanted, per_guide = {}, {}
    for guide in G.GUIDES_DATA:
        rows = G.guide_matches(products, guide, limit=20)
        per_guide[guide["slug"]] = [p["code"] for p in rows]
        for p in rows:
            wanted.setdefault(p["code"], p)
    print("guides:", len(per_guide), " codes referenced:", len(wanted))

    (OUT / "t").mkdir(parents=True, exist_ok=True)
    out_index, debug, done, skipped, missing = {}, [], 0, 0, 0
    for code, p in sorted(wanted.items()):
        big, small = OUT / ("%s.webp" % code), OUT / "t" / ("%s.webp" % code)
        if not args.force and big.exists() and small.exists() and not args.debug:
            out_index[code] = {"c": p["cid"], "p": p["pn"], "n": p["name"]}
            skipped += 1
            continue
        src = PAGES / p["cid"] / ("%d.webp" % p["pn"])
        cat = cats.get(p["cid"])
        if not src.exists() or not cat:
            missing += 1
            continue
        pdf = ROOT / cat["pdf"]
        try:
            rendered = Image.open(src)
            spans, pw, ph = text_spans(pdf, p["pn"])
        except Exception:
            missing += 1
            continue
        cols = 4 if rendered.width > rendered.height else 3
        box = crop_box(rendered, spans, code, cols, pw)
        if not box or box[2] - box[0] < 40 or box[3] - box[1] < 40:
            missing += 1
            print("   no crop:", p["cid"], p["pn"], code, box)
            continue
        # Render the region straight from the PDF: one lossy generation less
        # than cutting it out of the page WebP, and real pixels to downsample.
        sc = rendered.width / pw
        reg = pymupdf.Rect(box[0] / sc, box[1] / sc, box[2] / sc, box[3] / sc)
        z = RENDER_LONG / max(reg.width, reg.height, 0.01)
        doc = pymupdf.open(pdf)
        pix = doc[p["pn"] - 1].get_pixmap(matrix=pymupdf.Matrix(z, z), clip=reg, alpha=False)
        doc.close()
        if pix.width < 40 or pix.height < 40:
            missing += 1
            print("   empty render:", p["cid"], p["pn"], code, reg, pix.width, pix.height)
            continue
        im = pad_frac(trim(Image.frombytes("RGB", (pix.width, pix.height), pix.samples)))
        fit(im, BIG).save(big, "WEBP", quality=82, method=5)
        fit(im, THUMB).save(small, "WEBP", quality=80, method=5)
        out_index[code] = {"c": p["cid"], "p": p["pn"], "n": p["name"]}
        done += 1
        if args.debug and len(debug) < 24:
            tile = rendered.copy()
            ImageDraw.Draw(tile).rectangle(box, outline="red", width=6)
            debug.append(("%s p%d %s" % (p["cid"], p["pn"], code), tile))

    (OUT / "index.json").write_text(
        json.dumps({"codes": out_index, "guides": per_guide}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    total = sum(f.stat().st_size for f in OUT.glob("*.webp"))
    total += sum(f.stat().st_size for f in (OUT / "t").glob("*.webp"))
    print("cut %d, reused %d, no image %d; %d KB on disk"
          % (done, skipped, missing, total // 1024))
    for slug, codes in per_guide.items():
        got = sum(1 for c in codes if c in out_index)
        print("  %-46s %2d/%2d images" % (slug, got, len(codes)))

    if args.debug and debug:
        CW, cols = 380, 4
        tiles = []
        for lab, im in debug:
            h = round(im.height * CW / im.width)
            tiles.append((lab, im.resize((CW, h), Image.LANCZOS)))
        rows = (len(tiles) + cols - 1) // cols
        ch = max(i.height for _, i in tiles) + 18
        sheet = Image.new("RGB", (cols * CW, rows * ch), "white")
        d = ImageDraw.Draw(sheet)
        for k, (lab, im) in enumerate(tiles):
            x, y = (k % cols) * CW, (k // cols) * ch
            d.text((x + 3, y + 3), lab, fill="red")
            sheet.paste(im, (x, y + 16))
        sheet.save(ROOT / "_crop_boxes.png")
        print("debug sheet: %d boxes -> %s" % (len(tiles), ROOT / "_crop_boxes.png"))


if __name__ == "__main__":
    main()
