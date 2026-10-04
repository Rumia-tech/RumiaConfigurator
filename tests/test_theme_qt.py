"""Theme applied to Qt: fonts, style sheet, switching and the demo window."""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QMessageLogContext, QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from pytestqt.qtbot import QtBot

from rumia_configurator.core import paths
from rumia_configurator.core.settings import SettingsStore
from rumia_configurator.gui.theme import manager as manager_module
from rumia_configurator.gui.theme.fonts import REQUIRED_FAMILIES, load_fonts
from rumia_configurator.gui.theme.icons import available_icons, icon
from rumia_configurator.gui.theme.manager import ThemeManager, install_theme
from rumia_configurator.gui.theme.qss import STYLE_IMAGES, build_stylesheet
from rumia_configurator.gui.theme.tokens import METRICS, THEMES, ThemeName
from rumia_configurator.gui.theme_demo import ThemeDemoWindow
from rumia_configurator.gui.widgets.brand import ElidedButton, StatusLed, make_button, style_button

GUI_DIR = Path(__file__).resolve().parents[1] / "src" / "rumia_configurator" / "gui"
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")


@pytest.fixture
def manager(qapp: QApplication) -> Iterator[ThemeManager]:
    theme_manager, fonts = install_theme(qapp, "light")
    assert fonts.failures == []
    yield theme_manager
    qapp.setStyleSheet("")
    manager_module._reset_for_tests()


def test_brand_fonts_load_from_the_package(qapp: QApplication) -> None:
    result = load_fonts()
    assert result.failures == []
    assert result.missing_families == []
    assert set(REQUIRED_FAMILIES) <= result.families


@pytest.mark.parametrize("name", list(ThemeName))
def test_stylesheet_uses_only_token_colors(name: ThemeName) -> None:
    theme = THEMES[name]
    allowed = {c.upper() for c in theme.palette.colors().values()}
    used = {c.upper() for c in HEX.findall(build_stylesheet(theme))}
    assert used <= allowed, used - allowed


def test_no_hardcoded_colors_in_gui_code() -> None:
    """Colors live only in the tokens (UI-COL-01)."""
    tokens = GUI_DIR / "theme" / "tokens.py"
    offenders = [
        f"{source.relative_to(GUI_DIR)}: {match}"
        for source in GUI_DIR.rglob("*.py")
        if source != tokens
        for match in HEX.findall(source.read_text(encoding="utf-8"))
    ]
    assert offenders == []


@pytest.fixture
def qt_messages() -> Iterator[list[str]]:
    """Collect the messages Qt prints (qWarning and friends) during a test."""
    messages: list[str] = []

    def handler(_type: QtMsgType, _context: QMessageLogContext, message: str) -> None:
        messages.append(message)

    previous = qInstallMessageHandler(handler)
    yield messages
    qInstallMessageHandler(previous)


def _apply_and_polish(qapp: QApplication, qtbot: QtBot, sheet: str) -> None:
    qapp.setStyleSheet(sheet)
    button = QPushButton("x")
    qtbot.addWidget(button)
    button.show()
    qapp.processEvents()


def test_parse_errors_are_detected(
    qapp: QApplication, qtbot: QtBot, qt_messages: list[str]
) -> None:
    """Guard for the test below: a broken sheet must produce a message."""
    _apply_and_polish(qapp, qtbot, "QPushButton { color: ; {{{ ")
    qapp.setStyleSheet("")
    assert any("Could not parse" in m for m in qt_messages)


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_stylesheet_parses_without_warnings(
    manager: ThemeManager, qtbot: QtBot, qt_messages: list[str], mode: str
) -> None:
    manager.set_mode(mode)
    window = ThemeDemoWindow(manager)
    qtbot.addWidget(window)
    window.show()
    QApplication.processEvents()
    assert not [m for m in qt_messages if "Could not parse" in m]


def test_style_images_are_written(manager: ThemeManager) -> None:
    images = manager._style_images()
    assert set(images) == {name for name, _role in STYLE_IMAGES}
    for path in images.values():
        assert Path(path).is_file()


def test_every_bundled_icon_renders(qapp: QApplication) -> None:
    names = available_icons()
    assert "chevron-down" in names
    for name in names:
        assert not icon(name, "#0B2326").isNull(), name


def test_button_heights_follow_the_tokens(manager: ThemeManager, qtbot: QtBot) -> None:
    expected = {
        "large": METRICS.button_large,
        "normal": METRICS.button,
        "bar": METRICS.button_bar,
        "compact": METRICS.button_compact,
    }
    for size, height in expected.items():
        button = make_button("Button", "primary", size)  # type: ignore[arg-type]
        qtbot.addWidget(button)
        button.show()
        assert button.height() == height, size


def test_elided_button_shortens_only_when_narrow(manager: ThemeManager, qtbot: QtBot) -> None:
    button = ElidedButton(60, 300)
    style_button(button, size="bar", icon="chevron-down")
    qtbot.addWidget(button)
    name = "Rumia USB-CAN · /dev/serial/by-id/usb-Rumia_CAN_Interface_0123456789"
    button.set_full_text(name, "Choose")
    # The minimum never depends on the length of the name: the window does not grow.
    assert button.minimumSizeHint().width() < button.sizeHint().width()
    button.set_full_text("x" * 200, "Choose")
    minimum = button.minimumSizeHint().width()
    button.set_full_text(name, "Choose")
    assert button.minimumSizeHint().width() == minimum
    button.show()
    button.resize(button.sizeHint().width() + 200, button.height())
    assert button.fontMetrics().horizontalAdvance(button.text()) <= 300
    button.resize(minimum, button.height())
    assert "…" in button.text() and button.text() != name
    assert button.toolTip() == name
    button.set_full_text("CANable · COM5", "Choose")
    button.resize(button.sizeHint().width(), button.height())
    assert button.text() == "CANable · COM5"
    assert button.toolTip() == "Choose"
    assert button.full_text() == "CANable · COM5"


def test_mode_switch_changes_theme_without_restart(
    manager: ThemeManager, qapp: QApplication
) -> None:
    seen: list[ThemeName] = []
    manager.changed.connect(lambda theme: seen.append(theme.name))
    manager.set_mode("dark")
    assert manager.theme.name is ThemeName.DARK
    assert THEMES[ThemeName.DARK].palette.surface in qapp.styleSheet()
    manager.set_mode("light")
    assert seen == [ThemeName.DARK, ThemeName.LIGHT]
    with pytest.raises(ValueError):
        manager.set_mode("sepia")


def test_system_mode_follows_the_os_scheme(manager: ThemeManager) -> None:
    from PySide6.QtCore import Qt

    manager.set_mode("system")
    expected = (
        ThemeName.DARK
        if QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        else ThemeName.LIGHT
    )
    assert manager.theme.name is expected


def test_bound_icons_follow_the_theme(manager: ThemeManager, qtbot: QtBot) -> None:
    button = make_button("Scan", icon="refresh-cw")
    qtbot.addWidget(button)
    before = button.icon().pixmap(16).toImage()
    manager.set_mode("dark")
    after = button.icon().pixmap(16).toImage()
    assert before != after


def test_status_led_always_has_text(manager: ThemeManager, qtbot: QtBot) -> None:
    led = StatusLed("preop", "Pre-operational")
    qtbot.addWidget(led)
    assert led.state == "preop"
    assert led.label.text() == "Pre-operational"
    led.set_state("absent", "Absent")
    assert led.state == "absent"
    assert led.label.text() == "Absent"


def test_demo_saves_the_chosen_theme(manager: ThemeManager, qtbot: QtBot) -> None:
    store = SettingsStore(paths.settings_path())
    settings = store.load().settings

    def save(mode: str) -> None:
        settings.theme = mode
        store.save(settings)

    window = ThemeDemoWindow(manager, save)
    qtbot.addWidget(window)
    window.set_mode("dark")
    assert manager.theme.name is ThemeName.DARK
    assert store.load().settings.theme == "dark"
    checked = [b for b in window.mode_buttons.buttons() if b.isChecked()]
    assert [b.property("mode") for b in checked] == ["dark"]


def test_demo_titles_use_the_title_font(manager: ThemeManager, qtbot: QtBot) -> None:
    window = ThemeDemoWindow(manager)
    qtbot.addWidget(window)
    window.show()
    titles = [w for w in window.findChildren(QLabel) if w.property("role") == "title"]
    assert titles
    assert all(t.font().family() == "Archivo SemiExpanded" for t in titles)
    primary = [b for b in window.findChildren(QPushButton) if b.property("variant") == "primary"]
    assert primary
