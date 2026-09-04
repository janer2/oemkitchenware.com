# Yongli Catalog Page Generator

Generates SEO-friendly HTML category pages from the PDF catalogs and their
manual TOC files, plus a full-text search index used by the site's search box.

## What it produces

- `catalog/<catalog-id>/<category-slug>/index.html` — one page per category,
  with cover thumbnails rendered from the PDF, deep links into the 3D flip
  reader, WhatsApp/Email CTAs, and related-category links.
- `catalog/index.html` — hub page listing every category.
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

## After you update a PDF

1. Replace the PDF file(s) under `assets/` (keep the same filename) and/or
   edit `toc-*.json` (page numbers / category titles).
2. Run `python tools/gen_pages.py`.
3. Review `git status`, commit and push — GitHub Pages serves the update.

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
