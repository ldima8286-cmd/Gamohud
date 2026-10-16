#!/bin/sh
# Install the Gamohud desktop application (GUI + overlay) for the current user.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
APP_DIR="$PREFIX/share/gamohud"
BIN_DIR="$PREFIX/bin"
DESKTOP_DIR="$PREFIX/share/applications"
ICON_DIR="$PREFIX/share/icons/hicolor/scalable/apps"

SRC="$SCRIPT_DIR/dist/gamohud-gui"
if [ ! -d "$SRC" ]; then
    echo "Build first: ./build-gui.sh" >&2
    exit 1
fi

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
rm -rf "$APP_DIR/gamohud-gui"
cp -r "$SRC" "$APP_DIR/"
cp "$SCRIPT_DIR/assets/gamohud.svg" "$ICON_DIR/gamohud.svg"

cat > "$BIN_DIR/gamohud-gui" <<EOF
#!/bin/sh
exec "$APP_DIR/gamohud-gui/gamohud-gui" "\$@"
EOF
chmod +x "$BIN_DIR/gamohud-gui"

cat > "$BIN_DIR/gamohud-run" <<EOF
#!/bin/sh
exec "$APP_DIR/gamohud-gui/gamohud-gui" --run "\$@"
EOF
chmod +x "$BIN_DIR/gamohud-run"

cat > "$BIN_DIR/gamohud" <<EOF
#!/bin/sh
exec "$APP_DIR/gamohud-gui/gamohud-gui" "\$@"
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

echo "Installed:"
echo "  binary : $BIN_DIR/gamohud-gui"
echo "  runner : $BIN_DIR/gamohud-run"
echo "  entry  : $DESKTOP_DIR/gamohud.desktop"
echo "Run 'gamohud-gui' (ensure $BIN_DIR is in PATH)."
