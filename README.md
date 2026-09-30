# oemkitchenware.com

Marketing site for **Huizhou Yongli Industrial Co., Ltd.** — a BSCI & ISO 9001
certified OEM/ODM manufacturer of food-grade silicone kitchenware, baby care,
personal care and festive decorations (Huizhou, China, since 2010).

Static site, served by GitHub Pages from `main`. No build step and no server:
`index.html` holds the whole front end (CSS + JS inline).

## What is on the site

| Piece | Where |
|---|---|
| Homepage (cards, category grid, catalogue index, contact drawer) | `index.html` |
| Flip-book PDF reader | `index.html` (pdf.js + StPageFlip, vendored in `assets/pdfjs/`) |
| 5 catalogues | `assets/catalog-*.pdf` |
| 31 category landing pages (SEO) | `catalog/<catalog>/<section>/index.html` |
| Site search index | `search-index.json` |
| Cover images | `assets/covers/<id>.jpg` |
| 404 fallback | `404.html` |

## The one file to edit

`catalogs.json` is the **single source of truth**: the homepage, the cover
renderer, the category grid and the generator all read it. Adding a catalogue
means adding one object there — with `toc: null` for a catalogue whose outline
should *not* be cut into category pages (that is what `gridFromToc: false` +
`toc: null` do for `2026 New`, which would otherwise spawn 14 near-duplicate
pages).

```json
{ "id": "kitchen", "name": "Kitchen Gadgets", "sub": "Kitchen Items",
  "pdf": "assets/catalog-kitchen.pdf", "toc": "toc-kitchen.json",
  "theme": "...", "materials": "..." }
```

## Regenerating after a PDF changes

```bash
python tools/gen_pages.py --force --report   # category pages, hub, sitemap, search index
python tools/gen_covers.py                   # static cover JPGs
```

- `--force` is required when only the generator changed: the search-index cache
  key is the PDF hash, so a code-only change would otherwise be skipped.
- `--report` writes `catalog/item-review.md`, which shows how many product codes
  and names failed to pair — check it after a PDF swap instead of trusting it.
- `gen_pages.py` also rewrites the `<!-- INDEX:BEGIN -->…<!-- INDEX:END -->`
  block in `index.html` (the plain-HTML catalogue index crawlers read).

A **scanned/image-only PDF has no text layer**, so search, the TOC and the
category pages find nothing. Run `tools/ocr_text_layer.py` first (RapidOCR is
installed locally) to add an invisible text layer.

New or renamed logo art goes through `tools/trim_logo.py`: `assets/logo.png` is
a 1200×1200 square whose wordmark fills only the middle third, so the header uses
the trimmed `assets/logo-mark.png` instead.

`tools/gen_toc.py` proposes a table of contents from the font sizes on each page
and writes `<toc>.proposed.json` + a review sheet — it never overwrites the
checked-in outlines.

## Local preview

```bash
python -m http.server 8080 --directory .
```

`start-server.bat` / `start-server-hidden.vbs` do the same through a Windows
scheduled task; they are intentionally **not tracked** (see `.gitignore`).

## Reader architecture notes

- PDFs are fetched page by page over HTTP Range requests (`disableAutoFetch`),
  so opening a catalogue never downloads the whole file.
- Render scale is screen width × 1.15, capped at the source image width, and the
  read-ahead window adapts to how expensive a page is to rasterise (2/4/8 pages).
- The code/name pairing that powers product search depends on the **layout**: the
  landscape deck prints the code *below* the product name, the portrait ones
  *above* it, and long names wrap. `page_items()` therefore walks each column in
  both directions and glues wrapped lines back together.
