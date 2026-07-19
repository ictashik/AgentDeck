#!/bin/bash
# Builds the release binary via SPM and wraps it into a real .app bundle
# (Swift Package Manager doesn't produce app bundles on its own — a plain
# Info.plist + directory layout is all macOS actually requires).
set -euo pipefail
cd "$(dirname "$0")"

swift build -c release

APP="build/AgentDeckWidget.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
cp .build/release/AgentDeckWidget "$APP/Contents/MacOS/"
cp Resources/Info.plist "$APP/Contents/Info.plist"

echo "Built $APP"
echo "Run: open $APP"
