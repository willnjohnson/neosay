from __future__ import annotations

import argparse
import glob
import os
import random
import sys

from . import manifest, render, compose

PKG_DIR = os.path.dirname(os.path.abspath(__file__))

# Bundled 8-bit .rgbz pet files shipped directly with the package.
BUNDLED_DIR = os.path.join(PKG_DIR, "data")


def data_home() -> str:
    """Root of neosay's persistent storage (user-added pets + rendered cache).
    Defaults to ~/.neosay, overridable with NEOSAY_HOME."""
    return os.environ.get("NEOSAY_HOME", os.path.expanduser("~/.neosay"))


def pets_dir() -> str:
    """User directory for custom <slug>.rgbz pet files (~/.neosay/pets).
    Any .rgbz dropped here will override or supplement bundled pets."""
    d = os.path.join(data_home(), "pets")
    os.makedirs(d, exist_ok=True)
    return d


def art_dir() -> str:
    return os.path.join(data_home(), "art")


def pet_path(slug: str) -> str | None:
    """Resolve a slug to its .rgbz file, checking user pets_dir() first
    and falling back to BUNDLED_DIR."""
    for d in (pets_dir(), BUNDLED_DIR):
        p = os.path.join(d, f"{slug}.rgbz")
        if os.path.exists(p):
            return p
    return None


def available_slugs() -> list[str]:
    found = set()
    for d in (pets_dir(), BUNDLED_DIR):
        for path in glob.glob(os.path.join(d, "*.rgbz")):
            found.add(os.path.splitext(os.path.basename(path))[0])
    return sorted(found)


def display_name(slug: str) -> str:
    if slug == manifest.DEMO_SLUG:
        return "Demo Critter (not a real Neopet)"
    return manifest.NEOPETS.get(slug, {}).get("name", slug)


def resolve_pet(requested: str | None) -> str:
    available = available_slugs()
    real_available = [s for s in available if s != manifest.DEMO_SLUG]

    if requested:
        slug = requested.strip().lower()
        if slug not in manifest.NEOPETS and slug != manifest.DEMO_SLUG:
            sys.exit(f"neosay: unknown pet '{requested}'. Try `neosay -l`.")
        if slug not in available:
            sys.exit(
                f"neosay: no image for '{requested}' yet.\n"
                f"Drop a {slug}.rgbz into {pets_dir()}/ and try again."
            )
        return slug

    if real_available:
        return random.choice(real_available)
    if manifest.DEMO_SLUG in available:
        return manifest.DEMO_SLUG
    sys.exit(
        f"neosay: no pet images found in {pets_dir()}/ or {BUNDLED_DIR}/\n"
        f"Drop some <slug>.rgbz files in there (see `neosay -l` for slugs)."
    )


def read_message(args_message: list[str]) -> str:
    if args_message:
        return " ".join(args_message)
    if not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            return piped
    return "Neopia awaits!"


def list_pets() -> str:
    available = set(available_slugs())
    lines = ["Neosay pets (40 official 8-bit Neopets):", ""]
    for slug, info in sorted(manifest.NEOPETS.items(), key=lambda kv: kv[1]["name"]):
        mark = "\u2713" if slug in available else " "
        lines.append(f"  [{mark}] {info['name']:<12} -f {slug}")
    lines.append("")
    lines.append(f"[\u2713] = image present")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="neosay",
        description="cowsay/ponysay, but it's an 8-bit Neopet.",
    )
    p.add_argument("message", nargs="*", help="what the pet should say")
    p.add_argument("-f", "--pet", metavar="SLUG", help="pick a specific pet (see -l)")
    p.add_argument("-l", "--list", action="store_true", help="list available pets")
    p.add_argument("-T", "--think", action="store_true", help="thought bubble instead of speech")
    p.add_argument("-W", "--width", type=int, default=40, help="bubble text wrap width (default 40)")
    p.add_argument("--art-width", type=int, default=34, help="pet art width in columns (default 34)")
    p.add_argument("--ascii", action="store_true", help="use plain ASCII box-drawing")
    p.add_argument("--force-render", action="store_true", help="ignore the art cache and re-render")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list:
        print(list_pets())
        return 0

    slug = resolve_pet(args.pet)
    message = read_message(args.message)

    raw_path = pet_path(slug)
    art_lines = render.render_and_cache(
        raw_path, art_dir(), slug, width_cols=args.art_width, force=args.force_render
    )

    output = compose.compose(
        art_lines,
        art_width=args.art_width,
        message=message,
        bubble_width=args.width,
        think=args.think,
        ascii_only=args.ascii,
    )
    print(output)
    return 0


def entry() -> int:
    try:
        return main()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    raise SystemExit(entry())
