#!/usr/bin/env bash
# build_macos.sh — macOS Sequoia (15.x) build script for Screenshot Buffer
#
# Tested on: macOS Sequoia 15.x, Python 3.12, Apple Silicon + Intel
#
# Usage:
#   chmod +x build_macos.sh
#   ./build_macos.sh
#
# Optional — Developer ID signing (for distribution):
#   SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" ./build_macos.sh
#
set -euo pipefail

SIGN_IDENTITY="${SIGN_IDENTITY:-}"   # empty = ad-hoc sign only

echo "============================================================"
echo " Screenshot Buffer — macOS Sequoia Build"
echo "============================================================"

# ── Guard: must run on macOS ─────────────────────────────────────────
if [[ "$(uname)" != "Darwin" ]]; then
    echo "ERROR: This script must be run on macOS."
    exit 1
fi

MACOS_VER=$(sw_vers -productVersion)
ARCH=$(uname -m)
echo "  macOS : $MACOS_VER"
echo "  Arch  : $ARCH"
echo ""

# ── Python version check ─────────────────────────────────────────────
PYTHON_VER=$(python3 --version 2>&1)
echo "  Python: $PYTHON_VER"
PYVER_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYVER_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [[ "$PYVER_MAJOR" -lt 3 ]] || { [[ "$PYVER_MAJOR" -eq 3 ]] && [[ "$PYVER_MINOR" -lt 11 ]]; }; then
    echo "ERROR: Python 3.11 or newer required (found $PYTHON_VER)."
    echo "Install via: brew install python@3.12"
    exit 1
fi

# ── 1. Runtime dependencies ──────────────────────────────────────────
echo ""
echo "[1/6] Installing macOS runtime dependencies..."
pip3 install -r requirements_macos.txt
echo "  Dependencies installed ✓"

# ── 2. PyInstaller ───────────────────────────────────────────────────
echo ""
echo "[2/6] Installing PyInstaller..."
pip3 install "pyinstaller>=6.6.0"
echo "  PyInstaller installed ✓"

# ── 3. Icon ──────────────────────────────────────────────────────────
echo ""
echo "[3/6] Generating icon..."
python3 create_icon.py
if [ ! -f "assets/icon.icns" ]; then
    echo "WARNING: assets/icon.icns not found — bundle will use default icon"
fi

# ── 4. Clean previous build ──────────────────────────────────────────
echo ""
echo "[4/6] Cleaning previous build artefacts..."
rm -rf build dist __pycache__
echo "  Cleaned ✓"

# ── 5. PyInstaller build via .spec ───────────────────────────────────
echo ""
echo "[5/6] Building .app bundle (this takes ~1–2 minutes)..."

pyinstaller ScreenshotBuffer_macos.spec --noconfirm

APP="dist/ScreenshotBuffer.app"
PLIST="$APP/Contents/Info.plist"

if [ ! -d "$APP" ]; then
    echo "ERROR: Build produced no .app at $APP"
    exit 1
fi

# Verify LSUIElement is present (spec sets it; this is a safety check)
if ! /usr/libexec/PlistBuddy -c "Print :LSUIElement" "$PLIST" &>/dev/null; then
    echo "  Patching LSUIElement into Info.plist..."
    /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST"
fi
echo "  .app bundle built ✓"

# ── 6. Code signing ──────────────────────────────────────────────────
echo ""
echo "[6/6] Code signing..."

if [ -n "$SIGN_IDENTITY" ]; then
    echo "  Signing with identity: $SIGN_IDENTITY"
    codesign \
        --deep \
        --force \
        --options runtime \
        --entitlements entitlements.plist \
        --sign "$SIGN_IDENTITY" \
        "$APP"
    echo "  Signed with Developer ID ✓"
    echo ""
    echo "  Verifying signature..."
    codesign --verify --deep --strict "$APP" && echo "  Signature valid ✓"
else
    echo "  No SIGN_IDENTITY set — applying ad-hoc signature..."
    codesign \
        --deep \
        --force \
        --options runtime \
        --entitlements entitlements.plist \
        --sign - \
        "$APP"
    echo "  Ad-hoc signed ✓"
    echo "  NOTE: Users will need to right-click → Open on first launch"
    echo "        (Gatekeeper bypass for unsigned apps)."
fi

# ── Optional: build DMG ──────────────────────────────────────────────
echo ""
read -p "Create distributable DMG? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  Building DMG..."
    hdiutil create \
        -volname "Screenshot Buffer" \
        -srcfolder "$APP" \
        -ov \
        -format UDZO \
        "dist/ScreenshotBuffer.dmg"
    echo "  DMG created: dist/ScreenshotBuffer.dmg ✓"
fi

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo " Build complete!"
echo ""
echo " App bundle : dist/ScreenshotBuffer.app"
if [ -f "dist/ScreenshotBuffer.dmg" ]; then
echo " DMG        : dist/ScreenshotBuffer.dmg"
fi
echo ""
echo " To launch:"
echo "   open dist/ScreenshotBuffer.app"
echo " Or drag to /Applications."
echo ""
echo " REQUIRED — grant these permissions on FIRST LAUNCH:"
echo ""
echo "   1. Accessibility (for global hotkey Ctrl+Shift+S)"
echo "      System Settings → Privacy & Security → Accessibility"
echo "      → add ScreenshotBuffer → enable ✓"
echo ""
echo "   2. Screen Recording (for screenshot capture)"
echo "      System Settings → Privacy & Security → Screen Recording"
echo "      → add ScreenshotBuffer → enable ✓"
echo ""
echo "   After granting both, QUIT and RE-OPEN the app."
echo "============================================================"
