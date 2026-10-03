"""Ring buffer of received frames (NFR-PER-01)."""

import can
import numpy as np
import pytest

from rumia_configurator.core.traffic import (
    FLAG_ERROR,
    FLAG_EXTENDED,
    FLAG_RTR,
    FLAG_TX,
    FrameBuffer,
)


def message(seq: int, **kwargs: object) -> can.Message:
    options: dict[str, object] = {
        "arbitration_id": 0x181,
        "data": seq.to_bytes(4, "little"),
        "timestamp": 1000.0 + seq,
        "is_extended_id": False,  # python-can defaults to extended identifiers
    }
    options.update(kwargs)
    return can.Message(**options)  # type: ignore[arg-type]


def sequences(frames: np.ndarray) -> list[int]:
    return [int.from_bytes(bytes(row[:4]), "little") for row in frames["data"]]


def test_fields_are_stored() -> None:
    buffer = FrameBuffer(8)
    buffer.append(message(1, dlc=4), now=5.0)
    buffer.append(message(2, arbitration_id=0x18FF0001, is_extended_id=True), now=6.0)
    buffer.append(
        can.Message(arbitration_id=0x701, is_remote_frame=True, dlc=1, is_extended_id=False),
        now=7.0,
    )
    buffer.append(
        can.Message(arbitration_id=0x204, is_error_frame=True, data=[0] * 8, is_extended_id=False),
        now=8.0,
    )
    buffer.append(message(3), tx=True, now=9.0)
    frames = buffer.read_since(0).frames
    assert list(frames["can_id"]) == [0x181, 0x18FF0001, 0x701, 0x204, 0x181]
    assert list(frames["rx_time"]) == [5.0, 6.0, 7.0, 8.0, 9.0]
    assert frames["timestamp"][0] == 1001.0
    assert frames["dlc"][0] == 4
    assert bytes(frames["data"][0]) == bytes([1, 0, 0, 0, 0, 0, 0, 0])
    flags = list(frames["flags"])
    assert flags == [0, FLAG_EXTENDED, FLAG_RTR, FLAG_ERROR, FLAG_TX]
    assert (buffer.written, buffer.error_frames, buffer.tx_frames) == (5, 1, 1)


def test_readers_have_their_own_cursor() -> None:
    buffer = FrameBuffer(16)
    for seq in range(5):
        buffer.append(message(seq))
    first = buffer.read_since(0)
    late = buffer.read_since(3)
    assert sequences(first.frames) == [0, 1, 2, 3, 4]
    assert sequences(late.frames) == [3, 4]
    assert first.cursor == late.cursor == 5
    buffer.append(message(5))
    assert sequences(buffer.read_since(first.cursor).frames) == [5]
    assert len(buffer.read_since(6).frames) == 0  # nothing new


def test_wrap_around_keeps_the_order() -> None:
    buffer = FrameBuffer(4)
    cursor = 0
    seen: list[int] = []
    for seq in range(11):
        buffer.append(message(seq))
        if seq % 3 == 2:  # read now and then, never more than 4 behind
            result = buffer.read_since(cursor)
            assert result.lost == 0
            seen += sequences(result.frames)
            cursor = result.cursor
    seen += sequences(buffer.read_since(cursor).frames)
    assert seen == list(range(11))
    assert sequences(buffer.latest(10)) == [7, 8, 9, 10]


def test_a_reader_left_behind_is_told_how_many_it_lost() -> None:
    buffer = FrameBuffer(4)
    for seq in range(10):
        buffer.append(message(seq))
    result = buffer.read_since(0)
    assert result.lost == 6
    assert sequences(result.frames) == [6, 7, 8, 9]


def test_received_after_finds_the_last_second() -> None:
    buffer = FrameBuffer(8)
    for seq in range(12):  # wraps: only 4..11 remain
        buffer.append(message(seq), now=float(seq))
    assert sequences(buffer.received_after(8.5)) == [9, 10, 11]
    assert sequences(buffer.received_after(-1.0)) == list(range(4, 12))
    assert len(buffer.received_after(11.0)) == 0


def test_copies_are_independent() -> None:
    buffer = FrameBuffer(2)
    buffer.append(message(1))
    frames = buffer.read_since(0).frames
    buffer.append(message(2))
    buffer.append(message(3))  # overwrites the slot of frame 1
    assert sequences(frames) == [1]


def test_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError):
        FrameBuffer(0)
