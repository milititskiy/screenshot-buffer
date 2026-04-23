#!/usr/bin/env bash
# notarize.sh — Submit the DMG to Apple for notarization (optional)
#
# Notarization removes the Gatekeeper warning when users open the app.
# Without it, users must right-click → Open on first launch.
#
# Requirements:
#   - Apple Developer account ($99/year)
#   - App-specific password: https://appleid.apple.com → App-Specific Passwords
#   - Xcode command-line tools: xcode-select --install
#
# Usage:
#   APPLE_ID="you@example.com" \
#   TEAM_ID="ABCD123456" \
#   APP_PASSWORD="xxxx-xxxx-xxxx-xxxx" \
#   ./notarize.sh
#
set -euo pipefail

APPLE_ID="${APPLE_ID:?Set APPLE_ID env var}"
TEAM_ID="${TEAM_ID:?Set TEAM_ID env var}"
APP_PASSWORD="${APP_PASSWORD:?Set APP_PASSWORD env var}"
DMG="dist/ScreenshotBuffer.dmg"

if [ ! -f "$DMG" ]; then
    echo "ERROR: $DMG not found. Run build_macos.sh first."
    exit 1
fi

echo "============================================================"
echo " Notarizing $DMG"
echo "============================================================"

# ── 1. Submit for notarization ────────────────────────────────────────
echo ""
echo "[1/3] Submitting to Apple notary service..."
xcrun notarytool submit "$DMG" \
    --apple-id "$APPLE_ID" \
    --team-id  "$TEAM_ID" \
    --password "$APP_PASSWORD" \
    --wait \
    --progress

echo "  Submission accepted ✓"

# ── 2. Staple the ticket to the DMG ──────────────────────────────────
echo ""
echo "[2/3] Stapling notarization ticket to DMG..."
xcrun stapler staple "$DMG"
echo "  Stapled ✓"

# ── 3. Verify ─────────────────────────────────────────────────────────
echo ""
echo "[3/3] Verifying..."
spctl --assess --type open --context context:primary-signature "$DMG" && echo "  Gatekeeper: PASS ✓"

echo ""
echo "============================================================"
echo " Notarization complete!"
echo " $DMG is now trusted by Gatekeeper on all Macs."
echo " Users can open it without right-click → Open."
echo "============================================================"
