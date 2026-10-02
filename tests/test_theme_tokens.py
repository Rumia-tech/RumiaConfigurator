"""Brand tokens: contrast and palette rules (UI-COL-01, UI-COL-02), no Qt needed."""

import pytest

from rumia_configurator.gui.theme.contrast import contrast_ratio, parse_hex
from rumia_configurator.gui.theme.tokens import (
    GRAPHIC_MIN,
    GRAPHIC_PAIRS,
    TEXT_PAIRS,
    THEMES,
    ContrastPair,
    ThemeName,
)

ALL_THEMES = list(ThemeName)


def _ratio(name: ThemeName, pair: ContrastPair) -> float:
    colors = THEMES[name].palette.colors()
    return contrast_ratio(colors[pair.fg], colors[pair.bg])


def test_contrast_ratio_reference_values() -> None:
    assert contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert contrast_ratio("#FFFFFF", "#FFFFFF") == pytest.approx(1.0)
    # Deep Teal on white, the value quoted in the brand guidelines.
    assert contrast_ratio("#048087", "#FFFFFF") == pytest.approx(4.73, abs=0.01)


def test_parse_hex_rejects_other_formats() -> None:
    for bad in ("048087", "#04808", "#04808G", "rgb(0,0,0)"):
        with pytest.raises(ValueError):
            parse_hex(bad)


@pytest.mark.parametrize("name", ALL_THEMES)
@pytest.mark.parametrize("pair", TEXT_PAIRS, ids=lambda p: f"{p.fg}-on-{p.bg}")
def test_text_pairs_meet_wcag_aa(name: ThemeName, pair: ContrastPair) -> None:
    assert pair.waiver is None, "text pairs cannot be waived"
    ratio = _ratio(name, pair)
    assert ratio >= pair.minimum, f"{name}: {pair.fg} on {pair.bg} ({pair.use}) is {ratio:.2f}:1"


@pytest.mark.parametrize("name", ALL_THEMES)
@pytest.mark.parametrize("pair", GRAPHIC_PAIRS, ids=lambda p: f"{p.fg}-on-{p.bg}")
def test_graphic_pairs_meet_3_to_1_or_are_waived(name: ThemeName, pair: ContrastPair) -> None:
    ratio = _ratio(name, pair)
    if pair.waiver is None:
        assert ratio >= pair.minimum, f"{name}: {pair.fg} on {pair.bg} ({pair.use}) is {ratio:.2f}"


def test_waivers_are_still_needed() -> None:
    """A waiver that is no longer needed must be removed, not kept by habit."""
    for pair in GRAPHIC_PAIRS:
        if pair.waiver is not None:
            assert any(_ratio(name, pair) < pair.minimum for name in ALL_THEMES), pair


@pytest.mark.parametrize("name", ALL_THEMES)
def test_plot_series_are_visible_on_backgrounds(name: ThemeName) -> None:
    theme = THEMES[name]
    for series in theme.series:
        for bg in (theme.palette.bg, theme.palette.surface):
            assert contrast_ratio(series.color, bg) >= GRAPHIC_MIN, (name, series, bg)
        assert series.color != theme.palette.accent, "the yellow is never used for lines"


@pytest.mark.parametrize("name", ALL_THEMES)
def test_all_colors_are_valid_hex(name: ThemeName) -> None:
    for role, color in THEMES[name].palette.colors().items():
        parse_hex(color)  # raises on a malformed value
        assert color == color.upper(), f"{role}: write hex values in upper case"


def test_brand_core_colors_are_in_use() -> None:
    light = THEMES[ThemeName.LIGHT].palette
    assert light.primary == "#048087"  # Deep Teal
    assert light.ink == "#0B2326"  # Deep Ink
    assert light.text == "#3E5357"  # Slate
    assert light.line == "#DDE6E6"
    assert light.surface == "#F4F8F8"
    assert light.accent == "#E7A92F"  # Golden Yellow
    assert THEMES[ThemeName.DARK].palette.link == "#68B3B3"  # Sky Blue


def test_teal_text_only_on_white() -> None:
    """Teal on surface is below 4.5:1, so links on surface must use another color."""
    light = THEMES[ThemeName.LIGHT].palette
    assert contrast_ratio(light.link, light.surface) < 4.5
    assert light.link_on_surface != light.link
