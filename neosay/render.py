"""
Converts a pet image into terminal art using the Unicode half-block
trick: each character cell shows two vertical source pixels at once
(the glyph's foreground colour paints the top pixel, the background
colour paints the bottom one), giving roughly square-ish "big pixels"
that suit chunky 8-bit sprites well.

Cached renders are stored as plain text files (with the raw ANSI
escapes already baked in) next to the source images, so repeat runs
of `neosay` don't have to touch Pillow at all.
"""

from __future__ import annotations

import os
import re
from typing import List

from PIL import Image

from . import rgbz

RESET = "\x1b[0m"
ALPHA_THRESHOLD = 40
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _fg(r: int, g: int, b: int) -> str:
    return f"\x1b[38;2;{r};{g};{b}m"


def _bg(r: int, g: int, b: int) -> str:
    return f"\x1b[48;2;{r};{g};{b}m"


def autocrop(img: Image.Image, pad_frac: float = 0.03) -> Image.Image:
    """Crop to the opaque content's bounding box, with a little padding.

    Source images may have a lot of empty transparent margin
    around the actual character -- rendering that margin at
    terminal resolution wastes most of the pixel budget on blank
    space instead of the pet.
    """
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    if bbox is None:
        return img
    x0, y0, x1, y1 = bbox
    pad = int(round(max(x1 - x0, y1 - y0) * pad_frac))
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(img.width, x1 + pad)
    y1 = min(img.height, y1 + pad)
    return img.crop((x0, y0, x1, y1))


def render_image(path: str, width_cols: int = 40) -> List[str]:
    """Render an RGBZ pet file to a list of ANSI-coloured terminal lines."""
    img = rgbz.decode_file(path)
    img = autocrop(img) # autocrop defensively in case .rgbz was hand-code from art with extra transparent margin

    # Two source pixels tall per character row (half-block trick).
    aspect = img.height / img.width
    height_px = max(2, int(round(width_cols * aspect)))
    if height_px % 2:
        height_px += 1

    resample = Image.NEAREST
    img = img.resize((width_cols, height_px), resample)
    pixels = img.load()

    lines: List[str] = []
    for row in range(0, height_px, 2):
        line_chars = []
        last_code = None
        for col in range(width_cols):
            tr, tg, tb, ta = pixels[col, row]
            br, bg_, bb, ba = pixels[col, row + 1]
            top_on = ta > ALPHA_THRESHOLD
            bot_on = ba > ALPHA_THRESHOLD

            if top_on and bot_on:
                code = _fg(tr, tg, tb) + _bg(br, bg_, bb)
                ch = "\u2580"  # upper half block
            elif top_on and not bot_on:
                code = _fg(tr, tg, tb) + "\x1b[49m"
                ch = "\u2580"
            elif bot_on and not top_on:
                code = _fg(br, bg_, bb) + "\x1b[49m"
                ch = "\u2584"  # lower half block
            else:
                code = "\x1b[49m"
                ch = " "

            if code != last_code:
                line_chars.append(code)
                last_code = code
            line_chars.append(ch)
        line_chars.append(RESET)
        lines.append("".join(line_chars))

    return lines


def cache_path(art_dir: str, slug: str, width_cols: int) -> str:
    # width_cols is part of the filename (not just a render argument) so
    # that a cache built at one --art-width is never mistaken for one
    # built at another. Without this, requesting a different width
    # without --force-render would silently reuse art rendered at the
    # old width while compose() pads *other* rows to the new width,
    # leaving the two out of step (bubble border rows drift left/right
    # relative to rows where the pet art actually appears).
    return os.path.join(art_dir, f"{slug}.w{width_cols}.ans")


def render_and_cache(raw_path: str, art_dir: str, slug: str, width_cols: int = 40,
                      force: bool = False) -> List[str]:
    os.makedirs(art_dir, exist_ok=True)
    cpath = cache_path(art_dir, slug, width_cols)
    if not force and os.path.exists(cpath) and os.path.getmtime(cpath) >= os.path.getmtime(raw_path):
        with open(cpath, "r", encoding="utf-8") as fh:
            return fh.read().split("\n")

    lines = render_image(raw_path, width_cols=width_cols)
    with open(cpath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return lines


def visible_width(line: str) -> int:
    """Terminal column width of a single rendered line, i.e. its glyph
    count with ANSI escape sequences stripped out (they occupy zero
    terminal columns but count as characters in the raw string)."""
    return len(_ANSI_RE.sub("", line))