"""
tray_manager.py — System tray (Windows) / menu-bar (macOS) interface.

Inherits QObject so that signals from AppCore are delivered in the main
thread when connected to methods here.

No persistent main window.  All user interaction goes through:
  - The tray context menu
  - Minimal QInputDialog / QMessageBox popups
  - An optional collapsible log window
"""

import sys
from typing import Optional

from PySide6.QtCore import Qt, QObject
from PySide6.QtGui import (
    QColor, QCursor, QIcon, QImage, QPainter, QPixmap,
)
from PySide6.QtWidgets import (
    QApplication, QDialog, QInputDialog, QMenu,
    QPushButton, QSystemTrayIcon, QTextEdit, QVBoxLayout,
)

from app_core import AppCore
from settings_manager import SettingsManager


# ---------------------------------------------------------------------------
# Log window (optional, shown on demand)
# ---------------------------------------------------------------------------

class _LogWindow(QDialog):
    """Small read-only log viewer — hides instead of closing."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Screenshot Buffer — Logs")
        self.setMinimumSize(540, 320)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFontFamily("Courier New" if sys.platform == "win32" else "Menlo")
        layout.addWidget(self._text)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(80)
        clear_btn.clicked.connect(self._text.clear)
        layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def append(self, text: str) -> None:
        self._text.append(text)
        self._text.ensureCursorVisible()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()
        self.hide()


# ---------------------------------------------------------------------------
# Tray manager
# ---------------------------------------------------------------------------

class TrayManager(QObject):
    def __init__(self, core: AppCore, settings: SettingsManager) -> None:
        super().__init__()
        self._core     = core
        self._settings = settings
        self._log_win: Optional[_LogWindow] = None

        # Verify system tray availability
        if not QSystemTrayIcon.isSystemTrayAvailable():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                "Screenshot Buffer",
                "No system tray is available.\nThe app cannot run without one.",
            )
            QApplication.quit()
            return

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(self._build_icon())
        self._tray.setToolTip("Screenshot Buffer")
        self._tray.setVisible(True)

        self._build_menu()
        self._tray.activated.connect(self._on_activated)

        # Wire core signals → UI updates (all in main thread)
        core.status_changed_signal.connect(self._on_status)
        core.log_added_signal.connect(self._on_log)
        core.send_result_signal.connect(self._on_send_result)
        core.screenshot_received_signal.connect(self._on_received)

    # ------------------------------------------------------------------
    # Icon (drawn programmatically — no file dependency)
    # ------------------------------------------------------------------

    def _build_icon(self, color: str = "#2196F3") -> QIcon:
        size = 64
        img  = QImage(size, size, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)

        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Rounded blue square
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(2, 2, 60, 60, 12, 12)

        # Camera body
        p.setBrush(QColor("white"))
        p.drawRoundedRect(8, 22, 48, 30, 4, 4)

        # Lens ring
        p.setBrush(QColor("#90CAF9"))
        p.drawEllipse(22, 27, 20, 20)

        # Lens center
        p.setBrush(QColor("#1565C0"))
        p.drawEllipse(28, 33, 8, 8)

        # Viewfinder bump
        p.setBrush(QColor("white"))
        p.drawRoundedRect(24, 14, 14, 9, 3, 3)

        p.end()
        return QIcon(QPixmap.fromImage(img))

    # ------------------------------------------------------------------
    # Menu construction
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu = QMenu()

        # --- Status (read-only) ---
        self._status_action = menu.addAction(f"Status: {self._core.status}")
        self._status_action.setEnabled(False)

        # --- Info line (target IP) ---
        self._ip_display = menu.addAction(
            f"Target: {self._settings.target_ip}:{self._settings.port}"
        )
        self._ip_display.setEnabled(False)

        menu.addSeparator()

        # --- Configuration ---
        menu.addAction("Set Target IP …",    self._edit_ip)
        menu.addAction("Set Port …",         self._edit_port)
        menu.addAction("Set Shortcut …",     self._edit_shortcut)
        menu.addAction("Set My Name …",      self._edit_name)

        menu.addSeparator()

        # --- Mode submenu ---
        mode_menu = menu.addMenu("Mode")
        self._act_sender   = mode_menu.addAction("Sender")
        self._act_receiver = mode_menu.addAction("Receiver")
        self._act_both     = mode_menu.addAction("Both")
        for act in (self._act_sender, self._act_receiver, self._act_both):
            act.setCheckable(True)
        self._act_sender.triggered.connect(lambda: self._set_mode("sender"))
        self._act_receiver.triggered.connect(lambda: self._set_mode("receiver"))
        self._act_both.triggered.connect(lambda: self._set_mode("both"))
        self._refresh_mode()

        menu.addSeparator()

        # --- Toggle: receiving ---
        self._recv_act = menu.addAction("Enable Receiving")
        self._recv_act.setCheckable(True)
        self._recv_act.setChecked(self._settings.enable_receiving)
        self._recv_act.toggled.connect(self._toggle_receiving)

        # --- Toggle: sending ---
        self._send_act = menu.addAction("Enable Sending")
        self._send_act.setCheckable(True)
        self._send_act.setChecked(self._settings.enable_sending)
        self._send_act.toggled.connect(self._toggle_sending)

        menu.addSeparator()

        # --- Launch at startup ---
        self._startup_act = menu.addAction("Launch at Startup")
        self._startup_act.setCheckable(True)
        self._startup_act.setChecked(self._settings.launch_at_startup)
        self._startup_act.toggled.connect(self._toggle_startup)

        menu.addSeparator()

        # --- Actions ---
        menu.addAction("Test: Send Screenshot", self._test_send)
        menu.addAction("Show Logs",             self._show_logs)

        menu.addSeparator()
        menu.addAction("Quit", self._quit)

        self._tray.setContextMenu(menu)

    # ------------------------------------------------------------------
    # Tray activation (left-click on macOS should show menu)
    # ------------------------------------------------------------------

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if sys.platform == "darwin" and reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.MiddleClick,
        ):
            self._tray.contextMenu().popup(QCursor.pos())

    # ------------------------------------------------------------------
    # Signal handlers (main thread)
    # ------------------------------------------------------------------

    def _on_status(self, status: str) -> None:
        self._status_action.setText(f"Status: {status}")

    def _on_log(self, entry: str) -> None:
        if self._log_win is not None and self._log_win.isVisible():
            self._log_win.append(entry)

    def _on_received(self, metadata: object, _image_data: object) -> None:
        sender = "unknown"
        if isinstance(metadata, dict):
            sender = metadata.get("sender_name", sender)
        paste_key = "Cmd+V" if sys.platform == "darwin" else "Ctrl+V"
        if self._tray.supportsMessages():
            self._tray.showMessage(
                "Screenshot received",
                f"From {sender} — ready to paste ({paste_key})",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def _on_send_result(self, success: bool, msg: str) -> None:
        if self._tray.supportsMessages():
            self._tray.showMessage(
                "Screenshot Buffer",
                msg,
                QSystemTrayIcon.MessageIcon.Information
                if success
                else QSystemTrayIcon.MessageIcon.Warning,
                2500,
            )

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------

    def _edit_ip(self) -> None:
        text, ok = self._text_dialog(
            "Target IP", "Enter target machine's IP address:", self._settings.target_ip
        )
        if ok and text:
            self._settings.set("target_ip", text)
            self._ip_display.setText(
                f"Target: {self._settings.target_ip}:{self._settings.port}"
            )

    def _edit_port(self) -> None:
        val, ok = QInputDialog.getInt(
            None,
            "Port",
            "Enter port number (1024–65535):",
            value=self._settings.port,
            min=1024,
            max=65535,
        )
        if ok:
            self._settings.set("port", val)
            self._ip_display.setText(
                f"Target: {self._settings.target_ip}:{self._settings.port}"
            )
            self._core.restart_receiver()

    def _edit_shortcut(self) -> None:
        text, ok = self._text_dialog(
            "Global Shortcut",
            "Enter shortcut (e.g.  ctrl+shift+s   or   cmd+shift+s):",
            self._settings.shortcut,
        )
        if ok and text:
            self._core.hotkey.update_shortcut(text.strip().lower())

    def _edit_name(self) -> None:
        text, ok = self._text_dialog(
            "Sender Name",
            "Name shown to the receiver (e.g. MacBook-Pro):",
            self._settings.sender_name,
        )
        if ok and text:
            self._settings.set("sender_name", text.strip())

    def _set_mode(self, mode: str) -> None:
        self._settings.set("mode", mode)
        self._refresh_mode()
        self._core.restart_receiver()
        self._core.restart_hotkey()

    def _refresh_mode(self) -> None:
        mode = self._settings.mode
        self._act_sender.setChecked(mode == "sender")
        self._act_receiver.setChecked(mode == "receiver")
        self._act_both.setChecked(mode == "both")

    def _toggle_receiving(self, checked: bool) -> None:
        self._settings.set("enable_receiving", checked)
        self._core.restart_receiver()

    def _toggle_sending(self, checked: bool) -> None:
        self._settings.set("enable_sending", checked)
        self._core.restart_hotkey()

    def _toggle_startup(self, checked: bool) -> None:
        from startup_manager import set_startup
        self._settings.set("launch_at_startup", checked)
        set_startup(checked)

    def _test_send(self) -> None:
        self._core.send_screenshot_now()

    def _show_logs(self) -> None:
        if self._log_win is None:
            self._log_win = _LogWindow()
            for entry in self._core.logs:
                self._log_win.append(entry)
        self._log_win.show()
        self._log_win.raise_()
        self._log_win.activateWindow()

    def _quit(self) -> None:
        self._core.stop()
        QApplication.quit()

    # ------------------------------------------------------------------
    # Helper — styled input dialog
    # ------------------------------------------------------------------

    @staticmethod
    def _text_dialog(title: str, label: str, current: str) -> tuple[str, bool]:
        dlg = QInputDialog()
        dlg.setWindowTitle(title)
        dlg.setLabelText(label)
        dlg.setTextValue(current)
        dlg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        dlg.setMinimumWidth(360)
        ok = dlg.exec() == QInputDialog.DialogCode.Accepted
        return dlg.textValue().strip(), ok
