"""
setup_py2app.py — Build a native macOS .app using py2app.

py2app is a macOS-specific packager (alternative to PyInstaller) that
creates .app bundles in the same way Xcode does.

Usage (on a Mac):
    pip install py2app
    python setup_py2app.py py2app

Output: dist/ScreenshotBuffer.app
"""

from setuptools import setup

OPTIONS = {
    "app": ["main.py"],
    "options": {
        "py2app": {
            # ── App identity ────────────────────────────────────────
            "bundle_identifier": "com.screenshotbuffer",
            "iconfile": "assets/icon.icns",
            # ── PySide6 / Qt ────────────────────────────────────────
            # py2app uses 'packages' to pull in whole packages with
            # sub-modules (avoids missing plugin issues with Qt).
            "packages": [
                "PySide6",
                "pynput",
                "mss",
                "PIL",
                "AppKit",
                "Foundation",
                "objc",
            ],
            # ── Hidden imports not auto-detected ────────────────────
            "includes": [
                "pynput.keyboard._darwin",
                "pynput.mouse._darwin",
                "mss.darwin",
                "PIL.PngImagePlugin",
                "PIL.BmpImagePlugin",
            ],
            # ── Exclude heavy unused modules ─────────────────────────
            "excludes": [
                "tkinter",
                "unittest",
                "email",
                "http",
                "xmlrpc",
                "PySide6.QtWebEngineWidgets",
                "PySide6.QtWebEngineCore",
                "PySide6.QtMultimedia",
                "PySide6.Qt3DCore",
            ],
            # ── Extra data files ─────────────────────────────────────
            "resources": ["assets"],
            # ── Info.plist extras ────────────────────────────────────
            "plist": {
                # Hide from Dock — pure menu-bar app
                "LSUIElement": True,
                "LSBackgroundOnly": False,
                # Metadata
                "CFBundleName": "ScreenshotBuffer",
                "CFBundleDisplayName": "Screenshot Buffer",
                "CFBundleVersion": "1.0.0",
                "CFBundleShortVersionString": "1.0.0",
                # Privacy usage strings (Sequoia requires these)
                "NSScreenCaptureUsageDescription": (
                    "Screenshot Buffer captures your screen when you press "
                    "the global shortcut to send it to another computer."
                ),
                "NSAccessibilityUsageDescription": (
                    "Screenshot Buffer needs Accessibility access to register "
                    "a system-wide keyboard shortcut."
                ),
                "NSAppleEventsUsageDescription": (
                    "Screenshot Buffer uses Apple Events for clipboard operations."
                ),
                # Minimum macOS version
                "LSMinimumSystemVersion": "13.0",
                # Retina / high-DPI
                "NSHighResolutionCapable": True,
                # Allow LAN TCP (disables ATS for local network)
                "NSAppTransportSecurity": {
                    "NSAllowsArbitraryLoads": True,
                },
            },
            # ── Semi-standalone: include a Python framework copy ─────
            # "semi_standalone" = True uses the system Python (smaller)
            # Leave False for a fully self-contained app (recommended).
            "semi_standalone": False,
            # ── Architecture ─────────────────────────────────────────
            # "universal2" requires all dylibs to be universal as well.
            # Leave empty (native arch) unless you need fat binary.
            # "arch": "universal2",
        }
    },
}

setup(
    name="ScreenshotBuffer",
    version="1.0.0",
    description="Instant LAN screenshot sharing via tray/menu-bar",
    **OPTIONS,
)
