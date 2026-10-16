#!/usr/bin/env bash
# Shared bootstrap for the gamohud launchers (sourced, not executed directly).
#
# Creates a local virtual environment and installs the Python dependencies on
# first run, so a plain checkout just works. After sourcing, $PY points to the
# interpreter to use and $GAMOHUD_SRC to the project root.
#
# shellcheck shell=bash

GAMOHUD_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAMOHUD_VENV="$GAMOHUD_SRC/.venv"

_gamohud_find_python() {
    for _c in python3 python; do
        if command -v "$_c" >/dev/null 2>&1 \
            && "$_c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
            command -v "$_c"
            return 0
        fi
    done
    return 1
}

if [ ! -x "$GAMOHUD_VENV/bin/python" ] && [ ! -x "$GAMOHUD_VENV/Scripts/python.exe" ]; then
    _py="$(_gamohud_find_python)" || {
        echo "gamohud: Python 3.10+ not found. Please install Python 3 first." >&2
        exit 1
    }
    echo "gamohud: creating virtual environment (.venv) ..." >&2
    "$_py" -m venv "$GAMOHUD_VENV" || exit 1
fi

if [ -x "$GAMOHUD_VENV/bin/python" ]; then
    PY="$GAMOHUD_VENV/bin/python"
else
    PY="$GAMOHUD_VENV/Scripts/python.exe"
fi

if ! "$PY" -c 'import PySide6, yaml, psutil' >/dev/null 2>&1; then
    echo "gamohud: installing dependencies (first run, this may take a minute) ..." >&2
    "$PY" -m pip install --upgrade pip >/dev/null 2>&1 || true
    "$PY" -m pip install -r "$GAMOHUD_SRC/requirements.txt" || exit 1
fi
