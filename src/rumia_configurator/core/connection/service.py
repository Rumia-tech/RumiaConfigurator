"""Open and close the CAN bus, one adapter at a time (FR-CON-02..05, FR-CON-08).

:class:`ConnectionService` owns the python-can bus and the
``canopen.Network`` built on it. Opening is blocking (an SLCAN port alone
takes about two seconds), so the interface calls :meth:`ConnectionService.connect`
from a worker thread. Every change of state is reported to the listeners,
together with the :class:`ConnectionFailure` that caused it, if any.

There is no fallback: when an adapter cannot be opened the caller gets the
failure, and the virtual bus is opened only by :meth:`connect_virtual`, which
demo mode and the tests call explicitly.
"""

from __future__ import annotations

import logging
import platform
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

import can
import canopen

from rumia_configurator.core.connection.adapters import BACKENDS
from rumia_configurator.core.connection.errors import (
    ConnectionFailure,
    ErrorKind,
    classify_open_error,
)
from rumia_configurator.core.traffic import (
    DEFAULT_CAPACITY,
    FrameBuffer,
    RecordingNetwork,
    TrafficListener,
    TrafficStats,
    compute_stats,
)

logger = logging.getLogger(__name__)

NOTIFIER_CYCLE = 0.1  # seconds the receive thread blocks; also bounds disconnect()
SLCAN_PROBE_TIMEOUT = 0.5
SLCAN_TTY_BAUDRATE = 115200  # python-can default; USB CDC adapters ignore it
CR = b"\r"  # ends every SLCAN command and answer
BELL = b"\a"  # SLCAN answer to a command it refuses: still an SLCAN adapter

# SocketCAN error frame layout (linux/can/error.h), used by python-can for error frames
CAN_ERR_CRTL = 0x00000004  # controller problems, details in data[1]
CAN_ERR_BUSOFF = 0x00000040
CAN_ERR_CNT = 0x00000200  # TX/RX error counters in data[6] / data[7]
CAN_ERR_CRTL_PASSIVE = 0x10 | 0x20  # RX or TX error passive
CAN_ERR_CRTL_ACTIVE = 0x40  # back to error active

ControllerState = Literal["active", "passive", "bus-off"]


class ConnectionState(StrEnum):
    """Where the connection is."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    LOST = "lost"  # the adapter stopped answering; the bus has been closed


@dataclass(frozen=True)
class ConnectionConfig:
    """What to open: python-can backend, channel and bitrate in bit/s."""

    backend: str
    channel: str
    bitrate: int


@dataclass(frozen=True)
class ControllerStatus:
    """CAN controller health, as far as the adapter tells (FR-CON-08).

    ``None`` means "the adapter does not report it", never a guess.
    """

    state: ControllerState | None = None
    tx_errors: int | None = None
    rx_errors: int | None = None
    error_frames: int = 0


StateListener = Callable[[ConnectionState, ConnectionFailure | None], None]
BusFactory = Callable[..., can.BusABC]
SlcanProbe = Callable[[str], bytes]


def probe_slcan(channel: str, timeout: float = SLCAN_PROBE_TIMEOUT) -> bytes:
    """Send the SLCAN version command ``V`` on the serial port and return the answer.

    Any serial port opens, so an answer is needed to know that an SLCAN
    adapter is on the other side. The format of the answer is not checked:
    firmwares differ (the CANable firmware used with the Rumia interface
    answers with its git hash, python-can expects ``Vhhss``). The CAN channel
    is closed first (``C``), so no CAN frame is mixed with the answer and
    nothing is sent on the CAN bus. Errors opening the port are raised as
    they are and classified by the caller.
    """
    import serial  # pyserial, also used by python-can's slcan backend

    port, _, baud = channel.partition("@")  # python-can accepts "COM5@115200"
    with serial.Serial(port, int(baud) if baud else SLCAN_TTY_BAUDRATE, timeout=timeout) as tty:
        tty.write(b"C" + CR)
        time.sleep(0.05)
        tty.reset_input_buffer()
        tty.write(b"V" + CR)
        deadline = time.monotonic() + timeout
        answer = b""
        while time.monotonic() < deadline and not answer.endswith((CR, BELL)):
            answer += tty.read(tty.in_waiting or 1)
    return answer


class _BusWatcher(can.Listener):
    """Counts error frames and notices when the adapter stops answering."""

    def __init__(self, on_lost: Callable[[Exception], None]) -> None:
        self._on_lost = on_lost
        self._lock = threading.Lock()
        self.error_frames = 0
        self.tx_errors: int | None = None
        self.rx_errors: int | None = None
        self.state: ControllerState | None = None

    def on_message_received(self, msg: can.Message) -> None:
        if not msg.is_error_frame:
            return
        with self._lock:
            self.error_frames += 1
            flags = msg.arbitration_id
            data = bytes(msg.data)
            if flags & CAN_ERR_CNT and len(data) >= 8:
                self.tx_errors, self.rx_errors = data[6], data[7]
            if flags & CAN_ERR_BUSOFF:
                self.state = "bus-off"
            elif flags & CAN_ERR_CRTL and len(data) >= 2:
                if data[1] & CAN_ERR_CRTL_PASSIVE:
                    self.state = "passive"
                elif data[1] & CAN_ERR_CRTL_ACTIVE:
                    self.state = "active"

    def on_error(self, exc: Exception) -> None:
        self._on_lost(exc)

    def stop(self) -> None:
        """Nothing to release."""


class ConnectionService:
    """The one CAN bus of the application.

    ``bus_factory``, ``system`` and ``slcan_probe`` exist for the tests: they
    replace ``can.Bus``, ``platform.system()`` and the serial port check.
    """

    def __init__(
        self,
        bus_factory: BusFactory = can.Bus,
        system: str | None = None,
        slcan_probe: SlcanProbe = probe_slcan,
        buffer_capacity: int = DEFAULT_CAPACITY,
    ) -> None:
        self._bus_factory = bus_factory
        self._buffer_capacity = buffer_capacity
        self._traffic: FrameBuffer | None = None
        self._system = system or platform.system()
        self._slcan_probe = slcan_probe
        self._lock = threading.RLock()
        self._listeners: list[StateListener] = []
        self._state = ConnectionState.DISCONNECTED
        self._config: ConnectionConfig | None = None
        self._network: canopen.Network | None = None
        self._watcher: _BusWatcher | None = None

    # ----- state -----

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def config(self) -> ConnectionConfig | None:
        """What is open, or was open when the connection was lost."""
        return self._config

    @property
    def network(self) -> canopen.Network | None:
        """The ``canopen.Network`` on the open bus; ``None`` when not connected."""
        return self._network if self._state == ConnectionState.CONNECTED else None

    @property
    def traffic(self) -> FrameBuffer | None:
        """Frames of the current connection (kept after it ends, until the next one)."""
        return self._traffic

    def traffic_stats(self, now: float | None = None, lost: int = 0) -> TrafficStats:
        """Frames/s and estimated bus load of the last second (FR-CON-04).

        The load needs the bitrate: it is unknown for SocketCAN, where the
        operating system sets it, and the result has ``load_percent=None``.
        """
        buffer = self._traffic
        config = self._config
        if buffer is None or config is None:
            return TrafficStats()
        backend = BACKENDS.get(config.backend)
        known = config.backend == "virtual" or (backend is not None and backend.needs_bitrate)
        return compute_stats(buffer, config.bitrate if known else None, now, lost=lost)

    @property
    def is_virtual(self) -> bool:
        """True when the open bus is the virtual bus of demo mode."""
        return self._config is not None and self._config.backend == "virtual"

    def add_listener(self, listener: StateListener) -> None:
        """Call ``listener(state, failure)`` at every change; it may run on any thread."""
        self._listeners.append(listener)

    def _set_state(self, state: ConnectionState, failure: ConnectionFailure | None = None) -> None:
        self._state = state
        logger.info("Connection %s%s", state.value, f": {failure}" if failure else "")
        for listener in list(self._listeners):
            try:
                listener(state, failure)
            except Exception:  # a broken listener must not break the connection
                logger.exception("Connection listener failed")

    # ----- open and close -----

    def connect(self, config: ConnectionConfig) -> None:
        """Open ``config``; raises :class:`ConnectionFailure` with the probable cause.

        Blocking: call it from a worker thread, never from the GUI thread.
        """
        backend = BACKENDS.get(config.backend)
        with self._lock:
            self._check_can_connect(config)
            if backend is None:
                raise ConnectionFailure(
                    ErrorKind.INVALID_SETTINGS, config.backend, config.channel, "unknown backend"
                )
            if self._system not in backend.systems:
                raise ConnectionFailure(
                    ErrorKind.NOT_ON_THIS_SYSTEM, config.backend, config.channel, self._system
                )
            if not config.channel.strip():
                raise ConnectionFailure(
                    ErrorKind.INVALID_SETTINGS, config.backend, config.channel, "empty channel"
                )
            options: dict[str, Any] = {"interface": config.backend, "channel": config.channel}
            if backend.needs_bitrate:
                options["bitrate"] = config.bitrate
            self._open(config, options)

    def connect_virtual(self, channel: str, bitrate: int = 1_000_000) -> None:
        """Open the python-can virtual bus on ``channel`` (demo mode and tests only)."""
        config = ConnectionConfig("virtual", channel, bitrate)
        with self._lock:
            self._check_can_connect(config)
            self._open(
                config,
                {"interface": "virtual", "channel": channel, "receive_own_messages": False},
            )

    def _check_can_connect(self, config: ConnectionConfig) -> None:
        if self._state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
            raise ConnectionFailure(
                ErrorKind.ALREADY_CONNECTED, config.backend, config.channel, "one bus at a time"
            )

    def _open(self, config: ConnectionConfig, options: dict[str, Any]) -> None:
        self._config = config
        self._set_state(ConnectionState.CONNECTING)
        bus: can.BusABC | None = None
        try:
            if config.backend == "slcan":
                self._check_slcan_answers(config)
            bus = self._bus_factory(**options)
            traffic = FrameBuffer(self._buffer_capacity)
            network = RecordingNetwork(bus, traffic)
            network.NOTIFIER_CYCLE = NOTIFIER_CYCLE
            network.connect()  # with a bus already set, only starts the notifier
            watcher = _BusWatcher(self._on_bus_error)
            assert network.notifier is not None  # set by connect()
            # The one receive thread feeds the buffer too (NFR-PER-01).
            network.notifier.add_listener(TrafficListener(traffic))
            network.notifier.add_listener(watcher)
        except Exception as exc:
            failure = classify_open_error(exc, config.backend, config.channel, self._system)
            logger.warning("Could not open %s %s: %s", config.backend, config.channel, exc)
            if bus is not None:
                _shutdown_quietly(bus)
            self._set_state(ConnectionState.DISCONNECTED, failure)
            raise failure from exc
        self._network = network
        self._watcher = watcher
        self._traffic = traffic
        self._set_state(ConnectionState.CONNECTED)

    def _check_slcan_answers(self, config: ConnectionConfig) -> None:
        """Any serial port opens: make sure an SLCAN adapter is on the other side."""
        answer = self._slcan_probe(config.channel)
        text = answer.strip(CR + BELL + b"\n ").decode("ascii", "replace")
        if not answer or text == "V":  # silence, or a device that only echoes
            raise ConnectionFailure(
                ErrorKind.NOT_AN_ADAPTER,
                config.backend,
                config.channel,
                f"no answer to the SLCAN version command ({answer!r})",
            )
        logger.info("SLCAN adapter on %s, version %s", config.channel, text or "(not given)")

    def disconnect(self) -> None:
        """Close the bus. Does nothing when nothing is open."""
        with self._lock:
            network = self._network
            self._network = None
            self._watcher = None
            if network is not None:
                _disconnect_quietly(network)
            if self._state != ConnectionState.DISCONNECTED:
                self._set_state(ConnectionState.DISCONNECTED)

    def _on_bus_error(self, exc: Exception) -> None:
        """Receive thread: the adapter stopped answering (unplugged, driver error)."""
        with self._lock:
            if self._state != ConnectionState.CONNECTED or self._config is None:
                return
            network = self._network
            self._network = None
            self._watcher = None
            config = self._config
            failure = ConnectionFailure(
                ErrorKind.DEVICE_LOST,
                config.backend,
                config.channel,
                f"{type(exc).__name__}: {exc}",
            )
            self._set_state(ConnectionState.LOST, failure)
        if network is not None:
            # Close from another thread: the receive thread cannot wait for itself.
            threading.Thread(
                target=_disconnect_quietly, args=(network,), name="can-close", daemon=True
            ).start()

    # ----- controller health (FR-CON-08) -----

    def controller_status(self) -> ControllerStatus:
        """State and error counters of the CAN controller, where the adapter reports them."""
        network = self.network
        watcher = self._watcher
        if network is None or watcher is None:
            return ControllerStatus()
        state = _bus_state(network.bus) or watcher.state
        return ControllerStatus(state, watcher.tx_errors, watcher.rx_errors, watcher.error_frames)


def _bus_state(bus: can.BusABC | None) -> ControllerState | None:
    """``bus.state`` where the backend implements it (PCAN, Kvaser, ...).

    ``BusABC.state`` answers "active" for every backend that does not
    implement it: that would be a guess, so it is used only when overridden.
    """
    if bus is None or type(bus).state is can.BusABC.state:
        return None
    try:
        state = bus.state
    except (NotImplementedError, can.CanError, OSError, AttributeError):
        return None
    if state == can.BusState.ERROR:
        return "bus-off"
    if state == can.BusState.PASSIVE:
        return "passive"
    return "active"


def _shutdown_quietly(bus: can.BusABC) -> None:
    try:
        bus.shutdown()
    except Exception:
        logger.exception("Error while closing the bus")


def _disconnect_quietly(network: canopen.Network) -> None:
    try:
        network.disconnect()
    except Exception:
        logger.exception("Error while closing the bus")
