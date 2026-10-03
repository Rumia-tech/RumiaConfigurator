"""Applies the light or dark theme to the application and switches it at run time.

The mode is ``"system"``, ``"light"`` or ``"dark"`` (UI-COL-03): ``"system"``
follows the color scheme of the operating system and reacts when it changes.
"""

from __future__ import annotations

import atexit
import logging
import shutil
import tempfile
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import shiboken6
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel

from rumia_configurator.gui.theme.fonts import FontLoadResult, load_fonts, sans_font
from rumia_configurator.gui.theme.icons import icon, icon_pixmap, svg_text
from rumia_configurator.gui.theme.qss import STYLE_IMAGES, build_stylesheet
from rumia_configurator.gui.theme.tokens import THEMES, Palette, Theme, ThemeName

logger = logging.getLogger(__name__)

MODES = ("system", "light", "dark")


def app_icon() -> QIcon:
    """The application icon from the Rumia logo (UI-CMP-05)."""
    data = (files("rumia_configurator.gui") / "assets" / "app_icon.png").read_bytes()
    pixmap = QPixmap()
    pixmap.loadFromData(data)
    return QIcon(pixmap)


def build_palette(p: Palette) -> QPalette:
    """Qt palette for the widgets the style sheet does not cover."""
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: p.bg,
        QPalette.ColorRole.WindowText: p.text,
        QPalette.ColorRole.Base: p.bg,
        QPalette.ColorRole.AlternateBase: p.surface,
        QPalette.ColorRole.Text: p.text,
        QPalette.ColorRole.BrightText: p.ink,
        QPalette.ColorRole.Button: p.bg,
        QPalette.ColorRole.ButtonText: p.ink,
        QPalette.ColorRole.Highlight: p.link,
        QPalette.ColorRole.HighlightedText: p.on_link,
        QPalette.ColorRole.Link: p.link,
        QPalette.ColorRole.LinkVisited: p.link,
        QPalette.ColorRole.ToolTipBase: p.tooltip,
        QPalette.ColorRole.ToolTipText: p.on_tooltip,
        # No text lighter than ``text``, placeholders included.
        QPalette.ColorRole.PlaceholderText: p.text,
        QPalette.ColorRole.Light: p.bg,
        QPalette.ColorRole.Midlight: p.surface,
        QPalette.ColorRole.Mid: p.line,
        QPalette.ColorRole.Dark: p.line,
        QPalette.ColorRole.Shadow: p.line,
        QPalette.ColorRole.Accent: p.link,
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(p.text))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, QColor(p.surface))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, QColor(p.surface))
    return palette


@dataclass
class _IconBinding:
    """An icon to repaint on every theme change."""

    target: QAbstractButton | QLabel
    name: str
    role: str
    size: int


class ThemeManager(QObject):
    """Owns the current theme; emits ``changed`` after every switch."""

    changed = Signal(object)  # Theme

    def __init__(self, app: QApplication, mode: str = "system") -> None:
        super().__init__(app)
        self._app = app
        self._mode = "system"
        self._theme = THEMES[ThemeName.LIGHT]
        self._icons: list[_IconBinding] = []
        self._image_dir = Path(tempfile.mkdtemp(prefix="rumia-theme-"))
        atexit.register(shutil.rmtree, self._image_dir, ignore_errors=True)
        app.styleHints().colorSchemeChanged.connect(self._on_system_scheme_changed)
        self.set_mode(mode)

    @property
    def mode(self) -> str:
        """The user's choice: ``"system"``, ``"light"`` or ``"dark"``."""
        return self._mode

    @property
    def theme(self) -> Theme:
        """The theme in use, with ``"system"`` already resolved."""
        return self._theme

    def set_mode(self, mode: str) -> None:
        """Switch to ``"system"``, ``"light"`` or ``"dark"`` without a restart."""
        if mode not in MODES:
            raise ValueError(f"unknown theme mode {mode!r}; expected one of {MODES}")
        self._mode = mode
        self._apply(self._resolve())

    def color(self, role: str) -> str:
        """Hex value of palette ``role`` in the current theme."""
        value: str = getattr(self._theme.palette, role)
        return value

    def bind_icon(
        self, target: QAbstractButton | QLabel, name: str, role: str = "ink", size: int = 16
    ) -> None:
        """Give ``target`` icon ``name`` in color ``role`` and keep it in step with the theme."""
        binding = _IconBinding(target, name, role, size)
        self._icons.append(binding)
        self._paint_icon(binding)

    def _resolve(self) -> ThemeName:
        """Concrete theme for the current mode."""
        if self._mode == "light":
            return ThemeName.LIGHT
        if self._mode == "dark":
            return ThemeName.DARK
        scheme = self._app.styleHints().colorScheme()
        return ThemeName.DARK if scheme == Qt.ColorScheme.Dark else ThemeName.LIGHT

    def _apply(self, name: ThemeName) -> None:
        """Apply ``name`` to the whole application and notify the listeners."""
        self._theme = THEMES[name]
        self._app.setPalette(build_palette(self._theme.palette))
        self._app.setStyleSheet(build_stylesheet(self._theme, self._style_images()))
        self._icons = [b for b in self._icons if shiboken6.isValid(b.target)]
        for binding in self._icons:
            self._paint_icon(binding)
        logger.debug("Theme %s applied (mode %s)", name.value, self._mode)
        self.changed.emit(self._theme)

    def _style_images(self) -> dict[str, str]:
        """Write the recolored SVGs the style sheet refers to; return their paths."""
        paths: dict[str, str] = {}
        for name, role in STYLE_IMAGES:
            color = self.color(role)
            path = self._image_dir / f"{name}-{color.lstrip('#').lower()}.svg"
            if not path.exists():
                path.write_text(svg_text(name).replace("currentColor", color), encoding="utf-8")
            paths[name] = path.as_posix()
        return paths

    def _paint_icon(self, binding: _IconBinding) -> None:
        """Render one bound icon in the current theme."""
        color = self.color(binding.role)
        if isinstance(binding.target, QLabel):
            ratio = binding.target.devicePixelRatioF()
            binding.target.setPixmap(icon_pixmap(binding.name, color, binding.size, ratio))
        else:
            binding.target.setIcon(icon(binding.name, color, binding.size))

    def _on_system_scheme_changed(self, _scheme: Qt.ColorScheme) -> None:
        """Follow the operating system when the mode is ``"system"``."""
        if self._mode == "system":
            self._apply(self._resolve())


_manager: ThemeManager | None = None


def install_theme(app: QApplication, mode: str = "system") -> tuple[ThemeManager, FontLoadResult]:
    """Load the fonts, set style, font, icon and theme on ``app``.

    Call once, right after creating the ``QApplication``.
    """
    global _manager
    app.setStyle("Fusion")  # same rendering on Windows, Linux and macOS
    fonts = load_fonts()
    app.setFont(sans_font())
    app.setWindowIcon(app_icon())
    _manager = ThemeManager(app, mode)
    return _manager, fonts


def theme_manager() -> ThemeManager:
    """The manager created by :func:`install_theme`."""
    if _manager is None or not shiboken6.isValid(_manager):
        raise RuntimeError("install_theme() has not been called")
    return _manager


def _reset_for_tests() -> None:
    """Forget the installed manager (tests create a new one each time)."""
    global _manager
    _manager = None
