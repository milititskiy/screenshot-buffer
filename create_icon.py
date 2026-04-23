"""
create_icon.py — Generate application icon files for all platforms.

Run once before building:
    python create_icon.py

Produces:
    assets/icon.png       (256x256, used at runtime and as source)
    assets/icon.ico       (multi-size, Windows)
    assets/icon.icns      (macOS — requires iconutil, macOS only)
"""

import os
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow is required: pip install Pillow")
    sys.exit(1)

ASSETS = Path(__file__).parent / "assets"


def draw_icon(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    s   = size

    # Rounded blue square background
    d.rounded_rectangle([s * 0.02, s * 0.02, s * 0.98, s * 0.98],
                        radius=s * 0.16, fill="#2196F3")

    # Camera body (white)
    d.rounded_rectangle([s * 0.12, s * 0.34, s * 0.88, s * 0.80],
                        radius=s * 0.06, fill="white")

    # Lens outer ring
    cx, cy, lr = s * 0.5, s * 0.57, s * 0.15
    d.ellipse([cx - lr, cy - lr, cx + lr, cy + lr], fill="#90CAF9")

    # Lens center
    lr2 = s * 0.08
    d.ellipse([cx - lr2, cy - lr2, cx + lr2, cy + lr2], fill="#1565C0")

    # Viewfinder bump
    d.rounded_rectangle([s * 0.36, s * 0.22, s * 0.62, s * 0.36],
                        radius=s * 0.04, fill="white")

    return img


def create_icons() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    img = draw_icon(256)
    png_path = ASSETS / "icon.png"
    img.save(png_path)
    print(f"Saved {png_path}")

    # --- Windows .ico ---
    ico_path = ASSETS / "icon.ico"
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img_256 = draw_icon(256)
    img_256.save(
        ico_path,
        format="ICO",
        sizes=ico_sizes,
    )
    print(f"Saved {ico_path}")

    # --- macOS .icns (iconutil, macOS only) ---
    if sys.platform == "darwin":
        iconset_dir = ASSETS / "icon.iconset"
        iconset_dir.mkdir(exist_ok=True)
        for s in [16, 32, 64, 128, 256, 512]:
            draw_icon(s).save(iconset_dir / f"icon_{s}x{s}.png")
            draw_icon(s * 2).save(iconset_dir / f"icon_{s}x{s}@2x.png")
        icns_path = ASSETS / "icon.icns"
        try:
            subprocess.run(
                ["iconutil", "-c", "icns", "-o", str(icns_path), str(iconset_dir)],
                check=True,
            )
            print(f"Saved {icns_path}")
        except FileNotFoundError:
            print("iconutil not found — skipping .icns generation")
        except subprocess.CalledProcessError as exc:
            print(f"iconutil failed: {exc}")
    else:
        # Provide a fallback 1024px PNG for PyInstaller on macOS cross-compile
        large = ASSETS / "icon_1024.png"
        draw_icon(1024).save(large)
        print(f"Saved {large}  (use as macOS icon source)")


if __name__ == "__main__":
    create_icons()
    print("Done.")
