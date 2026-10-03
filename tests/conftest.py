"""Shared pytest configuration."""

import os
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import can
import canopen
import pytest

from rumia_configurator.core import app_log, paths
from rumia_configurator.core.simulator import Simulator, default_demo_nodes

# Run Qt headless unless the caller chose a platform plugin explicitly.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def user_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Redirect the per-user folders to a temporary folder for every test.

    Also closes the log handlers afterwards: on Windows an open log file
    cannot be deleted.
    """
    home = tmp_path / "user"
    monkeypatch.setattr(paths, "config_dir", lambda: home / "config")
    monkeypatch.setattr(paths, "log_dir", lambda: home / "logs")
    yield home
    app_log.shutdown_logging()


class FrameRecorder(can.Listener):
    """Keep every frame seen by a network, and wait for the ones a test expects."""

    def __init__(self) -> None:
        self.frames: list[can.Message] = []
        self._changed = threading.Condition()

    def on_message_received(self, msg: can.Message) -> None:
        with self._changed:
            self.frames.append(msg)
            self._changed.notify_all()

    def clear(self) -> None:
        with self._changed:
            self.frames.clear()

    def with_id(self, can_id: int) -> list[can.Message]:
        with self._changed:
            return [frame for frame in self.frames if frame.arbitration_id == can_id]

    def wait_for(
        self, predicate: Callable[[can.Message], bool], timeout: float = 2.0
    ) -> can.Message | None:
        """First recorded frame matching ``predicate``, waiting up to ``timeout`` seconds."""
        deadline = time.monotonic() + timeout
        with self._changed:
            while True:
                for frame in self.frames:
                    if predicate(frame):
                        return frame
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._changed.wait(remaining)


@pytest.fixture
def sim_channel() -> str:
    """A virtual CAN channel used by this test only."""
    return f"test-{uuid.uuid4().hex}"


@pytest.fixture
def recorder() -> FrameRecorder:
    """Frames received by ``app_network`` since the start of the test."""
    return FrameRecorder()


@pytest.fixture
def app_network(sim_channel: str, recorder: FrameRecorder) -> Iterator[canopen.Network]:
    """The application side of the virtual bus; every frame goes to ``recorder``."""
    network = canopen.Network()
    network.NOTIFIER_CYCLE = 0.1  # disconnect() waits up to one cycle
    network.connect(interface="virtual", channel=sim_channel, receive_own_messages=False)
    network.notifier.add_listener(recorder)
    yield network
    network.disconnect()


@pytest.fixture
def simulator(app_network: canopen.Network, sim_channel: str) -> Iterator[Simulator]:
    """The demo nodes (Smart IMU 29, INCLI Sense 10), running on the test channel.

    Started after ``app_network``, so the application sees the boot-up messages.
    """
    with Simulator(default_demo_nodes(), channel=sim_channel) as sim:
        yield sim
