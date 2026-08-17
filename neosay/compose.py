from __future__ import annotations

from typing import List

from .bubble import build_bubble, connector
from .render import visible_width


def compose(art_lines: List[str], art_width: int, message: str,
            bubble_width: int = 40, think: bool = False,
            ascii_only: bool = False) -> str:
    bubble_lines, tail_row = build_bubble(message, width=bubble_width,
                                         think=think, ascii_only=ascii_only)
    bw = len(bubble_lines[0])
    link = connector(think, ascii_only)
    link_gap = " " * len(link)

    # Measure the real rendered width. art_width is whatever --art-width 
    # was passed *this* call; art_lines could in principle still be a 
    # render from a different width (e.g. a caller reusing an old cache). 
    # Deriving the filler width from the actual content keeps blank rows 
    # lined up with real art rows even if those two ever disagree.
    real_width = visible_width(art_lines[0]) if art_lines else art_width

    art_height = len(art_lines)
    bubble_height = len(bubble_lines)

    # Vertical centering: align middles of art and bubble
    art_mid = art_height // 2
    bubble_mid = bubble_height // 2

    # How much to pad each side to align centers
    # Positive offset means bubble is taller, so art needs top padding
    offset = bubble_mid - art_mid

    pad_art_top = max(0, offset)
    pad_bubble_top = max(0, -offset)

    art_blank = " " * real_width
    bubble_blank = " " * bw

    art_padded = [art_blank] * pad_art_top + list(art_lines)
    bubble_padded = [bubble_blank] * pad_bubble_top + bubble_lines

    height = max(len(art_padded), len(bubble_padded))
    art_padded += [art_blank] * (height - len(art_padded))
    bubble_padded += [bubble_blank] * (height - len(bubble_padded))

    # The mouth connects at the bubble's tail row (adjusted for any top padding on bubble)
    mouth_final_row = tail_row + pad_bubble_top

    out_lines = []
    for i in range(height):
        gap = link if i == mouth_final_row else link_gap
        out_lines.append(f"{art_padded[i]} {gap}{bubble_padded[i]}")
    return "\n".join(out_lines)