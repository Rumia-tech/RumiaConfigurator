"""NMT menu of one node (FR-NET-04): in the node header and on a right click on its row.

The entries that ask for confirmation end with "…". The names of the NMT
commands are the CANopen ones and are not translated.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QWidget

from rumia_configurator.core.network import NmtCommand

# Commands of the node menu; the resets ask for confirmation.
NODE_COMMANDS = (
    NmtCommand.START,
    NmtCommand.STOP,
    NmtCommand.PRE_OPERATIONAL,
    NmtCommand.RESET_NODE,
    NmtCommand.RESET_COMMUNICATION,
)

COMMAND_NAMES = {
    NmtCommand.START: "Start",
    NmtCommand.STOP: "Stop",
    NmtCommand.PRE_OPERATIONAL: "Pre-operational",
    NmtCommand.RESET_NODE: "Reset node",
    NmtCommand.RESET_COMMUNICATION: "Reset communication",
}


class NmtMenu(QMenu):
    """Menu with the NMT commands of a node; emits ``command_chosen``."""

    command_chosen = Signal(object)  # NmtCommand

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.command_actions: dict[NmtCommand, QAction] = {}
        for command in NODE_COMMANDS:
            if command == NmtCommand.RESET_NODE:
                self.addSeparator()
            action = self.addAction("")
            action.triggered.connect(lambda _checked=False, c=command: self.command_chosen.emit(c))
            self.command_actions[command] = action
        self.retranslate()

    def retranslate(self) -> None:
        """Command names; "…" marks the commands that ask for confirmation."""
        for command, action in self.command_actions.items():
            name = COMMAND_NAMES[command]
            action.setText(f"{name}…" if command.is_reset else name)
            action.setToolTip(self.tr("Ask for confirmation") if command.is_reset else "")
