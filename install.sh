#!/usr/bin/env bash
# Installs the `neosay` command so you can run it as `neosay "..."`
# from anywhere, no `./` or `python3 -m` needed.
#
# Seeds pet art into neosay's persistent storage (~/.neosay/pets by
# default) and pre-renders the art cache.
#
# Usage:  ./install.sh                     # install + copy assets + cache
#         ./install.sh path/to/extra_pets/ # ...and copy extra pets from here too
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || {
    echo "neosay: '$PY' not found. Install Python 3.9+ first." >&2
    exit 1
}

echo "Installing neosay from $SCRIPT_DIR ..."

# Preferred path: pip, as a REGULAR (non-editable) install.
if "$PY" -m pip --version >/dev/null 2>&1; then
    ERR_LOG="$(mktemp)"
    if "$PY" -m pip install --user . -q 2>"$ERR_LOG"; then
        INSTALLED=1
    elif grep -qi "externally-managed-environment" "$ERR_LOG"; then
        echo "  (system pip is externally managed; retrying with --break-system-packages)"
        "$PY" -m pip install --user --break-system-packages . -q
        INSTALLED=1
    else
        cat "$ERR_LOG" >&2
        INSTALLED=0
    fi
    rm -f "$ERR_LOG"
else
    INSTALLED=0
fi

# Fallback: no usable pip, so drop a tiny wrapper script instead.
if [ "${INSTALLED:-0}" != "1" ]; then
    echo "  pip unavailable or install failed; falling back to a wrapper script."
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/neosay" << EOF
#!/usr/bin/env bash
PYTHONPATH="$SCRIPT_DIR\${PYTHONPATH:+:\$PYTHONPATH}" exec "$PY" -m neosay "\$@"
EOF
    chmod +x "$HOME/.local/bin"
fi

# Make sure `neosay` actually resolves on PATH now.
USER_BIN="$("$PY" -m site --user-base 2>/dev/null || true)/bin"

resolve_shell_rc() {
    case "${SHELL:-}" in
        */zsh) echo "$HOME/.zshrc" ;;
        *)     echo "$HOME/.bashrc" ;;
    esac
}

add_to_path_if_needed() {
    dir="$1"
    [ -d "$dir" ] || return 0
    case ":$PATH:" in
        *":$dir:"*) return 0 ;;
    esac
    rc="$(resolve_shell_rc)"
    line="export PATH=\"$dir:\$PATH\""
    if ! grep -qsF "$line" "$rc" 2>/dev/null; then
        printf '\n# added by neosay/install.sh\n%s\n' "$line" >> "$rc"
        echo "  Added $dir to PATH in $rc"
    fi
    export PATH="$dir:$PATH"
    echo "  Run 'source $rc' (or open a new terminal) to pick it up."
}

add_to_path_if_needed "$USER_BIN"
add_to_path_if_needed "$HOME/.local/bin"

echo
if command -v neosay >/dev/null 2>&1; then
    echo "neosay installed: $(command -v neosay)"
else
    echo "neosay installed, but not yet resolving on PATH in this shell session."
    echo "Open a new terminal (or source your shell rc file) and it'll be there."
fi

PETS_DIR="$("$PY" -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from neosay.cli import pets_dir; print(pets_dir())")"

# Seed ~/.neosay/pets/ directly from data/*.rgbz
BUNDLED_SRC="$SCRIPT_DIR/neosay/data"
if [ -d "$BUNDLED_SRC" ]; then
    echo
    echo "Copying pet art into $PETS_DIR/ ..."
    mkdir -p "$PETS_DIR"
    cp -n "$BUNDLED_SRC"/*.rgbz "$PETS_DIR/" 2>/dev/null || true
fi

# Optional: copy extra .rgbz pets from a directory passed as $1
IMPORT_SRC="${1:-}"
if [ -n "$IMPORT_SRC" ]; then
    echo
    if [ -d "$IMPORT_SRC" ]; then
        echo "Copying extra pets from $IMPORT_SRC ..."
        cp -n "$IMPORT_SRC"/*.rgbz "$PETS_DIR/" 2>/dev/null || true
    else
        echo "  '$IMPORT_SRC' not found or not a directory -- skipping." >&2
    fi
fi

# Pre-render the art cache for whatever's now in pets_dir().
echo
echo "Pre-rendering art cache for $PETS_DIR/ ..."
"$PY" - << PYEOF
import glob, os, sys
sys.path.insert(0, "$SCRIPT_DIR")
from neosay import render
from neosay.cli import pets_dir, art_dir

pets = sorted(glob.glob(os.path.join(pets_dir(), "*.rgbz")))
for path in pets:
    slug = os.path.splitext(os.path.basename(path))[0]
    render.render_and_cache(path, art_dir(), slug, force=True)
real = [p for p in pets if not os.path.basename(p).startswith("_")]
print(f"  cached {len(pets)} image(s) ({len(real)} real pet(s))")
PYEOF

echo
echo "$PETS_DIR is the pet folder -- drop <slug>.rgbz files in there any"
echo "time (see \`neosay -l\` for slugs) and they're picked up immediately,"
echo "no reinstall needed. It lives under \$NEOSAY_HOME (default ~/.neosay),"
echo "independent of $SCRIPT_DIR -- safe to delete once this finishes."
echo
echo "Then:"
echo '  neosay "Hello"'
