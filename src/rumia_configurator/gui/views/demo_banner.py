"""Banner shown for the whole session in demo mode (FR-CON-06).

It cannot be closed: the user must always know that the nodes on screen are
simulated and that no real device is connected.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from rumia_configurator.gui.theme.tokens import METRICS
from rumia_configurator.gui.widgets.brand import Callout


class DemoBanner(QFrame):
    """Full-width callout between the top bar and the work area."""

    def __init__(self, nodes: list[tuple[str, int]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._nodes = nodes
        m = METRICS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.space_l, m.space_s, m.space_l, m.space_s)
        self.callout = Callout("", "", "info", self)
        layout.addWidget(self.callout)
        self.retranslate()

    def retranslate(self) -> None:
        """Set the texts in the current language."""
        nodes = ", ".join(f"{name} {node_id}" for name, node_id in self._nodes)
        self.callout.title_label.setText(self.tr("Demo mode"))
        self.callout.text_label.setText(
            self.tr(
                "Virtual bus with simulated nodes (%1). No real device is connected: "
                "to use a sensor, restart the application without --demo."
            ).replace("%1", nodes)
        )
        self.callout.text_label.setVisible(True)

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 (Qt API)
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)
