"""What the application knows about one node of the network (FR-NET-02)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class NmtState(StrEnum):
    """NMT state as carried by the heartbeat (CiA 301)."""

    BOOTUP = "bootup"
    STOPPED = "stopped"
    OPERATIONAL = "operational"
    PRE_OPERATIONAL = "pre-operational"
    UNKNOWN = "unknown"  # found by the scan, no heartbeat seen yet

    @classmethod
    def from_heartbeat(cls, value: int) -> NmtState:
        """State of a heartbeat byte; bit 7 (toggle) is ignored."""
        return _HEARTBEAT_STATES.get(value & 0x7F, cls.UNKNOWN)


_HEARTBEAT_STATES = {
    0x00: NmtState.BOOTUP,
    0x04: NmtState.STOPPED,
    0x05: NmtState.OPERATIONAL,
    0x7F: NmtState.PRE_OPERATIONAL,
}


class SeenBy(StrEnum):
    """How the node was found first."""

    SCAN = "scan"
    HEARTBEAT = "heartbeat"
    BOOTUP = "bootup"


@dataclass(frozen=True)
class NodeInfo:
    """A node as known at one moment; ``None`` means "not read" or "not available"."""

    node_id: int
    seen_by: SeenBy
    nmt_state: NmtState = NmtState.UNKNOWN
    name: str | None = None  # 0x1008 Manufacturer device name
    vendor_id: int | None = None  # 0x1018:01
    product_code: int | None = None  # 0x1018:02
    revision: int | None = None  # 0x1018:03
    serial: int | None = None  # 0x1018:04
    heartbeat_ms: int | None = None  # 0x1017 Producer heartbeat time; 0 = off
    identity_read: bool = False  # the identity objects were asked for
    identity_error: str | None = None  # why some of them could not be read
    last_heartbeat: float | None = None  # NodeRegistry.now() of the last heartbeat
    heartbeat_missing: bool = False  # FR-NET-05
    silent_for: float = 0.0  # seconds since the last heartbeat (or since found)

    @property
    def heartbeat_off(self) -> bool:
        """The node says it sends no heartbeat (0x1017 = 0)."""
        return self.heartbeat_ms == 0
