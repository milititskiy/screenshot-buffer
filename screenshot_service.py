"""
screenshot_service.py — Full-screen capture, returns raw PNG bytes.

Uses `mss` for cross-platform screen grabbing (Windows & macOS).
On macOS you must grant Screen Recording permission to the terminal / app
(System Preferences → Privacy & Security → Screen Recording).
"""

import io
import sys
from PIL import Image


def capture_screenshot() -> bytes:
    """
    Capture the primary monitor.

    Returns:
        PNG image as raw bytes (in-memory, never written to disk).
    Raises:
        RuntimeError on failure (e.g. permission denied on macOS).
    """
    try:
        import mss  # type: ignore
    except ImportError as exc:
        raise RuntimeError("mss is not installed — run: pip install mss") from exc

    try:
        with mss.mss() as sct:
            # monitors[0] = all monitors combined; monitors[1] = primary
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)

            if sct_img.width == 0 or sct_img.height == 0:
                raise RuntimeError(
                    "Screenshot returned an empty image. "
                    "On macOS: grant Screen Recording permission "
                    "(System Preferences → Privacy → Screen Recording)."
                )

            # mss returns BGRA; convert to RGB via Pillow
            pil_img = Image.frombytes(
                "RGB",
                sct_img.size,
                sct_img.bgra,
                "raw",
                "BGRX",
            )

            buf = io.BytesIO()
            # compress_level=1 → fast compression (smaller than 0, still quick)
            pil_img.save(buf, format="PNG", optimize=False, compress_level=1)
            return buf.getvalue()

    except Exception as exc:
        raise RuntimeError(f"Screenshot capture failed: {exc}") from exc
