"""
app_core.py — Central coordinator (QObject so signals cross threads safely).

Thread model
------------
Main thread    : Qt event loop, tray UI, clipboard writes
Receiver thread: TCP accept + per-connection threads  (daemon)
Hotkey thread  : pynput GlobalHotKeys listener         (daemon)
Send thread    : screenshot capture + TCP send         (daemon, spawned on demand)

Cross-thread safety
-------------------
All signals are emitted from background threads and delivered to slots in
the main thread via Qt's automatic queued-connection mechanism (because
AppCore is created on the main thread).
"""

import datetime
import threading
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from clipboard_service import ClipboardService
from hotkey_manager import HotkeyManager
from receiver_service import ReceiverService
from sender_service import SenderService
from settings_manager import SettingsManager


class AppCore(QObject):
    # Signals — emitted from any thread, delivered to main-thread slots
    screenshot_received_signal = Signal(object, object)   # (metadata: dict, image_data: bytes)
    status_changed_signal      = Signal(str)
    log_added_signal           = Signal(str)
    send_result_signal         = Signal(bool, str)        # (success, message)

    def __init__(self, settings: SettingsManager) -> None:
        super().__init__()
        self.settings  = settings
        self._logs: list[str] = []
        self._log_lock = threading.Lock()
        self._status   = "Idle"

        self.clipboard = ClipboardService()
        self.sender    = SenderService(settings)
        self.receiver  = ReceiverService(settings, self._on_received_bg)
        self.hotkey    = HotkeyManager(settings, self._on_hotkey_bg)

        # screenshot_received must be handled in the main thread (clipboard)
        self.screenshot_received_signal.connect(self._handle_received_main)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        mode = self.settings.mode

        if self.settings.enable_receiving and mode in ("receiver", "both"):
            self.receiver.start()
            self._set_status("Listening")
        else:
            self._set_status("Idle")

        if self.settings.enable_sending and mode in ("sender", "both"):
            self.hotkey.start()

        self._log(f"Started — mode={mode}  shortcut={self.settings.shortcut!r}")

    def stop(self) -> None:
        self.receiver.stop()
        self.hotkey.stop()
        self._log("Stopped")

    # ------------------------------------------------------------------
    # Receiver restart (called from main thread after settings change)
    # ------------------------------------------------------------------

    def restart_receiver(self) -> None:
        self.receiver.stop()
        QTimer.singleShot(300, self._do_restart_receiver)

    def _do_restart_receiver(self) -> None:
        self.receiver = ReceiverService(self.settings, self._on_received_bg)
        self.screenshot_received_signal  # signal still connected — no reconnect needed
        mode = self.settings.mode
        if self.settings.enable_receiving and mode in ("receiver", "both"):
            self.receiver.start()
            self._set_status("Listening")
        else:
            self._set_status("Idle")

    # ------------------------------------------------------------------
    # Hotkey restart (called from main thread after settings change)
    # ------------------------------------------------------------------

    def restart_hotkey(self) -> None:
        self.hotkey.stop()
        self.hotkey = HotkeyManager(self.settings, self._on_hotkey_bg)
        mode = self.settings.mode
        if self.settings.enable_sending and mode in ("sender", "both"):
            self.hotkey.start()

    # ------------------------------------------------------------------
    # Send (called from main thread via tray menu or global hotkey thread)
    # ------------------------------------------------------------------

    def send_screenshot_now(self) -> None:
        """Fire-and-forget: capture + send on a background thread."""
        threading.Thread(target=self._do_send, daemon=True, name="SendShot").start()

    def _do_send(self) -> None:
        if not self.settings.enable_sending:
            self._log("Sending is disabled")
            return
        try:
            from screenshot_service import capture_screenshot
            self._log("Capturing screenshot …")
            image_data = capture_screenshot()
            self._log(f"Captured {len(image_data):,} bytes — sending …")
            ok = self.sender.send_screenshot(image_data)
            msg = "Screenshot sent!" if ok else f"Send failed — check target IP ({self.settings.target_ip}:{self.settings.port})"
            self._log(msg)
            self.send_result_signal.emit(ok, msg)
        except Exception as exc:
            msg = f"Send error: {exc}"
            self._log(msg)
            self.send_result_signal.emit(False, msg)

    # ------------------------------------------------------------------
    # Callbacks from background threads  (must NOT touch Qt UI directly)
    # ------------------------------------------------------------------

    def _on_hotkey_bg(self) -> None:
        """pynput thread → launch send on its own thread."""
        self._log("Hotkey triggered")
        threading.Thread(target=self._do_send, daemon=True, name="HotkeySend").start()

    def _on_received_bg(self, metadata: dict, image_data: bytes) -> None:
        """Receiver thread → hand off to main thread via signal."""
        self.screenshot_received_signal.emit(metadata, image_data)

    # ------------------------------------------------------------------
    # Main-thread slot: handle received image
    # ------------------------------------------------------------------

    def _handle_received_main(self, metadata: object, image_data: object) -> None:
        sender = metadata.get("sender", "unknown") if isinstance(metadata, dict) else "unknown"
        self._log(f"Received from '{sender}' — copying to clipboard …")
        self._set_status("Receiving")
        ok = self.clipboard.copy_image(image_data)
        if ok:
            self._log("Image in clipboard — press Ctrl+V / Cmd+V to paste")
            self._set_status("Ready — press Ctrl+V to paste")
        else:
            self._log("ERROR: clipboard copy failed")
            self._set_status("Clipboard error")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, status: str) -> None:
        self._status = status
        self.status_changed_signal.emit(status)

    def _log(self, msg: str) -> None:
        ts    = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        with self._log_lock:
            self._logs.append(entry)
            if len(self._logs) > 500:
                self._logs = self._logs[-500:]
        print(entry)
        # Emit from whatever thread we're on — Qt will queue it to the main thread
        self.log_added_signal.emit(entry)

    @property
    def status(self) -> str:
        return self._status

    @property
    def logs(self) -> list[str]:
        with self._log_lock:
            return list(self._logs)
