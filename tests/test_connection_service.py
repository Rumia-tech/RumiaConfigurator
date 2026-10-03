"""Opening and closing the bus (FR-CON-02..05, FR-CON-08).

No hardware: the virtual bus with the simulated nodes, and fake buses for
the failures.
"""

import threading
import time
from collections.abc import Callable
from typing import Any

import can
import pytest

from rumia_configurator.core.connection import (
    ConnectionConfig,
    ConnectionFailure,
    ConnectionService,
    ConnectionState,
    ErrorKind,
)
from rumia_configurator.core.simulator import Simulator

States = list[tuple[ConnectionState, ErrorKind | None]]

# Answer of the CANable firmware used with the Rumia interface to "V": its git hash.
RUMIA_FIRMWARE_ANSWER = b"b158aa7-dirty \r"


def answers(reply: bytes = RUMIA_FIRMWARE_ANSWER) -> Callable[[str], bytes]:
    """A serial probe that gets ``reply`` from the port."""
    return lambda channel: reply


def recording(service: ConnectionService) -> States:
    states: States = []
    service.add_listener(lambda state, failure: states.append((state, failure and failure.kind)))
    return states


class FakeBus(can.BusABC):
    """A bus that opens, receives what a test puts in ``incoming`` and can be "unplugged"."""

    def __init__(self, channel: str = "COM5", **_: Any) -> None:
        super().__init__(channel=channel)
        self.channel_info = f"fake {channel}"
        self.unplugged = threading.Event()
        self.closed = False
        self.sent: list[can.Message] = []
        self.incoming: list[can.Message] = []

    def send(self, msg: can.Message, timeout: float | None = None) -> None:
        self.sent.append(msg)

    def _recv_internal(self, timeout: float | None) -> tuple[can.Message | None, bool]:
        if self.unplugged.is_set():
            raise can.CanOperationError("device reports readiness to read but returned no data")
        if self.incoming:
            return self.incoming.pop(0), False
        time.sleep(min(timeout or 0.01, 0.01))
        return None, False

    def shutdown(self) -> None:
        self.closed = True
        super().shutdown()


# ----- acceptance: an open error is an error, never a virtual bus -----


def test_missing_port_is_an_error_not_a_virtual_bus() -> None:
    service = ConnectionService()
    states = recording(service)
    with pytest.raises(ConnectionFailure) as error:
        service.connect(ConnectionConfig("slcan", "COM_DOES_NOT_EXIST", 500_000))
    assert error.value.kind == ErrorKind.PORT_NOT_FOUND
    assert service.state == ConnectionState.DISCONNECTED
    assert service.network is None
    assert not service.is_virtual
    assert states == [
        (ConnectionState.CONNECTING, None),
        (ConnectionState.DISCONNECTED, ErrorKind.PORT_NOT_FOUND),
    ]


def test_virtual_backend_cannot_be_chosen_as_an_adapter() -> None:
    with pytest.raises(ConnectionFailure) as error:
        ConnectionService().connect(ConnectionConfig("virtual", "rumia-demo", 500_000))
    assert error.value.kind == ErrorKind.INVALID_SETTINGS


@pytest.mark.parametrize(
    ("config", "system", "kind"),
    [
        (ConnectionConfig("socketcan", "can0", 0), "Windows", ErrorKind.NOT_ON_THIS_SYSTEM),
        (ConnectionConfig("slcan", "  ", 500_000), "Windows", ErrorKind.INVALID_SETTINGS),
        (ConnectionConfig("nobody", "x", 500_000), "Windows", ErrorKind.INVALID_SETTINGS),
    ],
)
def test_settings_are_checked_before_opening(
    config: ConnectionConfig, system: str, kind: ErrorKind
) -> None:
    opened: list[dict[str, Any]] = []

    def factory(**options: Any) -> can.BusABC:
        opened.append(options)
        return FakeBus()

    with pytest.raises(ConnectionFailure) as error:
        ConnectionService(factory, system).connect(config)
    assert error.value.kind == kind
    assert opened == []


# ----- SLCAN check -----


@pytest.mark.parametrize("reply", [b"", b"V\r"], ids=["silent", "echo"])
def test_serial_port_without_slcan_adapter_is_refused(reply: bytes) -> None:
    opened: list[dict[str, Any]] = []

    def factory(**options: Any) -> can.BusABC:
        opened.append(options)
        return FakeBus()

    service = ConnectionService(factory, "Windows", answers(reply))
    with pytest.raises(ConnectionFailure) as error:
        service.connect(ConnectionConfig("slcan", "COM5", 500_000))
    assert error.value.kind == ErrorKind.NOT_AN_ADAPTER
    assert opened == []  # python-can never opened the port
    assert service.state == ConnectionState.DISCONNECTED


@pytest.mark.parametrize(
    "reply",
    [RUMIA_FIRMWARE_ANSWER, b"V1013\r", b"\a"],
    ids=["rumia-git-hash", "standard-version", "bell"],
)
def test_any_slcan_answer_is_accepted(reply: bytes) -> None:
    service = ConnectionService(lambda **_: FakeBus(), "Windows", answers(reply))
    service.connect(ConnectionConfig("slcan", "COM5", 500_000))
    assert service.state == ConnectionState.CONNECTED
    service.disconnect()


def test_busy_port_is_found_by_the_probe() -> None:
    def busy(channel: str) -> bytes:
        raise OSError(f"could not open port '{channel}': PermissionError(13, 'Access is denied.')")

    service = ConnectionService(lambda **_: FakeBus(), "Windows", busy)
    with pytest.raises(ConnectionFailure) as error:
        service.connect(ConnectionConfig("slcan", "COM5", 500_000))
    assert error.value.kind == ErrorKind.PORT_BUSY


def test_slcan_adapter_opens_with_the_bitrate() -> None:
    options: dict[str, Any] = {}
    bus = FakeBus()

    def factory(**kwargs: Any) -> can.BusABC:
        options.update(kwargs)
        return bus

    service = ConnectionService(factory, "Windows", answers())
    service.connect(ConnectionConfig("slcan", "COM5", 250_000))
    try:
        assert options == {"interface": "slcan", "channel": "COM5", "bitrate": 250_000}
        assert service.state == ConnectionState.CONNECTED
        assert service.network is not None
        assert service.config == ConnectionConfig("slcan", "COM5", 250_000)
    finally:
        service.disconnect()
    assert bus.closed


def test_socketcan_gets_no_bitrate() -> None:
    options: dict[str, Any] = {}

    def factory(**kwargs: Any) -> can.BusABC:
        options.update(kwargs)
        return FakeBus("can0")

    service = ConnectionService(factory, "Linux")
    service.connect(ConnectionConfig("socketcan", "can0", 500_000))
    service.disconnect()
    assert "bitrate" not in options


def test_one_bus_at_a_time() -> None:
    service = ConnectionService(lambda **_: FakeBus(), "Windows", answers())
    service.connect(ConnectionConfig("slcan", "COM5", 500_000))
    try:
        with pytest.raises(ConnectionFailure) as error:
            service.connect(ConnectionConfig("slcan", "COM6", 500_000))
        assert error.value.kind == ErrorKind.ALREADY_CONNECTED
        assert service.config is not None and service.config.channel == "COM5"
    finally:
        service.disconnect()


# ----- virtual bus with the simulated nodes -----


def test_virtual_bus_finds_the_simulated_nodes(simulator: Simulator, sim_channel: str) -> None:
    service = ConnectionService()
    states = recording(service)
    service.connect_virtual(sim_channel)
    assert service.is_virtual
    network = service.network
    assert network is not None
    network.scanner.search()
    deadline = time.monotonic() + 2
    while len(network.scanner.nodes) < 2 and time.monotonic() < deadline:
        time.sleep(0.05)
    assert sorted(network.scanner.nodes) == [10, 29]

    service.disconnect()
    service.disconnect()  # idempotent
    assert service.network is None
    assert [s for s, _ in states] == [
        ConnectionState.CONNECTING,
        ConnectionState.CONNECTED,
        ConnectionState.DISCONNECTED,
    ]


# ----- lost adapter and controller state -----


def test_unplugged_adapter_is_reported_as_lost() -> None:
    bus = FakeBus()
    service = ConnectionService(lambda **_: bus, "Windows", answers())
    states = recording(service)
    service.connect(ConnectionConfig("slcan", "COM5", 500_000))
    bus.unplugged.set()
    deadline = time.monotonic() + 2
    while not bus.closed and time.monotonic() < deadline:
        time.sleep(0.02)
    assert service.state == ConnectionState.LOST
    assert states[-1] == (ConnectionState.LOST, ErrorKind.DEVICE_LOST)
    assert bus.closed  # closed by the service, no thread left reading
    assert service.network is None
    service.disconnect()
    assert service.state == ConnectionState.DISCONNECTED


def test_error_frames_give_counters_and_state() -> None:
    bus = FakeBus()
    service = ConnectionService(lambda **_: bus, "Windows", answers())
    service.connect(ConnectionConfig("slcan", "COM5", 500_000))
    try:
        assert service.controller_status().state is None  # slcan does not report it
        bus.incoming.append(
            can.Message(
                arbitration_id=0x204,  # controller problem + counters
                is_error_frame=True,
                data=[0, 0x20, 0, 0, 0, 0, 130, 7],
            )
        )
        deadline = time.monotonic() + 2
        while service.controller_status().error_frames == 0 and time.monotonic() < deadline:
            time.sleep(0.02)
        status = service.controller_status()
        assert status.error_frames == 1
        assert (status.tx_errors, status.rx_errors) == (130, 7)
        assert status.state == "passive"

        bus.incoming.append(can.Message(arbitration_id=0x040, is_error_frame=True, data=[0] * 8))
        deadline = time.monotonic() + 2
        while service.controller_status().state != "bus-off" and time.monotonic() < deadline:
            time.sleep(0.02)
        assert service.controller_status().state == "bus-off"
    finally:
        service.disconnect()


def test_status_is_empty_when_disconnected() -> None:
    status = ConnectionService().controller_status()
    assert status.state is None and status.tx_errors is None and status.error_frames == 0
