"""Frames per second and bus load (FR-CON-04).

The bus load is an **estimate**. The exact length of a frame depends on bit
stuffing (a bit added after five equal bits), which depends on the content
of the frame. The estimate uses the nominal length of a data frame plus an
average 10% for stuffing:

- standard identifier (11 bit): 47 + 8 * DLC bits;
- extended identifier (29 bit): 67 + 8 * DLC bits;
- remote frames carry no data bytes.

The nominal length counts SOF, arbitration, control, data, CRC, ACK, EOF and
the 3-bit interframe space. Error frames are counted apart and not included
in the load.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from rumia_configurator.core.traffic.buffer import (
    FLAG_ERROR,
    FLAG_EXTENDED,
    FLAG_RTR,
    FrameBuffer,
    Frames,
)

STANDARD_FRAME_BITS = 47
EXTENDED_FRAME_BITS = 67
STUFFING_FACTOR = 1.1  # average bit stuffing, see the module docstring
WINDOW_SECONDS = 1.0


def frame_bits(dlc: int, extended: bool = False, rtr: bool = False) -> float:
    """Estimated bits on the bus for one frame, stuffing included."""
    data_bits = 0 if rtr else 8 * min(dlc, 8)
    nominal = (EXTENDED_FRAME_BITS if extended else STANDARD_FRAME_BITS) + data_bits
    return nominal * STUFFING_FACTOR


def frames_bits(frames: Frames) -> float:
    """Estimated bits of every data and remote frame in ``frames`` (vectorised)."""
    flags = frames["flags"]
    usable = (flags & FLAG_ERROR) == 0
    extended = (flags & FLAG_EXTENDED) != 0
    rtr = (flags & FLAG_RTR) != 0
    data_bits = np.where(rtr, 0, 8 * np.minimum(frames["dlc"], 8))
    nominal = np.where(extended, EXTENDED_FRAME_BITS, STANDARD_FRAME_BITS) + data_bits
    return float(np.sum(nominal[usable])) * STUFFING_FACTOR


@dataclass(frozen=True)
class TrafficStats:
    """Traffic of the last second and totals since the connection."""

    frames_per_s: float = 0.0
    load_percent: float | None = None  # None: the bitrate is not known (SocketCAN)
    total_rx: int = 0
    total_tx: int = 0
    error_frames: int = 0
    lost: int = 0  # frames overwritten before a reader could take them


def compute_stats(
    buffer: FrameBuffer,
    bitrate: int | None,
    now: float | None = None,
    window: float = WINDOW_SECONDS,
    lost: int = 0,
) -> TrafficStats:
    """Statistics of ``buffer`` over the last ``window`` seconds before ``now``."""
    now = time.monotonic() if now is None else now
    recent = buffer.received_after(now - window)
    recent = recent[recent["rx_time"] <= now]
    data_frames = int(np.count_nonzero((recent["flags"] & FLAG_ERROR) == 0))
    load = None
    if bitrate:
        load = 100.0 * frames_bits(recent) / (bitrate * window)
    tx = buffer.tx_frames
    return TrafficStats(
        frames_per_s=data_frames / window,
        load_percent=load,
        total_rx=buffer.written - tx - buffer.error_frames,
        total_tx=tx,
        error_frames=buffer.error_frames,
        lost=lost,
    )
