"""Qt side of the network: scan in a worker, heartbeat alarm timer, node list, profiles.

:class:`NetworkController` owns the :class:`NodeRegistry` and the
:class:`ProfileRegistry` of the open connection. After every identity read
the node is recognised and the EDS of its product is loaded (FR-NET-03,
FR-NET-08); the user can choose another profile for the session.

The scan and the identity reads are SDO transactions: they run in a pool
with **one** thread, so two transactions never overlap. A 4 Hz timer
in the GUI thread checks the heartbeats and publishes the node list.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QThreadPool, QTimer, Signal, SignalInstance

from rumia_configurator.core.connection import BACKENDS, ConnectionService, ConnectionState
from rumia_configurator.core.network import (
    BROADCAST,
    NmtCommand,
    NodeInfo,
    NodeRegistry,
    send_nmt,
)
from rumia_configurator.profiles.association import ProfileRegistry
from rumia_configurator.profiles.catalog import Product
from rumia_configurator.profiles.eds import EdsLoadError

logger = logging.getLogger(__name__)

CHECK_INTERVAL_MS = 250  # heartbeat alarm within 250 ms of the deadline (FR-NET-05)
SHUTDOWN_WAIT_MS = 5000


class NetworkController(QObject):
    """Scan, identity reads and heartbeat monitoring for the network panel."""

    nodes_changed = Signal(list)  # list[NodeInfo], by Node-ID
    scan_running = Signal(bool)
    scan_finished = Signal(int)  # number of nodes known after the scan
    scan_failed = Signal(str)  # technical detail, for the log and the status bar
    heartbeat_alarm = Signal(int, bool)  # node_id, missing
    command_verified = Signal(
        object, int, object
    )  # NmtCommand, node_id (0 = all), dict of outcomes; dict does not cross threads
    command_failed = Signal(object, int, str)  # NmtCommand, node_id, technical detail
    profiles_changed = Signal(object)  # dict[int, NodeProfile]
    profile_failed = Signal(int, object)  # node_id, EdsLoadError
    _scan_done = Signal(int)  # from the worker; delivered in the GUI thread

    def __init__(self, service: ConnectionService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._registry: NodeRegistry | None = None
        self._profiles: ProfileRegistry | None = None
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)  # one SDO transaction at a time
        self._queued: set[int] = set()
        self._scanning = False
        self._closed = False
        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self.tick)
        self._scan_done.connect(self._finish_scan)

    @property
    def registry(self) -> NodeRegistry | None:
        return self._registry

    @property
    def profiles(self) -> ProfileRegistry | None:
        return self._profiles

    @property
    def scanning(self) -> bool:
        return self._scanning

    def on_connection_state(self, state: ConnectionState, _failure: object = None) -> None:
        """Start following the network when connected; forget it otherwise."""
        if state == ConnectionState.CONNECTED and self._registry is None:
            network = self._service.network
            config = self._service.config
            if network is None or config is None:
                return
            backend = BACKENDS.get(config.backend)
            known = config.backend == "virtual" or (backend is not None and backend.needs_bitrate)
            self._registry = NodeRegistry(network, config.bitrate if known else None)
            self._profiles = ProfileRegistry()  # manual choices last for the session
            self._queued.clear()
            self._timer.start()
        elif state != ConnectionState.CONNECTED and self._registry is not None:
            self._timer.stop()
            self._pool.waitForDone(SHUTDOWN_WAIT_MS)
            self._registry.close()
            self._registry = None
            self._profiles = None
            self._scanning = False
        self.nodes_changed.emit(self._registry.snapshot() if self._registry else [])
        self.profiles_changed.emit(self._profiles.all() if self._profiles else {})

    def scan(self) -> None:
        """Scan the network in the worker; ignored if a scan is running."""
        registry = self._registry
        if registry is None or self._scanning:
            return
        self._scanning = True
        self.scan_running.emit(True)
        self._pool.start(lambda: self._scan_worker(registry))

    def send_command(self, command: NmtCommand, node_id: int = BROADCAST) -> None:
        """Send an NMT command in the worker, then check its effect on the heartbeat.

        Confirmation, when needed, is asked before calling this (rule 5).
        """
        registry = self._registry
        if registry is None:
            return
        self._pool.start(lambda: self._command_worker(registry, command, node_id))

    def associate_product(self, node_id: int, product: Product) -> None:
        """Use ``product`` for ``node_id`` until disconnection (worker)."""
        profiles = self._profiles
        if profiles is not None:
            self._pool.start(lambda: self._associate(node_id, profiles.associate_product, product))

    def associate_file(self, node_id: int, path: Path) -> None:
        """Use the EDS or DCF at ``path`` for ``node_id``; errors with ``profile_failed``."""
        profiles = self._profiles
        if profiles is not None:
            self._pool.start(lambda: self._associate(node_id, profiles.associate_file, path))

    def associate_none(self, node_id: int) -> None:
        """No profile for ``node_id`` until disconnection."""
        profiles = self._profiles
        if profiles is not None:
            self._pool.start(lambda: self._associate(node_id, profiles.associate_none))

    def automatic_profile(self, node_id: int) -> None:
        """Forget the choice of the user and recognise ``node_id`` again."""
        profiles, registry = self._profiles, self._registry
        if profiles is None or registry is None:
            return
        info = next((n for n in registry.snapshot() if n.node_id == node_id), None)
        self._pool.start(lambda: self._associate(node_id, profiles.clear, info))

    def shutdown(self) -> None:
        """Application exit: wait for the worker, stop listening, emit nothing more."""
        self._closed = True
        self._timer.stop()
        self._pool.waitForDone(SHUTDOWN_WAIT_MS)
        if self._registry is not None:
            self._registry.close()
            self._registry = None

    # ----- GUI thread -----

    def tick(self) -> None:
        """Check the heartbeats, read new identities, publish the list."""
        registry = self._registry
        if registry is None:
            return
        for node_id, missing in registry.check_heartbeats():
            self.heartbeat_alarm.emit(node_id, missing)
        pending = set(registry.pending_identity())
        self._queued &= pending
        new = sorted(pending - self._queued)
        if new and not self._scanning:  # the scan reads the identities itself
            self._queued.update(new)
            self._pool.start(lambda: self._identity_worker(registry, new))
        self.nodes_changed.emit(registry.snapshot())
        if self._profiles is not None:
            self.profiles_changed.emit(self._profiles.all())

    def _finish_scan(self, count: int) -> None:
        self._scanning = False
        self.scan_running.emit(False)
        if count >= 0:
            self.scan_finished.emit(count)

    # ----- worker -----

    def _emit(self, signal: SignalInstance, *args: object) -> None:
        if self._closed:
            return
        try:
            signal.emit(*args)
        except RuntimeError:  # the Qt object was deleted meanwhile
            logger.debug("Network signal dropped: controller deleted")

    def _scan_worker(self, registry: NodeRegistry) -> None:
        try:
            found = registry.scan()
            for node_id in registry.pending_identity():
                self._recognise(registry.read_identity(node_id))
            count = len(found)
        except Exception as exc:  # bus closed or adapter lost during the scan
            logger.exception("Scan failed")
            self._emit(self.scan_failed, f"{type(exc).__name__}: {exc}")
            count = -1
        self._emit(self._scan_done, count)

    def _command_worker(self, registry: NodeRegistry, command: NmtCommand, node_id: int) -> None:
        network = self._service.network
        if network is None:
            self._emit(self.command_failed, command, node_id, "not connected")
            return
        targets = [node_id] if node_id != BROADCAST else [n.node_id for n in registry.snapshot()]
        try:
            sent_at = registry.now()
            send_nmt(network, command, node_id)
            logger.info("NMT %s sent to node %d", command.name, node_id)
            outcomes = registry.verify_nmt(command, targets, sent_at)
        except Exception as exc:  # adapter lost while sending
            logger.exception("NMT %s to node %d failed", command.name, node_id)
            self._emit(self.command_failed, command, node_id, f"{type(exc).__name__}: {exc}")
            return
        self._emit(self.command_verified, command, node_id, outcomes)

    def _recognise(self, info: NodeInfo) -> None:
        """Worker: recognise the node and load the EDS of its product."""
        profiles = self._profiles
        if profiles is not None:
            profiles.on_identity(info)

    def _associate(self, node_id: int, action: Callable[..., object], *args: object) -> None:
        """Worker: run a manual association; a file that cannot be loaded is reported."""
        try:
            action(node_id, *args)
        except EdsLoadError as exc:
            logger.warning("EDS for node %d not loaded: %s", node_id, exc)
            self._emit(self.profile_failed, node_id, exc)
        except Exception:
            logger.exception("Profile of node %d not changed", node_id)

    def _identity_worker(self, registry: NodeRegistry, node_ids: list[int]) -> None:
        for node_id in node_ids:
            try:
                self._recognise(registry.read_identity(node_id))
            except Exception:  # the bus may close meanwhile
                logger.exception("Identity of node %d not read", node_id)
                return
