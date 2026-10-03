"""Demo mode: banner always visible, simulator started and stopped (FR-CON-06)."""

from collections.abc import Iterator

import can
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from rumia_configurator.core import paths
from rumia_configurator.core.settings import SettingsStore
from rumia_configurator.core.simulator import SimulatedNode, Simulator
from rumia_configurator.gui import app as app_module
from rumia_configurator.gui.i18n import LanguageManager
from rumia_configurator.gui.main_window import MainWindow
from rumia_configurator.gui.theme import manager as theme_module
from rumia_configurator.gui.theme.manager import ThemeManager, install_theme

DEMO_NODES = [("Smart IMU", 29), ("INCLI Sense", 10)]


@pytest.fixture
def managers(qapp: QApplication) -> Iterator[tuple[ThemeManager, LanguageManager]]:
    theme_manager, _fonts = install_theme(qapp, "light")
    language_manager = LanguageManager(qapp, "en")
    yield theme_manager, language_manager
    language_manager.uninstall()
    qapp.setStyleSheet("")
    theme_module._reset_for_tests()


def make_window(
    qtbot: QtBot,
    managers: tuple[ThemeManager, LanguageManager],
    demo_nodes: list[tuple[str, int]] | None,
) -> MainWindow:
    theme_manager, language_manager = managers
    store = SettingsStore(paths.settings_path())
    window = MainWindow(store, store.load().settings, theme_manager, language_manager, demo_nodes)
    qtbot.addWidget(window)
    window.show()
    return window


def test_banner_names_the_simulated_nodes_in_both_languages(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    window = make_window(qtbot, managers, DEMO_NODES)
    banner = window.demo_banner
    assert banner is not None and banner.isVisible()
    assert banner.callout.title_label.text() == "Demo mode"
    assert "Smart IMU 29, INCLI Sense 10" in banner.callout.text_label.text()

    window.set_language("it")
    QApplication.processEvents()
    assert banner.callout.title_label.text() == "Modalità demo"
    assert "Smart IMU 29, INCLI Sense 10" in banner.callout.text_label.text()


def test_no_banner_without_demo(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    window = make_window(qtbot, managers, None)
    assert window.demo_banner is None


def test_start_demo_runs_the_simulator_until_quit(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    def private_channel(nodes: list[SimulatedNode]) -> Simulator:
        return Simulator(nodes, channel="test-demo-start")

    monkeypatch.setattr(app_module, "Simulator", private_channel)
    simulator = app_module._start_demo(qapp)
    assert simulator is not None and simulator.running
    assert [n.node_id for n in simulator.nodes] == [29, 10]
    qapp.aboutToQuit.emit()
    assert not simulator.running
    qapp.aboutToQuit.disconnect(simulator.stop)


def test_demo_start_failure_is_reported(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No silent fallback: a failure reaches the user with cause and remedy."""

    def fail(self: Simulator) -> None:
        raise can.CanError("bus unavailable")

    messages: list[str] = []
    monkeypatch.setattr(Simulator, "start", fail)
    monkeypatch.setattr(QMessageBox, "critical", lambda parent, title, text: messages.append(text))
    assert app_module._start_demo(qapp) is None
    assert len(messages) == 1
    assert "bus unavailable" in messages[0]
    assert "--demo" in messages[0]
