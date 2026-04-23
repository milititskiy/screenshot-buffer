"""
clipboard_service.py — Copy a PNG image (bytes) to the system clipboard.

Platform strategy
-----------------
Windows:
    Uses win32clipboard (pywin32).
    Sets CF_DIB  (Device-Independent Bitmap)  — universally understood.
    Also sets the custom "PNG" format          — preferred by modern apps
    such as Slack, Telegram, browsers, and Office.

macOS:
    Primary:  NSPasteboard + NSImage via PyObjC.
              NSImage encodes the image as TIFF + PNG on the pasteboard,
              which every Cocoa / Electron app accepts.
    Fallback: AppleScript `set the clipboard to (read ... as «class PNGf»)`
              for environments where PyObjC is unavailable.

Linux / other (best-effort):
    Uses QClipboard (Qt) which works in most X11 / Wayland setups.
"""

import io
import sys
import time


class ClipboardService:
    def copy_image(self, image_data: bytes) -> bool:
        """
        Copy *image_data* (raw PNG bytes) to the system clipboard.

        Returns True on success, False on failure.
        Must be called from the main / UI thread.
        """
        try:
            if sys.platform == "win32":
                return self._copy_windows(image_data)
            elif sys.platform == "darwin":
                return self._copy_macos(image_data)
            else:
                return self._copy_qt(image_data)
        except Exception as exc:
            print(f"[Clipboard] Error: {exc}")
            return False

    # ------------------------------------------------------------------
    # Windows — win32clipboard (pywin32)
    # ------------------------------------------------------------------

    def _copy_windows(self, image_data: bytes) -> bool:
        import win32clipboard  # type: ignore
        import win32con        # type: ignore
        from PIL import Image

        # Build DIB (Device-Independent Bitmap) from the PNG
        pil_img = Image.open(io.BytesIO(image_data)).convert("RGB")
        bmp_buf = io.BytesIO()
        pil_img.save(bmp_buf, format="BMP")
        bmp_bytes = bmp_buf.getvalue()
        # CF_DIB = everything after the 14-byte BITMAPFILEHEADER
        dib_bytes = bmp_bytes[14:]

        # Register the "PNG" custom clipboard format once
        png_fmt = win32clipboard.RegisterClipboardFormat("PNG")

        # Retry loop: another process might briefly own the clipboard
        last_exc: Exception | None = None
        for _ in range(5):
            try:
                win32clipboard.OpenClipboard()
                try:
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32con.CF_DIB, dib_bytes)
                    win32clipboard.SetClipboardData(png_fmt, image_data)
                    return True
                finally:
                    win32clipboard.CloseClipboard()
            except Exception as exc:
                last_exc = exc
                time.sleep(0.1)

        raise RuntimeError(f"Clipboard unavailable after retries: {last_exc}")

    # ------------------------------------------------------------------
    # macOS — NSPasteboard (PyObjC preferred, AppleScript fallback)
    # ------------------------------------------------------------------

    def _copy_macos(self, image_data: bytes) -> bool:
        try:
            from AppKit import NSPasteboard, NSImage, NSData  # type: ignore
            pb = NSPasteboard.generalPasteboard()
            pb.clearContents()
            ns_data  = NSData.dataWithBytes_length_(image_data, len(image_data))
            ns_image = NSImage.alloc().initWithData_(ns_data)
            if ns_image is not None and ns_image.isValid():
                result = pb.writeObjects_([ns_image])
                return bool(result)
            print("[Clipboard] NSImage is invalid, trying AppleScript fallback")
            return self._copy_macos_applescript(image_data)
        except ImportError:
            print("[Clipboard] PyObjC not found, using AppleScript fallback")
            return self._copy_macos_applescript(image_data)

    def _copy_macos_applescript(self, image_data: bytes) -> bool:
        import os
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
            fh.write(image_data)
            tmp = fh.name
        try:
            # «class PNGf» is the AppleScript type code for PNG images
            script = f'set the clipboard to (read POSIX file "{tmp}" as \u00abclass PNGf\u00bb)'
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                timeout=8,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError as exc:
            print(f"[Clipboard] osascript failed: {exc.stderr.decode().strip()}")
            return False
        except Exception as exc:
            print(f"[Clipboard] AppleScript fallback failed: {exc}")
            return False
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Linux / generic — Qt clipboard
    # ------------------------------------------------------------------

    def _copy_qt(self, image_data: bytes) -> bool:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QImage

        qimg = QImage()
        qimg.loadFromData(image_data)
        if qimg.isNull():
            print("[Clipboard] QImage failed to load PNG data")
            return False
        app = QApplication.instance()
        if app is None:
            return False
        app.clipboard().setImage(qimg)
        return True
