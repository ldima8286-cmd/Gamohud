#!/usr/bin/env bash
# One-command installer for Gamohud.
#
# Linux/macOS (portable): runs from the repo, or clones from GitHub if piped/remote.
# For a one-liner install:
#   curl -fsSL https://raw.githubusercontent.com/ldima8286-cmd/Gamohud/main/install.sh | sh
#
# Or locally (from a cloned repo): ./install.sh
set -e

REPO_URL="https://github.com/ldima8286-cmd/Gamohud.git"
REPO_BRANCH="main"
INSTALL_DIR="${GAMOHUD_HOME:-$HOME/.local/share/gamohud}"
PREFIX="${PREFIX:-$HOME/.local}"

BIN_DIR="$PREFIX/bin"
DESKTOP_DIR="$PREFIX/share/applications"
ICON_DIR="$PREFIX/share/icons/hicolor/scalable/apps"
APP_DIR="$INSTALL_DIR/app"

SRC=""

# Detect if we're running from inside the repo.
_SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || true)"
if [ -z "$_SCRIPT_PATH" ]; then
    _SCRIPT_PATH="$0"
fi

SCRIPT_DIR_DET="$(cd "$(dirname "$_SCRIPT_PATH")" 2>/dev/null && pwd)"
if [ -n "$SCRIPT_DIR_DET" ] && [ -f "$SCRIPT_DIR_DET/src/app.py" ] && [ -f "$SCRIPT_DIR_DET/requirements.txt" ]; then
    SRC="$SCRIPT_DIR_DET"
fi

# If piped (or $0 doesn't look like repo), clone into INSTALL_DIR.
if [ -z "$SRC" ]; then
    command -v git >/dev/null 2>&1 || { echo "error: git is required to install." >&2; exit 1; }
    mkdir -p "$(dirname "$INSTALL_DIR")"
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "Updating Gamohud in $INSTALL_DIR..."
        git -C "$INSTALL_DIR" pull --ff-only || true
        SRC="$INSTALL_DIR"
    else
        echo "Cloning Gamohud from $REPO_URL..."
        rm -rf "$INSTALL_DIR"
        git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
        SRC="$INSTALL_DIR"
    fi
fi

# Ensure venv + deps
echo "Setting up Python environment..."
(
    cd "$SRC"
    if [ ! -x ".venv/bin/python" ]; then
        _py="$(command -v python3 || command -v python)" || { echo "error: python3/python 3.10+ not found." >&2; exit 1; }
        "$_py" -m venv .venv
    fi
    PY=".venv/bin/python"
    "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info>=(3,10) else 1)' || { echo "error: Python 3.10+ required." >&2; exit 1; }
    "$PY" -m pip install --upgrade pip >/dev/null 2>&1 || true
    "$PY" -m pip install -r requirements.txt
)

# Vulkan layer (best effort)
if [ -x "$SRC/layer/build_layer.sh" ]; then
    if "$SRC/layer/build_layer.sh" --install; then
        echo "Vulkan layer installed (real FPS backend available)."
    else
        echo "Vulkan layer not built (no compiler/Vulkan headers) - skipping."
    fi
fi

# Install launcher and desktop entry
mkdir -p "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR" "$APP_DIR"

cp "$SRC/assets/gamohud.svg" "$ICON_DIR/gamohud.svg" 2>/dev/null || true

cat > "$BIN_DIR/gamohud-gui" <<EOF
#!/bin/sh
exec "$SRC/.venv/bin/python" "$SRC/src/app.py" "\$@"
EOF
chmod +x "$BIN_DIR/gamohud-gui"

cat > "$BIN_DIR/gamohud-run" <<EOF
#!/bin/sh
exec "$SRC/.venv/bin/python" "$SRC/src/run_wrapper.py" "\$@"
EOF
chmod +x "$BIN_DIR/gamohud-run"

cat > "$BIN_DIR/gamohud" <<EOF
#!/bin/sh
exec "$BIN_DIR/gamohud-gui" "\$@"
EOF
chmod +x "$BIN_DIR/gamohud"

cat > "$DESKTOP_DIR/gamohud.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Gamohud
GenericName=Performance Overlay
Comment=Standalone system monitor and FPS overlay (no MangoHud required)
Exec=$BIN_DIR/gamohud-gui
Icon=gamohud
Terminal=false
Categories=Utility;Game;
Keywords=overlay;fps;monitor;gamohud;
StartupNotify=true
EOF
chmod +x "$DESKTOP_DIR/gamohud.desktop"

echo "---"
echo "Done."
echo "Run: gamohud-gui (or 'gamohud')"
echo "Ensure $BIN_DIR is in your PATH if not already."
echo "Source: $SRC"
