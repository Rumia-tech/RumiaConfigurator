"""NMT commands in the window: confirmation, sending, result (FR-NET-04, NFR-REL-03)."""

from collections.abc import Iterator

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from rumia_configurator.core import paths
from rumia_configurator.core.network import NmtCommand
from rumia_configurator.core.settings import SettingsStore
from rumia_configurator.core.simulator import Simulator
from rumia_configurator.gui import dialogs
from rumia_configurator.gui.connection import ConnectionController
from rumia_configurator.gui.i18n import LanguageManager
from rumia_configurator.gui.main_window import MainWindow
from rumia_configurator.gui.theme import manager as theme_module
from rumia_configurator.gui.theme.manager import ThemeManager, install_theme

Asked = list[tuple[str, str, str, str, str]]


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
    main.show()
    return main


def answer(monkeypatch: pytest.MonkeyPatch, confirm: bool) -> Asked:
    """Replace the confirmation dialog: record the question, give ``confirm``."""
    asked: Asked = []

    def fake(
        parent: object, title: str, what: str, consequences: str, advice: str, button: str
    ) -> bool:
        asked.append((title, what, consequences, advice, button))
        return confirm

    monkeypatch.setattr(dialogs, "confirm_action", fake)
    return asked


def connect_demo(qtbot: QtBot, window: MainWindow, simulator: Simulator, channel: str) -> None:
    for node in simulator.nodes:
        node.store(0x1017, 0, 100)  # faster heartbeat: faster checks
    window.start_demo_connection(channel)
    panel = window.node_panel
    qtbot.waitUntil(
        lambda: (
            sorted(panel.rows) == [10, 29]
            and all(r.info and r.info.identity_read for r in panel.rows.values())
        ),
        timeout=4000,
    )


def nmt_frames_sent(window: MainWindow) -> list[bytes]:
    traffic = window.connection.service.traffic
    assert traffic is not None
    frames = traffic.latest(2000)
    return [bytes(f["data"][:2]) for f in frames if f["can_id"] == 0 and f["flags"] & 0x08]


def test_network_buttons_follow_the_connection(
    qtbot: QtBot, window: MainWindow, simulator: Simulator, sim_channel: str
) -> None:
    panel = window.node_panel
    buttons = (panel.start_button, panel.preop_button, panel.reset_button)
    assert not any(b.isEnabled() for b in buttons)
    assert not window.workspace.nmt_button.isEnabled()
    connect_demo(qtbot, window, simulator, sim_channel)
    assert all(b.isEnabled() for b in buttons)
    assert not window.workspace.nmt_button.isEnabled()  # no node selected yet
    panel.select(29)
    assert window.workspace.nmt_button.isEnabled()


def test_cancelled_reset_sends_nothing(
    qtbot: QtBot,
    window: MainWindow,
    simulator: Simulator,
    sim_channel: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Acceptance: without confirmation nothing reaches the bus."""
    connect_demo(qtbot, window, simulator, sim_channel)
    asked = answer(monkeypatch, confirm=False)
    window.node_panel.reset_button.click()
    qtbot.wait(300)
    assert len(asked) == 1
    title, what, consequences, _advice, button = asked[0]
    assert title == "Reset node · Whole network"
    assert what == "Reset every node of the network?"
    assert "also those not in the list" in consequences
    assert button == "Reset all nodes"
    assert nmt_frames_sent(window) == []


def test_confirmed_preop_to_the_network_is_sent_and_checked(
    qtbot: QtBot,
    window: MainWindow,
    simulator: Simulator,
    sim_channel: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connect_demo(qtbot, window, simulator, sim_channel)
    answer(monkeypatch, confirm=True)
    window.node_panel.preop_button.click()
    qtbot.waitUntil(
        lambda: (
            window.status.last_event.text()
            == "Whole network: Pre-operational confirmed by 2 of 2 nodes"
        ),
        timeout=4000,
    )
    assert nmt_frames_sent(window) == [b"\x80\x00"]
    panel = window.node_panel
    qtbot.waitUntil(lambda: panel.rows[29].led.label.text() == "Pre-operational", timeout=2000)
    assert panel.rows[29].led.state == "preop"
    assert not window.workspace.notice.isVisible()


def test_start_from_the_node_menu_needs_no_confirmation(
    qtbot: QtBot,
    window: MainWindow,
    simulator: Simulator,
    sim_channel: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connect_demo(qtbot, window, simulator, sim_channel)
    asked = answer(monkeypatch, confirm=False)
    window.node_panel.select(29)
    window.workspace.nmt_menu.command_actions[NmtCommand.STOP].trigger()
    qtbot.waitUntil(
        lambda: window.status.last_event.text() == "Node 29: Stop confirmed by the heartbeat",
        timeout=4000,
    )
    assert asked == []
    assert nmt_frames_sent(window) == [b"\x02\x1d"]


def test_reset_of_one_node_asks_first(
    qtbot: QtBot,
    window: MainWindow,
    simulator: Simulator,
    sim_channel: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connect_demo(qtbot, window, simulator, sim_channel)
    asked = answer(monkeypatch, confirm=True)
    row = window.node_panel.rows[10]
    menu = row.nmt_menu()  # the menu of the right click
    assert menu.command_actions[NmtCommand.RESET_COMMUNICATION].text() == "Reset communication…"
    menu.command_actions[NmtCommand.RESET_COMMUNICATION].trigger()
    assert asked[0][1] == "Reset the communication of node 10?"
    qtbot.waitUntil(
        lambda: (
            window.status.last_event.text()
            == "Node 10: Reset communication confirmed by the heartbeat"
        ),
        timeout=4000,
    )
    assert nmt_frames_sent(window) == [b"\x82\x0a"]


def test_node_that_does_not_answer_shows_a_warning(
    qtbot: QtBot,
    window: MainWindow,
    simulator: Simulator,
    sim_channel: str,
) -> None:
    connect_demo(qtbot, window, simulator, sim_channel)
    window.node_panel.select(29)
    simulator.node(29).stop_heartbeat()
    window.request_nmt(29, NmtCommand.START)
    qtbot.waitUntil(lambda: window.workspace.notice.isVisible(), timeout=4000)
    assert window.workspace.notice.title_label.text() == "Start not confirmed by node 29"
    assert window.status.last_event.text() == "Node 29: no heartbeat after Start"


def test_confirmation_dialog_defaults_to_cancel(qapp: QApplication) -> None:
    box, confirm = dialogs.build_confirmation(
        None, "Reset node · Node 29", "Reset node 29?", "It restarts.", "Be safe.", "Reset"
    )
    assert box.defaultButton() is box.button(QMessageBox.StandardButton.Cancel)
    assert box.escapeButton() is box.button(QMessageBox.StandardButton.Cancel)
    assert confirm.text() == "Reset"
    assert box.text() == "Reset node 29?"
    assert box.informativeText() == "It restarts.\n\nBe safe."
    assert box.icon() == QMessageBox.Icon.Warning
    box.deleteLater()
