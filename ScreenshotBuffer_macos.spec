# -*- mode: python ; coding: utf-8 -*-
#
# ScreenshotBuffer_macos.spec
# PyInstaller spec for macOS Sequoia (15.x)
#
# Build with:
#   pyinstaller ScreenshotBuffer_macos.spec
#
# Requirements: run this on macOS with all deps installed.

import sys
from pathlib import Path

block_cipher = None

# ── Hidden imports ────────────────────────────────────────────────────
# pynput uses runtime-selected backends; force the darwin one.
# PyObjC frameworks must be explicitly listed.
HIDDEN_IMPORTS = [
    # pynput darwin backends
    "pynput.keyboard._darwin",
    "pynput.mouse._darwin",
    # PyObjC — core frameworks used by our code and PySide6
    "AppKit",
    "Foundation",
    "Cocoa",
    "objc",
    "PyObjCTools",
    "PyObjCTools.AppHelper",
    # mss internal
    "mss.darwin",
    # PIL formats
    "PIL._imaging",
    "PIL.PngImagePlugin",
    "PIL.BmpImagePlugin",
    # PySide6 modules actually used
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]

# ── Analysis ──────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=[
        ("assets", "assets"),                   # icon files
    ],
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy unused Qt modules to keep bundle size down
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtMultimedia",
        "PySide6.Qt3DCore",
        "PySide6.QtBluetooth",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtLocation",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "tkinter",
        "unittest",
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Executable (inside the .app) ──────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ScreenshotBuffer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX causes issues with macOS code signing
    console=False,      # windowed — no terminal window
    argv_emulation=False,
    target_arch=None,   # None = native arch; use "universal2" for fat binary
    codesign_identity=None,   # None = ad-hoc sign; set to Developer ID for distrib.
    entitlements_file="entitlements.plist",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ScreenshotBuffer",
)

# ── .app Bundle ───────────────────────────────────────────────────────
app = BUNDLE(
    coll,
    name="ScreenshotBuffer.app",
    icon="assets/icon.icns",
    bundle_identifier="com.screenshotbuffer",
    version="1.0.0",
    info_plist={
        # ── Dock / menu-bar behaviour ───────────────────────────────
        "LSUIElement": True,                    # hide from Dock — menu-bar only
        "LSBackgroundOnly": False,              # allow menu-bar icon
        # ── App metadata ────────────────────────────────────────────
        "CFBundleName": "ScreenshotBuffer",
        "CFBundleDisplayName": "Screenshot Buffer",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleIdentifier": "com.screenshotbuffer",
        "CFBundleIconFile": "icon.icns",
        # ── macOS minimum version ───────────────────────────────────
        "LSMinimumSystemVersion": "13.0",       # Ventura+; Sequoia is 15.x
        # ── Privacy usage descriptions (shown in permission dialogs) ─
        "NSScreenCaptureUsageDescription":
            "Screenshot Buffer needs Screen Recording to capture your screen "
            "when you press the global shortcut.",
        "NSAppleEventsUsageDescription":
            "Screenshot Buffer uses Apple Events for clipboard operations.",
        # ── Accessibility (required for global hotkeys) ─────────────
        "NSAccessibilityUsageDescription":
            "Screenshot Buffer needs Accessibility access to register a "
            "system-wide keyboard shortcut.",
        # ── Allow running on Apple Silicon + Intel ──────────────────
        "LSArchitecturePriority": ["arm64", "x86_64"],
        # ── High-resolution display support ─────────────────────────
        "NSHighResolutionCapable": True,
        # ── Suppress App Transport Security (LAN-only TCP) ──────────
        "NSAppTransportSecurity": {
            "NSAllowsArbitraryLoads": True,
        },
    },
)
