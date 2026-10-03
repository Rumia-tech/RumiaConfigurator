"""CAN adapters and python-can backends the application supports (FR-CON-01, FR-CON-02).

:func:`list_adapters` finds the adapters it can see without loading any
vendor driver: serial ports (SLCAN adapters such as the Rumia USB-CAN
interface) and, on Linux, SocketCAN interfaces. PEAK, Kvaser, IXXAT and
candleLight (gs_usb) adapters are chosen by backend and channel instead,
because probing them would load their drivers at every refresh.

The ``virtual`` backend is not listed here: it is opened only by demo mode
(see ``ConnectionService.connect_virtual``).
"""

from __future__ import annotations

import logging
import platform
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

logger = logging.getLogger(__name__)

AdapterKind = Literal["rumia", "canable", "serial", "socketcan"]

# USB identifiers of SLCAN adapters (VID, PID) -> kind. Add new adapters here.
KNOWN_USB_IDS: dict[tuple[int, int], AdapterKind] = {
    (0x17D0, 0x118E): "rumia",  # Rumia CAN Interface
    (0x16D0, 0x117E): "canable",  # CANable with the original SLCAN firmware
}

_KIND_ORDER: dict[AdapterKind, int] = {"rumia": 0, "canable": 1, "socketcan": 2, "serial": 3}

# CiA 301 bitrates in bit/s (FR-CON-03); not every adapter supports 800 kbit/s.
BITRATES: tuple[int, ...] = (
    10_000,
    20_000,
    50_000,
    125_000,
    250_000,
    500_000,
    800_000,
    1_000_000,
)

ARPHRD_CAN = 280  # /sys/class/net/<name>/type of a SocketCAN interface


@dataclass(frozen=True)
class Backend:
    """A python-can interface the application can open."""

    name: str  # python-can interface name
    label: str  # product family, not translated (brand names)
    channel_example: str
    systems: tuple[str, ...]  # platform.system() values where it can work
    needs_bitrate: bool = True  # False: the bitrate is set outside the app (SocketCAN)


BACKENDS: dict[str, Backend] = {
    b.name: b
    for b in (
        Backend("slcan", "SLCAN (Rumia, CANable)", "COM5", ("Windows", "Linux", "Darwin")),
        Backend("socketcan", "SocketCAN", "can0", ("Linux",), needs_bitrate=False),
        Backend("pcan", "PEAK PCAN", "PCAN_USBBUS1", ("Windows", "Linux", "Darwin")),
        Backend("kvaser", "Kvaser", "0", ("Windows", "Linux")),
        Backend("ixxat", "IXXAT", "0", ("Windows", "Linux")),
        Backend("gs_usb", "candleLight (gs_usb)", "0", ("Windows", "Linux", "Darwin")),
    )
}


@dataclass(frozen=True)
class AdapterInfo:
    """An adapter found on this computer."""

    backend: str
    channel: str
    description: str
    kind: AdapterKind
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None

    @property
    def usb_id(self) -> str:
        """``"17D0:118E"``, or ``""`` when the adapter is not a USB device."""
        if self.vid is None or self.pid is None:
            return ""
        return f"{self.vid:04X}:{self.pid:04X}"


class SerialPortInfo(Protocol):
    """The fields of ``serial.tools.list_ports_common.ListPortInfo`` used here."""

    device: str
    description: str
    vid: int | None
    pid: int | None
    serial_number: str | None
    manufacturer: str | None
    product: str | None


def backends_for(system: str | None = None) -> list[Backend]:
    """Backends that can work on ``system`` (default: this computer)."""
    system = system or platform.system()
    return [b for b in BACKENDS.values() if system in b.systems]


def _serial_kind(port: SerialPortInfo) -> AdapterKind:
    if port.vid is not None and port.pid is not None:
        known = KNOWN_USB_IDS.get((port.vid, port.pid))
        if known is not None:
            return known
    return "serial"


def _default_comports() -> list[SerialPortInfo]:
    from serial.tools import list_ports

    return list(list_ports.comports())


def serial_adapters(
    comports: Callable[[], Iterable[SerialPortInfo]] = _default_comports,
) -> list[AdapterInfo]:
    """Serial ports, each a possible SLCAN adapter."""
    adapters = []
    for port in comports():
        description = port.product or port.description or port.device
        adapters.append(
            AdapterInfo(
                backend="slcan",
                channel=port.device,
                description=description,
                kind=_serial_kind(port),
                vid=port.vid,
                pid=port.pid,
                serial_number=port.serial_number,
            )
        )
    return adapters


def socketcan_adapters(net_dir: Path = Path("/sys/class/net")) -> list[AdapterInfo]:
    """SocketCAN interfaces (Linux), read from ``/sys/class/net/*/type``."""
    adapters: list[AdapterInfo] = []
    if not net_dir.is_dir():
        return adapters
    for interface in sorted(net_dir.iterdir()):
        try:
            kind = int((interface / "type").read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            continue
        if kind == ARPHRD_CAN:
            adapters.append(
                AdapterInfo("socketcan", interface.name, f"SocketCAN {interface.name}", "socketcan")
            )
    return adapters


def list_adapters(
    system: str | None = None,
    comports: Callable[[], Iterable[SerialPortInfo]] = _default_comports,
    net_dir: Path = Path("/sys/class/net"),
) -> list[AdapterInfo]:
    """Adapters found on this computer: Rumia first, then CANable, SocketCAN, other ports.

    A failure of one source is logged and the others are still listed.
    """
    system = system or platform.system()
    found: list[AdapterInfo] = []
    try:
        found.extend(serial_adapters(comports))
    except Exception:  # pyserial can fail on unusual drivers: never block the list
        logger.exception("Could not list the serial ports")
    if system == "Linux":
        found.extend(socketcan_adapters(net_dir))
    return sorted(found, key=lambda a: (_KIND_ORDER[a.kind], a.channel))
