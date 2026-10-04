"""Acceptance of T1.3: 5000 frames/s for 30 s on the virtual bus, nothing lost (NFR-PER-01).

A generator on a second virtual bus sends frames with a sequence number at an
exact rate. The application side is a real :class:`ConnectionService`, with a
small buffer (about 3 s), so the reader must keep up as the 30 Hz GUI timer
does: if it fell behind, the buffer would report the lost frames.
"""

import threading
import time

import can
import pytest

from rumia_configurator.core.connection import ConnectionService
from rumia_configurator.core.traffic import TrafficStats

RATE = 5000  # frames per second
SECONDS = 30
FRAMES = RATE * SECONDS
CAPACITY = 1 << 14  # 16384 frames: about 3 s, so a reader that stalls loses frames
READ_INTERVAL = 1 / 30  # like the GUI timer


def test_5000_frames_per_second_for_30_seconds_without_losses(sim_channel: str) -> None:
    service = ConnectionService(buffer_capacity=CAPACITY)
    service.connect_virtual(sim_channel, bitrate=1_000_000)
    buffer = service.traffic
    assert buffer is not None
    generator = can.Bus(interface="virtual", channel=sim_channel, receive_own_messages=False)

    sent = {"elapsed": 0.0}

    def send_all() -> None:
        start = time.perf_counter()
        for seq in range(FRAMES):
            due = start + seq / RATE
            while time.perf_counter() < due:  # busy wait: sleep() is too coarse on Windows
                pass
            generator.send(can.Message(arbitration_id=0x181, data=seq.to_bytes(4, "little")))
        sent["elapsed"] = time.perf_counter() - start

    sender = threading.Thread(target=send_all, name="load-generator")
    received: list[int] = []
    lost = 0
    cursor = 0
    middle: TrafficStats | None = None
    started = time.monotonic()
    sender.start()
    try:
        while sender.is_alive() or cursor < FRAMES:
            time.sleep(READ_INTERVAL)
            result = buffer.read_since(cursor)
            cursor = result.cursor
            lost += result.lost
            received.extend(
                int.from_bytes(bytes(row[:4]), "little") for row in result.frames["data"]
            )
            if middle is None and time.monotonic() - started > SECONDS / 2:
                middle = service.traffic_stats()
            if time.monotonic() - started > SECONDS * 2:
                break  # never hang: the asserts below say what went wrong
    finally:
        sender.join()
        generator.shutdown()
        service.disconnect()

    if sent["elapsed"] > SECONDS * 1.05:
        pytest.fail(
            f"The test generator itself could not keep {RATE} frames/s "
            f"({FRAMES} frames in {sent['elapsed']:.1f} s): the machine is too busy, "
            "this says nothing about the receive path."
        )
    assert lost == 0
    assert len(received) == FRAMES
    assert received == list(range(FRAMES))  # nothing missing, nothing duplicated, in order
    assert middle is not None
    # A one-second sample: on a busy runner the generator falls behind for a moment and
    # catches up later (macOS CI measured 4724 frames/s), so the margin is wider here.
    assert middle.frames_per_s == pytest.approx(RATE, rel=0.10)
    assert middle.load_percent is not None and middle.load_percent > 0
