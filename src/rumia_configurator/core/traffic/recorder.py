"""Put every frame of the bus into the :class:`FrameBuffer`.

:class:`TrafficListener` is added to the one ``can.Notifier`` of the open
``canopen.Network``: it runs in the python-can receive thread, so no extra
thread is needed. :class:`RecordingNetwork` also stores the frames the
application sends, marked as TX, because they are part of the bus load and
of the bus monitor.
"""

from __future__ import annotations

import logging
from typing import Any

import can
import canopen

from rumia_configurator.core.traffic.buffer import FrameBuffer

logger = logging.getLogger(__name__)


class TrafficListener(can.Listener):
    """Receive thread: store every message, data or error frame."""

    def __init__(self, buffer: FrameBuffer) -> None:
        self.buffer = buffer

    def on_message_received(self, msg: can.Message) -> None:
        self.buffer.append(msg)

    def stop(self) -> None:
        """Nothing to release."""


class RecordingNetwork(canopen.Network):
    """``canopen.Network`` that also stores the frames it sends.

    Periodic sending (``send_periodic``: heartbeat, SYNC producer) is done by
    python-can tasks and is not recorded; the application does not use it yet.
    """

    def __init__(self, bus: can.BusABC, buffer: FrameBuffer) -> None:
        super().__init__(bus)
        self.traffic = buffer

    def send_message(self, can_id: int, data: Any, remote: bool = False) -> None:
        super().send_message(can_id, data, remote)
        msg = can.Message(
            arbitration_id=can_id,
            data=bytes(data) if not remote else b"",
            is_extended_id=can_id > 0x7FF,
            is_remote_frame=remote,
            timestamp=0.0,
        )
        try:
            self.traffic.append(msg, tx=True)
        except Exception:  # recording must never break sending
            logger.exception("Could not record a sent frame")
