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

# catalogs.json is the single source of truth: it feeds the homepage, the cover
# renderer, the category grid and this generator. It used to be duplicated as a
# literal here, and adding a catalog meant editing both lists (forget one and the
# build silently lost it), so CATS is derived from the JSON instead.
CATALOGS_FILE = ROOT / "catalogs.json"


def load_catalogs():
    raw = json.loads(CATALOGS_FILE.read_text(encoding="utf-8"))
    out = []
    for c in raw:
        if not c.get("id") or not c.get("pdf"):
            raise SystemExit("catalogs.json entry needs an id and a pdf: %r" % (c,))
        out.append({
            "id": c["id"],
            "pdf": c["pdf"],
            # toc = outline used to cut this PDF into category pages; catalogs
            # whose outline should not spawn near-duplicate pages keep it null
            "toc": c.get("toc") or None,
            "name": c.get("name") or c["id"],
            "sub": c.get("sub") or "",
            "gridFromToc": c.get("gridFromToc", True),
            "theme": c.get("theme") or c.get("name") or c["id"],
            "materials": c.get("materials") or "Food-grade materials",
        })
    return out


CATS = load_catalogs()

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


CODE_RE = re.compile(r"^[A-Z]{1,5}-?\d{2,7}$")
# A name is only believable if it reads like a product, not like a spec line or
# a stray OCR fragment from the neighbouring column.
SPEC_RE = re.compile(
    r"^(material|size|weight|color|colour|capacity|packing|qty|logo|moq|height|"
    r"width|length|depth|thickness|dia|diameter|bottom|base|top)\b", re.I)
MEASURE_RE = re.compile(r"^[\d\s.,:x*×/\-]+(mm|cm|g|kg|ml|l|oz|pcs)?$", re.I)
LINE_GAP = 22      # lines closer than this belong to the same product cell
COL_TOL = 90       # half-width of one product column
RUN_LIMIT = 170    # how far a name may sit from its code


def is_product_name(text):
    t = text.strip()
    if len(t) < 8 or " " not in t:
        return False
    if SPEC_RE.match(t) or MEASURE_RE.match(t):
        return False
    if sum(ch.isalpha() for ch in t) < 6:
        return False
    # "1200ml:200x164 mm, 490g" is a spec block, not a name
    if sum(ch.isdigit() for ch in t) / float(len(t)) > 0.25:
        return False
    return len(t.split()) >= 2


def page_lines(doc, pno):
    """Every text line of a page as (text, x0, y0, x1, y1), sorted top-to-bottom."""
    try:
        data = doc[pno].get_text("dict")
    except Exception:
        return []
    lines = []
    for blk in data.get("blocks", []):
        for ln in blk.get("lines", []):
            txt = "".join(sp.get("text", "") for sp in ln.get("spans", [])).strip()
            if txt:
                x0, y0, x1, y1 = ln["bbox"]
                lines.append((txt, x0, y0, x1, y1))
    lines.sort(key=lambda t: (t[2], t[1]))
    return lines


def page_items(doc, pno, max_items=60):
    """Pair every product code on a page with its product name.

    The decks lay their cells out differently: the landscape catalogs print the
    code on the line under the name, the portrait ones print it on the line
    above, and long names wrap onto a second line. So instead of only looking
    above the code we walk the column both ways, glue wrapped lines back
    together and keep the run that actually reads like a product.
    """
    lines = page_lines(doc, pno)
    if not lines:
        return []

    def is_code(txt):
        return bool(CODE_RE.match(txt.upper().replace(" ", "")))

    def is_spec(txt):
        return bool(SPEC_RE.match(txt) or MEASURE_RE.match(txt))

    def run_against(anchor, direction):
        """Lines stacked against `anchor`, going up (-1) or down (1).

        Returns (text in reading order, distance to the nearest line). Stops at
        a code or spec line so a run never swallows the neighbouring product.
        """
        cx = (anchor[1] + anchor[3]) / 2.0
        col = [s for s in lines
               if s is not anchor and abs((s[1] + s[3]) / 2.0 - cx) <= COL_TOL]
        top, bottom, out, gap = anchor[2], anchor[4], [], None
        while len(out) < 3:
            if direction < 0:
                cand = [s for s in col if -3 <= top - s[4] <= LINE_GAP]
                nxt = max(cand, key=lambda s: s[4]) if cand else None
            else:
                cand = [s for s in col if -3 <= s[2] - bottom <= LINE_GAP]
                nxt = min(cand, key=lambda s: s[2]) if cand else None
            if nxt is None:
                break
            txt = nxt[0].strip()
            # a name may start with a digit ("8-Piece Kitchen Utensil Set"),
            # a measurement may not be mostly digits ("165 x 55 mm", "111")
            if is_code(txt) or is_spec(txt):
                break
            if sum(ch.isdigit() for ch in txt) > len(txt) * 0.5:
                break
            if gap is None:
                edge = nxt[4] if direction < 0 else nxt[2]
                gap = abs(edge - (anchor[2] if direction < 0 else anchor[4]))
            out.append(txt)
            top, bottom = min(top, nxt[2]), max(bottom, nxt[4])
            if len(" ".join(out)) > 70:
                break
        text = " ".join(reversed(out)) if direction < 0 else " ".join(out)
        return text, (gap if gap is not None else 1e9)

    def partner(anchor, limit=RUN_LIMIT):
        """The product name belonging to `anchor`, whichever side it sits on."""
        best, best_gap = "", 1e9
        for direction in (-1, 1):
            text, gap = run_against(anchor, direction)
            if gap > limit or not is_product_name(text):
                continue
            if gap < best_gap:
                best, best_gap = text, gap
        return best

    items, seen = [], set()
    for code in [s for s in lines if is_code(s[0])][:max_items]:
        nm = partner(code)
        items.append([nm, code[0].upper().replace(" ", "")])
        if nm:
            seen.add(nm.lower())
    # Catalogs whose products carry no printed code are still worth an entry:
    # the name sits directly above its "Material:/Size:" block.
    for sp in lines[:max_items * 3]:
        if not is_spec(sp[0].strip()):
            continue
        nm = partner(sp)
        if nm and nm.lower() not in seen:
            seen.add(nm.lower())
            items.append([nm, ""])
    return items[:max_items]


def item_audit(doc, pno):
    """What the pairing could *not* resolve on a page, for the review report.

    The rules above are tuned heuristics (code shapes, spec words, line gaps), so
    every catalog change can quietly shift what pairs with what. Rather than
    re-inventing a probe each time, the generator can print the leftovers.
    """
    lines = page_lines(doc, pno)
    if not lines:
        return None
    items = page_items(doc, pno)
    paired_codes = set(it[1] for it in items if it[1])
    codes = [s[0].upper().replace(" ", "") for s in lines
             if CODE_RE.match(s[0].upper().replace(" ", ""))]
    names = [it[0] for it in items if it[0]]
    return {
        "codes": len(codes),
        "codes_unpaired": [c for c in codes if c not in paired_codes],
        "named": len(names),
        "unnamed": len([it for it in items if not it[1]]),
    }


def write_home_index(cats_built):
    """Rewrite the crawlable catalogue index inside index.html.

    The homepage cards are drawn by JavaScript, so a crawler that does not execute
    scripts sees almost no text on the most important URL of the site. This block
    is plain HTML - every catalog, every section, every section landing page.
    """
    cols = []
    for cat, cat_pages in cats_built:
        links = "".join(
            '<li><a href="/catalog/%s/%s/">%s</a><span>p.%d</span></li>'
            % (cat["id"], slugify(p["title"]), esc(p["title"]), int(p["page"]))
            for p in cat_pages)
        cols.append('<div class="hi-col"><h3>%s</h3><p class="hi-sub">%s</p><ul>%s</ul>'
                    '<a class="hi-all" href="/catalog/%s/">Browse all %s &rarr;</a></div>'
                    % (esc(cat["name"]), esc(cat["sub"]), links, cat["id"], esc(cat["name"])))
    block = ("<!-- INDEX:BEGIN -->\n"
             '<div class="home-index">\n'
             "<h2>Full catalogue index</h2>\n"
             '<p class="hi-lede">Every section of every catalogue, listed as printed in the '
             "PDFs. Open the flip-book reader or jump straight to a section page - each one "
             "lists the products, codes and materials for that range.</p>\n"
             '<div class="hi-grid">%s</div>\n'
             "</div>\n"
             "<!-- INDEX:END -->" % "".join(cols))
    path = ROOT / "index.html"
    html = path.read_text(encoding="utf-8")
    if "<!-- INDEX:BEGIN -->" not in html:
        print("home index markers missing in index.html - skipped")
        return
    path.write_text(re.sub(r"<!-- INDEX:BEGIN -->.*?<!-- INDEX:END -->", block, html, flags=re.S),
                    encoding="utf-8")
    print("home index block rewritten:", sum(len(p) for _, p in cats_built), "section links")


def write_item_report(rows):
    """catalog/item-review.md — a short human-checkable list per catalog."""
    out = ["# Search-index pairing review",
           "",
           "Generated by `python tools/gen_pages.py --report`. Use it to spot-check the",
           "heuristics in `page_items()` after a catalog changes: anything listed under",
           "*unpaired codes* or *unnamed rows* is a product the search index may show",
           "without a code (or miss entirely).",
           ""]
    for cid, name, stats, samples in rows:
        out.append("## %s (%s)" % (name, cid))
        out.append("")
        out.append("- pages with products: **%d**" % stats["pages"])
        out.append("- codes found: **%d**, paired with a name: **%d** (%.1f%%)"
                   % (stats["codes"], stats["codes"] - stats["unpaired"],
                      100.0 * (stats["codes"] - stats["unpaired"]) / max(1, stats["codes"])))
        out.append("- rows without a code: **%d**" % stats["unnamed"])
        if samples:
            out.append("")
            out.append("| page | issue | text |")
            out.append("|---|---|---|")
            for pn, kind, txt in samples:
                out.append("| %d | %s | %s |" % (pn, kind, txt.replace("|", "/")))
        out.append("")
    path = OUT / "item-review.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")
    print("item review written:", path.relative_to(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="catalog id to build")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="also write catalog/item-review.md: how many product "
                         "codes/names failed to pair, with samples to check")
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

    write_home_index(cats_built)

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

    # ---- Static full-text search index ----
    # Scanning every deck for product codes and names is the slow half of this
    # script (the kitchen deck alone is 168 pages), so each catalog's rows are
    # cached under its PDF hash: change one deck and only that deck is re-scanned.
    # --force still re-scans everything, which is what you want after editing
    # page_items() rather than a PDF.
    idx_path = ROOT / "search-index.json"
    idx_cache_path = ROOT / ".search-cache.json"
    idx_cache = {}
    if idx_cache_path.exists() and not args.force:
        try:
            idx_cache = json.loads(idx_cache_path.read_text(encoding="utf-8"))
        except Exception:
            idx_cache = {}
    idx_ids = [c for c in CATS if (ROOT / c["pdf"]).exists()]
    pdf_sha = {c["id"]: (manifest.get(c["id"]) or {}).get("pdf") or sha1_file(ROOT / c["pdf"])
               for c in idx_ids}
    entries = []
    for c in idx_ids:
        cached = idx_cache.get(c["id"])
        mark = len(entries)
        if (cached and cached.get("sha") == pdf_sha[c["id"]] and not args.force
                and not (args.only and args.only != c["id"])):
            entries.extend(cached.get("entries", []))
            print("  index reused:", c["id"], len(cached.get("entries", [])), "entries")
        else:
            # page -> section title, so a search hit can name its category
            sec = {}
            toc_rel = c.get("toc") or ("toc-%s.json" % c["id"])
            toc_file = ROOT / toc_rel
            if toc_file.exists():
                try:
                    leaves = [l for l in flatten_toc(json.loads(toc_file.read_text(encoding="utf-8")))]
                    for i, lf in enumerate(leaves):
                        start = int(lf["page"])
                        end = int(leaves[i + 1]["page"]) - 1 if i + 1 < len(leaves) else 10 ** 6
                        for p in range(start, end + 1):
                            if p not in sec:
                                sec[p] = re.sub(r"<[^>]+>", "", str(lf["title"])).strip()
                except Exception as exc:
                    print("  ! outline not usable for sections:", exc)
            with pymupdf.open(str(ROOT / c["pdf"])) as doc:
                for pn in range(1, doc.page_count + 1):
                    txt = re.sub(r"\s+", " ", doc[pn - 1].get_text()).strip()
                    if not txt:
                        continue
                    e = {"id": c["id"], "pn": pn, "text": txt[:4000]}
                    if sec.get(pn):
                        e["section"] = sec[pn]
                    items = page_items(doc, pn - 1)
                    if items:
                        e["items"] = items
                    entries.append(e)
            idx_cache[c["id"]] = {"sha": pdf_sha[c["id"]], "entries": entries[mark:]}
            print("  index scanned:", c["id"], len(entries) - mark, "entries")

    # Self-describing file: the reader can tell a product-level index from the
    # older page-level one, and look up catalog names without guessing.
    payload = {
        "v": 2,
        "unit": "product",
        "catalogs": {c["id"]: c["name"] for c in idx_ids},
        "entries": entries,
    }
    idx_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                        encoding="utf-8")
    idx_cache_path.write_text(json.dumps(idx_cache, ensure_ascii=False), encoding="utf-8")
    print("search-index.json updated:", len(entries), "entries,",
          round(idx_path.stat().st_size / 1024), "KB")

    if args.report:
        rows = []
        for c in CATS:
            pdf = ROOT / c["pdf"]
            if not pdf.exists():
                continue
            stats = {"pages": 0, "codes": 0, "unpaired": 0, "unnamed": 0}
            samples = []
            with pymupdf.open(str(pdf)) as doc:
                for pn in range(1, doc.page_count + 1):
                    au = item_audit(doc, pn - 1)
                    if not au:
                        continue
                    stats["pages"] += 1
                    stats["codes"] += au["codes"]
                    stats["unpaired"] += len(au["codes_unpaired"])
                    stats["unnamed"] += au["unnamed"]
                    for code in au["codes_unpaired"][:2]:
                        if len([s for s in samples if s[0] == pn and s[1] == "unpaired code"]) < 2:
                            samples.append((pn, "unpaired code", code))
                    if au["unnamed"] and len(samples) < 24:
                        samples.append((pn, "row without code",
                                        "%d row(s) on this page" % au["unnamed"]))
            rows.append((c["id"], c["name"], stats, samples[:24]))
            print("audit:", c["id"], stats)
        write_item_report(rows)

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print("manifest written (index info saved)")


if __name__ == "__main__":
    main()
