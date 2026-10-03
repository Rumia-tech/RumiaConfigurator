"""Run simulated nodes on a CAN bus (FR-CON-06).

The simulator opens its own ``canopen.Network`` on a python-can bus. With the
``virtual`` interface every bus opened on the same channel in the same
process sees the frames of the others, so the application connects to the
channel and finds the simulated nodes as if they were real devices.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterable
from types import TracebackType
from typing import Any

import canopen

from rumia_configurator.core.simulator.node import SimulatedNode
from rumia_configurator.core.simulator.products import IncliSenseNode, SmartImuNode

logger = logging.getLogger(__name__)

DEMO_CHANNEL = "rumia-demo"
TICK_SECONDS = 0.01
# How long the receive thread blocks; it also bounds how long stop() waits for it.
NOTIFIER_CYCLE = 0.1


def default_demo_nodes() -> list[SimulatedNode]:
    """The nodes of demo mode: Smart IMU (ID 29) and INCLI Sense (ID 10)."""
    return [SmartImuNode(), IncliSenseNode()]


class Simulator:
    """Simulated nodes on one bus, with one tick thread for the TPDOs.

    Use it as a context manager, or call :meth:`start` and :meth:`stop`.
    ``bus_options`` go to ``can.Bus``: with a real adapter the simulator can
    play the devices for an application on another computer.
    """

    def __init__(
        self,
        nodes: Iterable[SimulatedNode],
        interface: str = "virtual",
        channel: str = DEMO_CHANNEL,
        tick: float = TICK_SECONDS,
        **bus_options: Any,
    ) -> None:
        self.nodes = list(nodes)
        ids = [node.node_id for node in self.nodes]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Two simulated nodes have the same Node-ID: {sorted(ids)}")
        self.interface = interface
        self.channel = channel
        self.tick = tick
        self._bus_options = bus_options
        if interface == "virtual":
            self._bus_options.setdefault("receive_own_messages", False)
        self._network: canopen.Network | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._t0 = 0.0

    @property
    def running(self) -> bool:
        """True between :meth:`start` and :meth:`stop`."""
        return self._network is not None

    def node(self, node_id: int) -> SimulatedNode:
        """The simulated node with ``node_id``."""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        raise KeyError(node_id)

    def clock(self) -> float:
        """Seconds since :meth:`start`."""
        return time.monotonic() - self._t0

    def start(self) -> None:
        """Open the bus, boot every node and start sending TPDOs.

        Errors opening the bus (``can.CanError``, ``OSError``) are raised to
        the caller: the simulator never falls back to another bus.
        """
        if self.running:
            return
        network = canopen.Network()
        network.NOTIFIER_CYCLE = NOTIFIER_CYCLE
        network.connect(interface=self.interface, channel=self.channel, **self._bus_options)
        self._network = network
        self._t0 = time.monotonic()
        for node in self.nodes:
            node.attach(network, self.clock)
            node.boot()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="can-simulator", daemon=True)
        self._thread.start()
        logger.info(
            "Simulator started on %s/%s with nodes %s",
            self.interface,
            self.channel,
            ", ".join(f"{node.product_name} ({node.node_id})" for node in self.nodes),
        )

    def stop(self) -> None:
        """Stop the TPDOs and the heartbeats and close the bus."""
        if self._thread is not None:
            self._stop.set()
            self._thread.join()
            self._thread = None
        network = self._network
        if network is None:
            return
        for node in self.nodes:
            node.detach()
        network.disconnect()
        self._network = None
        logger.info("Simulator stopped")

    def _run(self) -> None:
        while not self._stop.wait(self.tick):
            now = self.clock()
            for node in self.nodes:
                try:
                    node.poll(now)
                except Exception:  # one faulty node must not stop the others
                    logger.exception("Simulated node %d failed to send its TPDOs", node.node_id)

    def __enter__(self) -> Simulator:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()
