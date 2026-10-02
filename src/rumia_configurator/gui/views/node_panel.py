"""Network panel on the left: scan, node list, network-wide NMT commands (UI-LAY-02).

The node list arrives with the scan (T1.4); for now the panel shows its empty state.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from rumia_configurator.gui.theme.tokens import METRICS
from rumia_configurator.gui.widgets.brand import SectionLabel, make_button, make_label

MIN_WIDTH = 220


class NodePanel(QFrame):
    """Surface panel; its width is set by the splitter and saved between sessions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "panel")
        self.setMinimumWidth(MIN_WIDTH)
        m = METRICS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.space_l, m.space_l, m.space_l, m.space_l)
        layout.setSpacing(m.space_s + 2)

        header = QHBoxLayout()
        self.title = SectionLabel("", self)
        header.addWidget(self.title)
        header.addStretch(1)
        self.scan_button = make_button("", size="compact", icon="refresh-cw", parent=self)
        self.scan_button.setEnabled(False)
        header.addWidget(self.scan_button)
        layout.addLayout(header)

        self.empty_title = make_label("", "strong", self)
        self.empty_title.setWordWrap(True)
        layout.addWidget(self.empty_title)
        self.empty_text = make_label("", "small", self)
        self.empty_text.setWordWrap(True)
        layout.addWidget(self.empty_text)
        layout.addStretch(1)

        self.network_label = SectionLabel("", self)
        layout.addWidget(self.network_label)
        commands = QGridLayout()
        commands.setSpacing(m.space_xs + 2)
        self.start_button = make_button("", size="compact", parent=self)
        self.preop_button = make_button("", size="compact", parent=self)
        self.reset_button = make_button("", size="compact", parent=self)
        for column, button in enumerate((self.start_button, self.preop_button, self.reset_button)):
            button.setEnabled(False)
            commands.addWidget(button, 0, column)
        layout.addLayout(commands)
        self.node_count = 0
        self.retranslate()

    def retranslate(self) -> None:
        self.title.setText(self.tr("Network · %n node(s)", "", self.node_count))
        self.scan_button.setText(self.tr("Scan"))
        self.scan_button.setToolTip(self.tr("Look for the nodes on the network"))
        self.empty_title.setText(self.tr("No nodes yet"))
        self.empty_text.setText(
            self.tr("Connect to the adapter, then press Scan to find the nodes on the network.")
        )
        self.network_label.setText(self.tr("Commands to the whole network"))
        self.start_button.setText(self.tr("Start"))
        self.start_button.setToolTip(self.tr("Put every node in Operational state"))
        self.preop_button.setText(self.tr("Pre-op"))
        self.preop_button.setToolTip(self.tr("Put every node in Pre-operational state"))
        self.reset_button.setText(self.tr("Reset"))
        self.reset_button.setToolTip(self.tr("Restart every node"))

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 (Qt API)
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)
