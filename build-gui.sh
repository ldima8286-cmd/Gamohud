#!/bin/bash
# Build the Gamohud desktop GUI (PySide6) into dist/gamohud-gui.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_SP="$SCRIPT_DIR/.venv/lib/python3.13/site-packages"
QT_LIB="$VENV_SP/PySide6/Qt/lib"

export PYTHONPATH="/var/data/python/lib/python3.13/site-packages:/usr/lib/python3.13/site-packages:$VENV_SP:$PYTHONPATH"
export PATH="/run/host/usr/bin:/var/data/python/bin:$PATH"
export LD_LIBRARY_PATH="$QT_LIB:/run/host/usr/lib64:$LD_LIBRARY_PATH"

exec "$SCRIPT_DIR/.venv/bin/python" -m PyInstaller --noconfirm gamohud-gui.spec "$@"
