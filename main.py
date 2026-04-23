"""
main.py — Application entry point.

Run with:
    python main.py

The app starts silently — look for the tray icon (Windows) or menu-bar
icon (macOS).  No main window appears.
"""

import sys
import os


def main() -> None:
    # ----------------------------------------------------------------
    # Qt application — must be created before any other Qt objects
    # ----------------------------------------------------------------
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    # Allow tray icon to remain when all windows are closed
    app = QApplication(sys.argv)
    app.setApplicationName("ScreenshotBuffer")
    app.setApplicationDisplayName("Screenshot Buffer")
    app.setQuitOnLastWindowClosed(False)

    # ----------------------------------------------------------------
    # macOS: hide from Dock — appear as a pure menu-bar app
    # ----------------------------------------------------------------
    if sys.platform == "darwin":
        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyAccessory  # type: ignore
            NSApplication.sharedApplication().setActivationPolicy_(
                NSApplicationActivationPolicyAccessory
            )
        except ImportError:
            pass   # pyobjc not installed; app will appear in Dock (minor cosmetic issue)

    # ----------------------------------------------------------------
    # Core + Tray
    # ----------------------------------------------------------------
    from settings_manager import SettingsManager
    from app_core import AppCore
    from tray_manager import TrayManager

    settings = SettingsManager()
    core     = AppCore(settings)
    tray     = TrayManager(core, settings)   # noqa: F841 — keeps tray alive

    core.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
