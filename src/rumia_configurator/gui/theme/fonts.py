"""Bundled brand fonts (SIL OFL), loaded at startup without installing them (UI-TYP-01)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from importlib.resources import files

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QFont, QFontDatabase

from rumia_configurator.gui.theme.tokens import TYPOGRAPHY

logger = logging.getLogger(__name__)

REQUIRED_FAMILIES = (
    TYPOGRAPHY.title_family,
    TYPOGRAPHY.sans_family,
    TYPOGRAPHY.mono_family,
)


@dataclass
class FontLoadResult:
    """Families registered with Qt and the files that could not be loaded."""

    families: set[str] = field(default_factory=set)
    failures: list[str] = field(default_factory=list)

    @property
    def missing_families(self) -> list[str]:
        """Brand families that are not available after loading."""
        return [f for f in REQUIRED_FAMILIES if f not in self.families]


def load_fonts() -> FontLoadResult:
    """Register every bundled ``.ttf`` with Qt. Needs a ``QGuiApplication``.

    A file that cannot be loaded is logged with its cause; Qt then falls back to
    a system font, so the problem is visible in the log and in the result.
    """
    result = FontLoadResult()
    root = files("rumia_configurator.gui.theme") / "fonts"
    for family_dir in sorted(root.iterdir(), key=lambda p: p.name):
        if not family_dir.is_dir():
            continue
        for font_file in sorted(family_dir.iterdir(), key=lambda p: p.name):
            if not font_file.name.endswith(".ttf"):
                continue
            try:
                data = font_file.read_bytes()
            except OSError as exc:
                result.failures.append(f"{font_file.name}: {exc}")
                continue
            font_id = QFontDatabase.addApplicationFontFromData(QByteArray(data))
            if font_id < 0:
                result.failures.append(f"{font_file.name}: Qt rejected the font data")
                continue
            result.families.update(QFontDatabase.applicationFontFamilies(font_id))
    for failure in result.failures:
        logger.warning("Font not loaded: %s", failure)
    if result.missing_families:
        logger.warning(
            "Brand fonts missing: %s. The interface uses system fonts instead; "
            "reinstall the application to restore them.",
            ", ".join(result.missing_families),
        )
    return result


def sans_font(pixel_size: int = TYPOGRAPHY.body_px) -> QFont:
    """IBM Plex Sans, the font of body text, buttons and menus."""
    font = QFont(TYPOGRAPHY.sans_family)
    font.setPixelSize(pixel_size)
    return font


def mono_font(pixel_size: int = TYPOGRAPHY.mono_px) -> QFont:
    """IBM Plex Mono with fixed-width digits, for values, IDs and frames (UI-TYP-02)."""
    font = QFont(TYPOGRAPHY.mono_family)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(pixel_size)
    return font


def section_label_font() -> QFont:
    """Uppercase mono labels with 0.08 em letter spacing."""
    font = mono_font(TYPOGRAPHY.label_px)
    font.setLetterSpacing(
        QFont.SpacingType.AbsoluteSpacing, TYPOGRAPHY.label_px * TYPOGRAPHY.label_spacing_em
    )
    return font
