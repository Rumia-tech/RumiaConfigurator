"""Status bar: bus state, adapter, bitrate, frames/s, load, errors, last event (UI-LAY-04).

Bus state, adapter, bitrate and controller health come from the connection
(T1.1, FR-CON-04, FR-CON-08); frames/s, estimated bus load and lost frames
from the traffic statistics, twice a second (T1.3).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QLocale
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from rumia_configurator.core.connection import ConnectionState, ControllerStatus
from rumia_configurator.core.traffic import TrafficStats
from rumia_configurator.gui.theme.fonts import mono_font
from rumia_configurator.gui.theme.tokens import METRICS, TYPOGRAPHY
from rumia_configurator.gui.views.top_bar import format_bitrate
from rumia_configurator.gui.widgets.brand import StatusLed, refresh_style


class StatusBar(QFrame):
    """Deep Ink bar at the bottom of the window."""

    def __init__(self, bitrate: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "statusbar")
        m = METRICS
        self.setFixedHeight(m.statusbar_height)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(m.space_l, 0, m.space_l, 0)
        layout.setSpacing(m.space_l + 2)
        self.bus = StatusLed("stopped", "", self)
        layout.addWidget(self.bus)
        self.adapter = self._field(layout)
        self.bitrate = self._field(layout)
        self.frames = self._field(layout)
        self.load = self._field(layout)
        self.errors = self._field(layout)
        layout.addStretch(1)
        self.last_event = self._field(layout)
        self.last_event.setProperty("muted", "true")
        self._bitrate = bitrate
        self._event: str | None = None
        self._state = ConnectionState.DISCONNECTED
        self._adapter_text: str | None = None
        self._controller = ControllerStatus()
        self._traffic = TrafficStats()
        self.retranslate()

    def _field(self, layout: QHBoxLayout) -> QLabel:
        """Add a mono label to the bar and return it."""
        label = QLabel(self)
        label.setFont(mono_font(TYPOGRAPHY.small_px))
        layout.addWidget(label)
        return label

    def show_event(self, text: str) -> None:
        """Show the last event; the text must already be translated."""
        self._event = text
        self.last_event.setText(text)

    def set_connection(
        self, state: ConnectionState, adapter_text: str | None, bitrate: int
    ) -> None:
        """Show the connection state, the adapter (``None``: none chosen) and the bitrate."""
        self._state = state
        self._adapter_text = adapter_text
        self._bitrate = bitrate
        if state != ConnectionState.CONNECTED:
            self._controller = ControllerStatus()
            self._traffic = TrafficStats()
        self.retranslate()

    def set_traffic(self, stats: TrafficStats) -> None:
        """Show frames per second, estimated bus load and lost frames (FR-CON-04)."""
        self._traffic = stats
        self._show_traffic()

    def _show_traffic(self) -> None:
        stats = self._traffic
        locale = QLocale()  # follows the language of the interface
        self.frames.setText(
            self.tr("%1 frames/s").replace("%1", locale.toString(round(stats.frames_per_s)))
        )
        if stats.load_percent is None:
            load = "-"
        else:
            load = locale.toString(stats.load_percent, "f", 1) + " %"
        text = self.tr("load %1").replace("%1", load)
        if stats.lost:
            text += " · " + self.tr("lost %1").replace("%1", locale.toString(stats.lost))
        self.load.setText(text)
        self.load.setProperty("error", "true" if stats.lost else "false")
        refresh_style(self.load)

    def set_controller(self, status: ControllerStatus) -> None:
        """Show the CAN controller state and error counters (FR-CON-08)."""
        self._controller = status
        self._show_controller()

    def _show_controller(self) -> None:
        status = self._controller
        if self._state != ConnectionState.CONNECTED:
            text = self.tr("errors %1").replace("%1", "0")
        else:
            states = {
                "active": self.tr("error active"),
                "passive": self.tr("error passive"),
                "bus-off": self.tr("bus-off"),
            }
            parts = [states[status.state] if status.state else self.tr("controller n/a")]
            if status.tx_errors is not None and status.rx_errors is not None:
                parts.append(f"TEC {status.tx_errors} REC {status.rx_errors}")
            parts.append(self.tr("errors %1").replace("%1", str(status.error_frames)))
            text = " · ".join(parts)
        self.errors.setText(text)
        alarm = self._state == ConnectionState.CONNECTED and status.state in ("passive", "bus-off")
        self.errors.setProperty("error", "true" if alarm else "false")
        refresh_style(self.errors)

    def retranslate(self) -> None:
        """Set every text of the bar in the current language."""
        if self._state == ConnectionState.CONNECTED:
            self.bus.set_state("operational", self.tr("Connected"))
        elif self._state == ConnectionState.CONNECTING:
            self.bus.set_state("preop", self.tr("Connecting…"))
        elif self._state == ConnectionState.LOST:
            self.bus.set_state("error", self.tr("Adapter lost"))
        else:
            self.bus.set_state("stopped", self.tr("Not connected"))
        self.adapter.setText(self._adapter_text or self.tr("no adapter"))
        self.bitrate.setText(format_bitrate(self._bitrate))
        self._show_traffic()
        self._show_controller()
        if self._event is None:
            self.last_event.setText(self.tr("Ready"))

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 (Qt API)
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)
