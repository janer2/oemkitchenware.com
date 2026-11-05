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

### The zoom tier (`--hi`)

    python tools/gen_page_images.py --hi            # incremental
    python tools/gen_page_images.py --hi --force    # re-render the tier

    assets/pages/<id>/hi-<n>.webp — 4000 px (q66) landscape, 2000 px (q66) portrait

One tier cannot serve both views, which is the softness a review caught when
clicking to zoom. The spread is ~1000 CSS px per landscape page, so a 2x click on
a 2x screen asks for 4000 px and the 2600 px base is 1.5x short — the browser can
only smear what it has. The zoom tier is rendered at what that click needs.

It costs nothing on the normal load: `index.html` records only the URL
(`img.dataset.hi`), and fetches a page's hi file as soon as the screen is asking
for more pixels than the base holds — `clientWidth x devicePixelRatio x zoom >
base` — putting the base back below `base x 0.9`. There is deliberately no safety
margin on the up-switch: any margin leaves a band where the base is stretched and
the big file sits idle, so the reader zooms and nothing gets sharper. Measured on
the 2023 deck at 1700 CSS px / DPR 1.302 (base need 2214 px): zoom 1.0 keeps the
base, a 2x click needs 4427 px and fetches `hi-53.webp` once (naturalWidth 2600 →
4000), 2.78x reuses it without refetching, and zooming out to 1.0 swaps back to the
base. A 2x zoom trigger alone would be wrong — the same click is short of pixels
on a 2x desktop and still fine on a 3x phone, whose page is 366 CSS px wide, so the
phone stays on the base until about 2.4x and never pays the 36 MB.

Only the visible page is ever swapped (a wide deck shows one page, so the next
page is not loaded ahead of time) — a 4000 px page decodes to roughly four times
the base page's RAM, so holding two would be wasteful.

**The ceiling is the catalogue, not the renderer.** 2023 prints each product photo
as its own JPEG of 577–794 px at ~200 ppi; rendering the page at 4000 px puts those
crops at 0.76–1.29x of their source pixels, i.e. native. 2026 is a single
1920x1080 bitmap per page (150 ppi), so its hi file is interpolation by definition.
WebP at q66 costs about 2% edge energy versus the raw render, so encoding is not
the limit either; past roughly 2.3x on the 2023 deck the artwork itself runs out.
Replacing the softest photos means sourcing better originals, not re-rendering.

Where the ceiling is: the tier is capped by what the PDF actually contains — the
2026 deck is a 1920x1080 raster per page (150 dpi) and the kitchen product shots
are 240-300 px, so beyond about 2x those photos cannot get sharper, only the
vector text can.

Landscape pages are 1:1 to about 2.6x on a 1x display at the base size, and to
about 4x with the tier; portrait to about 4x on a 1x display. Decoded memory is
the other limit (a 2600 px page is ~15 MB in RAM), which is why the reader keeps
only a small ring of pages warm.

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

## Item photos for the guide pages (`gen_guide_images.py`)

    python tools/gen_guide_images.py            # incremental
    python tools/gen_guide_images.py --force    # re-cut everything

Cuts one product shot per catalogue item for the guide and product pages — 234
codes, ~5.5 MB. A catalogue prints each item's code beside its own photo, so the
code's position in the page's text layer marks where that product sits, and the
code is what every crop is anchored to. Nothing is guessed per page: a page can
hold one row or two, a full grid or a single group card, and the crop follows the
code either way.

Where the picture is, and why it is done differently per page type:

- **Portrait pages** (kitchen, baby, ladies, Christmas) run a white card as
  `[photo][code][name][bullets]`, so an item's photo is the card *above its own
  code*. The ceiling comes from the text layer — just below the previous item's
  last bullet — which is what keeps the row above, and the page heading, out of
  the frame. The white-card mask then says which pixels are the card at all:
  measured 2026-10-12, a card is (255,254,255) while the page's artwork is
  (255,231,201), and because that artwork varies *across* a row a plain
  background test calls the whole column content, which is how earlier crops
  swallowed the row above and the page title.
- **Landscape decks** (2026, 2023) print on white with no card, so the photo is
  told from the type by height: a shot is a 327-416 px dense block against 24-79
  px for a line of text. The crop is the last tall block above the code.

Sharpness: the crop is **rendered from the PDF** at 1400 px on its long side and
then resampled down, instead of being cut out of the already-compressed page WebP
and scaled back up — one whole lossy generation less, and real pixels for the
resampler. The embedded artwork sets the ceiling, measured 2026-10-12: a 2023
cell carries 454-722 px, a 2026 cell about 480 px (its page is a single
1920x1080 raster), and a kitchen cell only 240-300 px. So a portrait crop cannot
be pushed past roughly what it now is, while the landscape ones gained about
twice the detail they used to have at 1100 px.

Writes `assets/guide-images/<CODE>.webp` (640 px long side: hero and hub cards)
and `assets/guide-images/t/<CODE>.webp` (320 px: the item grid), plus
`index.json` (which codes have a photo, and the per-guide shortlist the pages
render). Aspect ratio is preserved everywhere and the pages use
`object-fit: contain`, so no card distorts or slices a product — the first
version squashed the crops into squares and cover-cropped them, which cut
products in half and sliced their printed labels. A code with no photo, and every
page when this script has not been run, renders without pictures rather than
pointing at missing files. `--debug` writes a sheet of the detected boxes to
`_crop_boxes.png` for eyeballing before committing.

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
4. Run `python tools/gen_page_images.py` — the flip reader's page images — then
   `python tools/gen_page_images.py --hi` once per PDF change, for the zoom tier.
5. Run `python tools/gen_guide_images.py` — the item photos the guide and
   product pages show (needs step 4: it crops from the rendered pages).
6. Run `python tools/gen_seo_pages.py` — product pages, guides, merged sitemap.
7. Run `python tools/check_seo_pages.py` and `python tools/check_reader_js.py`,
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
