"""Stroke icons (Lucide, ISC license) recolored with the theme tokens (UI-CMP-04)."""

from __future__ import annotations

from functools import cache
from importlib.resources import files

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from rumia_configurator.gui.theme.tokens import METRICS


def available_icons() -> list[str]:
    """Names of the bundled icons, without the ``.svg`` extension."""
    root = files("rumia_configurator.gui.theme") / "icons"
    return sorted(p.name.removesuffix(".svg") for p in root.iterdir() if p.name.endswith(".svg"))


@cache
def svg_text(name: str) -> str:
    """Source of icon ``name``; strokes use ``currentColor``."""
    resource = files("rumia_configurator.gui.theme") / "icons" / f"{name}.svg"
    if not resource.is_file():
        raise FileNotFoundError(f"icon {name!r} is not bundled; available: {available_icons()}")
    return resource.read_text(encoding="utf-8")


@cache
def icon_pixmap(name: str, color: str, size: int = METRICS.icon, ratio: float = 1.0) -> QPixmap:
    """Render icon ``name`` in ``color`` (``#RRGGBB``) as a ``size`` px pixmap."""
    svg = svg_text(name).replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixels = round(size * ratio)
    pixmap = QPixmap(pixels, pixels)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, pixels, pixels))
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def icon(name: str, color: str, size: int = METRICS.icon) -> QIcon:
    """Icon ``name`` in ``color``, sharp on normal and high-density screens."""
    result = QIcon()
    for ratio in (1.0, 2.0):
        result.addPixmap(icon_pixmap(name, color, size, ratio))
    return result
