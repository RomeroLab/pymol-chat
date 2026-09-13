#!/usr/bin/env bash
set -euo pipefail

HELPER_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HELPER_DIR/PyMOLChatVoice.app"
EXECUTABLE="$APP_DIR/Contents/MacOS/PyMOLChatVoice"
SOURCE="$HELPER_DIR/main.m"
PLIST="$APP_DIR/Contents/Info.plist"

if [[ -x "$EXECUTABLE" && "$EXECUTABLE" -nt "$SOURCE" && "$EXECUTABLE" -nt "$PLIST" ]]; then
    exit 0
fi

mkdir -p "$APP_DIR/Contents/MacOS" "$HELPER_DIR/.module-cache"
xcrun clang -fobjc-arc -fmodules-cache-path="$HELPER_DIR/.module-cache" \
  -O2 "$SOURCE" -o "$EXECUTABLE" -framework AVFoundation -framework Foundation
codesign --force --deep --sign - "$APP_DIR" >/dev/null
"$EXECUTABLE" --self-test
