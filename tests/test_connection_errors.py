"""Exceptions of python-can turned into causes the user can act on (FR-CON-05).

The exceptions below are the ones python-can 4.6 really raises; the Windows
ones were captured on a machine without adapters or vendor drivers.
"""

import errno

import can
import pytest

from rumia_configurator.core.connection import ConnectionFailure, ErrorKind, classify_open_error


def wrapped(outer: Exception, cause: BaseException) -> Exception:
    """``outer`` raised ``from cause``, as python-can does for serial errors."""
    outer.__cause__ = cause
    return outer


CASES = [
    pytest.param(
        can.CanInitializationError(
            "could not open port 'COM99': FileNotFoundError(2, "
            "'Impossibile trovare il file specificato.', None, 2)"
        ),
        "Windows",
        ErrorKind.PORT_NOT_FOUND,
        id="windows-port-missing-italian",
    ),
    pytest.param(
        can.CanInitializationError(
            "could not open port 'COM3': FileNotFoundError(2, "
            "'The system cannot find the file specified.', None, 2)"
        ),
        "Windows",
        ErrorKind.PORT_NOT_FOUND,
        id="windows-port-missing-english",
    ),
    pytest.param(
        can.CanInitializationError(
            "could not open port 'COM3': PermissionError(13, 'Accesso negato.', None, 5)"
        ),
        "Windows",
        ErrorKind.PORT_BUSY,
        id="windows-port-in-use",
    ),
    pytest.param(
        wrapped(
            can.CanInitializationError("could not open port /dev/ttyACM0"),
            OSError(errno.EACCES, "Permission denied"),
        ),
        "Linux",
        ErrorKind.PERMISSION_DENIED,
        id="linux-dialout",
    ),
    pytest.param(
        wrapped(
            can.CanInitializationError("could not open port /dev/ttyACM0"),
            OSError(errno.EBUSY, "Device or resource busy"),
        ),
        "Linux",
        ErrorKind.PORT_BUSY,
        id="linux-busy",
    ),
    pytest.param(
        can.CanInitializationError(
            "could not open port /dev/ttyACM0: [Errno 11] Could not exclusively lock port"
        ),
        "Linux",
        ErrorKind.PORT_BUSY,
        id="linux-locked",
    ),
    pytest.param(
        wrapped(
            can.CanInitializationError("could not open port /dev/ttyACM9"),
            OSError(errno.ENOENT, "No such file or directory"),
        ),
        "Linux",
        ErrorKind.PORT_NOT_FOUND,
        id="linux-port-missing",
    ),
    pytest.param(
        OSError(errno.ENETDOWN, "Network is down"),
        "Linux",
        ErrorKind.INTERFACE_DOWN,
        id="socketcan-down",
    ),
    pytest.param(
        OSError("PCANBasic library not found."), "Windows", ErrorKind.DRIVER_MISSING, id="pcan"
    ),
    pytest.param(
        NameError("name 'canGetNumberOfChannels' is not defined"),
        "Windows",
        ErrorKind.DRIVER_MISSING,
        id="kvaser",
    ),
    pytest.param(
        can.CanInterfaceNotImplementedError(
            "Cannot import module can.interfaces.gs_usb for CAN interface 'gs_usb': "
            "No module named 'usb'"
        ),
        "Windows",
        ErrorKind.DRIVER_MISSING,
        id="gs_usb-without-pyusb",
    ),
    pytest.param(
        can.CanInterfaceNotImplementedError(
            "The IXXAT VCI library has not been initialized. Check the logs for more details."
        ),
        "Windows",
        ErrorKind.DRIVER_MISSING,
        id="ixxat",
    ),
    pytest.param(
        ValueError("Must specify a serial port."), "Windows", ErrorKind.INVALID_SETTINGS, id="value"
    ),
    pytest.param(
        RuntimeError("something nobody expected"), "Windows", ErrorKind.UNKNOWN, id="unknown"
    ),
]


@pytest.mark.parametrize(("exc", "system", "kind"), CASES)
def test_open_errors_are_classified(exc: Exception, system: str, kind: ErrorKind) -> None:
    failure = classify_open_error(exc, "slcan", "COM3", system)
    assert failure.kind == kind
    assert failure.backend == "slcan"
    assert failure.channel == "COM3"
    assert type(exc).__name__ in failure.detail  # original text kept for the log


def test_a_failure_is_returned_unchanged() -> None:
    failure = ConnectionFailure(ErrorKind.NOT_AN_ADAPTER, "slcan", "COM3", "no answer")
    assert classify_open_error(failure, "slcan", "COM3", "Windows") is failure
