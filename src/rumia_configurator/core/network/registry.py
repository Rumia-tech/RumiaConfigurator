"""Nodes on the network: scan, boot-up and heartbeat, identity (FR-NET-01, 02, 05).

A node becomes known when it answers the SDO scan, sends its boot-up message
or sends a heartbeat. PDOs are not used to find nodes: a PDO moved to another
COB-ID would make a node appear that does not exist.

The heartbeat and SDO callbacks run in the python-can receive thread; the
scan and the identity reads are blocking and run in a worker. One lock
protects the records. The registry never runs two SDO transactions at once:
the caller must not call :meth:`NodeRegistry.scan` and
:meth:`NodeRegistry.read_identity` from two threads (the GUI uses a
one-thread pool).
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace

import canopen
from canopen.objectdictionary import ObjectDictionary
from canopen.sdo.client import SdoClient
from canopen.sdo.exceptions import SdoAbortedError, SdoCommunicationError

from rumia_configurator.core.network.nmt import NmtCommand, NmtOutcome
from rumia_configurator.core.network.nodes import NmtState, NodeInfo, SeenBy

logger = logging.getLogger(__name__)

NODE_IDS = range(1, 128)
SCAN_REQUEST = bytes([0x40, 0x00, 0x10, 0x00, 0, 0, 0, 0])  # SDO upload of 0x1000:00
SCAN_MIN_WINDOW = 1.0  # seconds to wait for the answers after the last request
FRAME_BITS = 122  # an SDO frame of 8 bytes, stuffing included (see core.traffic.stats)
HEARTBEAT_TOLERANCE = 1.5  # alarm when no heartbeat for 1.5 x the expected period
SDO_TIMEOUT = 0.3  # seconds for each identity read
VERIFY_MIN = 1.0  # seconds to wait for the effect of an NMT command, at least
VERIFY_MAX = 10.0  # and at most
DEFAULT_HEARTBEAT = 1.0  # seconds, when the period of a node is not known

Clock = Callable[[], float]


@dataclass
class _Record:
    """Mutable record of a node, kept under the registry lock."""

    info: NodeInfo
    found_at: float
    observed_period: float | None = None
    last_bootup: float | None = None


class NodeRegistry:
    """The nodes seen on one connection. Close it when the connection closes."""

    def __init__(
        self,
        network: canopen.Network,
        bitrate: int | None = None,
        clock: Clock = time.perf_counter,  # monotonic() ticks every ~16 ms on Windows
    ) -> None:
        self._network = network
        self._bitrate = bitrate
        self._clock = clock
        self._lock = threading.Lock()
        self._nodes: dict[int, _Record] = {}
        self._clients: dict[int, SdoClient] = {}
        for node_id in NODE_IDS:
            network.subscribe(0x700 + node_id, self._on_heartbeat)
            network.subscribe(0x580 + node_id, self._on_sdo_answer)

    def close(self) -> None:
        """Stop listening; the network may already be closed."""
        for node_id in NODE_IDS:
            for can_id, callback in (
                (0x700 + node_id, self._on_heartbeat),
                (0x580 + node_id, self._on_sdo_answer),
            ):
                with contextlib.suppress(KeyError, ValueError):
                    self._network.unsubscribe(can_id, callback)
        for node_id, client in self._clients.items():
            with contextlib.suppress(KeyError, ValueError):
                self._network.unsubscribe(0x580 + node_id, client.on_response)
        self._clients.clear()

    # ----- what is known -----

    def now(self) -> float:
        """The clock of the registry: pass it as ``sent_at`` to :meth:`verify_nmt`."""
        return self._clock()

    def snapshot(self) -> list[NodeInfo]:
        """Every known node, by Node-ID, with ``silent_for`` computed now."""
        now = self._clock()
        with self._lock:
            records = sorted(self._nodes.values(), key=lambda r: r.info.node_id)
            return [
                replace(r.info, silent_for=now - (r.info.last_heartbeat or r.found_at))
                for r in records
            ]

    def pending_identity(self) -> list[int]:
        """Nodes whose identity has not been read yet."""
        with self._lock:
            return sorted(n for n, r in self._nodes.items() if not r.info.identity_read)

    # ----- receive thread -----

    def _on_heartbeat(self, can_id: int, data: bytearray, timestamp: float) -> None:
        if not data:
            return
        node_id = can_id - 0x700
        state = NmtState.from_heartbeat(data[0])
        now = self._clock()
        with self._lock:
            record = self._nodes.get(node_id)
            if record is None:
                seen = SeenBy.BOOTUP if state == NmtState.BOOTUP else SeenBy.HEARTBEAT
                record = _Record(NodeInfo(node_id, seen), found_at=now)
                self._nodes[node_id] = record
                logger.info("Node %d found by %s", node_id, seen.value)
            info = record.info
            if state == NmtState.BOOTUP:
                # The node restarted: its identity and settings may have changed.
                record.observed_period = None
                record.last_bootup = now
                record.info = replace(
                    info, nmt_state=state, last_heartbeat=now, identity_read=False
                )
                return
            if info.last_heartbeat is not None and info.nmt_state != NmtState.BOOTUP:
                record.observed_period = now - info.last_heartbeat
            record.info = replace(info, nmt_state=state, last_heartbeat=now)

    def _on_sdo_answer(self, can_id: int, data: bytearray, timestamp: float) -> None:
        node_id = can_id - 0x580
        with self._lock:
            if node_id not in self._nodes:
                self._nodes[node_id] = _Record(NodeInfo(node_id, SeenBy.SCAN), self._clock())
                logger.info("Node %d found by the scan", node_id)

    # ----- worker thread -----

    def scan(self) -> list[int]:
        """Ask every Node-ID for 0x1000 and return the nodes that answered.

        Blocking: sends 127 SDO requests, then waits for the answers.
        """
        before = set(self._nodes)
        for node_id in NODE_IDS:
            self._network.send_message(0x600 + node_id, SCAN_REQUEST)
        time.sleep(self.scan_window())
        with self._lock:
            found = sorted(self._nodes)
        logger.info("Scan: %d nodes (%d new)", len(found), len(set(found) - before))
        return found

    def scan_window(self) -> float:
        """Seconds to wait for the answers: longer on slow buses."""
        if not self._bitrate:
            return SCAN_MIN_WINDOW
        send_time = len(NODE_IDS) * 2 * FRAME_BITS / self._bitrate  # requests and answers
        return max(SCAN_MIN_WINDOW, 2 * send_time)

    def read_identity(self, node_id: int) -> NodeInfo:
        """Read 0x1008, 0x1018:01..04 and 0x1017 from ``node_id``; blocking.

        An object that cannot be read stays ``None``; the reasons are joined
        in ``identity_error``. The node stays in the list in any case.
        """
        client = self._client(node_id)
        errors: list[str] = []

        def upload(index: int, subindex: int) -> bytes | None:
            try:
                data: bytes = client.upload(index, subindex)
                return data
            except SdoAbortedError as exc:
                errors.append(f"0x{index:04X}:{subindex:02X} abort 0x{exc.code:08X}")
            except SdoCommunicationError as exc:
                errors.append(f"0x{index:04X}:{subindex:02X} {exc}")
            return None

        name = _text(upload(0x1008, 0))
        identity = [_unsigned(upload(0x1018, sub)) for sub in (1, 2, 3, 4)]
        heartbeat = _unsigned(upload(0x1017, 0))
        with self._lock:
            record = self._nodes.get(node_id)
            if record is None:
                record = _Record(NodeInfo(node_id, SeenBy.SCAN), self._clock())
                self._nodes[node_id] = record
            record.info = replace(
                record.info,
                name=name,
                vendor_id=identity[0],
                product_code=identity[1],
                revision=identity[2],
                serial=identity[3],
                heartbeat_ms=heartbeat,
                identity_read=True,
                identity_error="; ".join(errors) or None,
            )
            return record.info

    def _client(self, node_id: int) -> SdoClient:
        client = self._clients.get(node_id)
        if client is None:
            client = SdoClient(0x600 + node_id, 0x580 + node_id, ObjectDictionary())
            client.network = self._network
            client.RESPONSE_TIMEOUT = SDO_TIMEOUT
            self._network.subscribe(0x580 + node_id, client.on_response)
            self._clients[node_id] = client
        return client

    # ----- effect of an NMT command (NFR-REL-03) -----

    def verify_nmt(
        self, command: NmtCommand, node_ids: list[int], sent_at: float
    ) -> dict[int, NmtOutcome]:
        """Wait for the heartbeats that confirm ``command``, sent at ``sent_at``.

        Blocking. Each node is given 2 x its heartbeat period (between 1 and
        10 s). A reset is confirmed by a boot-up message after ``sent_at``;
        the other commands by a heartbeat in the expected state.
        """
        outcomes: dict[int, NmtOutcome] = {}
        deadlines: dict[int, float] = {}
        with self._lock:
            for node_id in node_ids:
                record = self._nodes.get(node_id)
                if record is None:
                    outcomes[node_id] = NmtOutcome.NO_HEARTBEAT
                    continue
                if record.info.heartbeat_off:
                    outcomes[node_id] = NmtOutcome.NOT_VERIFIABLE
                    continue
                period = _expected_period(record.info, record.observed_period)
                wait = 2 * (period or DEFAULT_HEARTBEAT)
                deadlines[node_id] = sent_at + min(VERIFY_MAX, max(VERIFY_MIN, wait))
        while deadlines:
            now = self._clock()
            with self._lock:
                for node_id in list(deadlines):
                    outcome = self._nmt_outcome(command, self._nodes[node_id], sent_at)
                    if outcome == NmtOutcome.CONFIRMED or now >= deadlines[node_id]:
                        outcomes[node_id] = outcome
                        del deadlines[node_id]
            if deadlines:
                time.sleep(0.02)
        return outcomes

    @staticmethod
    def _nmt_outcome(command: NmtCommand, record: _Record, sent_at: float) -> NmtOutcome:
        """Outcome so far; final when CONFIRMED or when the time is over."""
        if command.is_reset:
            if record.last_bootup is not None and record.last_bootup >= sent_at:
                return NmtOutcome.CONFIRMED
            heard = record.info.last_heartbeat is not None and record.info.last_heartbeat >= sent_at
            return NmtOutcome.NOT_CONFIRMED if heard else NmtOutcome.NO_HEARTBEAT
        info = record.info
        if info.last_heartbeat is None or info.last_heartbeat < sent_at:
            return NmtOutcome.NO_HEARTBEAT
        if info.nmt_state == command.expected:
            return NmtOutcome.CONFIRMED
        return NmtOutcome.NOT_CONFIRMED

    # ----- heartbeat alarm (FR-NET-05) -----

    def check_heartbeats(self) -> list[tuple[int, bool]]:
        """Update the alarms; return ``(node_id, missing)`` for each change.

        A heartbeat is missing when none arrived for 1.5 x the expected
        period: 0x1017 when it was read, else the period observed between
        the last heartbeats. No alarm when 0x1017 is 0 or nothing is known.
        """
        now = self._clock()
        changes: list[tuple[int, bool]] = []
        with self._lock:
            for node_id, record in self._nodes.items():
                info = record.info
                period = _expected_period(info, record.observed_period)
                reference = info.last_heartbeat or record.found_at
                missing = period is not None and now - reference > HEARTBEAT_TOLERANCE * period
                if missing != info.heartbeat_missing:
                    record.info = replace(info, heartbeat_missing=missing)
                    changes.append((node_id, missing))
                    logger.warning(
                        "Node %d: heartbeat %s", node_id, "missing" if missing else "back"
                    )
        return changes


def _expected_period(info: NodeInfo, observed: float | None) -> float | None:
    if info.heartbeat_ms is not None:
        return info.heartbeat_ms / 1000 if info.heartbeat_ms > 0 else None
    return observed


def _unsigned(data: bytes | None) -> int | None:
    if not data:
        return None
    return int.from_bytes(data[:4].ljust(4, b"\0"), "little")


def _text(data: bytes | None) -> str | None:
    if data is None:
        return None
    text = data.decode("latin-1").rstrip("\0").strip()
    return text or None
