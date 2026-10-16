#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR/.venv/lib/python3.13/site-packages:/var/data/python/lib/python3.13/site-packages:$PYTHONPATH"
VENV_PY="$SCRIPT_DIR/.venv/bin/python"
exec "$VENV_PY" "$SCRIPT_DIR/src/app.py" "$@"
