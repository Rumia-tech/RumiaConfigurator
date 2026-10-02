"""Status bar: bus state, adapter, bitrate, frames/s, load, errors, last event (UI-LAY-04).

The values arrive with the connection and the statistics (T1.1, T1.3).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from rumia_configurator.gui.theme.fonts import mono_font
from rumia_configurator.gui.theme.tokens import METRICS, TYPOGRAPHY
from rumia_configurator.gui.views.top_bar import format_bitrate
from rumia_configurator.gui.widgets.brand import StatusLed


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
        self.retranslate()

    def _field(self, layout: QHBoxLayout) -> QLabel:
        label = QLabel(self)
        label.setFont(mono_font(TYPOGRAPHY.small_px))
        layout.addWidget(label)
        return label

    def show_event(self, text: str) -> None:
        """Show the last event; the text must already be translated."""
        self._event = text
        self.last_event.setText(text)

    def retranslate(self) -> None:
        self.bus.set_state("stopped", self.tr("Not connected"))
        self.adapter.setText(self.tr("no adapter"))
        self.bitrate.setText(format_bitrate(self._bitrate))
        self.frames.setText(self.tr("%1 frames/s").replace("%1", "0"))
        self.load.setText(self.tr("load %1").replace("%1", "-"))
        self.errors.setText(self.tr("errors %1").replace("%1", "0"))
        if self._event is None:
            self.last_event.setText(self.tr("Ready"))

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 (Qt API)
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)
