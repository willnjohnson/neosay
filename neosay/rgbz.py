"""
neosay's own RGBZ image format.

Pet art is stored as a tiny header followed by zlib-
compressed raw RGBA8888 pixel data instead ("RGB" pixels + "Z" for the
zlib payload).

Layout (big-endian):
    0:4   magic       b"RGBZ"
    4:5   version     uint8, currently 1
    5:7   width       uint16
    7:9   height      uint16
    9:    payload     zlib.compress(raw RGBA8888 bytes, row-major,
                      top-to-bottom / left-to-right)

Decompressed payload size is always width * height * 4 bytes, which is
checked on decode as a basic corruption guard.
"""

from __future__ import annotations

import struct
import zlib

from PIL import Image

MAGIC = b"RGBZ"
VERSION = 1
_HEADER = struct.Struct(">4sBHH")  # magic, version, width, height


class RGBZError(ValueError):
    """Raised for malformed or unsupported .rgbz data."""


def encode(img: Image.Image) -> bytes:
    """Encode a PIL image as RGBZ bytes."""
    img = img.convert("RGBA")
    if img.width > 0xFFFF or img.height > 0xFFFF:
        raise RGBZError(f"image too large for RGBZ: {img.width}x{img.height}")
    header = _HEADER.pack(MAGIC, VERSION, img.width, img.height)
    payload = zlib.compress(img.tobytes(), level=9)
    return header + payload


def decode(data: bytes) -> Image.Image:
    """Decode RGBZ bytes back into a PIL RGBA image."""
    if len(data) < _HEADER.size:
        raise RGBZError("truncated RGBZ header")
    magic, version, width, height = _HEADER.unpack_from(data, 0)
    if magic != MAGIC:
        raise RGBZError(f"not an RGBZ file (bad magic: {magic!r})")
    if version != VERSION:
        raise RGBZError(f"unsupported RGBZ version: {version}")
    try:
        raw = zlib.decompress(data[_HEADER.size:])
    except zlib.error as exc:
        raise RGBZError(f"corrupt RGBZ payload: {exc}") from exc
    expected = width * height * 4
    if len(raw) != expected:
        raise RGBZError(
            f"RGBZ payload size mismatch: expected {expected} bytes "
            f"for {width}x{height}, got {len(raw)}"
        )
    return Image.frombytes("RGBA", (width, height), raw)


def encode_file(src_path: str, dest_path: str) -> None:
    """Read any Pillow-openable image at src_path and write it to
    dest_path as RGBZ."""
    with Image.open(src_path) as img:
        data = encode(img)
    with open(dest_path, "wb") as fh:
        fh.write(data)


def decode_file(path: str) -> Image.Image:
    with open(path, "rb") as fh:
        return decode(fh.read())
