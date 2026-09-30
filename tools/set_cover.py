# -*- coding: utf-8 -*-
"""Install a hand-made cover image as a catalogue's homepage card cover.

gen_covers.py renders a card from page 1 of each PDF. When a catalogue has a
designed cover instead (a poster made outside the deck), drop the artwork in with
this tool and set "coverLocked": true on that catalog in catalogs.json so the
renderer leaves it alone on the next pipeline run.

    python tools/set_cover.py new2026 path\\to\\cover.png
"""
import argparse
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CATALOGS = json.loads((ROOT / "catalogs.json").read_text(encoding="utf-8"))
WIDTH = 640          # ~2x the largest on-page card width
QUALITY = 78


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("catalog_id")
    ap.add_argument("image")
    args = ap.parse_args()

    ids = [c["id"] for c in CATALOGS]
    if args.catalog_id not in ids:
        raise SystemExit("unknown catalog id %r (known: %s)" % (args.catalog_id, ", ".join(ids)))

    src = Path(args.image)
    if not src.exists():
        raise SystemExit("no such image: %s" % src)

    im = Image.open(src)
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        im = im.convert("RGBA")
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    scale = WIDTH / float(im.width)
    im = im.resize((WIDTH, max(1, round(im.height * scale))), Image.LANCZOS)

    out = ROOT / "assets" / "covers" / ("%s.jpg" % args.catalog_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    locked = next(c for c in CATALOGS if c["id"] == args.catalog_id).get("coverLocked", False)
    print("wrote %s  %dx%d  %.0f KB  coverLocked=%s"
          % (out, im.width, im.height, out.stat().st_size / 1024.0, locked))
    if not locked:
        print("NOTE: set \"coverLocked\": true for %s in catalogs.json, "
              "otherwise gen_covers.py will overwrite this on the next run." % args.catalog_id)


if __name__ == "__main__":
    main()
