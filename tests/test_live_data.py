"""From the receive buffer to the interface at 30 Hz (NFR-PER-03, FR-CON-04)."""

import time
from collections.abc import Iterator

import can
import canopen
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from rumia_configurator.core import paths
from rumia_configurator.core.connection import ConnectionService, ConnectionState
from rumia_configurator.core.settings import SettingsStore
from rumia_configurator.core.simulator import Simulator
from rumia_configurator.core.traffic import FLAG_TX, TrafficStats
from rumia_configurator.gui.connection import ConnectionController
from rumia_configurator.gui.i18n import LanguageManager
from rumia_configurator.gui.live import LiveData
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


def test_frames_reach_the_gui_within_100_ms(
    qtbot: QtBot, simulator: Simulator, sim_channel: str
) -> None:
    service = ConnectionService()
    service.connect_virtual(sim_channel)
    live = LiveData(service)
    batches: list[np.ndarray] = []
    stats: list[TrafficStats] = []
    live.frames_received.connect(batches.append)
    live.stats_updated.connect(stats.append)
    live.start()
    try:
        before = service.traffic.written if service.traffic else 0
        qtbot.waitUntil(lambda: service.traffic is not None and service.traffic.written > before)
        arrived = time.monotonic()
        qtbot.waitUntil(lambda: sum(len(b) for b in batches) > before, timeout=1000)
        assert time.monotonic() - arrived < 0.1
        qtbot.waitUntil(lambda: len(stats) >= 3, timeout=2000)  # one every 500 ms
        assert stats[-1].frames_per_s > 0
    finally:
        live.stop()
        service.disconnect()
    assert stats[-1] == TrafficStats()  # stop() resets the status bar


def test_a_tick_with_5000_frames_per_second_is_fast(qtbot: QtBot, sim_channel: str) -> None:
    """170 new frames per tick (5000 frames/s at 30 Hz) cost well under a frame of 33 ms."""
    service = ConnectionService()
    service.connect_virtual(sim_channel)
    live = LiveData(service)
    try:
        live.start()
        live.stop()
        live.start()
        buffer = service.traffic
        assert buffer is not None
        durations = []
        for _ in range(30):
            for seq in range(170):
                buffer.append(can.Message(arbitration_id=0x181, data=bytes(8), timestamp=seq))
            live.tick()
            durations.append(live.last_tick_ms)
        assert max(durations) < 5.0
    finally:
        live.stop()
        service.disconnect()


def test_frames_sent_by_the_application_are_recorded(
    simulator: Simulator, sim_channel: str
) -> None:
    service = ConnectionService()
    service.connect_virtual(sim_channel)
    try:
        network = service.network
        assert network is not None and service.traffic is not None
        node = canopen.RemoteNode(29, canopen.ObjectDictionary())
        network.add_node(node)
        assert node.sdo.upload(0x1008, 0) == b"Smart IMU"
        frames = service.traffic.latest(100)
        sent = frames[(frames["flags"] & FLAG_TX) != 0]
        assert 0x61D in set(sent["can_id"].tolist())  # SDO request to node 29
        assert service.traffic_stats().total_tx >= 1
    finally:
        service.disconnect()


def test_status_bar_shows_frames_and_load(
    qtbot: QtBot,
    managers: tuple[ThemeManager, LanguageManager],
    simulator: Simulator,
    sim_channel: str,
) -> None:
    theme_manager, language_manager = managers
    store = SettingsStore(paths.settings_path())
    window = MainWindow(
        store,
        store.load().settings,
        theme_manager,
        language_manager,
        [("Smart IMU", 29), ("INCLI Sense", 10)],
        ConnectionController(lister=lambda: []),
    )
    qtbot.addWidget(window)
    published: list[TrafficStats] = []
    window.live.stats_updated.connect(published.append)
    window.start_demo_connection(sim_channel)
    qtbot.waitUntil(lambda: window.live.running, timeout=3000)
    # Wait for a full one-second window after the connection.
    qtbot.waitUntil(lambda: len(published) >= 4, timeout=4000)
    last = published[-1]
    # Smart IMU 2 TPDOs every 500 ms, INCLI Sense 10 per second, two heartbeats: about
    # 16 frames/s. The exact count is tested in test_traffic_stats and test_traffic_load;
    # here: the status bar shows what LiveData published.
    assert 8 <= last.frames_per_s <= 24
    assert last.load_percent is not None
    assert window.status.frames.text() == f"{round(last.frames_per_s)} frames/s"
    assert window.status.load.text() == f"load {last.load_percent:.1f} %"
    window.set_language("it")
    QApplication.processEvents()
    italian = f"{window.status._traffic.load_percent:.1f}".replace(".", ",")
    assert window.status.load.text() == f"carico {italian} %"  # decimal comma in Italian

    window.connection.state_changed.emit(ConnectionState.DISCONNECTED, None)
    assert not window.live.running
    assert window.status.frames.text() == "0 frame/s"


def test_lost_frames_are_shown(
    qtbot: QtBot, managers: tuple[ThemeManager, LanguageManager]
) -> None:
    theme_manager, language_manager = managers
    store = SettingsStore(paths.settings_path())
    window = MainWindow(
        store,
        store.load().settings,
        theme_manager,
        language_manager,
        connection=ConnectionController(lister=lambda: []),
    )
    qtbot.addWidget(window)
    window.status.set_connection(ConnectionState.CONNECTED, "x", 500_000)
    window.status.set_traffic(TrafficStats(frames_per_s=5000, load_percent=55.5, lost=42))
    assert window.status.load.text() == "load 55.5 % · lost 42"
    assert window.status.load.property("error") == "true"
