"""Inspect catalogue PDFs before they enter the pipeline.

Drop the new category PDFs into _incoming/ and run:

    python tools/import_catalogs.py            # report only
    python tools/import_catalogs.py --write    # add them to catalogs.json

It answers the four questions that decide whether a deck can go live unmodified:

  1. Is there a text layer?  A scanned PDF renders fine but is invisible to the
     site search and to the TOC extractor; those must run tools/ocr_text_layer.py
     first (RapidOCR is installed locally).
  2. Landscape or portrait?  Landscape decks are shown one page at a time and
     rendered at 2600 px; portrait pages sit in a two-page spread at 1600 px.
  3. Is the page count and file size sane?  A 200 MB deck is a problem before it
     is rendered, not after.
  4. Does the highest-resolution artwork beat the base width?  If not, the deck
     needs no zoom tier at all (see gen_page_images.py --hi).

The report is deliberately dumb text so it can be pasted into a message.
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import pymupdf
except ImportError:  # older wheels expose the fitz name
    import fitz as pymupdf

ROOT = Path(__file__).resolve().parent.parent
INCOMING = ROOT / "_incoming"
CATALOGS = ROOT / "catalogs.json"

# page widths the generator will use, so the report can say whether a zoom tier
# would have anything to add
BASE_LAND, BASE_PORT = 2600, 1600


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "catalog"


def inspect(path):
    doc = pymupdf.open(path)
    rect = doc[0].rect
    pages = doc.page_count
    land = rect.width >= rect.height * 1.05

    text_chars = 0
    no_text_pages = 0
    best_native = 0
    for page in doc:
        t = page.get_text()
        n = len(t.strip())
        text_chars += n
        if n < 20:
            no_text_pages += 1
        for b in page.get_image_info(xrefs=True):
            placed = b["bbox"][2] - b["bbox"][0]
            if placed <= 1 or b["width"] < 200:
                continue
            if ((b["bbox"][2] - b["bbox"][0]) * (b["bbox"][3] - b["bbox"][1])
                    < 0.04 * rect.width * rect.height):
                continue
            native = b["width"] * rect.width / placed
            best_native = max(best_native, native)

    base_w = BASE_LAND if land else BASE_PORT
    doc.close()
    return {
        "id": slugify(path.stem.replace("catalog-", "")),
        "file": path.name,
        "pages": pages,
        "mb": round(path.stat().st_size / 1048576, 1),
        "pt": "%.0fx%.0f" % (rect.width, rect.height),
        "land": land,
        "text": text_chars,
        "no_text_pages": no_text_pages,
        "native": int(best_native),
        "base_w": base_w,
        "needs_ocr": text_chars < pages * 20,
        "needs_hi": best_native > base_w * 1.05,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="append the inspected decks to catalogs.json")
    ap.add_argument("--dir", default=str(INCOMING))
    args = ap.parse_args()

    src = Path(args.dir)
    pdfs = sorted(src.glob("*.pdf")) if src.exists() else []
    if not pdfs:
        print("No PDFs in %s" % src)
        print("Put the 14 category PDFs there and run this again.")
        return 1

    rows = [inspect(p) for p in pdfs]

    print("%-28s %-14s %4s %7s %10s %7s %9s %s"
          % ("file", "id", "pg", "MB", "size pt", "orient", "text/pg", "verdict"))
    for r in rows:
        verdict = []
        if r["needs_ocr"]:
            verdict.append("OCR first")
        if not r["needs_hi"]:
            verdict.append("no zoom tier needed")
        print("%-28s %-14s %4d %7.1f %10s %7s %9d %s"
              % (r["file"], r["id"], r["pages"], r["mb"], r["pt"],
                 "landscape" if r["land"] else "portrait",
                 r["text"] // max(r["pages"], 1),
                 ", ".join(verdict) or "ok"))

    dup = [r["id"] for r in rows if [x["id"] for x in rows].count(r["id"]) > 1]
    if dup:
        print("\nWARNING: duplicate ids: %s" % ", ".join(sorted(set(dup))))
    total_mb = sum(r["mb"] for r in rows)
    # rough per-page cost of the WebP tiers measured on the current 458 pages:
    # base ~0.10 MB/page, zoom tier ~0.14 MB/page
    print("\n%d PDFs, %.1f MB. Estimated page images: %.0f MB base + %.0f MB zoom tier."
          % (len(rows), total_mb,
             sum(r["pages"] for r in rows) * 0.10,
             sum(r["pages"] for r in rows if r["needs_hi"]) * 0.14))

    if args.write:
        cats = json.loads(CATALOGS.read_text(encoding="utf-8"))
        have = {c["id"] for c in cats}
        added = 0
        for r in rows:
            if r["id"] in have:
                continue
            cats.append({
                "id": r["id"],
                "name": r["id"].replace("-", " ").title(),
                "pdf": "assets/catalog-%s.pdf" % r["id"],
                "toc": None,
                "wide": r["land"],
            })
            added += 1
        CATALOGS.write_text(json.dumps(cats, indent=2), encoding="utf-8")
        print("catalogs.json: %d entries added, %d total" % (added, len(cats)))
        print("Next: move PDFs to assets/catalog-<id>.pdf, then run the pipeline.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
