"""Qt side of the connection: worker threads, signals and error messages.

:class:`ConnectionController` wraps the :class:`ConnectionService` of
``core``. Opening the bus and listing the adapters can block for seconds,
so they run in a ``QThreadPool`` worker: the GUI thread never touches the bus
(architecture rule 2). The service reports its state from any thread; the
controller turns it into a Qt signal, which Qt delivers in the GUI thread.

:func:`failure_message` gives the three-part message (what happened, why,
what to do) shown for every :class:`ErrorKind`.
"""

from __future__ import annotations

import logging
import platform
from collections.abc import Callable, Sequence

from PySide6.QtCore import (
    QCoreApplication,
    QObject,
    QThreadPool,
    QTimer,
    Signal,
    SignalInstance,
)

from rumia_configurator.core.connection import (
    BACKENDS,
    AdapterInfo,
    ConnectionConfig,
    ConnectionFailure,
    ConnectionService,
    ConnectionState,
    ErrorKind,
    list_adapters,
)

logger = logging.getLogger(__name__)

STATUS_INTERVAL_MS = 1000  # controller state polling (FR-CON-08)
SHUTDOWN_WAIT_MS = 5000  # an SLCAN open in progress can take a few seconds

AdapterLister = Callable[[], Sequence[AdapterInfo]]


class ConnectionController(QObject):
    """Runs the connection service off the GUI thread and reports with signals."""

    state_changed = Signal(object, object)  # ConnectionState, ConnectionFailure | None
    adapters_listed = Signal(list)  # list[AdapterInfo]
    status_updated = Signal(object)  # ControllerStatus

    def __init__(
        self,
        service: ConnectionService | None = None,
        lister: AdapterLister = list_adapters,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service or ConnectionService()
        self._lister = lister
        # Own pool, so that shutdown() can wait for these workers only.
        self._pool = QThreadPool(self)
        self._closed = False
        self.service.add_listener(self._on_service_state)
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(STATUS_INTERVAL_MS)
        self._status_timer.timeout.connect(self._poll_status)
        self.state_changed.connect(self._follow_state)

    @property
    def state(self) -> ConnectionState:
        return self.service.state

    def refresh_adapters(self) -> None:
        """List the adapters in a worker; the result arrives with ``adapters_listed``."""
        self._pool.start(self._list_adapters)

    def connect_bus(self, config: ConnectionConfig) -> None:
        """Open ``config`` in a worker; the outcome arrives with ``state_changed``."""
        self._pool.start(lambda: self._run(lambda: self.service.connect(config)))

    def connect_virtual(self, channel: str, bitrate: int) -> None:
        """Open the virtual bus of demo mode in a worker."""
        self._pool.start(lambda: self._run(lambda: self.service.connect_virtual(channel, bitrate)))

    def disconnect_bus(self) -> None:
        """Close the bus in a worker."""
        self._pool.start(lambda: self._run(self.service.disconnect))

    def shutdown(self) -> None:
        """Application exit: wait for the workers, then close the bus.

        After this the controller emits nothing, so a worker that ends late
        never reaches a window that no longer exists.
        """
        self._closed = True
        self._status_timer.stop()
        if not self._pool.waitForDone(SHUTDOWN_WAIT_MS):
            logger.warning("A connection worker is still running at exit")
        self.service.disconnect()

    # ----- workers -----

    def _emit(self, signal: SignalInstance, *args: object) -> None:
        """Emit from a worker, unless the controller is shutting down."""
        if self._closed:
            return
        try:
            signal.emit(*args)
        except RuntimeError:  # the Qt object was deleted meanwhile
            logger.debug("Connection signal dropped: controller deleted")

    def _list_adapters(self) -> None:
        try:
            adapters = list(self._lister())
        except Exception:
            logger.exception("Could not list the adapters")
            adapters = []
        self._emit(self.adapters_listed, adapters)

    @staticmethod
    def _run(action: Callable[[], None]) -> None:
        try:
            action()
        except ConnectionFailure:
            pass  # already reported to the listeners with the new state
        except Exception:  # the worker must never die silently
            logger.exception("Unexpected error in a connection worker")

    def _on_service_state(self, state: ConnectionState, failure: ConnectionFailure | None) -> None:
        self._emit(self.state_changed, state, failure)

    # ----- GUI thread -----

    def _follow_state(self, state: ConnectionState, _failure: object) -> None:
        if state == ConnectionState.CONNECTED:
            self._status_timer.start()
            self._poll_status()
        else:
            self._status_timer.stop()

    def _poll_status(self) -> None:
        self.status_updated.emit(self.service.controller_status())


# The texts are written in QCoreApplication.translate("ConnectionMessages", ...) calls
# with literal arguments: pyside6-lupdate extracts nothing else.


def failure_message(failure: ConnectionFailure, system: str | None = None) -> tuple[str, str]:
    """Title and text of the message for ``failure``: what happened, why, what to do."""
    system = system or platform.system()
    backend = BACKENDS.get(failure.backend)
    family = backend.label if backend is not None else failure.backend
    channel = failure.channel or "-"
    kind = failure.kind

    if kind == ErrorKind.DEVICE_LOST:
        title = QCoreApplication.translate("ConnectionMessages", "Connection lost")
        what = QCoreApplication.translate("ConnectionMessages", "The connection to %1 was lost.")
    else:
        title = QCoreApplication.translate("ConnectionMessages", "Connection failed")
        what = QCoreApplication.translate("ConnectionMessages", "Could not connect to %1.")

    why, todo = _cause_and_remedy(kind, failure, system)
    text = "\n\n".join(
        (
            what.replace("%1", channel),
            why.replace("%1", channel).replace("%2", family).replace("%3", failure.detail),
            todo.replace("%1", channel),
        )
    )
    return title, text


def _cause_and_remedy(kind: ErrorKind, failure: ConnectionFailure, system: str) -> tuple[str, str]:
    """The "why" and "what to do" parts for ``kind``."""
    if kind == ErrorKind.PORT_NOT_FOUND:
        return (
            QCoreApplication.translate(
                "ConnectionMessages",
                "Cause: the port does not exist. The adapter is unplugged or has another name.",
            ),
            QCoreApplication.translate(
                "ConnectionMessages",
                "Plug the adapter in, choose Refresh list in the adapter menu and select it again.",
            ),
        )
    if kind == ErrorKind.PORT_BUSY:
        return (
            QCoreApplication.translate(
                "ConnectionMessages",
                "Cause: another program is using the port, for example another "
                "configurator, a serial terminal or a second copy of this application.",
            ),
            QCoreApplication.translate(
                "ConnectionMessages",
                "Close the other program, or disconnect it from the port, then try again.",
            ),
        )
    if kind == ErrorKind.PERMISSION_DENIED:
        return (
            QCoreApplication.translate(
                "ConnectionMessages",
                "Cause: your user is not allowed to use serial ports on this computer.",
            ),
            QCoreApplication.translate(
                "ConnectionMessages",
                "Ask the administrator to run once: sudo usermod -aG dialout $USER "
                "(uucp on Arch Linux and macOS), then log out and in again. "
                "This application never asks for administrator rights.",
            ),
        )
    if kind == ErrorKind.DRIVER_MISSING:
        return QCoreApplication.translate(
            "ConnectionMessages", "Cause: the driver or library of %2 is not installed."
        ), _driver_remedy(failure.backend)
    if kind == ErrorKind.INTERFACE_DOWN:
        return (
            QCoreApplication.translate(
                "ConnectionMessages", "Cause: the SocketCAN interface %1 is down."
            ),
            QCoreApplication.translate(
                "ConnectionMessages",
                "Ask the administrator to bring it up with the network bitrate, for example: "
                "sudo ip link set %1 up type can bitrate 500000. "
                "For SocketCAN the bitrate is set there, not in this application.",
            ),
        )
    if kind == ErrorKind.NOT_AN_ADAPTER:
        return (
            QCoreApplication.translate(
                "ConnectionMessages",
                "Cause: the port opened, but nothing answered like an SLCAN adapter. "
                "It may be another device, or an adapter with a different firmware.",
            ),
            QCoreApplication.translate(
                "ConnectionMessages",
                "Choose the port of the Rumia USB-CAN interface (it is first in the list, "
                "marked RUMIA). If it is already selected, unplug it, plug it in again "
                "and retry.",
            ),
        )
    if kind == ErrorKind.NOT_ON_THIS_SYSTEM:
        return (
            QCoreApplication.translate(
                "ConnectionMessages", "Cause: %2 adapters cannot be used on this operating system."
            ),
            QCoreApplication.translate(
                "ConnectionMessages", "Choose another adapter type in Other adapter…"
            ),
        )
    if kind == ErrorKind.INVALID_SETTINGS:
        return (
            QCoreApplication.translate(
                "ConnectionMessages", "Cause: the connection settings are not valid (%3)."
            ),
            QCoreApplication.translate(
                "ConnectionMessages",
                "Check the adapter type, the channel and the bitrate in Other adapter…",
            ),
        )
    if kind == ErrorKind.ALREADY_CONNECTED:
        return (
            QCoreApplication.translate(
                "ConnectionMessages", "Cause: only one bus can be open at a time."
            ),
            QCoreApplication.translate(
                "ConnectionMessages", "Disconnect first, then connect to the other adapter."
            ),
        )
    if kind == ErrorKind.DEVICE_LOST:
        return (
            QCoreApplication.translate(
                "ConnectionMessages",
                "Cause: the adapter stopped answering. It was unplugged, "
                "or its driver reported an error.",
            ),
            QCoreApplication.translate(
                "ConnectionMessages", "Plug the adapter in again and press Connect."
            ),
        )
    return (
        QCoreApplication.translate(
            "ConnectionMessages",
            "Cause: the CAN library reported an error that the application does not know: %3",
        ),
        QCoreApplication.translate(
            "ConnectionMessages",
            "Try again. If it happens again, export the logs (menu, Export logs…) "
            "and send them to Rumia support.",
        ),
    )


def _driver_remedy(backend: str) -> str:
    if backend == "pcan":
        return QCoreApplication.translate(
            "ConnectionMessages",
            "Install the PEAK driver with the PCAN-Basic library from the manufacturer's "
            "website, then restart the application.",
        )
    if backend == "kvaser":
        return QCoreApplication.translate(
            "ConnectionMessages",
            "Install the Kvaser drivers with the CANlib library from the manufacturer's "
            "website, then restart the application.",
        )
    if backend == "ixxat":
        return QCoreApplication.translate(
            "ConnectionMessages",
            "Install the IXXAT VCI driver from the manufacturer's website, "
            "then restart the application.",
        )
    if backend == "gs_usb":
        return QCoreApplication.translate(
            "ConnectionMessages",
            "This version of the application does not include support for candleLight "
            "(gs_usb) adapters. Use an SLCAN adapter such as the Rumia USB-CAN interface.",
        )
    return QCoreApplication.translate(
        "ConnectionMessages", "Install the driver of the adapter, then restart the application."
    )
