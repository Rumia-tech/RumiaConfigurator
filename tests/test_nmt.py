"""NMT commands and their check on the heartbeat (FR-NET-04, NFR-REL-03)."""

import time
from collections.abc import Callable, Iterator

import pytest

from rumia_configurator.core.connection import ConnectionService
from rumia_configurator.core.network import (
    BROADCAST,
    NmtCommand,
    NmtOutcome,
    NmtState,
    NodeRegistry,
    nmt_frame,
    send_nmt,
)
from rumia_configurator.core.simulator import Simulator
from rumia_configurator.core.traffic import FLAG_TX


@pytest.fixture
def connected(
    simulator: Simulator, sim_channel: str
) -> Iterator[tuple[ConnectionService, NodeRegistry]]:
    """Application connected to the demo nodes, heartbeat every 100 ms, identities read."""
    for node in simulator.nodes:
        node.store(0x1017, 0, 100)
    service = ConnectionService()
    service.connect_virtual(sim_channel)
    assert service.network is not None
    registry = NodeRegistry(service.network, 1_000_000)
    assert wait_until(lambda: len(registry.snapshot()) == 2)
    for node_id in registry.pending_identity():
        registry.read_identity(node_id)
    yield service, registry
    registry.close()
    service.disconnect()


def wait_until(condition: Callable[[], bool], timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


def command(
    service: ConnectionService, registry: NodeRegistry, cmd: NmtCommand, node_id: int
) -> dict[int, NmtOutcome]:
    assert service.network is not None
    targets = [node_id] if node_id != BROADCAST else [10, 29]
    sent_at = registry.now()
    send_nmt(service.network, cmd, node_id)
    return registry.verify_nmt(cmd, targets, sent_at)


def state(registry: NodeRegistry, node_id: int) -> NmtState:
    return next(i.nmt_state for i in registry.snapshot() if i.node_id == node_id)


@pytest.mark.parametrize(
    ("cmd", "node_id", "frame"),
    [
        (NmtCommand.START, 29, b"\x01\x1d"),
        (NmtCommand.STOP, 29, b"\x02\x1d"),
        (NmtCommand.PRE_OPERATIONAL, BROADCAST, b"\x80\x00"),
        (NmtCommand.RESET_NODE, 127, b"\x81\x7f"),
        (NmtCommand.RESET_COMMUNICATION, 1, b"\x82\x01"),
    ],
)
def test_nmt_frames(cmd: NmtCommand, node_id: int, frame: bytes) -> None:
    assert nmt_frame(cmd, node_id) == frame


def test_node_id_out_of_range_is_refused() -> None:
    with pytest.raises(ValueError):
        nmt_frame(NmtCommand.START, 128)


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        (NmtCommand.STOP, NmtState.STOPPED),
        (NmtCommand.PRE_OPERATIONAL, NmtState.PRE_OPERATIONAL),
        (NmtCommand.START, NmtState.OPERATIONAL),
    ],
)
def test_state_commands_are_confirmed_by_the_heartbeat(
    connected: tuple[ConnectionService, NodeRegistry], cmd: NmtCommand, expected: NmtState
) -> None:
    service, registry = connected
    assert command(service, registry, cmd, 29) == {29: NmtOutcome.CONFIRMED}
    assert state(registry, 29) == expected


def test_command_to_the_whole_network(connected: tuple[ConnectionService, NodeRegistry]) -> None:
    service, registry = connected
    outcomes = command(service, registry, NmtCommand.PRE_OPERATIONAL, BROADCAST)
    assert outcomes == {10: NmtOutcome.CONFIRMED, 29: NmtOutcome.CONFIRMED}
    assert outcomes == command(service, registry, NmtCommand.START, BROADCAST)


@pytest.mark.parametrize("cmd", [NmtCommand.RESET_NODE, NmtCommand.RESET_COMMUNICATION])
def test_reset_is_confirmed_by_the_boot_up(
    connected: tuple[ConnectionService, NodeRegistry], cmd: NmtCommand
) -> None:
    service, registry = connected
    assert command(service, registry, cmd, 29) == {29: NmtOutcome.CONFIRMED}
    assert 29 in registry.pending_identity()  # read again after the restart


def test_silent_node_gives_no_heartbeat(
    connected: tuple[ConnectionService, NodeRegistry], simulator: Simulator
) -> None:
    service, registry = connected
    simulator.node(29).stop_heartbeat()
    started = time.monotonic()
    assert command(service, registry, NmtCommand.STOP, 29) == {29: NmtOutcome.NO_HEARTBEAT}
    assert time.monotonic() - started < 1.5  # 2 x 100 ms, at least 1 s


def test_heartbeat_off_is_not_verifiable(
    connected: tuple[ConnectionService, NodeRegistry], simulator: Simulator
) -> None:
    service, registry = connected
    simulator.node(29).store(0x1017, 0, 0)
    registry.read_identity(29)
    assert command(service, registry, NmtCommand.STOP, 29) == {29: NmtOutcome.NOT_VERIFIABLE}


def test_state_not_reached_is_not_confirmed(
    connected: tuple[ConnectionService, NodeRegistry], simulator: Simulator
) -> None:
    """A node that ignores the command keeps sending its old state."""
    service, registry = connected
    sim = simulator.node(29)
    network = sim._network
    assert network is not None
    network.unsubscribe(0, sim.local.nmt.on_command)  # the node no longer obeys NMT
    try:
        outcome = command(service, registry, NmtCommand.STOP, 29)
    finally:
        network.subscribe(0, sim.local.nmt.on_command)
    assert outcome == {29: NmtOutcome.NOT_CONFIRMED}


def test_commands_are_recorded_as_sent(connected: tuple[ConnectionService, NodeRegistry]) -> None:
    service, registry = connected
    assert service.traffic is not None
    before = service.traffic.written
    command(service, registry, NmtCommand.START, 29)
    frames = service.traffic.read_since(before).frames
    sent = frames[(frames["flags"] & FLAG_TX) != 0]
    nmt = sent[sent["can_id"] == 0]
    assert len(nmt) == 1
    assert bytes(nmt["data"][0][:2]) == b"\x01\x1d"
