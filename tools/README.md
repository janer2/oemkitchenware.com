# Yongli Catalog Page Generator

Generates SEO-friendly HTML category pages from the PDF catalogs and their
manual TOC files, plus a full-text search index used by the site's search box.

## What it produces

- `catalog/<catalog-id>/<category-slug>/index.html` — one page per category,
  with cover thumbnails rendered from the PDF, deep links into the 3D flip
  reader, WhatsApp/Email CTAs, and related-category links.
- `catalog/index.html` — hub page listing every category.
- `catalog/<catalog-id>/index.html` — one landing page per catalog (written by
  `cat_hub_html()`); the homepage "Browse all …" links, every section
  breadcrumb and the sitemap point here.
- `search-index.json` — page text of all catalogs (used by site search; the
  site falls back to on-the-fly extraction if this file is missing).
- `sitemap.xml` — rewritten with all generated URLs.

## Usage

    # Python 3 + PyMuPDF (pip install pymupdf)
    python tools/gen_pages.py            # all catalogs, skips unchanged ones
    python tools/gen_pages.py --only kitchen
    python tools/gen_pages.py --force    # rebuild everything regardless

Change detection is based on SHA-1 of each catalog PDF and TOC JSON, recorded
in `catalog/.genmanifest.json`. A catalog is skipped when neither its PDF nor
its TOC changed.

## Buyer guides and product pages (`gen_seo_pages.py`)

A second generator adds the two layers the catalog/category structure cannot
cover. It reads `search-index.json` only — no PDF is re-scanned.

    python tools/gen_seo_pages.py             # 200 product pages + 12 guides
    python tools/gen_seo_pages.py --limit 60  # smaller product batch
    python tools/gen_seo_pages.py --no-sitemap

- `product/<CODE>/index.html` — one page per printed item code (name, range,
  materials, catalog page, related items, Product + BreadcrumbList JSON-LD).
- `guides/<slug>/index.html` — buyer-intent content pages. The topics come from
  the store's own keyword report (top inquiry words, top traffic words,
  advertised main product lines), recorded in `GUIDES_DATA`. They carry FAQPage
  and ItemList JSON-LD, link to the matching product pages, and stay inside this
  site: the independent site deliberately does not link out to any marketplace.
- `guides/index.html`, `product/index.html` — crawlable hubs.
- the "Sourcing guides & full product list" block on the homepage, between the
  `<!-- GUIDES:BEGIN -->` / `<!-- GUIDES:END -->` markers.
- its URLs merged into `sitemap.xml`.

Each page it writes carries `<!-- gen_seo_pages.py -->`, and a run deletes stale
`product/<CODE>/` folders it previously wrote — never a page from `gen_pages.py`.

## The reader's page images (`gen_page_images.py`)

    python tools/gen_page_images.py                # incremental
    python tools/gen_page_images.py --force        # re-render everything
    python tools/gen_page_images.py --only kitchen --quality 84

Writes `assets/pages/<id>/<n>.webp` — **2600 px wide (q76) for a landscape deck,
 1600 px (q80) for a portrait page** — 458 pages / ~47 MB for the current six
catalogues, plus `assets/pages/<id>/meta.json` and the single
`assets/pages/manifest.json` the reader fetches.

The two widths follow what the page is displayed at. A landscape deck is shown
one page at a time at ~1000 CSS px, so a Retina screen wants ~2000 px of source
before anything is zoomed, and the reader zooms to 4x; a portrait page sits in a
two-page spread at ~350-500 CSS px. WebP at these sizes costs about what the old
1100 px JPEG cost, which is what makes the extra pixels affordable — the first
version rendered 1100 px JPEG and read as soft on a wide screen.

One source per page is a deliberate trade: a set that stays sharp at 4x would be
roughly ten times the bytes. Landscape pages are 1:1 up to about 2.6x zoom,
portrait up to about 4x on a 1x display. Decoded memory is the other limit (a
2600 px page is ~15 MB in RAM), which is why the reader keeps only a small ring
of pages warm.

`index.html` opens a catalogue from those images: two or three small requests
per spread instead of one 17-21 MB PDF, and pdf.js is not loaded in that mode.
The manifest carries the page count, the PDF page box (so the flip geometry and
the landscape/portrait decision stay identical) and a contents list, which is
why the sidebar still works for the 2026 deck that has no `toc-<id>.json`.
A catalogue with no image set still falls back to the PDF path, so the reader
cannot be broken by a missing render. Re-runs skip pages newer than the PDF.

Do not "fix" the reader by putting a `PDFDataRangeTransport` back: pdf.js
3.11.174 only forwards `disableRange`/`disableStream` to a custom transport, so
one open becomes 120-150 serialised requests and the reader never finishes.

## Verifying the generated pages

    python tools/check_seo_pages.py

Walks the homepage, every `catalog/**`, `product/**` and `guides/**` page and
reports titles over 65 chars, descriptions over 160, missing/duplicate `<h1>`,
missing canonical, invalid JSON-LD, any internal link whose target file does not
exist, plus sitemap URLs with no page behind them and generated pages missing
from the sitemap. Run it before every push.

## After you update a PDF

1. Replace the PDF file(s) under `assets/` (keep the same filename) and/or
   edit `toc-*.json` (page numbers / category titles).
2. Run `python tools/gen_pages.py` — regenerates category pages, hubs, the
   homepage index block, the search index and `sitemap.xml`.
3. Run `python tools/gen_covers.py` — card covers, 400 px thumbs, reader stills.
4. Run `python tools/gen_page_images.py` — the flip reader's page images.
5. Run `python tools/gen_seo_pages.py` — product pages, guides, merged sitemap.
6. Run `python tools/check_seo_pages.py` and `python tools/check_reader_js.py`,
   then review `git status`, commit and push — GitHub Pages serves the update.

`gen_pages.py` rewrites `sitemap.xml` from scratch, so always run
`gen_seo_pages.py` after it, never before.

## Keeping handwritten copy

Each generated category page supports a manual block:

```html
<section id="custom"> ...your own content... </section>
```

The generator detects this block in an existing page and carries it over on
rebuild. Everything else on the page is regenerated from the template, so put
hand-edited marketing copy inside the `#custom` section only.

## Input mapping

| Catalog id | PDF | TOC |
|---|---|---|
| kitchen | assets/catalog-kitchen.pdf | toc-kitchen.json |
| baby | assets/catalog-baby.pdf | toc-baby.json |
| ladies | assets/catalog-ladies.pdf | toc-ladies.json |
| balls | assets/catalog-balls.pdf | (none — whole book as one category) |
