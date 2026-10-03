"""Connection in the main window: adapter, bitrate, Connect/Disconnect, errors (T1.1)."""

from collections.abc import Iterator

import can
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from rumia_configurator.core import paths
from rumia_configurator.core.connection import (
    AdapterInfo,
    ConnectionFailure,
    ConnectionService,
    ConnectionState,
    ControllerStatus,
    ErrorKind,
)
from rumia_configurator.core.settings import SettingsStore
from rumia_configurator.core.simulator import Simulator
from rumia_configurator.gui.connection import ConnectionController, failure_message
from rumia_configurator.gui.i18n import LanguageManager
from rumia_configurator.gui.main_window import MainWindow
from rumia_configurator.gui.theme import manager as theme_module
from rumia_configurator.gui.theme.manager import ThemeManager, install_theme

RUMIA = AdapterInfo("slcan", "COM5", "Rumia CAN Interface", "rumia", 0x17D0, 0x118E, "R1")
OTHER = AdapterInfo("slcan", "COM3", "Bluetooth link", "serial")


def slcan_answers(channel: str) -> bytes:
    """Serial probe: the port answers like the Rumia interface firmware."""
    return b"b158aa7-dirty \r"


class AnsweringBus(can.BusABC):
    """An SLCAN adapter that opens and receives nothing."""

    def __init__(self, channel: str = "COM5", **_: object) -> None:
        super().__init__(channel=channel)
        self.channel_info = channel

    def send(self, msg: can.Message, timeout: float | None = None) -> None:
        pass

    def _recv_internal(self, timeout: float | None) -> tuple[None, bool]:
        return None, False


@pytest.fixture
def managers(qapp: QApplication) -> Iterator[tuple[ThemeManager, LanguageManager]]:
    theme_manager, _fonts = install_theme(qapp, "light")
    language_manager = LanguageManager(qapp, "en")
    yield theme_manager, language_manager
    language_manager.uninstall()
    qapp.setStyleSheet("")
    theme_module._reset_for_tests()


@pytest.fixture
def messages(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Error dialogs shown, as (title, text), instead of opening them."""
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        QMessageBox, "critical", lambda parent, title, text: shown.append((title, text))
    )
    return shown


def make_window(
    qtbot: QtBot,
    managers: tuple[ThemeManager, LanguageManager],
    service: ConnectionService | None = None,
    adapters: list[AdapterInfo] | None = None,
    demo: bool = False,
) -> MainWindow:
    theme_manager, language_manager = managers
    store = SettingsStore(paths.settings_path())
    found = adapters if adapters is not None else []
    controller = ConnectionController(service, lister=lambda: found)
    window = MainWindow(
        store,
        store.load().settings,
        theme_manager,
        language_manager,
        [("Smart IMU", 29), ("INCLI Sense", 10)] if demo else None,
        controller,
    )
    qtbot.addWidget(window)
    window.show()
    return window


def wait_state(qtbot: QtBot, window: MainWindow, state: ConnectionState) -> None:
    qtbot.waitUntil(lambda: window.top_bar._state == state, timeout=3000)


def test_rumia_adapter_is_proposed_first(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    window = make_window(qtbot, managers, adapters=[RUMIA, OTHER])
    qtbot.waitUntil(lambda: window.top_bar.connect_button.isEnabled(), timeout=3000)
    assert window.top_bar.adapter.text() == "Rumia USB-CAN · COM5"
    menu = [a.text() for a in window.top_bar.adapter_menu.actions() if a.text()]
    assert menu[0] == "RUMIA · Rumia CAN Interface · COM5 (17D0:118E)"
    assert menu[-2:] == ["Refresh list", "Other adapter…"]
    assert window.status.adapter.text() == "Rumia USB-CAN · COM5"


def test_bitrate_menu_has_the_cia_values(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    window = make_window(qtbot, managers)
    values = [a.text() for a in window.top_bar.bitrate_menu.actions()]
    assert values == [f"{v} kbit/s" for v in (10, 20, 50, 125, 250, 500, 800, 1000)]
    window.top_bar.bitrate_menu.actions()[5].trigger()
    assert window.top_bar.bitrate.text() == "500 kbit/s"
    assert window.status.bitrate.text() == "500 kbit/s"


def test_connect_then_disconnect_saves_the_adapter(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    service = ConnectionService(lambda **_: AnsweringBus(), "Windows", slcan_answers)
    window = make_window(qtbot, managers, service, adapters=[RUMIA])
    qtbot.waitUntil(lambda: window.top_bar.connect_button.isEnabled(), timeout=3000)
    window.select_bitrate(250_000)
    window.top_bar.connect_button.click()
    wait_state(qtbot, window, ConnectionState.CONNECTED)

    top = window.top_bar
    assert top.connect_button.text() == "Disconnect"
    assert top.connection.state == "operational"
    assert not top.adapter.isEnabled() and not top.bitrate.isEnabled()  # locked while connected
    assert window.status.bus.label.text() == "Connected"
    qtbot.waitUntil(lambda: "controller n/a" in window.status.errors.text(), timeout=3000)
    saved = SettingsStore(paths.settings_path()).load().settings.connection
    assert (saved.backend, saved.channel, saved.bitrate) == ("slcan", "COM5", 250_000)

    top.connect_button.click()
    wait_state(qtbot, window, ConnectionState.DISCONNECTED)
    assert top.connect_button.text() == "Connect"
    assert top.adapter.isEnabled()


def test_open_error_shows_what_why_and_what_to_do(
    qtbot: QtBot,
    managers: tuple[ThemeManager, LanguageManager],
    messages: list[tuple[str, str]],
) -> None:
    def busy(channel: str) -> bytes:  # the probe is the first to open the port
        raise OSError(
            "could not open port 'COM5': PermissionError(13, 'Access is denied.', None, 5)"
        )

    service = ConnectionService(lambda **_: AnsweringBus(), "Windows", busy)
    window = make_window(qtbot, managers, service, adapters=[RUMIA])
    qtbot.waitUntil(lambda: window.top_bar.connect_button.isEnabled(), timeout=3000)
    window.top_bar.connect_button.click()
    qtbot.waitUntil(lambda: bool(messages), timeout=3000)

    title, text = messages[0]
    assert title == "Connection failed"
    what, why, todo = text.split("\n\n")
    assert what == "Could not connect to COM5."
    assert "another program" in why
    assert "Close the other program" in todo
    assert window.top_bar.connection.state == "stopped"
    assert window.status.last_event.text() == "Connection failed"
    assert not window.connection.service.is_virtual  # never a silent fallback


def test_demo_mode_connects_to_the_simulator(
    qtbot: QtBot,
    managers: tuple[ThemeManager, LanguageManager],
    simulator: Simulator,
    sim_channel: str,
) -> None:
    window = make_window(qtbot, managers, demo=True)
    window.start_demo_connection(sim_channel)
    wait_state(qtbot, window, ConnectionState.CONNECTED)
    top = window.top_bar
    assert top.adapter.text() == "Virtual bus (demo)"
    assert not top.adapter.isEnabled()
    assert not top.connect_button.isEnabled()  # demo mode stays connected
    assert window.status.adapter.text() == "virtual bus (demo)"
    network = window.connection.service.network
    assert network is not None
    network.scanner.search()
    qtbot.waitUntil(lambda: len(network.scanner.nodes) == 2, timeout=3000)
    # The virtual bus is never saved as the user's adapter.
    assert SettingsStore(paths.settings_path()).load().settings.connection.backend == "slcan"


@pytest.mark.parametrize("language", ["it", "en"])
def test_top_bar_still_fits_when_connected_with_a_long_name(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager], language: str
) -> None:
    long_name = AdapterInfo(
        "slcan", "/dev/serial/by-id/usb-Rumia_CAN_Interface_0123456789", "x", "rumia"
    )
    window = make_window(qtbot, managers, adapters=[long_name])
    window.set_language(language)
    qtbot.waitUntil(lambda: window.top_bar.connect_button.isEnabled(), timeout=3000)
    window.status.set_controller(ControllerStatus("passive", 130, 7, 12345))
    window.status.show_event("Connection failed")
    for state in (ConnectionState.DISCONNECTED, ConnectionState.CONNECTED):  # Disconnect is longer
        window.connection.state_changed.emit(state, None)
        for _ in range(3):
            QApplication.processEvents()
        # UI-LAY-06, with some room left for the next controls of the top bar
        assert window.minimumSizeHint().width() <= 1366 - 20, state
    assert "/dev/serial/by-id" in window.top_bar.adapter.toolTip()


@pytest.mark.parametrize("kind", list(ErrorKind))
def test_every_error_has_three_parts(kind: ErrorKind) -> None:
    failure = ConnectionFailure(kind, "pcan", "PCAN_USBBUS1", "detail text")
    for system in ("Windows", "Linux", "Darwin"):
        title, text = failure_message(failure, system)
        parts = text.split("\n\n")
        assert title
        assert len(parts) == 3 and all(parts), (kind, parts)
        assert "%1" not in text and "%2" not in text and "%3" not in text


def test_lost_adapter_is_reported(
    qtbot: QtBot,
    managers: tuple[ThemeManager, LanguageManager],
    messages: list[tuple[str, str]],
) -> None:
    window = make_window(qtbot, managers)
    failure = ConnectionFailure(ErrorKind.DEVICE_LOST, "slcan", "COM5", "unplugged")
    window.connection.state_changed.emit(ConnectionState.LOST, failure)
    assert window.top_bar.connection.state == "error"
    assert window.top_bar.connection.label.text() == "Adapter lost"
    assert window.status.bus.state == "error"
    assert messages[0][0] == "Connection lost"
