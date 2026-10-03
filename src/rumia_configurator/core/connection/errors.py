"""Turn the exceptions of python-can into causes the user can act on (FR-CON-05).

Every python-can backend reports a failed open in its own way: a
``CanInitializationError`` wrapping an ``OSError`` for serial ports, a plain
``OSError`` when the PEAK library is missing, even a ``NameError`` when the
Kvaser library is not installed. :func:`classify_open_error` accepts any
exception and returns a :class:`ConnectionFailure` with one
:class:`ErrorKind`; the interface turns the kind into a message in three
parts (what happened, why, what to do).
"""

from __future__ import annotations

import errno
import platform
from enum import StrEnum

import can


class ErrorKind(StrEnum):
    """Probable cause of a connection problem."""

    PORT_NOT_FOUND = "port_not_found"
    PORT_BUSY = "port_busy"
    PERMISSION_DENIED = "permission_denied"
    DRIVER_MISSING = "driver_missing"
    INTERFACE_DOWN = "interface_down"
    NOT_AN_ADAPTER = "not_an_adapter"
    INVALID_SETTINGS = "invalid_settings"
    NOT_ON_THIS_SYSTEM = "not_on_this_system"
    ALREADY_CONNECTED = "already_connected"
    DEVICE_LOST = "device_lost"
    UNKNOWN = "unknown"


class ConnectionFailure(Exception):  # noqa: N818 (a failure, not a bug: reads better)
    """A connection that could not be opened, or was lost.

    ``detail`` keeps the original text of the library for the log and for
    support; the user sees a message chosen from ``kind``.
    """

    def __init__(self, kind: ErrorKind, backend: str, channel: str, detail: str = "") -> None:
        super().__init__(f"{kind.value} ({backend} {channel}): {detail}")
        self.kind = kind
        self.backend = backend
        self.channel = channel
        self.detail = detail


# Pieces of text the libraries use, lower case. Checked after the errno.
_NOT_FOUND_TEXTS = (
    "could not open port",
    "no such file",
    "no such device",
    "cannot find the file",
    "impossibile trovare il file",
    "filenotfounderror",
)
_BUSY_TEXTS = ("could not exclusively lock", "resource busy", "device or resource busy")
_ACCESS_DENIED_TEXTS = ("access is denied", "accesso negato", "permission denied", "errno 13")
_DRIVER_TEXTS = (
    "library not found",
    "is unavailable",
    "not available",
    "cannot import",
    "no module named",
    "could not load",
    "dll",
    "no backend available",
)
_DOWN_TEXTS = ("network is down",)


def _chain(exc: BaseException) -> list[BaseException]:
    """The exception followed by its causes (python-can wraps the OS errors)."""
    found: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None and current not in found:
        found.append(current)
        current = current.__cause__ or current.__context__
    return found


def _errnos(chain: list[BaseException]) -> set[int]:
    numbers = set()
    for item in chain:
        if isinstance(item, OSError) and item.errno is not None:
            numbers.add(item.errno)
        for arg in getattr(item, "args", ()):
            if isinstance(arg, OSError) and arg.errno is not None:
                numbers.add(arg.errno)
    return numbers


def _text(chain: list[BaseException]) -> str:
    return " | ".join(f"{type(item).__name__}: {item}" for item in chain).lower()


def classify_open_error(
    exc: BaseException, backend: str, channel: str, system: str | None = None
) -> ConnectionFailure:
    """Probable cause of ``exc``, raised while opening ``backend`` on ``channel``.

    ``system`` is ``platform.system()`` ("Windows", "Linux", "Darwin"); tests
    pass it to check the rules of every system on any machine.
    """
    system = system or platform.system()
    chain = _chain(exc)
    numbers = _errnos(chain)
    text = _text(chain)
    detail = f"{type(exc).__name__}: {exc}"

    def failure(kind: ErrorKind) -> ConnectionFailure:
        return ConnectionFailure(kind, backend, channel, detail)

    if isinstance(exc, ConnectionFailure):
        return exc
    if any(isinstance(item, ValueError) for item in chain) and not numbers:
        return failure(ErrorKind.INVALID_SETTINGS)
    if errno.ENETDOWN in numbers or any(t in text for t in _DOWN_TEXTS):
        return failure(ErrorKind.INTERFACE_DOWN)
    if errno.EBUSY in numbers or any(t in text for t in _BUSY_TEXTS):
        return failure(ErrorKind.PORT_BUSY)
    if errno.EACCES in numbers or any(t in text for t in _ACCESS_DENIED_TEXTS):
        # On Windows a COM port that another program holds answers "access denied".
        return failure(ErrorKind.PORT_BUSY if system == "Windows" else ErrorKind.PERMISSION_DENIED)
    if errno.ENOENT in numbers or errno.ENODEV in numbers:
        return failure(ErrorKind.PORT_NOT_FOUND)
    if any(
        isinstance(item, (can.CanInterfaceNotImplementedError, ImportError, NameError))
        for item in chain
    ) or any(t in text for t in _DRIVER_TEXTS):
        return failure(ErrorKind.DRIVER_MISSING)
    if any(t in text for t in _NOT_FOUND_TEXTS):
        return failure(ErrorKind.PORT_NOT_FOUND)
    return failure(ErrorKind.UNKNOWN)
