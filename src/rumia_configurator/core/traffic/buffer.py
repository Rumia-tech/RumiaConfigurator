"""Ring buffer of CAN frames, filled by the receive thread (NFR-PER-01).

One preallocated numpy array holds the most recent frames. The receive
thread (and the application, for the frames it sends) appends; any number of
readers take what is new since their own cursor. A reader that falls more
than one buffer behind is told how many frames it lost: frames are never
dropped silently.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import can
import numpy as np
import numpy.typing as npt

DEFAULT_CAPACITY = 1 << 18  # 262144 frames: about 52 s at 5000 frames/s, about 12 MB

# Bits of the ``flags`` field
FLAG_EXTENDED = 0x01
FLAG_RTR = 0x02
FLAG_ERROR = 0x04
FLAG_TX = 0x08  # sent by this application

FRAME_DTYPE = np.dtype(
    [
        ("rx_time", "f8"),  # time.monotonic() when the frame was stored: statistics
        ("timestamp", "f8"),  # timestamp given by python-can / the adapter (FR-DAT-03)
        ("can_id", "u4"),
        ("dlc", "u1"),
        ("flags", "u1"),
        ("data", "u1", (8,)),
    ]
)

Frames = npt.NDArray[np.void]


@dataclass(frozen=True)
class ReadResult:
    """Frames new for one reader, its next cursor and how many it missed."""

    frames: Frames
    cursor: int
    lost: int


class FrameBuffer:
    """Fixed-size ring of frames with independent reader cursors.

    A cursor is the total number of frames written when the reader last
    read; it starts at :attr:`written` (only new frames) or at 0 (everything
    still in the buffer).
    """

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._frames = np.zeros(capacity, dtype=FRAME_DTYPE)
        self._lock = threading.Lock()
        self._written = 0
        self._error_frames = 0
        self._tx_frames = 0

    @property
    def written(self) -> int:
        """Frames stored since the buffer was created."""
        return self._written

    @property
    def error_frames(self) -> int:
        """Error frames stored since the buffer was created."""
        return self._error_frames

    @property
    def tx_frames(self) -> int:
        """Frames sent by the application since the buffer was created."""
        return self._tx_frames

    def append(self, msg: can.Message, tx: bool = False, now: float | None = None) -> None:
        """Store ``msg``; ``tx`` marks a frame sent by the application."""
        flags = (
            (FLAG_EXTENDED if msg.is_extended_id else 0)
            | (FLAG_RTR if msg.is_remote_frame else 0)
            | (FLAG_ERROR if msg.is_error_frame else 0)
            | (FLAG_TX if tx else 0)
        )
        data = np.frombuffer(bytes(msg.data[:8]).ljust(8, b"\0"), dtype=np.uint8)
        rx_time = time.monotonic() if now is None else now
        record = (rx_time, msg.timestamp, msg.arbitration_id, msg.dlc, flags, data)
        with self._lock:
            self._frames[self._written % self.capacity] = record
            self._written += 1
            if flags & FLAG_ERROR:
                self._error_frames += 1
            if tx:
                self._tx_frames += 1

    def read_since(self, cursor: int) -> ReadResult:
        """Copy of the frames written after ``cursor``, oldest first."""
        with self._lock:
            written = self._written
            oldest = max(0, written - self.capacity)
            lost = max(0, oldest - cursor)
            start = max(cursor, oldest)
            frames = self._slice(start, written)
        return ReadResult(frames, written, lost)

    def received_after(self, rx_time: float) -> Frames:
        """Copy of the frames stored after ``rx_time`` (``time.monotonic()``).

        ``rx_time`` grows with every append (one writer at a time, under the
        lock), so a binary search finds the start: the cost does not depend
        on how long the session has been running.
        """
        with self._lock:
            written = self._written
            count = min(written, self.capacity)
            first = written - count
            low, high = 0, count
            while low < high:
                middle = (low + high) // 2
                if self._frames[(first + middle) % self.capacity]["rx_time"] <= rx_time:
                    low = middle + 1
                else:
                    high = middle
            return self._slice(first + low, written)

    def latest(self, count: int) -> Frames:
        """Copy of the last ``count`` frames (fewer if the buffer holds fewer)."""
        with self._lock:
            written = self._written
            start = max(0, written - min(count, self.capacity))
            return self._slice(start, written)

    def _slice(self, start: int, end: int) -> Frames:
        """Frames ``start`` to ``end`` (total counts), copied. Caller holds the lock."""
        if end <= start:
            return np.empty(0, dtype=FRAME_DTYPE)
        # Fancy indexing copies, and handles the wrap-around of the ring.
        frames: Frames = self._frames[np.arange(start, end) % self.capacity]
        return frames
