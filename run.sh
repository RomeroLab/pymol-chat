#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYMOL_APP="${PYMOL_APP:-/Applications/PyMOL.app}"

if [[ ! -x "$PYMOL_APP/Contents/bin/pymol" ]]; then
  echo "PyMOL was not found at $PYMOL_APP" >&2
  echo "Set PYMOL_APP to the application location and try again." >&2
  exit 1
fi

if command -v xcrun >/dev/null 2>&1; then
  "$PROJECT_DIR/voice_helper/build.sh"
else
  echo "Warning: Xcode Command Line Tools are unavailable; voice input will be disabled." >&2
fi

exec "$PYMOL_APP/Contents/bin/pymol" -r "$PROJECT_DIR/launch_plugin.py" "$@"
