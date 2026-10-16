#!/usr/bin/env bash
# Run the Gamohud GUI from source.
#
# On first run this creates a local .venv and installs the dependencies, so a
# plain checkout (or `git clone`) can be launched with a single command. No
# compiler is required for the GUI itself (the optional Vulkan layer is the only
# part that needs one - see ./layer/build_layer.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_bootstrap.sh
. "$SCRIPT_DIR/_bootstrap.sh"

exec "$PY" "$SCRIPT_DIR/src/app.py" "$@"
