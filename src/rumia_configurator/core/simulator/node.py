"""A simulated CANopen node built on ``canopen.LocalNode``.

``LocalNode`` already answers SDO requests from the object dictionary and
tracks the NMT state. This module adds what a real device does on top:

- boot-up message, heartbeat and automatic switch to Operational at start;
- a new boot-up after NMT Reset node / Reset communication;
- no SDO answers while Stopped (CiA 301);
- store (0x1010) and restore (0x1011) with the "save" / "load" signatures;
- TPDOs built from the mapping in the object dictionary, sent by the event
  timer, so a PDO reconfigured through SDO is sent as configured.

The node does not own a thread: :class:`~.simulator.Simulator` calls
:meth:`SimulatedNode.poll` from its tick thread, while SDO and NMT requests
arrive from the python-can receive thread. One lock per node serialises both.
"""

from __future__ import annotations

import copy
import logging
import struct
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import canopen
from canopen import objectdictionary
from canopen.objectdictionary import ODVariable
from canopen.sdo.exceptions import SdoAbortedError

from rumia_configurator.profiles.eds import load_object_dictionary

logger = logging.getLogger(__name__)

# NMT command specifiers (CiA 301)
NMT_RESET_NODE = 0x81
NMT_RESET_COMMUNICATION = 0x82
NMT_START = 0x01
NMT_ENTER_PRE_OPERATIONAL = 0x80

# NMT states as sent in the heartbeat
STATE_STOPPED = 4
STATE_OPERATIONAL = 5

STORE_SIGNATURE = b"save"
RESTORE_SIGNATURE = b"load"
ABORT_DATA_CANNOT_BE_STORED = 0x08000020
ABORT_VALUE_RANGE_EXCEEDED = 0x06090030

TPDO_COMM_FIRST = 0x1800
TPDO_COMM_LAST = 0x19FF
TPDO_MAP_OFFSET = 0x0200  # 0x1800 + n -> 0x1A00 + n
COB_ID_INVALID = 0x80000000
EVENT_DRIVEN_TYPES = (254, 255)
COMMUNICATION_AREA = range(0x1000, 0x2000)


RawProvider = Callable[[], bytes]


class _LockedLocalNode(canopen.LocalNode):
    """``LocalNode`` whose data store is guarded by a re-entrant lock.

    ``providers`` give the raw bytes of live measurements, computed when they
    are read, exactly as the device firmware would put them on the bus.
    """

    def __init__(self, node_id: int, od: objectdictionary.ObjectDictionary) -> None:
        super().__init__(node_id, od)
        self.lock = threading.RLock()
        self.providers: dict[tuple[int, int], RawProvider] = {}

    def get_data(self, index: int, subindex: int, check_readable: bool = False) -> bytes:
        with self.lock:
            provider = self.providers.get((index, subindex))
            if provider is not None:
                return provider()
            data: bytes = super().get_data(index, subindex, check_readable)
            return data

    def set_data(
        self, index: int, subindex: int, data: bytes, check_writable: bool = False
    ) -> None:
        with self.lock:
            super().set_data(index, subindex, data, check_writable)


class SimulatedNode:
    """One simulated device on the bus.

    Subclasses add the measurements with :meth:`provide`: the value is
    computed from :meth:`now` at every read, so SDO reads and TPDOs always
    carry the current sample.
    """

    def __init__(self, node_id: int, eds_path: Path, *, auto_start: bool = True) -> None:
        result = load_object_dictionary(eds_path, node_id)
        for warning in result.warnings:
            logger.debug("Simulated node %d, %s: %s", node_id, eds_path.name, warning)
        od = result.od
        self.product_name: str = od.device_information.product_name or eds_path.stem
        if 0x1008 not in od:
            od.add_object(_device_name_object(self.product_name))
        self.node_id = node_id
        self.auto_start = auto_start
        self.local = _LockedLocalNode(node_id, od)
        self.local.add_read_callback(self._read_store_restore)
        self.local.add_write_callback(self._write_store_restore)
        self._network: canopen.Network | None = None
        self._clock: Callable[[], float] = time.monotonic
        self._frame_time: float | None = None
        self._persistent: dict[int, dict[int, bytes]] = {}
        self._next_due: dict[int, float] = {}
        self._periods: dict[int, float] = {}

    # ----- lifecycle, called by the Simulator -----

    def attach(self, network: canopen.Network, clock: Callable[[], float]) -> None:
        """Join ``network``; ``clock`` gives the simulation time in seconds."""
        self._network = network
        self._clock = clock
        network.add_node(self.local)
        # Replace the SDO subscription: a Stopped node does not answer SDO.
        network.unsubscribe(self.local.sdo.rx_cobid, self.local.sdo.on_request)
        network.subscribe(self.local.sdo.rx_cobid, self._on_sdo_request)
        # Runs after the LocalNode NMT handler, which has already set the state.
        network.subscribe(0, self._on_nmt_command)

    def detach(self) -> None:
        """Stop the heartbeat and leave the network."""
        network = self._network
        if network is None:
            return
        self.local.nmt.stop_heartbeat()
        network.unsubscribe(0, self._on_nmt_command)
        network.unsubscribe(self.local.sdo.rx_cobid, self._on_sdo_request)
        # remove_network() unsubscribes the original SDO handler: put it back first.
        network.subscribe(self.local.sdo.rx_cobid, self.local.sdo.on_request)
        self.local.remove_network()
        network.nodes.pop(self.node_id, None)
        self._network = None

    def boot(self) -> None:
        """Power-on: boot-up message, Pre-operational with heartbeat, then Operational."""
        with self.local.lock:
            nmt = self.local.nmt
            nmt.stop_heartbeat()
            self._next_due.clear()
            nmt.send_command(NMT_RESET_COMMUNICATION)  # state 0: sends the boot-up message
            nmt.send_command(NMT_ENTER_PRE_OPERATIONAL)  # 0 -> 127 starts the heartbeat
            if self.auto_start:
                nmt.send_command(NMT_START)

    def stop_heartbeat(self) -> None:
        """Stop sending the heartbeat, as a node whose cable was cut (tests, FR-NET-05)."""
        with self.local.lock:
            self.local.nmt.stop_heartbeat()

    def resume_heartbeat(self) -> None:
        """Send the heartbeat again with the period of 0x1017."""
        with self.local.lock:
            self.local.nmt.start_heartbeat(int(self.read(0x1017)))

    # ----- state -----

    @property
    def nmt_state(self) -> str:
        """NMT state name, e.g. ``"OPERATIONAL"``."""
        state: str = self.local.nmt.state
        return state

    def now(self) -> float:
        """Simulation time in seconds; fixed while a TPDO is being built."""
        if self._frame_time is not None:
            return self._frame_time
        return self._clock()

    def provide(self, index: int, subindex: int, provider: RawProvider) -> None:
        """Compute the raw bytes of ``index:subindex`` with ``provider`` at every read."""
        self.variable(index, subindex)  # KeyError if the EDS does not have the object
        self.local.providers[(index, subindex)] = provider

    def read(self, index: int, subindex: int = 0) -> Any:
        """Current value of an object, decoded (raises ``SdoAbortedError``)."""
        var = self.variable(index, subindex)
        return var.decode_raw(self.local.get_data(index, subindex))

    def store(self, index: int, subindex: int, value: Any) -> None:
        """Write a value into the object dictionary, bypassing access checks."""
        var = self.variable(index, subindex)
        self.local.set_data(index, subindex, var.encode_raw(value))

    def variable(self, index: int, subindex: int = 0) -> ODVariable:
        """Object dictionary entry for ``index:subindex``."""
        entry = self.local.object_dictionary[index]
        if isinstance(entry, ODVariable):
            return entry
        var: ODVariable = entry[subindex]
        return var

    # ----- TPDO production -----

    def poll(self, now: float) -> None:
        """Send every TPDO whose event timer has expired (called by the tick thread)."""
        network = self._network
        if network is None:
            return
        with self.local.lock:
            if self.local.nmt.state != "OPERATIONAL":
                self._next_due.clear()
                return
            for comm in self._tpdo_comm_indices():
                frame = self._due_frame(comm, now)
                if frame is not None:
                    network.send_message(frame[0], frame[1])

    def _tpdo_comm_indices(self) -> list[int]:
        od = self.local.object_dictionary
        return [i for i in range(TPDO_COMM_FIRST, TPDO_COMM_LAST + 1) if i in od]

    def _optional(self, index: int, subindex: int) -> int:
        """Integer value of an object, or 0 if the object does not exist."""
        try:
            value: int = self.read(index, subindex)
        except (KeyError, SdoAbortedError):
            return 0
        return value

    def _due_frame(self, comm: int, now: float) -> tuple[int, bytes] | None:
        """COB-ID and payload of TPDO ``comm`` if it must be sent now."""
        cob_id = self._optional(comm, 1)
        period = self._optional(comm, 5) / 1000.0
        if (
            cob_id & COB_ID_INVALID
            or self._optional(comm, 2) not in EVENT_DRIVEN_TYPES
            or period <= 0
        ):
            self._next_due.pop(comm, None)
            return None
        due = self._next_due.get(comm)
        if due is None or self._periods.get(comm) != period:
            due = now  # first frame right away, also after a new event timer
        self._periods[comm] = period
        if now < due:
            return None
        self._next_due[comm] = due + period if now - due < period else now + period
        payload = self._build_payload(comm + TPDO_MAP_OFFSET, now)
        if payload is None:
            return None
        return cob_id & 0x7FF, payload

    def _build_payload(self, mapping: int, now: float) -> bytes | None:
        """Concatenate the mapped objects; ``None`` if the mapping cannot be sent."""
        payload = bytearray()
        self._frame_time = now
        try:
            for sub in range(1, self._optional(mapping, 0) + 1):
                entry = self._optional(mapping, sub)
                index, subindex, bits = entry >> 16, (entry >> 8) & 0xFF, entry & 0xFF
                if bits % 8:
                    logger.warning("TPDO 0x%04X: bit-level mapping is not simulated", mapping)
                    return None
                if index < 0x20:  # dummy entry: data type index, value ignored
                    payload.extend(bytes(bits // 8))
                else:
                    payload.extend(self.local.get_data(index, subindex)[: bits // 8])
        except (KeyError, SdoAbortedError) as exc:
            logger.warning("TPDO 0x%04X maps a missing object: %s", mapping, exc)
            return None
        finally:
            self._frame_time = None
        if len(payload) > 8:
            logger.warning("TPDO 0x%04X maps more than 8 bytes", mapping)
            return None
        return bytes(payload)

    # ----- SDO and NMT requests (python-can receive thread) -----

    def _on_sdo_request(self, can_id: int, data: bytearray, timestamp: float) -> None:
        if self.local.nmt.state == "STOPPED":
            return
        self.local.sdo.on_request(can_id, data, timestamp)

    def _on_nmt_command(self, can_id: int, data: bytearray, timestamp: float) -> None:
        command, node_id = struct.unpack_from("BB", data)
        if node_id not in (0, self.node_id):
            return
        if command == NMT_RESET_NODE:
            self._restore_saved(everything=True)
            self.boot()
        elif command == NMT_RESET_COMMUNICATION:
            self._restore_saved(everything=False)
            self.boot()

    # ----- store and restore (0x1010, 0x1011) -----

    def _read_store_restore(self, index: int, subindex: int, od: ODVariable) -> int | None:
        # Reading 0x1010/0x1011 tells that the device saves on command (value 1).
        if index in (0x1010, 0x1011) and subindex > 0:
            return 1
        return None

    def _write_store_restore(self, index: int, subindex: int, od: ODVariable, data: bytes) -> None:
        if index == 0x1010 and subindex > 0:
            if bytes(data) != STORE_SIGNATURE:
                raise SdoAbortedError(ABORT_DATA_CANNOT_BE_STORED)
            self._persistent = copy.deepcopy(self.local.data_store)
            logger.info("Simulated node %d: parameters stored", self.node_id)
        elif index == 0x1011 and subindex > 0:
            if bytes(data) != RESTORE_SIGNATURE:
                raise SdoAbortedError(ABORT_DATA_CANNOT_BE_STORED)
            self._persistent = {}
            logger.info("Simulated node %d: defaults restored at the next reset", self.node_id)

    def _restore_saved(self, everything: bool) -> None:
        """Reload the stored values: all of them, or only the communication area."""
        with self.local.lock:
            store = self.local.data_store
            saved = copy.deepcopy(self._persistent)
            if everything:
                store.clear()
                store.update(saved)
                return
            for index in [i for i in store if i in COMMUNICATION_AREA]:
                del store[index]
            store.update({i: v for i, v in saved.items() if i in COMMUNICATION_AREA})


def _device_name_object(name: str) -> ODVariable:
    """0x1008 Manufacturer device name, for EDS files that do not have it."""
    var = ODVariable("Manufacturer device name", 0x1008)
    var.data_type = objectdictionary.VISIBLE_STRING
    var.access_type = "const"
    var.default = name  # type: ignore[assignment]  # canopen types it as int, strings are valid
    return var
