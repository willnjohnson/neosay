"""
Cowsay-style speech bubble, wrapped to a max width, with a short tail
that reaches back toward the pet. Since 8-bit Neopets (usually) face right,
the pet sits on the LEFT and the bubble sits on the RIGHT, with the tail
pointing left into the pet's face.
"""

from __future__ import annotations

import textwrap
from typing import List, Tuple

BOX_UNICODE = dict(
    tl="\u256d",
    tr="\u256e",
    bl="\u2570",
    br="\u256f",
    h="\u2500",
    v="\u2502",
    conn="\u2524",
)
BOX_ASCII = dict(
    tl=".",
    tr=".",
    bl="'",
    br="'",
    h="-",
    v="|",
    conn="+",
)


def wrap_text(text: str, width: int) -> List[str]:
    text = " ".join(text.split())  # collapse whitespace/newlines
    if not text:
        text = "..."
    wrapped = textwrap.wrap(text, width=width) or [""]
    return wrapped


def build_bubble(text: str, width: int = 40, think: bool = False,
                  ascii_only: bool = False) -> Tuple[List[str], int]:
    """Returns (lines, tail_row) where tail_row is the index within
    `lines` that the connector to the pet should attach to."""
    box = BOX_ASCII if ascii_only else BOX_UNICODE
    body = wrap_text(text, width)
    inner_w = max(len(line) for line in body)

    tail_row = 1 + len(body) // 2  # middle text line

    lines = [box["tl"] + box["h"] * (inner_w + 2) + box["tr"]]
    for idx, line in enumerate(body):
        current_row = 1 + idx
        # Replace vertical border with '┤' (or '+' in ASCII) at the tail connection row
        left_v = box["conn"] if current_row == tail_row else box["v"]
        lines.append(f"{left_v} {line.ljust(inner_w)} {box['v']}")
    lines.append(box["bl"] + box["h"] * (inner_w + 2) + box["br"])

    if think:
        # Swap the tail-row border glyph for a soft curve, cowthink-style.
        pass
    return lines, tail_row


def connector(think: bool, ascii_only: bool) -> str:
    if think:
        return "o  O  " if not ascii_only else "o O "
    return "\u2500\u2500\u2500" if not ascii_only else "---"
