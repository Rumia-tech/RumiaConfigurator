"""WCAG 2.1 contrast ratio between two sRGB colors."""

from __future__ import annotations

import re

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def parse_hex(color: str) -> tuple[int, int, int]:
    """Return the 0-255 channels of a ``#RRGGBB`` color."""
    if not _HEX.match(color):
        raise ValueError(f"not a #RRGGBB color: {color!r}")
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def relative_luminance(color: str) -> float:
    """Relative luminance as defined by WCAG 2.1."""

    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = parse_hex(color)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """Contrast ratio from 1 to 21; the order of the two colors does not matter."""
    lighter, darker = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)
