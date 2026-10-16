#!/bin/bash
# Dev launcher for gamohud-run (applies profiles / FPS backends to any command).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR/.venv/lib/python3.13/site-packages:/var/data/python/lib/python3.13/site-packages:$PYTHONPATH"
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/src/run_wrapper.py" "$@"
