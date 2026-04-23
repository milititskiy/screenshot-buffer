"""
hotkey_manager.py — Register and manage a system-wide global hotkey.

Uses pynput's GlobalHotKeys which works on Windows and macOS without
any visible window being focused.

macOS note: the first time the app runs, macOS will ask for Accessibility
permission (System Preferences → Privacy & Security → Accessibility).
The hotkey will NOT fire until permission is granted.

Windows note: pynput does not require administrator rights for hotkeys.
"""

import threading
from typing import Callable

from pynput import keyboard  # type: ignore


# Keys that become <key> in pynput format
_SPECIAL_KEYS = {
    "ctrl", "shift", "alt", "cmd", "meta", "super",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8",
    "f9", "f10", "f11", "f12",
    "space", "tab", "enter", "esc", "backspace", "delete",
    "home", "end", "page_up", "page_down",
    "up", "down", "left", "right",
}


def _normalize(shortcut: str) -> str:
    """
    Convert a human-readable shortcut string to pynput GlobalHotKeys format.

    Examples:
        "ctrl+shift+s"  →  "<ctrl>+<shift>+s"
        "cmd+shift+s"   →  "<cmd>+<shift>+s"
        "ctrl+alt+f4"   →  "<ctrl>+<alt>+<f4>"
    """
    parts = [p.strip().lower() for p in shortcut.split("+")]
    return "+".join(f"<{p}>" if p in _SPECIAL_KEYS else p for p in parts)


class HotkeyManager:
    def __init__(self, settings, on_trigger: Callable) -> None:
        self._settings   = settings
        self._on_trigger = on_trigger
        self._hotkey: keyboard.GlobalHotKeys | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        raw  = self._settings.shortcut
        norm = _normalize(raw)
        try:
            self._hotkey = keyboard.GlobalHotKeys(
                {norm: self._fired},
                # suppress=False so other apps still receive the key combo
            )
            self._hotkey.daemon = True
            self._hotkey.start()
            print(f"[Hotkey] Registered: {raw!r}  (pynput: {norm!r})")
        except Exception as exc:
            print(f"[Hotkey] Registration failed for {norm!r}: {exc}")
            self._hotkey = None

    def stop(self) -> None:
        hk = self._hotkey
        if hk is not None:
            try:
                hk.stop()
            except Exception:
                pass
            self._hotkey = None
        print("[Hotkey] Unregistered")

    def update_shortcut(self, shortcut_str: str) -> None:
        """Re-register with a new shortcut string."""
        self.stop()
        self._settings.set("shortcut", shortcut_str)
        self.start()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fired(self) -> None:
        """Called from pynput's listener thread — dispatch off-thread."""
        threading.Thread(target=self._on_trigger, daemon=True, name="HotkeyDispatch").start()
