"""Main window: layout at 1366x768, live language and theme switch, saved layout."""

import base64
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QByteArray, QLocale
from PySide6.QtWidgets import QApplication, QMainWindow, QScrollBar
from pytestqt.qtbot import QtBot

from rumia_configurator.core import paths
from rumia_configurator.core.settings import Settings, SettingsStore
from rumia_configurator.gui.i18n import LanguageManager, resolve_language
from rumia_configurator.gui.main_window import MainWindow
from rumia_configurator.gui.theme import manager as theme_module
from rumia_configurator.gui.theme.manager import ThemeManager, install_theme
from rumia_configurator.gui.theme.tokens import ThemeName

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def managers(qapp: QApplication) -> Iterator[tuple[ThemeManager, LanguageManager]]:
    theme_manager, _fonts = install_theme(qapp, "light")
    language_manager = LanguageManager(qapp, "it")
    yield theme_manager, language_manager
    language_manager.uninstall()
    qapp.setStyleSheet("")
    theme_module._reset_for_tests()


def make_window(
    qtbot: QtBot,
    managers: tuple[ThemeManager, LanguageManager],
    settings: Settings | None = None,
) -> MainWindow:
    theme_manager, language_manager = managers
    store = SettingsStore(paths.settings_path())
    window = MainWindow(store, settings or store.load().settings, theme_manager, language_manager)
    qtbot.addWidget(window)
    return window


def settle(window: MainWindow) -> None:
    """Let Qt deliver the language change and redo the layouts."""
    for _ in range(3):
        QApplication.processEvents()
    window.centralWidget().layout().activate()


@pytest.mark.parametrize("language", ["it", "en"])
def test_fits_1366x768_without_horizontal_scrolling(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager], language: str
) -> None:
    window = make_window(qtbot, managers)
    window.set_language(language)
    window.set_ui_mode("expert")  # the widest tab bar
    window.resize(1366, 768)
    window.show()
    settle(window)
    assert window.minimumSizeHint().width() <= 1366
    assert window.top_bar.minimumSizeHint().width() <= 1366
    assert window.width() == 1366
    scrollbars = [
        bar
        for bar in window.findChildren(QScrollBar)
        if bar.isVisible() and bar.orientation().name == "Horizontal"
    ]
    assert scrollbars == []


def test_language_switch_without_restart(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    window = make_window(qtbot, managers)
    window.show()
    assert window.top_bar.connect_button.text() == "Connetti"
    assert window.workspace.tabs.tabText(0) == "Panoramica"
    assert window.node_panel.title.text() == "RETE · 0 NODI"
    window.set_language("en")
    settle(window)
    assert window.top_bar.connect_button.text() == "Connect"
    assert window.workspace.tabs.tabText(0) == "Overview"
    assert window.node_panel.title.text() == "NETWORK · 0 NODES"
    assert window.top_bar.language_button.text() == "EN"
    assert SettingsStore(paths.settings_path()).load().settings.language == "en"


def test_theme_switch_from_the_menu(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    theme_manager, _ = managers
    window = make_window(qtbot, managers)
    window.top_bar._theme_choices["dark"].trigger()
    assert theme_manager.theme.name is ThemeName.DARK
    assert window.top_bar._theme_choices["dark"].isChecked()
    assert SettingsStore(paths.settings_path()).load().settings.theme == "dark"
    window.top_bar._theme_choices["light"].trigger()
    assert theme_manager.theme.name is ThemeName.LIGHT


def test_base_mode_shows_overview_and_plots_only(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    window = make_window(qtbot, managers)
    window.top_bar.base_button.click()
    assert window.workspace.visible_tabs() == ["overview", "plots"]
    window.top_bar.expert_button.click()
    assert window.workspace.visible_tabs() == [
        "overview",
        "parameters",
        "pdo",
        "plots",
        "monitor",
        "log",
    ]
    assert SettingsStore(paths.settings_path()).load().settings.ui_mode == "expert"


def test_layout_is_saved_and_restored(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    window = make_window(qtbot, managers)
    window.resize(1400, 820)
    window.show()
    window.splitter.setSizes([330, 1070])
    settle(window)
    window.close()
    saved = SettingsStore(paths.settings_path()).load().settings
    assert saved.node_panel_width == 330
    assert saved.window_geometry

    # The offscreen test screen is only 800x600 and Qt fits restored windows
    # into it, so the size is checked through the saved data itself.
    assert QMainWindow().restoreGeometry(QByteArray(base64.b64decode(saved.window_geometry)))
    again = make_window(qtbot, managers)
    again.show()
    settle(again)
    assert again.splitter.sizes()[0] == 330


def test_invalid_saved_geometry_falls_back_to_default(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    window = make_window(qtbot, managers, Settings(window_geometry="not base64!"))
    assert window.size().width() == 1366


def test_disabled_controls_until_connected(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    window = make_window(qtbot, managers)
    for button in (
        window.top_bar.connect_button,
        window.top_bar.adapter,
        window.node_panel.scan_button,
        window.node_panel.reset_button,
    ):
        assert not button.isEnabled()
    assert window.top_bar.connection.state == "stopped"


@pytest.mark.parametrize(
    ("setting", "system", "expected"),
    [
        ("it", "en_US", "it"),
        ("en", "it_IT", "en"),
        ("", "it_IT", "it"),
        ("", "en_GB", "en"),
        ("", "de_DE", "en"),
    ],
)
def test_resolve_language(setting: str, system: str, expected: str) -> None:
    assert resolve_language(setting, QLocale(system)) == expected


def test_translations_are_complete_and_compiled() -> None:
    """Every tr() string is in the .ts files, translated, and the .qm files match."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "i18n.py"), "check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
