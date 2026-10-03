"""Live data for the interface: one 30 Hz timer reads the frame buffer (NFR-PER-03).

The receive thread fills the :class:`FrameBuffer`; the GUI thread never
touches the bus. :class:`LiveData` runs a 30 Hz ``QTimer`` in the GUI thread:
at every tick it takes the frames that are new since its cursor and emits
them with ``frames_received`` for the views that show live data (plots, bus
monitor). Every 500 ms it emits the traffic statistics for the status bar,
which would be unreadable if it changed 30 times a second.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal

from rumia_configurator.core.connection import ConnectionService
from rumia_configurator.core.traffic import FrameBuffer, TrafficStats

TICK_MS = 33  # 30 Hz
STATS_EVERY_TICKS = 15  # about 500 ms


class LiveData(QObject):
    """Moves new frames and statistics from the buffer to the views."""

    frames_received = Signal(object)  # numpy array of FRAME_DTYPE, oldest first
    stats_updated = Signal(object)  # TrafficStats

    def __init__(self, service: ConnectionService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._buffer: FrameBuffer | None = None
        self._cursor = 0
        self._lost = 0
        self._ticks = 0
        self.last_tick_ms = 0.0  # duration of the last tick, for the performance tests
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self.tick)

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    def start(self) -> None:
        """Follow the buffer of the connection just opened, from its first frame."""
        self._buffer = self._service.traffic
        self._cursor = 0
        self._lost = 0
        self._ticks = 0
        self._timer.start()
        self.tick()

    def stop(self) -> None:
        """Stop reading; the statistics go back to zero."""
        self._timer.stop()
        self._buffer = None
        self.stats_updated.emit(TrafficStats())

    def tick(self) -> None:
        """Read what is new; every ``STATS_EVERY_TICKS`` ticks, publish the statistics."""
        buffer = self._buffer
        if buffer is None:
            return
        started = time.perf_counter()
        result = buffer.read_since(self._cursor)
        self._cursor = result.cursor
        self._lost += result.lost
        if len(result.frames):
            self.frames_received.emit(result.frames)
        if self._ticks % STATS_EVERY_TICKS == 0:
            self.stats_updated.emit(self._service.traffic_stats(lost=self._lost))
        self._ticks += 1
        self.last_tick_ms = (time.perf_counter() - started) * 1000
