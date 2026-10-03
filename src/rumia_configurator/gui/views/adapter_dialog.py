"""Dialog "Other adapter…": backend and channel of an adapter that is not listed.

PEAK, Kvaser, IXXAT and candleLight adapters are not probed (that would load
their drivers at every refresh), and a serial port may have a name the list
does not show: here the user types it.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QWidget,
)

from rumia_configurator.core.connection import Backend
from rumia_configurator.gui.widgets.brand import make_label


class AdapterDialog(QDialog):
    """Choose a backend among those that work on this system and type the channel."""

    def __init__(
        self,
        backends: list[Backend],
        backend: str = "",
        channel: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Other adapter"))
        self._backends = backends
        layout = QFormLayout(self)
        self.backend_box = QComboBox(self)
        for item in backends:
            self.backend_box.addItem(item.label, item.name)
        index = self.backend_box.findData(backend)
        self.backend_box.setCurrentIndex(max(index, 0))
        layout.addRow(self.tr("Adapter type"), self.backend_box)
        self.channel_edit = QLineEdit(channel, self)
        layout.addRow(self.tr("Channel"), self.channel_edit)
        self.hint = make_label("", "small", self)
        self.hint.setWordWrap(True)
        layout.addRow("", self.hint)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)
        self.backend_box.currentIndexChanged.connect(self._update_hint)
        self.channel_edit.textChanged.connect(self._update_hint)
        self._update_hint()

    def selection(self) -> tuple[str, str]:
        """Backend name and channel, with spaces trimmed."""
        return str(self.backend_box.currentData()), self.channel_edit.text().strip()

    def _update_hint(self) -> None:
        backend = self._backends[self.backend_box.currentIndex()]
        self.channel_edit.setPlaceholderText(backend.channel_example)
        hint = self.tr("Example: %1").replace("%1", backend.channel_example)
        if not backend.needs_bitrate:
            hint += " " + self.tr(
                "The bitrate of this adapter is set in the operating system, not here."
            )
        self.hint.setText(hint)
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setEnabled(bool(self.channel_edit.text().strip()))
