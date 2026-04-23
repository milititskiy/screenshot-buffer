# Screenshot Buffer

A lightweight, background-only tray/menu-bar utility that **instantly sends
screenshots between two computers on the same LAN** and **copies the received
image directly to the clipboard** so you can paste it with `Ctrl+V` / `Cmd+V`
into any application.

---

## 1. Product Summary

| Feature | Detail |
|---|---|
| UI | System tray (Windows) / Menu bar (macOS) — no main window |
| Send trigger | Configurable global hotkey (default `Ctrl+Shift+S`) |
| Transport | Direct TCP over LAN |
| Receive action | Image copied to clipboard — paste immediately |
| Compatibility | Slack, Telegram, Word, browser editors, Paint, etc. |
| Platforms | Windows 10/11, macOS 12+ |

---

## 2. Technology Choice

**Chosen stack: Python 3.11+ + PySide6 + pynput + mss + Pillow**

| Alternative | Why rejected |
|---|---|
| **Electron** | 150–300 MB binary; JavaScript makes native clipboard/hotkey harder |
| **Tauri** | Rust learning curve; clipboard image API is limited in v1 |
| **PyQt5** | GPL; PySide6 (LGPL) preferred |
| **tkinter** | No system tray, no global hotkeys |
| **PySide6** ✅ | Cross-platform tray, Qt clipboard, small install, LGPL |

Supporting libraries:

| Library | Role |
|---|---|
| `pynput` | Global hotkeys without an active window |
| `mss` | Fast cross-platform screen capture |
| `Pillow` | PNG ↔ BMP conversion for clipboard |
| `pywin32` | `win32clipboard` — native Windows clipboard (CF_DIB + PNG format) |
| `pyobjc-framework-Cocoa` | `NSPasteboard` — native macOS clipboard |

---

## 3. Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        main.py                                │
│   QApplication (main thread, Qt event loop)                   │
└───────┬───────────────────────────────────────────────────────┘
        │ creates
        ▼
┌───────────────────┐      signals (queued,    ┌────────────────┐
│   AppCore         │ ◄─── thread-safe) ──────► TrayManager    │
│   (QObject)       │                           (QObject)       │
└──┬──┬──┬──┬───────┘                           └────────────────┘
   │  │  │  │
   │  │  │  └─ ClipboardService   (main thread — Qt clipboard)
   │  │  └──── HotkeyManager      (pynput thread — daemon)
   │  └─────── SenderService      (ad-hoc daemon threads)
   └────────── ReceiverService    (listener + per-conn daemon threads)
                    │
                    └─ protocol.py  (encode / decode wire frames)
```

**Thread safety rule:** background threads never touch the UI or clipboard
directly.  They emit Qt signals which are automatically queued to the main
thread via `AutoConnection`.

---

## 4. Project Structure

```
sender_screenshot_buffer/
├── main.py               Entry point
├── app_core.py           Central coordinator (QObject, owns all services)
├── tray_manager.py       System tray / menu-bar UI
├── hotkey_manager.py     Global shortcut registration (pynput)
├── screenshot_service.py Screen capture (mss + Pillow)
├── sender_service.py     TCP client — sends one frame per connection
├── receiver_service.py   TCP server — multi-threaded listener
├── clipboard_service.py  Platform-specific image clipboard write
├── protocol.py           Binary wire format (encode / decode)
├── settings_manager.py   JSON settings in ~/.screenshot_buffer/
├── startup_manager.py    OS login-item integration
├── create_icon.py        Generates assets/icon.{png,ico,icns}
├── requirements.txt
├── build_windows.bat
├── build_macos.sh
└── assets/               (created by create_icon.py)
    ├── icon.png
    ├── icon.ico
    └── icon.icns
```

---

## 5. Wire Protocol

```
Offset  Size   Field
──────  ─────  ──────────────────────────────────────
0       4      Magic bytes: b'SNAP'
4       4      Metadata length  N  (uint32 big-endian)
8       4      Image length     M  (uint32 big-endian)
12      N      JSON: { "sender": "…", "timestamp": …, "image_size": … }
12+N    M      PNG image bytes (in-memory, never touches disk)
```

Hard limit: 100 MB per image.  Oversized frames are rejected and the
connection is dropped.

---

## 6. Clipboard Implementation Detail

### Windows (`clipboard_service.py → _copy_windows`)

1. Decode PNG → Pillow RGB image
2. Encode as BMP in memory
3. Strip 14-byte `BITMAPFILEHEADER` → raw `CF_DIB` blob
4. `win32clipboard.RegisterClipboardFormat("PNG")` — custom format ID
5. Open clipboard, empty it, set **both** `CF_DIB` and `"PNG"` formats
6. Close clipboard

Setting two formats allows:
- Old apps (Paint, Photoshop) to use `CF_DIB`
- Modern apps (Slack, Telegram, browsers) to prefer the lossless `"PNG"` format

### macOS (`clipboard_service.py → _copy_macos`)

1. Wrap raw PNG bytes in `NSData`
2. Create `NSImage` from `NSData` (automatically supports PNG, TIFF, JPEG)
3. `NSPasteboard.generalPasteboard().clearContents()`
4. `NSPasteboard.writeObjects_([ns_image])` — writes TIFF + PNG representations

Every Cocoa and Electron app on macOS reads from `NSPasteboard`, so this
works with Slack, Telegram, Safari, Word, Pages, etc.

**Fallback** (no PyObjC): AppleScript
`set the clipboard to (read POSIX file "…" as «class PNGf»)`

---

## 7. Windows — Run Instructions (Development)

### Prerequisites

- Python 3.11 or 3.12 (https://python.org/downloads)
- pip (bundled with Python)

### Steps

```bat
cd sender_screenshot_buffer

:: Install dependencies
pip install -r requirements.txt

:: Run
python main.py
```

A blue camera icon appears in the Windows system tray (bottom-right).

**First-time setup:**

1. Right-click the tray icon
2. **Set Target IP …** — enter the IP of the receiving machine
3. **Mode** → choose *Sender*, *Receiver*, or *Both*

**To send a screenshot:** press `Ctrl+Shift+S`
**To receive:** ensure the other machine runs the app in Receiver or Both mode;
the image is automatically placed in your clipboard when it arrives.

---

## 8. macOS — Run Instructions (Development)

### Prerequisites

- Python 3.11 or 3.12 (Homebrew: `brew install python`)
- pip

### Steps

```bash
cd sender_screenshot_buffer

# Install dependencies (includes PyObjC for clipboard + Dock hiding)
pip install -r requirements.txt

# Run
python main.py
```

A blue camera icon appears in the macOS menu bar.

**macOS permissions (required on first run):**

| Permission | Where to grant |
|---|---|
| **Accessibility** | System Preferences → Privacy & Security → Accessibility |
| **Screen Recording** | System Preferences → Privacy & Security → Screen Recording |

You must grant these and then re-launch the app.

**To send:** press `Cmd+Shift+S`  
*(macOS default is `Ctrl+Shift+S` too; change via tray menu → Set Shortcut)*

---

## 9. Packaging Instructions

### Windows — Single `.exe`

```bat
build_windows.bat
```

Output: `dist\ScreenshotBuffer.exe`  
Size: ~60–80 MB (PySide6 bundled)

Distribute the single `.exe` — no Python installation required.

### macOS — `.app` Bundle

```bash
chmod +x build_macos.sh
./build_macos.sh
```

Output: `dist/ScreenshotBuffer.app`

The build script patches `Info.plist` with `LSUIElement = true` so the app
hides from the Dock automatically (pure menu-bar app).

To distribute: create a DMG:

```bash
hdiutil create -volname "ScreenshotBuffer" \
    -srcfolder dist/ScreenshotBuffer.app \
    -ov -format UDZO \
    dist/ScreenshotBuffer.dmg
```

**Note:** The `.app` is unsigned.  Users must right-click → Open the first
time to bypass macOS Gatekeeper, or you can sign it with an Apple Developer
certificate:

```bash
codesign --deep --force --sign "Developer ID Application: YOUR NAME (TEAMID)" \
    dist/ScreenshotBuffer.app
```

---

## 10. Known Limitations

| Area | Limitation |
|---|---|
| **macOS Accessibility** | Global hotkey silently fails until Accessibility permission is granted in System Preferences. The app provides no automatic prompt — grant it manually. |
| **macOS Screen Recording** | `mss` returns a black image if Screen Recording is denied. Grant the permission and restart. |
| **Windows Defender / AV** | PyInstaller bundles may be flagged as suspicious. Add an exclusion or sign the binary. |
| **Multiple monitors** | Only the primary monitor is captured. Multi-monitor support requires selecting `mss.monitors[0]` (all monitors combined). |
| **Firewall** | The receiver listens on TCP port 9876 (configurable). Ensure the port is open on the receiving machine's firewall. |
| **No encryption** | Traffic is plaintext TCP. Use only on trusted private networks. |
| **One sender at a time** | The receiver handles concurrent connections but the clipboard is overwritten by the most recent image. |
| **Large screenshots** | A 4K monitor produces a ~3–8 MB PNG. Transfer is fast on LAN (< 1 s) but may be slower on congested networks. |
| **macOS code signing** | Without signing, users see a Gatekeeper warning on first launch. |
| **Linux** | Clipboard falls back to Qt (`QClipboard`). Global hotkeys and tray work but are untested. Screen recording may require `xhost` access. |

---

## Quick-Start Cheat Sheet

```
Machine A (Sender)          Machine B (Receiver)
──────────────────          ────────────────────
python main.py              python main.py
Set Target IP → B's IP      Mode: Receiver (or Both)
Mode: Sender (or Both)

Press Ctrl+Shift+S  ──────────────────────────►  Image in clipboard
                                                 Press Ctrl+V → paste
```
