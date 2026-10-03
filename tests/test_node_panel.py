"""Network panel in the main window (UI-LAY-02, acceptance of T1.4)."""

from collections.abc import Iterator

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QScrollBar
from pytestqt.qtbot import QtBot

from rumia_configurator.core import paths
from rumia_configurator.core.connection import ConnectionState
from rumia_configurator.core.settings import SettingsStore
from rumia_configurator.core.simulator import Simulator
from rumia_configurator.gui.connection import ConnectionController
from rumia_configurator.gui.i18n import LanguageManager
from rumia_configurator.gui.main_window import MainWindow
from rumia_configurator.gui.theme import manager as theme_module
from rumia_configurator.gui.theme.manager import ThemeManager, install_theme


@pytest.fixture
def managers(qapp: QApplication) -> Iterator[tuple[ThemeManager, LanguageManager]]:
    theme_manager, _fonts = install_theme(qapp, "light")
    language_manager = LanguageManager(qapp, "en")
    yield theme_manager, language_manager
    language_manager.uninstall()
    qapp.setStyleSheet("")
    theme_module._reset_for_tests()


@pytest.fixture
def window(qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]) -> MainWindow:
    theme_manager, language_manager = managers
    store = SettingsStore(paths.settings_path())
    main = MainWindow(
        store,
        store.load().settings,
        theme_manager,
        language_manager,
        [("Smart IMU", 29), ("INCLI Sense", 10)],
        ConnectionController(lister=lambda: []),
    )
    qtbot.addWidget(main)
    main.resize(1366, 768)
    main.show()
    return main


def connect_demo(qtbot: QtBot, window: MainWindow, channel: str) -> None:
    window.start_demo_connection(channel)
    qtbot.waitUntil(lambda: window.node_panel.scan_button.isEnabled(), timeout=3000)


def test_scan_shows_both_simulated_nodes(
    qtbot: QtBot, window: MainWindow, simulator: Simulator, sim_channel: str
) -> None:
    """Acceptance of T1.4: in demo the panel shows the two nodes with their state."""
    panel = window.node_panel
    assert not panel.scan_button.isEnabled()  # not connected yet
    connect_demo(qtbot, window, sim_channel)
    qtbot.mouseClick(panel.scan_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not panel.scan_button.isEnabled(), timeout=1000)  # Scanning…
    qtbot.waitUntil(
        lambda: (
            sorted(panel.rows) == [10, 29]
            and all(row.info and row.info.identity_read for row in panel.rows.values())
        ),
        timeout=5000,
    )
    qtbot.waitUntil(lambda: panel.scan_button.isEnabled(), timeout=3000)
    assert panel.title.text() == "NETWORK · 2 NODES"  # section labels are upper case
    imu = panel.rows[29]
    assert imu.name_label.text() == "Smart IMU"
    qtbot.waitUntil(lambda: imu.led.label.text() == "Operational", timeout=3000)
    assert imu.led.state == "operational"
    assert imu.detail.text() == "heartbeat 1000 ms"
    assert panel.rows[10].name_label.text() == "INCLI Sense"
    assert window.status.last_event.text() == "Scan finished: 2 nodes"


def test_missing_heartbeat_is_shown_on_the_row_and_in_the_status_bar(
    qtbot: QtBot, window: MainWindow, simulator: Simulator, sim_channel: str
) -> None:
    """Acceptance of T1.4: alarm when a simulated node stops."""
    connect_demo(qtbot, window, sim_channel)
    panel = window.node_panel
    simulator.node(29).store(0x1017, 0, 100)  # shorter period: faster test
    qtbot.waitUntil(lambda: sorted(panel.rows) == [10, 29], timeout=3000)
    qtbot.waitUntil(lambda: panel.rows[29].detail.text() == "heartbeat 100 ms", timeout=3000)

    simulator.node(29).stop_heartbeat()
    row = panel.rows[29]
    qtbot.waitUntil(lambda: row.led.state == "error", timeout=2000)
    assert row.led.label.text().startswith("Heartbeat missing for ")
    assert window.status.last_event.text() == "Node 29: heartbeat missing"
    assert panel.rows[10].led.state == "operational"

    simulator.node(29).resume_heartbeat()
    qtbot.waitUntil(lambda: row.led.state == "operational", timeout=2000)
    assert window.status.last_event.text() == "Node 29: heartbeat back"


def test_selection_shows_the_node_in_the_header(
    qtbot: QtBot, window: MainWindow, simulator: Simulator, sim_channel: str
) -> None:
    connect_demo(qtbot, window, sim_channel)
    panel = window.node_panel
    qtbot.waitUntil(lambda: 10 in panel.rows and 29 in panel.rows, timeout=3000)
    qtbot.mouseClick(panel.rows[29], Qt.MouseButton.LeftButton)
    assert panel.selected == 29
    assert panel.rows[29].property("selected") == "true"
    qtbot.waitUntil(lambda: window.workspace.title.text() == "Smart IMU · node 29", timeout=3000)
    assert "Product code 0x00000000" in window.workspace.subtitle.text()

    panel.rows[29].setFocus()
    qtbot.keyClick(panel, Qt.Key.Key_Up)  # keyboard: up to node 10
    assert panel.selected == 10
    assert panel.rows[29].property("selected") == "false"


def test_disconnecting_empties_the_panel(
    qtbot: QtBot, window: MainWindow, simulator: Simulator, sim_channel: str
) -> None:
    connect_demo(qtbot, window, sim_channel)
    panel = window.node_panel
    qtbot.waitUntil(lambda: len(panel.rows) == 2, timeout=3000)
    window.connection.service.disconnect()
    qtbot.waitUntil(lambda: not panel.rows, timeout=3000)
    assert not panel.scan_button.isEnabled()
    assert panel.empty_title.isVisible()
    assert window.workspace.title.text() == "No node selected"


@pytest.mark.parametrize("language", ["it", "en"])
def test_panel_fits_without_horizontal_scrolling(
    qtbot: QtBot, window: MainWindow, simulator: Simulator, sim_channel: str, language: str
) -> None:
    window.set_language(language)
    connect_demo(qtbot, window, sim_channel)
    panel = window.node_panel
    qtbot.waitUntil(lambda: len(panel.rows) == 2, timeout=3000)
    window.splitter.setSizes([272, 1366 - 272])
    simulator.node(29).stop_heartbeat()  # the longest state text
    qtbot.waitUntil(lambda: panel.rows[29].led.state == "error", timeout=4000)
    QApplication.processEvents()
    bars = [
        bar
        for bar in panel.findChildren(QScrollBar)
        if bar.isVisible() and bar.orientation() == Qt.Orientation.Horizontal
    ]
    assert bars == []
    assert panel.minimumSizeHint().width() <= 272
    assert window.connection.state == ConnectionState.CONNECTED
