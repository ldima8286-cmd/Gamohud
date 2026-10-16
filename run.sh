#!/usr/bin/env bash
# (Legacy alias) Run Gamohud GUI from source. See run-gui.sh for details.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_bootstrap.sh
. "$SCRIPT_DIR/_bootstrap.sh"

exec "$PY" "$SCRIPT_DIR/src/app.py" "$@"
