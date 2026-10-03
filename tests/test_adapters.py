"""Adapters found on the computer (FR-CON-01, FR-CON-02)."""

from dataclasses import dataclass
from pathlib import Path

from rumia_configurator.core.connection import BACKENDS, backends_for, list_adapters


@dataclass
class Port:
    """The fields of pyserial's ListPortInfo that the code reads."""

    device: str
    description: str = "n/a"
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    product: str | None = None


PORTS = [
    Port("COM3", "Bluetooth link"),
    Port("COM7", "USB serial", 0x16D0, 0x117E, "C1", "Protofusion Labs", "CANable"),
    Port("COM5", "USB serial", 0x17D0, 0x118E, "R42", "Rumia", "Rumia CAN Interface"),
]


def test_rumia_adapter_comes_first_then_canable_then_other_ports() -> None:
    adapters = list_adapters("Windows", comports=lambda: PORTS)
    assert [(a.channel, a.kind) for a in adapters] == [
        ("COM5", "rumia"),
        ("COM7", "canable"),
        ("COM3", "serial"),
    ]
    rumia = adapters[0]
    assert rumia.backend == "slcan"
    assert rumia.description == "Rumia CAN Interface"
    assert rumia.usb_id == "17D0:118E"
    assert rumia.serial_number == "R42"
    assert adapters[2].usb_id == ""


def test_socketcan_interfaces_are_listed_on_linux(tmp_path: Path) -> None:
    for name, kind in (("can0", "280"), ("eth0", "1"), ("vcan1", "280")):
        (tmp_path / name).mkdir()
        (tmp_path / name / "type").write_text(kind + "\n", encoding="ascii")
    (tmp_path / "broken").mkdir()  # no type file: skipped
    adapters = list_adapters("Linux", comports=lambda: [], net_dir=tmp_path)
    assert [(a.backend, a.channel) for a in adapters] == [
        ("socketcan", "can0"),
        ("socketcan", "vcan1"),
    ]


def test_no_socketcan_outside_linux(tmp_path: Path) -> None:
    (tmp_path / "can0").mkdir()
    (tmp_path / "can0" / "type").write_text("280", encoding="ascii")
    assert list_adapters("Windows", comports=lambda: [], net_dir=tmp_path) == []


def test_a_failing_serial_listing_does_not_hide_the_rest(tmp_path: Path) -> None:
    def broken() -> list[Port]:
        raise OSError("driver crashed")

    (tmp_path / "can0").mkdir()
    (tmp_path / "can0" / "type").write_text("280", encoding="ascii")
    adapters = list_adapters("Linux", comports=broken, net_dir=tmp_path)
    assert [a.channel for a in adapters] == ["can0"]


def test_backends_per_system() -> None:
    assert "virtual" not in BACKENDS  # demo mode only
    assert {b.name for b in backends_for("Linux")} == {
        "slcan",
        "socketcan",
        "pcan",
        "kvaser",
        "ixxat",
        "gs_usb",
    }
    assert "socketcan" not in {b.name for b in backends_for("Windows")}
    assert {b.name for b in backends_for("Darwin")} == {"slcan", "pcan", "gs_usb"}
