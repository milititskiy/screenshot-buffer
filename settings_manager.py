"""
settings_manager.py — Persistent settings stored in ~/.screenshot_buffer/settings.json
"""

import json
import socket
from pathlib import Path

_CONFIG_DIR  = Path.home() / ".screenshot_buffer"
_CONFIG_FILE = _CONFIG_DIR / "settings.json"

DEFAULTS: dict = {
    "target_ip":        "192.168.1.100",
    "port":             9876,
    "shortcut":         "ctrl+shift+s",
    "mode":             "both",          # sender | receiver | both
    "enable_receiving": True,
    "enable_sending":   True,
    "sender_name":      socket.gethostname(),
    "launch_at_startup": False,
}


class SettingsManager:
    def __init__(self) -> None:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._data: dict = dict(DEFAULTS)
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if _CONFIG_FILE.exists():
            try:
                saved = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
                self._data.update(saved)
            except Exception as exc:
                print(f"[Settings] Could not load settings: {exc}")

    def save(self) -> None:
        try:
            _CONFIG_FILE.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[Settings] Could not save settings: {exc}")

    # ------------------------------------------------------------------
    # Generic get / set
    # ------------------------------------------------------------------

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()

    # ------------------------------------------------------------------
    # Typed properties (read-only convenience)
    # ------------------------------------------------------------------

    @property
    def target_ip(self) -> str:
        return self._data["target_ip"]

    @property
    def port(self) -> int:
        return int(self._data["port"])

    @property
    def shortcut(self) -> str:
        return self._data["shortcut"]

    @property
    def mode(self) -> str:
        return self._data["mode"]

    @property
    def enable_receiving(self) -> bool:
        return bool(self._data["enable_receiving"])

    @property
    def enable_sending(self) -> bool:
        return bool(self._data["enable_sending"])

    @property
    def sender_name(self) -> str:
        return self._data["sender_name"]

    @property
    def launch_at_startup(self) -> bool:
        return bool(self._data["launch_at_startup"])
