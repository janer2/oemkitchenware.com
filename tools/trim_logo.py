# -*- coding: utf-8 -*-
"""Trim the whitespace around the Yongli wordmark.

assets/logo.png is a 1200x1200 square whose wordmark only fills the middle
third, so a `height:38px` header rule rendered the mark about 13px tall. This
writes assets/logo-mark.png (cropped to the ink, downscaled to ~3x the header
size so it stays crisp on retina screens) for the site header. The square
original is left untouched for the favicon / apple-touch-icon / og:image.
"""
from pathlib import Path

from PIL import Image

BASE = Path(r"C:\oemkitchenware")
SRC = BASE / "assets" / "logo.png"
OUT = BASE / "assets" / "logo-mark.png"
TARGET_H = 150          # ~3.4x the 44px header height
MARGIN = 6              # a hair of padding so glyphs are not clipped


def main():
    im = Image.open(SRC).convert("RGBA")
    flat = Image.new("RGBA", im.size, (255, 255, 255, 255))
    flat.alpha_composite(im)
    ink = flat.convert("L").point(lambda p: 255 if p < 245 else 0)
    box = ink.getbbox()
    if not box:
        raise SystemExit("no ink found in %s" % SRC)
    x0, y0, x1, y1 = box
    x0 = max(0, x0 - MARGIN)
    y0 = max(0, y0 - MARGIN)
    x1 = min(im.width, x1 + MARGIN)
    y1 = min(im.height, y1 + MARGIN)
    mark = im.crop((x0, y0, x1, y1))
    scale = TARGET_H / float(mark.height)
    mark = mark.resize((max(1, round(mark.width * scale)), TARGET_H), Image.LANCZOS)
    mark.save(OUT, "PNG", optimize=True)
    print("ink box = %s -> %s" % ((x0, y0, x1, y1), mark.size))
    print("%s %.1f KB" % (OUT.name, OUT.stat().st_size / 1024.0))


main()
