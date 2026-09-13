#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$PROJECT_DIR/build/portable"
APP_DIR="$BUILD_DIR/staging/Chat with PyMOL.app"
CONTENTS="$APP_DIR/Contents"
RESOURCES="$CONTENTS/Resources"
OUTPUT="$PROJECT_DIR/outputs/Chat-with-PyMOL-macOS.dmg"

rm -rf "$BUILD_DIR"
mkdir -p "$CONTENTS/MacOS" "$RESOURCES/voice_helper" "$PROJECT_DIR/outputs"

cp "$PROJECT_DIR/packaging/launcher/Info.plist" "$CONTENTS/Info.plist"
cp "$PROJECT_DIR/launch_plugin.py" "$RESOURCES/launch_plugin.py"
cp -R "$PROJECT_DIR/pymol_chat" "$RESOURCES/pymol_chat"
find "$RESOURCES/pymol_chat" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$RESOURCES/pymol_chat" -type f -name '*.pyc' -delete

cp "$PROJECT_DIR/voice_helper/main.m" "$RESOURCES/voice_helper/main.m"
cp -R "$PROJECT_DIR/voice_helper/PyMOLChatVoice.app" "$RESOURCES/voice_helper/"

xcrun clang -fobjc-arc -O2 -arch arm64 -arch x86_64 \
  "$PROJECT_DIR/packaging/launcher/main.m" \
  -o "$CONTENTS/MacOS/ChatWithPyMOL" -framework AppKit -framework Foundation

xcrun clang -fobjc-arc -O2 -arch arm64 -arch x86_64 \
  "$PROJECT_DIR/voice_helper/main.m" \
  -o "$RESOURCES/voice_helper/PyMOLChatVoice.app/Contents/MacOS/PyMOLChatVoice" \
  -framework AVFoundation -framework Foundation

codesign --force --sign - "$RESOURCES/voice_helper/PyMOLChatVoice.app" >/dev/null
codesign --force --deep --sign - "$APP_DIR" >/dev/null

cp "$PROJECT_DIR/packaging/README.txt" "$BUILD_DIR/staging/Read Me.txt"
ln -s /Applications "$BUILD_DIR/staging/Applications"

rm -f "$OUTPUT"
hdiutil create -volname "Chat with PyMOL" -srcfolder "$BUILD_DIR/staging" \
  -ov -format UDZO "$OUTPUT"

codesign --verify --deep --strict "$APP_DIR"
echo "$OUTPUT"
