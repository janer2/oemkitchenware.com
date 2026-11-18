"""Build a chapter list for the category PDFs from their product names.

These decks have no printed section headings - the artwork is product grids, and
every text run is either a product name, a code or a spec line. So the chapter
bar in the reader is derived instead: each page's product names are matched
against a vocabulary of product families, the page is assigned to the family that
dominates it, and consecutive pages of the same family become one chapter.

    python tools/gen_toc_from_names.py            # all decks that have a toc file
    python tools/gen_toc_from_names.py kitchen-tools baking-tools

Writes toc-<id>.json in the same shape gen_toc produces: [{title, page}, ...].
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent

# Ordered: the first pattern that matches a product name wins, so put the
# specific families before the generic ones ("ice cream scoop" is Ice Cream, not
# Spoons; "measuring spoon" is Measuring, not Spoons).
FAMILIES = [
    ("Ice Cream & Popsicles", r"\b(ice ?cream|popsicle|ice ?pop|ice ?cube|ice ?ball|sorbet|gelato|frozen dessert)\b"),
    ("Coffee & Tea", r"\b(coffee|espresso|latte|teapot|teabag|tea strainer|tea infuser|frother|pour.?over|dripper|kettle)\b"),
    # "brush" alone is a basting brush in one deck and a cleaning brush in the
    # next, so it is not a family word; only the qualified forms are.
    ("Baking & Pastry", r"\b(bakeware|baking (?:mat|sheet|pan|tray|set)|cake|muffin|cupcake|cookie|dough|pastry|rolling pin|whisk|sifter|icing|pie |loaf|bread|proofing|sourdough|basting brush|pastry brush)\b"),
    ("Measuring", r"\b(measuring|measurement|kitchen scale|thermometer|kitchen timer|graduated)\b"),
    ("Knives & Cutting", r"\b(knife|knives|cleaver|chopper|slicer|grater|peeler|zester|scissors|shears|sharpener|cutting board|chopping board)\b"),
    ("Tongs & Turners", r"\b(tong|tweezer|turner|lifter|spatula turner)\b"),
    ("Spoons & Ladles", r"\b(spoon|ladle|scoop|skimmer|slotted)\b"),
    ("Bowls & Strainers", r"\b(colander|strainer|sieve|steamer basket|mixing bowl|salad bowl)\b"),
    ("Storage & Organisation", r"\b(container|storage|canister|organi[sz]er|spice jar|food bag|storage bag|rack|shelf|hanger|hook|clip|dispenser|wrap|foil|lid)\b"),
    ("Tableware & Serveware", r"\b(plate|dish|platter|tray|tableware|cutlery|placemat|coaster|napkin|chopstick|serveware)\b"),
    ("Drinkware & Bottles", r"\b(bottle|tumbler|flask|mug|straw|drinkware|thermos)\b"),
    ("Cleaning", r"\b(cleaning|scrub|scouring|sponge|cleaning cloth|wipe|glove|drain|mop|squeegee|dustpan|cleaning brush|dish brush)\b"),
    ("Beauty & Personal Care", r"\b(bath|body scrub|shower|facial|face|massage|comb|mirror|makeup|cosmetic|manicure|pedicure|hair|cupping)\b"),
    ("Kids & Baby", r"\b(baby|kid|child|toddler|bib|feeding|pacifier|teether|weaning|sippy)\b"),
    ("Pet", r"\b(pet|dog|cat|puppy|kitten)\b"),
    ("Outdoor & BBQ", r"\b(bbq|barbecue|grill|outdoor|camping|picnic|garden)\b"),
    ("Household", r"\b(household|laundry|ironing|bathroom|toilet|shoe|umbrella|sewing)\b"),
]
COMPILED = [(name, re.compile(pat, re.I)) for name, pat in FAMILIES]

CODE = re.compile(r"^[A-Z]{1,3}[-\s]?\d{3,5}$")


def page_family(page):
    names = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            text = "".join(s["text"] for s in line["spans"]).strip()
            if not text or CODE.match(text.replace(" ", "")) or len(text) < 4:
                continue
            if re.match(r"^\d+\s*/\s*\d+$", text):
                continue
            names.append(text)
    scores = {}
    for name, rx in COMPILED:
        hits = sum(1 for n in names if rx.search(n))
        if hits:
            scores[name] = scores.get(name, 0) + hits
    if not scores:
        return None
    best, hits = max(scores.items(), key=lambda kv: kv[1])
    # One stray match on a page of twenty products is a coincidence, not a
    # section: demand at least two names, or a clear share of the page.
    if hits < 2 and hits / max(1, len(names)) < 0.4:
        return None
    return best


def build(pdf):
    doc = pymupdf.open(str(pdf))
    raw = [page_family(p) for p in doc]
    # A single page sandwiched between two pages of the same family is usually a
    # mixed layout rather than a real section break; smooth first so the side bar
    # does not flicker between families every other page.
    seq = list(raw)
    for i in range(1, len(raw) - 1):
        if raw[i] and raw[i - 1] == raw[i + 1] and raw[i] != raw[i - 1]:
            seq[i] = raw[i - 1]
    # A page with no recognisable family inside a single-family deck is a layout
    # of mixed photos, not a new section: carry the previous family forward,
    # otherwise the same title reappears as "(2)", "(3)", "(4)".
    carry = None
    for i, fam in enumerate(seq):
        if fam:
            carry = fam
        else:
            seq[i] = carry
    first = next((f for f in seq if f), None)
    seq = [f or first for f in seq]
    chapters, last, start = [], None, None
    for i, fam in enumerate(seq, start=1):
        if fam != last:
            if last:
                chapters.append({"title": last, "page": start})
            last, start = fam, i
    if last:
        chapters.append({"title": last, "page": start})

    # A one-page chapter is noise between two real ones: fold it into the
    # neighbour it came from rather than showing a label that flashes past.
    merged, seen = [], {}
    for i, ch in enumerate(chapters):
        nxt = chapters[i + 1]["page"] if i + 1 < len(chapters) else doc.page_count + 1
        if nxt - ch["page"] < 2 and merged:
            continue
        # A catalogue interleaves families, so a title legitimately comes back
        # later; number the repeat instead of showing two identical entries.
        seen[ch["title"]] = seen.get(ch["title"], 0) + 1
        title = ch["title"] if seen[ch["title"]] == 1 else "%s (%d)" % (ch["title"], seen[ch["title"]])
        merged.append({"title": title, "page": ch["page"]})
    return merged, doc.page_count


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    cat = json.loads((ROOT / "catalogs.json").read_text(encoding="utf-8"))
    ids = args or [c["id"] for c in cat if c.get("toc")]
    for cid in ids:
        entry = next((c for c in cat if c["id"] == cid), None)
        if not entry:
            print("unknown id", cid)
            continue
        pdf = ROOT / entry["pdf"]
        chapters, total = build(pdf)
        out = ROOT / ("toc-%s.json" % cid)
        if len(chapters) < 3:
            # A single-entry side bar is worse than none: it looks broken.
            if out.exists():
                out.unlink()
            print("%-32s %3d pages  too flat (%d chapter), no toc" % (cid, total, len(chapters)))
            continue
        out.write_text(json.dumps(chapters, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("%-32s %3d pages  %2d chapters  %s" % (cid, total, len(chapters),
              ", ".join("%s@%d" % (c["title"], c["page"]) for c in chapters[:5])))


if __name__ == "__main__":
    main()
