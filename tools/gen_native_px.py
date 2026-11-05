"""Record, per page, the widest pixel detail the catalogue actually has.

The reader used to let a page be magnified to 4x. A catalogue page is a raster:
2023's cover is one 1920x1080 bitmap for a 20-inch page, its product photos are
577-794 px. Past about 1.3x there is nothing left but interpolation, which is what
"放大之后糊" is. So the zoom is capped at the page's own resolution.

For each page we take the image with the largest printed area (a logo in the
corner says nothing about the page) and ask: if it were the full page width, how
many pixels would that be? That is nativeWidth - the page width beyond which
magnifying adds no detail.

Writes "native": [px per page] into assets/pages/<id>/meta.json and rebuilds
assets/pages/manifest.json. Run after gen_page_images.py.
"""
import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "pages"
CATALOGS = json.loads((ROOT / "catalogs.json").read_text(encoding="utf-8"))
if isinstance(CATALOGS, dict):
    CATALOGS = CATALOGS.get("catalogs") or []

NO_LIMIT = 4000  # a page with no artwork: only vector, so the zoom tier is the limit


def page_native(page):
    """Detail of the artwork that dominates the page.

    Deliberately the image with the largest printed area, not the sharpest one on
    the page: a small crisp thumbnail must not license magnifying the big soft
    photo beside it, because the big one is what the eye judges.
    """
    w = page.rect.width
    page_area = page.rect.width * page.rect.height
    best, best_area = 0.0, 0.0
    for b in page.get_image_info(xrefs=True):
        x0, y0, x1, y1 = b["bbox"]
        placed_w = x1 - x0
        if placed_w <= 1 or b["width"] < 200:
            continue
        area = (x1 - x0) * (y1 - y0)
        # ignore furniture: a logo or a small swatch is not the page's detail
        if area < 0.04 * page_area:
            continue
        if area > best_area:
            best_area = area
            best = b["width"] * w / placed_w
    return int(round(best)) if best else NO_LIMIT


def main():
    manifest = {}
    for cat in CATALOGS:
        d = OUT / cat["id"]
        mpath = d / "meta.json"
        if not mpath.exists():
            continue
        meta = json.loads(mpath.read_text(encoding="utf-8"))
        pdf = ROOT / cat["pdf"]
        if not pdf.exists():
            print("MISSING PDF:", pdf)
            continue
        doc = pymupdf.open(pdf)
        native = [page_native(p) for p in doc]
        doc.close()
        meta["native"] = native
        mpath.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        manifest[cat["id"]] = meta
        lo, hi = min(native), max(native)
        print("%-9s %3d pages  native %5d..%-5d px  (limited on %d pages)"
              % (cat["id"], len(native), lo, hi, sum(1 for n in native if n < NO_LIMIT)))
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print("wrote", OUT / "manifest.json")


if __name__ == "__main__":
    sys.exit(main())
