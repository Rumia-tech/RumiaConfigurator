"""Generate the application icons and the top bar logos (UI-CMP-05, UI-LAY-01).

Run after changing ``packaging/icons/rumia_mark.svg`` or ``rumia_logo.png``::

    uv run python packaging/make_icons.py

Writes ``packaging/icons/rumia.{ico,icns,png}`` for the executables,
``src/rumia_configurator/gui/assets/app_icon.png`` for the window icon and
``src/rumia_configurator/gui/assets/logo_{light,dark}.png`` for the top bar
(the dark one has the grey wordmark turned white).
The generated files are committed, so building the app does not need Pillow.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "packaging" / "icons" / "rumia_mark.svg"
OUT_DIR = ROOT / "packaging" / "icons"
ASSETS = ROOT / "src" / "rumia_configurator" / "gui" / "assets"
RUNTIME_ICON = ASSETS / "app_icon.png"
LOGO_SOURCE = ROOT / "packaging" / "icons" / "rumia_logo.png"  # mark + wordmark, raster
LOGO_HEIGHT = 66  # 3x the 22 px of the top bar, sharp up to 300% scaling

MASTER = 1024
PADDING = 0.08  # transparent margin around the mark, as a fraction of the side
RENDER = 4096  # render size before cropping, large enough for a sharp 1024 px master


def render_master() -> Image.Image:
    """Render the SVG, crop it to the mark and center it in a square with a margin."""
    renderer = QSvgRenderer(str(SOURCE))
    if not renderer.isValid():
        raise SystemExit(f"Cannot read {SOURCE}: not a valid SVG file.")
    size = renderer.defaultSize()
    scale = RENDER / max(size.width(), size.height())
    image = QImage(
        round(size.width() * scale),
        round(size.height() * scale),
        QImage.Format.Format_ARGB32,
    )
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, image.width(), image.height()))
    painter.end()

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    full = Image.open(io.BytesIO(bytes(data.data()))).convert("RGBA")

    bbox = full.getchannel("A").getbbox()
    if bbox is None:
        raise SystemExit(f"{SOURCE} renders as an empty image.")
    mark = full.crop(bbox)
    side = round(max(mark.size) / (1 - 2 * PADDING))
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(mark, ((side - mark.width) // 2, (side - mark.height) // 2))
    return square.resize((MASTER, MASTER), Image.Resampling.LANCZOS)


def make_logos() -> tuple[Image.Image, Image.Image]:
    """Light and dark top bar logos: the dark one has the neutral grey wordmark in white."""
    source = Image.open(LOGO_SOURCE).convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        raise SystemExit(f"{LOGO_SOURCE} is an empty image.")
    light = source.crop(bbox)
    dark = light.copy()
    pixels = dark.load()
    assert pixels is not None
    for y in range(dark.height):
        for x in range(dark.width):
            r, g, b, a = pixels[x, y]  # type: ignore[misc]
            if a and max(r, g, b) - min(r, g, b) < 16:  # grey: the wordmark
                pixels[x, y] = (255, 255, 255, a)
    width = round(light.width * LOGO_HEIGHT / light.height)
    size = (width, LOGO_HEIGHT)
    return (
        light.resize(size, Image.Resampling.LANCZOS),
        dark.resize(size, Image.Resampling.LANCZOS),
    )


def main() -> None:
    """Generate every icon and logo and print what was written."""
    _app = QGuiApplication([])
    master = render_master()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_ICON.parent.mkdir(parents=True, exist_ok=True)

    master.resize((512, 512), Image.Resampling.LANCZOS).save(OUT_DIR / "rumia.png")
    master.save(
        OUT_DIR / "rumia.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    master.save(OUT_DIR / "rumia.icns")
    master.resize((256, 256), Image.Resampling.LANCZOS).save(RUNTIME_ICON)
    logo_light, logo_dark = make_logos()
    logo_light.save(ASSETS / "logo_light.png")
    logo_dark.save(ASSETS / "logo_dark.png")
    for path in (
        ASSETS / "logo_light.png",
        ASSETS / "logo_dark.png",
        OUT_DIR / "rumia.png",
        OUT_DIR / "rumia.ico",
        OUT_DIR / "rumia.icns",
        RUNTIME_ICON,
    ):
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
