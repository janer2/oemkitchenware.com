"""Give every WhatsApp link a return address.

WhatsApp reports nothing about where a chat started: a message that arrives from
the website, from a business card or from the marketplace profile all look alike.
The only durable signal is the prefilled message, which the buyer sees in the box
before sending. This sweep appends "(via oemkitchenware.com/<path>)" to every
wa.me link in every built page, deriving <path> from the file's own location, so
an incoming enquiry says which page it came from.

Limits worth knowing:
  - the buyer can delete the line before sending (then the enquiry is unattributed);
  - a link opened from a PDF, a business card or the marketplace has no tag by
    design, which is itself the useful signal: no tag means it did not start here.

Run it after the generators, since they rewrite the pages:

    python tools/gen_pages.py --force
    python tools/gen_seo_pages.py
    python tools/tag_whatsapp.py

Idempotent: a link that already carries the tag for its page is left alone.
"""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
WA_NUM = "8613824296558"
BASE = "https://wa.me/" + WA_NUM
HOST = "oemkitchenware.com"
DEFAULT_TEXT = "Hi Yongli, I would like a catalogue and a quote."

# an href pointing at the bare number, with or without a query string
LINK_RE = re.compile(r'href="(https://wa\.me/' + WA_NUM + r'[^"]*)"')
JS_RE = re.compile(r"'https://wa\.me/" + WA_NUM + r"'")
SKIP_DIRS = {"tools", "_incoming", "assets", ".git"}


def page_ref(rel: Path) -> str:
    """catalog/kitchen/index.html -> catalog/kitchen"""
    parts = list(rel.parts)
    if parts and parts[-1] == "index.html":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].rsplit(".", 1)[0]
    ref = "/".join(parts)
    return ref or "home"


def tagged_href(href: str, ref: str) -> str:
    """Return href with a "(via host/path)" marker inside its text parameter."""
    marker = "(via %s/%s)" % (HOST, ref)
    if not href.startswith(BASE + "?"):
        return BASE + "?text=" + quote(DEFAULT_TEXT + " " + marker, safe="")

    query = href[len(BASE) + 1:].replace("&amp;", "&")
    parts = query.split("&") if query else []
    out, has_text = [], False
    for part in parts:
        if part.startswith("text="):
            text = unquote(part[5:])
            if marker not in text:
                text = text.rstrip() + " " + marker
            out.append("text=" + quote(text, safe=""))
            has_text = True
        elif part:
            out.append(part)
    if not has_text:
        out.append("text=" + quote(DEFAULT_TEXT + " " + marker, safe=""))
    return BASE + "?" + "&".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    changed = 0
    links = 0
    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        src = path.read_text(encoding="utf-8")
        ref = page_ref(rel)

        def sub(m):
            nonlocal links
            links += 1
            return 'href="%s"' % tagged_href(m.group(1), ref)

        out = LINK_RE.sub(sub, src)
        if out != src:
            changed += 1
            if not args.dry_run:
                path.write_text(out, encoding="utf-8")

    print("%d links seen in %d pages, %d pages %s"
          % (links, len(list(ROOT.rglob('*.html'))),
             changed, "would change" if args.dry_run else "updated"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
