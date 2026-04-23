"""
startup_manager.py — Configure OS-level auto-start on login.

Windows: HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
macOS:   ~/Library/LaunchAgents/com.screenshotbuffer.plist
"""

import os
import sys
from pathlib import Path

_APP_NAME  = "ScreenshotBuffer"
_BUNDLE_ID = "com.screenshotbuffer"


def _exe_args() -> list[str]:
    """Return the command line needed to launch this app."""
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller bundle
        return [sys.executable]
    # Running as a plain Python script
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
    return [sys.executable, script]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def set_startup(enabled: bool) -> None:
    """Enable or disable launch-at-login for this app."""
    try:
        if sys.platform == "win32":
            _windows(enabled)
        elif sys.platform == "darwin":
            _macos(enabled)
        else:
            print("[Startup] Auto-start not supported on this platform")
    except Exception as exc:
        print(f"[Startup] Failed ({'enable' if enabled else 'disable'}): {exc}")


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

def _windows(enabled: bool) -> None:
    import winreg  # type: ignore

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    args = _exe_args()
    # Quote each argument in case paths contain spaces
    cmd = " ".join(f'"{a}"' if " " in a else a for a in args)

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        key_path,
        0,
        winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, cmd)
            print(f"[Startup] Registered in Run key: {cmd}")
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
                print("[Startup] Removed from Run key")
            except FileNotFoundError:
                pass  # already absent


# ---------------------------------------------------------------------------
# macOS LaunchAgent
# ---------------------------------------------------------------------------

_PLIST_DIR  = Path.home() / "Library" / "LaunchAgents"
_PLIST_PATH = _PLIST_DIR / f"{_BUNDLE_ID}.plist"


def _plist_content(args: list[str]) -> str:
    program_args = "\n        ".join(f"<string>{a}</string>" for a in args)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{_BUNDLE_ID}</string>
    <key>ProgramArguments</key>
    <array>
        {program_args}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{Path.home()}/.screenshot_buffer/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/.screenshot_buffer/stderr.log</string>
</dict>
</plist>
"""


def _macos(enabled: bool) -> None:
    if enabled:
        _PLIST_DIR.mkdir(parents=True, exist_ok=True)
        _PLIST_PATH.write_text(_plist_content(_exe_args()), encoding="utf-8")
        os.system(f'launchctl load "{_PLIST_PATH}"')
        print(f"[Startup] LaunchAgent installed: {_PLIST_PATH}")
    else:
        if _PLIST_PATH.exists():
            os.system(f'launchctl unload "{_PLIST_PATH}"')
            _PLIST_PATH.unlink()
            print("[Startup] LaunchAgent removed")
