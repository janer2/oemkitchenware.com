#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yongli category-page generator.

Reads assets/catalog-*.pdf + toc-*.json and emits static, SEO-friendly
category pages under catalog/<catalog-id>/<category-slug>/ plus a hub index
catalog/index.html and a rewritten sitemap.xml.

Usage:
    python tools/gen_pages.py            # all catalogs
    python tools/gen_pages.py --only kitchen
    python tools/gen_pages.py --force    # rebuild even if unchanged

Change detection: sha1 of each catalog's pdf + toc is stored in
catalog/.genmanifest.json; unchanged catalogs are skipped (unless --force).
Note: generated pages are rebuilt from templates. Manually edit category
HTML only if you accept it being overwritten on the next changed rebuild,
or keep edits inside the <section id="custom"> block which the template
carries over.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "catalog"
MANIFEST = OUT / ".genmanifest.json"
SITEMAP = ROOT / "sitemap.xml"
LOGO = "/assets/logo.png"
SITE = "https://oemkitchenware.com"
BRAND_LINE = ("BSCI & ISO 9001 certified OEM/ODM manufacturer since 2010. "
              "Serving customers in 34 countries with one-stop OEM, packaging, "
              "design and logistics. Vision: Make Globe Trade Easy.")

CATS = [
    {"id": "kitchen", "pdf": "assets/catalog-kitchen.pdf", "toc": "toc-kitchen.json",
     "name": "Kitchen Gadgets", "sub": "Kitchen Items",
     "theme": "silicone and stainless steel kitchenware",
     "materials": "Food-grade silicone, stainless steel, BPA-free plastic"},
    {"id": "baby", "pdf": "assets/catalog-baby.pdf", "toc": "toc-baby.json",
     "name": "Baby Care", "sub": "Infant & Nursery Products",
     "theme": "food-grade silicone baby care products",
     "materials": "Food-grade silicone, BPA-free materials, EN71 & FDA compliant"},
    {"id": "ladies", "pdf": "assets/catalog-ladies.pdf", "toc": "toc-ladies.json",
     "name": "Ladies' Appliances", "sub": "Personal Care & Beauty Devices",
     "theme": "personal care and beauty devices",
     "materials": "Safe, body-friendly materials with CE/RoHS compliant electronics"},
    {"id": "balls", "pdf": "assets/catalog-balls.pdf", "toc": None,
     "name": "Christmas Balls", "sub": "Festival Decorations",
     "theme": "festive Christmas and holiday decorations",
     "materials": "High-quality festive finishes, drop-safe decoration materials"},
]

# Sitemap entries the generator owns (rewritten each run)
SITEMAP_STATIC = [
    ("https://oemkitchenware.com/", "weekly", "1.0"),
    ("https://oemkitchenware.com/catalog/", "weekly", "0.9"),
]

TEMPLATE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; color: #222; background: #fff; line-height: 1.6; }
a { color: #1a1a2e; }
.topbar { display: flex; align-items: center; gap: 18px; padding: 12px 24px; border-bottom: 1px solid #eee; position: sticky; top: 0; background: #fff; z-index: 10; }
.topbar .logo img { height: 30px; width: auto; display: block; }
.topbar nav { margin-left: auto; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.topbar nav a { text-decoration: none; color: #444; font-size: .88rem; font-weight: 500; padding: 8px 14px; border-radius: 6px; }
.topbar nav a:hover { color: #1a1a2e; background: #f5f5f5; }
.topbar nav a.wa { color: #1a1a2e; border: 1px solid #25d366; }
.wrap { max-width: 980px; margin: 0 auto; padding: 26px 20px 60px; }
.crumbs { font-size: .8rem; color: #999; margin-bottom: 14px; }
.crumbs a { color: #1a1a2e; text-decoration: none; }
.crumbs a:hover { text-decoration: underline; }
h1 { font-size: 1.9rem; color: #1a1a2e; margin: 4px 0 10px; }
.lede { color: #555; max-width: 760px; margin-bottom: 24px; }
.cta-row { display: flex; flex-wrap: wrap; gap: 10px; margin: 8px 0 28px; }
.cta { display: inline-flex; align-items: center; gap: 8px; padding: 12px 22px; border-radius: 30px; text-decoration: none; font-size: .92rem; font-weight: 600; transition: background .2s, transform .2s; }
.cta.primary { background: #1a1a2e; color: #fff; }
.cta.primary:hover { background: #2b2b4a; transform: translateY(-1px); }
.cta.whatsapp { background: #25d366; color: #fff; }
.cta.whatsapp:hover { filter: brightness(.95); transform: translateY(-1px); }
.thumbs { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin: 10px 0 30px; }
.thumbs figure { border: 1px solid #eee; border-radius: 12px; overflow: hidden; background: #faf9f7; }
.thumbs img { width: 100%; height: auto; display: block; }
.thumbs figcaption { padding: 8px 12px; font-size: .76rem; color: #999; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }
section.block { margin-bottom: 30px; }
section.block h2 { font-size: 1.15rem; color: #1a1a2e; margin-bottom: 10px; border-bottom: 2px solid #e8a840; display: inline-block; padding-bottom: 4px; }
ul.ticks { list-style: none; }
ul.ticks li { padding: 5px 0 5px 26px; position: relative; color: #444; font-size: .9rem; }
ul.ticks li::before { content: ''; position: absolute; left: 2px; top: 11px; width: 9px; height: 9px; border-radius: 50%; background: #e8a840; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.chip { border: 1px solid #ddd; border-radius: 20px; padding: 5px 14px; font-size: .78rem; color: #444; }
.siblings { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.sibling { border: 1px solid #ddd; border-radius: 20px; padding: 6px 14px; font-size: .82rem; text-decoration: none; color: #1a1a2e; background: #fff; }
.sibling:hover { border-color: #1a1a2e; }
.foot { border-top: 1px solid #eee; text-align: center; padding: 26px 16px; color: #aaa; font-size: .78rem; }
@media (max-width: 768px) {
  .topbar { padding: 10px 14px; gap: 10px; }
  .topbar nav a { padding: 6px 10px; font-size: .82rem; }
  .wrap { padding: 18px 14px 44px; }
  h1 { font-size: 1.5rem; }
  .grid2 { grid-template-columns: 1fr; gap: 20px; }
  .thumbs { grid-template-columns: 1fr; }
}
"""


def sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slugify(s: str) -> str:
    s = s.lower().replace("&", " and ").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "page"


def flatten_toc(entries, path=()):
    """Yield leaf categories with their breadcrumb path (list of titles)."""
    for e in entries:
        title = e.get("title", "")
        page = int(e.get("page", 1))
        children = e.get("children") or []
        cur = path + (title,)
        if children:
            yield from flatten_toc(children, cur)
        else:
            yield {"title": title, "page": page, "path": cur}


def build_categories(cat):
    if cat["toc"]:
        raw = json.loads((ROOT / cat["toc"]).read_text(encoding="utf-8"))
        leaves = list(flatten_toc(raw))
    else:
        leaves = [{"title": cat["name"], "page": 1, "path": (cat["name"],)}]
    # de-duplicate leaves sharing the same start page (nested duplicates)
    seen = {}
    for lf in leaves:
        seen.setdefault(lf["page"], lf)
    leaves = [seen[k] for k in sorted(seen)]
    # compute page ranges
    for i, lf in enumerate(leaves):
        nxt = leaves[i + 1]["page"] if i + 1 < len(leaves) else None
        lf["end"] = (nxt - 1) if nxt else None  # pdf page count patched later
    return leaves


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def page_text(doc, start, end, limit=420):
    """Best-effort plain text of the category's first pages."""
    try:
        parts = []
        for pno in range(start, min(start + 3, end + 1)):
            txt = doc[pno - 1].get_text("text") or ""
            for ln in txt.splitlines():
                s = ln.strip()
                if s and len(s) > 2:
                    parts.append(s)
        joined = " ".join(parts)
        joined = re.sub(r"\s+", " ", joined).strip()
        return joined[:limit].rstrip(",; ") + ("..." if len(joined) > limit else "")
    except Exception:
        return ""


def render_thumb(doc, pno, dest: Path, width=760, quality=74):
    page = doc[pno - 1]
    rect = page.rect
    zoom = width / max(rect.width, 1)
    pix = page.get_pixmap(matrix=__import__("pymupdf").Matrix(zoom, zoom),
                          alpha=False)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(pix.tobytes("jpeg", jpg_quality=quality))
    return rect.width, rect.height


def page_html(cat, cat_dir, lf, cat_cover, cat_last, num_pages, doc, all_links):
    cid, cname = cat["id"], cat["name"]
    slug = slugify(lf["title"])
    url = f"{SITE}/catalog/{cid}/{slug}/"
    title = lf["title"]
    path = lf["path"]
    pg = lf["page"]
    end = lf.get("end") or num_pages
    n_pages = end - pg + 1
    desc = (f"{title} wholesale from Yongli — BSCI & ISO 9001 certified OEM/ODM "
            f"manufacturer of {cat['theme']} since 2010. "
            f"Full range of {n_pages} catalog pages, custom OEM/ODM welcome.")
    text = page_text(doc, pg, end)
    crumbs = ["<a href='/'>Home</a>", "<a href='/catalog/'>Categories</a>"]
    if len(path) > 1:
        crumbs.append(f"<a href='/catalog/{cid}/'>{esc(cname)}</a>")
    crumbs.append(f"<span>{esc(title)}</span>")
    thumbs = ""
    if cat_cover:
        cap = f"{esc(title)} — cover (PDF page {pg})"
        thumbs += f"<figure><img src='cover.jpg' alt='{esc(title)} — {esc(cname)}' loading='lazy'><figcaption>{cap}</figcaption></figure>"
    if cat_last and pg != end and end > pg:
        thumbs += (f"<figure><img src='last.jpg' alt='{esc(title)} range sample (page {end})' "
                   f"loading='lazy'><figcaption>Range sample — PDF page {end}</figcaption></figure>")
    siblings = ""
    if all_links:
        sib = [f"<a class='sibling' href='{SITE}/catalog/{cid}/{slugify(o['title'])}/'>{esc(o['title'])}</a>"
               for o in all_links if o["page"] != pg]
        if sib:
            siblings = f"<div class='siblings'>{''.join(sib)}</div>"
    cust = ""
    seg = Path(cat_dir) / slug / "index.html"
    if seg.exists():
        m = re.search(r"<section id=\"custom\">(.*?)</section>", seg.read_text(encoding="utf-8"), re.S)
        if m:
            cust = m.group(0)
    ld = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": nm,
                             "item": SITE + (u if u.startswith("/") else "/" + u)}
                            for i, (nm, u) in enumerate(
            [("Home", "/"), ("Categories", "/catalog/"), (cname, f"/catalog/{cid}/"),
             (title, f"/catalog/{cid}/{slug}/")])],
    }
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} — Wholesale {esc(cname)} Manufacturer | Yongli</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Yongli Kitchenware">
<meta property="og:title" content="{esc(title)} — Yongli {esc(cname)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{url}cover.jpg">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False)}
</script>
<style>{TEMPLATE_CSS}</style>
</head>
<body>
<header class="topbar">
  <a class="logo" href="/"><img src="/assets/logo.png" alt="Yongli — silicone kitchenware manufacturer"></a>
  <nav>
    <a href="/">3D Catalog</a>
    <a href="/#viewCustomize">Customize</a>
    <a href="/#viewAbout">About Us</a>
    <a class="wa" href="https://wa.me/8613824296558" target="_blank" rel="noopener">WhatsApp</a>
  </nav>
</header>
<main class="wrap">
  <nav class="crumbs" aria-label="Breadcrumb">{''.join(crumbs)}</nav>
  <h1>{esc(title)} — {esc(cname)}</h1>
  <p class="lede">{esc(desc)}</p>
  <div class="cta-row">
    <a class="cta primary" href="/?catalog={cid}&page={pg}">Open in 3D Flip Catalog ({n_pages} pages) &rarr;</a>
    <a class="cta whatsapp" href="https://wa.me/8613824296558?text={esc('Hi, I am interested in ' + title + '. Please send me details.')}" target="_blank" rel="noopener">WhatsApp Us</a>
    <a class="cta primary" href="mailto:info@yonglicc.com?subject={esc('Wholesale inquiry - ' + title)}">Email a Quote Request</a>
  </div>
  <div class="thumbs">{thumbs}</div>
  <div class="grid2">
    <section class="block">
      <h2>About This Range</h2>
      <ul class="ticks">
        <li>Range: {n_pages} catalog pages starting at PDF page {pg}</li>
        <li>Materials: {esc(cat['materials'])}</li>
        <li>OEM &amp; ODM: custom mold design, Pantone color matching, custom packaging and logo printing</li>
        <li>Exported to 34 countries across Europe, America, Middle East and beyond</li>
        <li>In-house R&amp;D, tooling and mass production since 2010</li>
      </ul>
    </section>
    <section class="block">
      <h2>Quality &amp; Compliance</h2>
      <div class="chips"><span class="chip">BSCI</span><span class="chip">ISO 9001</span><span class="chip">FDA</span><span class="chip">LFGB</span><span class="chip">EN71</span><span class="chip">REACH</span><span class="chip">RoHS</span></div>
      <p style="font-size:.88rem;color:#666;margin-top:12px">{BRAND_LINE}</p>
    </section>
  </div>
  {cust}
  <section class="block">
    <h2>Related Categories</h2>
    {siblings}
  </section>
</main>
<footer class="foot">&copy; 2026 Huizhou Yongli Industrial Co., Ltd. All rights reserved. <a href="/">Back to 3D catalog</a></footer>
</body>
</html>
"""
    return html


def hub_html(cats_built):
    parts = []
    for cat, cats in cats_built:
        cid = cat["id"]
        lis = "".join(
            f"<a class='sibling' href='/catalog/{cid}/{slugify(c['title'])}/'>{esc(c['title'])}</a>"
            for c in cats)
        parts.append(
            f"<section class='block'><h2>{esc(cat['name'])}</h2>"
            f"<p style='color:#666;font-size:.9rem;margin-bottom:10px'>{esc(cat['sub'])} — "
            f"<a href='/?catalog={cid}'>open in 3D flip catalog</a></p>"
            f"<div class='siblings'>{lis}</div></section>")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Product Categories — Yongli OEM Kitchenware, Baby, Personal Care &amp; Gifts</title>
<meta name="description" content="All Yongli product categories in one index — kitchen gadgets, baby care, personal care appliances and Christmas decorations. Click any category for details and wholesale inquiry.">
<link rel="canonical" href="{SITE}/catalog/">
<style>{TEMPLATE_CSS}</style>
</head>
<body>
<header class="topbar">
  <a class="logo" href="/"><img src="/assets/logo.png" alt="Yongli — silicone kitchenware manufacturer"></a>
  <nav><a href="/">3D Catalog</a><a href="/#viewCustomize">Customize</a><a href="/#viewAbout">About Us</a>
    <a class="wa" href="https://wa.me/8613824296558" target="_blank" rel="noopener">WhatsApp</a></nav>
</header>
<main class="wrap">
  <nav class="crumbs"><a href="/">Home</a> <span>&rarr; Categories</span></nav>
  <h1>Product Categories</h1>
  <p class="lede">{esc(BRAND_LINE)}</p>
  {''.join(parts)}
</main>
<footer class="foot">&copy; 2026 Huizhou Yongli Industrial Co., Ltd. <a href="/">Back to 3D catalog</a></footer>
</body>
</html>
"""
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="catalog id to build")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf

    manifest = {}
    if MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    out_pages = []
    cats_built = []
    for cat in CATS:
        if args.only and cat["id"] != args.only:
            continue
        pdf = ROOT / cat["pdf"]
        if not pdf.exists():
            print("skip (pdf missing):", cat["id"])
            continue
        toc_path = ROOT / cat["toc"] if cat["toc"] else None
        h_pdf = sha1_file(pdf)
        h_toc = sha1_file(toc_path) if toc_path else "none"
        rec = manifest.get(cat["id"])
        if rec and rec.get("pdf") == h_pdf and rec.get("toc") == h_toc and not args.force:
            print("unchanged, skip:", cat["id"])
            cats_built.append((cat, rec.get("cats", [])))
            out_pages.extend(rec.get("pages", []))
            continue

        leaves = build_categories(cat)
        doc = pymupdf.open(str(pdf))
        n = doc.page_count
        for lf in leaves:
            if lf.get("end") is None:
                lf["end"] = n
            lf["end"] = min(lf["end"], n)
        cat_dir = OUT / cat["id"]
        cat_pages = []
        for lf in leaves:
            slug = slugify(lf["title"])
            d = cat_dir / slug
            d.mkdir(parents=True, exist_ok=True)
            render_thumb(doc, lf["page"], d / "cover.jpg")
            has_last = lf["end"] > lf["page"]
            if has_last:
                render_thumb(doc, lf["end"], d / "last.jpg")
            url = f"{SITE}/catalog/{cat['id']}/{slug}/"
            out_pages.append((url, "monthly", "0.7"))
            cat_pages.append({"title": lf["title"], "page": lf["page"]})
            html = page_html(cat, cat_dir, lf, True, has_last, n, doc, leaves)
            (d / "index.html").write_text(html, encoding="utf-8")
            print("built:", cat["id"], "/", slug, f"(pages {lf['page']}-{lf['end']})")
        doc.close()
        manifest[cat["id"]] = {"pdf": h_pdf, "toc": h_toc, "cats": cat_pages,
                               "pages": out_pages[-len(cat_pages):]}
        cats_built.append((cat, cat_pages))
        out_pages.extend([(f"{SITE}/catalog/{cat['id']}/", "weekly", "0.8")])

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(hub_html(cats_built), encoding="utf-8")
    print("hub written: catalog/index.html")

    urls = []
    for u, cf, pr in SITEMAP_STATIC:
        urls.append((u, cf, pr))
    for cat in CATS:
        if args.only and cat["id"] != args.only:
            continue
        if args.only or cat["id"] in manifest:
            if not args.only:
                urls.append((f"{SITE}/catalog/{cat['id']}/", "weekly", "0.8"))
    urls.extend(out_pages)
    seen = set()
    xml_body = []
    for u, cf, pr in urls:
        if u in seen:
            continue
        seen.add(u)
        xml_body.append(f"  <url>\n    <loc>{u}</loc>\n    <changefreq>{cf}</changefreq>\n    <priority>{pr}</priority>\n  </url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(xml_body) + "\n</urlset>\n")
    SITEMAP.write_text(xml, encoding="utf-8")
    print("sitemap.xml updated with", len(seen), "urls")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print("manifest written")


if __name__ == "__main__":
    main()
