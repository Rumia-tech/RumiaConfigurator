"""Simulated nodes on the virtual bus (FR-CON-06).

The application side is a plain ``canopen.Network`` (fixture ``app_network``):
these tests talk to the simulator exactly as the application will.
"""

import struct
import time
from collections.abc import Callable
from dataclasses import dataclass

import can
import canopen
import pytest
from canopen.sdo.exceptions import SdoAbortedError, SdoCommunicationError

from conftest import FrameRecorder
from rumia_configurator.core.simulator import (
    INCLI_SENSE_NODE_ID,
    SMART_IMU_NODE_ID,
    IncliSenseNode,
    Simulator,
    SmartImuNode,
)
from rumia_configurator.profiles.eds import bundled_eds, load_object_dictionary

IMU = SMART_IMU_NODE_ID
INCLI = INCLI_SENSE_NODE_ID
SAVE = 0x65766173  # "save" as UNSIGNED32 little-endian
LOAD = 0x64616F6C  # "load"


def remote(network: canopen.Network, node_id: int, product: str) -> canopen.RemoteNode:
    """A remote node on the application side, with the bundled EDS."""
    od = load_object_dictionary(bundled_eds(product), node_id).od
    node = canopen.RemoteNode(node_id, od)
    network.add_node(node)
    return node


def nmt(network: canopen.Network, command: int, node_id: int) -> None:
    network.send_message(0, [command, node_id])


def frames_during(recorder: FrameRecorder, can_id: int, seconds: float) -> list[can.Message]:
    recorder.clear()
    time.sleep(seconds)
    return recorder.with_id(can_id)


def is_heartbeat(node_id: int, state: int) -> Callable[[can.Message], bool]:
    return lambda f: f.arbitration_id == 0x700 + node_id and bytes(f.data) == bytes([state])


# ----- acceptance -----


def test_scan_finds_both_nodes(simulator: Simulator, app_network: canopen.Network) -> None:
    """T1.2 acceptance: a scan of the virtual bus finds the two simulated nodes."""
    app_network.scanner.search()
    deadline = time.monotonic() + 2
    while set(app_network.scanner.nodes) != {IMU, INCLI} and time.monotonic() < deadline:
        time.sleep(0.05)
    assert sorted(app_network.scanner.nodes) == [INCLI, IMU]


# ----- NMT and heartbeat -----


def test_nodes_boot_up_and_go_operational(simulator: Simulator, recorder: FrameRecorder) -> None:
    for node_id in (IMU, INCLI):
        assert recorder.wait_for(is_heartbeat(node_id, 0)) is not None  # boot-up
        assert simulator.node(node_id).nmt_state == "OPERATIONAL"


def test_heartbeat_follows_1017(
    simulator: Simulator, app_network: canopen.Network, recorder: FrameRecorder
) -> None:
    node = remote(app_network, IMU, "smart_imu")
    assert node.sdo[0x1017].raw == 1000
    node.sdo[0x1017].raw = 50
    beats = frames_during(recorder, 0x700 + IMU, 0.5)
    assert len(beats) >= 6
    assert all(bytes(beat.data) == b"\x05" for beat in beats)


def test_stopped_node_sends_nothing_and_ignores_sdo(
    simulator: Simulator, app_network: canopen.Network, recorder: FrameRecorder
) -> None:
    node = remote(app_network, IMU, "smart_imu")
    node.sdo[0x1017].raw = 50
    nmt(app_network, 0x02, IMU)  # Stop
    assert recorder.wait_for(is_heartbeat(IMU, 4)) is not None
    assert frames_during(recorder, 0x180 + IMU, 0.6) == []
    node.sdo.RESPONSE_TIMEOUT = 0.1
    node.sdo.MAX_RETRIES = 1  # one attempt: 0 would retry forever
    with pytest.raises(SdoCommunicationError):
        node.sdo.upload(0x1000, 0)

    nmt(app_network, 0x01, IMU)  # Start
    recorder.clear()
    assert recorder.wait_for(lambda f: f.arbitration_id == 0x180 + IMU) is not None


def test_broadcast_pre_operational_stops_pdos_of_all_nodes(
    simulator: Simulator, app_network: canopen.Network, recorder: FrameRecorder
) -> None:
    nmt(app_network, 0x80, 0)
    time.sleep(0.05)
    assert simulator.node(IMU).nmt_state == "PRE-OPERATIONAL"
    assert simulator.node(INCLI).nmt_state == "PRE-OPERATIONAL"
    recorder.clear()
    time.sleep(0.6)
    assert [f for f in recorder.frames if 0x180 <= f.arbitration_id < 0x300] == []


def test_reset_node_boots_again_with_default_values(
    simulator: Simulator, app_network: canopen.Network, recorder: FrameRecorder
) -> None:
    node = remote(app_network, IMU, "smart_imu")
    node.sdo[0x1800][5].raw = 100
    recorder.clear()
    nmt(app_network, 0x81, IMU)  # Reset node
    assert recorder.wait_for(is_heartbeat(IMU, 0)) is not None
    assert node.sdo[0x1800][5].raw == 500
    assert simulator.node(IMU).nmt_state == "OPERATIONAL"


def test_stored_values_survive_reset_until_restore(
    simulator: Simulator, app_network: canopen.Network, recorder: FrameRecorder
) -> None:
    node = remote(app_network, IMU, "smart_imu")
    node.sdo[0x1800][5].raw = 100
    node.sdo[0x1010][1].raw = SAVE
    assert node.sdo[0x1010][1].raw == 1  # reads as "saves on command"
    nmt(app_network, 0x81, IMU)
    assert recorder.wait_for(is_heartbeat(IMU, 0)) is not None
    assert node.sdo[0x1800][5].raw == 100

    node.sdo[0x1011][1].raw = LOAD
    recorder.clear()
    nmt(app_network, 0x81, IMU)
    assert recorder.wait_for(is_heartbeat(IMU, 0)) is not None
    assert node.sdo[0x1800][5].raw == 500


# ----- SDO aborts -----


@pytest.mark.parametrize(
    ("index", "subindex", "value", "code"),
    [
        (0x1010, 1, 0x12345678, 0x08000020),  # wrong store signature
        (0x1011, 1, SAVE, 0x08000020),  # wrong restore signature
        (0x6001, 0, 5, 0x06010002),  # read-only measurement
    ],
)
def test_invalid_writes_are_aborted(
    simulator: Simulator,
    app_network: canopen.Network,
    index: int,
    subindex: int,
    value: int,
    code: int,
) -> None:
    node = remote(app_network, IMU, "smart_imu")
    size = 2 if index == 0x6001 else 4
    with pytest.raises(SdoAbortedError) as error:
        node.sdo.download(index, subindex, value.to_bytes(size, "little"))
    assert error.value.code == code


# ----- identity -----


def test_identity_over_sdo(simulator: Simulator, app_network: canopen.Network) -> None:
    imu = remote(app_network, IMU, "smart_imu")
    incli = remote(app_network, INCLI, "incli_sense")
    # The Smart IMU EDS has no 0x1008: the simulator answers with its ProductName.
    assert imu.sdo.upload(0x1008, 0) == b"Smart IMU"
    assert imu.sdo[0x1018][2].raw == 0
    assert imu.sdo[0x6007].raw == 3
    assert incli.sdo[0x1008].raw == "INCLI Sense"
    assert incli.sdo[0x1000].raw == 0x0002019A  # CiA 410, two axes


# ----- PDOs -----


def test_smart_imu_pdos_carry_plausible_data(simulator: Simulator, recorder: FrameRecorder) -> None:
    time.sleep(1.1)  # event timer 500 ms: frames at 0, 0.5 and 1.0 s
    accelerations = recorder.with_id(0x180 + IMU)
    rates = recorder.with_id(0x280 + IMU)
    assert 2 <= len(accelerations) <= 4
    assert 2 <= len(rates) <= 4
    for frame in accelerations:
        x, y, z = struct.unpack("<hhh", frame.data)
        assert 900 < (x * x + y * y + z * z) ** 0.5 < 1100  # about 1 g, in mg
    for frame in rates:
        assert all(abs(v) < 10_000 for v in struct.unpack("<hhh", frame.data))  # mdps


def test_incli_pdo_every_100_ms(simulator: Simulator, recorder: FrameRecorder) -> None:
    frames = frames_during(recorder, 0x180 + INCLI, 1.0)
    assert 8 <= len(frames) <= 12
    for frame in frames:
        longitudinal, lateral = struct.unpack("<hh", frame.data)
        assert abs(longitudinal) <= 520  # 0.01 degree units: within ±5.2 degrees
        assert abs(lateral) <= 320


def test_new_event_timer_applies_at_once(
    simulator: Simulator, app_network: canopen.Network, recorder: FrameRecorder
) -> None:
    node = remote(app_network, IMU, "smart_imu")
    node.sdo[0x1800][5].raw = 50
    assert len(frames_during(recorder, 0x180 + IMU, 0.5)) >= 7


def test_disabled_tpdo_is_not_sent(
    simulator: Simulator, app_network: canopen.Network, recorder: FrameRecorder
) -> None:
    node = remote(app_network, IMU, "smart_imu")
    node.sdo[0x1800][1].raw = 0x80000000 | 0x180 + IMU
    assert frames_during(recorder, 0x180 + IMU, 0.6) == []
    assert recorder.with_id(0x280 + IMU) != []


def test_remapped_tpdo_is_sent_as_configured(
    simulator: Simulator, app_network: canopen.Network, recorder: FrameRecorder
) -> None:
    node = remote(app_network, IMU, "smart_imu")
    mapping = node.sdo[0x1A00]
    mapping[0].raw = 0
    mapping[1].raw = 0x60030010  # only Acc_z
    mapping[0].raw = 1
    node.sdo[0x1800][5].raw = 50
    recorder.clear()
    frame = recorder.wait_for(lambda f: f.arbitration_id == 0x180 + IMU and len(f.data) == 2)
    assert frame is not None
    assert 900 < struct.unpack("<h", frame.data)[0] < 1100


# ----- INCLI Sense, CiA 410 -----


@dataclass(frozen=True)
class FixedSlope:
    longitudinal: float
    lateral: float

    def sample(self, t: float) -> tuple[float, float]:
        return self.longitudinal, self.lateral


def test_incli_inversion_preset_and_offsets(app_network: canopen.Network, sim_channel: str) -> None:
    sim_node = IncliSenseNode(motion=FixedSlope(2.5, -1.0))  # type: ignore[arg-type]
    with Simulator([sim_node], channel=sim_channel):
        node = remote(app_network, INCLI, "incli_sense")
        assert node.sdo[0x6010].raw == 250  # resolution 0.01 degree
        assert node.sdo[0x6020].raw == -100

        node.sdo[0x6011].raw = 0x01  # invert
        assert node.sdo[0x6010].raw == -250

        node.sdo[0x6011].raw = 0x03  # invert, apply offsets
        node.sdo[0x6012].raw = 0  # preset: zero here
        assert node.sdo[0x6013].raw == 250
        assert node.sdo[0x6010].raw == 0
        node.sdo[0x6014].raw = 5  # differential offset
        assert node.sdo[0x6010].raw == 5

        node.sdo[0x6000].raw = 100  # resolution 0.1 degree
        assert node.sdo[0x6020].raw == -10
        with pytest.raises(SdoAbortedError) as error:
            node.sdo[0x6000].raw = 7
        assert error.value.code == 0x06090030


# ----- the Simulator object -----


def test_duplicate_node_ids_are_refused() -> None:
    with pytest.raises(ValueError, match="same Node-ID"):
        Simulator([SmartImuNode(), SmartImuNode()])


def test_stop_is_idempotent_and_closes_the_bus(sim_channel: str) -> None:
    sim = Simulator([SmartImuNode(auto_start=False)], channel=sim_channel)
    sim.start()
    assert sim.running
    assert sim.node(IMU).nmt_state == "PRE-OPERATIONAL"
    sim.stop()
    sim.stop()
    assert not sim.running


def test_open_error_is_raised_not_hidden() -> None:
    sim = Simulator([SmartImuNode()], interface="no-such-interface", channel="x")
    with pytest.raises(can.CanInterfaceNotImplementedError):
        sim.start()
    assert not sim.running
