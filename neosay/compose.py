from __future__ import annotations

from typing import List

from .bubble import build_bubble, connector


def compose(art_lines: List[str], art_width: int, message: str,
            bubble_width: int = 40, think: bool = False,
            ascii_only: bool = False) -> str:
    bubble_lines, tail_row = build_bubble(message, width=bubble_width,
                                           think=think, ascii_only=ascii_only)
    bw = len(bubble_lines[0])
    link = connector(think, ascii_only)
    link_gap = " " * len(link)

    mouth_row = len(art_lines) // 2
    offset = mouth_row - tail_row

    pad_art = max(0, -offset)
    pad_bubble = max(0, offset)

    art_blank = " " * art_width
    bubble_blank = " " * bw

    art_padded = [art_blank] * pad_art + list(art_lines)
    bubble_padded = [bubble_blank] * pad_bubble + bubble_lines

    height = max(len(art_padded), len(bubble_padded))
    art_padded += [art_blank] * (height - len(art_padded))
    bubble_padded += [bubble_blank] * (height - len(bubble_padded))

    mouth_final_row = mouth_row + pad_art

    out_lines = []
    for i in range(height):
        gap = link if i == mouth_final_row else link_gap
        out_lines.append(f"{art_padded[i]} {gap}{bubble_padded[i]}")
    return "\n".join(out_lines)
