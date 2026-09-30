# -*- coding: utf-8 -*-
"""Propose a table of contents for each catalogue so adding one is not manual.

The checked-in `toc-*.json` outlines are hand-verified (their page numbers were
compared against the printed catalogues) and this tool never touches them. It
produces the first draft two ways:

1. **Printed contents page.** Decks like the 2026 one carry a real contents page
   ("01 Kitchen Tools" ... "14 Household Essentials"). If a page in the first few
   holds enough `NN Title` lines, that list is the proposal - and each number is
   checked against the pages around it, because such numbers are often printed
   one off from the physical page.
2. **Typography.** Otherwise, walk the pages and start a section wherever the
   biggest heading-like line changes.

    python tools/gen_toc.py                 # every catalog with a toc file
    python tools/gen_toc.py kitchen         # just one
    python tools/gen_toc.py --review        # also write toc-review.md

Outputs `toc-<id>.proposed.json` and, with --review, `toc-review.md` comparing the
proposal with the checked-in outline.
"""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_pages as G  # noqa: E402  (ROOT, CATS and the code/spec line rules)

ROOT = G.ROOT
CODE_RE = G.CODE_RE
SPEC_RE = G.SPEC_RE
MEASURE_RE = G.MEASURE_RE

MAX_CHARS = 52
CONTENTS_MIN = 6          # a contents page needs at least this many "NN Title" lines
# On a printed contents page the OCR gives the number and the title as two lines
# on the same visual row ("01" | "Kitchen Tools"), so they are paired by row
# instead of by a single regex. A product name like "8-Piece Kitchen Utensil Set"
# does not produce a climbing 1,2,3... sequence, which is what rules it out.
NUM_LINE_RE = re.compile(r"^0*(\d{1,2})$")
TITLE_LINE_RE = re.compile(r"^[A-Z][A-Za-z&'’()\-]*(?:\s+[A-Za-z&'’()\-]+)*$")
ROW_TOL = 9.0
SPLIT_LOWER = re.compile(r"(?<=[a-z])(?=[A-Z])")
SPLIT_DIGIT = re.compile(r"(?<=[0-9])(?=[A-Z])")
SPLIT_RUN = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])")


def unglue(txt):
    """OCR glues tightly set titles together ("Knives&CuttingBoards")."""
    s = txt.strip()
    for rx in (SPLIT_LOWER, SPLIT_DIGIT, SPLIT_RUN):
        s = rx.sub(" ", s)
    s = s.replace("&", " & ")
    return re.sub(r"\s+", " ", s).strip()


def lines_of(doc, pno):
    """(text, size, bold, top) for every line on a page."""
    try:
        data = doc[pno].get_text("dict")
    except Exception:
        return []
    out = []
    for blk in data.get("blocks", []):
        for ln in blk.get("lines", []):
            spans = ln.get("spans", [])
            txt = "".join(sp.get("text", "") for sp in spans).strip()
            if txt:
                size = max((sp.get("size", 0) for sp in spans), default=0)
                bold = any(int(sp.get("flags", 0)) & 16 for sp in spans)
                out.append((txt, size, bold, ln["bbox"][1]))
    return out


def body_size(doc):
    sizes = [s for pno in range(doc.page_count) for _, s, _, _ in lines_of(doc, pno) if s]
    return statistics.median(sizes) if sizes else 10.0


def normalise(txt):
    return re.sub(r"[^a-z0-9&]+", " ", txt.lower()).strip()


def looks_like_heading(txt, size, bold, cutoff, page_h, top):
    t = txt.strip()
    if len(t) < 4 or len(t) > MAX_CHARS or size < cutoff:
        return False
    if CODE_RE.match(t.upper().replace(" ", "")) or SPEC_RE.match(t) or MEASURE_RE.match(t):
        return False
    letters = sum(ch.isalpha() for ch in t)
    if letters < 4 or letters / float(len(t)) < 0.6:
        return False
    if sum(ch.isdigit() for ch in t) > len(t) * 0.3:
        return False
    if t.endswith((".", ",", ";")) or "@" in t or "http" in t.lower():
        return False
    if not (bold or size >= cutoff * 1.35):     # a banner is bold or clearly bigger
        return False
    # section banners sit near the top of the page, product names do not
    return top <= page_h * 0.45


def contents_page(doc):
    """Read a printed contents page, if the deck has one near the front.

    A real contents page is mostly the list and its numbers run upwards, which is
    what keeps a page of product names from being mistaken for one.
    """
    best, best_n = [], 0
    for pno in range(min(8, doc.page_count)):
        page = lines_of(doc, pno)
        hits = []
        for txt, size, bold, top in page:
            m = NUM_LINE_RE.match(txt.strip())
            if not m:
                continue
            title = ""
            for other, osz, obold, otop in page:
                if other is txt or abs(otop - top) > ROW_TOL:
                    continue
                cand = unglue(other)
                if TITLE_LINE_RE.match(cand) and len(cand) >= 4:
                    title = cand
                    break
            if title:
                hits.append({"title": title, "page": int(m.group(1))})
        nums = [h["page"] for h in hits]
        if len(hits) < CONTENTS_MIN:
            continue
        if nums != sorted(set(nums)):                       # numbers must climb
            continue
        if any(b - a > 2 for a, b in zip(nums, nums[1:])):  # ... and stay consecutive
            continue
        if nums[0] > 2:
            continue
        if len(hits) > best_n:
            best, best_n = hits, len(hits)
    return best


def resolve_pages(doc, entries, from_contents):
    """A printed contents list numbers its *entries* (01, 02, ...), not pages.

    So look up where each title actually starts and use that; keep the printed
    number only as a fallback, marked as unresolved.
    """
    first = {}
    for pno in range(1, doc.page_count):        # skip the contents page itself
        for txt, size, bold, top in lines_of(doc, pno):
            n = normalise(unglue(txt))
            if n and n not in first:
                first[n] = pno + 1
    out = []
    for e in entries:
        want = normalise(e["title"])
        page = first.get(want)
        if page is None and want:
            cands = [p for t, p in first.items() if t == want or t.startswith(want)]
            page = min(cands) if cands else None
        out.append({"title": e["title"],
                    "page": page if page else int(e["page"]),
                    "contentsNo": int(e["page"]) if from_contents else None,
                    "resolved": bool(page)})
    return out


def propose_typography(doc, cutoff):
    """Start a new section wherever the biggest heading-like line changes."""
    sections, prev = [], None
    for pno in range(doc.page_count):
        page_h = doc[pno].rect.height or 1
        cands = [c for c in lines_of(doc, pno)
                 if looks_like_heading(unglue(c[0]), c[1], c[2], cutoff, page_h, c[3])]
        if not cands:
            continue
        txt, size, bold, top = sorted(cands, key=lambda c: (-c[1], not c[2], c[3]))[0]
        key = normalise(unglue(txt))
        if key and key != prev:
            sections.append({"title": unglue(txt), "page": pno + 1})
            prev = key
    return sections


def flatten(entries):
    for e in entries:
        if e.get("children"):
            yield from flatten(e["children"])
        else:
            yield e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("catalog", nargs="?", help="catalog id (default: all with a toc file)")
    ap.add_argument("--review", action="store_true", help="also write toc-review.md")
    args = ap.parse_args()

    review = ["# Outline review", "",
              "Produced by `python tools/gen_toc.py --review`. The checked-in outline is the",
              "source of truth; this is the first draft to compare it against. `source` says",
              "whether a deck's own printed contents page was used or the typography was read.",
              "`contents no.` is the entry number printed on that page (01, 02, ... - it is a",
              "list index, not a page), `page located` is where that heading actually turns up",
              "in the text layer, and anything marked `!!` needs a human.", ""]

    for cat in G.CATS:
        if args.catalog and cat["id"] != args.catalog:
            continue
        toc_path = ROOT / (cat.get("toc") or ("toc-%s.json" % cat["id"]))
        pdf = ROOT / cat["pdf"]
        if not pdf.exists():
            print("skip (pdf missing):", cat["id"])
            continue

        doc = pymupdf.open(str(pdf))
        body = body_size(doc)
        cutoff = max(body * 1.3, 12.0)
        contents = contents_page(doc)
        from_contents = len(contents) >= CONTENTS_MIN
        source, raw = ("printed contents page", contents) if from_contents \
            else ("typography", propose_typography(doc, cutoff))
        checked = resolve_pages(doc, raw, from_contents)
        doc.close()

        proposed = [{"title": c["title"], "page": c["page"]} for c in checked]
        located = len([c for c in checked if c["resolved"]])
        out = toc_path.with_suffix(".proposed.json")
        out.write_text(json.dumps(proposed, ensure_ascii=False, indent=1), encoding="utf-8")
        print("%-8s body=%.1fpt  %-21s -> %2d sections, %2d located -> %s"
              % (cat["id"], body, source, len(proposed), located, out.name))

        review += ["## %s (%s)" % (cat["name"], cat["id"]), "",
                   "source: **%s** | checked-in outline: **%d** sections | proposal: **%d**"
                   % (source, len(list(flatten(json.loads(toc_path.read_text(encoding="utf-8")))))
                      if toc_path.exists() else 0, len(proposed)), "",
                    "| proposed section | contents no. | page located | status |",
                    "|---|---|---|---|"]
        for c in checked:
            review.append("| %s | %s | %s | %s |"
                          % (c["title"],
                             c["contentsNo"] if c["contentsNo"] else "—",
                             c["page"] if c["resolved"] else "—",
                             "ok" if c["resolved"] else "!! title not found in the text layer"))
        review.append("")

        # Name check: even when no page can be located, a section that exists in
        # one list and not the other is a rename or a section nobody noticed.
        if toc_path.exists():
            have = set(normalise(unglue(str(e.get("title", ""))))
                       for e in flatten(json.loads(toc_path.read_text(encoding="utf-8"))))
            prop = set(normalise(unglue(c["title"])) for c in checked)
            only_prop = sorted(prop - have)
            only_have = sorted(have - prop)
            if only_prop or only_have:
                review.append("Name check (after normalising):")
                review.append("")
                for n in only_prop:
                    review.append("- in the proposal only: %s" % n)
                for n in only_have:
                    review.append("- in the checked-in outline only: %s" % n)
                review.append("")

    if args.review:
        (ROOT / "toc-review.md").write_text("\n".join(review), encoding="utf-8")
        print("wrote toc-review.md")


if __name__ == "__main__":
    main()
