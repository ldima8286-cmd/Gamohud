#!/usr/bin/env bash
# Launch `gamohud-run` from source: applies profiles / FPS backends to any command.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_bootstrap.sh
. "$SCRIPT_DIR/_bootstrap.sh"

exec "$PY" "$SCRIPT_DIR/src/run_wrapper.py" "$@"
