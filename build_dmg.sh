#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$PROJECT_DIR/build/portable"
APP_DIR="$BUILD_DIR/staging/Chat with PyMOL.app"
CONTENTS="$APP_DIR/Contents"
RESOURCES="$CONTENTS/Resources"
OUTPUT="${PYMOL_CHAT_DMG_OUTPUT:-$PROJECT_DIR/outputs/Chat-with-PyMOL-macOS.dmg}"
SIGNING_IDENTITY="${PYMOL_CHAT_SIGNING_IDENTITY:-}"

if [[ -n "$SIGNING_IDENTITY" && "$SIGNING_IDENTITY" != "Developer ID Application:"* ]]; then
  echo "Use the full Developer ID Application identity name for distribution signing." >&2
  exit 1
fi
mkdir -p "$(dirname "$OUTPUT")"

rm -rf "$BUILD_DIR"
mkdir -p "$CONTENTS/MacOS" "$RESOURCES/voice_helper" "$PROJECT_DIR/outputs"

cp "$PROJECT_DIR/packaging/launcher/Info.plist" "$CONTENTS/Info.plist"
cp "$PROJECT_DIR/launch_plugin.py" "$RESOURCES/launch_plugin.py"
cp -R "$PROJECT_DIR/pymol_chat" "$RESOURCES/pymol_chat"
find "$RESOURCES/pymol_chat" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$RESOURCES/pymol_chat" -type f -name '*.pyc' -delete

cp "$PROJECT_DIR/voice_helper/main.m" "$RESOURCES/voice_helper/main.m"
cp -R "$PROJECT_DIR/voice_helper/PyMOLChatVoice.app" "$RESOURCES/voice_helper/"
mkdir -p "$RESOURCES/voice_helper/PyMOLChatVoice.app/Contents/MacOS"

xcrun clang -fobjc-arc -O2 -arch arm64 -arch x86_64 \
  "$PROJECT_DIR/packaging/launcher/main.m" \
  -o "$CONTENTS/MacOS/ChatWithPyMOL" -framework AppKit -framework Foundation

xcrun clang -fobjc-arc -O2 -arch arm64 -arch x86_64 \
  "$PROJECT_DIR/voice_helper/main.m" \
  -o "$RESOURCES/voice_helper/PyMOLChatVoice.app/Contents/MacOS/PyMOLChatVoice" \
  -framework AVFoundation -framework Foundation

if [[ -n "$SIGNING_IDENTITY" ]]; then
  # Sign nested code first. Do not use --deep to sign a distribution build.
  codesign --force --sign "$SIGNING_IDENTITY" --timestamp --options runtime \
    --entitlements "$PROJECT_DIR/packaging/audio.entitlements.plist" \
    "$RESOURCES/voice_helper/PyMOLChatVoice.app"
  codesign --force --sign "$SIGNING_IDENTITY" --timestamp --options runtime \
    --entitlements "$PROJECT_DIR/packaging/audio.entitlements.plist" "$APP_DIR"
else
  codesign --force --sign - "$RESOURCES/voice_helper/PyMOLChatVoice.app" >/dev/null
  codesign --force --sign - "$APP_DIR" >/dev/null
fi

cp "$PROJECT_DIR/packaging/README.txt" "$BUILD_DIR/staging/Read Me.txt"
ln -s /Applications "$BUILD_DIR/staging/Applications"

rm -f "$OUTPUT"
hdiutil create -volname "Chat with PyMOL" -srcfolder "$BUILD_DIR/staging" \
  -ov -format UDZO "$OUTPUT"

if [[ -n "$SIGNING_IDENTITY" ]]; then
  codesign --sign "$SIGNING_IDENTITY" --timestamp "$OUTPUT"
  codesign --verify --strict "$OUTPUT"
fi

codesign --verify --deep --strict "$APP_DIR"
echo "$OUTPUT"
