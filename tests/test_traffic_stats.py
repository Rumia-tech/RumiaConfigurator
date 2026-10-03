"""Frames per second and estimated bus load (FR-CON-04).

Note: ``can.Message`` has an extended identifier by default; frames from the
bus carry the right flag, test frames must set ``is_extended_id=False``.
"""

import can
import pytest

from rumia_configurator.core.traffic import FrameBuffer, compute_stats, frame_bits


@pytest.mark.parametrize(
    ("dlc", "extended", "rtr", "nominal"),
    [
        (0, False, False, 47),
        (8, False, False, 111),
        (8, True, False, 131),
        (8, False, True, 47),  # a remote frame carries no data
    ],
)
def test_frame_bits(dlc: int, extended: bool, rtr: bool, nominal: int) -> None:
    assert frame_bits(dlc, extended, rtr) == pytest.approx(nominal * 1.1)


def fill(buffer: FrameBuffer, count: int, start: float, span: float, dlc: int = 8) -> None:
    for i in range(count):
        buffer.append(
            can.Message(arbitration_id=0x181, data=bytes(dlc), is_extended_id=False),
            now=start + span * (i + 1) / count,  # the window is (now - 1 s, now]
        )


def test_load_of_a_known_traffic() -> None:
    """1000 frames of 8 bytes in one second at 125 kbit/s."""
    buffer = FrameBuffer(4096)
    fill(buffer, 1000, start=10.0, span=1.0)
    stats = compute_stats(buffer, 125_000, now=11.0)
    assert stats.frames_per_s == 1000
    assert stats.load_percent == pytest.approx(100 * 1000 * 111 * 1.1 / 125_000)  # 97.7 %
    assert stats.total_rx == 1000


def test_only_the_last_second_counts() -> None:
    buffer = FrameBuffer(4096)
    fill(buffer, 500, start=0.0, span=1.0)  # old
    fill(buffer, 200, start=5.0, span=1.0)  # recent
    stats = compute_stats(buffer, 1_000_000, now=6.0)
    assert stats.frames_per_s == 200
    assert stats.total_rx == 700


def test_error_and_sent_frames() -> None:
    buffer = FrameBuffer(64)
    buffer.append(
        can.Message(arbitration_id=0x601, data=bytes(8), is_extended_id=False), tx=True, now=1.0
    )
    buffer.append(can.Message(arbitration_id=0x581, data=bytes(8), is_extended_id=False), now=1.1)
    buffer.append(can.Message(arbitration_id=0x20, is_error_frame=True, data=bytes(8)), now=1.2)
    stats = compute_stats(buffer, 500_000, now=1.5)
    assert stats.frames_per_s == 2  # error frames are counted apart
    assert (stats.total_rx, stats.total_tx, stats.error_frames) == (1, 1, 1)
    assert stats.load_percent == pytest.approx(100 * 2 * 111 * 1.1 / 500_000)


def test_no_load_without_bitrate() -> None:
    buffer = FrameBuffer(8)
    fill(buffer, 5, start=0.0, span=0.5)
    stats = compute_stats(buffer, None, now=1.0)
    assert stats.load_percent is None
    assert stats.frames_per_s == 5
