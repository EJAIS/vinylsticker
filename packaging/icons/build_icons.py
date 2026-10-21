"""
Render the app icon from the master SVG (packaging/icons/icon.svg).

Outputs (all committed, so builds never need this script):
    packaging/icons/icon.ico
        Windows icon with 16, 24, 32, 48, 64, 128 and 256 px images.
    packaging/icons/hicolor/<size>x<size>/apps/vinyl-label-printer.png
        Linux hicolor theme PNGs for 16, 32, 48, 64, 128, 256 and 512 px.

Elements with class="detail" in the SVG (grooves, label ring) are left out
up to SMALL_MAX px, where they would only blur into noise.

Regenerate after changing icon.svg (needs only the app's own dependencies,
PyQt6 and Pillow), from the repository root:
    pip install -r vinyl-label-printer/requirements.txt
    QT_QPA_PLATFORM=offscreen python packaging/icons/build_icons.py
Then commit icon.svg together with all generated files.
"""

import io
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PyQt6.QtGui import QGuiApplication, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

ICON_DIR = Path(__file__).resolve().parent
SVG_FILE = ICON_DIR / "icon.svg"
ICO_FILE = ICON_DIR / "icon.ico"
HICOLOR_DIR = ICON_DIR / "hicolor"
APP_ID = "vinyl-label-printer"

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
PNG_SIZES = (16, 32, 48, 64, 128, 256, 512)
SMALL_MAX = 24

SVG_NS = "http://www.w3.org/2000/svg"


def _svg_bytes(simplified: bool) -> bytes:
    """Return the master SVG, without class="detail" elements if simplified."""
    if not simplified:
        return SVG_FILE.read_bytes()
    ET.register_namespace("", SVG_NS)
    tree = ET.parse(SVG_FILE)
    for parent in tree.iter():
        for child in list(parent):
            if child.get("class") == "detail":
                parent.remove(child)
    return ET.tostring(tree.getroot(), encoding="utf-8")


def render(size: int) -> Image.Image:
    """Render the SVG to a square RGBA image of the given size."""
    renderer = QSvgRenderer(QByteArray(_svg_bytes(size <= SMALL_MAX)))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG: {SVG_FILE}")

    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()

    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGBA")


def main() -> None:
    _app = QGuiApplication(sys.argv)  # noqa: F841 - Qt needs an app instance

    for size in PNG_SIZES:
        out = HICOLOR_DIR / f"{size}x{size}" / "apps" / f"{APP_ID}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        render(size).save(out, optimize=True)
        print(f"wrote {out.relative_to(ICON_DIR)}")

    # Pillow builds each ICO entry from append_images when the size matches,
    # so every size is rendered from the SVG instead of being downscaled.
    images = [render(size) for size in ICO_SIZES]
    images[-1].save(
        ICO_FILE,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=images[:-1],
    )
    print(f"wrote {ICO_FILE.relative_to(ICON_DIR)}")


if __name__ == "__main__":
    main()
