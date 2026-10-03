"""Nodes on the network: scan, boot-up, heartbeat, identity (FR-NET-01, FR-NET-02, FR-NET-05).

The application side is ``app_network`` (a plain ``canopen.Network``) or a
real :class:`ConnectionService`; the nodes are the simulated ones.
"""

import time
from collections.abc import Callable, Iterator

import can
import canopen
import pytest

from rumia_configurator.core.connection import ConnectionService
from rumia_configurator.core.network import NmtState, NodeRegistry, SeenBy
from rumia_configurator.core.simulator import IncliSenseNode, Simulator, SmartImuNode
from rumia_configurator.core.traffic import FLAG_TX


@pytest.fixture
def registry(app_network: canopen.Network) -> Iterator[NodeRegistry]:
    nodes = NodeRegistry(app_network, 1_000_000)
    yield nodes
    nodes.close()


def wait_until(condition: Callable[[], bool], timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


def ids(registry: NodeRegistry) -> list[int]:
    return [info.node_id for info in registry.snapshot()]


def node(registry: NodeRegistry, node_id: int):  # type: ignore[no-untyped-def]
    return next(info for info in registry.snapshot() if info.node_id == node_id)


def test_scan_finds_and_identifies_the_nodes(registry: NodeRegistry, simulator: Simulator) -> None:
    assert registry.scan() == [10, 29]
    for node_id in registry.pending_identity():
        registry.read_identity(node_id)
    imu, incli = node(registry, 29), node(registry, 10)
    assert (imu.name, incli.name) == ("Smart IMU", "INCLI Sense")
    assert (imu.vendor_id, imu.product_code, imu.revision, imu.serial) == (0, 0, 0, 0)
    assert imu.heartbeat_ms == incli.heartbeat_ms == 1000
    assert imu.identity_read and imu.identity_error is None
    assert registry.pending_identity() == []


def test_nodes_appear_by_themselves(registry: NodeRegistry, simulator: Simulator) -> None:
    """No scan: boot-up and heartbeat are enough (passive listening)."""
    assert wait_until(lambda: ids(registry) == [10, 29])
    # The first heartbeat is sent in Pre-operational, the next ones in Operational.
    assert wait_until(lambda: node(registry, 29).nmt_state == NmtState.OPERATIONAL)
    assert node(registry, 29).seen_by in (SeenBy.BOOTUP, SeenBy.HEARTBEAT)
    assert registry.pending_identity() == [10, 29]


def test_nmt_state_follows_the_heartbeat(
    registry: NodeRegistry, simulator: Simulator, app_network: canopen.Network
) -> None:
    simulator.node(29).store(0x1017, 0, 50)  # faster heartbeat for the test
    app_network.send_message(0, [0x02, 29])  # NMT Stop
    assert wait_until(
        lambda: 29 in ids(registry) and node(registry, 29).nmt_state == NmtState.STOPPED
    )
    app_network.send_message(0, [0x80, 29])  # NMT Enter pre-operational
    assert wait_until(lambda: node(registry, 29).nmt_state == NmtState.PRE_OPERATIONAL)


def test_missing_heartbeat_raises_and_clears_the_alarm(
    registry: NodeRegistry, simulator: Simulator
) -> None:
    """Acceptance of FR-NET-05: alarm after 1.5 x 0x1017, cleared when it comes back."""
    sim = simulator.node(29)
    sim.store(0x1017, 0, 100)
    assert wait_until(lambda: 29 in ids(registry))
    assert registry.read_identity(29).heartbeat_ms == 100
    time.sleep(0.12)
    assert registry.check_heartbeats() == []

    sim.stop_heartbeat()
    time.sleep(0.3)  # more than 1.5 x 100 ms
    assert registry.check_heartbeats() == [(29, True)]
    assert node(registry, 29).heartbeat_missing
    assert node(registry, 29).silent_for >= 0.15
    assert registry.check_heartbeats() == []  # reported once

    sim.resume_heartbeat()
    assert wait_until(lambda: registry.check_heartbeats() == [(29, False)], timeout=1.0)
    assert not node(registry, 29).heartbeat_missing
    assert not node(registry, 10).heartbeat_missing


def test_no_alarm_when_the_heartbeat_is_off(registry: NodeRegistry, simulator: Simulator) -> None:
    sim = simulator.node(29)
    assert wait_until(lambda: 29 in ids(registry))
    sim.store(0x1017, 0, 0)  # the node stops producing heartbeats
    info = registry.read_identity(29)
    assert info.heartbeat_ms == 0 and info.heartbeat_off
    time.sleep(0.3)
    assert registry.check_heartbeats() == []


def test_a_node_without_a_name_stays_in_the_list(
    app_network: canopen.Network, sim_channel: str
) -> None:
    nameless = IncliSenseNode()
    del nameless.local.object_dictionary[0x1008]  # like the real Smart IMU today
    registry = NodeRegistry(app_network, 1_000_000)
    try:
        with Simulator([nameless], channel=sim_channel):
            assert registry.scan() == [10]
            info = registry.read_identity(10)
    finally:
        registry.close()
    assert info.name is None
    assert info.identity_error is not None and "0x1008:00 abort 0x06020000" in info.identity_error
    assert info.product_code == 0  # the rest was read


def test_pdos_do_not_make_nodes_appear(registry: NodeRegistry, sim_channel: str) -> None:
    sender = can.Bus(interface="virtual", channel=sim_channel)
    try:
        for can_id in (0x1AA, 0x2AA, 0x0AA):  # PDOs and EMCY of node 42
            sender.send(can.Message(arbitration_id=can_id, data=bytes(6), is_extended_id=False))
        time.sleep(0.2)
    finally:
        sender.shutdown()
    assert registry.snapshot() == []


def test_boot_up_asks_for_the_identity_again(
    registry: NodeRegistry, simulator: Simulator, app_network: canopen.Network
) -> None:
    assert wait_until(lambda: 29 in ids(registry))
    registry.read_identity(29)
    assert 29 not in registry.pending_identity()
    app_network.send_message(0, [0x81, 29])  # NMT Reset node
    assert wait_until(lambda: 29 in registry.pending_identity())


def test_scan_requests_are_recorded_as_sent(simulator: Simulator, sim_channel: str) -> None:
    service = ConnectionService()
    service.connect_virtual(sim_channel)
    try:
        assert service.network is not None and service.traffic is not None
        registry = NodeRegistry(service.network, 1_000_000)
        try:
            registry.scan()
        finally:
            registry.close()
        frames = service.traffic.latest(1000)
        sent = frames[(frames["flags"] & FLAG_TX) != 0]["can_id"].tolist()
        assert sorted(set(sent)) == list(range(0x601, 0x680))
    finally:
        service.disconnect()


def test_scan_waits_longer_on_slow_buses(app_network: canopen.Network) -> None:
    fast = NodeRegistry(app_network, 1_000_000)
    slow = NodeRegistry(app_network, 10_000)
    unknown = NodeRegistry(app_network, None)
    try:
        assert fast.scan_window() == unknown.scan_window() == 1.0
        assert slow.scan_window() > 6.0  # 254 frames of about 122 bits at 10 kbit/s
    finally:
        for registry in (fast, slow, unknown):
            registry.close()


def test_identity_of_a_simulated_smart_imu_without_scan(
    app_network: canopen.Network, sim_channel: str
) -> None:
    """Reading the identity of a node found only by heartbeat registers it too."""
    with Simulator([SmartImuNode()], channel=sim_channel):
        registry = NodeRegistry(app_network, 1_000_000)
        try:
            info = registry.read_identity(29)
        finally:
            registry.close()
    assert info.name == "Smart IMU"
