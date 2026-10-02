"""Design tokens of the Rumia brand (guidelines v2): colors, type and metrics.

This module is plain Python with no Qt import, so the contrast rules can be
tested without a display. Widgets never use colors, fonts or sizes directly:
they go through these tokens, the generated style sheet (``qss.py``) or the
theme manager (``manager.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum


class ThemeName(StrEnum):
    """The two concrete themes. "Follow the system" is resolved to one of them."""

    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True)
class Palette:
    """Color roles of one theme, as ``#RRGGBB`` strings."""

    bg: str  # window, cards
    surface: str  # panels, alternate rows, tiles, callouts
    line: str  # borders, separators, grids
    ink: str  # titles and values
    text: str  # body and secondary text: no text color is lighter than this
    primary: str  # fill of primary buttons
    on_primary: str  # text on primary buttons
    link: str  # links, active tab, selection, focus, LED Operational
    on_link: str  # text on a ``link`` fill (selected table rows)
    link_on_surface: str  # links inside ``surface`` containers
    accent: str  # LED Pre-op, warning badges; never text
    on_accent: str  # text on an ``accent`` badge
    error: str  # errors, SDO aborts, EMCY, bus-off
    error_bg: str  # background of EMCY rows in the bus monitor
    badge: str  # fill of neutral badges (RUMIA)
    on_badge: str
    statusbar: str
    on_statusbar: str
    statusbar_muted: str  # secondary text in the status bar
    tooltip: str
    on_tooltip: str

    def colors(self) -> dict[str, str]:
        """All roles as ``{role: hex}``."""
        return {f.name: getattr(self, f.name) for f in fields(self)}


# Values decided on 2 October 2026 (mockup screen 8).
LIGHT = Palette(
    bg="#FFFFFF",
    surface="#F4F8F8",
    line="#DDE6E6",
    ink="#0B2326",
    text="#3E5357",
    primary="#048087",
    on_primary="#FFFFFF",
    link="#048087",
    on_link="#FFFFFF",
    # Teal on surface is 4.42:1, below 4.5: links on surface are ink and underlined.
    link_on_surface="#0B2326",
    accent="#E7A92F",
    on_accent="#0B2326",
    error="#B3261E",
    error_bg="#FCEEED",
    badge="#0B2326",
    on_badge="#FFFFFF",
    statusbar="#0B2326",
    on_statusbar="#FFFFFF",
    statusbar_muted="#68B3B3",
    tooltip="#0B2326",
    on_tooltip="#FFFFFF",
)

DARK = Palette(
    bg="#0B2326",
    surface="#12333A",
    line="#2A5156",
    ink="#FFFFFF",
    text="#B7C7C9",
    primary="#048087",
    on_primary="#FFFFFF",
    # Teal on Deep Ink is 3.46:1: in the dark theme links and selection are Sky Blue.
    link="#68B3B3",
    on_link="#0B2326",
    link_on_surface="#68B3B3",
    accent="#E7A92F",
    on_accent="#0B2326",
    error="#FF8A80",
    # Provisional: not yet fixed by the brand guidelines.
    error_bg="#4A2B2E",
    badge="#2A5156",
    on_badge="#FFFFFF",
    statusbar="#061719",
    on_statusbar="#FFFFFF",
    statusbar_muted="#68B3B3",
    tooltip="#12333A",
    on_tooltip="#FFFFFF",
)

PALETTES: dict[ThemeName, Palette] = {ThemeName.LIGHT: LIGHT, ThemeName.DARK: DARK}


@dataclass(frozen=True)
class Series:
    """Style of one line in the plots: the yellow is never used for lines."""

    color: str
    dashed: bool


SERIES: dict[ThemeName, tuple[Series, ...]] = {
    ThemeName.LIGHT: (Series("#048087", False), Series("#3E5357", True), Series("#0B2326", False)),
    ThemeName.DARK: (Series("#68B3B3", False), Series("#B7C7C9", True), Series("#FFFFFF", False)),
}


@dataclass(frozen=True)
class Typography:
    """Font families (bundled, SIL OFL) and sizes in pixels."""

    title_family: str = "Archivo SemiExpanded"  # Archivo at 112.5% width
    sans_family: str = "IBM Plex Sans"
    mono_family: str = "IBM Plex Mono"
    page_title_px: int = 20
    section_title_px: int = 16
    body_px: int = 13
    small_px: int = 12
    mono_px: int = 13
    label_px: int = 11  # uppercase mono section labels
    label_spacing_em: float = 0.08
    badge_px: int = 10
    value_px: int = 26  # large live values in tiles
    unit_px: int = 14  # unit next to a large value


@dataclass(frozen=True)
class Metrics:
    """Radii, heights and spacing in pixels."""

    radius_button: int = 6
    radius_card: int = 10
    radius_tile: int = 8
    radius_badge: int = 3
    badge_padding: tuple[int, int] = (2, 6)  # vertical, horizontal
    button_large: int = 40  # main actions at the bottom of a panel
    button: int = 36
    button_bar: int = 32  # buttons and inputs in toolbars
    button_compact: int = 28  # side panel
    input_height: int = 32
    callout_bar: int = 3
    statusbar_height: int = 28
    tab_indicator: int = 2
    led: int = 8
    card_icon: int = 32
    icon: int = 16
    indicator: int = 16  # check boxes
    arrow: int = 12  # combo and spin box arrows
    scrollbar: int = 10
    space_xs: int = 4
    space_s: int = 8
    space_m: int = 12
    space_l: int = 16
    space_xl: int = 20
    space_xxl: int = 24


TYPOGRAPHY = Typography()
METRICS = Metrics()


@dataclass(frozen=True)
class Theme:
    """Everything the style sheet and the widgets need for one theme."""

    name: ThemeName
    palette: Palette
    series: tuple[Series, ...]
    typography: Typography = TYPOGRAPHY
    metrics: Metrics = METRICS


THEMES: dict[ThemeName, Theme] = {
    name: Theme(name, PALETTES[name], SERIES[name]) for name in ThemeName
}


@dataclass(frozen=True)
class ContrastPair:
    """A foreground role drawn on a background role, with its minimum ratio."""

    fg: str
    bg: str
    minimum: float
    use: str
    # Reason the pair is accepted below ``minimum``; ``None`` means it must pass.
    waiver: str | None = None


TEXT_MIN = 4.5
GRAPHIC_MIN = 3.0

# Every text/background combination the style sheet produces (UI-COL-02).
TEXT_PAIRS: tuple[ContrastPair, ...] = (
    ContrastPair("text", "bg", TEXT_MIN, "body text"),
    ContrastPair("text", "surface", TEXT_MIN, "body text in panels and alternate rows"),
    ContrastPair("ink", "bg", TEXT_MIN, "titles and values"),
    ContrastPair("ink", "surface", TEXT_MIN, "titles and values in panels"),
    ContrastPair("text", "line", TEXT_MIN, "disabled primary buttons, pressed buttons"),
    ContrastPair("link", "bg", TEXT_MIN, "links, active tab"),
    ContrastPair("link_on_surface", "surface", TEXT_MIN, "links in panels"),
    ContrastPair("on_primary", "primary", TEXT_MIN, "primary buttons"),
    ContrastPair("on_link", "link", TEXT_MIN, "selected rows"),
    ContrastPair("on_accent", "accent", TEXT_MIN, "warning badges"),
    ContrastPair("on_badge", "badge", TEXT_MIN, "RUMIA badge"),
    ContrastPair("error", "bg", TEXT_MIN, "error callout title"),
    ContrastPair("error", "surface", TEXT_MIN, "error text in panels"),
    ContrastPair("error", "error_bg", TEXT_MIN, "EMCY row"),
    ContrastPair("text", "error_bg", TEXT_MIN, "EMCY row"),
    ContrastPair("ink", "error_bg", TEXT_MIN, "EMCY row"),
    ContrastPair("on_statusbar", "statusbar", TEXT_MIN, "status bar"),
    ContrastPair("statusbar_muted", "statusbar", TEXT_MIN, "status bar, last event"),
    ContrastPair("on_tooltip", "tooltip", TEXT_MIN, "tooltips"),
)

_LED_WAIVER = (
    "Pre-op LED without border, decided on 2 October 2026: the state is always "
    "written next to the LED (UI-COL-04)."
)

# Icons, LEDs, focus rings and plot lines (UI-COL-02, 3:1). Borders in ``line``
# are decorative separators and are not listed.
GRAPHIC_PAIRS: tuple[ContrastPair, ...] = (
    ContrastPair("link", "bg", GRAPHIC_MIN, "LED Operational, focus ring"),
    ContrastPair("link", "surface", GRAPHIC_MIN, "LED Operational in panels"),
    ContrastPair("text", "bg", GRAPHIC_MIN, "LED Stopped, icons"),
    ContrastPair("text", "surface", GRAPHIC_MIN, "LED Stopped, icons in panels"),
    ContrastPair("error", "bg", GRAPHIC_MIN, "LED Absent, error callout bar"),
    ContrastPair("error", "surface", GRAPHIC_MIN, "LED Absent in panels"),
    ContrastPair("link", "statusbar", GRAPHIC_MIN, "bus LED in the status bar"),
    ContrastPair("on_statusbar", "statusbar", GRAPHIC_MIN, "bus LED 'not connected'"),
    ContrastPair("accent", "bg", GRAPHIC_MIN, "LED Pre-op", _LED_WAIVER),
    ContrastPair("accent", "surface", GRAPHIC_MIN, "LED Pre-op in panels", _LED_WAIVER),
)
